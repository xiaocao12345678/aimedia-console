"""独立运行日志窗口：非模态，可同时查看请求、响应、状态码、耗时与失败原因。

主窗口不再占着底部一条空间放日志；点标题栏「运行日志」打开这个窗口，
关掉后仍然保留历史，再次打开能接着看。
"""
from __future__ import annotations

import datetime as _dt
from pathlib import Path

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QFont, QGuiApplication
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from . import style
from .frameless import FrameHost, TitleBar

from core.paths import log_dir

LOG_DIR = log_dir()

LEVEL_COLORS = {
    "info": "#6fb1ff",
    "request": "#c79bff",
    "response": "#5fd39b",
    "warn": "#ffc16b",
    "error": "#ff8a8a",
    "poll": "#9aa7b4",
}

LEVEL_LABELS = {
    "all": "全部级别",
    "info": "信息",
    "request": "请求",
    "response": "响应",
    "poll": "轮询",
    "warn": "警告",
    "error": "错误",
}


class LogWindow(FrameHost, QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("运行日志")
        self.resize(1080, 640)
        self.install_frame()
        self.setStyleSheet(style.app_qss())

        shell = QVBoxLayout(self)
        shell.setContentsMargins(0, 0, 0, 0)
        root = QWidget()
        root.setObjectName("Root")
        shell.addWidget(root)

        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.titlebar = TitleBar(self, "运行日志 · 原始请求与响应", allow_maximize=False)
        outer.addWidget(self.titlebar)

        body = QVBoxLayout()
        body.setContentsMargins(14, 10, 14, 12)
        body.setSpacing(8)

        bar = QHBoxLayout()
        bar.setSpacing(8)
        self.badge = QLabel("就绪")
        self.badge.setObjectName("AppBadge")
        bar.addWidget(self.badge)

        bar.addWidget(QLabel("筛选"))
        self.level_filter = QComboBox()
        self.level_filter.setMaximumWidth(120)
        for key, label in LEVEL_LABELS.items():
            self.level_filter.addItem(label, userData=key)
        self.level_filter.currentIndexChanged.connect(self._rebuild)
        bar.addWidget(self.level_filter)

        self.autoscroll = QCheckBox("自动滚动")
        self.autoscroll.setChecked(True)
        bar.addWidget(self.autoscroll)
        bar.addStretch(1)

        copy_btn = QPushButton("复制全部")
        copy_btn.clicked.connect(self.copy_all)
        save_btn = QPushButton("另存为…")
        save_btn.clicked.connect(self.save_as)
        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self.clear)
        dir_btn = QPushButton("打开日志目录")
        dir_btn.clicked.connect(self.open_log_dir)
        for b in (copy_btn, save_btn, clear_btn, dir_btn):
            bar.addWidget(b)
        body.addLayout(bar)

        self.view = QPlainTextEdit()
        self.view.setObjectName("LogView")
        self.view.setReadOnly(True)
        self.view.setMaximumBlockCount(20000)
        font = QFont("Consolas")
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPointSize(9)
        self.view.setFont(font)
        body.addWidget(self.view, 1)

        self.hint = QLabel(
            "每条请求都会记下方法、URL、脱敏后的请求体、响应码与耗时；"
            "失败时保留平台返回的原始错误体。Key 只显示前 4 位。"
        )
        self.hint.setStyleSheet("color:#6b7683;font-size:11px;")
        body.addWidget(self.hint)

        outer.addLayout(body, 1)

        self._records: list[tuple[str, str, str]] = []  # (时间, 级别, 文本)
        self._badge_text = "就绪"
        self._badge_color = "#46515c"

    # ---------- 对外 ----------
    def append(self, level: str, message: str) -> None:
        stamp = _dt.datetime.now().strftime("%H:%M:%S")
        self._records.append((stamp, level, message))
        if len(self._records) > 8000:
            del self._records[:2000]
        if self._passes(level):
            self._emit_html(stamp, level, message)

    def set_state(self, text: str, color: str = "#46515c") -> None:
        self._badge_text = text
        self._badge_color = color
        self.badge.setText(text)
        self.badge.setStyleSheet(
            f"color:{color};font-size:11px;padding:2px 9px;"
            "border:1px solid rgba(148,170,196,0.55);border-radius:9px;"
            "background:rgba(255,255,255,0.55);"
        )

    def load_history(self, records: list[tuple[str, str, str]]) -> None:
        self._records = list(records)
        self._rebuild()

    # ---------- 内部 ----------
    def _passes(self, level: str) -> bool:
        want = self.level_filter.currentData()
        return want in (None, "all") or want == level

    def _emit_html(self, stamp: str, level: str, message: str) -> None:
        color = LEVEL_COLORS.get(level, "#d7dfe8")
        safe = (
            message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace("\n", "<br>").replace("  ", "&nbsp;&nbsp;")
        )
        self.view.appendHtml(
            f'<span style="color:#7d8590;">[{stamp}]</span> '
            f'<span style="color:{color};">{safe}</span>'
        )
        if self.autoscroll.isChecked():
            sb = self.view.verticalScrollBar()
            sb.setValue(sb.maximum())

    def _rebuild(self) -> None:
        self.view.clear()
        for stamp, level, message in self._records:
            if self._passes(level):
                self._emit_html(stamp, level, message)
        self.set_state(self._badge_text, self._badge_color)

    def copy_all(self) -> None:
        QGuiApplication.clipboard().setText(self.view.toPlainText())

    def save_as(self) -> None:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        default = LOG_DIR / f"run_{_dt.datetime.now():%Y%m%d_%H%M%S}.log"
        path, _ = QFileDialog.getSaveFileName(self, "保存运行日志", str(default), "日志 (*.log *.txt)")
        if path:
            Path(path).write_text(self.view.toPlainText(), encoding="utf-8")

    def clear(self) -> None:
        self._records.clear()
        self.view.clear()

    def open_log_dir(self) -> None:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(LOG_DIR)))

    def closeEvent(self, event):  # noqa: N802
        # 关掉只是隐藏：继续接收日志，下次打开还在
        self.hide()
        event.ignore()
