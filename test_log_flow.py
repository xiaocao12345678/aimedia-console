"""验证：任务日志真的进到独立日志窗口（用假 Key 打真实端点，零成本）"""
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
from core.tasks import Task

w = MainWindow()
w.resize(1300, 900)
w.show()
w.open_log_window()

img = BASE / "logs" / "probe.png"
task = Task("understand", "智谱 GLM", "glm-4.6v", "sk-invalid-probe", prompt="描述这张图", images=[str(img)])
task.sig_log.connect(w.append_log)
task.sig_fail.connect(lambda m, d: w.append_log("error", f"任务失败：{m}"))
task.sig_progress.connect(lambda p, t: w.page_understand.on_progress(p, t))
task.start()


def check():
    n = len(w.log_window._records)
    has_401 = any("401" in rec[2] for rec in w.log_window._records)
    has_req = any(rec[1] == "request" for rec in w.log_window._records)
    has_resp = any(rec[1] == "response" for rec in w.log_window._records)
    has_fail = any("任务失败" in rec[2] for rec in w.log_window._records)
    print(f"日志窗口记录数={n}")
    print(f"  含请求={has_req} 含响应={has_resp} 含401={has_401} 含失败原因={has_fail}")
    print(f"  主界面状态行={w.state_label.text()[:60]}")
    print(f"  日志窗口角标={w.log_window.badge.text()}")
    w.log_window.grab().save(str(BASE / "logs" / "glass_log_filled.png"))
    w.page_understand.grab().save(str(BASE / "logs" / "glass_understand2.png"))
    app.quit()


QTimer.singleShot(9000, check)
QTimer.singleShot(15000, app.quit)
app.exec()
