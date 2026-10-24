"""验证火山本地视频：上传成功 + 提交时的真实报错（模型未开通会明确报出来）。"""
import sys, time
from pathlib import Path
sys.path.insert(0, ".")
from core import providers
from core.config import Config

cfg = Config()
t0 = time.time()
try:
    out = providers.generate_video_edit(
        "火山方舟", "doubao-seedance-2-5-260628",
        "把画面转换成水彩画风格，保留镜头运动",
        "logs/test_clip.mp4", [], cfg.get_key("火山方舟"),
        log=lambda l, m: print("   ", l, m[:150]),
        options={"poll_interval": 10, "poll_timeout": 300, "duration": 5})
    print("OK", out)
except Exception as e:
    print("FAIL", f"{time.time()-t0:.0f}s", str(e)[:400])
