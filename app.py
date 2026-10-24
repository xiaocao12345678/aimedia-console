"""程序入口：单实例、全局异常兜底、高 DPI。"""
from __future__ import annotations

import ctypes
import datetime as _dt
import os
import sys
import traceback
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from PyQt6.QtCore import Qt  # noqa: E402
from PyQt6.QtGui import QFont  # noqa: E402
from PyQt6.QtWidgets import QApplication, QMessageBox  # noqa: E402

APP_ID = "ai-multimodal-console-9f31"


def _log_path() -> Path:
    from core.paths import log_dir

    return log_dir() / f"app_{_dt.datetime.now():%Y%m%d}.log"


def install_excepthook() -> None:
    def hook(exc_type, exc, tb):
        text = "".join(traceback.format_exception(exc_type, exc, tb))
        try:
            with open(_log_path(), "a", encoding="utf-8") as f:
                f.write(f"\n===== {_dt.datetime.now():%Y-%m-%d %H:%M:%S} =====\n{text}")
        except Exception:
            pass
        try:
            box = QMessageBox()
            box.setIcon(QMessageBox.Icon.Critical)
            box.setWindowTitle("程序出错")
            box.setText(f"{exc_type.__name__}: {exc}")
            box.setDetailedText(text)
            box.exec()
        except Exception:
            sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = hook


def single_instance_guard(app: QApplication) -> bool:
    """已有一个实例在跑时，把它的窗口提到前台并返回 False。"""
    try:
        from PyQt6.QtNetwork import QLocalServer, QLocalSocket
    except Exception:
        return True
    sock = QLocalSocket()
    sock.connectToServer(APP_ID)
    if sock.waitForConnected(200):
        sock.write(b"raise")
        sock.flush()
        sock.waitForBytesWritten(200)
        sock.disconnectFromServer()
        return False
    QLocalServer.removeServer(APP_ID)
    server = QLocalServer(app)
    server.listen(APP_ID)
    app._instance_server = server  # 保持引用，防止被回收
    return True


def main() -> int:
    if os.name == "nt":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName("AI 多模态控制台")
    app.setStyle("Fusion")
    app.setFont(QFont("Microsoft YaHei UI", 10))
    install_excepthook()

    if not single_instance_guard(app):
        return 0

    from ui.main_window import MainWindow

    win = MainWindow()
    win.show()
    win.raise_()
    win.activateWindow()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
