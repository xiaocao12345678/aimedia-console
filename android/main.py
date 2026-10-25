"""AI 多模态控制台 · Android 版入口。

四个功能页（理解 / 生图 / 视频 / 改视频）+ 密钥页 + 日志页，
核心调用逻辑与桌面版共用 android/core 里那套（providers / adapters / media）。
"""
from __future__ import annotations

import os
import sys
import time
import traceback
from pathlib import Path

# ---- Kivy 配置必须在导入 kivy 之前设置 ----
os.environ.setdefault("KIVY_NO_ARGS", "1")

from kivy.config import Config as KivyConfig

KivyConfig.set("kivy", "exit_on_escape", "0")
KivyConfig.set("kivy", "keyboard_mode", "systemanddock")

from kivy.app import App
from kivy.clock import Clock
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import NoTransition, ScreenManager
from kivy.uix.widget import Widget

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from core.config import Config                      # noqa: E402
from core.paths import asset_path, log_dir, output_dir  # noqa: E402

from ui.common import BG, BORDER, ERR, MUTED, NAV, OK, PRIMARY, TEXT, WARN, Field, RBtn  # noqa: E402
from ui.screens import (EditPage, ImagePage, KeysPage, LogPage, UnderstandPage,  # noqa: E402
                        VideoPage)

# ---------------------------------------------------------------- 中文字体
def _font_candidates() -> list[Path]:
    """Kivy 默认字体不含中文，必须显式指定，否则中文全是方块。"""
    cands: list[Path] = []
    for name in ("NotoSansSC.otf", "NotoSansCJK-Regular.ttc", "NotoSansCJKsc-Regular.otf"):
        cands.append(Path(asset_path(name)))
        cands.append(BASE / "assets" / name)
    # Android 系统字体（AOSP 与多数国产 ROM 都有，零体积方案）
    for p in ("/system/fonts/NotoSansCJK-Regular.ttc",
              "/system/fonts/NotoSansCJKsc-Regular.otf",
              "/system/fonts/DroidSansFallback.ttf",
              "/system/fonts/MiSans-Regular.ttf",
              "/system/fonts/OPPOSans-Regular.ttf",
              "/system/fonts/HarmonyOS_Sans_SC.ttf",
              "/system/fonts/Roboto-Regular.ttf"):
        cands.append(Path(p))
    # 桌面预览用（不打包进 APK）
    cands.append(Path("C:/Windows/Fonts/msyh.ttc"))
    cands.append(Path("C:/Windows/Fonts/simhei.ttf"))
    return cands


def register_fonts() -> str:
    """挑第一个真的能渲染中文的字体，注册成 Roboto / NotoSC。"""
    from kivy.core.text import Label as CoreLabel

    for font in _font_candidates():
        try:
            if not font.exists() or font.stat().st_size < 200_000:
                continue
            LabelBase.register(name="Roboto", fn_regular=str(font), fn_bold=str(font))
            LabelBase.register(name="NotoSC", fn_regular=str(font), fn_bold=str(font))
            probe = CoreLabel(text="中文测试", font_name="Roboto", font_size=18)
            probe.refresh()
            if probe.texture and probe.texture.size[0] > 10:
                return str(font)
        except Exception:
            continue
    return ""


# ---------------------------------------------------------------- 顶部/底部
class Header(BoxLayout):
    def __init__(self, app, **kw):
        super().__init__(orientation="horizontal", size_hint_y=None, height=dp(50),
                         padding=(dp(12), dp(6)), spacing=dp(6), **kw)
        self.app = app
        title = Label(text="AI 多模态控制台", halign="left", valign="middle",
                      color=list(TEXT), bold=True, font_size="16sp",
                      size_hint_x=1, text_size=(dp(200), None))
        self.add_widget(title)
        b1 = RBtn(text="密钥", filled=False, height=dp(34), font_size="12sp",
                  size_hint_x=None, width=dp(52))
        b1.bind(on_release=lambda *_: app.goto("keys"))
        b2 = RBtn(text="日志", filled=False, height=dp(34), font_size="12sp",
                  size_hint_x=None, width=dp(52))
        b2.bind(on_release=lambda *_: app.goto("logs"))
        self.add_widget(b1)
        self.add_widget(b2)


class NavBar(BoxLayout):
    LABELS = [("understand", "理解"), ("image", "生图"), ("video", "视频"), ("edit", "改视频")]

    def __init__(self, app, **kw):
        super().__init__(orientation="horizontal", size_hint_y=None, height=dp(56),
                         spacing=dp(2), padding=(dp(6), dp(4)), **kw)
        self.app = app
        self.buttons = {}
        for key, label in self.LABELS:
            b = RBtn(text=label, filled=False, height=dp(46), font_size="13sp")
            b.bind(on_release=lambda _b, k=key: app.goto(k))
            self.buttons[key] = b
            self.add_widget(b)


