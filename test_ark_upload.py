"""实测：火山方舟 Files API 能否上传本地视频，以及视频生成请求里怎么引用它。"""
import json, sys, time
from pathlib import Path

import requests

sys.path.insert(0, ".")
from core.config import Config

BASE = "https://ark.cn-beijing.volces.com/api/v3"
key = Config().get_key("火山方舟")
H = {"Authorization": f"Bearer {key}"}
clip = Path("logs/test_clip.mp4")

print("=== 1. 上传测试视频 ===")
with open(clip, "rb") as f:
    r = requests.post(f"{BASE}/files", headers=H,
                      files={"file": (clip.name, f, "video/mp4")},
                      data={"purpose": "user_data"}, timeout=300)
print("HTTP", r.status_code)
print(r.text[:600])
file_id = ""
try:
    file_id = (r.json() or {}).get("id", "")
except Exception:
    pass
print("file_id =", file_id)

if not file_id:
    sys.exit(0)

# 等文件预处理完成
for i in range(20):
    rr = requests.get(f"{BASE}/files/{file_id}", headers=H, timeout=60)
    st = (rr.json() or {}).get("status")
    print(f"  查询 {i+1}: status={st}")
    if st in ("processed", "active", "ready", "succeeded"):
        break
    if st in ("failed", "error"):
        print(rr.text[:400]); break
    time.sleep(3)

print()
print("=== 2. 试三种引用方式（只看是否被受理） ===")
prompt = "把画面转换成水彩画风格，保留镜头运动"
candidates = {
    "file id 直传": {"type": "video_url", "video_url": {"url": file_id}},
    "file:// 前缀": {"type": "video_url", "video_url": {"url": f"file://{file_id}"}},
    "asset:// 前缀": {"type": "video_url", "video_url": {"url": f"asset://{file_id}"}},
}
for label, part in candidates.items():
    body = {"model": "doubao-seedance-2-5-260628",
            "content": [{"type": "text", "text": prompt}, part],
            "watermark": False}
    rr = requests.post(f"{BASE}/contents/generations/tasks", headers={**H, "Content-Type": "application/json"},
                       json=body, timeout=120)
    ok = rr.status_code < 400
    print(f"  {label:<14} HTTP {rr.status_code} {'受理 task_id=' + str((rr.json() or {}).get('id')) if ok else rr.text[:200]}")
    if ok:
        print("    -> 这种写法可用")
