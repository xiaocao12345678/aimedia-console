#!/bin/bash
# 一次性准备 WSL 里的 Android 打包环境（换清华源 + 装 JDK/构建工具 + buildozer）
set -uo pipefail

echo "=== 1. 停掉慢速 apt ==="
pkill -9 -f "apt-get install" 2>/dev/null || true
pkill -9 -f "apt/methods" 2>/dev/null || true
sleep 2
rm -f /var/lib/dpkg/lock-frontend /var/lib/apt/lists/lock /var/cache/apt/archives/lock
dpkg --configure -a >/dev/null 2>&1 || true

echo "=== 2. 换清华源 ==="
if [ -f /etc/apt/sources.list.d/ubuntu.sources ]; then
  mv -f /etc/apt/sources.list.d/ubuntu.sources /etc/apt/sources.list.d/ubuntu.sources.bak
fi
cat > /etc/apt/sources.list <<'EOF'
deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ noble main restricted universe multiverse
deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ noble-updates main restricted universe multiverse
deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ noble-backports main restricted universe multiverse
deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ noble-security main restricted universe multiverse
EOF
apt-get update -qq 2>&1 | tail -3
echo "源已换好"

echo "=== 3. 装构建依赖 ==="
export DEBIAN_FRONTEND=noninteractive
apt-get install -y -qq \
  build-essential git zip unzip openjdk-17-jdk \
  python3-pip python3-venv python3-dev \
  autoconf automake libtool pkg-config \
  zlib1g-dev libncurses-dev libtinfo6 cmake \
  libffi-dev libssl-dev liblzma-dev libbz2-dev 2>&1 | tail -6

echo "=== 4. pip 换清华源并装 buildozer ==="
python3 -m pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple 2>/dev/null || true
python3 -m pip install --break-system-packages -q buildozer cython 2>&1 | tail -5

echo "=== 5. 检查 ==="
java -version 2>&1 | head -2
python3 --version
which buildozer && buildozer --version 2>&1 | head -3
echo "SETUP_DONE"
