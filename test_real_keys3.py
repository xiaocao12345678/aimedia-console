"""第三轮：修复后再验火山生图，并重试智谱视频（限流可能是瞬时的）。"""
from __future__ import annotations

import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from core import providers  # noqa: E402
from core.config import Config  # noqa: E402

cfg = Config()
PROMPT = "一只橘猫坐在窗台上，午后阳光，写实摄影"


def show(label, fn):
    t0 = time.time()
    try:
        out = fn()
        print(f"{label:<52} OK   {time.time()-t0:>6.1f}s  {out}")
        return True
    except Exception as e:
        print(f"{label:<52} FAIL {time.time()-t0:>6.1f}s  {str(e)[:180]}")
        return False


key_v = cfg.get_key("火山方舟")
for model, size in [("doubao-seedream-5-0-pro-260628", "2K"),
                    ("doubao-seedream-5-0-flash-260915", "2K"),
                    ("doubao-seedream-5-0-260128", "2K")]:
    show(f"火山 生图 {model} size={size}",
         lambda m=model, s=size: providers.generate_image(
             "火山方舟", m, PROMPT, [], key_v, log=lambda l, x: None,
             options={"size": s, "n": 1}))

# 多张（n=2）也要能走通，验证刚修的分支
show("火山 生图 5.0 pro 一次两张 (n=2)",
     lambda: providers.generate_image(
         "火山方舟", "doubao-seedream-5-0-pro-260628", PROMPT, [], key_v,
         log=lambda l, x: None, options={"size": "2K", "n": 2}))

key_z = cfg.get_key("智谱 GLM")
show("智谱 视频 cogvideox-flash 重试",
     lambda: providers.generate_video(
         "智谱 GLM", "cogvideox-flash", "一只橘猫在窗边伸懒腰，镜头缓慢推进", [], key_z,
         log=lambda l, x: None,
         options={"poll_interval": 8, "poll_timeout": 420, "duration": "5"}))
