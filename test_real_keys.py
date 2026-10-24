"""用真实 Key 跑一遍：图像理解 + 图像生成（每家 1 次，选最便宜的模型）。

不跑视频：单条 5s 视频会产生可见费用，等确认要跑再单独执行。
费用与产物都会打印出来，日志里 Key 一律脱敏。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from PIL import Image, ImageDraw  # noqa: E402

from core import providers  # noqa: E402
from core.config import Config  # noqa: E402

TEST_IMG = BASE / "logs" / "real_test_input.png"


def make_test_image() -> Path:
    img = Image.new("RGB", (640, 480), (238, 242, 247))
    d = ImageDraw.Draw(img)
    d.rectangle([40, 40, 240, 200], fill=(214, 96, 72), outline=(120, 40, 20), width=4)
    d.ellipse([300, 60, 460, 220], fill=(70, 130, 200))
    d.polygon([(320, 400), (400, 300), (480, 400)], fill=(240, 190, 60))
    d.text((60, 250), "TEST 42", fill=(30, 40, 50))
    d.text((60, 290), "MULTIMODAL", fill=(30, 40, 50))
    img.save(TEST_IMG)
    return TEST_IMG


# 每家挑最便宜/免费的一档
CASES = {
    "火山方舟": dict(
        u_model="doubao-seed-2-1-lite-260915",
        i_model="doubao-seedream-5-0-flash-260915",
    ),
    "阿里百炼": dict(
        u_model="qwen3.8-flash",
        i_model="wan2.7-image",
    ),
    "腾讯混元": dict(
        u_model="hy-vision-2.0-instruct",
        i_model="hy-image-v3",
    ),
    "智谱 GLM": dict(
        u_model="glm-4.6v-flash",   # 免费
        i_model="cogview-3-flash",   # 免费
    ),
    "MiniMax": dict(
        u_model="MiniMax-M3.1-Flash",
        i_model="image-01",
    ),
}

UNDERSTAND_PROMPT = "用一句话描述这张图，并读出图中出现的文字。"
IMAGE_PROMPT = "一只橘猫坐在窗台上，午后阳光，写实摄影"


def quiet_log(counter: dict):
    def _log(level: str, msg: str) -> None:
        counter[level] = counter.get(level, 0) + 1
        if level in ("error", "warn"):
            print(f"      [{level}] {msg.splitlines()[0][:160]}")
    return _log


def main() -> int:
    img = make_test_image()
    cfg = Config()
    rows = []

    for platform, models in CASES.items():
        key = cfg.get_key(platform)
        if not key:
            print(f"\n### {platform}: 跳过（没有 Key）")
            continue
        print(f"\n{'=' * 66}\n### {platform}")

        # ---- 图像理解 ----
        t0 = time.time()
        try:
            out = providers.understand(
                platform, models["u_model"], UNDERSTAND_PROMPT, [str(img)], key,
                log=quiet_log({}), options={"max_tokens": 256},
            )
            dt = time.time() - t0
            print(f"  理解 OK  {models['u_model']}  {dt:.1f}s → {out.strip()[:110]}")
            rows.append((platform, "理解", models["u_model"], "OK", f"{dt:.1f}s", out.strip()[:60]))
        except Exception as e:
            dt = time.time() - t0
            msg = str(e)
            print(f"  理解 FAIL {models['u_model']}  {dt:.1f}s → {msg[:200]}")
            rows.append((platform, "理解", models["u_model"], "FAIL", f"{dt:.1f}s", msg[:120]))

        # ---- 图像生成 ----
        t0 = time.time()
        opts = {"size": "1024x1024", "n": 1}
        if platform == "MiniMax":
            opts = {"size": "16:9", "n": 1}
        try:
            files = providers.generate_image(
                platform, models["i_model"], IMAGE_PROMPT, [], key,
                log=quiet_log({}), options=opts,
            )
            dt = time.time() - t0
            print(f"  生图 OK  {models['i_model']}  {dt:.1f}s → {files}")
            rows.append((platform, "生图", models["i_model"], "OK", f"{dt:.1f}s",
                         ",".join(Path(f).name for f in files)))
        except Exception as e:
            dt = time.time() - t0
            msg = str(e)
            print(f"  生图 FAIL {models['i_model']}  {dt:.1f}s → {msg[:200]}")
            rows.append((platform, "生图", models["i_model"], "FAIL", f"{dt:.1f}s", msg[:120]))

    print(f"\n{'=' * 66}\n汇总")
    print(f"{'平台':<10}{'能力':<6}{'模型':<34}{'结果':<6}{'耗时':<8}备注")
    for r in rows:
        print(f"{r[0]:<10}{r[1]:<6}{r[2]:<34}{r[3]:<6}{r[4]:<8}{r[5][:60]}")
    ok = sum(1 for r in rows if r[3] == "OK")
    print(f"\n成功 {ok} / {len(rows)}")
    return 0 if ok == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
