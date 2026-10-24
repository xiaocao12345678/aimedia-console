"""生成 Android 图标：512×512，蓝底圆角 + 白色 AI 字标。"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).resolve().parent
OUT = BASE / "assets"
OUT.mkdir(exist_ok=True)

SIZE = 512
img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# 背景：竖向渐变（深蓝 → 亮蓝），圆角半径 96
top = (31, 111, 235)
bottom = (14, 78, 186)
grad = Image.new("RGB", (1, SIZE))
for y in range(SIZE):
    t = y / (SIZE - 1)
    grad.putpixel((0, y), tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
grad = grad.resize((SIZE, SIZE))
mask = Image.new("L", (SIZE, SIZE), 0)
ImageDraw.Draw(mask).rounded_rectangle([0, 0, SIZE - 1, SIZE - 1], radius=96, fill=255)
img.paste(grad, (0, 0), mask)

# 文字 AI
font = None
for cand in [
    BASE / "assets" / "NotoSansSC.otf",
    Path("C:/Windows/Fonts/arialbd.ttf"),
    Path("C:/Windows/Fonts/msyhbd.ttc"),
]:
    if cand.exists():
        try:
            font = ImageFont.truetype(str(cand), 210)
            break
        except Exception:
            continue

d = ImageDraw.Draw(img)
text = "AI"
if font:
    box = d.textbbox((0, 0), text, font=font)
    w, h = box[2] - box[0], box[3] - box[1]
    d.text(((SIZE - w) / 2 - box[0], (SIZE - h) / 2 - box[1] - 10), text, font=font, fill=(255, 255, 255, 255))
else:
    d.rectangle([160, 200, 350, 330], fill=(255, 255, 255, 255))

# 下方两条细线（暗示"多模态"：文字 / 图像 / 视频）
d.rounded_rectangle([150, 372, 362, 384], radius=6, fill=(255, 255, 255, 210))
d.rounded_rectangle([196, 400, 316, 410], radius=5, fill=(255, 255, 255, 140))

path = OUT / "icon.png"
img.save(path)
print("saved", path, path.stat().st_size, "bytes", img.size)
