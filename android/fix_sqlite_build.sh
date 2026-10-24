#!/bin/bash
# sqlite 包之前是残缺的（472K，实际 12.4MB），换掉并校验所有包，然后重跑构建
set -uo pipefail

CACHE="/mnt/c/Users/22153/AppData/Local/hermes/cache/scratch/pkgcache"
PKG="/root/.local/share/python-for-android/packages"
LIST="/mnt/d/项目/AI多模态控制台/android/pkglist.txt"

echo "=== 1. 重新分发 + 校验每个包 ==="
while IFS=$'\t' read -r recipe url fname; do
  [ -z "${recipe:-}" ] && continue
  src="$CACHE/$fname"
  d="$PKG/$recipe"
  mkdir -p "$d"
  if [ ! -s "$src" ]; then
    echo "  ❌ $recipe/$fname 缓存缺失"
    continue
  fi
  cp -f "$src" "$d/$fname"
  touch "$d/.mark-$fname"

  # 完整性校验
  case "$fname" in
    *.tar.gz|*.tgz)
      if tar tzf "$d/$fname" >/dev/null 2>&1; then
        echo "  ✅ $recipe/$fname ($(( $(stat -c%s "$src") / 1024 )) KB)"
      else
        echo "  ⚠️  $recipe/$fname 解压校验失败（$(( $(stat -c%s "$src") / 1024 )) KB）"
      fi
      ;;
    *.zip)
      if unzip -tq "$d/$fname" >/dev/null 2>&1; then
        echo "  ✅ $recipe/$fname ($(( $(stat -c%s "$src") / 1024 )) KB)"
      else
        echo "  ⚠️  $recipe/$fname 解压校验失败（$(( $(stat -c%s "$src") / 1024 )) KB）"
      fi
      ;;
    *) echo "  ? $recipe/$fname" ;;
  esac
done < "$LIST"

echo
echo "=== 2. 重跑构建 ==="
pkill -9 -f "p4a apk" 2>/dev/null || true
sleep 1
export PIP_BREAK_SYSTEM_PACKAGES=1
exec bash "/mnt/d/项目/AI多模态控制台/android/build_p4a.sh"
