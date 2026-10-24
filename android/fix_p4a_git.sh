#!/bin/bash
# p4a 是从 PyPI 包解压的，没有 .git，buildozer 取 remote.origin.url 会失败。
# 这里给它做个本地 git 仓库（remote 指向本机备份），pull 秒完成，不会去连 GitHub。
set -uo pipefail

DST="/root/build_apk/.buildozer/android/platform/python-for-android"
BK="/root/p4a_backup"

if [ ! -f "$DST/setup.py" ]; then
  echo "!!! p4a 源码不在 $DST"
  exit 1
fi

rm -rf "$BK"
cp -r "$DST" "$BK"

cd "$DST"
rm -rf .git
git init -q
git config user.email "build@local"
git config user.name "local build"
git remote add origin "$BK"
git add -A >/dev/null 2>&1
git commit -qm "python-for-android from pypi 2026.5.9" >/dev/null 2>&1

echo "=== 检查 ==="
git config --get remote.origin.url
git log --oneline -1
echo "=== 继续构建 ==="
exec bash "/mnt/d/项目/AI多模态控制台/android/build_apk.sh"
