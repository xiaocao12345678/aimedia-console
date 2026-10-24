"""参考图工作流的提示词组装与结果解析。

思路：一次理解调用同时产出三样东西 ——
  ① 参考图分析（人可读，便于判断模型有没有看懂）
  ② 视频生成提示词（按镜头脚本顺序，直接喂给视频模型）
  ③ 生图提示词（用来生成"视频首帧参考图"）
要求模型只回 JSON，解析失败时降级处理，不让整个流程卡死。
"""
from __future__ import annotations

import json
import re
from typing import Any

ANALYZE_PROMPT = """你是短视频分镜与提示词工程师。用户会给你 {n} 张参考图，以及一句需求。

【用户需求】
{requirement}

请完成三件事，并且**只输出一个 JSON 对象**，不要写任何解释、不要用 markdown 代码块：

{{
  "analysis": "对参考图的结构化分析：主体与数量、外观与材质细节、场景环境、光线与色调、机位与景别；如果有多张图，说明它们之间的关系。中文，150-260 字。",
  "video_prompt": "可直接提交给视频生成模型的提示词。顺序：主体动作 → 外观细节 → 环境 → 机位与运镜 → 光线与色调。必须体现用户需求。中文，180-320 字，一段话，不要分点。",
  "image_prompt": "用于生成『视频首帧参考图』的绘图提示词：主体、姿态、构图与景别、环境、光线、色调、画面风格。要能独立成图，且与 video_prompt 的画面一致。中文，80-160 字。"
}}

约束：
- 不要出现"参考图""图片中"这类字样，直接描述画面本身。
- 不要臆造参考图里没有的关键物体；不确定的细节用合理默认值。
- 如果用户需求与参考图冲突，以用户需求为准，并在 analysis 里点明这处改动。
"""


def build_analyze_prompt(requirement: str, image_count: int) -> str:
    return ANALYZE_PROMPT.format(n=image_count, requirement=requirement.strip())


def _extract_json(text: str) -> Any:
    """从模型输出里挖出 JSON：优先 ```json 代码块，其次第一个平衡的 {...}。"""
    if not text:
        return None
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    candidates = []
    if fenced:
        candidates.append(fenced.group(1))
    start = text.find("{")
    if start >= 0:
        depth = 0
        for i in range(start, len(text)):
            ch = text[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidates.append(text[start : i + 1])
                    break
    for raw in candidates:
        try:
            return json.loads(raw)
        except Exception:
            # 常见毛病：中文引号、尾逗号
            fixed = (
                raw.replace("“", '"').replace("”", '"')
                .replace("\n", " ")
                .replace(",}", "}")
                .replace(", ]", "]")
            )
            try:
                return json.loads(fixed)
            except Exception:
                continue
    return None


def parse_analysis(text: str) -> dict:
    """把模型输出整理成三个字段；解析不出来就整体当提示词，保证流程能继续。"""
    data = _extract_json(text)
    if isinstance(data, dict):
        out = {
            "analysis": str(data.get("analysis") or "").strip(),
            "video_prompt": str(data.get("video_prompt") or data.get("prompt") or "").strip(),
            "image_prompt": str(data.get("image_prompt") or "").strip(),
            "raw": text,
            "parsed": True,
        }
    else:
        out = {
            "analysis": "",
            "video_prompt": text.strip(),
            "image_prompt": "",
            "raw": text,
            "parsed": False,
        }
    # 两个提示词互相兜底，避免某一步空着无法继续
    if not out["video_prompt"]:
        out["video_prompt"] = out["analysis"] or text.strip()
    if not out["image_prompt"]:
        out["image_prompt"] = out["video_prompt"]
    return out
