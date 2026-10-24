#!/bin/bash
# p4a 里触发 build isolation 的 pip 调用不止三处（每轮都出现新的 /tmp/build-env-*）。
# 不再逐个堵：在 p4a 入口给 subprocess.Popen 打 hook，
# 凡是 pip 的 install / download / wheel 命令，自动补 --no-build-isolation。
# hostpython3 里已经有 cython，关掉隔离后就能直接用本地那份。
set -uo pipefail

EP="/root/p4a_src/pythonforandroid/entrypoints.py"
cp -f "$EP" "$EP.bak_hook"

if grep -q "AI_MEDIA_PIP_HOOK" "$EP"; then
  echo "hook 已存在"
else
  python3 - "$EP" <<'PY'
import ast, io, sys
p = sys.argv[1]
s = io.open(p, encoding="utf-8").read()

hook = '''
# ===== AI_MEDIA_PIP_HOOK =====
# p4a 有多条 pip 调用路径会在 Python 3.12 上创建 build isolation 环境，
# 而那个环境里只有 setuptools，编译 kivy/pyjnius 这类带 Cython 的包直接失败。
# 这里在最底层（subprocess.Popen）统一补 --no-build-isolation，
# 让它复用 hostpython3 里已装的 cython。
def _ai_media_install_pip_hook():
    import subprocess as _sp

    if getattr(_sp.Popen, "_ai_hooked", False):
        return
    _orig = _sp.Popen.__init__

    def _patched(self, args, *a, **kw):
        try:
            if isinstance(args, (list, tuple)) and args:
                head = " ".join(str(x) for x in args[:2])
                if "pip" in head:
                    items = [str(x) for x in args]
                    if "--no-build-isolation" not in items:
                        for sub in ("install", "download", "wheel"):
                            if sub in items:
                                items.insert(items.index(sub) + 1, "--no-build-isolation")
                                break
                        args = items
        except Exception:
            pass
        return _orig(self, args, *a, **kw)

    _patched._ai_hooked = True
    _sp.Popen.__init__ = _patched
    _sp.Popen._ai_hooked = True


_ai_media_install_pip_hook()

'''

# 插到文件最前面（import 之前也可以，函数体里才 import subprocess）
s = hook + s
ast.parse(s)
io.open(p, "w", encoding="utf-8").write(s)
print("hook 已插入 entrypoints.py 顶部")
PY
fi

python3 -c "import ast;ast.parse(open('$EP',encoding='utf-8').read());print('语法 OK')" || exit 1
head -8 "$EP"

echo "=== 验证 hook 生效（跑一次 p4a --version，看是否报错）==="
p4a --version 2>&1 | head -3

echo "=== 重跑完整构建 ==="
bash /root/run_full_build.sh 2>&1
