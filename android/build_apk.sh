#!/usr/bin/env bash
# 在 WSL(Ubuntu) 里把 android/ 打成 debug APK
# 用法：bash build_apk.sh            （首次会下载 SDK/NDK，20-60 分钟）
set -uo pipefail

SRC="/mnt/d/项目/AI多模态控制台/android"
WORK="$HOME/build_apk"

echo "=== 1. 同步源码到 WSL 内部（/mnt/d 上直接构建太慢）==="
mkdir -p "$WORK"
rsync -a \
  --exclude 'bin' --exclude '.buildozer' --exclude '__pycache__' --exclude 'logs' \
  "$SRC/" "$WORK/"
cd "$WORK"
echo "工作目录：$WORK"
du -sh . 2>/dev/null

echo "=== 2. 环境检查 ==="
java -version 2>&1 | head -2
python3 --version
buildozer --version 2>&1 | head -2

echo "=== 3. 开始构建（首次会下载 Android SDK/NDK）==="
export ANDROID_HOME="$HOME/.buildozer/android/platform/android-sdk"
export PATH="$PATH:$HOME/.local/bin"
# Ubuntu 24.04 的 PEP 668：buildozer 内部会 pip install，必须放行
export PIP_BREAK_SYSTEM_PACKAGES=1
python3 -m pip config set global.break-system-packages true >/dev/null 2>&1 || true

buildozer -v android debug 2>&1 | tee build.log | tail -60

echo "=== 4. 产物 ==="
ls -la bin/ 2>/dev/null || echo "没有 bin/ 目录，构建失败"
