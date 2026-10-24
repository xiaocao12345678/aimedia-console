"""六家平台的 HTTP 适配实现。

每条端点都来自官方文档（详见各函数 docstring 里的链接）。字段名保持原样，
不做"猜测式兼容"：参数不被接受时让平台报错，界面把原始错误完整打出来。
"""
from __future__ import annotations

import base64
import json
import os
import time
from typing import Any, Callable, Optional

from . import net

LogFn = Callable[[str, str], None]
CancelFn = Callable[[], bool]


class ProviderError(RuntimeError):
    def __init__(self, message: str, detail: str = ""):
        super().__init__(message)
        self.detail = detail


# ------------------------------------------------------------------ 公共工具


def _log(log: Optional[LogFn]) -> LogFn:
    return log or (lambda level, msg: None)


def _post(url: str, headers: dict, body: dict, *, what: str, log: LogFn,
          timeout: float = 180.0) -> dict:
    r = net.request("POST", url, headers=headers, json_body=body, timeout=timeout, log=log)
    if not r.ok:
        raise ProviderError(f"{what}失败：HTTP {r.status} {r.error}", r.text[:4000] or "")
    return r.json or {}


def _get(url: str, headers: dict, *, what: str, log: LogFn, timeout: float = 120.0) -> dict:
    r = net.request("GET", url, headers=headers, timeout=timeout, log=log)
    if not r.ok:
        raise ProviderError(f"{what}失败：HTTP {r.status} {r.error}", r.text[:4000] or "")
    return r.json or {}


def _bearer(key: str) -> dict:
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def _dig(obj: Any, path: str, default: Any = None) -> Any:
    """按 'a.b.0.c' 取值，路径里纯数字表示列表下标。"""
    cur = obj
    for part in path.split("."):
        if cur is None:
            return default
        if isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError):
                return default
        elif isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return default
    return default if cur is None else cur


def _data_url(path: str) -> str:
    import mimetypes

    mime = mimetypes.guess_type(path)[0] or "image/png"
    with open(path, "rb") as f:
        return f"data:{mime};base64," + base64.b64encode(f.read()).decode("ascii")


def _ratio(size: str) -> str:
    s = (size or "").lower().replace("*", "x").replace("×", "x")
    table = {
        "1024x1024": "1:1", "1280x720": "16:9", "720x1280": "9:16",
        "1024x1536": "2:3", "1536x1024": "3:2", "1328x1328": "1:1",
        "1920x1080": "16:9", "1080x1920": "9:16", "2048x1080": "21:9",
    }
    if s in table:
        return table[s]
    if ":" in size:
        return size
    return "16:9"


def _int_or(value: Any, default: int) -> int:
    try:
        return int(str(value).strip())
    except Exception:
        return default


def _save_image(resp: dict, path_hint: str, log: LogFn, prefix: str) -> str:
    """把响应里的 url 或 b64_json 落盘。"""
    from .providers_util import stamp

    url = None
    b64 = None
    if isinstance(resp, dict):
        url = resp.get("url")
        b64 = resp.get("b64_json")
    if b64:
        with open(path_hint, "wb") as f:
            f.write(base64.b64decode(b64))
        log("info", f"图片已保存 {path_hint}")
        return path_hint
    if url:
        net.download(url, path_hint, log=log)
        return path_hint
    raise ProviderError("响应里没有图片地址或图片数据", json.dumps(resp, ensure_ascii=False)[:2000])


def _poll(fetch, *, status_get, done, failed, interval: float, timeout: float,
          log: LogFn, cancel: Optional[CancelFn], task_id: str) -> dict:
    log("info", f"开始轮询任务 {task_id}，间隔 {interval:.0f}s，最长等待 {timeout / 60:.0f} 分钟")
    return net.poll(
        fetch,
        is_done=done,
        is_failed=failed,
        interval=interval,
        timeout=timeout,
        log=log,
        cancel=cancel,
    )


# ================================================================== 火山方舟
# 文档：/docs/ark/image-understanding、/docs/ark/image-generation-api、
#       /docs/ark/create-video-generation-task-api、/docs/ark/get-video-generation-task-api
ARK_BASE = "https://ark.cn-beijing.volces.com/api/v3"


def ark_understand(model, prompt, images, key, *, log, cancel, options) -> str:
    log = _log(log)
    content = []
    for p in images:
        content.append({"type": "image_url", "image_url": {"url": _data_url(p)}})
    content.append({"type": "text", "text": prompt})
    body = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": options.get("max_tokens", 2048),
    }
    data = _post(f"{ARK_BASE}/chat/completions", _bearer(key), body, what="火山方舟图像理解", log=log)
    text = _dig(data, "choices.0.message.content", "")
    if not text:
        raise ProviderError("模型没有返回文本内容", json.dumps(data, ensure_ascii=False)[:2000])
    usage = data.get("usage") or {}
    log("info", f"token 用量：输入 {usage.get('prompt_tokens')} / 输出 {usage.get('completion_tokens')}")
    return text if isinstance(text, str) else json.dumps(text, ensure_ascii=False)


