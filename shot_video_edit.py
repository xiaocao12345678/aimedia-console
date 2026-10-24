import sys
from pathlib import Path
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication
app = QApplication(sys.argv); app.setStyle("Fusion")
app.setFont(QFont("Microsoft YaHei UI", 10))
from ui.main_window import MainWindow

w = MainWindow(); w.resize(1300, 900); w.show()

def shot():
    w.tabs.setCurrentIndex(4)   # 视频编辑
    app.processEvents()
    QTimer.singleShot(400, grab)

def grab():
    w.grab().save(str(BASE / "logs" / "glass_video_edit.png"))
    page = w.page_video_edit
    print("tabs:", [w.tabs.tabText(i) for i in range(w.tabs.count())])
    print("支持平台:", [page.model_row.platform_box.itemText(i) for i in range(page.model_row.platform_box.count())])
    print("当前平台:", page.model_row.platform(), "模型:", page.model_row.model())
    print("提示:", page.plat_note.text()[:60])
    app.quit()

QTimer.singleShot(1000, shot)
QTimer.singleShot(8000, app.quit)
app.exec()
