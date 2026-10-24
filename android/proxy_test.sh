#!/bin/bash
# 测 Windows 主机上的代理能否从 WSL 访问；能用就大幅加速 Python 源码/GitHub 下载
pkill -9 -f "p4a apk" 2>/dev/null || true
sleep 1

HOST_IP=$(ip route | grep default | awk '{print $3}')
echo "Windows 主机 IP: ${HOST_IP:-未取到}"

for port in 7890 7897 10809 1080; do
  echo "--- 端口 $port"
  timeout 12 curl -sI -x "http://${HOST_IP}:${port}" \
    https://www.python.org/ftp/python/3.14.2/Python-3.14.2.tgz 2>&1 | head -2
done

echo "--- 直连对比"
timeout 12 curl -sI https://www.python.org/ftp/python/3.14.2/Python-3.14.2.tgz 2>&1 | head -2
