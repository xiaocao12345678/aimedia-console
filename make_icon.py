"""生成应用图标 assets/app.ico（多尺寸）。"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).resolve().parent
OUT = BASE / "assets" / "app.ico"
S = 512

img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
# 渐变底：从浅蓝到深蓝
for y in range(S):
    t = y / S
    r = int(96 + (26 - 96) * t)
    g = int(162 + (100 - 162) * t)
    b = int(255 + (218 - 255) * t)
    d.line([(0, y), (S, y)], fill=(r, g, b, 255))
# 圆角遮罩
mask = Image.new("L", (S, S), 0)
ImageDraw.Draw(mask).rounded_rectangle([0, 0, S, S], radius=112, fill=255)
img.putalpha(mask)

# 顶部高光：自上而下渐隐，避免中间出现硬边
overlay = Image.new("RGBA", (S, S), (0, 0, 0, 0))
od = ImageDraw.Draw(overlay)
for y in range(S // 2):
    a = int(46 * (1 - y / (S / 2)) ** 1.6)
    if a > 0:
        od.line([(0, y), (S, y)], fill=(255, 255, 255, a))
overlay.putalpha(Image.composite(overlay.split()[3], Image.new("L", (S, S), 0), mask))
img = Image.alpha_composite(img, overlay)

font = None
for f in ("msyhbd.ttc", "msyh.ttc", "segoeuib.ttf", "arialbd.ttf"):
    try:
        font = ImageFont.truetype(f"C:/Windows/Fonts/{f}", 240)
        break
    except Exception:
        continue
d = ImageDraw.Draw(img)
text = "AI"
if font:
    box = d.textbbox((0, 0), text, font=font)
    w, h = box[2] - box[0], box[3] - box[1]
    d.text(((S - w) / 2 - box[0], (S - h) / 2 - box[1] - 8), text, font=font,
           fill=(255, 255, 255, 245))

img.save(OUT, sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
print("wrote", OUT, OUT.stat().st_size, "bytes")
