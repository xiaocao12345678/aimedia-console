#!/bin/bash
# archive.apache.org 太慢，改用国内镜像手动放好 ANT，buildozer 会跳过下载
set -uo pipefail

pkill -9 -f buildozer 2>/dev/null || true
sleep 2

DEST="/root/.buildozer/android/platform"
mkdir -p "$DEST"
cd /tmp

URLS=(
  "https://mirrors.aliyun.com/apache/ant/binaries/apache-ant-1.9.4-bin.tar.gz"
  "https://mirrors.huaweicloud.com/apache/ant/binaries/apache-ant-1.9.4-bin.tar.gz"
  "https://mirrors.tuna.tsinghua.edu.cn/apache/ant/binaries/apache-ant-1.9.4-bin.tar.gz"
  "https://archive.apache.org/dist/ant/binaries/apache-ant-1.9.4-bin.tar.gz"
)

got=""
for u in "${URLS[@]}"; do
  echo "=== $u"
  if timeout 120 curl -fsSL -o ant.tar.gz "$u" && [ -s ant.tar.gz ] && [ "$(stat -c%s ant.tar.gz)" -gt 1000000 ]; then
    echo "下载成功 $(du -h ant.tar.gz | cut -f1)"
    got=1
    break
  fi
  echo "  失败/太慢，换下一个"
done

if [ -z "$got" ]; then
  echo "!!! ANT 下载全部失败"
  exit 1
fi

rm -rf "$DEST/apache-ant-1.9.4"
tar xzf ant.tar.gz -C "$DEST"
ls "$DEST/apache-ant-1.9.4/bin/ant" && echo "ANT 就位"
"$DEST/apache-ant-1.9.4/bin/ant" -version 2>&1 | head -2

echo "=== 继续构建 ==="
exec bash "/mnt/d/项目/AI多模态控制台/android/build_apk.sh"
