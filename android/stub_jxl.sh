#!/bin/bash
# IMG.c 里 supported() 无条件引用 IMG_isJXL / IMG_LoadJXL_RW / IMG_isAVIF / IMG_LoadAVIF_RW。
# 关掉 jxl/avif 后这些符号缺失，链接失败。补一份桩实现：识别为"不认识"，加载返回 NULL。
set -uo pipefail

D="/root/.local/share/python-for-android/build/bootstrap_builds/sdl2/jni/SDL2_image"
[ -d "$D" ] || { echo "!! 目录不在"; exit 1; }

echo "=== 原始函数签名（从 IMG_jxl.c 取）==="
grep -nE "^(int|SDL_Surface|static).*(IMG_isJXL|IMG_LoadJXL_RW)" "$D/src/IMG_jxl.c" 2>/dev/null | head -4
grep -nE "^(int|SDL_Surface).*(IMG_isAVIF|IMG_LoadAVIF_RW)" "$D/src/IMG_avif.c" 2>/dev/null | head -4

cat > "$D/stub_optional_formats.c" <<'EOF'
/* 由构建脚本生成：JXL / AVIF 支持被关闭，这里提供空实现让 IMG.c 链接得过。 */
#include "SDL_image.h"

int IMG_isJXL(SDL_RWops *src)
{
    (void)src;
    return 0;
}

SDL_Surface *IMG_LoadJXL_RW(SDL_RWops *src)
{
    (void)src;
    return NULL;
}

int IMG_isAVIF(SDL_RWops *src)
{
    (void)src;
    return 0;
}

SDL_Surface *IMG_LoadAVIF_RW(SDL_RWops *src)
{
    (void)src;
    return NULL;
}
EOF

if grep -q "stub_optional_formats.c" "$D/Android.mk"; then
  echo "桩文件已加入 Android.mk"
else
  sed -i '/^LOCAL_SRC_FILES/a\    stub_optional_formats.c \\' "$D/Android.mk"
  echo "已把桩文件加进 LOCAL_SRC_FILES："
  grep -n -A2 "^LOCAL_SRC_FILES" "$D/Android.mk" | head -5
fi

echo "=== 重跑构建 ==="
pkill -9 -f "p4a apk" 2>/dev/null || true
sleep 1
export PIP_BREAK_SYSTEM_PACKAGES=1
exec bash "/mnt/d/项目/AI多模态控制台/android/build_p4a.sh"
