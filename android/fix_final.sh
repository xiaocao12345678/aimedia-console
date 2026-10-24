#!/bin/bash
# 1) 恢复被我改坏的 p4a 源码（.bak）
# 2) 用正确路径给 hostpython 装 Cython
# 3) 关掉 build isolation 后重跑
set -uo pipefail

echo "=== 1. 恢复 p4a 源码 ==="
for f in pythonpackage.py build.py recipe.py toolchain.py; do
  P="/root/p4a_src/pythonforandroid/$f"
  if [ -f "$P.bak" ]; then
    cp -f "$P.bak" "$P"
    echo "  已恢复 $f"
  fi
done
python3 -c "import ast;ast.parse(open('/root/p4a_src/pythonforandroid/pythonpackage.py',encoding='utf-8').read());print('  pythonpackage.py 语法 OK')" || exit 1

echo "=== 2. 找 hostpython 并装 Cython ==="
NB="/root/.local/share/python-for-android/build/other_builds/hostpython3/desktop/hostpython3/native-build"
SP="$NB/root/usr/local/lib/python3.14/site-packages"
HPY=""
for c in "$NB/root/usr/local/bin/python3" "$NB/root/usr/local/bin/python3.14" "$NB/python3" "$NB/root/usr/local/bin/hostpython3"; do
  [ -x "$c" ] && { HPY="$c"; break; }
done
if [ -z "$HPY" ]; then
  HPY=$(ls -1 "$NB"/root/usr/local/bin/python3* 2>/dev/null | head -1)
fi
echo "  hostpython = ${HPY:-未找到}"
if [ -n "${HPY:-}" ]; then
  "$HPY" -V 2>&1 | head -1
  rm -rf "$SP"/pip "$SP"/pip-*.dist-info 2>/dev/null || true
  "$HPY" -m ensurepip --upgrade --default-pip >/dev/null 2>&1 || true
  "$HPY" -m pip --version 2>&1 | tail -1
  "$HPY" -m pip install -q -i https://mirrors.aliyun.com/pypi/simple/ \
     --trusted-host mirrors.aliyun.com "cython>=0.29.34,<4" 2>&1 | tail -2
  "$HPY" -c "import Cython;print('  hostpython Cython', Cython.__version__)" 2>&1 | tail -1
fi

echo "=== 3. 重跑（关掉 build isolation）==="
export PIP_NO_BUILD_ISOLATION=1
export PIP_INDEX_URL="https://mirrors.aliyun.com/pypi/simple/"
export PIP_TRUSTED_HOST="mirrors.aliyun.com"
export PIP_BREAK_SYSTEM_PACKAGES=1
pkill -9 -f "p4a apk" 2>/dev/null || true
sleep 1
exec bash "/mnt/d/项目/AI多模态控制台/android/build_p4a.sh"
