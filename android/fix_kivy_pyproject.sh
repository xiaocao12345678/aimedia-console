#!/bin/bash
# kivy 2.3.1 的 sdist 没有 pyproject.toml，pip 建隔离环境时不知道要装 Cython。
# 往包里补一个 build-system 声明，重打包，并清掉旧的解压目录让 p4a 重新解。
set -uo pipefail

PKG="/root/.local/share/python-for-android/packages/kivy"
ZIP="$PKG/2.3.1.zip"
BUILD="/root/.local/share/python-for-android/build/other_builds/kivy-sdl2"

[ -f "$ZIP" ] || { echo "!! 没有 $ZIP"; exit 1; }

echo "=== 1. 解开 kivy 源码包 ==="
rm -rf /tmp/kivyfix && mkdir -p /tmp/kivyfix
cd /tmp/kivyfix
unzip -q "$ZIP"
TOP=$(ls -d */ | head -1)
TOP=${TOP%/}
echo "顶层目录：$TOP"
ls "$TOP" | head -5

echo "=== 2. 补 pyproject.toml ==="
cat > "$TOP/pyproject.toml" <<'EOF'
[build-system]
requires = ["setuptools>=61", "wheel", "cython>=0.29.34,<4"]
build-backend = "setuptools.build_meta"
EOF
cat "$TOP/pyproject.toml"

echo "=== 3. 重新打包 ==="
rm -f "$ZIP"
zip -qr "$ZIP" "$TOP"
touch "$PKG/.mark-2.3.1.zip"
ls -lh "$ZIP"

echo "=== 4. 清掉旧的解压目录，强制重新解包 ==="
rm -rf "$BUILD"
ls -d "$BUILD" 2>/dev/null || echo "已清"

echo "=== 5. 重跑构建 ==="
export PIP_INDEX_URL="https://mirrors.aliyun.com/pypi/simple/"
export PIP_TRUSTED_HOST="mirrors.aliyun.com"
export PIP_BREAK_SYSTEM_PACKAGES=1
pkill -9 -f "p4a apk" 2>/dev/null || true
sleep 1
exec bash "/mnt/d/项目/AI多模态控制台/android/build_p4a.sh"
