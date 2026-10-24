#!/bin/bash
# gh-proxy.com 实测 1.3 MB/s（其它镜像 0），换成它并清掉下了一半的包
set -uo pipefail

RECIPE="/root/p4a_src/pythonforandroid/recipe.py"
pkill -9 -f "p4a apk" 2>/dev/null || true
sleep 1

sed -i 's|_MIRRORS = .*|_MIRRORS = ("https://gh-proxy.com/",)|' "$RECIPE"
grep -n "_MIRRORS" "$RECIPE"

# 不完整的下载会让 recipe 报校验/解压错误，先清掉
rm -rf /root/.local/share/python-for-android/packages/*
rm -rf /root/.local/share/python-for-android/build

echo "=== 继续构建 ==="
export PIP_BREAK_SYSTEM_PACKAGES=1
exec bash "/mnt/d/项目/AI多模态控制台/android/build_p4a.sh"
