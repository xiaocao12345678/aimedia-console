"""参考图工作流：参考图 + 需求 → 分析 → 视频提示词 + 首帧参考图 → 可修改 → 生成视频。

布局取舍：
- 左边固定一列「输入与模型」：参考图、需求、三步各自的平台与模型，一次配好不用来回切页
- 右边是可滚动的产出流水：分析 → 提示词 → 参考图 → 视频，按实际顺序自上而下
- 每一步都用当前平台已保存的 Key；三步可以用不同平台（例如理解用火山、生图用百炼、视频用智谱）
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices, QPixmap
from PyQt6.QtWidgets import (
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
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core import error_hint, providers
from core.analysis import build_analyze_prompt
from core.tasks import Task

from core.paths import output_dir

OUTPUT_DIR = output_dir()

CARD_QSS = """
QFrame#Card {
    background: rgba(255, 255, 255, 0.55);
    border: 1px solid rgba(148, 170, 196, 0.45);
    border-radius: 12px;
}
QFrame#Shot {
    background: rgba(255, 255, 255, 0.62);
    border: 1px solid rgba(148, 170, 196, 0.45);
    border-radius: 10px;
}
QFrame#Shot[selected="true"] {
    border: 2px solid rgba(31, 111, 235, 0.85);
    background: rgba(232, 241, 255, 0.85);
}
QLabel#StepNo {
    color: #1c68e2;
    font-weight: 700;
    font-size: 12px;
    padding: 0px;
}
QLabel#StepTitle { font-size: 13px; font-weight: 600; color: #16202a; }
QLabel#Hint { color: #6b7683; font-size: 11px; }
"""


class ModelRow(QWidget):
    """一步的「平台 + 模型」选择。三步各自独立。"""

    changed = pyqtSignal()

    def __init__(self, config, capability: str, label: str, parent=None,
                 platforms: list[str] | None = None) -> None:
        super().__init__(parent)
        self.config = config
        self.capability = capability
        self._platforms = platforms
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        name = QLabel(label)
        name.setMinimumWidth(34)
        name.setStyleSheet("font-weight:600;color:#46515c;")
        row.addWidget(name)

        self.platform_box = QComboBox()
        self.platform_box.setMaximumWidth(96)
        for p in (platforms or providers.platforms()):
            self.platform_box.addItem(p)
        allowed = platforms or providers.platforms()
        saved_platform = config.get_pref(f"wf_{capability}_platform")
        if saved_platform in allowed:
            self.platform_box.setCurrentText(saved_platform)
        row.addWidget(self.platform_box)

        self.model_box = QComboBox()
        self.model_box.setEditable(True)
        self.model_box.setMinimumWidth(250)
        self.model_box.view().setMinimumWidth(620)
        # editable 下拉默认居中排版，长 ID 会被两头裁掉；强制左对齐至少保住模型 ID
        if self.model_box.lineEdit() is not None:
            self.model_box.lineEdit().setAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
        row.addWidget(self.model_box, 1)

        self.key_state = QLabel("")
        self.key_state.setStyleSheet("font-size:10px;")
        self.key_state.setMinimumWidth(40)
        row.addWidget(self.key_state)

        self.platform_box.currentTextChanged.connect(self._on_platform_changed)
        self.model_box.currentIndexChanged.connect(self._sync_model_tip)
        self._reload_models()
        self._sync_key_state()

    def _on_platform_changed(self, name: str) -> None:
        self.config.set_pref(f"wf_{self.capability}_platform", name)
        self._reload_models()
        self._sync_key_state()
        self.changed.emit()

    def _reload_models(self) -> None:
        platform = self.platform()
        models = providers.models_for(platform, self.capability)
        self.model_box.blockSignals(True)
        self.model_box.clear()
        for mid, note in models:
            idx = self.model_box.count()
            self.model_box.addItem(mid, userData=mid)
            self.model_box.setItemData(idx, note, Qt.ItemDataRole.ToolTipRole)
        saved = self.config.get_model(platform, f"wf_{self.capability}")
        pick = saved or (models[0][0] if models else "")
        if pick:
            idx = self.model_box.findData(pick)
            if idx >= 0:
                self.model_box.setCurrentIndex(idx)
            else:
                self.model_box.setEditText(pick)
        self.model_box.blockSignals(False)
        self._sync_model_tip()

    def _sync_model_tip(self) -> None:
        idx = self.model_box.currentIndex()
        note = self.model_box.itemData(idx, Qt.ItemDataRole.ToolTipRole) or ""
        self.model_box.setToolTip(f"{self.model()} — {note}" if note else self.model())
        le = self.model_box.lineEdit()
        if le is not None:
            le.setCursorPosition(0)   # 让长 ID 从左显示，而不是滚到尾部

    def _sync_key_state(self) -> None:
        has = bool(self.config.get_key(self.platform()))
        self.key_state.setText("有 Key" if has else "无 Key")
        self.key_state.setStyleSheet(
            "font-size:10px;color:#0a7d4f;" if has else "font-size:10px;color:#b76e00;"
        )

    def platform(self) -> str:
        return self.platform_box.currentText()

    def model(self) -> str:
        data = self.model_box.currentData()
        if data:
            return str(data).strip()
        return self.model_box.currentText().strip().split("  ·  ")[0].strip()

    def api_key(self) -> str:
        return self.config.get_key(self.platform())

    def remember(self) -> None:
        self.config.set_model(self.platform(), f"wf_{self.capability}", self.model())


class ShotCard(QFrame):
    """一张参考图：选中才能作为视频首帧或修改基础。"""

    picked = pyqtSignal(str)

    def __init__(self, path: str, on_pick, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Shot")
        self.path = path
        self._on_pick = on_pick
        self.setFixedHeight(120)          # 网格会拉伸控件，固定高度才不会上下错位
        # 横排：左缩略图、右信息与按钮，卡片更矮，一屏能放下两行
        h = QHBoxLayout(self)
        h.setContentsMargins(7, 7, 7, 7)
        h.setSpacing(8)

        self.thumb = QLabel()
        self.thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb.setCursor(Qt.CursorShape.PointingHandCursor)
        self.thumb.setFixedSize(104, 104)
        pm = QPixmap(path)
        if pm.isNull():
            self.thumb.setText("无法预览")
        else:
            self.thumb.setPixmap(pm.scaled(104, 104, Qt.AspectRatioMode.KeepAspectRatio,
                                            Qt.TransformationMode.SmoothTransformation))
        self.thumb.mousePressEvent = lambda _e: self._on_pick(self.path)
        h.addWidget(self.thumb)

        right = QVBoxLayout()
        right.setSpacing(4)
        name = QLabel(os.path.basename(path))
        name.setObjectName("Hint")
        name.setWordWrap(True)
        name.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        right.addWidget(name)

        pick = QPushButton("选为首帧")
        pick.clicked.connect(lambda: self._on_pick(self.path))
        open_btn = QPushButton("打开")
        open_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(path)))
        right.addWidget(pick)
        right.addWidget(open_btn)
        right.addStretch(1)
        h.addLayout(right, 1)

    def set_selected(self, on: bool) -> None:
        self.setProperty("selected", "true" if on else "false")
        self.style().unpolish(self)
        self.style().polish(self)


class WorkflowPage(QWidget):
    """三步流水线：分析 → 参考图 → 视频。"""

    def __init__(self, win) -> None:
        super().__init__()
        self.win = win
        self.config = win.config
        self.setStyleSheet(CARD_QSS)

        self.task: Optional[Task] = None
        self.ref_images: list[str] = []
        self.generated: list[str] = []
        self.selected: Optional[str] = None
        self.analysis_text = ""
        self._shot_cards: dict[str, ShotCard] = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 10, 12, 10)
        outer.setSpacing(8)

        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(self._build_left())
        split.addWidget(self._build_right())
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setSizes([470, 810])
        outer.addWidget(split, 1)

    # ------------------------------------------------------------ 左：输入与模型
    def _build_left(self) -> QWidget:
        panel = QWidget()
        panel.setMaximumWidth(500)
        v = QVBoxLayout(panel)
        v.setContentsMargins(0, 0, 6, 0)
        v.setSpacing(8)

        # ① 参考图 + 需求
        box1 = QGroupBox("① 参考图与需求")
        b1 = QVBoxLayout(box1)
        b1.setSpacing(6)
        row = QHBoxLayout()
        self.pick_btn = QPushButton("选择参考图")
        self.pick_btn.setObjectName("Primary")
        self.pick_btn.clicked.connect(self.pick_images)
        self.clear_btn = QPushButton("清空")
        self.clear_btn.clicked.connect(self.clear_images)
        self.ref_hint = QLabel("未选择（可多张）")
        self.ref_hint.setObjectName("Hint")
        row.addWidget(self.pick_btn)
        row.addWidget(self.clear_btn)
        row.addWidget(self.ref_hint, 1)
        b1.addLayout(row)

        self.ref_list = QListWidget()
        self.ref_list.setMaximumHeight(86)
        b1.addWidget(self.ref_list)

        b1.addWidget(QLabel("需求（要什么镜头、什么改动）"))
        self.req_edit = QPlainTextEdit()
        self.req_edit.setPlaceholderText(
            "例如：让主体在傍晚的街道上向前走，镜头缓慢推进，冷色调，保留画面里的头盔与风衣细节。"
        )
        self.req_edit.setMinimumHeight(86)
        b1.addWidget(self.req_edit)
        v.addWidget(box1)

        # ② 三步模型
        box2 = QGroupBox("② 每一步用哪个模型（可来自不同平台）")
        b2 = QVBoxLayout(box2)
        b2.setSpacing(6)
        self.row_understand = ModelRow(self.config, "understand", "理解")
        self.row_image = ModelRow(self.config, "image", "生图")
        self.row_video = ModelRow(self.config, "video", "视频")
        for r in (self.row_understand, self.row_image, self.row_video):
            b2.addWidget(r)
        hint = QLabel("理解：读参考图出分析与提示词；生图：出视频首帧；视频：出最终视频")
        hint.setObjectName("Hint")
        hint.setWordWrap(True)
        b2.addWidget(hint)
        v.addWidget(box2)

        # ③ 执行
        self.run_btn = QPushButton("分析并生成素材")
        self.run_btn.setObjectName("Primary")
        self.run_btn.setMinimumHeight(36)
        self.run_btn.clicked.connect(self.run_pipeline)
        v.addWidget(self.run_btn)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFormat("空闲")
        v.addWidget(self.progress)

        box3 = QGroupBox("③ 生成视频（用选中的参考图当首帧）")
        b3 = QVBoxLayout(box3)
        b3.setSpacing(6)
        row3 = QHBoxLayout()
        self.video_btn = QPushButton("生成视频")
        self.video_btn.setObjectName("Primary")
        self.video_btn.setMinimumHeight(32)
        self.video_btn.clicked.connect(self.run_video)
        self.open_video_btn = QPushButton("打开视频")
        self.open_video_btn.setEnabled(False)
        self.open_video_btn.clicked.connect(self.open_video)
        self.open_out_btn = QPushButton("输出目录")
        self.open_out_btn.clicked.connect(self.open_output)
        row3.addWidget(self.video_btn, 1)
        row3.addWidget(self.open_video_btn)
        row3.addWidget(self.open_out_btn)
        b3.addLayout(row3)
        self.video_status = QLabel("尚未生成视频")
        self.video_status.setObjectName("Hint")
        self.video_status.setWordWrap(True)
        b3.addWidget(self.video_status)
        self.last_video: Optional[str] = None
        v.addWidget(box3)

        self.state_label = QLabel("填好参考图与需求后，点上面的按钮")
        self.state_label.setObjectName("Hint")
        self.state_label.setWordWrap(True)
        v.addWidget(self.state_label)
        v.addStretch(1)
        return panel

    # ------------------------------------------------------------ 右：产出流水
    def _build_right(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        holder = QWidget()
        v = QVBoxLayout(holder)
        v.setContentsMargins(0, 0, 6, 0)
        v.setSpacing(9)

        # ② 分析
        card1 = QGroupBox("③ 参考图分析")
        c1 = QVBoxLayout(card1)
        self.analysis_view = QTextEdit()
        self.analysis_view.setReadOnly(True)
        self.analysis_view.setPlaceholderText("分析结果会出现在这里（只读，供你判断模型有没有看懂）。")
        self.analysis_view.setMinimumHeight(88)
        self.analysis_view.setMaximumHeight(112)
        c1.addWidget(self.analysis_view)
        v.addWidget(card1)

        # ③ 提示词（可改）
        card2 = QGroupBox("④ 视频提示词（可手动修改，改完可直接用于生成视频）")
        c2 = QVBoxLayout(card2)
        self.prompt_edit = QPlainTextEdit()
        self.prompt_edit.setPlaceholderText("模型生成的视频提示词；你可以直接改，也可以用下面的按钮让模型按新提示词重出参考图。")
        self.prompt_edit.setMinimumHeight(92)
        self.prompt_edit.setMaximumHeight(126)
        c2.addWidget(self.prompt_edit)
        row = QHBoxLayout()
        self.regen_btn = QPushButton("按此提示词重出参考图")
        self.regen_btn.clicked.connect(self.regenerate_from_prompt)
        row.addWidget(self.regen_btn)
        row.addStretch(1)
        c2.addLayout(row)
        v.addWidget(card2)

        # ④ 参考图
        card3 = QGroupBox("⑤ 视频参考图（点图选中；选中的那张会作为视频首帧，也是修改的基础）")
        c3 = QVBoxLayout(card3)
        self.shot_status = QLabel("还没有生成参考图")
        self.shot_status.setObjectName("Hint")
        c3.addWidget(self.shot_status)

        self.shot_area = QScrollArea()
        self.shot_area.setWidgetResizable(True)
        self.shot_area.setMinimumHeight(260)
        self.shot_canvas = QWidget()
        self.shot_grid = QGridLayout(self.shot_canvas)
        self.shot_grid.setSpacing(9)
        self.shot_grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.shot_area.setWidget(self.shot_canvas)

        e_row = QHBoxLayout()
        self.edit_instruction = QLineEdit()
        self.edit_instruction.setPlaceholderText("修改指令，例如：把外套换成深红色、镜头拉到半身、背景换成雨夜街道")
        self.modify_btn = QPushButton("基于选中图修改")
        self.modify_btn.clicked.connect(self.modify_selected)
        e_row.addWidget(self.edit_instruction, 1)
        e_row.addWidget(self.modify_btn)
        c3.addLayout(e_row)

        self.edit_hint = QLabel("修改 = 以「选中」那张做图生图，结果作为新的一张加入下方；不想要可以忽略")
        self.edit_hint.setObjectName("Hint")
        self.edit_hint.setWordWrap(True)
        c3.addWidget(self.edit_hint)
        c3.addWidget(self.shot_area, 1)
        v.addWidget(card3, 1)

        v.addStretch(1)
        scroll.setWidget(holder)
        return scroll

    def refresh_key_states(self) -> None:
        for row in (self.row_understand, self.row_image, self.row_video):
            row._sync_key_state()

    def showEvent(self, event):  # noqa: N802
        super().showEvent(event)
        # 从密钥界面回来、或换了平台后，Key 状态要立刻反映出来
        self.refresh_key_states()

    # ------------------------------------------------------------ 参考图
    def pick_images(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择参考图", str(Path.home()),
            "图片文件 (*.png *.jpg *.jpeg *.webp *.bmp)"
        )
        for f in files:
            if f in self.ref_images:
                continue
            self.ref_images.append(f)
            item = QListWidgetItem(os.path.basename(f))
            item.setData(Qt.ItemDataRole.UserRole, f)
            item.setToolTip(f)
            self.ref_list.addItem(item)
        self._sync_ref_hint()

    def clear_images(self) -> None:
        self.ref_images.clear()
        self.ref_list.clear()
        self._sync_ref_hint()

    def _sync_ref_hint(self) -> None:
        n = len(self.ref_images)
        self.ref_hint.setText("未选择（可多张）" if n == 0 else f"已选 {n} 张")

    # ------------------------------------------------------------ 任务封装
    def _busy(self, on: bool, text: str = "") -> None:
        for w in (self.run_btn, self.pick_btn, self.clear_btn, self.regen_btn,
                  self.modify_btn, self.video_btn, self.req_edit,
                  self.row_understand, self.row_image, self.row_video):
            w.setEnabled(not on)
        if on:
            self.progress.setRange(0, 0)
            self.progress.setFormat(text or "运行中…")
        else:
            self.progress.setRange(0, 100)
            self.progress.setValue(0)
            self.progress.setFormat("空闲")

    def _ensure_key(self, platform: str, step: str) -> bool:
        if self.config.get_key(platform):
            return True
        ret = QMessageBox.question(
            self, "缺少 API Key",
            f"{step}用的是「{platform}」，还没有配置 API Key。\n\n现在打开密钥管理界面吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ret == QMessageBox.StandardButton.Yes:
            self.win.open_key_manager()
        return False

    def _start(self, kind: str, row: ModelRow, prompt: str, images: list[str],
               options: dict, on_done, step_label: str) -> None:
        row.remember()
        self._active_platform = row.platform()
        task = Task(kind, row.platform(), row.model(), row.api_key(),
                    prompt=prompt, images=images, options=options)
        task.sig_log.connect(self.win.append_log)
        task.sig_progress.connect(self._on_progress)
        task.sig_done.connect(on_done)
        task.sig_fail.connect(self._on_fail)
        task.finished.connect(lambda: self._busy(False))
        self.task = task
        self.win.set_run_state(step_label, "#1f6feb")
        self.win.append_log("info", f"[工作流] {step_label} · {row.platform()} / {row.model()}")
        task.start()

    def _on_progress(self, percent: int, text: str) -> None:
        if percent < 0:
            self.progress.setRange(0, 0)
        else:
            self.progress.setRange(0, 100)
            self.progress.setValue(percent)
        if text:
            self.progress.setFormat(text)

    def _on_fail(self, message: str, detail: str) -> None:
        self.win.append_log("error", f"[工作流] 失败：{message}")
        if detail:
            self.win.append_log("error", detail)
        full = error_hint.decorate(message, getattr(self, "_active_platform", ""))
        if full != message:
            self.win.append_log("info", full.split("\n\n", 1)[-1])
        self.state_label.setText(f"失败：{message[:80]}")
        self.win.set_run_state("失败", "#c62828")
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFormat("失败")
        QMessageBox.critical(self, "这一步失败了", full)

    # ------------------------------------------------------------ ① 分析
    def run_pipeline(self) -> None:
        if not self.ref_images:
            QMessageBox.information(self, "缺少参考图", "请先选择至少一张参考图。")
            return
        requirement = self.req_edit.toPlainText().strip()
        if not requirement:
            QMessageBox.information(self, "缺少需求", "请写清你想要的画面或改动。")
            return
        if not self._ensure_key(self.row_understand.platform(), "参考图理解"):
            return
        prompt = build_analyze_prompt(requirement, len(self.ref_images))
        self.state_label.setText("正在分析参考图并生成提示词…")
        self._busy(True, "分析参考图…")
        self._start("analyze", self.row_understand, prompt, list(self.ref_images),
                    {"max_tokens": 2048}, self._on_analyzed, "分析参考图")

    def _on_analyzed(self, data: dict) -> None:
        self.analysis_text = data.get("analysis") or ""
        self.analysis_view.setPlainText(self.analysis_text or "（模型没有给出分析文本）")
        self.prompt_edit.setPlainText(data.get("video_prompt") or "")
        self._image_prompt = data.get("image_prompt") or ""
        self.state_label.setText("分析完成，接着生成视频参考图…")
        self.win.append_log(
            "info",
            f"[工作流] 分析完成：提示词 {len(self.prompt_edit.toPlainText())} 字"
            + ("" if data.get("parsed") else "（非 JSON，已降级处理）"),
        )
        # 自动进入第二步：用生成的首帧提示词出图
        self.generate_reference(self._image_prompt or self.prompt_edit.toPlainText())

    # ------------------------------------------------------------ ② 参考图
    def generate_reference(self, prompt: str, base_images: Optional[list[str]] = None) -> None:
        if not prompt.strip():
            QMessageBox.information(self, "缺少提示词", "生图提示词是空的，请先填写。")
            return
        if not self._ensure_key(self.row_image.platform(), "参考图生成"):
            return
        images = list(self.ref_images) if base_images is None else base_images
        self.state_label.setText("正在生成视频参考图…")
        self._busy(True, "生成参考图…")
        self._start("wf_image", self.row_image, prompt, images,
                    {"size": "1024x1024", "n": 1}, self._on_reference_done, "生成参考图")

    def regenerate_from_prompt(self) -> None:
        prompt = self.prompt_edit.toPlainText().strip()
        if not prompt:
            QMessageBox.information(self, "提示词为空", "请先填写或生成视频提示词。")
            return
        self.generate_reference(prompt)

    def _on_reference_done(self, payload: dict) -> None:
        files = payload.get("files") or []
        if not files:
            self.state_label.setText("没有拿到参考图，请看运行日志")
            return
        self.generated = files + self.generated
        self._rebuild_grid()
        self._select(files[0])
        self.state_label.setText(f"参考图已生成（{len(self.generated)} 张可选），可以修改或直接生成视频")
        self.shot_status.setText(
            f"共 {len(self.generated)} 张；当前选中：{os.path.basename(self.selected or '')}"
        )
        self.win.set_run_state("参考图就绪", "#0a7d4f")

    def _rebuild_grid(self) -> None:
        while self.shot_grid.count():
            item = self.shot_grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._shot_cards.clear()
        for i, path in enumerate(self.generated):
            card = ShotCard(path, self._select)
            card.set_selected(path == self.selected)
            r, c = divmod(i, 2)
            self.shot_grid.addWidget(card, r, c)
            self._shot_cards[path] = card

    def _select(self, path: str) -> None:
        self.selected = path
        for p, card in self._shot_cards.items():
            card.set_selected(p == path)
        self.shot_status.setText(
            f"共 {len(self.generated)} 张；当前选中：{os.path.basename(path)}"
        )

    def modify_selected(self) -> None:
        if not self.selected:
            QMessageBox.information(
                self, "先选一张", "点一下上面任意一张参考图，再写修改指令。"
            )
            return
        instruction = self.edit_instruction.text().strip()
        if not instruction:
            QMessageBox.information(self, "缺少修改指令", "写一句要改什么，例如「把外套换成深红色」。")
            return
        if not self._ensure_key(self.row_image.platform(), "参考图修改"):
            return
        self.state_label.setText("正在基于选中图修改…")
        self._busy(True, "修改参考图…")
        self._start("wf_image", self.row_image, instruction, [self.selected],
                    {"size": "1024x1024", "n": 1}, self._on_modified, "修改参考图")

    def _on_modified(self, payload: dict) -> None:
        self._on_reference_done(payload)
        self.edit_instruction.clear()
        self.state_label.setText("修改完成，新图已加在上面并选中")

    # ------------------------------------------------------------ ③ 视频
    def run_video(self) -> None:
        prompt = self.prompt_edit.toPlainText().strip()
        if not prompt:
            QMessageBox.information(self, "缺少提示词", "请先生成或填写视频提示词。")
            return
        if not self.selected:
            ret = QMessageBox.question(
                self, "没有选中参考图",
                "现在没有选中的参考图，将按纯文生视频处理。继续吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if ret != QMessageBox.StandardButton.Yes:
                return
        if not self._ensure_key(self.row_video.platform(), "视频生成"):
            return
        images = [self.selected] if self.selected else []
        self.last_video = None
        self.open_video_btn.setEnabled(False)
        self.state_label.setText("正在生成视频（异步任务，进度见运行日志）…")
        self._busy(True, "生成视频…")
        self._start("video", self.row_video, prompt, images,
                    {"duration": "5", "resolution": "768P", "poll_interval": 5,
                     "poll_timeout": 1800},
                    self._on_video_done, "生成视频")

    def _on_video_done(self, payload: dict) -> None:
        path = payload.get("file")
        if not path:
            self.video_status.setText("任务结束但没有拿到视频文件，请看运行日志")
            return
        self.last_video = path
        self.open_video_btn.setEnabled(True)
        size_mb = os.path.getsize(path) / (1024 * 1024) if os.path.exists(path) else 0
        self.video_status.setText(f"已保存：{path}（{size_mb:.2f} MB）")
        self.state_label.setText("视频已生成，可用「打开视频」查看")
        self.win.set_run_state("视频完成", "#0a7d4f")

    def open_video(self) -> None:
        if self.last_video and os.path.exists(self.last_video):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.last_video))

    def open_output(self) -> None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(OUTPUT_DIR)))
