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
seq = [("火山方舟", "tut_volc"), ("百度千帆", "tut_qianfan"), ("MiniMax", "tut_minimax")]

def open_keys():
    d = KeyManagerDialog(w.config, w); d.resize(980, 800); d.show()
    app.processEvents()
    def snap():
        d.grab().save(str(BASE / "logs" / "keys_all_links.png"))
        d.close()
        QTimer.singleShot(250, lambda: run(0))
    QTimer.singleShot(500, snap)

def run(i):
    if i >= len(seq):
        print("done"); app.quit(); return
    name, fname = seq[i]
    t = TutorialDialog(name, w); t.resize(680, 600); t.show()
    app.processEvents()
    def snap():
        t.grab().save(str(BASE / "logs" / f"{fname}.png"))
        t.close()
        QTimer.singleShot(250, lambda: run(i + 1))
    QTimer.singleShot(600, snap)

QTimer.singleShot(900, open_keys)
QTimer.singleShot(15000, app.quit)
app.exec()
