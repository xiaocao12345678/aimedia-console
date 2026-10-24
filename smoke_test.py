"""冒烟测试：启动界面、截图、退出。用于自证界面能正常渲染。"""
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont

app = QApplication(sys.argv)
app.setStyle("Fusion")
app.setFont(QFont("Microsoft YaHei UI", 10))

from ui.main_window import MainWindow

w = MainWindow()
w.resize(1280, 880)
w.show()

shots = []

def shot():
    p = BASE / "logs" / "smoke_tabs.png"
    p.parent.mkdir(parents=True, exist_ok=True)
    # 依次切三个标签各截一张
    for i, name in enumerate(["understand", "image", "video"]):
        w.tabs.setCurrentIndex(i)
        app.processEvents()
        q = BASE / "logs" / f"smoke_{name}.png"
        w.grab().save(str(q))
        shots.append(str(q))
    w.tabs.setCurrentIndex(0)
    print("SHOTS:", shots)
    app.quit()

QTimer.singleShot(1200, shot)
app.exec()
