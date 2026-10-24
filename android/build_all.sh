#!/bin/bash
# 清掉坏掉的 git 镜像配置，多源 clone python-for-android，然后跑构建
set -uo pipefail

git config --global --unset-all 'url.https://ghproxy.net/https://github.com/.insteadOf' 2>/dev/null || true

P4A_DIR="/root/build_apk/.buildozer/android/platform/python-for-android"

if [ -f "$P4A_DIR/setup.py" ]; then
  echo "p4a 已存在，跳过 clone：$(du -sh "$P4A_DIR" | cut -f1)"
else
  mkdir -p "$(dirname "$P4A_DIR")"
  for m in \
    "https://gh.llkk.cc/https://github.com/kivy/python-for-android.git" \
    "https://github.moeyy.xyz/https://github.com/kivy/python-for-android.git" \
    "https://hub.gitmirror.com/https://github.com/kivy/python-for-android.git" \
    "https://ghproxy.net/https://github.com/kivy/python-for-android.git" \
    "https://gitclone.com/github.com/kivy/python-for-android.git" ; do
    echo "=== 尝试 $m"
    rm -rf "$P4A_DIR"
    if timeout 300 git clone --depth 1 -b master "$m" "$P4A_DIR" >/tmp/clone.log 2>&1 && [ -f "$P4A_DIR/setup.py" ]; then
      echo "CLONE_OK $m  $(du -sh "$P4A_DIR" | cut -f1)"
      break
    fi
    tail -2 /tmp/clone.log
  done
fi

if [ ! -f "$P4A_DIR/setup.py" ]; then
  echo "!!! p4a clone 全部失败"
  exit 1
fi

exec bash "/mnt/d/项目/AI多模态控制台/android/build_apk.sh"
