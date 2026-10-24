#!/bin/bash
# 生成「recipe → 官方下载地址 → 文件名 → 目标目录」清单，供 Windows 侧用代理下载
set -uo pipefail
OUT="/mnt/d/项目/AI多模态控制台/android/pkglist.txt"

python3 - "$OUT" <<'PY'
import os, re, sys, urllib.parse

RECIPES = "/root/p4a_src/pythonforandroid/recipes"
PKG = "/root/.local/share/python-for-android/packages"
ORDER = ["hostpython3", "libffi", "openssl", "sdl2_image", "sdl2_mixer",
         "sdl2_ttf", "sqlite3", "python3", "sdl2", "pyjnius", "kivy", "setuptools"]

out = []
for name in ORDER:
    p = os.path.join(RECIPES, name, "__init__.py")
    if not os.path.isfile(p):
        continue
    txt = open(p, encoding="utf-8", errors="ignore").read()
    ver = None
    for pat in (r"^\s*version\s*=\s*['\"]([^'\"]+)['\"]",
                r"^\s*version\s*=\s*\(\s*['\"]([^'\"]+)['\"]"):
        m = re.search(pat, txt, re.M)
        if m:
            ver = m.group(1)
            break
    m = re.search(r"^\s*url\s*=\s*['\"]([^'\"]+)['\"]", txt, re.M)
    if not m or not ver:
        continue
    url = m.group(1).replace("{version}", ver)
    fname = urllib.parse.urlparse(url).path.split("/")[-1]
    out.append(f"{name}\t{url}\t{fname}")

with open(sys.argv[1], "w", encoding="utf-8") as f:
    f.write("\n".join(out) + "\n")
print(f"写出 {len(out)} 条到 {sys.argv[1]}")
for line in out:
    print("  ", line)
PY
