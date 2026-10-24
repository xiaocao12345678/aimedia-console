#!/bin/bash
pkill -9 -f gradle 2>/dev/null || true
pkill -9 -f "p4a apk" 2>/dev/null || true

t() {
  local s
  s=$(timeout 12 curl -sL --max-time 11 -o /dev/null -w "%{speed_download}" "$1" 2>/dev/null || echo 0)
  printf "%7s KB/s  %s\n" "$(( ${s%.*} / 1024 ))" "$1"
}

echo "=== gradle 发行版镜像测速（约 230 MB）==="
t "https://mirrors.cloud.tencent.com/gradle/gradle-8.14.3-all.zip"
t "https://mirrors.huaweicloud.com/gradle/gradle-8.14.3-all.zip"
t "https://mirrors.aliyun.com/gradle/gradle-8.14.3-all.zip"
t "https://services.gradle.org/distributions/gradle-8.14.3-all.zip"
