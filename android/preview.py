"""桌面预览：按手机尺寸打开 Android 版界面，逐页截图，然后退出。

只为验证 Kivy 布局在打包前是对的（不用等半小时构建才发现崩）。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("KIVY_NO_ARGS", "1")
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from kivy.clock import Clock
from kivy.core.window import Window

from main import ConsoleApp

OUT = BASE / "logs"
OUT.mkdir(exist_ok=True)
app = ConsoleApp()
shots: list[tuple[float, str, str | None]] = [
    (1.5, "pv_understand", None),
    (2.6, "pv_image", "image"),
    (3.6, "pv_video", "video"),
    (4.6, "pv_edit", "edit"),
    (5.6, "pv_keys", "keys"),
    (6.6, "pv_logs", "logs"),
]


def grab(dt, name: str, target: str | None):
    if target:
        app.goto(target)
    Clock.schedule_once(lambda _dt: Window.screenshot(name=str(OUT / f"{name}.png")), 0.4)


for delay, name, target in shots:
    Clock.schedule_once(lambda dt, n=name, t=target: grab(dt, n, t), delay)

Clock.schedule_once(lambda *_: app.stop(), 9.0)
app.run()
print("截图完成：")
for f in sorted(OUT.glob("pv_*.png")):
    print(" ", f.name, f.stat().st_size, "bytes")
