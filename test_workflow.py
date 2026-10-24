"""工作流链路自检。

模型调用被替换成本地假实现（不花费用、不依赖 Key），
验证的是界面流程本身：分析 → 填提示词 → 出参考图 → 选中 → 二次修改 → 生成视频。
"""
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from PIL import Image
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

app = QApplication(sys.argv)
app.setStyle("Fusion")
app.setFont(QFont("Microsoft YaHei UI", 10))

from core import providers
from core.analysis import parse_analysis

# ---------- 1. 解析器单测 ----------
cases = {
    "标准 JSON": '{"analysis":"A","video_prompt":"V","image_prompt":"I"}',
    "代码块包裹": '```json\n{"analysis":"A2","video_prompt":"V2","image_prompt":"I2"}\n```',
    "中文引号+尾逗号": '{“analysis”:"A3",“video_prompt”:"V3",“image_prompt”:"I3",}',
    "非 JSON": "这是一段普通的视频描述，没有 JSON。",
}
print("=== parse_analysis ===")
for name, text in cases.items():
    d = parse_analysis(text)
    print(f"{name:<10} parsed={d['parsed']} analysis={d['analysis'][:12]!r} video={d['video_prompt'][:14]!r} image={d['image_prompt'][:12]!r}")

# ---------- 2. 替换模型调用 ----------
OUT = BASE / "output"
OUT.mkdir(exist_ok=True)
calls = []


def fake_understand(platform, model, prompt, images, api_key, *, log=None, cancel=None, options=None):
    calls.append(("understand", platform, model, len(images), prompt[:40]))
    if log:
        log("info", "[mock] 理解模型返回示例 JSON")
    return (
        '```json\n{"analysis": "一名戴全盔的骑手站在傍晚的街口，冷色调，胸口有反光条。",'
        ' "video_prompt": "骑手跨上车向前骑行，镜头缓慢推进，霓虹招牌从身后掠过，冷色调，浅景深。",'
        ' "image_prompt": "骑手正面半身，深色头盔与反光风衣，黄昏街道霓虹背景，冷色调，电影感。"}\n```'
    )


def fake_image(platform, model, prompt, images, api_key, *, log=None, cancel=None, options=None):
    calls.append(("image", platform, model, len(images), prompt[:30]))
    out = OUT / f"mock_ref_{int(time.time() * 1000)}.png"
    img = Image.new("RGB", (640, 640), (38, 96, 168))
    # 画几笔，方便肉眼区分不同次生成
    for i in range(0, 640, 40):
        for j in range(0, 640, 40):
            if (i // 40 + j // 40) % 2 == 0:
                img.paste((66, 132, 220), (i, j, i + 40, j + 40))
    img.save(out)
    if log:
        log("info", f"[mock] 生成参考图 {out.name}")
    return [str(out)]


def fake_video(platform, model, prompt, images, api_key, *, log=None, cancel=None, options=None):
    calls.append(("video", platform, model, len(images), prompt[:30]))
    out = OUT / "mock_video.mp4"
    out.write_bytes(b"\x00" * 1024)
    if log:
        log("info", f"[mock] 生成视频 {out.name}")
    return str(out)


providers.understand = fake_understand
providers.generate_image = fake_image
providers.generate_video = fake_video

# ---------- 3. 界面流程 ----------
from ui.main_window import MainWindow

w = MainWindow()
w.config.set_key("火山方舟", "mock-key-for-test")
w.resize(1300, 900)
w.show()
w.tabs.setCurrentIndex(0)
page = w.page_workflow

# 预置参考图与需求
ref = BASE / "logs" / "probe.png"
page.ref_images = [str(ref)]
page.ref_hint.setText("已选 1 张")
page.req_edit.setPlainText("让骑手在傍晚街道向前骑行，镜头推进，冷色调，保留头盔与反光风衣细节。")

steps = []


def wait_task(nextfn=None, label="", timeout=15):
    """轮询等着后台任务结束（QThread 不能阻塞主线程）"""
    t0 = time.time()

    def tick():
        t = page.task
        if t is None or t.isFinished():
            steps.append(f"{label} done calls={len(calls)}")
            if nextfn:
                QTimer.singleShot(150, nextfn)
            return
        if time.time() - t0 > timeout:
            steps.append(f"{label} TIMEOUT")
            QTimer.singleShot(100, nextfn or finish)
            return
        QTimer.singleShot(120, tick)

    QTimer.singleShot(150, tick)


def step1():
    page.run_pipeline()          # 分析 → 自动生图
    wait_task(step2, "analyze+image")


def step2():
    ok = {
        "analysis": bool(page.analysis_view.toPlainText().strip()),
        "prompt": bool(page.prompt_edit.toPlainText().strip()),
        "shots": len(page.generated),
        "selected": bool(page.selected),
    }
    print("=== 分析+生图结果 ===")
    print(ok)
    print("分析:", page.analysis_view.toPlainText()[:60])
    print("提示词:", page.prompt_edit.toPlainText()[:60])
    # 二次修改
    page.edit_instruction.setText("把外套改成深红色，镜头拉到半身")
    page.modify_selected()
    wait_task(step3, "modify")


def step3():
    print("=== 修改后 ===")
    print("参考图数量:", len(page.generated), "选中:", Path(page.selected).name if page.selected else None)
    page.win_tmp = True
    page.run_video()
    wait_task(step4, "video")


def step4():
    print("=== 视频 ===")
    print("video_status:", page.video_status.text()[:90])
    print("last_video:", page.last_video)
    w.grab().save(str(BASE / "logs" / "glass_workflow_filled.png"))
    page.shot_area.grab().save(str(BASE / "logs" / "glass_workflow_shots.png"))
    finish()


def finish():
    print("=== 调用序列 ===")
    for c in calls:
        print("  ", c)
    print("=== 步骤 ===")
    for s in steps:
        print("  ", s)
    w.config.set_key("火山方舟", "")
    app.quit()


QTimer.singleShot(800, step1)
QTimer.singleShot(60000, finish)
app.exec()
