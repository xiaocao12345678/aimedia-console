"""界面自检（玻璃版）：主窗口 / 伪最大化 / 密钥管理对话框 截图与尺寸校验。"""
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

from ui.main_window import MainWindow
from ui.key_manager import KeyManagerDialog, TutorialDialog

SHOT_DIR = BASE / "logs"
SHOT_DIR.mkdir(parents=True, exist_ok=True)
report = []

w = MainWindow()
w.resize(1300, 900)
w.show()


def step1():
    w.tabs.setCurrentIndex(0)
    app.processEvents()
    w.grab().save(str(SHOT_DIR / "glass_workflow.png"))
    for idx, name in ((1, "understand"), (2, "image"), (3, "video")):
        w.tabs.setCurrentIndex(idx)
        app.processEvents()
        w.grab().save(str(SHOT_DIR / f"glass_{name}.png"))
    w.tabs.setCurrentIndex(0)
    app.processEvents()
    report.append(f"acrylic={w.acrylic_method} ({w.acrylic_method_note()})")
    report.append(f"normal geometry={w.width()}x{w.height()}")
    w.open_log_window()
    app.processEvents()
    QTimer.singleShot(600, step1b)


def step1b():
    if w.log_window is not None:
        w.log_window.grab().save(str(SHOT_DIR / "glass_log.png"))
        report.append(
            f"log window {w.log_window.width()}x{w.log_window.height()} "
            f"records={len(w.log_window._records)} acrylic={w.log_window.acrylic_method}"
        )
    QTimer.singleShot(200, step2)


def step2():
    w.toggle_maximize()
    app.processEvents()
    QTimer.singleShot(500, step3)


def step3():
    avail = app.primaryScreen().availableGeometry()
    geo = w.geometry()
    ok = abs(geo.width() - avail.width()) <= 2 and abs(geo.height() - avail.height()) <= 2
    report.append(
        f"pseudo-max: window={geo.width()}x{geo.height()} available={avail.width()}x{avail.height()} "
        f"铺满工作区={ok} 遮任务栏={'否' if ok else '是'}"
    )
    w.grab().save(str(SHOT_DIR / "glass_maximized.png"))
    w.toggle_maximize()
    app.processEvents()
    report.append(f"restored geometry={w.width()}x{w.height()} pseudo_max={w.is_pseudo_maximized()}")
    QTimer.singleShot(300, step4)


def step4():
    dlg = KeyManagerDialog(w.config, w)
    dlg.resize(980, 800)
    dlg.show()
    app.processEvents()
    QTimer.singleShot(600, lambda: step5(dlg))


def step5(dlg):
    dlg.grab().save(str(SHOT_DIR / "glass_keys.png"))
    report.append(
        f"key dialog {dlg.width()}x{dlg.height()} rows={len(dlg.rows)} "
        f"summary={dlg.summary.text()} acrylic={dlg.acrylic_method}"
    )
    dlg.close()
    QTimer.singleShot(300, step6)


def step6():
    tut = TutorialDialog("智谱 GLM", w)
    tut.resize(680, 560)
    tut.show()
    app.processEvents()
    QTimer.singleShot(700, lambda: step7(tut))


def step7(tut):
    tut.grab().save(str(SHOT_DIR / "glass_tutorial.png"))
    report.append(f"tutorial dialog {tut.width()}x{tut.height()} acrylic={tut.acrylic_method}")
    tut.close()
    QTimer.singleShot(200, step8)


def step8():
    tut = TutorialDialog("百度千帆", w)
    tut.resize(680, 560)
    tut.show()
    app.processEvents()
    QTimer.singleShot(600, lambda: step9(tut))


def step9(tut):
    tut.grab().save(str(SHOT_DIR / "glass_tutorial2.png"))
    tut.close()
    for line in report:
        print(line, flush=True)
    app.quit()


QTimer.singleShot(1200, step1)
QTimer.singleShot(15000, app.quit)
app.exec()
