#!/bin/bash
# 独立跑一次完整构建（所有补丁已就位）：
#   Python 3.12 + grp/pwd 桩函数 + 三处 --no-build-isolation + hostpython 有 cython
set -uo pipefail

export PIP_INDEX_URL="https://mirrors.aliyun.com/pypi/simple/"
export PIP_TRUSTED_HOST="mirrors.aliyun.com"
export PIP_BREAK_SYSTEM_PACKAGES=1
export PIP_NO_BUILD_ISOLATION=1
export ANDROIDSDK="/root/android_sdk"
export ANDROIDNDK="/root/android_ndk"
export PATH="$PATH:/root/.local/bin"

echo "===== 开始 $(date) ====="
echo "--- 关键补丁确认 ---"
grep -c "no-build-isolation" /root/p4a_src/pythonforandroid/build.py 2>/dev/null | xargs echo "build.py no-build-isolation 处数:"
grep -c "no-build-isolation" /root/p4a_src/pythonforandroid/pythonpackage.py 2>/dev/null | xargs echo "pythonpackage.py 处数:"
grep -c "_ai_media_stub_patched" /root/p4a_src/pythonforandroid/recipes/python3/__init__.py 2>/dev/null | xargs echo "grp/pwd 桩补丁:"
grep -E "^\s*version\s*=" /root/p4a_src/pythonforandroid/recipes/python3/__init__.py | head -1

pkill -9 -f "p4a apk" 2>/dev/null || true
sleep 1

cd /root/build_apk 2>/dev/null || cd /root/p4a_app
APP=/root/p4a_app
rm -rf "$APP"; mkdir -p "$APP"
rsync -a --exclude 'bin' --exclude '.buildozer' --exclude '__pycache__' \
      --exclude 'logs' --exclude '*.pyc' --exclude 'buildozer.spec' --exclude '*.sh' \
      /root/build_apk/ "$APP/"

echo "--- app 目录 ---"
du -sh "$APP"

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
  --debug 2>&1

echo "===== p4a 退出码 $?  $(date) ====="
ls -lah /root/*.apk 2>/dev/null || echo "没有 APK"
