#!/bin/bash
# WSL 打包环境（第二版）：清代理 + 换阿里云源 + 装 JDK/工具/中文字体 + buildozer
set -uo pipefail

echo "=== 0. 清掉代理变量（有代理时国内镜像会 403）==="
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY all_proxy ALL_PROXY ftp_proxy FTP_PROXY 2>/dev/null || true
env | grep -i proxy || echo "（无代理变量）"

echo "=== 1. 换阿里云源 ==="
mkdir -p /etc/apt/sources.list.d
rm -f /etc/apt/sources.list.d/ubuntu.sources /etc/apt/sources.list.d/*.list 2>/dev/null || true
cat > /etc/apt/sources.list <<'EOF'
deb http://mirrors.aliyun.com/ubuntu/ noble main restricted universe multiverse
deb http://mirrors.aliyun.com/ubuntu/ noble-updates main restricted universe multiverse
deb http://mirrors.aliyun.com/ubuntu/ noble-backports main restricted universe multiverse
deb http://mirrors.aliyun.com/ubuntu/ noble-security main restricted universe multiverse
EOF
apt-get update 2>&1 | tail -3

echo "=== 2. 装依赖 + 中文字体 ==="
export DEBIAN_FRONTEND=noninteractive
apt-get install -y --fix-missing \
  build-essential git zip unzip openjdk-17-jdk \
  python3-pip python3-venv python3-dev \
  autoconf automake libtool pkg-config \
  zlib1g-dev libncurses-dev libtinfo6 cmake \
  libffi-dev libssl-dev liblzma-dev libbz2-dev \
  fonts-noto-cjk 2>&1 | tail -8

echo "=== 3. pip（阿里云 PyPI 镜像）装 buildozer ==="
python3 -m pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ 2>/dev/null || true
python3 -m pip config set global.trusted-host mirrors.aliyun.com 2>/dev/null || true
python3 -m pip install --break-system-packages -q buildozer cython 2>&1 | tail -5

echo "=== 4. 字体 ==="
ls -la /usr/share/fonts/opentype/noto/ 2>/dev/null | head -6

echo "=== 5. 检查 ==="
java -version 2>&1 | head -2
python3 --version
command -v buildozer && buildozer --version 2>&1 | head -2
echo "SETUP_DONE"
