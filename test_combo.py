import sys
from pathlib import Path
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

app = QApplication(sys.argv)
app.setStyle("Fusion")
app.setFont(QFont("Microsoft YaHei UI", 10))

from core import providers

print("=== 各平台可用模型数（理解/生图/生视频）===")
for p in providers.platforms():
    counts = {providers.capability_label(c): len(providers.models_for(p, c)) for c in ("understand", "image", "video")}
    print(f"{p:<8} {counts}")

from ui.main_window import MainWindow
w = MainWindow()
w.resize(1300, 900)
w.show()

def open_popup():
    box = w.page_understand.model_box
    box.showPopup()
    app.processEvents()
    QTimer.singleShot(500, snap)

def snap():
    screen = app.primaryScreen()
    pm = screen.grabWindow(0)
    ok = pm.save(str(BASE / "logs" / "glass_combo.png"))
    print("popup screenshot saved:", ok, pm.width(), "x", pm.height())
    w.page_understand.model_box.hidePopup()
    app.quit()

QTimer.singleShot(900, open_popup)
QTimer.singleShot(6000, app.quit)
app.exec()
