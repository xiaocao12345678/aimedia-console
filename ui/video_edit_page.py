"""视频编辑 / 参考视频重绘页：输入一段参考视频（+ 可选参考图），按指令生成新视频。

支持三家（各自的契约不同，程序自动处理）：
- 阿里百炼  wan2.7-videoedit：指令编辑、换装、风格迁移；media 里 video + reference_image
- 火山方舟  Seedance：参考视频重绘；视频只接受公网 URL 或平台素材 ID
- MiniMax   H3：多模态参考；视频可 base64（≤40MB）
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from core import error_hint, providers
from core.media import file_size_mb, is_url
from core.paths import output_dir
from core.tasks import Task

from .workflow_page import ModelRow

OUTPUT_DIR = output_dir()

PLATFORM_NOTES = {
    "阿里百炼": "本地视频 ≤10 MB 自动转 base64；更长的请填公网 URL。支持再给参考图做换装/换物。",
    "火山方舟": "本地视频会先上传到方舟文件服务（≤512 MB）再引用；也支持直接填公网 URL。",
    "MiniMax": "本地视频 ≤40 MB 自动转 base64；参考图同样支持本地或 URL。",
}

CARD_QSS = """
QFrame#Card {
    background: rgba(255, 255, 255, 0.55);
    border: 1px solid rgba(148, 170, 196, 0.45);
    border-radius: 12px;
}
QLabel#Hint { color: #6b7683; font-size: 11px; }
"""


class VideoEditPage(QWidget):
    def __init__(self, win) -> None:
        super().__init__()
        self.win = win
        self.config = win.config
        self.setStyleSheet(CARD_QSS)

        self.task: Optional[Task] = None
        self.video_path = ""
        self.image_paths: list[str] = []
        self.last_video: Optional[str] = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 10, 12, 10)
        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(self._build_left())
        split.addWidget(self._build_right())
        split.setSizes([470, 810])
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        outer.addWidget(split)

    # ---------------------------------------------------------------- 左：输入
    def _build_left(self) -> QWidget:
        panel = QWidget()
        panel.setMaximumWidth(500)
        v = QVBoxLayout(panel)
        v.setContentsMargins(0, 0, 6, 0)
        v.setSpacing(8)

        box1 = QGroupBox("① 参考视频（要改的那段）")
        b1 = QVBoxLayout(box1)
        b1.setSpacing(6)

        row1 = QHBoxLayout()
        self.pick_video_btn = QPushButton("选择本地视频")
        self.pick_video_btn.setObjectName("Primary")
        self.pick_video_btn.clicked.connect(self.pick_video)
        self.clear_video_btn = QPushButton("清除")
        self.clear_video_btn.clicked.connect(self.clear_video)
        self.video_hint = QLabel("未选择")
        self.video_hint.setObjectName("Hint")
        row1.addWidget(self.pick_video_btn)
        row1.addWidget(self.clear_video_btn)
        row1.addWidget(self.video_hint, 1)
        b1.addLayout(row1)

        b1.addWidget(QLabel("或者填公网视频 URL（可选；火山方舟传本地文件时会自动上传）"))
        self.video_url = QLineEdit()
        self.video_url.setPlaceholderText("https://example.com/clip.mp4")
        b1.addWidget(self.video_url)
        v.addWidget(box1)

        box2 = QGroupBox("② 参考图（可选，最多 3 张：换装、换物的参考）")
        b2 = QVBoxLayout(box2)
        b2.setSpacing(6)
        row2 = QHBoxLayout()
        self.pick_img_btn = QPushButton("选择参考图")
        self.pick_img_btn.clicked.connect(self.pick_images)
        self.clear_img_btn = QPushButton("清空")
        self.clear_img_btn.clicked.connect(self.clear_images)
        self.img_hint = QLabel("未选择")
        self.img_hint.setObjectName("Hint")
        row2.addWidget(self.pick_img_btn)
        row2.addWidget(self.clear_img_btn)
        row2.addWidget(self.img_hint, 1)
        b2.addLayout(row2)
        self.img_list = QListWidget()
        self.img_list.setMaximumHeight(76)
        b2.addWidget(self.img_list)
        v.addWidget(box2)

        box3 = QGroupBox("③ 指令（要改成什么样）")
        b3 = QVBoxLayout(box3)
        self.prompt = QPlainTextEdit()
        self.prompt.setPlaceholderText(
            "例如：把整个画面转换成黏土动画风格，保留人物动作与镜头运动；"
            "或：把人物外套换成参考图里的红色风衣。"
        )
        self.prompt.setMinimumHeight(88)
        b3.addWidget(self.prompt)
        v.addWidget(box3)

        box4 = QGroupBox("④ 平台与模型（只有这三家支持视频输入）")
        b4 = QVBoxLayout(box4)
        b4.setSpacing(6)
        supported = providers.platforms_for("video_edit")
        self.model_row = ModelRow(self.config, "video_edit", "模型", platforms=supported)
        self.model_row.changed.connect(self._sync_note)
        b4.addWidget(self.model_row)
        self.plat_note = QLabel("")
        self.plat_note.setObjectName("Hint")
        self.plat_note.setWordWrap(True)
        b4.addWidget(self.plat_note)

        form = QHBoxLayout()
        form.setSpacing(8)
        form.addWidget(QLabel("分辨率"))
        self.resolution = QComboBox()
        self.resolution.setEditable(True)
        self.resolution.addItems(["720P", "1080P", "768P", "2K"])
        self.resolution.setMaximumWidth(110)
        form.addWidget(self.resolution)
        form.addWidget(QLabel("时长(秒)"))
        self.duration = QSpinBox()
        self.duration.setRange(2, 30)
        self.duration.setValue(5)
        self.duration.setMaximumWidth(80)
        form.addWidget(self.duration)
        form.addStretch(1)
        b4.addLayout(form)

        form2 = QHBoxLayout()
        form2.setSpacing(8)
        form2.addWidget(QLabel("轮询间隔(秒)"))
        self.poll_interval = QSpinBox()
        self.poll_interval.setRange(3, 60)
        self.poll_interval.setValue(10)
        self.poll_interval.setMaximumWidth(80)
        form2.addWidget(self.poll_interval)
        form2.addWidget(QLabel("最长等待(分)"))
        self.poll_timeout = QSpinBox()
        self.poll_timeout.setRange(1, 120)
        self.poll_timeout.setValue(30)
        self.poll_timeout.setMaximumWidth(80)
        form2.addWidget(self.poll_timeout)
        form2.addStretch(1)
        b4.addLayout(form2)
        v.addWidget(box4)

        self.run_btn = QPushButton("开始改视频")
        self.run_btn.setObjectName("Primary")
        self.run_btn.setMinimumHeight(36)
        self.run_btn.clicked.connect(self.start)
        v.addWidget(self.run_btn)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFormat("空闲")
        v.addWidget(self.progress)

        self.state_label = QLabel("选好参考视频、写清指令，然后点上面的按钮")
        self.state_label.setObjectName("Hint")
        self.state_label.setWordWrap(True)
        v.addWidget(self.state_label)
        v.addStretch(1)
        self._sync_note()
        return panel

    # ---------------------------------------------------------------- 右：结果
    def _build_right(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        holder = QWidget()
        v = QVBoxLayout(holder)
        v.setContentsMargins(0, 0, 6, 0)
        v.setSpacing(9)

        box = QGroupBox("结果")
        b = QVBoxLayout(box)
        self.result_status = QLabel("尚未生成")
        self.result_status.setObjectName("Hint")
        self.result_status.setWordWrap(True)
        b.addWidget(self.result_status)

        row = QHBoxLayout()
        self.open_video_btn = QPushButton("打开视频")
        self.open_video_btn.setEnabled(False)
        self.open_video_btn.clicked.connect(self.open_video)
        open_dir = QPushButton("打开输出目录")
        open_dir.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(OUTPUT_DIR))))
        row.addWidget(self.open_video_btn)
        row.addWidget(open_dir)
        row.addStretch(1)
        b.addLayout(row)
        v.addWidget(box)

        tips = QGroupBox("这三家的差别（提交前看一眼能少踩坑）")
        t = QVBoxLayout(tips)
        for p in providers.platforms_for("video_edit"):
            models = "、".join(m for m, _ in providers.models_for(p, "video_edit"))
            lab = QLabel(
                f"<b>{p}</b>（{models}）<br><span style='color:#46515c'>{PLATFORM_NOTES.get(p, '')}</span>"
            )
            lab.setWordWrap(True)
            lab.setTextFormat(Qt.TextFormat.RichText)
            lab.setStyleSheet("font-size:12px;border:none;background:transparent;")
            t.addWidget(lab)

        extra = QLabel(
            "<span style='color:#6b7683'>"
            "· 视频编辑按输出时长计费，通常比文生视频贵；时长/分辨率以平台限制为准，超限会被直接拒绝。<br>"
            "· 火山方舟的视频输入只认公网 URL，本地文件请先上传；百炼与 MiniMax 支持小文件直接转 base64。<br>"
            "· 每一步的请求与平台返回都在「运行日志」窗口里，被拒时先看那里的原始错误码。"
            "</span>"
        )
        extra.setWordWrap(True)
        extra.setTextFormat(Qt.TextFormat.RichText)
        extra.setStyleSheet("font-size:12px;border:none;background:transparent;")
        t.addWidget(extra)
        v.addWidget(tips)

        v.addStretch(1)
        scroll.setWidget(holder)
        return scroll

    # ---------------------------------------------------------------- 素材
    def pick_video(self) -> None:
        f, _ = QFileDialog.getOpenFileName(
            self, "选择参考视频", str(Path.home()),
            "视频文件 (*.mp4 *.mov *.m4v *.webm *.mkv)"
        )
        if not f:
            return
        self.video_path = f
        self.video_url.clear()
        self.video_hint.setText(f"{os.path.basename(f)}（{file_size_mb(f):.1f} MB）")
        self.state_label.setText("参考视频已选好")

    def clear_video(self) -> None:
        self.video_path = ""
        self.video_url.clear()
        self.video_hint.setText("未选择")

    def pick_images(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择参考图", str(Path.home()),
            "图片文件 (*.png *.jpg *.jpeg *.webp)"
        )
        for f in files:
            if f in self.image_paths or len(self.image_paths) >= 3:
                continue
            self.image_paths.append(f)
            item = QListWidgetItem(os.path.basename(f))
            item.setData(Qt.ItemDataRole.UserRole, f)
            self.img_list.addItem(item)
        self._sync_img_hint()

    def clear_images(self) -> None:
        self.image_paths.clear()
        self.img_list.clear()
        self._sync_img_hint()

    def _sync_img_hint(self) -> None:
        n = len(self.image_paths)
        self.img_hint.setText("未选择" if n == 0 else f"已选 {n} 张")

    def _sync_note(self) -> None:
        p = self.model_row.platform()
        self.plat_note.setText(PLATFORM_NOTES.get(p, ""))
        if p == "火山方舟" and self.video_path and not self.video_url.text().strip():
            self.plat_note.setText(
                "当前选的是本地文件：提交时会先上传到方舟文件服务（Files API，≤512 MB），"
                "拿 file id 再引用。"
            )
            self.plat_note.setStyleSheet("font-size:11px;color:#0a7d4f;")
        else:
            self.plat_note.setStyleSheet("font-size:11px;color:#6b7683;")

    # ---------------------------------------------------------------- 执行
    def _busy(self, on: bool, text: str = "") -> None:
        for w in (self.run_btn, self.pick_video_btn, self.clear_video_btn, self.pick_img_btn,
                  self.clear_img_btn, self.prompt, self.video_url, self.model_row,
                  self.resolution, self.duration, self.poll_interval, self.poll_timeout):
            w.setEnabled(not on)
        if on:
            self.progress.setRange(0, 0)
            self.progress.setFormat(text or "运行中…")
        else:
            self.progress.setRange(0, 100)
            self.progress.setValue(0)
            self.progress.setFormat("空闲")

    def start(self) -> None:
        prompt = self.prompt.toPlainText().strip()
        if not prompt:
            QMessageBox.information(self, "缺少指令", "写清要把视频改成什么样。")
            return
        source = self.video_url.text().strip() or self.video_path
        if not source:
            QMessageBox.information(self, "缺少参考视频", "选择本地视频，或填一个公网视频 URL。")
            return
        platform = self.model_row.platform()
        if not self.config.get_key(platform):
            ret = QMessageBox.question(
                self, "缺少 API Key",
                f"「{platform}」还没有配置 API Key，现在打开密钥界面吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if ret == QMessageBox.StandardButton.Yes:
                self.win.open_key_manager()
            return

        self.model_row.remember()
        options = {
            "resolution": self.resolution.currentText().strip(),
            "duration": self.duration.value(),
            "poll_interval": self.poll_interval.value(),
            "poll_timeout": self.poll_timeout.value() * 60,
        }
        task = Task(
            "video_edit", platform, self.model_row.model(), self.config.get_key(platform),
            prompt=prompt, images=list(self.image_paths), options=options,
            video_source=source,
        )
        task.sig_log.connect(self.win.append_log)
        task.sig_progress.connect(self.on_progress)
        task.sig_done.connect(self.on_done)
        task.sig_fail.connect(self.on_fail)
        task.finished.connect(lambda: self._busy(False))
        self.task = task

        self.last_video = None
        self.open_video_btn.setEnabled(False)
        self._busy(True, "提交任务…")
        self.win.set_run_state("视频编辑中", "#1f6feb")
        self.win.append_log(
            "info",
            f"[视频编辑] {platform} / {self.model_row.model()} · "
            f"视频={'URL' if is_url(source) else Path(source).name} · 参考图 {len(self.image_paths)} 张",
        )
        self.state_label.setText("已提交，等待平台处理（进度见运行日志）")
        task.start()

    def on_progress(self, percent: int, text: str) -> None:
        if percent < 0:
            self.progress.setRange(0, 0)
        else:
            self.progress.setRange(0, 100)
            self.progress.setValue(percent)
        if text:
            self.progress.setFormat(text)

    def on_fail(self, message: str, detail: str) -> None:
        self.win.append_log("error", f"[视频编辑] 失败：{message}")
        if detail:
            self.win.append_log("error", detail)
        full = error_hint.decorate(message, self.model_row.platform())
        if full != message:
            self.win.append_log("info", full.split("\n\n", 1)[-1])
        self.result_status.setText(f"失败：{message[:120]}")
        self.state_label.setText("失败，原因与建议见运行日志")
        self.win.set_run_state("失败", "#c62828")
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFormat("失败")
        QMessageBox.critical(self, "视频编辑失败", full)

    def on_done(self, payload: dict) -> None:
        path = payload.get("file")
        if not path:
            self.result_status.setText("任务结束但没有拿到视频文件，请看运行日志")
            return
        self.last_video = path
        self.open_video_btn.setEnabled(True)
        size_mb = os.path.getsize(path) / (1024 * 1024) if os.path.exists(path) else 0
        self.result_status.setText(f"已保存：{path}（{size_mb:.2f} MB）")
        self.state_label.setText("完成，可点「打开视频」查看")
        self.win.set_run_state("视频编辑完成", "#0a7d4f")
        self.win.append_log("info", f"[视频编辑] 完成：{path}")

    def open_video(self) -> None:
        if self.last_video and os.path.exists(self.last_video):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.last_video))

    def refresh_key_states(self) -> None:
        self.model_row._sync_key_state()

    def showEvent(self, event):  # noqa: N802
        super().showEvent(event)
        self.refresh_key_states()
        self._sync_note()
