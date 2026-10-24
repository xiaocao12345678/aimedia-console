"""平台注册表与统一入口。

界面只认这三个函数：understand / generate_image / generate_video。
具体 HTTP 细节在 adapters.py，一家一个实现。

模型清单统一是 (模型ID, 说明) 二元组：
- 下拉框显示 "ID · 说明"，调用只取 ID（手输时也按 ID 处理）
- 只收录「程序已实现调用路径」的模型，避免列出来却调不通
"""
from __future__ import annotations

from typing import Callable

from .adapters import (
    ProviderError,
    ark_image,
    ark_understand,
    ark_video,
    ark_video_edit,
    bl_image,
    bl_understand,
    bl_video,
    bl_video_edit,
    mm_image,
    mm_understand,
    mm_video,
    mm_video_edit,
    qf_image,
    qf_understand,
    qf_video,
    th_image,
    th_understand,
    th_video,
    zp_image,
    zp_understand,
    zp_video,
)

__all__ = [
    "ProviderError",
    "platforms",
    "models_for",
    "model_ids",
    "capability_label",
    "docs_url",
    "understand",
    "generate_image",
    "generate_video",
    "generate_video_edit",
    "platforms_for",
    "MODELS",
    "DOCS",
    "KEY_HINTS",
]

CAPABILITY_LABELS = {
    "understand": "图像理解",
    "image": "图像生成",
    "video": "视频生成",
    "video_edit": "视频编辑 / 参考视频",
}

