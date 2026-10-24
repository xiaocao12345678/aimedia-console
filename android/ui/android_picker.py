"""Android 原生相册 / 文件选择器（Storage Access Framework）。

为什么不用 Kivy FileChooser：
  · 它要直接遍历 /storage/emulated/0，Android 11+ 必须申请 MANAGE_EXTERNAL_STORAGE，
    用户得去系统设置里手动开「所有文件访问」，很多人找不到入口；
  · 小屏上文件树导航体验差，看不到缩略图。

SAF 的做法是发一个 ACTION_GET_CONTENT Intent，由系统弹相册/文件管理器，
用户选完只把「那一个文件的访问权」交给本应用：
  · 不需要任何存储权限；
  · 选出来的是 content:// URI，用 openFileDescriptor 拿 fd 拷进 cache 目录，
    之后照常当本地路径用。

桌面/非 Android 平台直接返回 False，调用方 fallback 到 Kivy 的 FilePicker。
"""
from __future__ import annotations

import os
import shutil
from typing import Callable

MIME_IMAGE = "image/*"
MIME_VIDEO = "video/*"


def is_android() -> bool:
    return bool(os.environ.get("ANDROID_ARGUMENT"))


class MediaPicker:
    """选图 / 选视频。回调参数是「本地文件路径」列表（已拷进 cache）。"""

    REQUEST_CODE = 0x5E1

    def __init__(self) -> None:
        from android import activity  # p4a 提供，只在 Android 上存在
        from jnius import autoclass

        self._activity_mod = activity
        self._Intent = autoclass("android.content.Intent")
        self._PythonActivity = autoclass("org.kivy.android.PythonActivity")
        self._bound = False
        self._on_done: Callable[[list[str]], None] | None = None
        self._limit = 1

    # ---- 对外入口 ----------------------------------------------------
    def pick(self, on_done: Callable[[list[str]], None], kind: str = "image",
             limit: int = 1) -> None:
        self._on_done = on_done
        self._limit = max(1, int(limit))

        if not self._bound:
            self._activity_mod.bind(on_activity_result=self._on_activity_result)
            self._bound = True

        Intent = self._Intent
        intent = Intent(Intent.ACTION_GET_CONTENT)
        intent.setType(MIME_IMAGE if kind == "image" else MIME_VIDEO)
        intent.addCategory(Intent.CATEGORY_OPENABLE)
        if self._limit > 1:
            intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, True)

        act = self._PythonActivity.mActivity
        # 用 chooser 包装一次，避免用户默认关联到某个奇怪的应用
        chooser = Intent.createChooser(intent, "选择" + ("图片" if kind == "image" else "视频"))
        act.startActivityForResult(chooser, self.REQUEST_CODE)

    # ---- 回调 --------------------------------------------------------
    def _on_activity_result(self, request_code, result_code, intent) -> None:
        if request_code != self.REQUEST_CODE:
            return
        cb = self._on_done
        self._on_done = None
        if cb is None:
            return

        # RESULT_OK == -1
        if result_code != -1 or intent is None:
            cb([])
            return

        uris = []
        try:
            clip = intent.getClipData()
            if clip is not None:
                for i in range(clip.getItemCount()):
                    uris.append(clip.getItemAt(i).getUri())
            else:
                data = intent.getData()
                if data is not None:
                    uris.append(data)
        except Exception:
            cb([])
            return

        paths: list[str] = []
        for uri in uris[: self._limit]:
            try:
                dest = self._copy_to_cache(uri)
                if dest:
                    paths.append(dest)
            except Exception:
                continue
        cb(paths)

    # ---- content:// → 本地文件 --------------------------------------
    def _copy_to_cache(self, uri) -> str | None:
        act = self._PythonActivity.mActivity
        resolver = act.getContentResolver()

        name = self._display_name(resolver, uri) or "picked"
        # 保证唯一，避免同名覆盖
        cache_dir = act.getCacheDir().getAbsolutePath()
        stem, ext = os.path.splitext(name)
        dest = os.path.join(cache_dir, name)
        n = 1
        while os.path.exists(dest):
            dest = os.path.join(cache_dir, f"{stem}_{n}{ext}")
            n += 1

        pfd = resolver.openFileDescriptor(uri, "r")
        if pfd is None:
            return None
        fd = pfd.detachFd()
        try:
            with os.fdopen(fd, "rb") as src, open(dest, "wb") as dst:
                shutil.copyfileobj(src, dst, 1024 * 256)
        except Exception:
            try:
                os.remove(dest)
            except OSError:
                pass
            return None
        return dest

    @staticmethod
    def _display_name(resolver, uri) -> str | None:
        try:
            cursor = resolver.query(uri, ["_display_name"], None, None, None)
            if cursor is None:
                return None
            try:
                if cursor.moveToFirst():
                    return cursor.getString(0)
            finally:
                cursor.close()
        except Exception:
            return None
        return None
