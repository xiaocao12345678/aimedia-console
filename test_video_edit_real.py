"""实测视频编辑：用官方示例视频 URL 跑百炼 wan2.7-videoedit（验证 media 契约）。"""
import sys, time
from pathlib import Path
sys.path.insert(0, ".")
from core import providers
from core.config import Config

SAMPLE = "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20260402/ldnfdf/wan2.7-videoedit-style-change.mp4"
cfg = Config()

def run(platform, model, opts, label):
    key = cfg.get_key(platform)
    if not key:
        print(f"{label}: 无 Key，跳过"); return
    t0 = time.time()
    try:
        p = providers.generate_video_edit(
            platform, model, "将整个画面转换为黏土动画风格，保留人物动作与镜头运动",
            SAMPLE, [], key,
            log=lambda l, m: print("   ", l, m[:130]),
            options=opts)
        print(f"OK {label} {time.time()-t0:.0f}s -> {p} {Path(p).stat().st_size} bytes")
    except Exception as e:
        print(f"FAIL {label} {time.time()-t0:.0f}s -> {str(e)[:300]}")

run("阿里百炼", "wan2.7-videoedit",
    {"resolution": "720P", "duration": 5, "poll_interval": 10, "poll_timeout": 900},
    "百炼 wan2.7-videoedit")