def ark_image(model, prompt, images, key, *, log, cancel, options) -> list[str]:
    from .providers_util import stamp

    log = _log(log)
    size = (options.get("size") or "").strip()
    body: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "response_format": "url",
        "output_format": "png",
        "watermark": False,
    }
    if size:
        body["size"] = size
    # 实测：seedream 5.0 系列不支持一次性出多张
    # （传 sequential_image_generation 会 400：not supported by the current model），
    # 所以这里固定单张，要更多张就多点几次。
    want_n = int(options.get("n") or 1)
    if want_n > 1:
        log("warn", f"火山方舟生图一次只返回 1 张（请求 {want_n} 张已被忽略）")
    if images:
        body["image"] = [_data_url(p) for p in images]
    if options.get("seed") not in (None, ""):
        body["seed"] = int(options["seed"])
    data = _post(f"{ARK_BASE}/images/generations", _bearer(key), body, what="火山方舟图像生成", log=log)
    items = data.get("data") or []
    if not items:
        raise ProviderError("响应里没有 data 数组", json.dumps(data, ensure_ascii=False)[:2000])
    out = []
    for i, item in enumerate(items):
        out.append(_save_image(item, stamp("img_火山方舟", ".png"), log, "火山方舟"))
    log("info", f"生图完成，共 {len(out)} 张")
    return out


def ark_video(model, prompt, images, key, *, log, cancel, options) -> str:
    from .providers_util import stamp

    log = _log(log)
    content: list[dict] = [{"type": "text", "text": prompt}]
    for p in images:
        content.append({"type": "image_url", "image_url": {"url": _data_url(p)}})
    body: dict[str, Any] = {
        "model": model,
        "content": content,
        "ratio": _ratio(options.get("size") or "") if images else _ratio(options.get("size") or ""),
        "duration": _int_or(options.get("duration"), 5),
        "watermark": False,
    }
    if images:
        body["ratio"] = "adaptive"
    data = _post(f"{ARK_BASE}/contents/generations/tasks", _bearer(key), body,
                 what="火山方舟视频任务提交", log=log)
    task_id = data.get("id")
    if not task_id:
        raise ProviderError("没有拿到任务 id", json.dumps(data, ensure_ascii=False)[:2000])

    def fetch():
        return net.request("GET", f"{ARK_BASE}/contents/generations/tasks/{task_id}",
                           headers=_bearer(key), timeout=60, log=log)

    def failed(d):
        st = d.get("status")
        if st in ("failed", "expired", "cancelled"):
            err = d.get("error") or {}
            return f"{st}: {err.get('code')} {err.get('message')}".strip()
        return None

    res = _poll(
        fetch,
        status_get=lambda d: d.get("status"),
        done=lambda d: d.get("status") == "succeeded",
        failed=failed,
        interval=float(options.get("poll_interval") or 10),
        timeout=float(options.get("poll_timeout", 1200)),
        log=log,
        cancel=cancel,
        task_id=task_id,
    )
    url = _dig(res, "content.video_url")
    if not url:
        raise ProviderError("任务成功但没有 video_url", json.dumps(res, ensure_ascii=False)[:2000])
    return net.download(url, stamp("vid_火山方舟", ".mp4"), log=log)


# ================================================================ 阿里云百炼
# 文档：/model-studio/vision-model、/model-studio/text-to-image、
#       /model-studio/wan3-video-generation-api-reference
BL_BASE = "https://dashscope.aliyuncs.com"


def bl_understand(model, prompt, images, key, *, log, cancel, options) -> str:
    log = _log(log)
    content: list[dict] = [{"type": "text", "text": prompt}]
    for p in images:
        content.append({"type": "image_url", "image_url": {"url": _data_url(p)}})
    body = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
    }
    data = _post(f"{BL_BASE}/compatible-mode/v1/chat/completions", _bearer(key), body,
                 what="百炼图像理解", log=log)
    text = _dig(data, "choices.0.message.content", "")
    if not text:
        raise ProviderError("模型没有返回文本内容", json.dumps(data, ensure_ascii=False)[:2000])
    return text if isinstance(text, str) else json.dumps(text, ensure_ascii=False)


def bl_image(model, prompt, images, key, *, log, cancel, options) -> list[str]:
    from .providers_util import stamp

    log = _log(log)
    content: list[dict] = []
    for p in images:
        content.append({"image": _data_url(p)})
    content.append({"text": prompt})
    params: dict[str, Any] = {"watermark": False, "n": int(options.get("n") or 1)}
    size = (options.get("size") or "").strip()
    if size:
        params["size"] = size.replace("x", "*") if "x" in size else size
    if options.get("seed") not in (None, ""):
        params["seed"] = int(options["seed"])
    body = {"model": model, "input": {"messages": [{"role": "user", "content": content}]},
            "parameters": params}
    data = _post(f"{BL_BASE}/api/v1/services/aigc/multimodal-generation/generation",
                 _bearer(key), body, what="百炼图像生成", log=log)
    items = _dig(data, "output.choices.0.message.content") or []
    out = []
    for item in items:
        if isinstance(item, dict) and item.get("image"):
            out.append(_save_image({"url": item["image"]}, stamp("img_百炼", ".png"), log, "百炼"))
    if not out:
        raise ProviderError("响应里没有图片", json.dumps(data, ensure_ascii=False)[:2000])
    return out


