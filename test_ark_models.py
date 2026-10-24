"""探测火山哪些 seedance 模型已开通 + 试 file id 引用。"""
import sys
import requests
sys.path.insert(0, ".")
from core.config import Config

BASE = "https://ark.cn-beijing.volces.com/api/v3"
key = Config().get_key("火山方舟")
H = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
FILE_ID = "file-20261022234727-mn8z9"

models = [
    "doubao-seedance-2-5-260628", "doubao-seedance-2-0-260128",
    "doubao-seedance-2-0-fast-260128", "doubao-seedance-2-0-mini-260615",
    "doubao-seedance-1-0-pro-250528", "doubao-seedance-1-0-lite-i2v-250428",
]
print("=== 文生视频最小请求：看哪些模型已开通 ===")
for m in models:
    body = {"model": m, "content": [{"type": "text", "text": "一只猫在跑"}], "watermark": False}
    r = requests.post(f"{BASE}/contents/generations/tasks", headers=H, json=body, timeout=60)
    code = ""
    try:
        code = (r.json().get("error") or {}).get("code", "")
    except Exception:
        pass
    print(f"  {m:<34} HTTP {r.status_code} {code or r.text[:120]}")

print()
print("=== 已开通的模型上试 file id 引用 ===")
for m in models:
    for label, url in (("file id", FILE_ID), ("asset://", f"asset://{FILE_ID}")):
        body = {"model": m, "watermark": False,
                "content": [{"type": "text", "text": "把画面变成水彩风格"},
                            {"type": "video_url", "video_url": {"url": url}}]}
        r = requests.post(f"{BASE}/contents/generations/tasks", headers=H, json=body, timeout=60)
        code = ""
        try:
            code = (r.json().get("error") or {}).get("code", "")
        except Exception:
            pass
        tag = "OK 受理" if r.status_code < 400 else f"{code or r.status_code}"
        print(f"  {m:<34} {label:<10} {tag}")
        if r.status_code < 400:
            print("      task:", (r.json() or {}).get("id"))
