"""运行路径：区分「开发时」和「打包成 EXE 之后」。

打包后（PyInstaller onedir）：
- 只读资源（assets 图标）在 sys._MEIPASS 里（即 EXE 同级的 _internal 目录）
- 可写目录（output / logs）必须放在 EXE 同级，不能写进 _MEIPASS（可能是只读或临时目录）
所以这里分两套：resource_dir() 与 app_dir()。
"""
from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_dir() -> Path:
    """可写根目录：打包后是 EXE 所在目录，开发时是项目根目录。"""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def resource_dir() -> Path:
    """只读资源根目录（assets/ 等）。"""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", app_dir()))
    return Path(__file__).resolve().parent.parent


def asset_path(name: str) -> str:
    return (resource_dir() / "assets" / name).as_posix()


def output_dir() -> Path:
    d = app_dir() / "output"
    d.mkdir(parents=True, exist_ok=True)
    return d


def log_dir() -> Path:
    d = app_dir() / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d
