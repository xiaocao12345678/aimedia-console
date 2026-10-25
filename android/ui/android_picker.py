"""Android 原生相册 / 文件选择器（Storage Access Framework）。

为什么不用 Kivy FileChooser：
  · 它要直接遍历 /storage/emulated/0，Android 11+ 必须申请 MANAGE_EXTERNAL_STORAGE，
    而这个权限只给文件管理器类应用——普通应用即使声明了，设置里的开关也是灰的、
    点不动（HyperOS / ColorOS / MIUI 都一样）。这条路本身走不通。
  · 小屏上文件树导航也没法看缩略图。

SAF 的做法是发一个 ACTION_GET_CONTENT Intent，由系统弹相册/文件管理器，
用户选完只把「那一个文件的访问权」交给本应用：
  · 不需要任何存储权限；
  · 选出来的是 content:// URI，用 openFileDescriptor 拿 fd 拷进 cache 目录，
    之后照常当本地路径用。

健壮性约定（重要，闪退就是没做到这些）：
  · 所有 jnius 调用都包 try/except，异常只记录 last_error 并回调空列表，
    **绝不让 JavaException 冒到 Kivy 的回调栈**——那样会直接闪退，且没有任何提示。
  · 用 cast("android.app.Activity", ...) 而不是直接用 mActivity：
    PythonActivity 是 Java 子类，jnius 查父类方法时偶尔解析不到，cast 是官方示例写法。
  · 不用 Intent.createChooser 包一层：多一层 Java 对象就多一个出错面，
    ACTION_GET_CONTENT 本身就会让系统弹出选择器。
"""
from __future__ import annotations

import os
import shutil
from typing import Callable

MIME_IMAGE = "image/*"
MIME_VIDEO = "video/*"


def is_android() -> bool:
    if os.environ.get("ANDROID_ARGUMENT"):
        return True
    try:
        import android  # noqa: F401
        return True
    except Exception:
        return False


class MediaPicker:
    """选图 / 选视频。回调参数是「本地文件路径」列表（已拷进 cache）。"""

    REQUEST_CODE = 0x5E1

    def __init__(self) -> None:
        from android import activity  # p4a 提供，只在 Android 上存在
        from jnius import autoclass, cast

        self._activity_mod = activity
        self._Intent = autoclass("android.content.Intent")
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        # 关键：cast 成 android.app.Activity，保证 startActivityForResult 能被解析到
        self._act = cast("android.app.Activity", PythonActivity.mActivity)
        self._bound = False
        self._on_done: Callable[[list[str]], None] | None = None
        self._limit = 1
        self.last_error = ""

    # ---- 对外入口 ----------------------------------------------------
    def pick(self, on_done: Callable[[list[str]], None], kind: str = "image",
             limit: int = 1) -> None:
        self._on_done = on_done
        self._limit = max(1, int(limit))

        try:
            if not self._bound:
                self._activity_mod.bind(on_activity_result=self._on_activity_result)
                self._bound = True

            Intent = self._Intent
            intent = Intent(Intent.ACTION_GET_CONTENT)
            intent.setType(MIME_IMAGE if kind == "image" else MIME_VIDEO)
            intent.addCategory(Intent.CATEGORY_OPENABLE)
            try:
                intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            except Exception:
                pass
            if self._limit > 1:
                # 某些 ROM 对 putExtra 的布尔装箱敏感，失败就退化成单选
                try:
                    intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, True)
                except Exception:
                    pass

            self._act.startActivityForResult(intent, self.REQUEST_CODE)
        except Exception as exc:  # 绝不把异常抛给 Kivy
            self.last_error = f"{type(exc).__name__}: {exc}"
            cb, self._on_done = self._on_done, None
            if cb is not None:
                try:
                    cb([])
                except Exception:
                    pass

    # ---- 回调 --------------------------------------------------------
    def _on_activity_result(self, request_code, result_code, intent) -> None:
        if request_code != self.REQUEST_CODE:
            return
        cb = self._on_done
        self._on_done = None
        if cb is None:
            return

        paths: list[str] = []
        try:
            # RESULT_OK == -1
            if result_code == -1 and intent is not None:
                uris = []
                clip = intent.getClipData()
                if clip is not None:
                    for i in range(clip.getItemCount()):
                        uris.append(clip.getItemAt(i).getUri())
                else:
                    data = intent.getData()
                    if data is not None:
                        uris.append(data)

                for uri in uris[: self._limit]:
                    try:
                        dest = self._copy_to_cache(uri)
                        if dest:
                            paths.append(dest)
                    except Exception as exc:
                        self.last_error = f"copy {type(exc).__name__}: {exc}"
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
        finally:
            try:
                cb(paths)
            except Exception:
                pass

    # ---- content:// → 本地文件 --------------------------------------
    def _copy_to_cache(self, uri) -> str | None:
        resolver = self._act.getContentResolver()

        name = self._display_name(resolver, uri) or "picked"
        cache_dir = self._act.getCacheDir().getAbsolutePath()
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
