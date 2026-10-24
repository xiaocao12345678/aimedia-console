#!/bin/bash
# buildozer 会对比 p4a 的 remote url，不同就删掉重新 clone GitHub。
# 用 git 的 insteadOf 把官方 URL 重写到本地备份，这样 clone 秒完成、
# 记录的 remote 也是官方 URL，不会再被判定为「old url」。
set -uo pipefail

P4A_DIR="/root/build_apk/.buildozer/android/platform/python-for-android"
BK="/root/p4a_backup"

pkill -9 -f buildozer 2>/dev/null || true
pkill -9 -f "git clone" 2>/dev/null || true
sleep 2

if [ ! -f "$BK/setup.py" ]; then
  echo "备份不存在，从当前目录重建"
  rm -rf "$BK"
  cp -r "$P4A_DIR" "$BK"
fi

git config --global --unset-all 'url.https://ghproxy.net/https://github.com/.insteadOf' 2>/dev/null || true
git config --global --add url."/root/p4a_backup".insteadOf "https://github.com/kivy/python-for-android.git"
git config --global --add url."/root/p4a_backup".insteadOf "https://github.com/kivy/python-for-android"

echo "=== 重写规则 ==="
git config --global --get-regexp "url\..*insteadof" || true

rm -rf "$P4A_DIR"
echo "=== 模拟 buildozer 的 clone（应走本地）==="
git clone -b master --single-branch https://github.com/kivy/python-for-android.git "$P4A_DIR" 2>&1 | tail -3
cd "$P4A_DIR" && git config --get remote.origin.url && git log --oneline -1 && du -sh .

echo "=== 继续构建 ==="
exec bash "/mnt/d/项目/AI多模态控制台/android/build_apk.sh"
