#!/bin/bash
# 修 hostpython3 里坏掉的 pip（BuildDependencyInstallError = 混装），再继续构建
set -uo pipefail

NB="/root/.local/share/python-for-android/build/other_builds/hostpython3/desktop/hostpython3/native-build"
SP="$NB/root/usr/local/lib/python3.14/site-packages"

echo "=== 找 hostpython 可执行文件 ==="
HPY=""
for c in "$NB/root/usr/local/bin/python3" "$NB/root/usr/local/bin/python3.14" "$NB/python3" "$NB/root/usr/local/bin/hostpython3"; do
  [ -x "$c" ] && { HPY="$c"; break; }
done
if [ -z "$HPY" ]; then
  HPY=$(find "$NB" -maxdepth 4 -type f \( -name "python3" -o -name "python3.14" \) -perm -u+x 2>/dev/null | head -1)
fi
echo "hostpython = ${HPY:-未找到}"
[ -n "${HPY:-}" ] || { echo "!! 找不到 hostpython"; exit 1; }
"$HPY" -V 2>&1 | head -1

echo "=== 清掉混装的 pip ==="
rm -rf "$SP"/pip "$SP"/pip-*.dist-info 2>/dev/null || true
ls "$SP" 2>/dev/null | grep -i "^pip" || echo "（pip 目录已清空）"

echo "=== ensurepip 重装 ==="
"$HPY" -m ensurepip --upgrade --default-pip 2>&1 | tail -2
"$HPY" -m pip --version 2>&1 | tail -1

echo "=== 装 Cython（阿里云）==="
"$HPY" -m pip install -q -i https://mirrors.aliyun.com/pypi/simple/ \
    --trusted-host mirrors.aliyun.com "Cython" 2>&1 | tail -3
"$HPY" -c "import Cython; print('Cython OK', Cython.__version__)" 2>&1 | tail -1

echo "=== 重跑构建 ==="
export PIP_INDEX_URL="https://mirrors.aliyun.com/pypi/simple/"
export PIP_TRUSTED_HOST="mirrors.aliyun.com"
export PIP_BREAK_SYSTEM_PACKAGES=1
pkill -9 -f "p4a apk" 2>/dev/null || true
sleep 1
exec bash "/mnt/d/项目/AI多模态控制台/android/build_p4a.sh"
