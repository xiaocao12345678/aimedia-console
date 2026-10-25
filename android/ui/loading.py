"""加载遮罩：转圈 + 当前步骤 + 已等待秒数。

为什么需要：
  图片生成几秒到几十秒、视频生成要几分钟。这期间如果只是把按钮变灰、状态栏
  写一句"生成中…"，用户会以为卡死了——尤其轮询阶段长时间没有任何变化。
  遮罩上给三样东西就够：动画在动（说明程序还活着）、在做什么、已经等多久。

为什么用 canvas 画圆弧而不是字符动画：
  盲文点阵 ⠋⠙⠹（U+28xx）在中文字体里通常没有字形，手机上会显示成方块；
  ASCII 的 |/-\\ 能显示但很土。直接画 270° 圆弧并旋转，跟字体无关，也不吃资源。
"""
from __future__ import annotations

from kivy.clock import Clock
from kivy.graphics import Color, Line, PopMatrix, PushMatrix, Rotate
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.widget import Widget

from .common import MUTED, RBtn, TEXT


class Spinner(Widget):
    """一段 270° 圆弧绕中心旋转。"""

    def __init__(self, **kw):
        super().__init__(**kw)
        with self.canvas:
            PushMatrix()
            self._rot = Rotate(angle=0, origin=self.center)
            Color(0.24, 0.52, 0.90, 1)
            self._arc = Line(circle=(self.center_x, self.center_y, dp(15), 0, 270),
                             width=dp(3))
            PopMatrix()
        self.bind(pos=self._sync, size=self._sync)
        self._ev = Clock.schedule_interval(self._spin, 0.045)

    def _sync(self, *_a):
        self._rot.origin = self.center
        self._arc.circle = (self.center_x, self.center_y, dp(15), 0, 270)

    def _spin(self, dt):
        try:
            self._rot.angle = (self._rot.angle - 14) % 360
        except Exception:
            pass

    def stop(self):
        if self._ev is not None:
            self._ev.cancel()
            self._ev = None


class LoadingOverlay(ModalView):
    def __init__(self, **kw):
        # 注意：Kivy 2.3.1 的 ModalView 没有 overlay 参数，背景色叫 overlay_color
        super().__init__(
            auto_dismiss=False,
            overlay_color=(0.97, 0.98, 1.0, 0.94),
            background="",
            size_hint=(None, None),
            size=(dp(270), dp(230)),
            **kw,
        )
        self._msg = "处理中…"
        self._elapsed = 0.0
        self._ev = None

        box = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(12))

        self.spinner = Spinner(size_hint_y=None, height=dp(58))
        box.add_widget(self.spinner)

        self.lbl_msg = Label(text=self._msg, font_size="15sp", color=list(TEXT),
                             halign="center", valign="center", size_hint_y=None, height=dp(28))
        self.lbl_msg.bind(size=lambda *_: setattr(self.lbl_msg, "text_size", self.lbl_msg.size))
        box.add_widget(self.lbl_msg)

        self.lbl_time = Label(text="", font_size="12sp", color=list(MUTED),
                              size_hint_y=None, height=dp(20))
        box.add_widget(self.lbl_time)

        # 视频要跑几分钟，留个出口：隐藏遮罩但任务照常跑，完成后自动出结果
        self.btn_bg = RBtn(text="放到后台继续", filled=False,
                           size_hint_y=None, height=dp(34), font_size="12sp")
        self.btn_bg.bind(on_release=lambda *_: self.hide())
        box.add_widget(self.btn_bg)

        self.add_widget(box)

    # ---- 计时 --------------------------------------------------------
    def _tick(self, dt):
        self._elapsed += dt
        secs = int(self._elapsed)
        if secs >= 3:
            self.lbl_time.text = f"已等待 {secs} 秒"

    # ---- 对外 --------------------------------------------------------
    def show(self, msg: str = "处理中…"):  # noqa: A003
        self._msg = msg
        self._elapsed = 0.0
        self.lbl_msg.text = msg
        self.lbl_time.text = ""
        try:
            self.open()
        except Exception:
            pass
        if self._ev is None:
            self._ev = Clock.schedule_interval(self._tick, 0.5)

    def update(self, msg: str):
        """轮询阶段不断回调，把「第 N 次检查」这类信息显示出来。"""
        if msg and msg != self._msg:
            self._msg = msg
            self.lbl_msg.text = msg

    def hide(self):
        if self._ev is not None:
            self._ev.cancel()
            self._ev = None
        try:
            self.dismiss()
        except Exception:
            pass
