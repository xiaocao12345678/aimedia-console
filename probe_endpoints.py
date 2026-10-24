"""端点连通性自检：用无效 Key 打真实端点。

判定标准：
  401/403      端点存在，鉴权被拒（说明 URL 与请求结构对得上）
  200+业务码  MiniMax 特有：HTTP 200 但 base_resp.status_code 非 0，同样说明端点正确
  400/422      端点存在，参数/模型名被拒（同样说明路径正确）
  404          路径写错
  000 / 超时   网络或在 DNS 层就失败
不产生费用：Key 是假的，请求在鉴权层就被拦下。
"""
from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from PIL import Image  # noqa: E402

from core import adapters, net  # noqa: E402

FAKE_KEY = "sk-invalid-probe-0000"
IMG = BASE / "logs" / "probe.png"
IMG.parent.mkdir(parents=True, exist_ok=True)
if not IMG.exists():
    Image.new("RGB", (64, 64), (40, 120, 200)).save(IMG)

logs: list[str] = []


def log(level: str, msg: str) -> None:
    line = f"[{level}] {msg}"
    logs.append(line)
    first = msg.splitlines()[0] if msg else ""
    print("   ", first[:180])


def probe(label: str, fn, *args, **kwargs) -> str:
    net_logs: list[str] = []
    before = len(logs)
    try:
        fn(*args, log=log, cancel=lambda: False, options=kwargs.pop("options", {}))
        return "意外成功（Key 居然是有效的？）"
    except adapters.ProviderError as e:
        msg = str(e)
        detail = (getattr(e, "detail", "") or "")[:300]
        code = ""
        if "HTTP " in msg:
            code = msg.split("HTTP ")[1].split(" ")[0].strip("：:，,")
        if "业务错误码 1004" in msg or "业务错误码 1001" in msg:
            return f"OK 端点存在（HTTP 200 + 业务鉴权错误码，MiniMax 特有） | {msg[:120]}"
        verdict = {
            "401": "OK 端点存在（鉴权拒绝）",
            "403": "OK 端点存在（无权限）",
            "400": "OK 端点存在（参数/模型被拒）",
            "422": "OK 端点存在（参数校验失败）",
            "429": "OK 端点存在（限流）",
            "404": "!! 路径可能写错",
            "000": "!! 连不上",
        }.get(code, f"? 状态 {code or '未知'}")
        return f"{verdict} | {msg[:120]} | {detail[:120]}"


CASES = [
    ("火山方舟 理解", adapters.ark_understand, "doubao-seed-2-1-pro-260915", "描述图片", [str(IMG)]),
    ("火山方舟 生图", adapters.ark_image, "doubao-seedream-5-0-pro-260628", "一只猫", []),
    ("火山方舟 视频", adapters.ark_video, "doubao-seedance-2-0-260128", "一只猫在跑", []),
    ("百炼 理解", adapters.bl_understand, "qwen3-vl-plus", "描述图片", [str(IMG)]),
    ("百炼 生图", adapters.bl_image, "qwen-image-3.0-pro", "一只猫", []),
    ("百炼 视频", adapters.bl_video, "wan3.0-video", "一只猫在跑", []),
    ("腾讯混元 理解", adapters.th_understand, "hy-vision-2.0-instruct", "描述图片", [str(IMG)]),
    ("腾讯混元 生图", adapters.th_image, "hy-image-v3.5-preview", "一只猫", []),
    ("腾讯混元 视频", adapters.th_video, "hy-video-v1.5", "一只猫在跑", []),
    ("智谱 理解", adapters.zp_understand, "glm-4.6v", "描述图片", [str(IMG)]),
    ("智谱 生图", adapters.zp_image, "glm-image", "一只猫", []),
    ("智谱 视频", adapters.zp_video, "cogvideox-3", "一只猫在跑", []),
    ("千帆 理解", adapters.qf_understand, "ernie-4.5-turbo-vl", "描述图片", [str(IMG)]),
    ("千帆 生图", adapters.qf_image, "qwen-image", "一只猫", []),
    ("千帆 视频", adapters.qf_video, "musesteamer-2.1-turbo-i2v", "一只猫在跑", []),
    ("MiniMax 理解", adapters.mm_understand, "MiniMax-M3.1-Flash", "描述图片", [str(IMG)]),
    ("MiniMax 生图", adapters.mm_image, "image-01", "一只猫", []),
    ("MiniMax 视频", adapters.mm_video, "MiniMax-H3", "一只猫在跑", []),
]

print("=" * 70)
results = []
for label, fn, model, prompt, imgs in CASES:
    print(f"\n### {label}")
    verdict = probe(label, fn, model, prompt, imgs, FAKE_KEY)
    results.append((label, verdict))
    print("   =>", verdict)

print("\n" + "=" * 70)
for label, verdict in results:
    print(f"{label:<14} {verdict[:110]}")

(Path(BASE) / "logs" / "probe_result.txt").write_text(
    "\n".join(f"{a}\t{b}" for a, b in results), encoding="utf-8"
)
