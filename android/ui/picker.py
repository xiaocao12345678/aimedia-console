"""文件选择弹窗：Android 与桌面共用（Kivy 自带 FileChooser）。

Android 上要读 /sdcard 需要 MANAGE_EXTERNAL_STORAGE（buildozer.spec 已声明），
首次使用系统会弹「允许访问所有文件」，同意后才能浏览。
"""
from __future__ import annotations

import os
from pathlib import Path

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.popup import Popup

from .common import MUTED, RBtn, TEXT

IMAGE_FILTERS = ["*.png", "*.jpg", "*.jpeg", "*.webp", "*.bmp"]
VIDEO_FILTERS = ["*.mp4", "*.mov", "*.m4v", "*.webm", "*.mkv"]


def _start_dir(kind: str) -> str:
    if os.environ.get("ANDROID_ARGUMENT"):
        for cand in ("/storage/emulated/0/DCIM", "/storage/emulated/0/Pictures",
                     "/storage/emulated/0/Download", "/storage/emulated/0"):
            if os.path.isdir(cand):
                return cand
        return "/storage/emulated/0"
    home = Path.home()
    for sub in ("Pictures", "Downloads", "Desktop"):
        p = home / sub
        if p.is_dir():
            return str(p)
    return str(home)


class FilePicker(Popup):
    def __init__(self, on_pick, kind: str = "image", limit: int = 1, **kw):
        self.on_pick = on_pick
        self.kind = kind
        self.limit = limit
        title = "选择图片" if kind == "image" else "选择视频"
        super().__init__(title=title, size_hint=(0.98, 0.95),
                         title_color=list(TEXT), separator_color=(0.2, 0.5, 0.9, 1), **kw)

        root = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        self.chooser = FileChooserListView(
            path=_start_dir(kind),
            filters=IMAGE_FILTERS if kind == "image" else VIDEO_FILTERS,
            multiselect=(limit > 1),
        )
        root.add_widget(self.chooser)

        self.hint = RBtn(text=f"最多可选 {limit} 个" if limit > 1 else "点一个文件，再按确认",
                         filled=False, height=dp(30), font_size="12sp",
                         color=list(MUTED), disabled=True)
        root.add_widget(self.hint)

        bar = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        cancel = RBtn(text="取消", filled=False)
        cancel.bind(on_release=lambda *_: self.dismiss())
        self.ok = RBtn(text="确认选择")
        self.ok.bind(on_release=self._confirm)
        bar.add_widget(cancel)
        bar.add_widget(self.ok)
        root.add_widget(bar)
        self.content = root

    def _confirm(self, *_):
        sel = list(self.chooser.selection or [])
        if not sel:
            self.hint.text = "还没有选中文件"
            return
        sel = [s for s in sel if os.path.isfile(s)][: self.limit]
        if not sel:
            self.hint.text = "选中的不是文件"
            return
        self.dismiss()
        self.on_pick(sel)


# ---------------------------------------------------------------- 分发
_picker_singleton = None


def _error_popup(msg: str) -> None:
    """把失败原因显示出来——静默失败比闪退更难查。"""
    try:
        from kivy.uix.label import Label
        from kivy.uix.boxlayout import BoxLayout
        pop = Popup(title="打开相册失败", size_hint=(0.9, 0.35))
        box = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
        lab = Label(text=msg, halign="left", valign="top", font_size="13sp")
        lab.bind(size=lambda *_: setattr(lab, "text_size", (lab.width, None)))
        box.add_widget(lab)
        ok = RBtn(text="知道了")
        ok.bind(on_release=lambda *_: pop.dismiss())
        box.add_widget(ok)
        pop.content = box
        pop.open()
    except Exception:
        pass


def open_picker(on_pick, kind: str = "image", limit: int = 1) -> None:
    """Android 走系统相册（SAF，免存储权限），其他平台用 Kivy 的 FilePicker。"""
    global _picker_singleton
    try:
        from .android_picker import MediaPicker, is_android
    except Exception as exc:
        print(f"[picker] android_picker 导入失败: {exc}")
        is_android = lambda: False  # noqa: E731

    if is_android():
        try:
            if _picker_singleton is None:
                _picker_singleton = MediaPicker()
            _picker_singleton.pick(on_pick, kind, limit)
            err = getattr(_picker_singleton, "last_error", "")
            if err:
                _error_popup(f"系统相册没能打开：\n{err}")
        except Exception as exc:
            # 兜住一切，避免闪退；把原因直接给用户看
            print(f"[picker] SAF 调用异常: {exc}")
            _error_popup(f"{type(exc).__name__}: {exc}")
    else:
        FilePicker(on_pick, kind, limit).open()
