#!/bin/bash
# 用 PyPI（阿里云镜像）拿 python-for-android 源码，绕开 GitHub 龟速/502
set -uo pipefail

pkill -9 -f "git clone" 2>/dev/null || true
pkill -9 -f "buildozer" 2>/dev/null || true
sleep 2

DST="/root/build_apk/.buildozer/android/platform/python-for-android"
mkdir -p /tmp/p4adl

echo "=== 1. 从阿里云 PyPI 下载 sdist ==="
python3 -m pip download python-for-android --no-deps --no-binary :all: -d /tmp/p4adl 2>&1 | tail -4
ls -la /tmp/p4adl

echo "=== 2. 解压 ==="
cd /tmp
for f in /tmp/p4adl/*.tar.gz; do
  echo "解压 $f"
  tar xzf "$f"
done
ls -d /tmp/python*android* 2>/dev/null
SRC=$(ls -d /tmp/python_for_android-* /tmp/python-for-android-* 2>/dev/null | head -1)
echo "源码目录：$SRC"
if [ -z "${SRC:-}" ] || [ ! -f "$SRC/setup.py" ]; then
  echo "!!! 没拿到源码"
  exit 1
fi

echo "=== 3. 放进 buildozer 期望的位置 ==="
rm -rf "$DST"
mkdir -p "$(dirname "$DST")"
cp -r "$SRC" "$DST"
du -sh "$DST"
ls "$DST" | head -8
echo "版本：$(grep -m1 version "$DST/setup.py" || true)"

echo "=== 4. 开始构建 ==="
exec bash "/mnt/d/项目/AI多模态控制台/android/build_apk.sh"
