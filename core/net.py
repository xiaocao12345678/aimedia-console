"""HTTP 封装：统一超时、重试、脱敏和运行日志。

设计原则：任何一次外部请求都要在界面上留下记录（方法、URL、脱敏后的请求体、
状态码、耗时、错误原文），失败时保留完整响应体，便于定位是鉴权、配额还是参数问题。
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

import requests

LogFn = Callable[[str, str], None]  # (level, message)

_SENSITIVE_KEYS = {"authorization", "api_key", "apikey", "x-api-key", "token", "access_key"}


def mask(secret: str, keep: int = 4) -> str:
    if not secret:
        return "(空)"
    if len(secret) <= keep * 2:
        return "*" * len(secret)
    return f"{secret[:keep]}…{secret[-keep:]} (len={len(secret)})"


def mask_obj(obj: Any) -> Any:
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if str(k).lower() in _SENSITIVE_KEYS and isinstance(v, str):
                out[k] = mask(v)
            else:
                out[k] = mask_obj(v)
        return out
    if isinstance(obj, list):
        return [mask_obj(x) for x in obj]
    if isinstance(obj, str) and obj.startswith("data:") and ";base64," in obj:
        head, _, b64 = obj.partition(";base64,")
        return f"{head};base64,<{len(b64)} 字符的图片数据已省略>"
    if isinstance(obj, str) and len(obj) > 400:
        return obj[:200] + f"…(共 {len(obj)} 字符,已截断)"
    return obj


def dumps(obj: Any, limit: int = 1500) -> str:
    try:
        s = json.dumps(mask_obj(obj), ensure_ascii=False, indent=2)
    except Exception:
        s = repr(obj)
    if len(s) > limit:
        s = s[:limit] + f"\n…(已截断,原长 {len(s)})"
    return s


@dataclass
class Response:
    status: int = 0
    ok: bool = False
    json: Any = None
    text: str = ""
    elapsed: float = 0.0
    error: str = ""
    url: str = ""
    headers: dict = field(default_factory=dict)

    def brief(self) -> str:
        if self.error:
            return f"HTTP {self.status} {self.elapsed:.2f}s 错误: {self.error}"
        return f"HTTP {self.status} {self.elapsed:.2f}s"


class HttpError(RuntimeError):
    def __init__(self, message: str, response: Optional[Response] = None):
        super().__init__(message)
        self.response = response


def request(
    method: str,
    url: str,
    *,
    headers: Optional[dict] = None,
    json_body: Any = None,
    data: Any = None,
    timeout: float = 120.0,
    retries: int = 1,
    log: Optional[LogFn] = None,
    stream: bool = False,
) -> Response:
    log = log or (lambda level, msg: None)
    headers = dict(headers or {})
    payload_preview = dumps(json_body) if json_body is not None else (str(data)[:500] if data else "")
    log("request", f"→ {method} {url}")
    if payload_preview:
        log("request", f"  请求体: {payload_preview}")

    last = Response(url=url)
    for attempt in range(retries + 1):
        started = time.time()
        try:
            resp = requests.request(
                method,
                url,
                headers=headers,
                json=json_body,
                data=data if json_body is None else None,
                timeout=timeout,
                stream=stream,
            )
            elapsed = time.time() - started
            body = resp.text if not stream else ""
            parsed = None
            if body:
                try:
                    parsed = json.loads(body)
                except Exception:
                    parsed = None
            last = Response(
                status=resp.status_code,
                ok=resp.status_code < 400,
                json=parsed,
                text=body[:8000],
                elapsed=elapsed,
                url=url,
                headers=dict(resp.headers),
            )
            log("response", f"← {resp.status_code} {url} 用时 {elapsed:.2f}s")
            if body:
                preview = dumps(parsed) if parsed is not None else body[:1500]
                log("response", f"  响应: {preview}")
            if resp.status_code < 400:
                return last
            # 4xx 除 408/429 之外不重试
            if resp.status_code not in (408, 429) or attempt >= retries:
                last.error = _extract_error(parsed, body) or f"HTTP {resp.status_code}"
                return last
            log("warn", f"  状态 {resp.status_code}，{2 ** attempt}s 后重试")
            time.sleep(2 ** attempt)
        except requests.exceptions.Timeout as e:
            elapsed = time.time() - started
            last = Response(url=url, elapsed=elapsed, error=f"请求超时（{timeout:.0f}s）: {e}")
            log("error", f"✗ 超时 {url} 用时 {elapsed:.2f}s")
            if attempt >= retries:
                return last
        except requests.exceptions.RequestException as e:
            elapsed = time.time() - started
            last = Response(url=url, elapsed=elapsed, error=f"网络错误: {e.__class__.__name__}: {e}")
            log("error", f"✗ 网络错误 {url}: {e}")
            if attempt >= retries:
                return last
            time.sleep(1 + attempt)
    return last


def _extract_error(parsed: Any, body: str) -> str:
    if isinstance(parsed, dict):
        for path in (("error", "message"), ("error",), ("message",), ("msg",), ("Message",), ("code", "message")):
            cur: Any = parsed
            for key in path:
                if isinstance(cur, dict) and key in cur:
                    cur = cur[key]
                else:
                    cur = None
                    break
            if isinstance(cur, str) and cur:
                return cur
        err = parsed.get("error")
        if isinstance(err, dict):
            for key in ("code", "type", "message"):
                if isinstance(err.get(key), str):
                    return f"{err.get(key)}"
        if isinstance(err, str):
            return err
    return (body or "").strip()[:400]


def raise_for(resp: Response, what: str) -> Any:
    """非 2xx 直接抛 HttpError，附带原始响应，便于界面展示完整失败原因。"""
    if not resp.ok:
        raise HttpError(f"{what}失败：{resp.error or 'HTTP ' + str(resp.status)}", resp)
    return resp.json


def poll(
    fetch: Callable[[], Response],
    *,
    is_done: Callable[[Any], bool],
    is_failed: Callable[[Any], Optional[str]],
    interval: float = 5.0,
    timeout: float = 900.0,
    log: Optional[LogFn] = None,
    on_tick: Optional[Callable[[int, Any], None]] = None,
    cancel: Optional[Callable[[], bool]] = None,
) -> Any:
    """通用异步任务轮询。fetch() 返回 Response，is_done/is_failed 判定 json。"""
    log = log or (lambda level, msg: None)
    started = time.time()
    attempt = 0
    while True:
        attempt += 1
        if cancel and cancel():
            raise HttpError("任务已取消")
        resp = fetch()
        if not resp.ok and resp.status not in (0,) and attempt == 1:
            raise HttpError(f"轮询失败：{resp.error}", resp)
        data = resp.json if resp.ok else None
        if data is not None:
            fail = is_failed(data)
            if fail:
                raise HttpError(f"任务失败：{fail}", resp)
            if is_done(data):
                log("info", f"任务完成（第 {attempt} 次轮询，总耗时 {time.time() - started:.0f}s）")
                return data
        if on_tick:
            on_tick(attempt, data)
        waited = time.time() - started
        if waited > timeout:
            raise HttpError(f"任务超时（{timeout:.0f}s，已轮询 {attempt} 次）", resp)
        log("poll", f"  第 {attempt} 次轮询未完成，{interval:.0f}s 后再查（已等待 {waited:.0f}s）")
        time.sleep(interval)


def download(url: str, dest_path, log: Optional[LogFn] = None, timeout: float = 300.0) -> str:
    log = log or (lambda level, msg: None)
    log("info", f"下载结果文件: {url}")
    started = time.time()
    with requests.get(url, stream=True, timeout=timeout) as r:
        r.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                if chunk:
                    f.write(chunk)
    log("info", f"已保存 {dest_path}（{time.time() - started:.1f}s）")
    return str(dest_path)
