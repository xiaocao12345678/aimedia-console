#!/bin/bash
# B 方案：p4a 的 python3 / hostpython3 recipe 从 3.14.2 降到 3.12.8
#  3.12 下 kivy / cython / setuptools 都有成熟 wheel，不必现场编译，绕过那一路 build isolation 问题
set -uo pipefail

CACHE="/mnt/c/Users/22153/AppData/Local/hermes/cache/scratch/pkgcache/v3.12.8.tar.gz"
[ -s "$CACHE" ] || { echo "!! 源码包不在: $CACHE"; exit 1; }
echo "源码包: $(du -h "$CACHE" | cut -f1)"

echo "=== 1. 改 recipe 版本 ==="
for r in python3 hostpython3; do
  F="/root/p4a_src/pythonforandroid/recipes/$r/__init__.py"
  [ -f "$F" ] || { echo "  跳过 $r（没有 recipe）"; continue; }
  cp -f "$F" "$F.bak312"
  sed -i "s/version = '3\.14\.2'/version = '3.12.8'/g; s/version = \"3\.14\.2\"/version = \"3.12.8\"/g" "$F"
  grab=$(grep -nE "^\s*version\s*=" "$F" | head -1)
  echo "  $r -> $grab"
  grep -nE "^\s*url\s*=" "$F" | head -1
done

echo "=== 2. 放进 p4a 缓存并打 .mark ==="
for r in python3 hostpython3; do
  D="/root/.local/share/python-for-android/packages/$r"
  mkdir -p "$D"
  cp -f "$CACHE" "$D/v3.12.8.tar.gz"
  touch "$D/.mark-v3.12.8.tar.gz"
  rm -f "$D/v3.14.2.tar.gz" "$D/.mark-v3.14.2.tar.gz" 2>/dev/null || true
  ls -lh "$D" | tail -3
done

echo "=== 3. 清掉 3.14 的编译产物（保留 SDL2/openssl/libffi/sqlite3）==="
B="/root/.local/share/python-for-android/build"
rm -rf "$B/other_builds/hostpython3" \
       "$B/other_builds/python3"* \
       "$B/other_builds/kivy-sdl2" \
       "$B/other_builds/pyjnius-sdl2" \
       "$B/python-installs" \
       /root/.local/share/python-for-android/dists
echo "剩余 other_builds："
ls "$B/other_builds" 2>/dev/null | tr '\n' ' '; echo

echo "=== 4. 重跑构建 ==="
export PIP_INDEX_URL="https://mirrors.aliyun.com/pypi/simple/"
export PIP_TRUSTED_HOST="mirrors.aliyun.com"
export PIP_BREAK_SYSTEM_PACKAGES=1
export PIP_NO_BUILD_ISOLATION=1
pkill -9 -f "p4a apk" 2>/dev/null || true
sleep 1
exec bash "/mnt/d/项目/AI多模态控制台/android/build_p4a.sh"
