#!/bin/bash
pkill -9 -f preload_all 2>/dev/null || true

t() {
  local s
  s=$(timeout 12 curl -sL --max-time 11 -o /dev/null -w "%{speed_download}" "$1" 2>/dev/null || echo 0)
  printf "%6s KB/s  %s\n" "$(( ${s%.*} / 1024 ))" "$1"
}

t "https://mirrors.tuna.tsinghua.edu.cn/openssl/source/openssl-3.3.1.tar.gz"
t "https://www.openssl.org/source/openssl-3.3.1.tar.gz"
t "https://www.libsdl.org/release/SDL2-2.30.11.tar.gz"
t "https://gitee.com/mirrors/kivy/repository/archive/2.3.1.zip"
t "https://gitee.com/mirrors/libffi/repository/archive/v3.4.2.tar.gz"
