#!/bin/bash
# openssl 单独补：清华源 23 KB/s 但能下，用 wget 断点续传慢慢磨，下完打 .mark
set -uo pipefail

D="/root/.local/share/python-for-android/packages/openssl"
F="openssl-3.3.1.tar.gz"
mkdir -p "$D"
cd "$D"

URLS=(
  "https://mirrors.tuna.tsinghua.edu.cn/openssl/source/openssl-3.3.1.tar.gz"
  "https://mirrors.ustc.edu.cn/openssl/source/openssl-3.3.1.tar.gz"
  "https://mirrors.aliyun.com/openssl/source/openssl-3.3.1.tar.gz"
)

for u in "${URLS[@]}"; do
  echo "=== $u"
  for attempt in 1 2 3; do
    wget -q -c --tries=3 --timeout=60 --read-timeout=120 -O "$F" "$u" && break
    echo "  第 $attempt 次失败，重试"
    sleep 3
  done
  if [ -s "$F" ]; then
    SZ=$(stat -c%s "$F")
    echo "  已下 $((SZ/1024)) KB"
    if [ "$SZ" -gt 10000000 ]; then
      # 校验能否解压
      if tar tzf "$F" >/dev/null 2>&1; then
        touch ".mark-$F"
        echo "  ✅ 完整，已打标记"
        ls -lh "$F" ".mark-$F"
        exit 0
      else
        echo "  压缩包损坏，换源重下"
        rm -f "$F"
      fi
    fi
  fi
done

echo "!!! openssl 没拿到"
exit 1