def bl_video(model, prompt, images, key, *, log, cancel, options) -> str:
    from .providers_util import stamp

    log = _log(log)
    headers = _bearer(key)
    headers["X-DashScope-Async"] = "enable"
    inp: dict[str, Any] = {"prompt": prompt}
    if images:
        inp["media"] = [{"type": "first_frame", "url": _data_url(images[0])}]
    params: dict[str, Any] = {"prompt_extend": True}
    if options.get("resolution"):
        params["resolution"] = options["resolution"]
    if options.get("duration"):
        params["duration"] = _int_or(options["duration"], 5)
    size = (options.get("size") or "").strip()
    if size and ":" not in size and "x" in size:
        params["ratio"] = _ratio(size)
    body = {"model": model, "input": inp, "parameters": params}
    data = _post(f"{BL_BASE}/api/v1/services/aigc/video-generation/video-synthesis",
                 headers, body, what="百炼视频任务提交", log=log)
    task_id = _dig(data, "output.task_id")
    if not task_id:
        raise ProviderError("没有拿到 task_id", json.dumps(data, ensure_ascii=False)[:2000])

    def fetch():
        return net.request("GET", f"{BL_BASE}/api/v1/tasks/{task_id}",
                           headers=_bearer(key), timeout=60, log=log)

    def failed(d):
        st = _dig(d, "output.task_status")
        if st in ("FAILED", "CANCELED", "UNKNOWN"):
            return f"{st}: {_dig(d, 'output.code')} {_dig(d, 'output.message')}".strip()
        return None

    res = _poll(
        fetch,
        status_get=lambda d: _dig(d, "output.task_status"),
        done=lambda d: _dig(d, "output.task_status") == "SUCCEEDED",
        failed=failed,
        interval=float(options.get("poll_interval") or 15),
        timeout=float(options.get("poll_timeout", 1200)),
        log=log,
        cancel=cancel,
        task_id=task_id,
    )
    url = _dig(res, "output.video_url")
    if not url:
        raise ProviderError("任务成功但没有 video_url", json.dumps(res, ensure_ascii=False)[:2000])
    return net.download(url, stamp("vid_百炼", ".mp4"), log=log)


# ================================================================ 腾讯 TokenHub
# 文档：/document/product/1823/136956（图片理解）、135745（Hy 生图）、137202（Hy 生视频）
TH_BASE = "https://tokenhub.tencentmaas.com/v1"


def th_understand(model, prompt, images, key, *, log, cancel, options) -> str:
    log = _log(log)
    content: list[dict] = []
    for p in images:
        content.append({"type": "image_url", "image_url": {"url": _data_url(p)}})
    content.append({"type": "text", "text": prompt})
    body = {"model": model, "messages": [{"role": "user", "content": content}], "stream": False}
    data = _post(f"{TH_BASE}/chat/completions", _bearer(key), body, what="腾讯混元图像理解", log=log)
    text = _dig(data, "choices.0.message.content", "")
    if not text:
        raise ProviderError("模型没有返回文本内容", json.dumps(data, ensure_ascii=False)[:2000])
    return text if isinstance(text, str) else json.dumps(text, ensure_ascii=False)


def th_image(model, prompt, images, key, *, log, cancel, options) -> list[str]:
    from .providers_util import stamp

    log = _log(log)
    size = (options.get("size") or "").strip()
    if model == "hy-image-v3":
        # Hy-Image-3.0 独立端点：data[n].url
        body: dict[str, Any] = {"model": model, "prompt": prompt}
        if size:
            body["size"] = size
        data = _post(f"{TH_BASE}/wand/hunyuan-image/v3-generation", _bearer(key), body,
                     what="混元生图 3.0", log=log)
        items = data.get("data") or []
        if not items:
            raise ProviderError("响应里没有 data 数组", json.dumps(data, ensure_ascii=False)[:2000])
        return [_save_image(it, stamp("img_混元", ".png"), log, "混元") for it in items]

    # Hy-Image-3.5-preview：messages 形态，结果在 choices[0].delta.image.url
    content: list[dict] = []
    for p in images:
        content.append({"type": "image_url", "image_url": {"url": _data_url(p)}})
    content.append({"type": "text", "text": prompt})
    body = {"model": model, "messages": [{"role": "user", "content": content}]}
    if size:
        body["size"] = size
    data = _post(f"{TH_BASE}/wand/hunyuan-image/v35-generation", _bearer(key), body,
                 what="混元生图 3.5", log=log)
    url = _dig(data, "choices.0.delta.image.url")
    if not url:
        raise ProviderError("响应里没有图片地址", json.dumps(data, ensure_ascii=False)[:2000])
    return [_save_image({"url": url}, stamp("img_混元", ".png"), log, "混元")]


