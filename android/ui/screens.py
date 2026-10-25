"""六个页面：理解 / 生图 / 视频 / 改视频 / 密钥 / 日志。

每个功能页都自带「平台 + 模型」两列下拉（移动端屏幕窄，不放在全局顶栏），
下拉内容来自 core.providers，与桌面版共用同一份模型清单。
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import AsyncImage
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

from core import error_hint, providers
from core.media import file_size_mb, is_url
from core.paths import output_dir
from core.runner import Runner

from .common import (BG, BORDER, CARD, CARD_DIM, ERR, MUTED, OK, PRIMARY, TEXT, WARN,
                     Body, Card, Field, RBtn, Sel, Thumb)
from .picker import open_picker

OUT = output_dir()


def open_externally(path: str) -> None:
    """用系统程序打开文件（Android 走 FileProvider 不可靠，这里尽量温和）。"""
    try:
        if os.environ.get("ANDROID_ARGUMENT"):
            from jnius import autoclass, cast  # noqa: F401
            from android.storage import primary_external_storage_path  # noqa: F401
            # Android 上不强行起 Intent（file:// 在 7.0+ 会崩），交给系统相册/文件管理器
            return
        if sys.platform.startswith("win"):
            os.startfile(path)  # noqa: S606
        else:
            subprocess.Popen(["xdg-open", path])  # noqa: S603,S607
    except Exception:
        pass


def _txt_input(hint: str, height=dp(88), **kw) -> TextInput:
    ti = TextInput(
        hint_text=hint, multiline=True, size_hint_y=None, height=height,
        background_color=(1, 1, 1, 0.9), foreground_color=list(TEXT),
        cursor_color=list(PRIMARY), padding=[dp(10), dp(9), dp(10), dp(9)],
        font_size="14sp", **kw
    )
    return ti


def _scroll(inner) -> ScrollView:
    sv = ScrollView(size_hint=(1, 1), bar_width=dp(3), scroll_type=["bars", "content"])
    sv.add_widget(inner)
    return sv


class Page(Screen):
    """功能页基类：平台/模型行 + 日志 + 任务执行。"""

    capability = "understand"
    title_cn = ""

    # 遮罩上写什么：视频类必须提前说明要等几分钟，否则用户会以为卡死
    BUSY_TEXT = {
        "understand": "正在分析图片…",
        "image": "正在生成图片…",
        "video": "正在生成视频，可能要几分钟…",
        "video_edit": "正在编辑视频，可能要几分钟…",
    }

    def busy_text(self) -> str:
        return self.BUSY_TEXT.get(self.capability, "正在处理…")

    def __init__(self, app, **kw):
        super().__init__(**kw)
        self.app = app
        self.config = app.config
        self.runner: Runner | None = None
        self.root_box = BoxLayout(orientation="vertical", padding=(dp(10), dp(8)), spacing=dp(8))
        self.body = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8))
        self.body.bind(minimum_height=self.body.setter("height"))
        self.add_widget(self.root_box)
        self.root_box.add_widget(_scroll(self.body))
        self.build()

    # ------------------------------------------------------------ 模型行
    def model_row(self, platforms: list[str] | None = None) -> tuple[Spinner, Spinner]:
        plats = platforms or providers.platforms_for(self.capability)
        saved_plat = self.config.get_pref(f"plat_{self.capability}_last", plats[0])
        cur_plat = saved_plat if saved_plat in plats else plats[0]

        row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(8))
        plat = Sel(text=cur_plat, values=plats, size_hint_x=0.42,
                       background_color=(1, 1, 1, 1), color=list(TEXT), font_size="13sp")
        models = Sel(size_hint_x=0.58, background_color=(1, 1, 1, 1),
                         color=list(TEXT), font_size="12.5sp")
        plat.bind(text=lambda _i, v: self._fill_models(models, v))
        self._fill_models(models, cur_plat)
        row.add_widget(plat)
        row.add_widget(models)
        self.body.add_widget(row)
        return plat, models

    def _fill_models(self, spinner: Spinner, platform: str) -> None:
        items = providers.models_for(platform, self.capability)
        ids = [m for m, _ in items]
        if not ids:
            spinner.values = ["（该平台不支持）"]
            spinner.text = "（该平台不支持）"
            return
        spinner.values = ids
        saved = self.config.get_model(platform, self.capability)
        spinner.text = saved if saved in ids else ids[0]
        # 说明放进下拉项不合适（Spinner 只显示 text），这里用长按提示替代不了，
        # 所以把当前模型的说明显示在下面一行（见 model_hint）

    def model_of(self, spinner: Spinner) -> str:
        return (spinner.text or "").split(" · ")[0].strip()

    # ------------------------------------------------------------ 基础交互
    def add_card(self, *widgets, tone=None) -> Card:
        card = Card(tone=list(tone or CARD))
        for w in widgets:
            card.add_widget(w)
        self.body.add_widget(card)
        return card

    def add(self, widget) -> None:
        self.body.add_widget(widget)

    def note(self, text: str, color=MUTED) -> None:
        lab = Field(text=text, color=list(color))
        self.body.add_widget(lab)

    def toast(self, msg: str, color=MUTED) -> None:
        self.app.toast(msg, color)

    def ensure_key(self, platform: str) -> bool:
        if self.config.get_key(platform):
            return True
        self.app.toast(f"「{platform}」还没有配 Key，去「密钥」页填一下", ERR)
        return False

    def start(self, **kw) -> None:
        if self.runner and self.runner.is_alive():
            self.toast("上一个任务还在跑，稍等", WARN)
            return
        self._show_loading()
        r = Runner(
            on_log=lambda lvl, msg: Clock.schedule_once(lambda dt: self._log(lvl, msg), 0),
            on_progress=lambda pct, txt: Clock.schedule_once(lambda dt: self._progress(pct, txt), 0),
            on_done=lambda payload: Clock.schedule_once(lambda dt: self._finish(payload, None), 0),
            on_fail=lambda msg, detail: Clock.schedule_once(
                lambda dt: self._finish(None, (msg, detail)), 0),
            **kw,
        )
        self.runner = r
        try:
            r.start()
        except Exception as exc:      # 线程都起不来时别把遮罩留在屏幕上
            self._hide_loading()
            self.toast(f"任务启动失败：{exc}", ERR)

    # ---- 加载遮罩 ----------------------------------------------------
    def _show_loading(self) -> None:
        try:
            self.app.loading.show(self.busy_text())
        except Exception:
            pass

    def _hide_loading(self) -> None:
        try:
            self.app.loading.hide()
        except Exception:
            pass

    def _finish(self, payload, fail) -> None:
        """先收遮罩再交回页面，避免页面的 _done 抛错时遮罩一直挂着。"""
        self._hide_loading()
        try:
            if fail is None:
                self._done(payload)
            else:
                self._fail(*fail)
        except Exception as exc:
            self.app.log("error", f"处理结果时出错：{exc}")

    def _log(self, level: str, msg: str) -> None:
        self.app.log(level, msg)

    def _progress(self, pct: int, txt: str) -> None:
        if txt:
            self.app.set_status(txt)
            try:
                self.app.loading.update(txt)      # 轮询阶段的"第 N 次检查"也显示在遮罩上
            except Exception:
                pass

    def _done(self, payload: dict) -> None:
        self.app.set_status("完成")

    def _fail(self, message: str, detail: str) -> None:
        plat = getattr(self, "_plat", "")
        hint, url = error_hint.hint_for(message, plat)
        self._hint = hint or ""
        self._hint_url = url or ""
        self.app.log("error", f"失败：{message}")
        if detail:
            self.app.log("error", detail)
        if hint:
            self.app.log("info", f"建议：{hint}")
            if url:
                self.app.log("info", f"入口：{url}")
        self.app.set_status("失败")
        # 提示条优先给「下一步该干什么」，而不是把一长串英文原文塞给用户
        self.app.toast((hint or message)[:110], ERR)

    def failure_text(self, message: str) -> str:
        """结果区显示：建议在前、原始错误压后，方便直接照着做。"""
        hint = getattr(self, "_hint", "")
        url = getattr(self, "_hint_url", "")
        if not hint:
            return f"失败：{message}"
        parts = [f"失败：{hint}"]
        if url:
            parts.append(f"开通 / 管理入口：\n{url}")
        parts.append(f"原始错误：{message[:240]}")
        return "\n\n".join(parts)

    def build(self) -> None:  # 子类实现
        raise NotImplementedError


# ------------------------------------------------------------------ 图像理解
class UnderstandPage(Page):
    capability = "understand"
    title_cn = "理解"

    def build(self):
        self.images: list[str] = []
        self.plat, self.model = self.model_row()

        self.pick_card = self.add_card(
            Field(text="参考图（可选，多张会一起送去理解）", color=list(TEXT)),
            self._pick_row(),
        )
        self.note("支持 png / jpg / webp；图越大越慢，超过 8MB 建议先压缩。")

        self.prompt = _txt_input("想问这张图什么？例如：描述这个场景、列出画面里的零件、判断这个设计有没有干涉")
        self.add_card(Field(text="问题", color=list(TEXT)), self.prompt)

        self.go = RBtn(text="开始理解")
        self.go.bind(on_release=self._run)
        self.add(self.go)

        self.result = _txt_input("结果会显示在这里（可长按复制）", height=dp(220))
        self.result.readonly = True
        self.add_card(Field(text="结果", color=list(TEXT)), self.result)

    def _pick_row(self):
        row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        b = RBtn(text="选择图片", filled=False, size_hint_x=None, width=dp(112))
        b.bind(on_release=lambda *_: open_picker(self._on_pick, "image", 4))
        c = RBtn(text="清空", filled=False, size_hint_x=None, width=dp(64))
        c.bind(on_release=lambda *_: self._clear())
        self.pick_hint = Field(text="未选择", color=list(MUTED))
        row.add_widget(b)
        row.add_widget(c)
        row.add_widget(self.pick_hint)
        return row

    def _on_pick(self, files: list[str]):
        self.images = files[:4]
        self.pick_hint.text = f"已选 {len(self.images)} 张：" + "、".join(
            Path(f).name for f in self.images)

    def _clear(self):
        self.images = []
        self.pick_hint.text = "未选择"

    def _run(self, *_):
        plat = self.plat.text
        self._plat = plat
        if not self.ensure_key(plat):
            return
        q = self.prompt.text.strip() or "描述这张图片的内容与关键细节"
        self.config.set_pref(f"plat_{self.capability}_last", plat)
        self.config.set_model(plat, self.capability, self.model.text)
        self.go.disabled = True
        self.app.set_status("识别中…")
        self.start(kind="understand", platform=plat, model=self.model.text,
                   api_key=self.config.get_key(plat), prompt=q, images=list(self.images))

    def _done(self, payload: dict):
        self.go.disabled = False
        self.app.set_status("完成")
        self.result.text = payload.get("text") or "（没有返回文本）"

    def _fail(self, message: str, detail: str):
        self.go.disabled = False
        super()._fail(message, detail)
        self.result.text = self.failure_text(message)


# ------------------------------------------------------------------ 图像生成
class ImagePage(Page):
    capability = "image"
    title_cn = "生图"

    def build(self):
        self.images: list[str] = []
        self.plat, self.model = self.model_row()

        self.prompt = _txt_input("描述画面：主体、光线、材质、镜头…", height=dp(104))
        self.add_card(Field(text="提示词", color=list(TEXT)), self.prompt)

        opts = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        self.size_sel = Sel(text="1024x1024", values=["1024x1024", "1280x720", "720x1280", "1536x1024", "1024x1536"],
                            size_hint_x=0.55, background_color=(1, 1, 1, 1), color=list(TEXT), font_size="13sp")
        self.count = Sel(text="1 张", values=["1 张", "2 张", "4 张"], size_hint_x=0.45,
                             background_color=(1, 1, 1, 1), color=list(TEXT), font_size="13sp")
        opts.add_widget(self.size_sel)
        opts.add_widget(self.count)
        self.add_card(Field(text="尺寸 / 张数", color=list(TEXT)), opts)

        row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        b = RBtn(text="加参考图（可选）", filled=False, size_hint_x=None, width=dp(156))
        b.bind(on_release=lambda *_: open_picker(self._on_pick, "image", 1))
        c = RBtn(text="清空", filled=False, size_hint_x=None, width=dp(64))
        c.bind(on_release=lambda *_: self._clear())
        self.pick_hint = Field(text="无参考图 = 文生图", color=list(MUTED))
        row.add_widget(b)
        row.add_widget(c)
        row.add_widget(self.pick_hint)
        self.add_card(Field(text="参考图（有则图生图）", color=list(TEXT)), row)

        self.go = RBtn(text="生成图片")
        self.go.bind(on_release=self._run)
        self.add(self.go)

        self.grid = GridLayout(cols=2, spacing=dp(8), size_hint_y=None)
        self.grid.bind(minimum_height=self.grid.setter("height"))
        self.result_card = self.add_card(Field(text="结果", color=list(TEXT)), self.grid)

    def _on_pick(self, files):
        self.images = files[:1]
        self.pick_hint.text = Path(self.images[0]).name

    def _clear(self):
        self.images = []
        self.pick_hint.text = "无参考图 = 文生图"

    def _run(self, *_):
        plat = self.plat.text
        self._plat = plat
        if not self.ensure_key(plat):
            return
        prompt = self.prompt.text.strip()
        if not prompt:
            self.toast("先写提示词", WARN)
            return
        self.config.set_pref(f"plat_{self.capability}_last", plat)
        self.config.set_model(plat, self.capability, self.model.text)
        n = int(self.count.text.split()[0])
        self.go.disabled = True
        self.app.set_status("生成中…")
        self.grid.clear_widgets()
        self.start(kind="image", platform=plat, model=self.model.text,
                   api_key=self.config.get_key(plat), prompt=prompt,
                   images=list(self.images),
                   options={"size": self.size_sel.text, "n": n})

    def _done(self, payload: dict):
        self.go.disabled = False
        self.app.set_status("完成")
        files = payload.get("files") or []
        if not files:
            self.toast("没有拿到图片", ERR)
            return
        for f in files:
            self._add_thumb(f)
        self.toast(f"已保存 {len(files)} 张到 {OUT}")

    def _add_thumb(self, path: str):
        img = Thumb(source="file://" + path, size_hint_y=None, height=dp(150))
        img.bind(on_release=lambda *_: self._preview(path))
        self.grid.add_widget(img)

    def _preview(self, path: str):
        pop = Popup(title=Path(path).name, size_hint=(0.96, 0.92))
        pop.content = AsyncImage(source="file://" + path, allow_stretch=True, keep_ratio=True)
        pop.open()

    def _fail(self, message: str, detail: str):
        self.go.disabled = False
        super()._fail(message, detail)


# ------------------------------------------------------------------ 视频生成
class VideoPage(Page):
    capability = "video"
    title_cn = "视频"

    def build(self):
        self.images: list[str] = []
        self.plat, self.model = self.model_row()

        self.prompt = _txt_input("描述镜头：主体动作、镜头运动、光线、时长感…", height=dp(104))
        self.add_card(Field(text="提示词", color=list(TEXT)), self.prompt)

        row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        b = RBtn(text="参考图（可选）", filled=False, size_hint_x=None, width=dp(136))
        b.bind(on_release=lambda *_: open_picker(self._on_pick, "image", 3))
        c = RBtn(text="清空", filled=False, size_hint_x=None, width=dp(64))
        c.bind(on_release=lambda *_: self._clear())
        self.pick_hint = Field(text="无参考图 = 文生视频；最多 3 张", color=list(MUTED))
        row.add_widget(b)
        row.add_widget(c)
        row.add_widget(self.pick_hint)
        self.add_card(Field(text="参考图（有则图生视频，最多 3 张）", color=list(TEXT)), row)

        opts = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        self.size_sel = Sel(text="1280x720", values=["1280x720", "720x1280", "960x960", "1920x1080"],
                            size_hint_x=0.55, background_color=(1, 1, 1, 1), color=list(TEXT), font_size="13sp")
        self.dur = Sel(text="5 秒", values=["5 秒", "10 秒"], size_hint_x=0.45,
                           background_color=(1, 1, 1, 1), color=list(TEXT), font_size="13sp")
        opts.add_widget(self.size_sel)
        opts.add_widget(self.dur)
        self.add_card(Field(text="尺寸 / 时长", color=list(TEXT)), opts)

        self.go = RBtn(text="生成视频")
        self.go.bind(on_release=self._run)
        self.add(self.go)

        self.out = Field(text="生成的视频会存到 " + str(OUT), color=list(MUTED))
        self.add_card(Field(text="结果", color=list(TEXT)), self.out)
        self.preview = BoxLayout(size_hint_y=None, height=0)
        self.add(self.preview)

    def _on_pick(self, files):
        self.images = files[:3]
        if not self.images:
            self.pick_hint.text = "无参考图 = 文生视频；最多 3 张"
            return
        if len(self.images) == 1:
            self.pick_hint.text = Path(self.images[0]).name
        else:
            self.pick_hint.text = f"已选 {len(self.images)} 张：" + "、".join(
                Path(p).name for p in self.images)

    def _clear(self):
        self.images = []
        self.pick_hint.text = "无参考图 = 文生视频；最多 3 张"

    def _run(self, *_):
        plat = self.plat.text
        self._plat = plat
        if not self.ensure_key(plat):
            return
        prompt = self.prompt.text.strip()
        if not prompt:
            self.toast("先写提示词", WARN)
            return
        self.config.set_pref(f"plat_{self.capability}_last", plat)
        self.config.set_model(plat, self.capability, self.model.text)
        self.go.disabled = True
        self.app.set_status("提交中…")
        self.out.text = "已提交，生成要几分钟，进度看「日志」"
        self.start(kind="video", platform=plat, model=self.model.text,
                   api_key=self.config.get_key(plat), prompt=prompt,
                   images=list(self.images),
                   options={"size": self.size_sel.text, "duration": int(self.dur.text.split()[0])})

    def _done(self, payload: dict):
        self.go.disabled = False
        self.app.set_status("完成")
        path = payload.get("file")
        if not path:
            self.toast("任务结束但没有视频", ERR)
            return
        mb = os.path.getsize(path) / 1024 / 1024 if os.path.exists(path) else 0
        self.out.text = f"已保存：{path}\n{mb:.2f} MB\n用手机的「相册 / 文件管理」打开即可"

    def _fail(self, message: str, detail: str):
        self.go.disabled = False
        super()._fail(message, detail)
        self.out.text = self.failure_text(message)


# ------------------------------------------------------------------ 视频编辑
class EditPage(Page):
    capability = "video_edit"
    title_cn = "改视频"

    NOTES = {
        "阿里百炼": "本地视频 ≤10 MB 自动转 base64，更大的填公网 URL。",
        "火山方舟": "本地视频会先传到方舟文件服务（≤512 MB）再引用。",
        "MiniMax": "本地视频 ≤40 MB 自动转 base64。",
    }

    def build(self):
        self.video = ""
        self.images: list[str] = []
        self.plat, self.model = self.model_row(providers.platforms_for("video_edit"))

        vrow = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        b = RBtn(text="选择视频", filled=False, size_hint_x=None, width=dp(112))
        b.bind(on_release=lambda *_: open_picker(self._on_video, "video", 1))
        c = RBtn(text="清空", filled=False, size_hint_x=None, width=dp(64))
        c.bind(on_release=lambda *_: self._clear_video())
        self.video_hint = Field(text="未选择", color=list(MUTED))
        vrow.add_widget(b)
        vrow.add_widget(c)
        vrow.add_widget(self.video_hint)
        self.video_url = _txt_input("或填公网视频 URL（火山方舟也支持）", height=dp(44))
        self.add_card(Field(text="参考视频", color=list(TEXT)), vrow, self.video_url)

        irow = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        ib = RBtn(text="参考图（可选）", filled=False, size_hint_x=None, width=dp(136))
        ib.bind(on_release=lambda *_: open_picker(self._on_images, "image", 3))
        ic = RBtn(text="清空", filled=False, size_hint_x=None, width=dp(64))
        ic.bind(on_release=lambda *_: self._clear_images())
        self.img_hint = Field(text="未选择", color=list(MUTED))
        irow.add_widget(ib)
        irow.add_widget(ic)
        irow.add_widget(self.img_hint)
        self.add_card(Field(text="参考图（换装 / 换物用）", color=list(TEXT)), irow)

        self.prompt = _txt_input("要改成什么样？例如：把整个画面转换成黏土动画风格，保留人物动作", height=dp(96))
        self.add_card(Field(text="指令", color=list(TEXT)), self.prompt)

        opts = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        self.res = Sel(text="720P", values=["720P", "1080P", "480P"],
                           size_hint_x=0.5, background_color=(1, 1, 1, 1), color=list(TEXT), font_size="13sp")
        self.dur = Sel(text="5 秒", values=["5 秒", "10 秒"], size_hint_x=0.5,
                           background_color=(1, 1, 1, 1), color=list(TEXT), font_size="13sp")
        opts.add_widget(self.res)
        opts.add_widget(self.dur)
        self.add_card(Field(text="分辨率 / 时长", color=list(TEXT)), opts)

        self.go = RBtn(text="开始改视频")
        self.go.bind(on_release=self._run)
        self.add(self.go)

        self.out = Field(text="生成的视频会存到 " + str(OUT), color=list(MUTED))
        self.add_card(Field(text="结果", color=list(TEXT)), self.out)

    def _on_video(self, files):
        self.video = files[0]
        self.video_hint.text = f"{Path(self.video).name}（{file_size_mb(self.video):.1f} MB）"
        self.video_url.text = ""

    def _clear_video(self):
        self.video = ""
        self.video_hint.text = "未选择"

    def _on_images(self, files):
        self.images = files[:3]
        self.img_hint.text = f"已选 {len(self.images)} 张"

    def _clear_images(self):
        self.images = []
        self.img_hint.text = "未选择"

    def _run(self, *_):
        plat = self.plat.text
        self._plat = plat
        if not self.ensure_key(plat):
            return
        prompt = self.prompt.text.strip()
        if not prompt:
            self.toast("先写要改成什么样", WARN)
            return
        source = self.video_url.text.strip() or self.video
        if not source:
            self.toast("先选参考视频或填 URL", WARN)
            return
        self.config.set_pref(f"plat_{self.capability}_last", plat)
        self.config.set_model(plat, self.capability, self.model.text)
        self.go.disabled = True
        self.app.set_status("提交中…")
        self.out.text = "已提交，视频编辑较慢（3–10 分钟），进度看「日志」"
        self.start(kind="video_edit", platform=plat, model=self.model.text,
                   api_key=self.config.get_key(plat), prompt=prompt,
                   images=list(self.images),
                   video_source=source,
                   options={"resolution": self.res.text,
                            "duration": int(self.dur.text.split()[0])})

    def _done(self, payload: dict):
        self.go.disabled = False
        self.app.set_status("完成")
        path = payload.get("file")
        if not path:
            self.toast("任务结束但没有视频", ERR)
            return
        mb = os.path.getsize(path) / 1024 / 1024 if os.path.exists(path) else 0
        self.out.text = f"已保存：{path}\n{mb:.2f} MB\n用手机的「相册 / 文件管理」打开即可"

    def _fail(self, message: str, detail: str):
        self.go.disabled = False
        super()._fail(message, detail)
        self.out.text = self.failure_text(message)


# ------------------------------------------------------------------ 密钥
class KeysPage(Screen):
    TUTORIAL = {
        "火山方舟": "console.volcengine.com/ark → API Key；模型要「开通管理」里开通",
        "阿里百炼": "bailian.console.aliyun.com/cn-beijing → API Key；模型广场里开通",
        "腾讯混元": "console.cloud.tencent.com/tokenhub → API Key；在线推理里启用后付费",
        "智谱 GLM": "bigmodel.cn → API Keys（用「模型标准 API」那类 Key）",
        "百度千帆": "console.bce.baidu.com/iam → API Key（资源选所有资源）",
        "MiniMax": "platform.minimax.cn → 接口密钥（按量付费那套）",
    }
    URLS = {
        "火山方舟": "https://console.volcengine.com/ark/region:ark+cn-beijing/apiKey",
        "阿里百炼": "https://bailian.console.aliyun.com/cn-beijing/model/settings/api-key",
        "腾讯混元": "https://console.cloud.tencent.com/tokenhub/apikey?regionId=1",
        "智谱 GLM": "https://bigmodel.cn/usercenter/proj-mgmt/apikeys",
        "百度千帆": "https://console.bce.baidu.com/iam/#/iam/apikey/list",
        "MiniMax": "https://platform.minimax.cn/console/access?tab=api-keys",
    }

    def __init__(self, app, **kw):
        super().__init__(**kw)
        self.app = app
        self.config = app.config
        box = BoxLayout(orientation="vertical", padding=(dp(10), dp(8)), spacing=dp(8))
        inner = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8))
        inner.bind(minimum_height=inner.setter("height"))
        box.add_widget(_scroll(inner))
        self.add_widget(box)

        inner.add_widget(Field(text="API Key 存在手机本地（XOR+Base64 混淆，不是加密）。\n"
                                    "填完点右边「保存」。Key 与「开通模型」是两件事，"
                                    "后者在下面各行的说明里。", color=list(MUTED)))

        self.inputs: dict[str, TextInput] = {}
        for plat in providers.platforms():
            card = Card(tone=list(CARD))
            head = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(6))
            head.add_widget(Body(text=plat, color=list(TEXT)))
            head.add_widget(Label(text="●", color=list(MUTED), size_hint_x=None, width=dp(18)))
            card.add_widget(head)

            ti = _txt_input("粘贴 API Key", height=dp(44))
            ti.text = self.config.get_key(plat)
            ti.password = True
            self.inputs[plat] = ti
            card.add_widget(ti)

            card.add_widget(Field(text="获取：" + self.TUTORIAL[plat], color=list(MUTED)))

            bar = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
            sv = RBtn(text="保存", filled=True, height=dp(42))
            sv.bind(on_release=lambda _b, p=plat: self._save(p))
            op = RBtn(text="打开控制台", filled=False, height=dp(42), font_size="13sp")
            op.bind(on_release=lambda _b, p=plat: self._open(self.URLS[p]))
            bar.add_widget(sv)
            bar.add_widget(op)
            card.add_widget(bar)
            inner.add_widget(card)

    def _save(self, plat: str):
        val = self.inputs[plat].text.strip()
        self.config.set_key(plat, val)
        self.app.toast(f"{plat} 已保存" if val else f"{plat} 已清空", OK if val else WARN)
        self.app.refresh_key_state()

    def _open(self, url: str):
        try:
            if os.environ.get("ANDROID_ARGUMENT"):
                from jnius import autoclass
                Intent = autoclass("android.content.Intent")
                Uri = autoclass("android.net.Uri")
                PythonActivity = autoclass("org.kivy.android.PythonActivity")
                intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                PythonActivity.mActivity.startActivity(intent)
                return
            import webbrowser
            webbrowser.open(url)
        except Exception as e:
            self.app.toast(f"打不开浏览器：{e}", ERR)


# ------------------------------------------------------------------ 日志
class LogPage(Screen):
    def __init__(self, app, **kw):
        super().__init__(**kw)
        self.app = app
        box = BoxLayout(orientation="vertical", padding=(dp(10), dp(8)), spacing=dp(8))
        bar = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        b1 = RBtn(text="清空", filled=False, height=dp(44))
        b1.bind(on_release=lambda *_: self._clear())
        b2 = RBtn(text="复制全部", filled=False, height=dp(44))
        b2.bind(on_release=lambda *_: self._copy())
        bar.add_widget(b1)
        bar.add_widget(b2)
        box.add_widget(bar)

        self.view = TextInput(readonly=True, multiline=True, font_size="12sp",
                              background_color=(1, 1, 1, 0.94), foreground_color=list(TEXT),
                              padding=[dp(8), dp(8), dp(8), dp(8)])
        box.add_widget(self.view)
        self.add_widget(box)

    def append(self, level: str, msg: str) -> None:
        prefix = {"error": "✗ ", "warn": "! ", "info": "· "}.get(level, "  ")
        self.view.text += f"{prefix}{msg}\n"
        Clock.schedule_once(lambda *_: setattr(self.view, "scroll_y", 0), 0.05)

    def _clear(self):
        self.view.text = ""

    def _copy(self):
        from kivy.core.clipboard import Clipboard
        Clipboard.copy(self.view.text)
        self.app.toast("日志已复制")
