#!/bin/bash
# gitee 镜像 14 秒就下完 30MB CPython 源码（gh-proxy 只有 5-35KB/s）。
# 先把最大的 CPython 预置进 p4a 缓存，其余包让它自己下，边下边看。
set -uo pipefail

PKG="/root/.local/share/python-for-android/packages"
pkill -9 -f "p4a apk" 2>/dev/null || true
sleep 1

if [ ! -s /tmp/cp.tgz ]; then
  echo "从 gitee 重新下载 CPython"
  timeout 180 curl -sL -o /tmp/cp.tgz \
    "https://gitee.com/mirrors/cpython/repository/archive/v3.14.2.tar.gz"
fi
ls -lh /tmp/cp.tgz
tar tzf /tmp/cp.tgz | head -1

mkdir -p "$PKG/hostpython3" "$PKG/python3"
cp /tmp/cp.tgz "$PKG/hostpython3/v3.14.2.tar.gz"
cp /tmp/cp.tgz "$PKG/python3/v3.14.2.tar.gz"
echo "已预置："
ls -lh "$PKG/hostpython3/" "$PKG/python3/"

echo "=== 继续构建 ==="
export PIP_BREAK_SYSTEM_PACKAGES=1
exec bash "/mnt/d/项目/AI多模态控制台/android/build_p4a.sh"