def th_video(model, prompt, images, key, *, log, cancel, options) -> str:
    from .providers_util import stamp

    log = _log(log)
    body: dict[str, Any] = {"model": model, "prompt": prompt}
    if images:
        body["image_url"] = _data_url(images[0])
    else:
        body["aspect_ratio"] = _ratio(options.get("size") or "")
    data = _post(f"{TH_BASE}/wand/hunyuan-video/generation", _bearer(key), body,
                 what="混元生视频任务提交", log=log)
    task_id = data.get("task_id")
    if not task_id:
        raise ProviderError("没有拿到 task_id", json.dumps(data, ensure_ascii=False)[:2000])

    def fetch():
        return net.request("GET", f"{TH_BASE}/wand/hunyuan-video/tasks/{task_id}",
                           headers=_bearer(key), timeout=60, log=log)

    def failed(d):
        if d.get("status") == "failed":
            err = d.get("error") or {}
            return f"{err.get('code')} {err.get('message')}".strip() or "failed"
        return None

    res = _poll(
        fetch,
        status_get=lambda d: d.get("status"),
        done=lambda d: d.get("status") == "succeeded",
        failed=failed,
        interval=float(options.get("poll_interval") or 4),
        timeout=float(options.get("poll_timeout", 1200)),
        log=log,
        cancel=cancel,
        task_id=task_id,
    )
    videos = res.get("videos") or []
    url = videos[0].get("url") if videos and isinstance(videos[0], dict) else None
    if not url:
        raise ProviderError("任务成功但没有视频地址", json.dumps(res, ensure_ascii=False)[:2000])
    return net.download(url, stamp("vid_混元", ".mp4"), log=log)


# ==================================================================== 智谱 GLM
# 文档：/api-reference 模型-api 对话补全 / 图像生成 / 视频生成异步 / 查询异步结果
ZP_BASE = "https://open.bigmodel.cn/api/paas/v4"


def zp_understand(model, prompt, images, key, *, log, cancel, options) -> str:
    log = _log(log)
    content: list[dict] = []
    for p in images:
        content.append({"type": "image_url", "image_url": {"url": _data_url(p)}})
    content.append({"type": "text", "text": prompt})
    body = {"model": model, "messages": [{"role": "user", "content": content}], "stream": False}
    data = _post(f"{ZP_BASE}/chat/completions", _bearer(key), body, what="智谱图像理解", log=log)
    content_out = _dig(data, "choices.0.message.content")
    if isinstance(content_out, list):
        text = "".join(part.get("text", "") for part in content_out if isinstance(part, dict))
    else:
        text = content_out or ""
    if not text:
        raise ProviderError("模型没有返回文本内容", json.dumps(data, ensure_ascii=False)[:2000])
    return text


ZP_SIZES = ["1280x1280", "1568x1056", "1056x1568", "1472x1088", "1088x1472", "1728x960", "960x1728"]


def zp_image(model, prompt, images, key, *, log, cancel, options) -> list[str]:
    from .providers_util import stamp

    log = _log(log)
    body: dict[str, Any] = {"model": model, "prompt": prompt, "watermark_enabled": False}
    size = (options.get("size") or "").strip()
    if size in ZP_SIZES:
        body["size"] = size
    elif size:
        log("warn", f"尺寸 {size} 不在智谱枚举内，改用默认 1280x1280（可选：{', '.join(ZP_SIZES)}）")
    if model == "glm-image":
        body["quality"] = "hd"
    data = _post(f"{ZP_BASE}/images/generations", _bearer(key), body, what="智谱图像生成", log=log)
    items = data.get("data") or []
    if not items:
        raise ProviderError("响应里没有 data 数组", json.dumps(data, ensure_ascii=False)[:2000])
    return [_save_image(it, stamp("img_智谱", ".png"), log, "智谱") for it in items]


ZP_VSIZES = ["1280x720", "720x1280", "1024x1024", "1920x1080", "1080x1920", "2048x1080", "3840x2160"]


