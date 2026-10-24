#!/bin/bash
# patch 文件上下文对不上（前面的 pyconfig patch 改了行号）。
# 改为 monkey patch recipe 的 apply_patches：原生 patch 打完后，直接往源码插桩。
set -uo pipefail

INIT="/root/p4a_src/pythonforandroid/recipes/python3/__init__.py"

# 撤掉会失败的 patch 注册
sed -i "/patches\/android-grp.patch/d; /patches\/android-pwd.patch/d" "$INIT"

if grep -q "_ai_media_stub_patched" "$INIT"; then
  echo "monkey patch 已存在"
else
  cat >> "$INIT" <<'PY'


# ==== AI_MEDIA_ANDROID_STUB ====
# Android NDK 不提供 setgrent/getgrent/endgrent（pwd 同理），
# Python 的 grpmodule.c / pwdmodule.c 会调用它们，交叉编译直接报
# "implicit declaration of function 'endgrent' is invalid in C99"。
# 在原生 patches 打完、源码已解压之后，往文件里插入最小桩实现。
_ai_media_stub_patched = True
_ai_orig_apply_patches = Python3Recipe.apply_patches

_GRP_STUB = """
#ifdef __ANDROID__
static void setgrent(void) { }
static void endgrent(void) { }
static struct group *getgrent(void) { return NULL; }
#endif
"""

_PWD_STUB = """
#ifdef __ANDROID__
static void setpwent(void) { }
static void endpwent(void) { }
static struct passwd *getpwent(void) { return NULL; }
#endif
"""


def _ai_media_apply_patches(self, arch, build_dir=None):
    _ai_orig_apply_patches(self, arch, build_dir)

    import os
    d = build_dir or self.get_build_dir(arch)
    targets = [
        (os.path.join(d, "Modules", "grpmodule.c"), "#include <grp.h>", _GRP_STUB),
        (os.path.join(d, "Modules", "pwdmodule.c"), "#include <pwd.h>", _PWD_STUB),
    ]
    for path, anchor, stub in targets:
        try:
            if not os.path.exists(path):
                continue
            src = open(path, encoding="utf-8", errors="ignore").read()
            if "AI_MEDIA_ANDROID_STUB" in src:
                continue
            if anchor not in src:
                print(f"[ai-media] {path} 里找不到锚点 {anchor}")
                continue
            src = src.replace(anchor, anchor + "\n/* AI_MEDIA_ANDROID_STUB */" + stub, 1)
            open(path, "w", encoding="utf-8").write(src)
            print(f"[ai-media] 已插桩 {os.path.basename(path)}")
        except Exception as exc:
            print(f"[ai-media] 插桩失败 {path}: {exc}")


Python3Recipe.apply_patches = _ai_media_apply_patches
PY
  echo "monkey patch 已追加"
fi

python3 -c "import ast;ast.parse(open('$INIT',encoding='utf-8').read());print('语法 OK')" || exit 1
tail -5 "$INIT"

echo "=== 清旧解压目录并重跑 ==="
rm -rf /root/.local/share/python-for-android/build/other_builds/python3*
export PIP_INDEX_URL="https://mirrors.aliyun.com/pypi/simple/"
export PIP_TRUSTED_HOST="mirrors.aliyun.com"
export PIP_BREAK_SYSTEM_PACKAGES=1
pkill -9 -f "p4a apk" 2>/dev/null || true
sleep 1
exec bash "/mnt/d/项目/AI多模态控制台/android/build_p4a.sh"
