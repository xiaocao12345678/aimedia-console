"""第二轮：换模型定位问题（区分「Key 无效」「模型未开通」「限流」「余额不足」）。

第一轮已经确认：五家鉴权都通过了（没有一家报 401），失败都是账户/额度/开通层面的。
这一轮换同平台的其它模型，判断是"单个模型没开"还是"整个能力没开"。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from core import providers  # noqa: E402
from core.config import Config  # noqa: E402

IMG = BASE / "logs" / "real_test_input.png"
UNDERSTAND_PROMPT = "一句话描述这张图，并读出文中的文字。"
IMAGE_PROMPT = "一只橘猫坐在窗台上，午后阳光"
COST_NOTE = "失败请求不收费；成功会扣一点额度"


def try_understand(platform, model, key):
    t0 = time.time()
    try:
        out = providers.understand(platform, model, UNDERSTAND_PROMPT, [str(IMG)], key,
                                   log=lambda l, m: None, options={"max_tokens": 128})
        return "OK", f"{time.time()-t0:.1f}s", out.strip().replace("\n", " ")[:70]
    except Exception as e:
        return "FAIL", f"{time.time()-t0:.1f}s", str(e)[:150]


def try_image(platform, model, key, size="1024x1024"):
    t0 = time.time()
    opts = {"size": size, "n": 1}
    try:
        files = providers.generate_image(platform, model, IMAGE_PROMPT, [], key,
                                         log=lambda l, m: None, options=opts)
        return "OK", f"{time.time()-t0:.1f}s", ",".join(Path(f).name for f in files)
    except Exception as e:
        return "FAIL", f"{time.time()-t0:.1f}s", str(e)[:150]


def main() -> None:
    cfg = Config()
    print(COST_NOTE)

    plan = [
        # 火山：生图换标准版与 pro，确认是否整条生图能力未开通
        ("火山方舟", "image", "doubao-seedream-5-0-260128", "2048x2048"),
        ("火山方舟", "image", "doubao-seedream-5-0-pro-260628", "2048x2048"),
        ("火山方舟", "image", "doubao-seedream-4-5-251128", "2048x2048"),
        # 火山：理解再确认一次另一个模型
        ("火山方舟", "understand", "doubao-seed-2-1-pro-260915", None),

        # 腾讯：生图换 3.5
        ("腾讯混元", "image", "hy-image-v3.5-preview", "1024x1024"),

        # 智谱：理解换付费模型，确认是否只是免费版限流
        ("智谱 GLM", "understand", "glm-4.6v", None),
        ("智谱 GLM", "understand", "glm-4.6v-flashx", None),

        # 百炼：换一个视频/图像模型确认开通范围
        ("阿里百炼", "image", "qwen-image-3.0-pro", "1024*1024"),

        # 智谱：视频用官方免费的 flash 模型验证链路
        ("智谱 GLM", "video", "cogvideox-flash", None),
    ]

    for platform, cap, model, size in plan:
        key = cfg.get_key(platform)
        if not key:
            print(f"{platform:<10}{cap:<11}{model:<32} 跳过（无 Key）")
            continue
        print(f"\n>>> {platform} / {cap} / {model}")
        if cap == "understand":
            status, dt, info = try_understand(platform, model, key)
        elif cap == "image":
            status, dt, info = try_image(platform, model, key, size or "1024x1024")
        else:
            t0 = time.time()
            try:
                path = providers.generate_video(platform, model, "一只橘猫在窗边伸懒腰，镜头缓慢推进",
                                                [], key, log=lambda l, m: None,
                                                options={"poll_interval": 8, "poll_timeout": 600,
                                                         "duration": "5", "resolution": "768P"})
                status, dt, info = "OK", f"{time.time()-t0:.1f}s", path
            except Exception as e:
                status, dt, info = "FAIL", f"{time.time()-t0:.1f}s", str(e)[:150]
        print(f"    {status:<5}{dt:<9}{info}")


if __name__ == "__main__":
    main()
