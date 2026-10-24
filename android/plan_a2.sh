#!/bin/bash
# A 方案（精确版）：
#   build.py:641 的 pip install 是 kivy/pyjnius 真正构建 wheel 的地方 → 加 --no-build-isolation
#   recipe.py 的 venv 依赖列表 → 加 cython，保证关掉隔离后 venv 里有 Cython 可用
set -uo pipefail

B="/root/p4a_src/pythonforandroid/build.py"
R="/root/p4a_src/pythonforandroid/recipe.py"

cp -f "$B" "$B.bak2"; cp -f "$R" "$R.bak2"

python3 - "$B" "$R" <<'PY'
import ast, io, sys

build_p, recipe_p = sys.argv[1], sys.argv[2]

# ---- 1. build.py：pip install 加 --no-build-isolation ----
s = io.open(build_p, encoding="utf-8").read()
old = '"install -c ._tmp_p4a_recipe_constraints.txt -v ."'
new = '"install --no-build-isolation -c ._tmp_p4a_recipe_constraints.txt -v ."'
if old in s:
    s = s.replace(old, new)
    ast.parse(s)
    io.open(build_p, "w", encoding="utf-8").write(s)
    print("① build.py 补丁完成")
else:
    print("① build.py 目标串没找到（可能已打过）")

# ---- 2. recipe.py：venv 依赖加 cython ----
r = io.open(recipe_p, encoding="utf-8").read()
old2 = 'packages=["build[virtualenv]", "pip", "setuptools", "patchelf"]'
new2 = 'packages=["build[virtualenv]", "pip", "setuptools", "cython<4", "patchelf"]'
n = r.count(old2)
if n:
    r = r.replace(old2, new2)
    ast.parse(r)
    io.open(recipe_p, "w", encoding="utf-8").write(r)
    print(f"② recipe.py 补丁完成（{n} 处）")
else:
    print("② recipe.py 目标串没找到")
PY

echo "=== 确认 ==="
grep -n "no-build-isolation" "$B" | head -3
grep -n "cython<4" "$R" | head -3

echo "=== 重跑构建 ==="
export PIP_INDEX_URL="https://mirrors.aliyun.com/pypi/simple/"
export PIP_TRUSTED_HOST="mirrors.aliyun.com"
export PIP_BREAK_SYSTEM_PACKAGES=1
export PIP_NO_BUILD_ISOLATION=1
pkill -9 -f "p4a apk" 2>/dev/null || true
sleep 1
exec bash "/mnt/d/项目/AI多模态控制台/android/build_p4a.sh"
