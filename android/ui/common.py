"""移动端通用控件与配色（Kivy 版）。

Kivy 没有 QSS，圆角/描边都靠 canvas 指令画；这里把常用的封装掉，
业务页面只用 Card / RBtn / Field 这几个组件。
"""
from __future__ import annotations

from kivy.graphics import Color, Line, RoundedRectangle, Triangle
from kivy.metrics import dp
from kivy.properties import BooleanProperty, ListProperty, NumericProperty, StringProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import AsyncImage
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner

# ---------------------------------------------------------------- 配色
BG = (0.955, 0.965, 0.980, 1)
CARD = (1.0, 1.0, 1.0, 0.86)
CARD_DIM = (0.965, 0.975, 0.990, 0.86)
NAV = (1.0, 1.0, 1.0, 0.96)
BORDER = (0.80, 0.845, 0.895, 1)
PRIMARY = (0.122, 0.435, 0.922, 1)      # #1f6feb
PRIMARY_DIM = (0.122, 0.435, 0.922, 0.55)
TEXT = (0.145, 0.183, 0.227, 1)
MUTED = (0.435, 0.478, 0.525, 1)
ERR = (0.776, 0.157, 0.157, 1)
OK = (0.039, 0.490, 0.310, 1)
WARN = (0.718, 0.431, 0.0, 1)

FONT_NAME = "NotoSC"


def _rgba(c):
    return list(c)


class Card(BoxLayout):
    """白底圆角卡片。"""

    radius = NumericProperty(dp(14))
    tone = ListProperty(list(CARD))

    def __init__(self, **kw):
        kw.setdefault("orientation", "vertical")
        kw.setdefault("padding", (dp(12), dp(10), dp(12), dp(10)))
        kw.setdefault("spacing", dp(8))
        kw.setdefault("size_hint_y", None)
        super().__init__(**kw)
        self.bind(minimum_height=self.setter("height"))
        with self.canvas.before:
            from kivy.graphics import Color, Line, RoundedRectangle
            self._color = Color(*self.tone)
            self._rect = RoundedRectangle(radius=[self.radius])
            self._edge_color = Color(*BORDER)
            self._edge = Line(rounded_rectangle=(0, 0, 0, 0, self.radius), width=1)
        self.bind(pos=self._sync, size=self._sync, tone=self._sync_color)
        self._sync()

    def _sync_color(self, *_):
        self._color.rgba = self.tone

    def _sync(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size
        if getattr(self, "_edge", None) is not None:
            self._edge.rounded_rectangle = (self.x, self.y, self.width, self.height, self.radius)


class RBtn(ButtonBehavior, Label):
    """圆角按钮：filled=True 蓝底白字，False 白底描边。"""

    filled = BooleanProperty(True)
    danger = BooleanProperty(False)
    radius = NumericProperty(dp(11))
    bg = ListProperty(list(PRIMARY))

    def __init__(self, **kw):
        kw.setdefault("size_hint_y", None)
        kw.setdefault("size_hint_x", 1)
        kw.setdefault("height", dp(46))
        kw.setdefault("halign", "center")
        kw.setdefault("valign", "middle")
        kw.setdefault("font_size", "15sp")
        kw.setdefault("bold", True)
        super().__init__(**kw)
        with self.canvas.before:
            from kivy.graphics import Color, Line, RoundedRectangle
            self._color = Color(*PRIMARY)
            self._rect = RoundedRectangle(radius=[self.radius])
            self._line_color = Color(*BORDER)
            self._line = Line(rounded_rectangle=(0, 0, 0, 0, self.radius), width=1)
        self.bind(pos=self._sync, size=self._on_size,
                  filled=self._sync_colors, disabled=self._sync_colors)
        self._sync_colors()
        self._on_size()

    def _on_size(self, *_):
        self._sync_size()
        self._sync()

    def _sync_size(self, *_):
        self.text_size = (self.width - dp(16), None)

    def _sync_colors(self, *_):
        if self.disabled:
            self._color.rgba = (0.72, 0.76, 0.80, 1)
            self.color = (1, 1, 1, 0.85)
            self._line_color.rgba = (0, 0, 0, 0)
        elif self.filled:
            self._color.rgba = list(ERR) if self.danger else list(self.bg)
            self.color = (1, 1, 1, 1)
            self._line_color.rgba = (0, 0, 0, 0)
        else:
            self._color.rgba = (1, 1, 1, 0.92)
            self.color = list(ERR) if self.danger else list(TEXT)
            self._line_color.rgba = list(BORDER)

    def _sync(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size
        self._line.rounded_rectangle = (self.x, self.y, self.width, self.height, self.radius)


class Sel(Spinner):
    """浅色圆角下拉，自带小三角。

    Kivy 默认 Spinner 的贴图是深灰色（在 Fusion 主题下尤其明显），
    在浅色界面里很突兀，所以自己画背景和箭头。
    """

    def __init__(self, **kw):
        kw.setdefault("background_normal", "")
        kw.setdefault("background_down", "")
        kw.setdefault("background_color", (0, 0, 0, 0))
        kw.setdefault("color", list(TEXT))
        kw.setdefault("font_size", "13sp")
        super().__init__(**kw)
        with self.canvas.before:
            self._cc1 = Color(1, 1, 1, 1)
            self._bg = RoundedRectangle(radius=[dp(9)])
            self._cc2 = Color(*BORDER)
            self._ln = Line(rounded_rectangle=(0, 0, 0, 0, dp(9)), width=1)
        with self.canvas.after:
            self._cc3 = Color(*MUTED)
            self._tri = Triangle()
        self.bind(pos=self._sync, size=self._sync)
        self._sync()

    def _sync(self, *_):
        r = dp(9)
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._ln.rounded_rectangle = (self.x, self.y, self.width, self.height, r)
        cx = self.x + self.width - dp(15)
        cy = self.y + self.height / 2
        w, h = dp(5), dp(4)
        self._tri.points = [cx - w, cy + h, cx + w, cy + h, cx, cy - h]


class Thumb(ButtonBehavior, AsyncImage):
    """可点击的缩略图（AsyncImage 本身没有点击事件）。"""

    def __init__(self, **kw):
        kw.setdefault("size_hint_y", None)
        kw.setdefault("height", dp(150))
        kw.setdefault("allow_stretch", True)
        kw.setdefault("keep_ratio", True)
        kw.setdefault("nocache", False)
        super().__init__(**kw)


class Field(Label):
    """小节标题/说明文字。"""

    def __init__(self, **kw):
        kw.setdefault("size_hint_y", None)
        kw.setdefault("halign", "left")
        kw.setdefault("valign", "top")
        kw.setdefault("font_size", "12.5sp")
        kw.setdefault("color", list(MUTED))
        super().__init__(**kw)
        self.bind(width=lambda *_: setattr(self, "text_size", (self.width, None)),
                  texture_size=lambda *_: setattr(self, "height", max(dp(16), self.texture_size[1])))


class Body(Label):
    """正文（可自动撑高）。"""

    def __init__(self, **kw):
        kw.setdefault("size_hint_y", None)
        kw.setdefault("halign", "left")
        kw.setdefault("valign", "top")
        kw.setdefault("font_size", "13.5sp")
        kw.setdefault("color", list(TEXT))
        super().__init__(**kw)
        self.bind(width=lambda *_: setattr(self, "text_size", (self.width, None)),
                  texture_size=lambda *_: setattr(self, "height", max(dp(18), self.texture_size[1])))
