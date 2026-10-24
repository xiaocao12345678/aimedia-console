"""线程链路测试：假 Key 走完整 Task 流程，验证信号、日志与错误展示。"""
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from core.tasks import Task

app = QApplication(sys.argv)
img = BASE / "logs" / "probe.png"
events = []

task = Task("understand", "智谱 GLM", "glm-4.6v", "sk-invalid-probe", prompt="描述这张图", images=[str(img)])
task.sig_log.connect(lambda lvl, msg: events.append(("log", lvl, msg.splitlines()[0][:110])))
task.sig_progress.connect(lambda p, t: events.append(("progress", str(p), t)))
task.sig_done.connect(lambda payload: events.append(("done", str(payload)[:80], "")))
task.sig_fail.connect(lambda m, d: events.append(("fail", m[:160], d[:80])))
task.finished.connect(app.quit)
task.start()
QTimer.singleShot(90000, app.quit)
app.exec()

for e in events:
    print(e)

ok = any(e[0] == "fail" and ("401" in e[1] or "HTTP" in e[1]) for e in events)
req = any(e[1] == "request" for e in events)
resp = any(e[1] == "response" for e in events)
print()
print("线程跑通:", ok)
print("请求已记录:", req)
print("响应已记录:", resp)
