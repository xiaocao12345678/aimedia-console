#!/bin/bash
# 从 PyPI 包重建一个「合法的 git 仓库」版 p4a（有 master 分支、有 commit），
# 再用 git insteadOf 把官方 GitHub URL 重写到它，让 buildozer 的 clone/pull 都走本地。
set -uo pipefail

SRC_TGZ=$(ls /tmp/p4adl/python_for_android-*.tar.gz 2>/dev/null | head -1)
P4A="/root/p4a_src"

pkill -9 -f buildozer 2>/dev/null || true
pkill -9 -f "git clone" 2>/dev/null || true
sleep 2

if [ -z "${SRC_TGZ:-}" ] || [ ! -f "$SRC_TGZ" ]; then
  echo "!!! 找不到 PyPI 包，重新下载"
  mkdir -p /tmp/p4adl
  python3 -m pip download python-for-android --no-deps --no-binary :all: -d /tmp/p4adl 2>&1 | tail -2
  SRC_TGZ=$(ls /tmp/p4adl/python_for_android-*.tar.gz | head -1)
fi
echo "包：$SRC_TGZ"

rm -rf "$P4A"
mkdir -p "$P4A"
tar xzf "$SRC_TGZ" -C "$P4A" --strip-components=1

cd "$P4A"
git init -q
git config user.email "build@local"
git config user.name "local"
git add -A >/dev/null 2>&1
git commit -qm "python-for-android 2026.5.9 (from pypi)" >/dev/null 2>&1
git branch -M master
echo "仓库状态："
git log --oneline -1
git branch --show-current
ls | head -5

echo "=== 设置 URL 重写（GitHub → 本地）==="
git config --global --unset-all 'url./root/p4a_backup.insteadOf' 2>/dev/null || true
git config --global --add url."/root/p4a_src".insteadOf "https://github.com/kivy/python-for-android.git"
git config --global --add url."/root/p4a_src".insteadOf "https://github.com/kivy/python-for-android"
git config --global --get-regexp "url\..*insteadof"

echo "=== 验证 clone 能走本地 ==="
rm -rf /tmp/clonetest
git clone -b master --single-branch https://github.com/kivy/python-for-android.git /tmp/clonetest 2>&1 | tail -2
cd /tmp/clonetest && echo "origin=$(git config --get remote.origin.url)" && du -sh .
rm -rf /tmp/clonetest

echo "=== 开始构建 ==="
exec bash "/mnt/d/项目/AI多模态控制台/android/build_apk.sh"
