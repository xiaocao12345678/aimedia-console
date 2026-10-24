"""主窗口：无边框玻璃窗 + 三分页任务 + 实时运行日志。

Key 不再在这里逐家填写，统一放到「平台密钥」界面（ui/key_manager.py）；
窗口顶部只负责选择"当前调用哪一家"。
"""
from __future__ import annotations

import datetime as _dt
import os
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QSize, QTimer, QUrl
from PyQt6.QtGui import QDesktopServices, QFont, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizeGrip,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core import error_hint, providers
from core.config import Config
from core.tasks import Task

from . import style
from .frameless import FrameHost, TitleBar
from .key_manager import KeyManagerDialog
from .log_window import LogWindow
from .video_edit_page import VideoEditPage
from .workflow_page import WorkflowPage

APP_TITLE = "AI 多模态控制台"

LEVEL_COLORS = {
    "info": "#6fb1ff",
    "request": "#c79bff",
    "response": "#5fd39b",
    "warn": "#ffc16b",
    "error": "#ff8a8a",
    "poll": "#9aa7b4",
}

from core.paths import app_dir, log_dir, output_dir  # noqa: E402

BASE_DIR = app_dir()
OUTPUT_DIR = app_dir() / "output"
LOG_DIR = app_dir() / "logs"


def _now() -> str:
    return _dt.datetime.now().strftime("%H:%M:%S")


class ImagePicker(QWidget):
    """选图控件：列表 + 缩略图。"""

    def __init__(self, multiple: bool = True, label: str = "图片", parent=None) -> None:
        super().__init__(parent)
        self.multiple = multiple
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(QLabel(label))
        self.hint = QLabel("未选择")
        self.hint.setStyleSheet("color:#6b7683;")
        self.hint.setMinimumWidth(56)
        row.addWidget(self.hint, 1)
        add_btn = QPushButton("选择图片")
        add_btn.setObjectName("Primary")
        add_btn.clicked.connect(self.pick)
        rm_btn = QPushButton("移除选中")
        rm_btn.clicked.connect(self.remove_selected)
        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self.clear)
        row.addWidget(add_btn)
        row.addWidget(rm_btn)
        row.addWidget(clear_btn)
        layout.addLayout(row)

        self.list = QListWidget()
        self.list.setIconSize(QSize(44, 44))
        self.list.setMaximumHeight(84)
        layout.addWidget(self.list)

    def pick(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择图片", str(Path.home()),
            "图片文件 (*.png *.jpg *.jpeg *.webp *.bmp)"
        )
        if not files:
            return
        if not self.multiple:
            self.list.clear()
            files = files[:1]
        for f in files:
            item = QListWidgetItem(os.path.basename(f))
            pm = QPixmap(f)
            if not pm.isNull():
                item.setIcon(QIcon(pm.scaled(44, 44, Qt.AspectRatioMode.KeepAspectRatio,
                                             Qt.TransformationMode.SmoothTransformation)))
            item.setData(Qt.ItemDataRole.UserRole, f)
            item.setToolTip(f)
            self.list.addItem(item)
        self._sync_hint()

    def remove_selected(self) -> None:
        for item in self.list.selectedItems():
            self.list.takeItem(self.list.row(item))
        self._sync_hint()

    def clear(self) -> None:
        self.list.clear()
        self._sync_hint()

    def _sync_hint(self) -> None:
        n = self.list.count()
        self.hint.setText("未选择" if n == 0 else f"已选 {n} 张")

    def paths(self) -> list[str]:
        return [self.list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.list.count())]