class StatusBar(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation="horizontal", size_hint_y=None, height=dp(30),
                         padding=(dp(12), 0), **kw)
        self.label = Label(text="就绪", halign="left", valign="middle", font_size="12sp",
                           color=list(MUTED), text_size=(Window.width - dp(24), None))
        self.add_widget(self.label)
        self._toast_job = None

    def set(self, text: str, color=MUTED) -> None:
        self.label.text = text
        self.label.color = list(color)

    def toast(self, text: str, color=MUTED) -> None:
        self.set(text, color)
        if self._toast_job:
            self._toast_job.cancel()
        self._toast_job = Clock.schedule_once(lambda *_: self.set("就绪", MUTED), 3.2)


# ---------------------------------------------------------------- App
class ConsoleApp(App):
    title = "AI 多模态控制台"

    def build(self):
        font_used = register_fonts()
        Window.clearcolor = BG
        if not os.environ.get("ANDROID_ARGUMENT"):
            Window.size = (420, 860)   # 桌面上按手机比例预览

        self.config = Config()
        self.log_path = log_dir() / f"app_{time.strftime('%Y%m%d')}.log"

        root = BoxLayout(orientation="vertical")
        root.add_widget(Header(self))

        self.sm = ScreenManager(transition=NoTransition())
        self.pages = {}
        for key, cls, name in (
            ("understand", UnderstandPage, "understand"),
            ("image", ImagePage, "image"),
            ("video", VideoPage, "video"),
            ("edit", EditPage, "edit"),
        ):
            page = cls(self, name=name)
            self.pages[key] = page
            self.sm.add_widget(page)
        self.keys_page = KeysPage(self, name="keys")
        self.log_page = LogPage(self, name="logs")
        self.sm.add_widget(self.keys_page)
        self.sm.add_widget(self.log_page)
        root.add_widget(self.sm)

        self.status = StatusBar()
        root.add_widget(self.status)
        self.nav = NavBar(self)
        root.add_widget(self.nav)

        self.log("info", f"启动完成 · 字体 {font_used or '（未找到中文字体，可能显示方块）'}")
        self.log("info", f"产物目录 {output_dir()}")
        self.log("info", f"日志文件 {self.log_path}")
        configured = [p for p in ("火山方舟", "阿里百炼", "腾讯混元", "智谱 GLM", "百度千帆", "MiniMax")
                      if self.config.get_key(p)]
        self.log("info", f"已配置 Key：{len(configured)}/6 " + ("、".join(configured) or "（无）"))

        self.goto("understand")
        # SAF 选图不需要存储权限，启动时不再检查/跳转系统权限页
        Window.bind(on_keyboard=self._on_key)
        return root

    # ------------------------------------------------------------ 导航
    def goto(self, key: str) -> None:
        if key not in [s.name for s in self.sm.screens]:
            return
        self.sm.current = key
        for k, b in self.nav.buttons.items():
            b.filled = (k == key)
            b._sync_colors()

    # ------------------------------------------------------------ 日志
    def log(self, level: str, msg: str) -> None:
        try:
            self.log_page.append(level, msg)
        except Exception:
            pass
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%H:%M:%S')}][{level}] {msg}\n")
        except Exception:
            pass

    def set_status(self, text: str, color=MUTED) -> None:
        self.status.set(text, color)

    def toast(self, text: str, color=MUTED) -> None:
        self.status.toast(text, color)
        self.log("error" if color == ERR else "info", text)

    def refresh_key_state(self) -> None:
        pass

    # ------------------------------------------------------------ 返回键
    def _on_key(self, _window, key, *_args):
        from kivy.core.window import Keyboard
        if key == Keyboard.keycodes.get("escape", 27) and self.sm.current != "understand":
            self.goto("understand")
            return True
        return False


def _install_exception_guard() -> None:
    """让 Kivy 回调里的异常不杀进程，并把堆栈写进日志。

    Kivy 默认在 on_exception 里可能直接结束进程——表现在用户那边就是"点一下闪退"，
    什么提示都没有。接上 ExceptionManager 后返回 PASS，界面还在，错误可查。
    """
    try:
        from kivy.base import ExceptionHandler, ExceptionManager

        class _Guard(ExceptionHandler):
            def handle_exception(self, inst):
                try:
                    txt = "".join(traceback.format_exception(
                        type(inst), inst, inst.__traceback__))
                    print(txt)
                    try:
                        from core.paths import output_dir
                        with open(os.path.join(output_dir(), "crash.log"),
                                  "a", encoding="utf-8") as f:
                            f.write(f"\n=== {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n{txt}")
                    except Exception:
                        pass
                except Exception:
                    pass
                return ExceptionManager.PASS   # 继续跑，不退出

        ExceptionManager.add_handler(_Guard())
    except Exception:
        traceback.print_exc()


def main() -> None:
    _install_exception_guard()
    try:
        ConsoleApp().run()
    except Exception:
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
