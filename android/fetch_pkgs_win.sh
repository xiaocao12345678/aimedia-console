#!/bin/bash
# 在 Windows 侧用 FlClash 代理（127.0.0.1:7890）把 p4a 需要的源码包全部下好
set -uo pipefail

BASE="/d/项目/AI多模态控制台/android"
LIST="$BASE/pkglist.txt"
CACHE="/c/Users/22153/AppData/Local/hermes/cache/scratch/pkgcache"   # 用纯 ASCII 路径，MSYS curl 写中文路径会 error 23
PROXY="http://127.0.0.1:7890"

mkdir -p "$CACHE"
total=0; ok=0

while IFS=$'\t' read -r recipe url fname; do
  [ -z "${recipe:-}" ] && continue
  total=$((total+1))
  out="$CACHE/$fname"

  # hostpython3 与 python3 指向同一个包，已下过就复用
  if [ -s "$out" ] && [ "$(stat -c%s "$out")" -gt 50000 ]; then
    echo "复用 $fname ($(( $(stat -c%s "$out") / 1024 )) KB)"
    ok=$((ok+1)); continue
  fi

  echo "下载 $recipe <- $fname"
  if curl -fsSL --proxy "$PROXY" --max-time 600 --retry 3 -o "$out" "$url"; then
    sz=$(stat -c%s "$out")
    if [ "$sz" -gt 50000 ]; then
      echo "   ok $((sz/1024)) KB"
      ok=$((ok+1))
    else
      echo "   太小，删掉"; rm -f "$out"
    fi
  else
    echo "   失败"; rm -f "$out"
  fi
done < "$LIST"

echo
echo "完成 $ok / $total"
ls -lh "$CACHE" | head -14
