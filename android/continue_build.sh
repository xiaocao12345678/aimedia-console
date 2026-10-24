#!/bin/bash
# 测一下 python.org 实际下载速度，然后继续 p4a 构建
set -uo pipefail

echo "=== 测速（10 秒采样）==="
SPD=$(timeout 12 curl -o /dev/null -w "%{speed_download}" \
      https://www.python.org/ftp/python/3.14.2/Python-3.14.2.tgz 2>/dev/null || echo 0)
echo "python.org: $(( ${SPD%.*} / 1024 )) KB/s"

echo "=== 现有 package 缓存 ==="
ls -la /root/.local/share/python-for-android/packages/*/ 2>/dev/null | head -12

echo "=== 继续构建 ==="
exec bash "/mnt/d/项目/AI多模态控制台/android/build_p4a.sh"