class BasePage(QWidget):
    kind = ""

    def __init__(self, win: "MainWindow", parent=None) -> None:
        super().__init__(parent)
        self.win = win
        self.task: Optional[Task] = None
        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(14, 12, 14, 12)
        self.root.setSpacing(9)

    def build_header(self, hint: str) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(QLabel("模型"))
        self.model_box = QComboBox()
        self.model_box.setEditable(True)
        self.model_box.setMinimumWidth(380)
        # 下拉列表要比输入框宽，否则「ID · 说明」会被截断
        self.model_box.view().setMinimumWidth(640)
        if self.model_box.lineEdit() is not None:
            self.model_box.lineEdit().setAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
        self.model_box.setToolTip("可从列表选择，也可直接输入新的模型 ID")
        row.addWidget(self.model_box)
        self.refresh_btn = QPushButton("刷新模型")
        self.refresh_btn.clicked.connect(self.reload_models)
        row.addWidget(self.refresh_btn)
        row.addSpacing(6)
        tip = QLabel(hint)
        tip.setStyleSheet("color:#6b7683;font-size:11px;")
        row.addWidget(tip)
        row.addStretch(1)

        self.progress = QProgressBar()
        self.progress.setMaximumWidth(210)
        self.progress.setTextVisible(True)
        self.progress.setFormat("空闲")
        self.progress.setValue(0)
        row.addWidget(self.progress)

        self.run_btn = QPushButton("开始")
        self.run_btn.setObjectName("Primary")
        self.run_btn.setMinimumWidth(104)
        self.run_btn.clicked.connect(self.start)
        row.addWidget(self.run_btn)

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setMinimumWidth(76)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel)
        row.addWidget(self.cancel_btn)
        return row

    def current_model(self) -> str:
        """优先取 itemData（真实模型 ID），手输时回退解析显示文本。"""
        data = self.model_box.currentData()
        if data:
            return str(data).strip()
        text = self.model_box.currentText().strip()
        return text.split("  ·  ")[0].strip()

    def reload_models(self) -> None:
        platform = self.win.platform()
        models = providers.models_for(platform, self.kind)
        current = self.current_model()
        self.model_box.blockSignals(True)
        self.model_box.clear()
        for model_id, note in models:
            self.model_box.addItem(f"{model_id}  ·  {note}", userData=model_id)
        saved = self.win.config.get_model(platform, self.kind)
        pick = current or saved or (models[0][0] if models else "")
        if pick:
            idx = self.model_box.findData(pick)
            if idx >= 0:
                self.model_box.setCurrentIndex(idx)
            else:
                self.model_box.setEditText(pick)
        self.model_box.setToolTip(
            f"{providers.capability_label(self.kind)}可用模型 {len(models)} 个；"
            "可从列表选择，也可直接输入新的模型 ID"
        )
        self.model_box.blockSignals(False)

    def start(self) -> None:
        raise NotImplementedError

    def cancel(self) -> None:
        if self.task and self.task.isRunning():
            self.task.cancel()
            self.win.append_log("warn", "已请求取消，等待当前请求返回…")

    def busy(self, on: bool, text: str = "") -> None:
        self.run_btn.setEnabled(not on)
        self.cancel_btn.setEnabled(on)
        self.refresh_btn.setEnabled(not on)
        self.model_box.setEnabled(not on)
        for w in self.extra_locks():
            w.setEnabled(not on)
        if on:
            self.progress.setRange(0, 0)
            self.progress.setFormat(text or "运行中…")
        else:
            self.progress.setRange(0, 100)
            self.progress.setValue(0)
            self.progress.setFormat("空闲")

    def extra_locks(self) -> list[QWidget]:
        return []

    def make_task(self, kind_override: str | None = None, images: list[str] | None = None,
                  options: dict | None = None) -> Optional[Task]:
        platform = self.win.platform()
        key = self.win.api_key()
        if not key:
            ret = QMessageBox.question(
                self, "缺少 API Key",
                f"「{platform}」还没有配置 API Key。\n\n现在打开密钥管理界面吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if ret == QMessageBox.StandardButton.Yes:
                self.win.open_key_manager()
            return None
        model = self.current_model()
        if not model:
            QMessageBox.warning(self, "缺少模型", "请选择或输入模型 ID。")
            return None
        self.win.config.set_model(platform, self.kind, model)
        task = Task(
            kind_override or self.kind, platform, model, key,
            prompt=self.prompt_text(),
            images=images or [], options=options or {},
        )
        task.sig_log.connect(self.win.append_log)
        task.sig_done.connect(self.on_done)
        task.sig_fail.connect(self.on_fail)
        task.sig_progress.connect(self.on_progress)
        task.finished.connect(lambda: self.busy(False))
        self.task = task
        return task

    def on_progress(self, percent: int, text: str) -> None:
        if percent < 0:
            self.progress.setRange(0, 0)
        else:
            self.progress.setRange(0, 100)
            self.progress.setValue(percent)
        if text:
            self.progress.setFormat(text)

    def on_fail(self, message: str, detail: str) -> None:
        self.win.append_log("error", f"任务失败：{message}")
        if detail:
            self.win.append_log("error", detail)
        full = error_hint.decorate(message, self.current_platform())
        if full != message:
            self.win.append_log("info", full.split("\n\n", 1)[-1])
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFormat("失败")
        self.win.set_run_state("失败", style.ERR)
        QMessageBox.critical(self, "任务失败", full)

    def on_done(self, payload: dict) -> None:
        raise NotImplementedError

    def prompt_text(self) -> str:
        return ""


class UnderstandPage(BasePage):
    kind = "understand"

    def __init__(self, win, parent=None) -> None:
        super().__init__(win, parent)
        self.root.addLayout(self.build_header("每张图单独提问，可一次选多张"))

        self.picker = ImagePicker(multiple=True, label="待识别图片")
        self.root.addWidget(self.picker)

        box = QGroupBox("提问 / 指令")
        v = QVBoxLayout(box)
        self.prompt = QPlainTextEdit()
        self.prompt.setPlaceholderText("例如：逐条列出画面里的设备名称、状态与可见缺陷；不确定的标注“不确定”。")
        self.prompt.setPlainText("请详细描述这张图片：主体、文字（逐字抄录）、场景、可判断的状态与异常。")
        self.prompt.setMaximumHeight(84)
        v.addWidget(self.prompt)
        self.root.addWidget(box)

        out_box = QGroupBox("识别结果")
        ov = QVBoxLayout(out_box)
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("结果会显示在这里，可全选复制。")
        ov.addWidget(self.output)
        row = QHBoxLayout()
        row.addStretch(1)
        self.save_btn = QPushButton("另存为文本…")
        self.save_btn.clicked.connect(self.save_text)
        row.addWidget(self.save_btn)
        ov.addLayout(row)
        self.root.addWidget(out_box, 1)

    def extra_locks(self) -> list[QWidget]:
        return [self.picker, self.prompt]

    def prompt_text(self) -> str:
        return self.prompt.toPlainText().strip()

    def start(self) -> None:
        images = self.picker.paths()
        if not images:
            QMessageBox.information(self, "还没有图片", "请先选择至少一张图片。")
            return
        if not self.prompt_text():
            QMessageBox.information(self, "还没有问题", "请填写要问的问题或指令。")
            return
        task = self.make_task(images=images, options={"max_tokens": 2048})
        if not task:
            return
        self.busy(True, "识别中…")
        self.win.set_run_state("运行中", style.ACCENT)
        self.win.append_log("info", f"开始识别：{self.win.platform()} / {task.model} / {len(images)} 张图")
        task.start()

    def on_done(self, payload: dict) -> None:
        text = payload.get("text") or "(模型返回空内容)"
        self.output.setPlainText(text)
        self.win.append_log("info", f"识别完成，输出 {len(text)} 字符")
        self.win.set_run_state("完成", style.OK)

    def save_text(self) -> None:
        if not self.output.toPlainText().strip():
            return
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        default = OUTPUT_DIR / f"识别_{_dt.datetime.now():%Y%m%d_%H%M%S}.txt"
        path, _ = QFileDialog.getSaveFileName(self, "保存识别结果", str(default), "文本 (*.txt)")
        if path:
            Path(path).write_text(self.output.toPlainText(), encoding="utf-8")
            self.win.append_log("info", f"已保存 {path}")


class ImageGenPage(BasePage):
    kind = "image"

    def __init__(self, win, parent=None) -> None:
        super().__init__(win, parent)
        self.root.addLayout(self.build_header("文生图 / 图生图"))

        box = QGroupBox("提示词")
        v = QVBoxLayout(box)
        self.prompt = QPlainTextEdit()
        self.prompt.setPlaceholderText("描述要生成的画面；需要图生图时在下方选一张参考图。")
        self.prompt.setMaximumHeight(92)
        v.addWidget(self.prompt)
        self.root.addWidget(box)

        opt = QHBoxLayout()
        opt.setSpacing(14)
        self.picker = ImagePicker(multiple=False, label="参考图（可选）")
        self.picker.setMaximumWidth(430)
        opt.addWidget(self.picker, 1)

        form = QGridLayout()
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)
        form.addWidget(QLabel("尺寸 / 比例"), 0, 0)
        self.size_box = QComboBox()
        self.size_box.setEditable(True)
        self.size_box.setMaximumWidth(160)
        self.size_box.addItems(["1024x1024", "1280x720", "720x1280", "1024x1536",
                                "1536x1024", "1328x1328", "4:3", "16:9", "9:16"])
        form.addWidget(self.size_box, 0, 1)
        form.addWidget(QLabel("生成数量"), 0, 2)
        self.count = QSpinBox()
        self.count.setRange(1, 4)
        self.count.setValue(1)
        self.count.setToolTip(
            "各家支持数量不同：火山 / 百炼 / MiniMax 支持多张；智谱 glm-image 每次只返回 1 张。"
        )
        form.addWidget(self.count, 0, 3)
        form.addWidget(QLabel("随机种子"), 1, 0)
        self.seed = QLineEdit()
        self.seed.setPlaceholderText("留空随机")
        form.addWidget(self.seed, 1, 1)
        opt.addLayout(form, 1)
        self.root.addLayout(opt)

        out_box = QGroupBox("生成结果")
        ov = QVBoxLayout(out_box)
        bar = QHBoxLayout()
        self.status = QLabel("尚未生成")
        self.status.setStyleSheet("color:#6b7683;")
        bar.addWidget(self.status, 1)
        self.open_dir_btn = QPushButton("打开输出目录")
        self.open_dir_btn.clicked.connect(self.open_output)
        bar.addWidget(self.open_dir_btn)
        ov.addLayout(bar)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.canvas = QWidget()
        self.grid = QGridLayout(self.canvas)
        self.grid.setSpacing(10)
        self.scroll.setWidget(self.canvas)
        ov.addWidget(self.scroll, 1)
        self.root.addWidget(out_box, 1)
        self.files: list[str] = []

    def extra_locks(self) -> list[QWidget]:
        return [self.picker, self.prompt, self.size_box, self.count, self.seed]

    def prompt_text(self) -> str:
        return self.prompt.toPlainText().strip()

    def start(self) -> None:
        if not self.prompt_text():
            QMessageBox.information(self, "还没有提示词", "请填写要生成的画面描述。")
            return
        options = {
            "size": self.size_box.currentText().strip(),
            "n": self.count.value(),
            "seed": self.seed.text().strip(),
        }
        if self.seed.text().strip():
            try:
                options["seed"] = int(self.seed.text().strip())
            except ValueError:
                QMessageBox.warning(self, "种子不合法", "随机种子必须是整数，或留空。")
                return
        task = self.make_task(images=self.picker.paths(), options=options)
        if not task:
            return
        self._clear_grid()
        self.busy(True, "生成中…")
        self.win.set_run_state("运行中", style.ACCENT)
        self.win.append_log("info", f"开始生图：{self.win.platform()} / {task.model} / {options}")
        task.start()

    def _clear_grid(self) -> None:
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def on_done(self, payload: dict) -> None:
        files = payload.get("files") or []
        self.files = files
        if not files:
            self.status.setText("没有拿到图片，请查看运行日志")
            return
        for i, f in enumerate(files):
            self._add_thumb(f, i)
        self.status.setText(f"已生成 {len(files)} 张 → {OUTPUT_DIR}")
        self.win.append_log("info", f"生图完成：{len(files)} 张")
        self.win.set_run_state("完成", style.OK)

    def _add_thumb(self, path: str, index: int) -> None:
        holder = QFrame()
        holder.setStyleSheet(
            "QFrame { background: rgba(255,255,255,0.45); border:1px solid rgba(255,255,255,0.7);"
            " border-radius: 12px; }"
        )
        v = QVBoxLayout(holder)
        v.setContentsMargins(8, 8, 8, 8)
        label = QLabel()
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("border: none; background: transparent;")
        pm = QPixmap(path)
        if pm.isNull():
            label.setText(f"无法预览\n{path}")
        else:
            label.setPixmap(pm.scaled(300, 300, Qt.AspectRatioMode.KeepAspectRatio,
                                      Qt.TransformationMode.SmoothTransformation))
        v.addWidget(label)
        name = QLabel(os.path.basename(path))
        name.setStyleSheet("color:#6b7683;font-size:11px;border:none;background:transparent;")
        name.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        v.addWidget(name)
        btn = QPushButton("打开图片")
        btn.clicked.connect(lambda _, p=path: QDesktopServices.openUrl(QUrl.fromLocalFile(p)))
        v.addWidget(btn)
        r, c = divmod(index, 3)
        self.grid.addWidget(holder, r, c)

    def open_output(self) -> None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(OUTPUT_DIR)))


