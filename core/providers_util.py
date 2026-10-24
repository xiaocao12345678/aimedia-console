"""文件名与目录工具。"""
from __future__ import annotations

import datetime as _dt
import uuid
from pathlib import Path

from .paths import output_dir


def ensure_output() -> Path:
    return output_dir()


def stamp(prefix: str, ext: str) -> Path:
    ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    return ensure_output() / f"{prefix}_{ts}_{uuid.uuid4().hex[:6]}{ext}"
