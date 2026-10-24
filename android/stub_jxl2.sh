#!/bin/bash
# 补齐 IMG.c 需要的全部 8 个 JXL/AVIF 符号后重新链接
set -uo pipefail

D="/root/.local/share/python-for-android/build/bootstrap_builds/sdl2/jni/SDL2_image"
[ -d "$D" ] || { echo "!! 目录不在"; exit 1; }

cat > "$D/stub_optional_formats.c" <<'EOF'
/* 由构建脚本生成：JXL / AVIF 支持被关闭，提供空实现让 IMG.c 链接得过。
   识别函数一律返回 0（不认识），加载函数返回 NULL，Init/Quit 空转。 */
#include "SDL_image.h"

int IMG_InitJXL(void)
{
    return 0;
}

void IMG_QuitJXL(void)
{
}

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

int IMG_InitAVIF(void)
{
    return 0;
}

void IMG_QuitAVIF(void)
{
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

echo "桩文件函数清单："
grep -E "^(int|void|SDL_Surface)" "$D/stub_optional_formats.c"

echo "=== 重跑构建 ==="
pkill -9 -f "p4a apk" 2>/dev/null || true
sleep 1
export PIP_BREAK_SYSTEM_PACKAGES=1
exec bash "/mnt/d/项目/AI多模态控制台/android/build_p4a.sh"
