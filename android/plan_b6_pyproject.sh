#!/bin/bash
# Python 3.12 已编过（桩生效）。现在卡在 kivy/pyjnius 的 sdist 没声明 Cython 依赖，
# pip 的隔离环境只装 setuptools，导致 "No module named 'Cython'"。
# 3.12 下有现成 wheel，给两个 sdist 补 pyproject.toml 即可让 pip 自动装。
set -uo pipefail

PKG="/root/.local/share/python-for-android/packages"

fix_zip() {
  local zip="$1"
  local zip="$1"
  [ -f "$zip" ] || { echo "  跳过（不存在）: $zip"; return; }
  local work="/tmp/zzfix_$(basename "$zip" .zip)_$$"
  rm -rf "$work"; mkdir -p "$work"
  unzip -q "$zip" -d "$work"
  local top
  top=$(ls -d "$work"/*/ 2>/dev/null | head -1)
  [ -n "${top:-}" ] || { echo "  解压后没有顶层目录: $zip"; rm -rf "$work"; return; }
  if [ -f "$top/pyproject.toml" ]; then
    echo "  已有 pyproject.toml: $(basename "$zip")"
  else
    cat > "$top/pyproject.toml" <<'EOF'
[build-system]
requires = ["setuptools>=61", "wheel", "cython>=0.29.34,<4"]
build-backend = "setuptools.build_meta"
EOF
    echo "  已补 pyproject.toml: $(basename "$zip")"
  fi
  rm -f "$zip"
  (cd "$work" && zip -qr "$zip" ./*)
  touch "$(dirname "$zip")/.mark-$(basename "$zip")"
  ls -lh "$zip"
  rm -rf "$work"
}

echo "=== 1. kivy ==="
fix_zip "$PKG/kivy/2.3.1.zip"

echo "=== 2. pyjnius ==="
fix_zip "$PKG/pyjnius/1.7.0.zip"

echo "=== 3. 清掉这两个 recipe 的旧解压目录 ==="
rm -rf /root/.local/share/python-for-android/build/other_builds/kivy-sdl2 \
       /root/.local/share/python-for-android/build/other_builds/pyjnius-sdl2

echo "=== 4. 重跑 ==="
export PIP_INDEX_URL="https://mirrors.aliyun.com/pypi/simple/"
export PIP_TRUSTED_HOST="mirrors.aliyun.com"
export PIP_BREAK_SYSTEM_PACKAGES=1
pkill -9 -f "p4a apk" 2>/dev/null || true
sleep 1
exec bash "/mnt/d/项目/AI多模态控制台/android/build_p4a.sh"
