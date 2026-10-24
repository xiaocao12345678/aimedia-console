#!/bin/bash
# Android.mk 第 52 行无条件 include external/libjxl/Android.mk。
# 既然已经关掉 SUPPORT_JXL/AVIF（不再需要 jxl/avif 模块），
# 放一个空的 Android.mk 让 include 能成功即可。
set -uo pipefail

D="/root/.local/share/python-for-android/build/bootstrap_builds/sdl2/jni/SDL2_image"
[ -d "$D" ] || { echo "!! 目录不在"; exit 1; }

echo "=== 当前 include 情况 ==="
grep -n "include.*external/\|include.*LIBRARY_PATH" "$D/Android.mk" | head -10

mkdir -p "$D/external/libjxl" "$D/external/libavif"
: > "$D/external/libjxl/Android.mk"
: > "$D/external/libavif/Android.mk"
echo "=== 已放空 Android.mk ==="
ls -la "$D/external/libjxl/" "$D/external/libavif/"

echo "=== 确认 SUPPORT 开关是 false ==="
grep -n "SUPPORT_JXL\|SUPPORT_AVIF" "$D/Android.mk" | head -4

echo "=== 重跑构建 ==="
pkill -9 -f "p4a apk" 2>/dev/null || true
sleep 1
export PIP_BREAK_SYSTEM_PACKAGES=1
exec bash "/mnt/d/项目/AI多模态控制台/android/build_p4a.sh"
