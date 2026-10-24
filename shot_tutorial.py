import sys
from pathlib import Path
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication
from core import error_hint

# 先验错误映射（纯逻辑，无需界面）
cases = [
    ('HTTP 404 {"error":{"code":"ModelNotOpen","message":"Your account 2120138338 has not activated the model doubao-seedance-2-5-260628."}}', "火山方舟"),
    ('HTTP 402 No free trial quota is available for this model. To continue, please enable postpaid billing.', "腾讯混元"),
    ('HTTP 400 {"message":"insufficient balance"}', "MiniMax"),
    ('HTTP 429 该模型当前访问量过大，请您稍后再试', "智谱 GLM"),
]
for msg, plat in cases:
    hint, url = error_hint.hint_for(msg, plat)
    print(f"[{plat}] -> {hint}")
    print(f"    链接: {url}")

app = QApplication(sys.argv); app.setStyle("Fusion")
app.setFont(QFont("Microsoft YaHei UI", 10))
from ui.key_manager import TutorialDialog

dialogs = []
def shoot(platform, name):
    d = TutorialDialog(platform)
    d.resize(700, 660)
    d.show()
    dialogs.append(d)
    app.processEvents()
    def grab(d=d, name=name):
        d.grab().save(str(BASE / "logs" / f"dlg_{name}.png"))
        print("saved", name)
    QTimer.singleShot(500, grab)

QTimer.singleShot(300, lambda: shoot("火山方舟", "ark"))
QTimer.singleShot(1500, lambda: shoot("阿里百炼", "bailian"))
QTimer.singleShot(3200, app.quit)
app.exec()
