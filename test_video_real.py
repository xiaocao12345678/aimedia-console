import sys, time
from pathlib import Path
sys.path.insert(0, ".")
from core import providers
from core.config import Config
cfg = Config()
t0 = time.time()
try:
    p = providers.generate_video("智谱 GLM", "cogvideox-3",
        "一只橘猫在窗边伸懒腰，镜头缓慢推进，午后暖光",
        [], cfg.get_key("智谱 GLM"),
        log=lambda l, m: print("   ", l, m[:120]),
        options={"poll_interval": 8, "poll_timeout": 600, "duration": "5"})
    print("OK", f"{time.time()-t0:.0f}s", p, Path(p).stat().st_size, "bytes")
except Exception as e:
    print("FAIL", f"{time.time()-t0:.0f}s", str(e)[:250])
