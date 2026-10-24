#!/bin/bash
# 走 p4a 的 recipe patch 机制：
#   Android NDK 没有 setgrent/endgrent/getgrent（以及 pwd 系列），
#   在 grpmodule.c / pwdmodule.c 里补最小桩实现，编译能过、模块仍存在。
set -uo pipefail

REC="/root/p4a_src/pythonforandroid/recipes/python3"
PATCH_DIR="$REC/patches"
PATCH="$PATCH_DIR/android-grp-pwd.patch"
INIT="$REC/__init__.py"

mkdir -p "$PATCH_DIR"

echo "=== 1. 写 patch 文件 ==="
cat > "$PATCH" <<'EOF'
--- a/Modules/grpmodule.c
+++ b/Modules/grpmodule.c
@@ -4,4 +4,12 @@
 #include "Python.h"
 #include "posixmodule.h"
 
 #include <grp.h>
+
+/* Android NDK 未提供这些 libc 函数，补最小桩实现（grp 模块功能不可用，但解释器正常） */
+#if defined(__ANDROID__)
+static void setgrent(void) { }
+static void endgrent(void) { }
+static struct group *getgrent(void) { return NULL; }
+#endif
--- a/Modules/pwdmodule.c
+++ b/Modules/pwdmodule.c
@@ -4,4 +4,12 @@
 #include "Python.h"
 #include "posixmodule.h"
 
 #include <pwd.h>
+
+/* Android NDK 同样没有 pwd 系列，补桩 */
+#if defined(__ANDROID__)
+static void setpwent(void) { }
+static void endpwent(void) { }
+static struct passwd *getpwent(void) { return NULL; }
+#endif
EOF
ls -l "$PATCH"
head -6 "$PATCH"

echo "=== 2. 注册到 recipe 的 patches 列表 ==="
cp -f "$INIT" "$INIT.bak_patch"
python3 - "$INIT" <<'PY'
import ast, io, sys
p = sys.argv[1]
s = io.open(p, encoding="utf-8").read()
if "android-grp-pwd.patch" in s:
    print("已注册")
    raise SystemExit(0)
old = "    patches = [\n"
if old not in s:
    print("!! 找不到 patches = [ 结构")
    raise SystemExit(1)
s = s.replace(old, old + "        'patches/android-grp-pwd.patch',\n", 1)
ast.parse(s)
io.open(p, "w", encoding="utf-8").write(s)
print("已插入 patches 列表")
PY

sed -n '70,78p' "$INIT"

echo "=== 3. 清掉旧的 python3 解压目录，让 p4a 重新解包并打 patch ==="
rm -rf /root/.local/share/python-for-android/build/other_builds/python3*

echo "=== 4. 重跑 ==="
export PIP_INDEX_URL="https://mirrors.aliyun.com/pypi/simple/"
export PIP_TRUSTED_HOST="mirrors.aliyun.com"
export PIP_BREAK_SYSTEM_PACKAGES=1
pkill -9 -f "p4a apk" 2>/dev/null || true
sleep 1
exec bash "/mnt/d/项目/AI多模态控制台/android/build_p4a.sh"
