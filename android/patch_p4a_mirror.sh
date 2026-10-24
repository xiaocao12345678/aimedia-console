#!/bin/bash
# p4a 所有 recipe 都从 github.com 抓（cpython/sdl2/libffi/kivy/pyjnius），国内直连会被墙。
# 在 recipe.py 里把 urlretrieve 换掉，遇到 github.com 自动走 ghproxy.net 镜像。
set -uo pipefail

RECIPE="/root/p4a_src/pythonforandroid/recipe.py"
pkill -9 -f "p4a apk" 2>/dev/null || true
sleep 1

if grep -q "_mirror_urlretrieve" "$RECIPE"; then
  echo "补丁已存在，跳过"
else
  cp "$RECIPE" "$RECIPE.bak"
  python3 - "$RECIPE" <<'PY'
import sys
p = sys.argv[1]
src = open(p, encoding='utf-8').read()
anchor = "from urllib.request import urlretrieve"
patch = anchor + """

# ---- 本地补丁：GitHub 直连被墙，统一走镜像（ghproxy.net）----
_mirror_urlretrieve = urlretrieve
_MIRRORS = ("https://ghproxy.net/", "https://ghfast.top/")


def urlretrieve(url, *args, **kwargs):  # noqa: F811
    if isinstance(url, str) and "github.com" in url and "ghproxy" not in url:
        for base in _MIRRORS:
            try:
                return _mirror_urlretrieve(base + url, *args, **kwargs)
            except Exception as exc:  # 镜像失败就试下一个
                print(f"[mirror] {base} 失败：{exc}")
                continue
    return _mirror_urlretrieve(url, *args, **kwargs)
"""
assert anchor in src, "找不到锚点"
src = src.replace(anchor, patch, 1)
open(p, "w", encoding='utf-8').write(src)
print("补丁写入成功")
PY
fi

grep -n "_mirror_urlretrieve" "$RECIPE" | head -3

echo "=== 继续构建 ==="
export PIP_BREAK_SYSTEM_PACKAGES=1
exec bash "/mnt/d/项目/AI多模态控制台/android/build_p4a.sh"