def zp_video(model, prompt, images, key, *, log, cancel, options) -> str:
    from .providers_util import stamp

    log = _log(log)
    body: dict[str, Any] = {"model": model, "prompt": prompt}
    if model == "cogvideox-3":
        body["quality"] = "quality"
        size = (options.get("size") or "").strip()
        body["size"] = size if size in ZP_VSIZES else "1920x1080"
        duration = _int_or(options.get("duration"), 5)
        body["duration"] = 10 if duration >= 10 else 5
        body["fps"] = 30
    if images:
        body["image_url"] = _data_url(images[0])
    data = _post(f"{ZP_BASE}/videos/generations", _bearer(key), body, what="智谱视频任务提交", log=log)
    task_id = data.get("id")
    if not task_id:
        raise ProviderError("没有拿到任务 id", json.dumps(data, ensure_ascii=False)[:2000])

    def fetch():
        return net.request("GET", f"{ZP_BASE}/async-result/{task_id}",
                           headers=_bearer(key), timeout=60, log=log)

    def failed(d):
        st = d.get("task_status")
        if st == "FAIL":
            return json.dumps(d, ensure_ascii=False)[:800]
        return None

    res = _poll(
        fetch,
        status_get=lambda d: d.get("task_status"),
        done=lambda d: d.get("task_status") == "SUCCESS",
        failed=failed,
        interval=float(options.get("poll_interval") or 5),
        timeout=float(options.get("poll_timeout", 1200)),
        log=log,
        cancel=cancel,
        task_id=task_id,
    )
    url = _dig(res, "video_result.0.url")
    if not url:
        raise ProviderError("任务成功但没有视频地址", json.dumps(res, ensure_ascii=False)[:2000])
    return net.download(url, stamp("vid_智谱", ".mp4"), log=log)


# ==================================================================== 百度千帆
# 文档：/doc/qianfan-api/s/rm7u7qdiq（视觉）、8m7u6un8a（图像）、Emil7rnswy（文生视频）
QF_BASE = "https://qianfan.baidubce.com"


def qf_understand(model, prompt, images, key, *, log, cancel, options) -> str:
    log = _log(log)
    content: list[dict] = []
    for p in images:
        content.append({"type": "image_url", "image_url": {"url": _data_url(p)}})
    content.append({"type": "text", "text": prompt})
    body = {"model": model, "messages": [{"role": "user", "content": content}], "stream": False}
    data = _post(f"{QF_BASE}/v2/chat/completions", _bearer(key), body, what="千帆图像理解", log=log)
    text = _dig(data, "choices.0.message.content", "")
    if not text:
        raise ProviderError("模型没有返回文本内容", json.dumps(data, ensure_ascii=False)[:2000])
    return text if isinstance(text, str) else json.dumps(text, ensure_ascii=False)


def qf_image(model, prompt, images, key, *, log, cancel, options) -> list[str]:
    from .providers_util import stamp

    log = _log(log)
    size = (options.get("size") or "").strip()
    body: dict[str, Any] = {"model": model, "prompt": prompt}
    if size and "x" in size:
        body["size"] = size
    if options.get("n"):
        body["n"] = int(options["n"])
    if images:
        body["image"] = _data_url(images[0])
    path = "/v2/images/generations"
    if model.startswith("musesteamer"):
        path = "/v2/musesteamer/images/generations"
        body["response_format"] = "url"
    elif model.startswith("ernie-image"):
        path = "/v2/ernie-image/images/generations"
        body["watermark"] = False
    data = _post(f"{QF_BASE}{path}", _bearer(key), body, what="千帆图像生成", log=log)
    items = data.get("data") or []
    if not items:
        raise ProviderError("响应里没有 data 数组", json.dumps(data, ensure_ascii=False)[:2000])
    return [_save_image(it, stamp("img_千帆", ".png"), log, "千帆") for it in items]


def qf_video(model, prompt, images, key, *, log, cancel, options) -> str:
    """两套互不兼容的视频 API：蒸汽机 MuseSteamer 与千帆自研 K 系列。"""
    from .providers_util import stamp

    log = _log(log)
    timeout = float(options.get("poll_timeout", 1200))

    if model.upper().startswith("K"):
        # 千帆自研 K 系列（K3.0 / K2.6 / K2.5-Turbo）
        body = {
            "model": model,
            "type": "text2video",
            "model_parameters": {
                "prompt": prompt,
                "mode": "pro" if (options.get("resolution") or "").upper() in ("1080P", "2K") else "std",
                "aspect_ratio": _ratio(options.get("size") or ""),
                "duration": str(_int_or(options.get("duration"), 5)),
                "sound": "off",
            },
        }
        data = _post(f"{QF_BASE}/beta/video/generations/qianfan-video", _bearer(key), body,
                     what="千帆K系列视频提交", log=log)
        task_id = _dig(data, "data.task_id")
        if not task_id:
            raise ProviderError("没有拿到 task_id", json.dumps(data, ensure_ascii=False)[:2000])

        def fetch_k():
            return net.request(
                "GET",
                f"{QF_BASE}/beta/video/generations/qianfan-video?task_id={task_id}&model={model}",
                headers=_bearer(key), timeout=60, log=log,
            )

        res = _poll(
            fetch_k,
            status_get=lambda d: _dig(d, "data.task_status"),
            done=lambda d: _dig(d, "data.task_status") == "succeed",
            failed=lambda d: _dig(d, "data.task_status_msg") if _dig(d, "data.task_status") == "failed" else None,
            interval=float(options.get("poll_interval") or 10), timeout=timeout,
            log=log, cancel=cancel, task_id=task_id,
        )
        url = _dig(res, "data.task_result.videos.0.url")
    else:
        # 百度蒸汽机 MuseSteamer
        content: list[dict] = [{"type": "text", "text": prompt}]
        for p in images:
            content.append({"type": "image_url", "image_url": {"url": _data_url(p)}})
        body = {"model": model, "content": content}
        data = _post(f"{QF_BASE}/video/generations", _bearer(key), body,
                     what="蒸汽机视频提交", log=log)
        task_id = data.get("task_id")
        if not task_id:
            raise ProviderError("没有拿到 task_id", json.dumps(data, ensure_ascii=False)[:2000])

        def fetch_m():
            return net.request("GET", f"{QF_BASE}/video/generations?task_id={task_id}",
                               headers=_bearer(key), timeout=60, log=log)

        res = _poll(
            fetch_m,
            status_get=lambda d: d.get("status"),
            done=lambda d: d.get("status") == "succeeded",
            failed=lambda d: (d.get("error") or {}).get("message") if d.get("status") == "failed" else None,
            interval=float(options.get("poll_interval") or 10), timeout=timeout,
            log=log, cancel=cancel, task_id=task_id,
        )
        url = _dig(res, "content.video_url")

    if not url:
        raise ProviderError("任务成功但没有视频地址", json.dumps(res, ensure_ascii=False)[:2000])
    return net.download(url, stamp("vid_千帆", ".mp4"), log=log)


