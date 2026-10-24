"""后台任务线程。界面线程只负责显示，所有网络请求都在这里跑。"""
from __future__ import annotations

import traceback
from typing import Any, Callable, Optional

from PyQt6.QtCore import QThread, pyqtSignal

from . import providers
from .analysis import parse_analysis


class Task(QThread):
    sig_log = pyqtSignal(str, str)      # level, message
    sig_done = pyqtSignal(object)       # result payload
    sig_fail = pyqtSignal(str, str)     # message, detail
    sig_progress = pyqtSignal(int, str)  # percent(-1 = 不确定), 状态文字

    def __init__(
        self,
        kind: str,
        platform: str,
        model: str,
        api_key: str,
        prompt: str = "",
        images: Optional[list[str]] = None,
        options: Optional[dict] = None,
        video_source: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.kind = kind
        self.platform = platform
        self.model = model
        self.api_key = api_key
        self.prompt = prompt
        self.images = images or []
        self.options = options or {}
        self.video_source = video_source
        self._cancelled = False

    # 供 providers 回调用
    def log(self, level: str, message: str) -> None:
        self.sig_log.emit(level, message)

    def cancelled(self) -> bool:
        return self._cancelled

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:  # noqa: D401
        try:
            if self.kind == "understand":
                self.sig_progress.emit(-1, "正在识别…")
                text = providers.understand(
                    self.platform, self.model, self.prompt, self.images, self.api_key,
                    log=self.log, cancel=self.cancelled, options=self.options,
                )
                if self._cancelled:
                    self.sig_fail.emit("已取消", "")
                    return
                self.sig_done.emit({"text": text})
            elif self.kind == "image":
                self.sig_progress.emit(-1, "正在生成图片…")
                files = providers.generate_image(
                    self.platform, self.model, self.prompt, self.images[:1], self.api_key,
                    log=self.log, cancel=self.cancelled, options=self.options,
                )
                if self._cancelled:
                    self.sig_fail.emit("已取消", "")
                    return
                self.sig_done.emit({"files": files})
            elif self.kind == "video":
                self.sig_progress.emit(-1, "正在提交视频任务…")
                path = providers.generate_video(
                    self.platform, self.model, self.prompt, self.images[:1], self.api_key,
                    log=self.log, cancel=self.cancelled, options=self.options,
                )
                if self._cancelled:
                    self.sig_fail.emit("已取消", "")
                    return
                self.sig_done.emit({"file": path})
            elif self.kind == "analyze":
                # 工作流第一步：理解参考图 + 需求 → 分析 / 视频提示词 / 生图提示词
                self.sig_progress.emit(-1, "分析参考图…")
                text = providers.understand(
                    self.platform, self.model, self.prompt, self.images, self.api_key,
                    log=self.log, cancel=self.cancelled, options=self.options,
                )
                if self._cancelled:
                    self.sig_fail.emit("已取消", "")
                    return
                data = parse_analysis(text)
                if not data.get("parsed"):
                    self.log("warn", "模型没有返回标准 JSON，已把整段文本当作视频提示词")
                self.sig_done.emit(data)
            elif self.kind == "video_edit":
                # 视频编辑 / 参考视频重绘：参考视频 + 可选参考图 + 指令
                self.sig_progress.emit(-1, "正在提交视频编辑任务…")
                path = providers.generate_video_edit(
                    self.platform, self.model, self.prompt, self.video_source,
                    self.images, self.api_key,
                    log=self.log, cancel=self.cancelled, options=self.options,
                )
                if self._cancelled:
                    self.sig_fail.emit("已取消", "")
                    return
                self.sig_done.emit({"file": path})
            elif self.kind == "wf_image":
                # 工作流第二步（可重复）：生成或修改视频参考图
                self.sig_progress.emit(-1, "生成参考图…")
                files = providers.generate_image(
                    self.platform, self.model, self.prompt, self.images, self.api_key,
                    log=self.log, cancel=self.cancelled, options=self.options,
                )
                if self._cancelled:
                    self.sig_fail.emit("已取消", "")
                    return
                self.sig_done.emit({"files": files, "prompt": self.prompt})
            else:
                self.sig_fail.emit(f"未知任务类型: {self.kind}", "")
        except providers.ProviderError as e:
            self.sig_fail.emit(str(e), getattr(e, "detail", "") or "")
        except Exception as e:  # 兜底：任何异常都要在界面上说清楚
            detail = traceback.format_exc()
            self.sig_log.emit("error", detail)
            self.sig_fail.emit(f"{e.__class__.__name__}: {e}", detail)
