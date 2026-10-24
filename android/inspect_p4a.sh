#!/bin/bash
# 看 p4a 到底用什么下载（决定怎么给它加镜像）
echo "=== recipe.py 下载相关 ==="
grep -nE "urlretrieve|urlopen|requests\.|wget|download_file|sh\.curl" /root/p4a_src/pythonforandroid/recipe.py | head -12
echo
echo "=== 用到的 recipe 版本 ==="
for r in python3 sdl2 libffi openssl kivy pyjnius; do
  f=/root/p4a_src/pythonforandroid/recipes/$r/__init__.py
  [ -f "$f" ] || continue
  echo "--- $r"
  grep -nE "^\s*version|^version|url = |depends = " "$f" | head -4
done