# ================================================================== MiniMax
# 文档：/docs/api-reference/text-openai-api、image-generation-t2i、video-generation-v2-create
MM_BASE = "https://api.minimax.cn"


def _mm_check(data: dict, what: str) -> None:
    """MiniMax 用 HTTP 200 + base_resp.status_code 表达业务错误，必须单独判。"""
    base = data.get("base_resp") or {}
    code = base.get("status_code")
    if code not in (None, 0):
        raise ProviderError(
            f"{what}失败：MiniMax 业务错误码 {code} — {base.get('status_msg', '')}",
            json.dumps(data, ensure_ascii=False)[:2000],
        )


def mm_understand(model, prompt, images, key, *, log, cancel, options) -> str:
    log = _log(log)
    content: list[dict] = [{"type": "text", "text": prompt}]
    for p in images:
        content.append({"type": "image_url", "image_url": {"url": _data_url(p)}})
    body = {"model": model, "messages": [{"role": "user", "content": content}],
            "max_completion_tokens": options.get("max_tokens", 2048)}
    data = _post(f"{MM_BASE}/v1/chat/completions", _bearer(key), body, what="MiniMax 图像理解", log=log)
    _mm_check(data, "MiniMax 图像理解")
    text = _dig(data, "choices.0.message.content", "")
    if not text:
        raise ProviderError("模型没有返回文本内容", json.dumps(data, ensure_ascii=False)[:2000])
    return text if isinstance(text, str) else json.dumps(text, ensure_ascii=False)


def mm_image(model, prompt, images, key, *, log, cancel, options) -> list[str]:
    from .providers_util import stamp

    log = _log(log)
    body: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "response_format": "url",
        "n": int(options.get("n") or 1),
        "prompt_optimizer": True,
    }
    size = (options.get("size") or "").strip()
    if ":" in size:
        body["aspect_ratio"] = size
    elif "x" in size:
        w, h = size.lower().split("x")[:2]
        body["width"], body["height"] = _int_or(w, 1024), _int_or(h, 1024)
    if options.get("seed") not in (None, ""):
        body["seed"] = int(options["seed"])
    data = _post(f"{MM_BASE}/v1/image_generation", _bearer(key), body, what="MiniMax 图像生成", log=log)
    _mm_check(data, "MiniMax 图像生成")
    urls = _dig(data, "data.image_urls") or []
    b64s = _dig(data, "data.image_base64") or []
    out: list[str] = []
    for u in urls:
        out.append(_save_image({"url": u}, stamp("img_MiniMax", ".png"), log, "MiniMax"))
    for b in b64s:
        out.append(_save_image({"b64_json": b}, stamp("img_MiniMax", ".png"), log, "MiniMax"))
    if not out:
        raise ProviderError("响应里没有图片", json.dumps(data, ensure_ascii=False)[:2000])
    return out