class VideoGenPage(BasePage):
    kind = "video"

    def __init__(self, win, parent=None) -> None:
        super().__init__(win, parent)
        self.root.addLayout(self.build_header("文生视频 / 图生视频（异步任务）"))

        box = QGroupBox("提示词")
        v = QVBoxLayout(box)
        self.prompt = QPlainTextEdit()
        self.prompt.setPlaceholderText("按镜头脚本写：主体动作 → 外观细节 → 环境 → 机位与运镜 → 光线。")
        self.prompt.setMaximumHeight(96)
        v.addWidget(self.prompt)
        self.root.addWidget(box)

        row = QHBoxLayout()
        row.setSpacing(14)
        self.picker = ImagePicker(multiple=False, label="首帧图（可选）")
        self.picker.setMaximumWidth(430)
        row.addWidget(self.picker, 1)

        form = QGridLayout()
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)
        form.addWidget(QLabel("时长(秒)"), 0, 0)
        self.duration = QComboBox()
        self.duration.setEditable(True)
        self.duration.setMaximumWidth(130)
        self.duration.addItems(["5", "10", "15", "30"])
        form.addWidget(self.duration, 0, 1)
        form.addWidget(QLabel("分辨率"), 0, 2)
        self.resolution = QComboBox()
        self.resolution.setEditable(True)
        self.resolution.setMaximumWidth(130)
        self.resolution.addItems(["768P", "1080P", "2K", "4K"])
        form.addWidget(self.resolution, 0, 3)
        form.addWidget(QLabel("轮询间隔(秒)"), 1, 0)
        self.poll_interval = QSpinBox()
        self.poll_interval.setMaximumWidth(130)
        self.poll_interval.setRange(2, 60)
        self.poll_interval.setValue(5)
        form.addWidget(self.poll_interval, 1, 1)
        form.addWidget(QLabel("最长等待(分)"), 1, 2)
        self.poll_timeout = QSpinBox()
        self.poll_timeout.setMaximumWidth(130)
        self.poll_timeout.setRange(1, 120)
        self.poll_timeout.setValue(20)
        form.addWidget(self.poll_timeout, 1, 3)
        row.addLayout(form, 1)
        self.root.addLayout(row)

        out_box = QGroupBox("生成结果")
        ov = QVBoxLayout(out_box)
        self.status = QLabel("尚未生成")
        self.status.setStyleSheet("color:#6b7683;")
        self.status.setWordWrap(True)
        ov.addWidget(self.status)
        bar = QHBoxLayout()
        self.open_file_btn = QPushButton("打开视频")
        self.open_file_btn.setEnabled(False)
        self.open_file_btn.clicked.connect(self.open_video)
        self.open_dir_btn = QPushButton("打开输出目录")
        self.open_dir_btn.clicked.connect(self.open_output)
        bar.addWidget(self.open_file_btn)
        bar.addWidget(self.open_dir_btn)
        bar.addStretch(1)
        ov.addLayout(bar)
        self.preview = QLabel("视频生成通常需要 1–10 分钟，进度会逐条写入「运行日志」窗口（标题栏可打开）。")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setStyleSheet(
            "color:#6b7683;border:1px dashed rgba(255,255,255,0.85);border-radius:12px;"
            "background: rgba(255,255,255,0.25);padding:24px;"
        )
        self.preview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        ov.addWidget(self.preview, 1)
        self.root.addWidget(out_box, 1)
        self.last_file: Optional[str] = None

    def extra_locks(self) -> list[QWidget]:
        return [self.picker, self.prompt, self.duration, self.resolution,
                self.poll_interval, self.poll_timeout]

    def prompt_text(self) -> str:
        return self.prompt.toPlainText().strip()

    def start(self) -> None:
        if not self.prompt_text():
            QMessageBox.information(self, "还没有提示词", "请填写要生成的视频内容。")
            return
        options = {
            "duration": self.duration.currentText().strip(),
            "resolution": self.resolution.currentText().strip(),
            "poll_interval": self.poll_interval.value(),
            "poll_timeout": self.poll_timeout.value() * 60,
        }
        task = self.make_task(images=self.picker.paths(), options=options)
        if not task:
            return
        self.last_file = None
        self.open_file_btn.setEnabled(False)
        self.busy(True, "提交任务…")
        self.win.set_run_state("运行中", style.ACCENT)
        self.win.append_log("info", f"开始生视频：{self.win.platform()} / {task.model} / {options}")
        task.start()

    def on_done(self, payload: dict) -> None:
        path = payload.get("file")
        if not path:
            self.status.setText("任务结束但没有拿到视频文件，请查看日志")
            return
        self.last_file = path
        self.open_file_btn.setEnabled(True)
        size_mb = os.path.getsize(path) / (1024 * 1024) if os.path.exists(path) else 0
        self.status.setText(f"已保存：{path}（{size_mb:.2f} MB）")
        self.preview.setText("视频已就绪，点「打开视频」用系统播放器查看。")
        self.win.append_log("info", f"视频完成：{path}")
        self.win.set_run_state("完成", style.OK)

    def open_video(self) -> None:
        if self.last_file and os.path.exists(self.last_file):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.last_file))

    def open_output(self) -> None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(OUTPUT_DIR)))


