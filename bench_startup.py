"""测 EXE 冷启动到窗口出现的时间（onedir 应该很快）。"""
import ctypes, ctypes.wintypes, subprocess, time
from pathlib import Path

EXE = Path(r"D:/项目/AI多模态控制台/dist/AI多模态控制台/AI多模态控制台.exe")
TITLE = "AI 多模态控制台"

def wait_window(timeout=30.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        h = ctypes.windll.user32.FindWindowW(None, TITLE)
        if h:
            return time.time() - t0, h
        time.sleep(0.02)
    return None, 0

runs = []
for i in range(3):
    p = subprocess.Popen([str(EXE)], cwd=str(EXE.parent))
    dt, hwnd = wait_window()
    runs.append(dt)
    print(f"第 {i+1} 次：窗口出现 {dt:.2f}s" if dt else f"第 {i+1} 次：超时")
    # 关掉
    if hwnd:
        ctypes.windll.user32.PostMessageW(hwnd, 0x0010, 0, 0)  # WM_CLOSE
    try:
        p.wait(timeout=10)
    except Exception:
        p.terminate()
    time.sleep(1.2)

ok = [r for r in runs if r]
if ok:
    print(f"\n平均 {sum(ok)/len(ok):.2f}s，最快 {min(ok):.2f}s，最慢 {max(ok):.2f}s（含首次冷启动）")
