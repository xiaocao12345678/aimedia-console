"""平台密钥集中管理：六家 Key 一个界面填完，每行都带「获取教程」。

教程内容全部来自各平台官方文档（步骤、注意事项、官方链接均可核对，
链接见每家的 docs 字段）。
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from . import style
from .frameless import FrameHost, TitleBar

# 平台 → (Key 形态提示, 控制台地址)
ROWS: list[tuple[str, str, str]] = [
    ("火山方舟",
     "方舟控制台 → API Key 管理；形如 UUID，或带 ARK_ 前缀的密钥",
     "https://console.volcengine.com/ark/region:ark+cn-beijing/apiKey"),
    ("阿里百炼",
     "百炼控制台 → 模型服务 → API Key 设置；形如 sk-xxxxxxxx，注意先选地域",
     "https://bailian.console.aliyun.com/cn-beijing/model/settings/api-key"),
    ("腾讯混元",
     "TokenHub 控制台 → API Key；Bearer 直接用，不需要 TC3 签名",
     "https://console.cloud.tencent.com/tokenhub"),
    ("智谱 GLM",
     "BigModel → API Keys；形如 xxxxxxxx.yyyyyyyy（要用「模型标准 API」那类）",
     "https://open.bigmodel.cn"),
    ("百度千帆",
     "控制台 → 安全认证 → API Key；形如 bce-v3/ALTAK-xxxx/yyyy",
     "https://console.bce.baidu.com/iam/#/iam/apikey/list"),
    ("MiniMax",
     "开放平台 → 访问凭证里的接口密钥；按量付费用这套，M Plan 订阅 Key 不通用",
     "https://platform.minimax.cn/console/access?tab=api-keys"),
]

# 教程：steps 为分步操作，tips 为官方文档里点明的注意事项，docs 为官方教程页
TUTORIALS: dict[str, dict] = {
    "火山方舟": {
        "console": "https://console.volcengine.com/ark/region:ark+cn-beijing/apiKey",
        "docs": "https://docs.volcengine.com/docs/ark/api-key",
        "docs_name": "官方文档：获取 API Key 并配置",
        "steps": [
            '打开 <a href="https://console.volcengine.com/ark/region:ark+cn-beijing/apiKey">方舟 API Key 页面</a>'
            "（也可以从方舟控制台左侧「API Key 管理」进入）",
            "点「创建 API Key」，勾选要调用的模型范围（图像理解 / 生图 / 生视频是不同模型，可先全选）",
            "复制生成的 Key：形如 UUID，或 2026-09-17 之后带 <code>ARK_</code> 前缀的新格式明文",
            "回到「平台密钥」界面粘贴到本行输入框，点「保存」",
        ],
        "tips": [
            "官方说明：2026-09-17 12:00（UTC+8）之后创建的 ModelArk API Key 使用新的明文格式，"
            "此前创建的旧 Key 继续有效，鉴权方式不变",
            "接口地域固定为 cn-beijing（程序已按此配置）",
            "文档建议把 Key 放环境变量，避免硬编码或截图外泄",
        ],
        "activate": {
            "reason": "报 <code>404 ModelNotOpen ... has not activated the model doubao-seedance-2-5-260628</code>",
            "url": "https://ark.volcengine.com/region:cn-beijing/openManagement",
            "url_name": "方舟「开通管理」页",
            "steps": [
                "打开「开通管理」页（方舟控制台左侧菜单里也有这一项）",
                "在列表里找到要用的模型：视频用 <code>doubao-seedance-2-5</code> / <code>2-0</code> 系列，"
                "生图用 <code>doubao-seedream-5-0</code> 系列，理解用 <code>doubao-seed-2-0-pro</code>",
                "点该行的「开通服务」，弹窗里勾上「全选」和「自动开通新增模型」",
                "回到程序重跑同一条请求即可",
            ],
            "note": "注意：<b>上传文件（Files API）不需要开通模型</b>，只有真正生成才需要。"
                    "开通后仍优先消耗剩余免费额度，用完才按量计费；"
                    "状态显示「邀测中」的模型不能自助开通，需要提工单。",
        },
    },
    "阿里百炼": {
        "console": "https://bailian.console.aliyun.com/cn-beijing/model/settings/api-key",
        "docs": "https://help.aliyun.com/zh/model-studio/get-api-key",
        "docs_name": "官方文档：获取与配置 API Key",
        "steps": [
            '打开 <a href="https://bailian.console.aliyun.com/cn-beijing/model/settings/api-key">API Key 页面</a>'
            "（控制台 → 模型服务 → API Key 设置）",
            "<b>先选右上角的地域</b>（本程序默认北京），再创建或查看 API Key —— 每个地域的 Key 独立",
            "复制 Key（形如 sk-xxxxxxxx）",
            "回到本界面粘贴保存",
            '顺带在 <a href="https://bailian.console.aliyun.com/cn-beijing/model/market">模型广场</a>'
            " 确认要用的图像 / 视频模型在该地域已开通",
        ],
        "tips": [
            "官方明确：每个地域有独立的接入域名、API Key 和模型列表，<b>不能跨地域混用</b>",
            "程序默认调用北京地域 dashscope.aliyuncs.com；若账号被要求走业务空间域名，"
            "改 core/adapters.py 里的 BL_BASE",
            "Key 与所选地域要对应，否则会出现「Incorrect API key」这类鉴权失败",
            "模型广场能看到该地域可用的全部模型与计费，开通后再回来跑，能少踩「模型不存在 / 未开通」",
        ],
        "activate": {
            "reason": "报模型不存在 / 未开通（例如视频编辑 <code>wan2.7-videoedit</code> 返回 ModelNotFound）",
            "url": "https://bailian.console.aliyun.com/cn-beijing/model/market",
            "url_name": "百炼「模型广场」（北京地域）",
            "steps": [
                "确认控制台右上角地域是 <b>华北2（北京）</b> —— 程序默认调北京，地域不对应就是「模型不存在」",
                "在模型广场搜索要用的模型：视频编辑 <code>wan2.7-videoedit</code>、"
                "生图 <code>qwen-image-3.0-pro</code>、理解 <code>qwen3-vl</code> 系列",
                "点进模型详情，点「立即开通」（部分新模型需要单独确认协议）",
                "回到程序重跑",
            ],
            "note": "视频编辑类模型属于较新的能力，不少账号需要单独开通；"
                    "未开通时不会扣费，会直接报模型不存在或权限错误。",
        },
    },
    "腾讯混元": {
        "console": "https://console.cloud.tencent.com/tokenhub/apikey?regionId=1",
        "docs": "https://cloud.tencent.com/document/product/1823/130090",
        "docs_name": "官方文档：TokenHub API Key 管理",
        "steps": [
            '打开 TokenHub 的 <a href="https://console.cloud.tencent.com/tokenhub/apikey?regionId=1">API Key 管理</a> 页面',
            "点「创建 API Key」，填名称，可设置访问范围（建议先放开视觉理解 / 图像 / 视频）",
            "保存后在列表里复制 Key",
            "回到本界面粘贴保存",
        ],
        "tips": [
            "Key <b>长期有效</b>，可随时编辑、启停、删除；官方建议按用途分 Key，便于分账与回收",
            "新接入一律走 TokenHub；老的「腾讯混元大模型」平台已停止新增模型能力",
            "鉴权是 Bearer API Key，<b>不需要</b>腾讯云 TC3 签名",
        ],
        "activate": {
            "reason": "报 <code>402 No free trial quota is available for this model ... postpaid billing is not enabled</code>",
            "url": "https://console.cloud.tencent.com/tokenhub/inference",
            "url_name": "TokenHub 控制台「在线推理」",
            "steps": [
                "打开 TokenHub 控制台 → 「在线推理」→ 视觉模型（图像 / 视频 / 理解都在这里）",
                "找到要用的模型：生图 <code>Hy-Image-3.5</code>、视频 <code>HY-Video</code> 系列",
                "在操作列点「启用后付费」",
                "有新人免费体验包的，可以先去「模型广场」右上角领，领完再回来用",
            ],
            "note": "官方文档写明：免费体验额度用完后，<b>必须先开启后付费</b>才能继续调用；不开就一直是 402。",
        },
    },
    "智谱 GLM": {
        "console": "https://bigmodel.cn/usercenter/proj-mgmt/apikeys",
        "docs": "https://docs.bigmodel.cn/cn/api/introduction",
        "docs_name": "官方文档：身份验证 / API Keys",
        "steps": [
            '登录 BigModel，打开 <a href="https://bigmodel.cn/usercenter/proj-mgmt/apikeys">API Keys 页面</a>',
            "新建一个 API Key 并复制（形如 <code>xxxxxxxx.yyyyyyyy</code>，两段用点连接）",
            "回到本界面粘贴保存",
            "保存后随便选一个便宜模型试一次，日志里看到 200 就说明 Key 可用",
        ],
        "tips": [
            "官方说明：<b>个人套餐、团队套餐、模型标准 API 的 Key 分开管理，互不通用</b>。"
            "调本程序的图像理解 / 图像生成 / 视频生成要用「模型标准 API」那一类 Key",
            "Key 格式不对（少一段、带空格）会直接返回「令牌已过期或验证不正确」",
            "图像与视频的尺寸只接受固定枚举，填别的程序会自动回退并写日志",
        ],
        "activate": {
            "reason": "报 429 限流，或提示模型不可用",
            "url": "https://bigmodel.cn/usercenter/proj-mgmt/apikeys",
            "url_name": "BigModel 控制台",
            "steps": [
                "智谱的模型<b>不需要单独开通</b>，有额度/余额即可直接调用",
                "429 基本都出现在免费档（模型名带 <code>flash</code>），并发配额很低",
                "要稳定用就换同平台付费档：理解 <code>glm-4.6v</code>、生图 <code>cogview-3</code>、视频 <code>cogvideox-3</code>",
            ],
            "note": "个人套餐与模型标准 API 是两套 Key，程序用的是后者。",
        },
    },
    "百度千帆": {
        "console": "https://console.bce.baidu.com/iam/#/iam/apikey/list",
        "docs": "https://cloud.baidu.com/doc/qianfan-api/s/ym9chdsy5",
        "docs_name": "官方文档：认证鉴权（获取 API Key 全流程）",
        "steps": [
            '打开 <a href="https://console.bce.baidu.com/iam/#/iam/apikey/list">API Key 管理</a>'
            "（百度智能云控制台 → 安全认证 → API Key）；千帆平台内也有一入口："
            '<a href="https://console.bce.baidu.com/qianfan/ais/console/apiKey">qianfan/ais/console/apiKey</a>',
            "点「创建 API Key」，选择 <b>千帆 ModelBuilder</b>",
            "配置资源：选「所有资源」，或指定 appid（只有选中的应用能用这个 Key），点确定",
            "在 API Key 列表里复制 Key（形如 <code>bce-v3/ALTAK-xxxx/yyyy</code>）",
            "回到本界面粘贴保存",
        ],
        "tips": [
            "平台已默认开通 API 调用权限，不需要单独申请",
            "鉴权方式是把 <code>Bearer</code> 和 Key 拼进 Authorization 头，<b>不需要</b> AK/SK 签名",
            "资源没配置对时，调用会报权限/模型不存在类错误，回控制台检查 appid 范围",
        ],
        "activate": {
            "reason": "报权限不足 / 模型不存在",
            "url": "https://console.bce.baidu.com/qianfan/overview",
            "url_name": "千帆控制台",
            "steps": [
                "平台默认已开通 API 调用权限，一般不需要单独申请模型",
                "若报权限类错误：确认账号已实名认证，且 API Key 的资源范围选的是「所有资源」或包含对应 appid",
                "在千帆控制台的「在线服务 / 模型服务」里确认要用的模型在该区域可用",
            ],
            "note": "千帆的付费模型需要账户有余额；免费额度按模型单独计算。",
        },
    },
    "MiniMax": {
        "console": "https://platform.minimax.cn/console/access?tab=api-keys",
        "docs": "https://platform.minimax.cn/docs/guides/quickstart-preparation",
        "docs_name": "官方文档：前置准备（注册与获取 Key）",
        "steps": [
            "注册并登录 MiniMax 开放平台",
            '打开 <a href="https://platform.minimax.cn/console/access?tab=api-keys">访问凭证 · 接口密钥</a>'
            "（按量付费通道），点「创建新的 API Key」",
            "复制 Key",
            "回到本界面粘贴保存",
        ],
        "tips": [
            "按量付费与 M Plan 订阅是<b>两套 Key</b>：M Plan 的订阅 Key 在「订阅管理」里，"
            "本程序调的是按量付费接口，要用「接口密钥」那一套",
            "MiniMax 鉴权失败时仍可能返回 HTTP 200，真实错误在响应体 base_resp.status_code"
            "（1004 就是 Key 不对），程序已单独判这个字段",
            "图像接口是自有协议（/v1/image_generation），不走 OpenAI 的 /v1/images/generations",
        ],
        "activate": {
            "reason": "报 <code>402 insufficient balance</code>，或响应体里 <code>base_resp.status_code=1008</code>",
            "url": "https://platform.minimax.cn",
            "url_name": "MiniMax 开放平台（登录后进账户充值）",
            "steps": [
                "MiniMax <b>不需要开通模型</b>，只要有余额就能调",
                "登录开放平台，进「账户 / 充值」充一笔（按量付费通道）",
                "回到程序重跑同一条请求",
            ],
            "note": "MiniMax 的失败常藏在 HTTP 200 里，真实错误看 <code>base_resp.status_code</code>：1004 是 Key 不对，1008 是余额不足。",
        },
    },
}

ROW_QSS = """
QFrame#ActBox {
    background: rgba(232, 242, 255, 0.85);
    border: 1px solid rgba(120, 165, 220, 0.55);
    border-radius: 8px;
}
QFrame#KeyRow {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(255, 255, 255, 0.60), stop:1 rgba(248, 251, 255, 0.44));
    border: 1px solid rgba(148, 170, 196, 0.50);
    border-radius: 11px;
}
QFrame#KeyRow:hover {
    background: rgba(255, 255, 255, 0.78);
    border: 1px solid rgba(140, 163, 190, 0.72);
}
QLabel#PlatName { font-size: 13px; font-weight: 600; color: #16202a; }
QLabel#PlatHint { font-size: 10px; color: #6b7683; }
QLabel#ChipOk {
    color: #0a7d4f; font-size: 10px; padding: 1px 7px;
    border: 1px solid rgba(10, 125, 79, 0.40);
    border-radius: 8px; background: rgba(10, 125, 79, 0.10);
}
QLabel#ChipEmpty {
    color: #b76e00; font-size: 10px; padding: 1px 7px;
    border: 1px solid rgba(183, 110, 0, 0.40);
    border-radius: 8px; background: rgba(183, 110, 0, 0.10);
}
QToolButton#Eye {
    border: 1px solid rgba(255, 255, 255, 0.85);
    border-bottom: 1px solid rgba(118, 138, 166, 0.45);
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.70);
    padding: 0px 9px;
    color: #46515c;
    font-size: 11px;
    min-width: 42px;
    min-height: 24px;
}
QToolButton#Eye:hover { background: rgba(255, 255, 255, 0.95); }
QPushButton#RowBtn { padding: 4px 10px; font-size: 12px; }
QPushButton#TutBtn {
    padding: 4px 10px;
    font-size: 12px;
    color: #1c68e2;
    background: rgba(31, 111, 235, 0.10);
    border: 1px solid rgba(31, 111, 235, 0.35);
    border-radius: 8px;
}
QPushButton#TutBtn:hover {
    background: rgba(31, 111, 235, 0.18);
    border-color: rgba(31, 111, 235, 0.55);
}
QFrame#TipBox {
    background: rgba(255, 246, 226, 0.85);
    border: 1px solid rgba(226, 178, 92, 0.55);
    border-left: 3px solid rgba(226, 160, 40, 0.85);
    border-radius: 8px;
}
QLabel#StepText { font-size: 12px; color: #26303a; }
QLabel#SectTitle { font-size: 12px; font-weight: 600; color: #46515c; }
"""


class TutorialDialog(FrameHost, QDialog):
    """单平台「怎么拿到 API Key」教程：官方步骤 + 注意事项 + 直达链接。"""

    def __init__(self, platform: str, parent=None) -> None:
        super().__init__(parent)
        data = TUTORIALS.get(platform, {})
        self.setWindowTitle(f"{platform} · 获取 API Key")
        self.resize(700, 660)
        self.install_frame()
        self.setStyleSheet(style.app_qss() + ROW_QSS)

        shell = QVBoxLayout(self)
        shell.setContentsMargins(0, 0, 0, 0)
        root = QWidget()
        root.setObjectName("Root")
        shell.addWidget(root)

        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        bar = TitleBar(self, f"{platform} · 获取 API Key 教程", allow_maximize=False)
        outer.addWidget(bar)

        body = QVBoxLayout()
        body.setContentsMargins(16, 12, 16, 12)
        body.setSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        holder = QWidget()
        hv = QVBoxLayout(holder)
        hv.setContentsMargins(0, 0, 8, 0)
        hv.setSpacing(10)

        steps_title = QLabel("操作步骤")
        steps_title.setObjectName("SectTitle")
        hv.addWidget(steps_title)

        steps = data.get("steps") or []
        items = "".join(
            f'<li style="margin-bottom:8px;">{s}</li>' for s in steps
        )
        steps_label = QLabel(
            f'<ol style="margin-left:-14px; color:#26303a; font-size:12px; line-height:150%;">{items}</ol>'
        )
        steps_label.setObjectName("StepText")
        steps_label.setWordWrap(True)
        steps_label.setTextFormat(Qt.TextFormat.RichText)
        steps_label.setOpenExternalLinks(True)
        steps_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextBrowserInteraction
        )
        hv.addWidget(steps_label)

        tips = data.get("tips") or []
        if tips:
            tips_title = QLabel("注意事项（来自官方文档）")
            tips_title.setObjectName("SectTitle")
            hv.addWidget(tips_title)
            tip_box = QFrame()
            tip_box.setObjectName("TipBox")
            tv = QVBoxLayout(tip_box)
            tv.setContentsMargins(10, 8, 10, 8)
            tv.setSpacing(6)
            for t in tips:
                lab = QLabel(f"• {t}")
                lab.setWordWrap(True)
                lab.setTextFormat(Qt.TextFormat.RichText)
                lab.setStyleSheet("font-size:12px;color:#4a3a1a;border:none;background:transparent;")
                tv.addWidget(lab)
            hv.addWidget(tip_box)

        act = data.get("activate")
        if act:
            act_title = QLabel("模型开通（报 ModelNotOpen / 402 时才需要做）")
            act_title.setObjectName("SectTitle")
            hv.addWidget(act_title)

            act_box = QFrame()
            act_box.setObjectName("ActBox")
            av = QVBoxLayout(act_box)
            av.setContentsMargins(10, 8, 10, 8)
            av.setSpacing(7)

            reason = QLabel(f"什么情况下会用到：{act.get('reason', '')}")
            reason.setWordWrap(True)
            reason.setTextFormat(Qt.TextFormat.RichText)
            reason.setStyleSheet("font-size:12px;color:#1f4f86;border:none;background:transparent;")
            av.addWidget(reason)

            act_steps = "".join(
                f'<li style="margin-bottom:6px;">{s}</li>' for s in (act.get("steps") or [])
            )
            act_label = QLabel(
                f'<ol style="margin-left:-14px; color:#26303a; font-size:12px; line-height:150%;">'
                f'{act_steps}</ol>'
            )
            act_label.setWordWrap(True)
            act_label.setTextFormat(Qt.TextFormat.RichText)
            act_label.setOpenExternalLinks(True)
            act_label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextBrowserInteraction
            )
            act_label.setStyleSheet("border:none;background:transparent;")
            av.addWidget(act_label)

            note = act.get("note")
            if note:
                note_label = QLabel(note)
                note_label.setWordWrap(True)
                note_label.setTextFormat(Qt.TextFormat.RichText)
                note_label.setStyleSheet(
                    "font-size:11px;color:#46515c;border:none;background:transparent;"
                )
                av.addWidget(note_label)

            open_row = QHBoxLayout()
            act_btn = QPushButton(act.get("url_name", "打开开通页"))
            act_btn.clicked.connect(lambda: self._open(act.get("url")))
            open_row.addWidget(act_btn)
            open_row.addStretch(1)
            av.addLayout(open_row)
            hv.addWidget(act_box)

        hv.addStretch(1)
        scroll.setWidget(holder)
        body.addWidget(scroll, 1)

        foot = QHBoxLayout()
        docs_name = data.get("docs_name", "打开官方文档")
        docs_btn = QPushButton(docs_name)
        docs_btn.clicked.connect(lambda: self._open(data.get("docs")))
        console_btn = QPushButton("打开控制台")
        console_btn.clicked.connect(lambda: self._open(data.get("console")))
        foot.addWidget(docs_btn)
        foot.addWidget(console_btn)
        foot.addStretch(1)
        done = QPushButton("我填好了")
        done.setObjectName("Primary")
        done.clicked.connect(self.accept)
        foot.addWidget(done)
        body.addLayout(foot)

        outer.addLayout(body, 1)

    @staticmethod
    def _open(url: str | None) -> None:
        if url:
            QDesktopServices.openUrl(QUrl(url))


class KeyRow(QFrame):
    saved = pyqtSignal(str)
    tutorial_requested = pyqtSignal(str)

    def __init__(self, config, platform: str, hint: str, console_url: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("KeyRow")
        self.config = config
        self.platform = platform
        self.console_url = console_url

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 7, 12, 7)
        outer.setSpacing(4)

        head = QHBoxLayout()
        head.setSpacing(8)
        self.dot = QLabel()
        self.dot.setFixedSize(8, 8)
        self.dot.setStyleSheet("border-radius:4px;background:#c7d2de;")
        head.addWidget(self.dot, 0, Qt.AlignmentFlag.AlignVCenter)
        name = QLabel(platform)
        name.setObjectName("PlatName")
        head.addWidget(name)
        self.chip = QLabel("")
        self.chip.setObjectName("ChipEmpty")
        head.addWidget(self.chip)
        head.addStretch(1)

        self.tut_btn = QPushButton("获取教程")
        self.tut_btn.setObjectName("TutBtn")
        self.tut_btn.setToolTip(f"查看 {platform} 官方获取 API Key 的步骤")
        self.tut_btn.clicked.connect(lambda: self.tutorial_requested.emit(self.platform))
        head.addWidget(self.tut_btn)

        self.console_btn = QPushButton("打开控制台")
        self.console_btn.setObjectName("RowBtn")
        self.console_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(self.console_url))
        )
        head.addWidget(self.console_btn)
        outer.addLayout(head)

        body = QHBoxLayout()
        body.setSpacing(7)
        self.edit = QLineEdit()
        self.edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit.setPlaceholderText("粘贴该平台 API Key")
        self.edit.setMinimumWidth(360)
        self.edit.setMinimumHeight(28)
        body.addWidget(self.edit, 1)

        self.eye = QToolButton()
        self.eye.setObjectName("Eye")
        self.eye.setText("显示")
        self.eye.setCheckable(True)
        self.eye.toggled.connect(self._toggle_echo)
        body.addWidget(self.eye)

        self.save_btn = QPushButton("保存")
        self.save_btn.setObjectName("RowBtn")
        self.save_btn.setMinimumHeight(28)
        self.save_btn.clicked.connect(self.save)
        body.addWidget(self.save_btn)
        outer.addLayout(body)

        tip = QLabel(hint)
        tip.setObjectName("PlatHint")
        outer.addWidget(tip)

        self.reload()

    def _toggle_echo(self, on: bool) -> None:
        self.edit.setEchoMode(
            QLineEdit.EchoMode.Normal if on else QLineEdit.EchoMode.Password
        )
        self.eye.setText("隐藏" if on else "显示")

    def reload(self) -> None:
        key = self.config.get_key(self.platform)
        self.edit.setText(key)
        self._sync_chip(bool(key))

    def _sync_chip(self, has: bool) -> None:
        self.dot.setStyleSheet(
            "border-radius:4px;background:#0a7d4f;" if has
            else "border-radius:4px;background:#c7d2de;"
        )
        self.chip.setText("已保存" if has else "未保存")
        self.chip.setObjectName("ChipOk" if has else "ChipEmpty")
        self.chip.style().unpolish(self.chip)
        self.chip.style().polish(self.chip)

    def save(self) -> None:
        key = self.edit.text().strip()
        self.config.set_key(self.platform, key)
        self._sync_chip(bool(key))
        self.saved.emit(self.platform)


class KeyManagerDialog(FrameHost, QDialog):
    keys_changed = pyqtSignal()

    def __init__(self, config, parent=None) -> None:
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("平台密钥")
        self.resize(980, 800)
        self.install_frame()
        # 对话框是独立顶层窗口，不会继承主窗口样式表，必须自己套一份
        self.setStyleSheet(style.app_qss() + ROW_QSS)

        shell = QVBoxLayout(self)
        shell.setContentsMargins(0, 0, 0, 0)

        root = QWidget()
        root.setObjectName("Root")
        shell.addWidget(root)

        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.titlebar = TitleBar(self, "平台密钥 · 六家集中管理", allow_maximize=False)
        outer.addWidget(self.titlebar)

        body = QVBoxLayout()
        body.setContentsMargins(16, 10, 16, 12)
        body.setSpacing(8)

        intro = QLabel(
            "每个平台的 Key 都保存在本机配置文件里，填完点「保存」；"
            "不知道去哪拿，就点每行右侧的「获取教程」（步骤来自各平台官方文档）。"
        )
        intro.setStyleSheet("color:#46515c;font-size:12px;")
        body.addWidget(intro)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        holder = QWidget()
        rows_layout = QVBoxLayout(holder)
        rows_layout.setContentsMargins(0, 0, 6, 0)
        rows_layout.setSpacing(10)

        self.rows: dict[str, KeyRow] = {}
        for platform, hint, console_url in ROWS:
            row = KeyRow(config, platform, hint, console_url)
            row.saved.connect(self._on_row_saved)
            row.tutorial_requested.connect(self.show_tutorial)
            rows_layout.addWidget(row)
            self.rows[platform] = row
        rows_layout.addStretch(1)
        scroll.setWidget(holder)
        body.addWidget(scroll, 1)

        foot = QHBoxLayout()
        self.summary = QLabel("")
        self.summary.setStyleSheet("color:#6b7683;font-size:12px;")
        foot.addWidget(self.summary)
        foot.addStretch(1)
        save_all = QPushButton("全部保存")
        save_all.setObjectName("Primary")
        save_all.clicked.connect(self.save_all)
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        foot.addWidget(save_all)
        foot.addWidget(close_btn)
        body.addLayout(foot)

        outer.addLayout(body, 1)
        self._refresh_summary()

    def show_tutorial(self, platform: str) -> None:
        dlg = TutorialDialog(platform, self)
        dlg.exec()

    def _on_row_saved(self, platform: str) -> None:
        self._refresh_summary()
        self.keys_changed.emit()

    def save_all(self) -> None:
        for row in self.rows.values():
            row.save()
        self._refresh_summary()

    def _refresh_summary(self) -> None:
        total = len(self.rows)
        ready = sum(1 for p in self.rows if self.config.has_key(p))
        self.summary.setText(f"已配置 {ready} / {total} 家")
        self.titlebar.badge.setText(f"{ready}/{total}")
        self.titlebar.badge.setVisible(True)