# 模型清单：ID 取自各家官方模型列表 / API 文档（2026-10 核对），说明里写档位与特性。
# 顺序即下拉顺序：旗舰/推荐在前。下拉框可编辑，平台上线新模型时直接手输 ID 即可。
MODELS: dict[str, dict[str, list[tuple[str, str]]]] = {
    "火山方舟": {
        "understand": [
            ("doubao-seed-2-1-pro-260915", "Seed 2.1 Pro · 旗舰，理解+推理"),
            ("doubao-seed-2-1-lite-260915", "Seed 2.1 Lite · 轻量"),
            ("doubao-seed-2-1-turbo-260628", "Seed 2.1 Turbo · 高并发"),
            ("doubao-seed-evolving", "Seed Evolving · 周更迭代版"),
            ("doubao-seed-2-0-pro-260128", "Seed 2.0 Pro · 上一代旗舰"),
            ("doubao-seed-1-6-vision-250815", "Seed 1.6 Vision · 纯视觉理解"),
        ],
        "image": [
            ("doubao-seedream-5-0-pro-260628", "Seedream 5.0 Pro · 旗舰（实测可用）"),
            ("doubao-seedream-5-0-flash-260915", "Seedream 5.0 Flash · 快速版（实测可用）"),
        ],
        "video": [
            ("doubao-seedance-2-5-260628", "Seedance 2.5 · 旗舰，支持 30s 与音频"),
            ("doubao-seedance-2-0-260128", "Seedance 2.0"),
            ("doubao-seedance-2-0-fast-260128", "Seedance 2.0 Fast · 出片快"),
            ("doubao-seedance-2-0-mini-260615", "Seedance 2.0 Mini · 便宜"),
            ("doubao-seedance-1-0-pro-250528", "Seedance 1.0 Pro · 即将下线"),
            ("doubao-seedance-1-0-lite-i2v-250428", "Seedance 1.0 Lite · 图生视频"),
        ],
        "video_edit": [
            ("doubao-seedance-2-5-260628", "Seedance 2.5 · 视频编辑 4–30s，可加参考图"),
            ("doubao-seedance-2-0-260128", "Seedance 2.0 · 参考视频重绘"),
        ],
    },
    "阿里百炼": {
        "understand": [
            ("qwen3.8-max", "千问 3.8 Max · 旗舰多模态"),
            ("qwen3.8-flash", "千问 3.8 Flash · 轻量"),
            ("qwen3.7-plus", "千问 3.7 Plus · 均衡"),
            ("qwen3-vl-plus", "Qwen3-VL Plus · 视觉专项"),
            ("qwen3-vl-max", "Qwen3-VL Max · 视觉旗舰"),
        ],
        "image": [
            ("qwen-image-3.0-pro", "千问图像 3.0 Pro · 复杂文字渲染"),
            ("qwen-image-2.1-pro", "千问图像 2.1 Pro · 上一代"),
            ("wan2.7-image-pro", "万相 2.7 Pro · 旗舰，支持 4K"),
            ("wan2.7-image", "万相 2.7 · 2K"),
        ],
        "video": [
            ("wan3.0-video", "万相 3.0 Video · 旗舰，原生 30s"),
            ("wan3.0-video-prime", "万相 3.0 Prime · 高速版"),
            ("wan2.7-t2v", "万相 2.7 文生视频"),
            ("wan2.7-i2v", "万相 2.7 图生视频"),
            ("wan2.7-r2v", "万相 2.7 参考生视频"),
            ("wan2.7-videoedit", "万相 2.7 视频编辑"),
            ("wan2.6-t2v", "万相 2.6 文生视频 · 旧协议"),
        ],
        "video_edit": [
            ("wan2.7-videoedit", "万相 2.7 视频编辑 · 指令编辑 / 换装 / 风格迁移"),
            ("wan3.0-video", "万相 3.0 · 多模态参考（含参考视频）"),
        ],
    },
    "腾讯混元": {
        "understand": [
            ("hy-vision-2.0-instruct", "HY Vision 2.0 · 旗舰视觉理解"),
            ("hunyuan-t1-vision-20250916", "HY Vision 1.5 Thinking · 视觉深度思考"),
            ("hunyuan-turbos-vision-video-20250728", "HY Vision Video · 视频理解"),
            ("youtu-vita", "优图 VITA · 图片+视频，128k"),
        ],
        "image": [
            ("hy-image-v3.5-preview", "Hy-Image 3.5 · 旗舰，最高 4K"),
            ("hy-image-v3", "Hy-Image 3.0 · 经典文生图"),
            ("seedream-image-v5.0-pro", "Seedream 5.0 Pro · 三方"),
            ("seedream-image-v5.0-lite", "Seedream 5.0 Lite · 三方"),
            ("kling-image-v3", "可灵 Image v3 · 三方"),
            ("kling-image-o1", "可灵 Image O1 · 三方"),
            ("wand-vega-image-pro", "WAND Vega Pro · 三方"),
            ("vidu-image-q2", "Vidu Image Q2 · 三方，异步"),
        ],
        "video": [
            ("hy-video-v1.5", "HY Video 1.5 · 自研，5s / 720P"),
        ],
        "video_edit": [],
    },
    "智谱 GLM": {
        "understand": [
            ("glm-4.6v", "GLM-4.6V · 视觉推理旗舰，支持工具调用"),
            ("glm-5.3-flash", "GLM-5.3-Flash · 原生多模态，1M 上下文"),
            ("glm-5.3-flashx", "GLM-5.3-FlashX · 高速版"),
            ("glm-5v-turbo", "GLM-5V-Turbo · 多模态 Coding"),
            ("glm-4.6v-flash", "GLM-4.6V-Flash · 免费（实测常被限流，建议备用）"),
            ("glm-4.5v", "GLM-4.5V · 上一代视觉推理"),
            ("glm-4v-flash", "GLM-4V-Flash · 免费，基础识图"),
            ("glm-ocr", "GLM-OCR · 文档/版面解析"),
        ],
        "image": [
            ("glm-image", "GLM-Image · 旗舰，文字渲染强"),
            ("cogview-4", "CogView-4 · 上一代通用"),
            ("cogview-4-250304", "CogView-4 快照版"),
            ("cogview-3-flash", "CogView-3-Flash · 免费（实测可用）"),
        ],
        "video": [
            ("cogvideox-3", "CogVideoX-3 · 旗舰，支持首尾帧与 4K"),
            ("cogvideox-2", "CogVideoX-2 · 上一代"),
            ("cogvideox-flash", "CogVideoX-Flash · 免费（实测 429 限流，建议改用 cogvideox-3）"),
        ],
        "video_edit": [],
    },
    "百度千帆": {
        "understand": [
            ("ernie-5.0", "文心 5.0 · 原生全模态旗舰"),
            ("ernie-4.5-turbo-vl", "ERNIE 4.5 Turbo VL · 视觉主力"),
            ("qwen3-vl-32b-instruct", "Qwen3-VL-32B · 三方"),
            ("deepseek-vl2", "DeepSeek-VL2 · 三方"),
        ],
        "image": [
            ("qwen-image", "Qwen-Image · iRAG 风格检索增强"),
            ("ernie-image-turbo", "ERNIE Image Turbo · 文心生图"),
            ("musesteamer-air-image", "蒸汽机 Air Image · 支持 b64 返回"),
            ("qwen-image-edit", "Qwen-Image-Edit · 图像编辑"),
        ],
        "video": [
            ("K3.0", "千帆 K3.0 · 自研旗舰，支持 4K"),
            ("K2.6", "千帆 K2.6 · 自研"),
            ("K2.5-Turbo", "千帆 K2.5 Turbo · 快"),
            ("musesteamer-2.1-turbo-i2v", "蒸汽机 2.1 Turbo · 图生视频"),
            ("musesteamer-2.0-pro-i2v", "蒸汽机 2.0 Pro · 图生视频"),
            ("musesteamer-2.0-turbo-i2v-audio", "蒸汽机 2.0 Turbo · 带音频"),
            ("musesteamer-2.0-lite-i2v", "蒸汽机 2.0 Lite · 便宜"),
        ],
        "video_edit": [],
    },
    "MiniMax": {
        "understand": [
            ("MiniMax-M3.1-Flash", "M3.1 Flash · 原生多模态，1M 上下文"),
            ("MiniMax-M3", "M3 · 原生多模态"),
        ],
        "image": [
            ("image-01", "Image-01 · 文生图/图生图，可自定义尺寸"),
            ("image-01-live", "Image-01 Live · 手绘/卡通风格增强"),
        ],
        "video": [
            ("MiniMax-H3", "H3 · 旗舰，768P/2K，4–15s，多模态参考"),
            ("MiniMax-H3-Max", "H3 Max · 极速版，480P/768P"),
        ],
        "video_edit": [
            ("MiniMax-H3", "H3 · 多模态参考（视频 + 图片 + 文本一起给）"),
        ],
    },
}

