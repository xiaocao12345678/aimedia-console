#!/bin/bash
# 绕过 buildozer（它的 ANT / pip / git 前置检查在 WSL 里处处卡），
# 直接用 python-for-android 的 p4a 命令行打包。
set -uo pipefail

export PIP_BREAK_SYSTEM_PACKAGES=1
export ANDROIDSDK="/root/android_sdk"
export ANDROIDNDK="/root/android_ndk"

# Android NDK 没有 getgrent/setgrent/getpwent 这类函数，
# 但 Python 的 configure 会误判它们存在，导致 grpmodule.c / pwdmodule.c 编译失败。
# 用 autoconf 缓存变量直接告诉它"没有"。
export ac_cv_func_setgrent=no
export ac_cv_func_getgrent=no
export ac_cv_func_endgrent=no
export ac_cv_func_setpwent=no
export ac_cv_func_getpwent=no
export ac_cv_func_endpwent=no
export ac_cv_func_getpwnam=no
export ac_cv_func_getpwuid=no
export ac_cv_func_getgrgid=no
export ac_cv_func_getgrnam=no
export PATH="$PATH:/root/.local/bin"
mkdir -p "$ANDROIDSDK" "$ANDROIDNDK"

echo "=== 1. 安装 p4a（本地源码，可编辑模式）==="
cd /root/p4a_src
python3 -m pip install -q -e . 2>&1 | tail -3
command -v p4a && p4a --version 2>&1 | head -2

echo "=== 2. 准备 app 目录 ==="
APP=/root/p4a_app
rm -rf "$APP"; mkdir -p "$APP"
rsync -a --exclude 'bin' --exclude '.buildozer' --exclude '__pycache__' \
      --exclude 'logs' --exclude '*.pyc' --exclude 'buildozer.spec' \
      --exclude '*.sh' /root/build_apk/ "$APP/"
du -sh "$APP"; ls "$APP" | head -8

echo "=== 3. 开始打包（会下载 Android SDK / NDK，数十 GB 内网流量，慢）==="
cd /root
p4a apk \
  --private "$APP" \
  --package org.aimedia.aimedia \
  --name "AI多模态控制台" \
  --version 1.0.0 \
  --requirements "python3,kivy==2.3.1,requests,pyjnius" \
  --android-api 34 \
  --min-api 24 \
  --arch arm64-v8a \
  --sdk-dir "$ANDROIDSDK" \
  --ndk-dir "$ANDROIDNDK" \
  --permission INTERNET \
  --permission MANAGE_EXTERNAL_STORAGE \
  --permission READ_EXTERNAL_STORAGE \
  --permission WRITE_EXTERNAL_STORAGE \
  --permission READ_MEDIA_IMAGES \
  --permission READ_MEDIA_VIDEO \
  --debug 2>&1 | tail -60

echo "=== 4. 产物 ==="
ls -la /root/*.apk 2>/dev/null || echo "!!! 没有 APK"
