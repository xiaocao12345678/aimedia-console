#!/bin/bash
# export 的 ac_cv_* 被 p4a 的 env 覆盖了，改为写进 python3 recipe 的 get_recipe_env，
# 让 configure 真正读到"Android 没有 getgrent/setgrent"这些事实。
set -uo pipefail

R="/root/p4a_src/pythonforandroid/recipes/python3/__init__.py"
[ -f "$R" ] || { echo "!! 没有 python3 recipe"; exit 1; }
cp -f "$R" "$R.bak_grp"

python3 - "$R" <<'PY'
import ast, io, re, sys

p = sys.argv[1]
s = io.open(p, encoding="utf-8").read()

if "ac_cv_func_setgrent" in s:
    print("补丁已存在")
    raise SystemExit(0)

# 找 class 定义行
m = re.search(r"^class\s+\w+\(.*Recipe.*\):\s*$", s, re.M)
if not m:
    print("!! 找不到 class 定义")
    raise SystemExit(1)

indent = "    "
method = (
    f"{indent}def get_recipe_env(self, arch=None, with_flags_in_cc=True):\n"
    f"{indent}    env = super().get_recipe_env(arch, with_flags_in_cc)\n"
    f"{indent}    # Android NDK 不提供 getgrent/setgrent/getpwent 等函数，\n"
    f"{indent}    # configure 却会检测到声明存在，导致 grpmodule.c/pwdmodule.c 编译失败。\n"
    f"{indent}    for _f in (\"setgrent\", \"getgrent\", \"endgrent\",\n"
    f"{indent}               \"setpwent\", \"getpwent\", \"endpwent\",\n"
    f"{indent}               \"getpwnam\", \"getpwuid\", \"getgrgid\", \"getgrnam\"):\n"
    f"{indent}        env[\"ac_cv_func_\" + _f] = \"no\"\n"
    f"{indent}    return env\n\n"
)

pos = m.end() + 1
s = s[:pos] + method + s[pos:]
ast.parse(s)
io.open(p, "w", encoding="utf-8").write(s)
print("get_recipe_env 已插入")
PY

echo "=== 确认 ==="
grep -n -A6 "ac_cv_func_setgrent" "$R" | head -10

echo "=== 重跑（先删 python3/hostpython3 的旧产物让 configure 重跑）==="
rm -rf /root/.local/share/python-for-android/build/other_builds/python3* \
       /root/.local/share/python-for-android/build/other_builds/hostpython3
export PIP_INDEX_URL="https://mirrors.aliyun.com/pypi/simple/"
export PIP_TRUSTED_HOST="mirrors.aliyun.com"
export PIP_BREAK_SYSTEM_PACKAGES=1
pkill -9 -f "p4a apk" 2>/dev/null || true
sleep 1
exec bash "/mnt/d/项目/AI多模态控制台/android/build_p4a.sh"
