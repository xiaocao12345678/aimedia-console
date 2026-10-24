"""把平台返回的错误码翻译成"下一步该干什么"。

很多失败不是代码问题，也不是 Key 问题，而是「这个模型没在该账号开通」或「没余额」。
这时候最有用的一句话不是错误原文，而是"去哪个页面点哪个按钮"。
"""
from __future__ import annotations

from typing import Optional

# 平台注册表的顺序与 key_manager 的教程保持一致
ACTIVATE_URL = {
    "火山方舟": "https://ark.volcengine.com/region:cn-beijing/openManagement",
    "阿里百炼": "https://bailian.console.aliyun.com/cn-beijing/model/market",
    "腾讯混元": "https://console.cloud.tencent.com/tokenhub/inference",
    "智谱 GLM": "https://bigmodel.cn/usercenter/proj-mgmt/apikeys",
    "百度千帆": "https://console.bce.baidu.com/qianfan",
    "MiniMax": "https://platform.minimax.cn",
}


def hint_for(message: str, platform: str) -> tuple[Optional[str], Optional[str]]:
    """返回 (建议文本, 控制台链接)。没有匹配到就返回 (None, None)。"""
    msg = message or ""
    low = msg.lower()
    url = ACTIVATE_URL.get(platform)

    if "modelnotopen" in low or "has not activated" in low or "modelnotfound" in low:
        return (
            f"这个模型没有在「{platform}」账号里开通。开通入口："
            f"{'方舟「开通管理」页 → 找到该模型 → 点「开通服务」' if platform == '火山方舟' else '平台控制台的模型/服务开通页'}。"
            "开通后同一条请求即可成功（免费额度会先被消耗）。",
            url,
        )
    if "no free trial quota" in low or "postpaid billing is not enabled" in low:
        return (
            "免费体验额度已用完，且该模型没有开启后付费。"
            "去 TokenHub 控制台的「在线推理」里找到这个模型，在操作列点「启用后付费」。",
            url,
        )
    if "insufficient balance" in low or "1008" in low or "余额" in msg:
        return "账户余额不足，充值后即可调用（Key 本身是有效的）。", url
    if "429" in msg or "访问量过大" in msg or "rate limit" in low or "too many requests" in low:
        return (
            "被限流了。免费档（模型名带 flash）经常这样，换成同平台的付费档，或等一会儿重试。",
            url,
        )
    if "401" in msg or "invalid_iam_token" in low or "api key" in low and "incorrect" in low:
        return "Key 无效或类型不对（比如智谱要用「模型标准 API」那类 Key）。去「平台密钥」重新填。", None
    if "does not exist or you do not have access" in low:
        return f"模型 ID 可能写错，或该模型未在「{platform}」开通。可先在下拉里换一个模型试。", url
    if "invalidparameter" in low or "parameter" in low and "not supported" in low:
        return "参数与所选模型不匹配（例如给不支持多图的模型传了多图参数）。换模型或调整参数。", None
    return None, None


def decorate(message: str, platform: str) -> str:
    """把建议拼到错误信息后面，供弹窗与日志使用。"""
    hint, url = hint_for(message, platform)
    if not hint:
        return message
    text = f"{message}\n\n建议：{hint}"
    if url:
        text += f"\n开通/管理入口：{url}"
    return text
