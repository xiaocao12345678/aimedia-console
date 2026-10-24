"""最小复现：QSS 箭头图在中文路径 vs 英文路径下是否都能显示"""
import os, shutil, sys
from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QComboBox, QVBoxLayout, QWidget

BASE = Path(__file__).resolve().parent
src = BASE / "assets" / "combo_arrow.png"
# 英文路径副本
eng_dir = Path(os.environ.get("TEMP", ".")) / "arrow_test"
eng_dir.mkdir(parents=True, exist_ok=True)
eng = eng_dir / "combo_arrow.png"
shutil.copy2(src, eng)

cn_path = src.as_posix()
en_path = eng.as_posix()
print("cn:", cn_path)
print("en:", en_path)

app = QApplication(sys.argv)
app.setStyle("Fusion")

w = QWidget()
w.resize(520, 200)
lay = QVBoxLayout(w)

def mk(label, arrow, widget_qss):
    cb = QComboBox()
    cb.addItems(["模型 A · 选项一", "模型 B · 选项二"])
    cb.setMinimumHeight(30)
    cb.setStyleSheet(widget_qss.replace("__ARROW__", arrow))
    lay.addWidget(cb)
    print(label, "styleSheet len", len(cb.styleSheet()))
    return cb

base_qss = """
QComboBox { background: rgba(255,255,255,0.8); border:1px solid #94aac4; border-radius:8px; padding:5px 8px; }
QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: center right; width:24px; border:none; }
QComboBox::down-arrow { image: url(__ARROW__); width:12px; height:12px; margin-right:6px; }
"""
mk("中文路径", cn_path, base_qss)
cb = mk("英文路径", en_path, base_qss)
ed = QComboBox()
ed.setEditable(True)
ed.addItems(["可编辑 模型 A · 选项一", "可编辑 模型 B · 选项二"])
ed.setMinimumHeight(30)
ed.setStyleSheet(base_qss.replace("__ARROW__", en_path))
lay.addWidget(ed)
ed2 = QComboBox()
ed2.setEditable(True)
ed2.addItems(["可编辑+右padding 模型 A", "可编辑+右padding 模型 B"])
ed2.setMinimumHeight(30)
ed2.setStyleSheet(
    base_qss.replace("__ARROW__", en_path)
    + "QComboBox { padding-right: 30px; }"
)
lay.addWidget(ed2)
w.resize(520, 300)
w.show()

def shot():
    w.grab().save(str(BASE / "logs" / "arrow_test.png"))
    print("saved")
    app.quit()

QTimer.singleShot(800, shot)
app.exec()
