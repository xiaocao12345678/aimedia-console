#!/bin/bash
# kivy wheel 的 build isolation 环境里要装 Cython，默认走 pypi.org 会失败/超时。
# 把 pip 全局指向阿里云镜像，让那个临时环境也能秒装 Cython。
set -uo pipefail

export PIP_INDEX_URL="https://mirrors.aliyun.com/pypi/simple/"
export PIP_TRUSTED_HOST="mirrors.aliyun.com"
export PIP_BREAK_SYSTEM_PACKAGES=1
# 注意：这里故意不设 PIP_NO_BUILD_ISOLATION，
# 让 pip 建隔离环境、并从阿里云装 Cython，而不是去翻 host 环境。
unset PIP_NO_BUILD_ISOLATION 2>/dev/null || true

echo "=== pip 源：$PIP_INDEX_URL"
python3 -m pip config set global.index-url "$PIP_INDEX_URL" 2>/dev/null || true
python3 -m pip config set global.trusted-host "$PIP_TRUSTED_HOST" 2>/dev/null || true

echo "=== 重跑构建 ==="
pkill -9 -f "p4a apk" 2>/dev/null || true
sleep 1
exec bash "/mnt/d/项目/AI多模态控制台/android/build_p4a.sh"