# 各平台 Key 的形态，填错时最容易卡在这里，切换平台时直接提示。
KEY_HINTS = {
    "火山方舟": "方舟控制台 → API Key 管理，形如 UUID 或 ARK_API_KEY",
    "阿里百炼": "DashScope API Key，形如 sk-xxxxxxxx（注意先选地域）",
    "腾讯混元": "TokenHub 控制台 → API Key（Bearer，无需 TC3 签名）",
    "智谱 GLM": "BigModel API Key，形如 xxxxxxxx.yyyyyyyy（模型标准 API 类）",
    "百度千帆": "千帆 API Key，形如 bce-v3/ALTAK-xxxxxxxx/yyyyyyyy",
    "MiniMax": "MiniMax 开放平台接口密钥（Bearer）",
}

DOCS = {
    "火山方舟": "https://docs.volcengine.com/docs/ark/video-generation-api",
    "阿里百炼": "https://help.aliyun.com/zh/model-studio/models",
    "腾讯混元": "https://cloud.tencent.com/document/product/1823/130051",
    "智谱 GLM": "https://docs.bigmodel.cn/cn/guide/start/model-overview",
    "百度千帆": "https://cloud.baidu.com/doc/qianfan-api/s/3mgm0hiik",
    "MiniMax": "https://platform.minimax.cn/docs/guides/models-intro",
}

_DISPATCH: dict[str, dict[str, Callable]] = {
    "火山方舟": {"understand": ark_understand, "image": ark_image, "video": ark_video,
                 "video_edit": ark_video_edit},
    "阿里百炼": {"understand": bl_understand, "image": bl_image, "video": bl_video,
                 "video_edit": bl_video_edit},
    "腾讯混元": {"understand": th_understand, "image": th_image, "video": th_video},
    "智谱 GLM": {"understand": zp_understand, "image": zp_image, "video": zp_video},
    "百度千帆": {"understand": qf_understand, "image": qf_image, "video": qf_video},
    "MiniMax": {"understand": mm_understand, "image": mm_image, "video": mm_video,
                "video_edit": mm_video_edit},
}


def platforms() -> list[str]:
    return list(_DISPATCH.keys())


def models_for(platform: str, capability: str) -> list[tuple[str, str]]:
    return list(MODELS.get(platform, {}).get(capability, []))


def platforms_for(capability: str) -> list[str]:
    """哪些平台在这个能力上真的有可用模型（用于只列出支持者的下拉）。"""
    return [p for p in platforms() if MODELS.get(p, {}).get(capability)]


def model_ids(platform: str, capability: str) -> list[str]:
    return [mid for mid, _note in models_for(platform, capability)]


def capability_label(capability: str) -> str:
    return CAPABILITY_LABELS.get(capability, capability)


def docs_url(platform: str) -> str:
    return DOCS.get(platform, "")


def _call(platform: str, capability: str, *args, **kwargs):
    impl = _DISPATCH.get(platform, {}).get(capability)
    if impl is None:
        raise ProviderError(f"「{platform}」还没有接入「{capability}」")
    try:
        return impl(*args, **kwargs)
    except ProviderError:
        raise
    except Exception as e:  # 把底层异常翻译成界面能读懂的信息
        import traceback

        raise ProviderError(f"{e.__class__.__name__}: {e}", traceback.format_exc()[-3000:])


def understand(platform, model, prompt, image_paths, api_key, *, log=None, cancel=None, options=None) -> str:
    return _call(platform, "understand", model, prompt, image_paths, api_key,
                 log=log, cancel=cancel, options=options or {})


def generate_image(platform, model, prompt, image_paths, api_key, *, log=None, cancel=None, options=None) -> list[str]:
    return _call(platform, "image", model, prompt, image_paths, api_key,
                 log=log, cancel=cancel, options=options or {})


def generate_video(platform, model, prompt, image_paths, api_key, *, log=None, cancel=None, options=None) -> str:
    return _call(platform, "video", model, prompt, image_paths, api_key,
                 log=log, cancel=cancel, options=options or {})


def generate_video_edit(platform, model, prompt, video_source, image_sources, api_key,
                        *, log=None, cancel=None, options=None) -> str:
    """视频编辑 / 参考视频重绘：输入一段参考视频（本地路径或公网 URL）+ 可选参考图。"""
    return _call(platform, "video_edit", model, prompt, video_source, image_sources or [],
                 api_key, log=log, cancel=cancel, options=options or {})
