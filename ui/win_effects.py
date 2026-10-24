"""Windows 窗口效果：亚克力（Acrylic）/ Mica 背景与圆角。

⚠ 所有 ctypes 调用都必须显式声明 argtypes / restype。
64 位进程的 HWND 是 64 位指针，而 ctypes 默认按 c_int（32 位）传参，
句柄被截断后调用 DwmSetWindowAttribute 会直接 access violation（进程闪退）。
"""
from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

IS_WINDOWS = sys.platform.startswith("win")

DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWA_SYSTEMBACKDROP_TYPE = 38

DWMWCP_DEFAULT = 0
DWMWCP_ROUND = 2

DWMSBT_MAINWINDOW = 2       # Mica
DWMSBT_TRANSIENTWINDOW = 3  # Acrylic
DWMSBT_TABBEDWINDOW = 4

_dwmapi = None
_user32 = None


def _libs():
    global _dwmapi, _user32
    if not IS_WINDOWS:
        return None, None
    if _dwmapi is None:
        _dwmapi = ctypes.WinDLL("dwmapi")
        _dwmapi.DwmSetWindowAttribute.argtypes = [
            wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD
        ]
        _dwmapi.DwmSetWindowAttribute.restype = ctypes.c_long

        _user32 = ctypes.WinDLL("user32", use_last_error=True)
        _user32.SetWindowCompositionAttribute.argtypes = [wintypes.HWND, ctypes.c_void_p]
        _user32.SetWindowCompositionAttribute.restype = wintypes.BOOL
        _user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        _user32.GetWindowRect.restype = wintypes.BOOL
    return _dwmapi, _user32


def windows_build() -> int:
    try:
        return int(sys.getwindowsversion().build)
    except Exception:
        return 0


def _dwm_set(hwnd: int, attr: int, value: int) -> bool:
    dwmapi, _ = _libs()
    if dwmapi is None:
        return False
    try:
        v = ctypes.c_int(value)
        res = dwmapi.DwmSetWindowAttribute(
            ctypes.c_void_p(hwnd), attr, ctypes.byref(v), ctypes.sizeof(v)
        )
        return int(res) == 0
    except Exception:
        return False


class _ACCENTPOLICY(ctypes.Structure):
    _fields_ = [
        ("AccentState", ctypes.c_int),
        ("AccentFlags", ctypes.c_int),
        ("GradientColor", ctypes.c_uint),
        ("AnimationId", ctypes.c_int),
    ]


class _WCADATA(ctypes.Structure):
    _fields_ = [
        ("Attribute", ctypes.c_int),
        ("Data", ctypes.c_void_p),
        ("SizeOfData", ctypes.c_size_t),
    ]


def _accent_blur(hwnd: int, gradient_argb: int = 0x66F4F8FD, accent_state: int = 4) -> bool:
    """亚克力/模糊。gradient_argb 是 0xAABBGGRR，alpha 决定奶白浓度。

    accent_state: 3 = ACCENT_ENABLE_BLURBEHIND（纯模糊）
                  4 = ACCENT_ENABLE_ACRYLICBLURBEHIND（亚克力，带着色）
    """
    _, user32 = _libs()
    if user32 is None:
        return False
    try:
        accent = _ACCENTPOLICY()
        accent.AccentState = accent_state
        accent.AccentFlags = 2
        accent.GradientColor = gradient_argb
        data = _WCADATA()
        data.Attribute = 19  # WCA_ACCENT_POLICY
        data.Data = ctypes.cast(ctypes.pointer(accent), ctypes.c_void_p)
        data.SizeOfData = ctypes.sizeof(accent)
        res = user32.SetWindowCompositionAttribute(ctypes.c_void_p(hwnd), ctypes.byref(data))
        return bool(res)
    except Exception:
        return False


def apply_glass(hwnd: int, dark: bool = False) -> str:
    """给窗口启用玻璃背景，返回实际生效的方式。hwnd 必须是有效窗口句柄。"""
    if not IS_WINDOWS or not hwnd:
        return "none"
    build = windows_build()
    _dwm_set(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, 1 if dark else 0)
    _dwm_set(hwnd, DWMWA_WINDOW_CORNER_PREFERENCE, DWMWCP_ROUND)

    # 首选：Win11 的 DWM SystemBackdrop（非 layered 窗口才绘制）
    if build >= 22621 and _dwm_set(hwnd, DWMWA_SYSTEMBACKDROP_TYPE, DWMSBT_TRANSIENTWINDOW):
        return "dwm-acrylic"
    if build >= 22000 and _dwm_set(hwnd, DWMWA_SYSTEMBACKDROP_TYPE, DWMSBT_MAINWINDOW):
        return "dwm-mica"
    # 回退：老接口（layered 窗口也能出模糊，Win10 常用）
    if _accent_blur(hwnd):
        return "accent-acrylic"
    if _accent_blur(hwnd, accent_state=3, gradient_argb=0x00000000):
        return "accent-blur"
    return "none"


def round_corners(hwnd: int, on: bool = True) -> None:
    if IS_WINDOWS and windows_build() >= 22000 and hwnd:
        _dwm_set(hwnd, DWMWA_WINDOW_CORNER_PREFERENCE, DWMWCP_ROUND if on else DWMWCP_DEFAULT)


def window_rect(hwnd: int):
    _, user32 = _libs()
    if user32 is None:
        return None
    rect = wintypes.RECT()
    if user32.GetWindowRect(ctypes.c_void_p(hwnd), ctypes.byref(rect)):
        return rect
    return None
