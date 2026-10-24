#!/bin/bash
# 从 Noto Sans CJK TTC 里抽出简体中文（SC）那一款，存成单个 OTF
set -uo pipefail

TTC="/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
OUT="/mnt/d/项目/AI多模态控制台/android/assets/NotoSansCJKsc-Regular.otf"

python3 -m pip install --break-system-packages -q fonttools 2>&1 | tail -2

python3 - "$TTC" "$OUT" <<'PY'
import sys
from fontTools.ttLib import TTCollection

ttc, out = sys.argv[1], sys.argv[2]
coll = TTCollection(ttc)
print("TTC 里有", len(coll.fonts), "个字体：")
target = None
for i, f in enumerate(coll.fonts):
    name = f["name"].getDebugName(4) or "?"
    print(f"  [{i}] {name}")
    if "SC" in name and target is None:
        target = (i, f)
assert target, "没找到 SC 那一款"
idx, font = target
font.save(out)
print(f"已提取 [{idx}] {font['name'].getDebugName(4)} -> {out}")
PY

ls -la "$OUT"
