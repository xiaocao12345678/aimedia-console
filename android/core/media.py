"""视频编辑要用的「素材输入」处理：本地文件怎么变成各平台能接受的引用。

三家要求不同（2026-10 核实）：
- 阿里百炼  media[].url：官方示例用公网 URL；DashScope 也接受 data: base64（小文件）
- 火山方舟  content.video_url.url：公网 URL 或 asset:// 素材 ID（不含 base64 说明）
- MiniMax   video_url.url：支持 data URL（≤50MB）或 mm_file://{file_id}

所以统一给两条路：能贴公网 URL 就贴 URL；只有本地文件时按平台转 base64，
超限或平台不支持时抛出可读错误，提示改用 URL。
"""
from __future__ import annotations

import mimetypes
import time
from pathlib import Path
from typing import Optional

import requests

ARK_FILES_URL = "https://ark.cn-beijing.volces.com/api/v3/files"

# 各平台单文件上限（MB）。超过就要求用公网 URL，避免把几十分钟视频塞进请求体。
BASE64_LIMIT_MB = {
    "阿里百炼": 10.0,
    "火山方舟": 8.0,
    "MiniMax": 40.0,
}

IMAGE_MAX_MB = 8.0


class MediaError(RuntimeError):
    pass


def is_url(value: str) -> bool:
    v = (value or "").strip().lower()
    return v.startswith("http://") or v.startswith("https://")


def file_size_mb(path: str) -> float:
    try:
        return Path(path).stat().st_size / (1024 * 1024)
    except OSError:
        return 0.0


def to_data_url(path: str, *, kind: str, limit_mb: float) -> str:
    """本地文件 → data URL。kind 用 'video' / 'image'。"""
    p = Path(path)
    if not p.is_file():
        raise MediaError(f"文件不存在：{path}")
    size = file_size_mb(path)
    if size > limit_mb:
        raise MediaError(
            f"{p.name} 有 {size:.1f} MB，超过该平台 base64 上限 {limit_mb:.0f} MB。"
            f"请改填可公网访问的视频 URL，或先压缩。"
        )
    mime = mimetypes.guess_type(p.name)[0]
    if not mime:
        mime = "video/mp4" if kind == "video" else "image/png"
    import base64

    with open(p, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def upload_ark_file(path: str, api_key: str, *, purpose: str = "user_data",
                    log=None, timeout: float = 300.0) -> str:
    """把本地文件传到火山方舟 Files API，返回 file id（形如 file-2026xxxx-xxxxx）。

    实测：上传接口不需要开通视频模型，返回 status=processing，通常几秒内变 active。
    文件会按平台策略过期（expire_at），所以不要长期拿它当永久引用。
    """
    log = log or (lambda lvl, msg: None)
    p = Path(path)
    if not p.is_file():
        raise MediaError(f"文件不存在：{path}")
    size_mb = file_size_mb(path)
    if size_mb > 512:
        raise MediaError(f"{p.name} 有 {size_mb:.0f} MB，超过方舟托管存储 512 MB 上限")

    log("info", f"上传到火山方舟 Files API：{p.name}（{size_mb:.1f} MB）")
    mime = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
    with open(p, "rb") as f:
        r = requests.post(
            ARK_FILES_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            files={"file": (p.name, f, mime)},
            data={"purpose": purpose},
            timeout=timeout,
        )
    if r.status_code >= 400:
        raise MediaError(f"上传失败：HTTP {r.status_code} {r.text[:300]}")
    data = r.json() or {}
    file_id = data.get("id")
    if not file_id:
        raise MediaError(f"上传响应里没有 id：{r.text[:300]}")
    log("info", f"上传成功 file_id={file_id} status={data.get('status')}")

    # 等预处理完成（active / processed），最多 ~30 秒
    for _ in range(10):
        if data.get("status") in ("active", "processed"):
            break
        time.sleep(3)
        rr = requests.get(f"{ARK_FILES_URL}/{file_id}",
                          headers={"Authorization": f"Bearer {api_key}"}, timeout=60)
        if rr.status_code < 400:
            data = rr.json() or {}
            log("info", f"  文件状态：{data.get('status')}")
            if data.get("status") in ("active", "processed"):
                break
    return file_id


def video_ref(platform: str, source: str, *, log=None) -> tuple[str, str]:
    """返回 (可直接提交的引用, 说明)。source 可以是本地路径或公网 URL。"""
    log = log or (lambda lvl, msg: None)
    src = (source or "").strip()
    if not src:
        raise MediaError("还没有选择参考视频")
    if is_url(src):
        log("info", f"参考视频用公网 URL：{src[:90]}")
        return src, "url"
    limit = BASE64_LIMIT_MB.get(platform, 8.0)
    if platform == "火山方舟":
        # 火山不吃 base64，但可以先上传到方舟文件服务拿 file id
        raise MediaError("需要先用 upload_ark_file 上传")
    data = to_data_url(src, kind="video", limit_mb=limit)
    log("info", f"参考视频转 base64：{Path(src).name}（{file_size_mb(src):.1f} MB）")
    return data, "base64"


def image_ref(platform: str, source: str, *, log=None) -> tuple[str, str]:
    log = log or (lambda lvl, msg: None)
    src = (source or "").strip()
    if not src:
        raise MediaError("参考图为空")
    if is_url(src):
        return src, "url"
    data = to_data_url(src, kind="image", limit_mb=IMAGE_MAX_MB)
    log("info", f"参考图转 base64：{Path(src).name}（{file_size_mb(src):.1f} MB）")
    return data, "base64"
