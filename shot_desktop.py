import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication
BASE = Path(r"D:/项目/AI多模态控制台")
app = QApplication([])
pm = app.primaryScreen().grabWindow(0)
out = BASE / "logs" / "exe_running.png"
pm.save(str(out))
print("saved", pm.width(), "x", pm.height())