def mm_video(model, prompt, images, key, *, log, cancel, options) -> str:
    from .providers_util import stamp

    log = _log(log)
    content: list[dict] = [{"type": "text", "text": prompt}]
    for p in images:
        content.append({"type": "image_url", "image_url": {"url": _data_url(p)}, "role": "first_frame"})
    duration = _int_or(options.get("duration"), 5)
    resolution = (options.get("resolution") or "").upper() or "768P"
    if model.endswith("Max"):
        resolution = "768P" if resolution not in ("480P", "768P") else resolution
        duration = max(5, min(15, duration))
    else:
        resolution = "2K" if resolution in ("2K", "1080P") else "768P"
        duration = max(4, min(15, duration))
    body: dict[str, Any] = {
        "model": model,
        "content": content,
        "resolution": resolution,
        "duration": duration,
        "ratio": "adaptive" if images else _ratio(options.get("size") or ""),
    }
    data = _post(f"{MM_BASE}/v2/video_generation", _bearer(key), body,
                 what="MiniMax 视频任务提交", log=log)
    _mm_check(data, "MiniMax 视频任务提交")
    task_id = data.get("task_id")
    if not task_id:
        raise ProviderError("没有拿到 task_id", json.dumps(data, ensure_ascii=False)[:2000])

    def fetch():
        return net.request("GET", f"{MM_BASE}/v2/query/video_generation/{task_id}",
                           headers=_bearer(key), timeout=60, log=log)

    def failed(d):
        st = _dig(d, "task.status")
        if st in ("failed", "cancelled"):
            err = _dig(d, "task.error") or {}
            return f"{st}: {err.get('code')} {err.get('message')}".strip()
        return None

    res = _poll(
        fetch,
        status_get=lambda d: _dig(d, "task.status"),
        done=lambda d: _dig(d, "task.status") == "succeeded",
        failed=failed,
        interval=float(options.get("poll_interval") or 10),
        timeout=float(options.get("poll_timeout", 1200)),
        log=log,
        cancel=cancel,
        task_id=task_id,
    )
    url = _dig(res, "task.content.url")
    if not url:
        raise ProviderError("任务成功但没有视频地址", json.dumps(res, ensure_ascii=False)[:2000])
    return net.download(url, stamp("vid_MiniMax", ".mp4"), log=log)


# ============================================ 视频编辑 / 参考视频重绘（三种契约）
# 百炼：wan2.7-videoedit，media 里放 video + reference_image，标准 video-synthesis 异步任务
# 火山：Seedance 2.0/2.5，content 里放 video_url（公网 URL / asset://），可选 image_url 参考
# MiniMax：H3，content 里放 video_url + role=reference_video，可选 image_url 参考


def bl_video_edit(model, prompt, video_source, image_sources, key, *, log, cancel, options) -> str:
    from .media import image_ref, video_ref
    from .providers_util import stamp

    log = _log(log)
    headers = _bearer(key)
    headers["X-DashScope-Async"] = "enable"

    vurl, _how = video_ref("阿里百炼", video_source, log=log)
    media = [{"type": "video", "url": vurl}]
    for src in image_sources:
        iurl, _ = image_ref("阿里百炼", src, log=log)
        media.append({"type": "reference_image", "url": iurl})

    params: dict[str, Any] = {"prompt_extend": True, "watermark": False}
    if options.get("resolution"):
        params["resolution"] = options["resolution"]
    if options.get("duration"):
        params["duration"] = _int_or(options["duration"], 5)
    if options.get("seed") not in (None, ""):
        params["seed"] = int(options["seed"])

    body = {"model": model, "input": {"prompt": prompt, "media": media}, "parameters": params}
    data = _post(f"{BL_BASE}/api/v1/services/aigc/video-generation/video-synthesis",
                 headers, body, what="百炼视频编辑提交", log=log)
    task_id = _dig(data, "output.task_id")
    if not task_id:
        raise ProviderError("没有拿到 task_id", json.dumps(data, ensure_ascii=False)[:2000])

    def fetch():
        return net.request("GET", f"{BL_BASE}/api/v1/tasks/{task_id}",
                           headers=_bearer(key), timeout=60, log=log)

    def failed(d):
        st = _dig(d, "output.task_status")
        if st in ("FAILED", "CANCELED", "UNKNOWN"):
            return f"{st}: {_dig(d, 'output.code')} {_dig(d, 'output.message')}".strip()
        return None

    res = _poll(fetch, status_get=lambda d: _dig(d, "output.task_status"),
                done=lambda d: _dig(d, "output.task_status") == "SUCCEEDED",
                failed=failed, interval=float(options.get("poll_interval") or 15),
                timeout=float(options.get("poll_timeout", 1800)),
                log=log, cancel=cancel, task_id=task_id)
    url = _dig(res, "output.video_url")
    if not url:
        raise ProviderError("任务成功但没有 video_url", json.dumps(res, ensure_ascii=False)[:2000])
    return net.download(url, stamp("edit_百炼", ".mp4"), log=log)


