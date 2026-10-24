#!/bin/bash
# 给 CPython 源码找最快的下载源（p4a 要从 GitHub 拿，直连被墙）
U="https://github.com/python/cpython/archive/refs/tags/v3.14.2.tar.gz"
echo "目标文件：CPython 3.14.2 源码（约 25 MB）"
echo

for base in \
  "https://ghproxy.net/" \
  "https://gh-proxy.com/" \
  "https://ghfast.top/" \
  "https://mirror.ghproxy.com/" \
  "https://gh.reallyfast.top/" \
  "https://cdn.moran233.xyz/" \
  "https://gh.xxooo.cf/" ; do
  SPD=$(timeout 15 curl -sL --max-time 14 -o /dev/null -w "%{speed_download}" "${base}${U}" 2>/dev/null || echo 0)
  KB=$(( ${SPD%.*} / 1024 ))
  printf "%-32s %6s KB/s\n" "$base" "$KB"
done

echo
echo "--- 直连"
SPD=$(timeout 10 curl -sL --max-time 9 -o /dev/null -w "%{speed_download}" "$U" 2>/dev/null || echo 0)
echo "github.com 直连: $(( ${SPD%.*} / 1024 )) KB/s"

echo
echo "--- gitee 镜像（不一定是同一份 tag 包）"
for g in \
  "https://gitee.com/mirrors/cpython/repository/archive/v3.14.2.tar.gz" \
  "https://gitee.com/mirrors/Python/repository/archive/v3.14.2.tar.gz" ; do
  code=$(timeout 15 curl -sL -o /dev/null -w "%{http_code} %{speed_download}" --max-time 14 "$g" 2>/dev/null || echo "0 0")
  echo "$g -> $code"
done
