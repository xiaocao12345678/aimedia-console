#!/bin/bash
# 把 Windows 下好的 gradle 发行版塞进 gradle wrapper 缓存（自己算 hash，避开 services.gradle.org）
set -uo pipefail

ZIP="/mnt/c/Users/22153/AppData/Local/hermes/cache/scratch/gradle-8.14.3-all.zip"
URL="https://services.gradle.org/distributions/gradle-8.14.3-all.zip"
VER="gradle-8.14.3-all"

if [ ! -s "$ZIP" ]; then
  echo "!!! 没找到 $ZIP"
  exit 1
fi
echo "zip: $(du -h "$ZIP" | cut -f1)"

HASH=$(python3 - "$URL" <<'PY'
import hashlib, sys
url = sys.argv[1]
n = int.from_bytes(hashlib.md5(url.encode()).digest(), "big")
digits = "0123456789abcdefghijklmnopqrstuvwxyz"
s = ""
while n:
    n, r = divmod(n, 36)
    s = digits[r] + s
print(s or "0")
PY
)
echo "wrapper hash: $HASH"

DEST="/root/.gradle/wrapper/dists/$VER/$HASH"
rm -rf "$DEST"; mkdir -p "$DEST"
cd "$DEST"
echo "解压到 $DEST"
unzip -q "$ZIP" -d "$DEST"
ls -d gradle-8.14.3 2>/dev/null && echo "✅ gradle 解压 OK"
# 标记文件（gradle 用来判断已完成）
cp "$ZIP" "$DEST/$VER.zip" 2>/dev/null || true
touch "$DEST/$VER.zip.ok"
chmod +x gradle-8.14.3/bin/gradle 2>/dev/null || true
du -sh "$DEST"
"$DEST/gradle-8.14.3/bin/gradle" --version 2>&1 | head -6

echo "=== 重跑构建 ==="
export PIP_BREAK_SYSTEM_PACKAGES=1
exec bash "/mnt/d/项目/AI多模态控制台/android/build_p4a.sh"
