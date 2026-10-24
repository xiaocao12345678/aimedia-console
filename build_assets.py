"""生成界面用到的小图标（下拉箭头）。只在开发期需要跑一次，产物在 assets/。

为什么不用 QSS 画三角：Qt 的 QSS 没有 CSS 那种 width/height:0 的盒子模型，
border 三角形技巧不成立；而覆盖了 QComboBox::drop-down 又不定制 ::down-arrow
时，Fusion 样式的默认箭头会被一起丢掉 —— 结果就是"下拉框看起来没有下拉"。
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QImage, QPainter, QPen

ASSETS = Path(__file__).resolve().parent / "assets"
ASSETS.mkdir(exist_ok=True)

SIZE = 24


def chevron(path: Path, color: str, width: float = 2.2) -> None:
    img = QImage(SIZE, SIZE, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color))
    pen.setWidthF(width)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.drawPolyline([QPointF(7, 9.5), QPointF(12, 14.5), QPointF(17, 9.5)])
    p.end()
    img.save(str(path))
    print("wrote", path, path.stat().st_size, "bytes")


def spin_arrow(path: Path, color: str, up: bool = True) -> None:
    img = QImage(16, 16, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color))
    pen.setWidthF(1.8)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    if up:
        p.drawPolyline([QPointF(4, 10), QPointF(8, 6), QPointF(12, 10)])
    else:
        p.drawPolyline([QPointF(4, 6), QPointF(8, 10), QPointF(12, 6)])
    p.end()
    img.save(str(path))
    print("wrote", path, path.stat().st_size, "bytes")


if __name__ == "__main__":
    chevron(ASSETS / "combo_arrow.png", "#46515c")
    chevron(ASSETS / "combo_arrow_disabled.png", "#a9b4c0")
    spin_arrow(ASSETS / "spin_up.png", "#46515c", up=True)
    spin_arrow(ASSETS / "spin_down.png", "#46515c", up=False)