class MainWindow(FrameHost, QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.config = Config()
        # 日志与状态：日志窗口懒创建，历史先存在这里
        self.log_window = None
        self._log_history: list[tuple[str, str, str]] = []
        self.run_state: tuple[str, str] = ("就绪", "#46515c")
        self.last_log_line = ""
        self.setWindowTitle(APP_TITLE)
        self.resize(1300, 900)
        self.setMinimumSize(1080, 720)
        self.install_frame()
        self.setStyleSheet(style.app_qss())

        shell = QVBoxLayout()
        shell.setContentsMargins(0, 0, 0, 0)
        host = QWidget()
        host.setObjectName("Shell")
        host.setAutoFillBackground(False)
        host.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        host.setLayout(shell)
        self.setCentralWidget(host)

        self.root = QWidget()
        self.root.setObjectName("Root")
        shell.addWidget(self.root)

        outer = QVBoxLayout(self.root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ---- 标题栏：平台选择 + 密钥管理入口 ----
        self.titlebar = TitleBar(self, APP_TITLE)
        self.titlebar.badge.setVisible(True)
        self.platform_box = QComboBox()
        self.platform_box.setMinimumWidth(140)
        for p in providers.platforms():
            self.platform_box.addItem(p)
        self.platform_box.currentTextChanged.connect(self._on_platform_changed)
        self.titlebar.add_widget(self.platform_box)

        self.console_btn = QPushButton("打开控制台")
        self.console_btn.clicked.connect(self.open_console)
        self.titlebar.add_widget(self.console_btn)

        self.log_btn = QPushButton("运行日志")
        self.log_btn.setToolTip("在新窗口查看完整请求与响应记录")
        self.log_btn.clicked.connect(self.open_log_window)
        self.titlebar.add_widget(self.log_btn)

        self.keys_btn = QPushButton("平台密钥")
        self.keys_btn.clicked.connect(self.open_key_manager)
        self.titlebar.add_widget(self.keys_btn)
        outer.addWidget(self.titlebar)

        # ---- 主体 ----
        body = QVBoxLayout()
        body.setContentsMargins(14, 10, 14, 10)
        body.setSpacing(8)

        self.tabs = QTabWidget()
        self.page_workflow = WorkflowPage(self)
        self.page_understand = UnderstandPage(self)
        self.page_image = ImageGenPage(self)
        self.page_video = VideoGenPage(self)
        self.page_video_edit = VideoEditPage(self)
        self.tabs.addTab(self.page_workflow, "参考图工作流")
        self.tabs.addTab(self.page_understand, "图像理解")
        self.tabs.addTab(self.page_image, "图像生成")
        self.tabs.addTab(self.page_video, "视频生成")
        self.tabs.addTab(self.page_video_edit, "视频编辑")
        self.tabs.currentChanged.connect(self._on_tab_changed)
        body.addWidget(self.tabs, 1)

        status_row = QHBoxLayout()
        status_row.setContentsMargins(0, 0, 0, 0)
        self.state_label = QLabel("")
        self.state_label.setTextFormat(Qt.TextFormat.RichText)
        self.state_label.setStyleSheet("font-size:11px;padding:2px 4px;color:#46515c;")
        status_row.addWidget(self.state_label, 1)
        self.size_grip = QSizeGrip(self.root)
        self.size_grip.setToolTip("拖动可调整窗口大小")
        status_row.addWidget(self.size_grip, 0, Qt.AlignmentFlag.AlignRight)
        body.addLayout(status_row)
        outer.addLayout(body, 1)

        self._refresh_key_badge()
        self._write_startup_note()
        self.append_log("info", f"{APP_TITLE} 已启动；输出目录 {OUTPUT_DIR}")
        self.append_log("info", "运行日志在新窗口中查看：标题栏「运行日志」")
        self.page_understand.reload_models()
        self._glass_logged = False

    # ---------- 平台与密钥 ----------
    def platform(self) -> str:
        return self.platform_box.currentText()

    def api_key(self) -> str:
        return self.config.get_key(self.platform())

    def _write_startup_note(self) -> None:
        """把启动关键信息写进 logs/startup.log：打包后排查"配置没读到"最省事。"""
        try:
            import sys

            from core.paths import app_dir, log_dir, resource_dir

            ready = sum(1 for p in providers.platforms() if self.config.has_key(p))
            lines = [
                f"--- {_dt.datetime.now():%Y-%m-%d %H:%M:%S} 启动 ---",
                f"frozen={bool(getattr(sys, 'frozen', False))}",
                f"exe_dir={app_dir()}",
                f"resource_dir={resource_dir()}",
                f"config={self.config.path} portable={self.config.portable}",
                f"keys={ready}/{len(providers.platforms())} 平台={','.join(p for p in providers.platforms() if self.config.has_key(p))}",
            ]
            with open(log_dir() / "startup.log", "a", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
        except Exception:
            pass

    def showEvent(self, event):  # noqa: N802
        super().showEvent(event)
        QTimer.singleShot(150, self._log_glass_method)

    def _log_glass_method(self) -> None:
        if getattr(self, "_glass_logged", False):
            return
        self._glass_logged = True
        self.append_log("info", f"玻璃背景：{self.acrylic_method_note()}")

    def acrylic_method_note(self) -> str:
        self._apply_glass()
        return {
            "accent-acrylic": "亚克力模糊（SetWindowCompositionAttribute · ACRYLICBLUR）",
            "accent-blur": "背景模糊（ACCENT_ENABLE_BLURBEHIND）",
            "dwm-acrylic": "Win11 亚克力（DWM SystemBackdrop）",
            "dwm-mica": "Win11 Mica（DWM SystemBackdrop）",
            "none": "系统模糊不可用，已退回实底",
        }.get(self.acrylic_method, self.acrylic_method)

    def _refresh_key_badge(self) -> None:
        ready = sum(1 for p in providers.platforms() if self.config.has_key(p))
        total = len(providers.platforms())
        current = self.platform()
        has = self.config.has_key(current)
        self.titlebar.badge.setText(f"密钥 {ready}/{total}")
        self.titlebar.badge.setToolTip("点击「平台密钥」集中填写与管理")
        self.keys_btn.setText("平台密钥 ●" if has else "平台密钥 ○")
        self.keys_btn.setToolTip(
            f"当前平台「{current}」{'已配置密钥' if has else '尚未配置密钥'}"
        )

    def _on_platform_changed(self, name: str) -> None:
        for page in (self.page_understand, self.page_image, self.page_video):
            page.reload_models()
        self._refresh_key_badge()
        self.append_log("info", f"已切换到「{name}」")

    def open_key_manager(self) -> None:
        dlg = KeyManagerDialog(self.config, self)
        dlg.keys_changed.connect(self._refresh_key_badge)
        dlg.exec()
        self._refresh_key_badge()
        self.page_workflow.refresh_key_states()
        for page in (self.page_understand, self.page_image, self.page_video):
            page.reload_models()

    def open_console(self) -> None:
        from .key_manager import ROWS

        for platform, _hint, url in ROWS:
            if platform == self.platform():
                QDesktopServices.openUrl(QUrl(url))
                self.append_log("info", f"在浏览器中打开「{platform}」控制台：{url}")
                return

    def show_status(self, text: str, msec: int = 4000) -> None:
        self.set_run_state(text, style.ACCENT)
        QTimer.singleShot(msec, lambda: self.set_run_state("就绪", "#46515c"))

    def _on_tab_changed(self, index: int) -> None:
        page = self.tabs.widget(index)
        if hasattr(page, "reload_models"):
            page.reload_models()
        if hasattr(page, "refresh_key_states"):
            page.refresh_key_states()

    def append_log(self, level: str, message: str) -> None:
        stamp = _dt.datetime.now().strftime("%H:%M:%S")
        self._log_history.append((stamp, level, message))
        if len(self._log_history) > 8000:
            del self._log_history[:2000]
        if self.log_window is not None:
            self.log_window.append(level, message)
        if message:
            self.last_log_line = message.splitlines()[0][:110]
            self._refresh_status()

    def set_run_state(self, text: str, color: str = "#46515c") -> None:
        """任务状态同时显示在主界面状态行和日志窗口角标。"""
        self.run_state = (text, color)
        if self.log_window is not None:
            self.log_window.set_state(text, color)
        self._refresh_status()

    def _refresh_status(self) -> None:
        state_text, state_color = getattr(self, "run_state", ("就绪", "#46515c"))
        last = getattr(self, "last_log_line", "")
        self.state_label.setText(f"<b style='color:{state_color}'>{state_text}</b>"
                                 f"<span style='color:#6b7683'> · {last}</span>")

    def open_log_window(self) -> None:
        if self.log_window is None:
            self.log_window = LogWindow(self)
            self.log_window.load_history(self._log_history)
            self.log_window.set_state(*getattr(self, "run_state", ("就绪", "#46515c")))
        self.log_window.show()
        self.log_window.raise_()
        self.log_window.activateWindow()

    # ---------- 窗口状态 ----------
    def on_max_state_changed(self) -> None:
        """FrameHost 在伪最大化/还原后回调这里。"""
        self.titlebar.sync_max_icon()
        maximized = self.is_pseudo_maximized()
        self.root.setProperty("maximized", "true" if maximized else "false")
        self.root.style().unpolish(self.root)
        self.root.style().polish(self.root)

    def closeEvent(self, event):  # noqa: N802
        for page in (self.page_workflow, self.page_understand,
                     self.page_image, self.page_video, self.page_video_edit):
            if page.task and page.task.isRunning():
                page.task.cancel()
                page.task.wait(2000)
        super().closeEvent(event)
