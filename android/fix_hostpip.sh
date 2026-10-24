#!/bin/bash
# hostpython3 的 pip 被我上一步 ensurepip 弄成混装（ImportError: BuildDependencyInstallError）。
# 清掉 site-packages 里的 pip 再用 ensurepip 重装一份干净的，然后装 Cython。
set -uo pipefail

D="/root/.local/share/python-for-android/build/other_builds/hostpython3/desktop/hostpython3/native-build"
SP="$D/root/usr/local/lib/python3.14/site-packages"
HPY="$D/python3"

[ -x "$HPY" ] || { echo "!! hostpython 不在 $HPY"; exit 1; }
echo "hostpython: $("$HPY" -V 2>&1)"

echo "=== 1. 清掉坏 pip ==="
rm -rf "$SP"/pip "$SP"/pip-*.dist-info "$SP"/_internal 2>/dev/null || true
ls "$SP" | grep -i "^pip" || echo "（pip 已清空）"

echo "=== 2. ensurepip 重装 ==="
"$HPY" -m ensurepip --upgrade --default-pip 2>&1 | tail -3
"$HPY" -m pip --version 2>&1 | tail -1

echo "=== 3. 装 Cython ==="
"$HPY" -m pip install -q -i https://mirrors.aliyun.com/pypi/simple/ \
    --trusted-host mirrors.aliyun.com "Cython<4" 2>&1 | tail -3
"$HPY" -c "import Cython; print('Cython OK', Cython.__version__)" 2>&1 | tail -1

echo "=== 4. 重跑构建 ==="
export PIP_NO_BUILD_ISOLATION=1
export PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
export PIP_TRUSTED_HOST=mirrors.aliyun.com
export PIP_BREAK_SYSTEM_PACKAGES=1
pkill -9 -f "p4a apk" 2>/dev/null || true
sleep 1
exec bash "/mnt/d/项目/AI多模态控制台/android/build_p4a.sh"
