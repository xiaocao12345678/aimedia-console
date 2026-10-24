#!/bin/bash
# 把 Windows 侧下载好的包分发进 WSL 的 p4a 缓存，并打好 .mark（p4a 靠 .mark 判断不用重下）
set -uo pipefail

CACHE="/mnt/c/Users/22153/AppData/Local/hermes/cache/scratch/pkgcache"
PKG="/root/.local/share/python-for-android/packages"
LIST="/mnt/d/项目/AI多模态控制台/android/pkglist.txt"

echo "=== 分发包 ==="
while IFS=$'\t' read -r recipe url fname; do
  [ -z "${recipe:-}" ] && continue
  src="$CACHE/$fname"
  dst_dir="$PKG/$recipe"
  mkdir -p "$dst_dir"
  if [ -s "$src" ] && [ "$(stat -c%s "$src")" -gt 50000 ]; then
    cp -f "$src" "$dst_dir/$fname"
    touch "$dst_dir/.mark-$fname"
    echo "  ✅ $recipe/$fname ($(( $(stat -c%s "$src") / 1024 )) KB)"
  else
    echo "  ❌ $recipe/$fname 缺失（缓存里没有）"
  fi
done < "$LIST"

echo
echo "=== 缓存现状 ==="
for d in "$PKG"/*/; do
  n=$(basename "$d")
  files=$(ls -A "$d" 2>/dev/null | grep -v '^\.mark' | tr '\n' ' ')
  marks=$(ls -A "$d" 2>/dev/null | grep -c '^\.mark')
  echo "  $n: [$files] mark=$marks"
done

echo
echo "=== 停掉旧的 p4a ==="
pkill -9 -f "p4a apk" 2>/dev/null || true
sleep 1

echo "=== 开始构建（离线，应该不会再卡下载）==="
export PIP_BREAK_SYSTEM_PACKAGES=1
exec bash "/mnt/d/项目/AI多模态控制台/android/build_p4a.sh"
