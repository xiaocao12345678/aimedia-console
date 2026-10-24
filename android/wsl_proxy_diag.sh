#!/bin/bash
# 诊断 WSL 到 Windows 代理的连通性
echo "=== WSL 网络模式 ==="
cat /mnt/c/Users/22153/.wslconfig 2>/dev/null || echo "（没有 .wslconfig，即默认 NAT 模式）"
echo
echo "=== 本机 IP ==="
ip -4 addr show | grep inet | grep -v 127.0.0.1
echo
echo "=== 网关 ==="
ip route | grep default

GW=$(ip route | grep default | awk '{print $3}')
echo
echo "=== 测试 127.0.0.1（mirrored 模式下可用）==="
for p in 7890 7891 7897 1080 10808 20172; do
  r=$(timeout 5 curl -s -o /dev/null -w "%{http_code}" -x "http://127.0.0.1:$p" https://www.google.com 2>/dev/null)
  echo "  127.0.0.1:$p -> ${r:-无响应}"
done

echo
echo "=== 测试网关 $GW（NAT 模式下要加 Allow LAN）==="
for p in 7890 7891 7897 1080 10808 20172; do
  r=$(timeout 5 curl -s -o /dev/null -w "%{http_code}" -x "http://$GW:$p" https://www.google.com 2>/dev/null)
  echo "  $GW:$p -> ${r:-无响应}"
done

echo
echo "=== Windows 侧监听端口（从 WSL 看不了，仅供参考：netsh 需在 Windows 执行）==="
