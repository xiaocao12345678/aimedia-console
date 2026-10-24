#!/bin/bash
# 修 kivy wheel 构建时缺 Cython：
#  1) 用 p4a 的 hostpython3 装一份 Cython（走阿里云 PyPI 镜像）
#  2) 关掉 pip 的 build isolation，让它复用这份 Cython
set -uo pipefail

echo "=== 1. 找 hostpython3 ==="
HP=$(find /root/.local/share/python-for-android/build/other_builds/hostpython3 \
     -type f -name "python3*" -perm -u+x 2>/dev/null | grep -vE "\.py$|config" | head -1)
echo "hostpython = ${HP:-未找到}"

if [ -n "${HP:-}" ]; then
  "$HP" -V 2>&1 | head -1
  echo "--- ensurepip"
  "$HP" -m ensurepip --upgrade 2>&1 | tail -2
  echo "--- 装 Cython（阿里云镜像）"
  "$HP" -m pip install -q -i https://mirrors.aliyun.com/pypi/simple/ \
      --trusted-host mirrors.aliyun.com "Cython<4" 2>&1 | tail -3
  "$HP" -c "import Cython; print('Cython OK', Cython.__version__)" 2>&1 | tail -1
fi

echo "=== 2. 同步给系统 python 也装一份（兜底）==="
python3 -m pip install -q --break-system-packages -i https://mirrors.aliyun.com/pypi/simple/ \
    --trusted-host mirrors.aliyun.com "Cython<4" 2>&1 | tail -2
python3 -c "import Cython; print('系统 Cython', Cython.__version__)" 2>&1 | tail -1

echo "=== 3. 关掉 build isolation + 走国内 PyPI，重跑构建 ==="
export PIP_NO_BUILD_ISOLATION=1
export PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
export PIP_TRUSTED_HOST=mirrors.aliyun.com
export PIP_BREAK_SYSTEM_PACKAGES=1
export CYTHON_INSTALL=1

pkill -9 -f "p4a apk" 2>/dev/null || true
sleep 1
exec bash "/mnt/d/项目/AI多模态控制台/android/build_p4a.sh"
