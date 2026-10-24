"""后台任务：threading 版（Android 上没有 PyQt，用回调 + Kivy 的 Clock 回主线程）。

与桌面版 core/tasks.py 的能力一一对应，只是把 pyqtSignal 换成普通回调。
"""
from __future__ import annotations

import threading
import traceback
from typing import Any, Callable, Optional

from . import providers
from .analysis import parse_analysis


class Runner(threading.Thread):
    """在后台线程里跑一次能力调用。

    on_log(level, msg) / on_progress(percent, text) / on_done(payload) / on_fail(message, detail)
    这四个回调由界面层负责切回主线程（Kivy 用 Clock.schedule_once）。
    """

    daemon = True

    def __init__(
        self,
        kind: str,
        platform: str,
        model: str,
        api_key: str,
        *,
        prompt: str = "",
        images: Optional[list[str]] = None,
        options: Optional[dict] = None,
        video_source: str = "",
        on_log: Optional[Callable[[str, str], None]] = None,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_done: Optional[Callable[[dict], None]] = None,
        on_fail: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        super().__init__()
        self.kind = kind
        self.platform = platform
        self.model = model
        self.api_key = api_key
        self.prompt = prompt
        self.images = images or []
        self.options = options or {}
        self.video_source = video_source
        self._on_log = on_log or (lambda lvl, msg: None)
        self._on_progress = on_progress or (lambda pct, txt: None)
        self._on_done = on_done or (lambda payload: None)
        self._on_fail = on_fail or (lambda msg, detail: None)
        self._cancelled = False

    # providers 需要的两个回调
    def log(self, level: str, message: str) -> None:
        self._on_log(level, message)

    def cancelled(self) -> bool:
        return self._cancelled

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        try:
            self._dispatch()
        except providers.ProviderError as e:
            self._on_fail(str(e), getattr(e, "detail", "") or "")
        except Exception as e:  # 兜底：任何异常都要说清楚
            detail = traceback.format_exc()
            self._on_log("error", detail)
            self._on_fail(f"{e.__class__.__name__}: {e}", detail)

    def _dispatch(self) -> None:
        k = self.kind
        if k == "understand":
            self._on_progress(-1, "正在识别…")
            text = providers.understand(
                self.platform, self.model, self.prompt, self.images, self.api_key,
                log=self.log, cancel=self.cancelled, options=self.options,
            )
            self._finish({"text": text})

        elif k in ("image", "wf_image"):
            self._on_progress(-1, "正在生成图片…")
            files = providers.generate_image(
                self.platform, self.model, self.prompt, self.images[:1] if k == "image" else self.images,
                self.api_key, log=self.log, cancel=self.cancelled, options=self.options,
            )
            self._finish({"files": files, "prompt": self.prompt})

        elif k == "video":
            self._on_progress(-1, "正在提交视频任务…")
            path = providers.generate_video(
                self.platform, self.model, self.prompt, self.images[:1], self.api_key,
                log=self.log, cancel=self.cancelled, options=self.options,
            )
            self._finish({"file": path})

        elif k == "analyze":
            self._on_progress(-1, "分析参考图…")
            text = providers.understand(
                self.platform, self.model, self.prompt, self.images, self.api_key,
                log=self.log, cancel=self.cancelled, options=self.options,
            )
            if self._cancelled:
                return self._cancelled_fail()
            data = parse_analysis(text)
            if not data.get("parsed"):
                self.log("warn", "模型没有返回标准 JSON，已把整段文本当作视频提示词")
            self._finish(data)

        elif k == "video_edit":
            self._on_progress(-1, "正在提交视频编辑任务…")
            path = providers.generate_video_edit(
                self.platform, self.model, self.prompt, self.video_source, self.images,
                self.api_key, log=self.log, cancel=self.cancelled, options=self.options,
            )
            self._finish({"file": path})

        else:
            self._on_fail(f"未知任务类型: {k}", "")

    def _cancelled_fail(self) -> None:
        self._on_fail("已取消", "")

    def _finish(self, payload: dict[str, Any]) -> None:
        if self._cancelled:
            self._cancelled_fail()
            return
        self._on_done(payload)
