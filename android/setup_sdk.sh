#!/bin/bash
# 装 Android SDK（commandline-tools + platform 34 + build-tools）+ NDK r25b，
# 然后重跑 p4a 打包。国内优先腾讯云镜像，失败回退 dl.google.com。
set -uo pipefail

SDK="/root/android_sdk"
NDK="/root/android_ndk"
mkdir -p "$SDK" "$NDK"
cd /tmp

get() {  # get <镜像URL> <官方URL> <输出文件>
  for u in "$1" "$2"; do
    echo "   尝试 $u"
    if timeout 600 curl -fL --retry 2 -o "$3" "$u" && [ -s "$3" ]; then
      echo "   成功 $(du -h "$3" | cut -f1)"
      return 0
    fi
  done
  echo "   !!! 下载失败"
  return 1
}

echo "=== 1. commandline-tools ==="
if [ -x "$SDK/cmdline-tools/latest/bin/sdkmanager" ]; then
  echo "已存在，跳过"
else
  get "https://mirrors.cloud.tencent.com/AndroidSDK/commandlinetools-linux-11076708_latest.zip" \
      "https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip" \
      clt.zip || exit 1
  rm -rf "$SDK/cmdline-tools"; mkdir -p "$SDK/cmdline-tools"
  unzip -q clt.zip -d "$SDK/cmdline-tools"
  mv "$SDK/cmdline-tools/cmdline-tools" "$SDK/cmdline-tools/latest"
  chmod +x "$SDK/cmdline-tools/latest/bin/"*
fi
export ANDROID_SDK_ROOT="$SDK"
export ANDROID_HOME="$SDK"
SDKM="$SDK/cmdline-tools/latest/bin/sdkmanager"

echo "=== 2. platform 34 / build-tools / platform-tools ==="
yes | "$SDKM" --licenses >/dev/null 2>&1 || true
"$SDKM" "platform-tools" "platforms;android-34" "build-tools;34.0.0" 2>&1 | tail -5
ls "$SDK/platforms" "$SDK/build-tools" 2>/dev/null

echo "=== 3. NDK r25b（约 1.2 GB）==="
if [ -f "$NDK/source.properties" ]; then
  echo "NDK 已存在，跳过"
else
  get "https://mirrors.cloud.tencent.com/AndroidSDK/android-ndk-r25b-linux.zip" \
      "https://dl.google.com/android/repository/android-ndk-r25b-linux.zip" \
      ndk.zip || exit 1
  rm -rf "$NDK"; mkdir -p "$NDK"
  unzip -q ndk.zip -d /tmp/ndkx
  mv /tmp/ndkx/android-ndk-r25b/* "$NDK"/ 2>/dev/null || true
  rm -rf /tmp/ndkx ndk.zip
fi
cat "$NDK/source.properties" 2>/dev/null | head -3

echo "=== 4. 重跑打包 ==="
exec bash "/mnt/d/项目/AI多模态控制台/android/build_p4a.sh"
