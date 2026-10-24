#!/bin/bash
# SDL2_image 的构建脚本要 git clone libtiff，GitHub 直连 TLS 中断。
# 先把 libtiff 用镜像 clone 好放进 external 目录，构建脚本看到已存在就会跳过。
set -uo pipefail

DST="/root/.local/share/python-for-android/build/bootstrap_builds/sdl2/jni/SDL2_image/external/libtiff"

if [ ! -d /root/libtiff_src/.git ]; then
  echo "重新 clone libtiff"
  rm -rf /root/libtiff_src
  timeout 240 git clone --depth 1 -b v4.2.0-SDL \
    "https://gh-proxy.com/https://github.com/libsdl-org/libtiff.git" /root/libtiff_src || exit 1
fi

mkdir -p "$(dirname "$DST")"
rm -rf "$DST"
cp -r /root/libtiff_src "$DST"
echo "libtiff 就位：$(du -sh "$DST" | cut -f1)"
ls "$DST" | head -5

echo "=== 重跑构建 ==="
pkill -9 -f "p4a apk" 2>/dev/null || true
sleep 1
export PIP_BREAK_SYSTEM_PACKAGES=1
exec bash "/mnt/d/项目/AI多模态控制台/android/build_p4a.sh"
