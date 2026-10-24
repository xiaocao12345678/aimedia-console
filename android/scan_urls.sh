#!/bin/bash
# 列出 p4a 各 recipe 需要从网上抓的包（pypi 之外），用于手工预下载
pkill -9 -f "p4a apk" 2>/dev/null || true

python3 - <<'PY'
import glob, re, os
rows = []
for f in sorted(glob.glob('/root/p4a_src/pythonforandroid/recipes/*/__init__.py')):
    recipe = os.path.basename(os.path.dirname(f))
    txt = open(f, encoding='utf-8', errors='ignore').read()
    for m in re.finditer(r'https?://[^\s"\')]+', txt):
        u = m.group(0).rstrip('.,')
        if 'pythonhosted' in u or 'pypi' in u or 'schemas' in u:
            continue
        rows.append((recipe, u))

seen = set()
for r, u in rows:
    if (r, u) in seen:
        continue
    seen.add((r, u))
    print(f"{r:22s} {u}")

print()
print("=== 已缓存 ===")
base = '/root/.local/share/python-for-android/packages'
if os.path.isdir(base):
    for d in sorted(os.listdir(base)):
        p = os.path.join(base, d)
        if os.path.isdir(p):
            files = os.listdir(p)
            print(f"{d:22s} {files if files else '(空)'}")
PY
