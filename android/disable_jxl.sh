#!/bin/bash
# SDL2_image 默认要 clone libjxl + libavif（它们还各自带子模块），GitHub 直连必断。
# kivy 只用 PNG/JPG，所以从 .gitmodules 删掉这两项、在 Android.mk 里关掉对应开关。
set -uo pipefail

D="/root/.local/share/python-for-android/build/bootstrap_builds/sdl2/jni/SDL2_image"
[ -d "$D" ] || { echo "!! SDL2_image 目录不在: $D"; exit 1; }

cp "$D/.gitmodules" "$D/.gitmodules.bak" 2>/dev/null || true
cp "$D/Android.mk" "$D/Android.mk.bak" 2>/dev/null || true

echo "=== 1. .gitmodules 摘掉 libjxl / libavif ==="
python3 - "$D/.gitmodules" <<'PY'
import re, sys
p = sys.argv[1]
txt = open(p, encoding="utf-8").read()
for name in ("libjxl", "libavif"):
    txt = re.sub(r'\[submodule "external/%s"\][^\[]*' % name, "", txt)
open(p, "w", encoding="utf-8").write(txt)
print("剩余子模块：")
print("".join(l for l in txt.splitlines(True) if l.startswith("[submodule")))
PY

echo "=== 2. Android.mk 关掉 JXL / AVIF ==="
sed -i 's/ifeq (\$(SUPPORT_JXL),true)/ifeq ($(SUPPORT_JXL),false)/' "$D/Android.mk"
sed -i 's/ifeq (\$(SUPPORT_AVIF),true)/ifeq ($(SUPPORT_AVIF),false)/' "$D/Android.mk"
sed -i '/src\/IMG_jxl\.c/d' "$D/Android.mk"
sed -i '/src\/IMG_avif\.c/d' "$D/Android.mk"
grep -n "SUPPORT_JXL\|SUPPORT_AVIF\|IMG_jxl\|IMG_avif" "$D/Android.mk" | head -6

echo "=== 3. 清掉半截的空目录 ==="
rm -rf "$D/external/libjxl" "$D/external/libavif"
ls "$D/external"

echo "=== 4. 重跑构建 ==="
pkill -9 -f "p4a apk" 2>/dev/null || true
pkill -9 -f "git clone" 2>/dev/null || true
sleep 1
export PIP_BREAK_SYSTEM_PACKAGES=1
exec bash "/mnt/d/项目/AI多模态控制台/android/build_p4a.sh"
