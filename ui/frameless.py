"""无系统标题栏窗口：自绘标题栏 + 亚克力背景 + 右下角缩放。

实现取舍（踩过的坑）：
处理 WM_NCCALCSIZE 去系统边框在部分 Qt6 / 驱动组合下会让 show() 直接
access violation 闪退。这里改用纯 Qt 方案：
  - FramelessWindowHint 去掉标题栏
  - 最大化不用 showMaximized()（会盖住任务栏），改为把窗口铺到 availableGeometry
  - 缩放交给右下角 QSizeGrip，避免自绘缩放热区在高 DPI 下算错
"""
from __future__ import annotations

from PyQt6.QtCore import QPoint, QRect, Qt, QTimer
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QToolButton, QWidget

from .win_effects import IS_WINDOWS, apply_glass


class FrameHost:
    """混入类：无边框 + 玻璃背景 + 伪最大化。"""

    _glass_applied = False
    acrylic_method = "none"
    _pseudo_max = False
    _normal_geometry: QRect | None = None

    def install_frame(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.WindowMinMaxButtonsHint
        )
        # 不开 WA_TranslucentBackground：它是 layered window，而 Win11 的 DWM
        # SystemBackdrop（亚克力/Mica）只在非 layered 窗口上绘制。
        # 背景透明靠 QSS 让 QWidget 不画底，再由 DWM 在窗口后面画模糊。
        self.setMouseTracking(True)

    # ---------- 玻璃背景 ----------
    def _apply_glass(self) -> None:
        if self._glass_applied:
            return
        self._glass_applied = True
        try:
            self.acrylic_method = apply_glass(int(self.winId()))
        except Exception:
            self.acrylic_method = "none"
        self._sync_glass_property()

    def _sync_glass_property(self) -> None:
        """模糊生效时 root 透明，否则退回实底；两种观感都能看。"""
        root = self.findChild(QWidget, "Root")
        if root is None:
            return
        ok = self.acrylic_method in ("accent-acrylic", "accent-blur", "dwm-acrylic", "dwm-mica")
        root.setProperty("glass", "true" if ok else "false")
        root.style().unpolish(root)
        root.style().polish(root)

    def showEvent(self, event):  # noqa: N802
        super().showEvent(event)
        QTimer.singleShot(0, self._apply_glass)

    # ---------- 伪最大化 ----------
    def is_pseudo_maximized(self) -> bool:
        return bool(getattr(self, "_pseudo_max", False))

    def toggle_maximize(self) -> None:
        if self.is_pseudo_maximized():
            self.restore_normal()
        else:
            self.maximize_to_screen()

    def maximize_to_screen(self) -> None:
        self._normal_geometry = self.geometry()
        screen = self.screen() or self.windowHandle().screen()
        if screen is None:
            return
        self.setGeometry(screen.availableGeometry())
        self._pseudo_max = True
        self._notify_frameless_state()

    def restore_normal(self) -> None:
        if self._normal_geometry is not None:
            self.setGeometry(self._normal_geometry)
        self._pseudo_max = False
        self._notify_frameless_state()

    def _notify_frameless_state(self) -> None:
        hook = getattr(self, "on_max_state_changed", None)
        if callable(hook):
            hook()


class TitleBar(QWidget):
    """自绘标题栏：左标题、中间可插入控件、右窗口按钮；可拖动、双击最大化。"""

    def __init__(self, window: QWidget, title: str = "AI 多模态控制台",
                 parent=None, allow_maximize: bool = True) -> None:
        super().__init__(parent)
        self.setObjectName("TitleBar")
        self._win = window
        self._drag_offset: QPoint | None = None
        self.setFixedHeight(46)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 6, 8, 6)
        lay.setSpacing(8)

        self.title = QLabel(title)
        self.title.setObjectName("AppTitle")
        lay.addWidget(self.title)

        self.badge = QLabel("")
        self.badge.setObjectName("AppBadge")
        self.badge.setVisible(False)
        lay.addWidget(self.badge)

        lay.addSpacing(8)
        self.slot = QHBoxLayout()
        self.slot.setSpacing(8)
        lay.addLayout(self.slot)
        lay.addStretch(1)

        self.btn_min = self._make_button("–", "最小化")
        self.btn_min.clicked.connect(self._win.showMinimized)
        self.btn_max = self._make_button("□", "最大化")
        self.btn_max.clicked.connect(self.toggle_max)
        self.btn_max.setVisible(allow_maximize)
        self.btn_close = QToolButton()
        self.btn_close.setObjectName("CloseBtn")
        self.btn_close.setText("✕")
        self.btn_close.setToolTip("关闭")
        self.btn_close.clicked.connect(self._win.close)
        for b in (self.btn_min, self.btn_max, self.btn_close):
            lay.addWidget(b)

    def _make_button(self, text: str, tip: str) -> QToolButton:
        b = QToolButton()
        b.setObjectName("WinBtn")
        b.setText(text)
        b.setToolTip(tip)
        return b

    def add_widget(self, widget: QWidget) -> None:
        self.slot.addWidget(widget)

    def toggle_max(self) -> None:
        toggle = getattr(self._win, "toggle_maximize", None)
        if callable(toggle):
            toggle()
        self.sync_max_icon()

    def sync_max_icon(self) -> None:
        maximized = bool(getattr(self._win, "is_pseudo_maximized", lambda: False)())
        self.btn_max.setText("❐" if maximized else "□")
        self.btn_max.setToolTip("还原" if maximized else "最大化")

    # ---------- 拖动 ----------
    def mousePressEvent(self, event):  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self._win.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):  # noqa: N802
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            target = event.globalPosition().toPoint()
            if bool(getattr(self._win, "is_pseudo_maximized", lambda: False)()):
                ratio = target.x() / max(1, self._win.width())
                self._win.restore_normal()
                self.sync_max_icon()
                self._drag_offset = QPoint(int(self._win.width() * ratio), self._drag_offset.y())
            self._win.move(target - self._drag_offset)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):  # noqa: N802
        self._drag_offset = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and not self.btn_max.isHidden():
            self.toggle_max()
        super().mouseDoubleClickEvent(event)