def ark_video_edit(model, prompt, video_source, image_sources, key, *, log, cancel, options) -> str:
    from .media import image_ref, is_url, upload_ark_file
    from .providers_util import stamp

    log = _log(log)
    image_parts: list[dict] = []
    for src in image_sources:
        iurl, _ = image_ref("火山方舟", src, log=log)
        image_parts.append({"type": "image_url", "image_url": {"url": iurl},
                            "role": "reference_image"})

    # 参考视频：公网 URL 直接用；本地文件先传方舟 Files API 拿 file id，
    # 再依次试 "file id 直传" 和 "asset://<file id>" —— 官方文档只写了"URL / 素材 ID"，
    # 本地文件这一路没有明确示例，所以两种写法都试，哪种被受理就用哪种。
    if is_url(video_source):
        refs = [(video_source, "公网 URL")]
    else:
        fid = upload_ark_file(video_source, key, log=log)
        refs = [(fid, "file id 直传"), (f"asset://{fid}", "asset:// + file id")]

    base_body: dict[str, Any] = {"model": model, "watermark": False}
    if options.get("size"):
        base_body["ratio"] = _ratio(options["size"])
    if options.get("duration"):
        base_body["duration"] = _int_or(options["duration"], 5)

    data = None
    for idx, (ref, label) in enumerate(refs, 1):
        base_body["content"] = ([{"type": "text", "text": prompt},
                                 {"type": "video_url", "video_url": {"url": ref}}] + image_parts)
        try:
            data = _post(f"{ARK_BASE}/contents/generations/tasks", _bearer(key), base_body,
                         what="火山视频编辑提交", log=log)
            log("info", f"参考视频引用方式被受理：{label}")
            break
        except ProviderError as e:
            msg = str(e)
            if any(k in msg for k in ("ModelNotOpen", "not activated", "ModelNotFound")):
                raise   # 账号没开通模型，跟引用格式无关
            if idx == len(refs):
                raise
            log("warn", f"{label} 未被接受，换下一种写法：{msg[:140]}")

    task_id = (data or {}).get("id")
    if not task_id:
        raise ProviderError("没有拿到任务 id", json.dumps(data, ensure_ascii=False)[:2000])

    def fetch():
        return net.request("GET", f"{ARK_BASE}/contents/generations/tasks/{task_id}",
                           headers=_bearer(key), timeout=60, log=log)

    def failed(d):
        st = d.get("status")
        if st in ("failed", "expired", "cancelled"):
            err = d.get("error") or {}
            return f"{st}: {err.get('code')} {err.get('message')}".strip()
        return None

    res = _poll(fetch, status_get=lambda d: d.get("status"),
                done=lambda d: d.get("status") == "succeeded",
                failed=failed, interval=float(options.get("poll_interval") or 10),
                timeout=float(options.get("poll_timeout", 1800)),
                log=log, cancel=cancel, task_id=task_id)
    url = _dig(res, "content.video_url")
    if not url:
        raise ProviderError("任务成功但没有 video_url", json.dumps(res, ensure_ascii=False)[:2000])
    return net.download(url, stamp("edit_火山", ".mp4"), log=log)


def mm_video_edit(model, prompt, video_source, image_sources, key, *, log, cancel, options) -> str:
    from .media import image_ref, video_ref
    from .providers_util import stamp

    log = _log(log)
    vurl, _how = video_ref("MiniMax", video_source, log=log)
    content: list[dict] = [{"type": "text", "text": prompt},
                           {"type": "video_url", "video_url": {"url": vurl},
                            "role": "reference_video"}]
    for src in image_sources:
        iurl, _ = image_ref("MiniMax", src, log=log)
        content.append({"type": "image_url", "image_url": {"url": iurl},
                        "role": "reference_image"})

    duration = _int_or(options.get("duration"), 6)
    duration = max(4, min(15, duration))
    resolution = (options.get("resolution") or "768P").upper()
    if resolution not in ("768P", "2K"):
        resolution = "768P"
    body: dict[str, Any] = {
        "model": model,
        "content": content,
        "resolution": resolution,
        "duration": duration,
        "ratio": _ratio(options.get("size") or "") if not options.get("keep_ratio") else "adaptive",
    }
    data = _post(f"{MM_BASE}/v2/video_generation", _bearer(key), body,
                 what="MiniMax 视频编辑提交", log=log)
    _mm_check(data, "MiniMax 视频编辑提交")
    task_id = data.get("task_id")
    if not task_id:
        raise ProviderError("没有拿到 task_id", json.dumps(data, ensure_ascii=False)[:2000])

    def fetch():
        return net.request("GET", f"{MM_BASE}/v2/query/video_generation/{task_id}",
                           headers=_bearer(key), timeout=60, log=log)

    def failed(d):
        st = _dig(d, "task.status")
        if st in ("failed", "cancelled"):
            err = _dig(d, "task.error") or {}
            return f"{st}: {err.get('code')} {err.get('message')}".strip()
        return None

    res = _poll(fetch, status_get=lambda d: _dig(d, "task.status"),
                done=lambda d: _dig(d, "task.status") == "succeeded",
                failed=failed, interval=float(options.get("poll_interval") or 10),
                timeout=float(options.get("poll_timeout", 1800)),
                log=log, cancel=cancel, task_id=task_id)
    url = _dig(res, "task.content.url")
    if not url:
        raise ProviderError("任务成功但没有视频地址", json.dumps(res, ensure_ascii=False)[:2000])
    return net.download(url, stamp("edit_MiniMax", ".mp4"), log=log)
