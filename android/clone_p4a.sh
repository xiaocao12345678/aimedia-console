#!/bin/bash
# 用国内加速镜像 clone python-for-android，避免 buildozer 直连 GitHub 龟速
set -uo pipefail

P4A_DIR="/root/build_apk/.buildozer/android/platform/python-for-android"

pkill -9 -f "buildozer" 2>/dev/null || true
pkill -9 -f "git clone.*python-for-android" 2>/dev/null || true
sleep 2
rm -rf "$P4A_DIR"
mkdir -p "$(dirname "$P4A_DIR")"

MIRRORS=(
  "https://ghfast.top/https://github.com/kivy/python-for-android.git"
  "https://ghproxy.net/https://github.com/kivy/python-for-android.git"
  "https://gitclone.com/github.com/kivy/python-for-android.git"
  "https://github.com/kivy/python-for-android.git"
)

for m in "${MIRRORS[@]}"; do
  echo "=== 尝试 $m"
  rm -rf "$P4A_DIR"
  if timeout 420 git clone --depth 1 -b master "$m" "$P4A_DIR" 2>&1 | tail -3; then
    if [ -f "$P4A_DIR/setup.py" ]; then
      echo "CLONE_OK 来自 $m"
      du -sh "$P4A_DIR"
      cd "$P4A_DIR" && git log --oneline -1
      exit 0
    fi
  fi
  echo "这个源不行，换下一个"
done

echo "!!! 所有镜像都失败"
exit 1
