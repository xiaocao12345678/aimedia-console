"""Android 版路径：与桌面版同一套接口，但目录按 Android 规则放。

- 应用私有目录（$ANDROID_PRIVATE）= 可写的根：配置、日志
- 外部存储 /sdcard/Download/AI多模态控制台 = 用户能看到的产物（图片、视频）

Android 上 /sdcard 写入在 Android 11+ 需要 MANAGE_EXTERNAL_STORAGE（打包时已声明，
首次使用会在系统里弹授权，需手动允许）。
"""
from __future__ import annotations

import os
from pathlib import Path

APP_DIRNAME = "AI多模态控制台"


def is_android() -> bool:
    return "ANDROID_ARGUMENT" in os.environ or "ANDROID_PRIVATE" in os.environ


def _private_root() -> Path:
    p = os.environ.get("ANDROID_PRIVATE")
    if p:
        return Path(p)
    return Path.home() / ".ai_media_console"


def _external_root() -> Path:
    for key in ("EXTERNAL_STORAGE", "SECONDARY_STORAGE"):
        v = os.environ.get(key)
        if v:
            first = v.split(":")[0]
            if Path(first).is_dir():
                return Path(first)
    guess = Path("/storage/emulated/0")
    return guess if guess.is_dir() else _private_root()


def app_dir() -> Path:
    """可写根目录（配置、日志）。"""
    if is_android():
        d = _private_root()
    else:
        d = Path(__file__).resolve().parent.parent
    d.mkdir(parents=True, exist_ok=True)
    return d


def resource_dir() -> Path:
    """只读资源（assets/）。打包后资源在 app 根目录里。"""
    if is_android():
        return _private_root().parent
    return Path(__file__).resolve().parent.parent


def asset_path(name: str) -> str:
    return (resource_dir() / "assets" / name).as_posix()


def output_dir() -> Path:
    """产物目录：Android 放外部存储的 Download，桌面放项目目录。"""
    if is_android():
        d = _external_root() / "Download" / APP_DIRNAME
        try:
            d.mkdir(parents=True, exist_ok=True)
            # 写一个探测文件，确认真的可写（权限没给时会抛）
            probe = d / ".write_test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            return d
        except Exception:
            d = _private_root() / "output"
            d.mkdir(parents=True, exist_ok=True)
            return d
    d = app_dir() / "output"
    d.mkdir(parents=True, exist_ok=True)
    return d


def log_dir() -> Path:
    d = app_dir() / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d
