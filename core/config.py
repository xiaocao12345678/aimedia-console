"""配置读写：API Key 与界面偏好。

Key 只保存在本机用户目录，用定长 XOR + Base64 做混淆（防止肉眼直视/误截图），
不是加密：任何能读到本机文件的人都能还原。需要真正保密请用系统凭据管理器。
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any

APP_NAME = "AI多模态控制台"

_XOR_KEY = b"m3dia-console-2026"


def appdata_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    d = Path(base) / APP_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def obfuscate(text: str) -> str:
    if not text:
        return ""
    raw = text.encode("utf-8")
    out = bytes(b ^ _XOR_KEY[i % len(_XOR_KEY)] for i, b in enumerate(raw))
    return base64.b64encode(out).decode("ascii")


def deobfuscate(text: str) -> str:
    if not text:
        return ""
    try:
        raw = base64.b64decode(text.encode("ascii"))
        out = bytes(b ^ _XOR_KEY[i % len(_XOR_KEY)] for i, b in enumerate(raw))
        return out.decode("utf-8")
    except Exception:
        return ""


def config_path() -> Path:
    """优先用 EXE 同级的 config.json（便携），没有才落到 %APPDATA%。"""
    from .paths import app_dir

    portable = app_dir() / "config.json"
    if portable.exists():
        return portable
    return appdata_dir() / "config.json"


class Config:
    def __init__(self) -> None:
        from .paths import app_dir

        self.path = config_path()
        self.portable = self.path == app_dir() / "config.json"
        self.data: dict[str, Any] = {"api_keys": {}, "models": {}, "prefs": {}}
        self.load()

    def load(self) -> None:
        if self.path.exists():
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    self.data.setdefault("api_keys", {}).update(loaded.get("api_keys") or {})
                    self.data.setdefault("models", {}).update(loaded.get("models") or {})
                    self.data.setdefault("prefs", {}).update(loaded.get("prefs") or {})
            except Exception:
                # 配置损坏不应阻止程序启动
                backup = self.path.with_suffix(".broken.json")
                try:
                    self.path.replace(backup)
                except Exception:
                    pass

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        tmp.replace(self.path)

    # ---- key ----
    def get_key(self, platform: str) -> str:
        return deobfuscate(self.data["api_keys"].get(platform, ""))

    def set_key(self, platform: str, key: str) -> None:
        if key.strip():
            self.data["api_keys"][platform] = obfuscate(key.strip())
        else:
            self.data["api_keys"].pop(platform, None)
        self.save()

    def has_key(self, platform: str) -> bool:
        return bool(self.data["api_keys"].get(platform))

    # ---- 模型选择记忆 ----
    def get_model(self, platform: str, capability: str) -> str:
        return (self.data["models"].get(platform) or {}).get(capability, "")

    def set_model(self, platform: str, capability: str, model: str) -> None:
        self.data["models"].setdefault(platform, {})[capability] = model
        self.save()

    # ---- 界面偏好 ----
    def get_pref(self, name: str, default: Any = None) -> Any:
        return (self.data.get("prefs") or {}).get(name, default)

    def set_pref(self, name: str, value: Any) -> None:
        self.data.setdefault("prefs", {})[name] = value
        self.save()
