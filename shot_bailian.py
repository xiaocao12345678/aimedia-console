import sys
from pathlib import Path
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication
app = QApplication(sys.argv); app.setStyle("Fusion")
app.setFont(QFont("Microsoft YaHei UI", 10))
from ui.key_manager import TutorialDialog, KeyManagerDialog
from ui.main_window import MainWindow

w = MainWindow(); w.resize(1300, 900); w.show()

def step1():
    d = KeyManagerDialog(w.config, w); d.resize(980, 800); d.show()
    app.processEvents()
    QTimer.singleShot(500, lambda: step2(d))

def step2(d):
    d.grab().save(str(BASE / "logs" / "keys_updated.png"))
    d.close()
    t = TutorialDialog("阿里百炼", w); t.resize(680, 600); t.show()
    app.processEvents()
    QTimer.singleShot(600, lambda: step3(t))

def step3(t):
    t.grab().save(str(BASE / "logs" / "tutorial_bailian.png"))
    t.close(); print("saved"); app.quit()

QTimer.singleShot(900, step1)
QTimer.singleShot(9000, app.quit)
app.exec()
