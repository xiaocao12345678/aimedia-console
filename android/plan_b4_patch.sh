#!/bin/bash
# 上一个 patch 文件把两个 diff 放一起且 hunk 行数算错 → "malformed patch"
# 拆成两个独立 patch，行数按实际上下文算准。
set -uo pipefail

REC="/root/p4a_src/pythonforandroid/recipes/python3"
PD="$REC/patches"
INIT="$REC/__init__.py"

rm -f "$PD/android-grp-pwd.patch"

echo "=== 1. grpmodule.c 的 patch ==="
cat > "$PD/android-grp.patch" <<'EOF'
--- a/Modules/grpmodule.c
+++ b/Modules/grpmodule.c
@@ -4,5 +4,12 @@
 #include "Python.h"
 #include "posixmodule.h"
 
 #include <grp.h>
+
+/* Android NDK has no setgrent/endgrent/getgrent: provide stubs */
+#if defined(__ANDROID__)
+static void setgrent(void) { }
+static void endgrent(void) { }
+static struct group *getgrent(void) { return NULL; }
+#endif
 
EOF

echo "=== 2. pwdmodule.c 的 patch ==="
cat > "$PD/android-pwd.patch" <<'EOF'
--- a/Modules/pwdmodule.c
+++ b/Modules/pwdmodule.c
@@ -4,5 +4,12 @@
 #include "Python.h"
 #include "posixmodule.h"
 
 #include <pwd.h>
+
+/* Android NDK has no setpwent/endpwent/getpwent: provide stubs */
+#if defined(__ANDROID__)
+static void setpwent(void) { }
+static void endpwent(void) { }
+static struct passwd *getpwent(void) { return NULL; }
+#endif
 
EOF

ls -l "$PD"
echo "--- 本地先验证 patch 能用（对已解压源码干跑）"
S="/root/.local/share/python-for-android/build/other_builds/python3"
if [ -d "$S" ]; then
  D=$(ls -d "$S"/*/python3 2>/dev/null | head -1)
  [ -n "${D:-}" ] && for f in android-grp.patch android-pwd.patch; do
    patch -p1 -d "$D" --dry-run -t -i "$PD/$f" && echo "  $f 可应用" || echo "  $f 干跑失败"
  done
fi

echo "=== 3. 更新 recipe 的 patches 列表 ==="
python3 - "$INIT" <<'PY'
import ast, io, re, sys
p = sys.argv[1]
s = io.open(p, encoding="utf-8").read()
# 去掉旧的坏 patch 注册
s = s.replace("        'patches/android-grp-pwd.patch',\n", "")
for name in ("android-grp.patch", "android-pwd.patch"):
    if name in s:
        continue
    s = s.replace("    patches = [\n",
                  "    patches = [\n        'patches/%s',\n" % name, 1)
ast.parse(s)
io.open(p, "w", encoding="utf-8").write(s)
print("已注册两个 patch")
PY
sed -n '70,78p' "$INIT"

echo "=== 4. 清旧解压目录并重跑 ==="
rm -rf /root/.local/share/python-for-android/build/other_builds/python3*
export PIP_INDEX_URL="https://mirrors.aliyun.com/pypi/simple/"
export PIP_TRUSTED_HOST="mirrors.aliyun.com"
export PIP_BREAK_SYSTEM_PACKAGES=1
pkill -9 -f "p4a apk" 2>/dev/null || true
sleep 1
exec bash "/mnt/d/项目/AI多模态控制台/android/build_p4a.sh"
