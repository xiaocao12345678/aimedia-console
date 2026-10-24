"""磨砂玻璃主题：配色与全局样式表。

设计取舍：
- 窗口用系统级亚克力（DWM）透出桌面模糊；控件只叠半透明白，不自己画模糊。
- 边框一律用「淡蓝灰细描边 + 白色高光」两层思路：
  纯白描边在浅色亚克力上完全看不见，界面会糊成一片白。
- 按钮用「白渐变 + 底部暗边」模拟玻璃块的厚度与高光。
"""
from __future__ import annotations

from core.paths import asset_path

ARROW = asset_path("combo_arrow.png")
ARROW_DISABLED = asset_path("combo_arrow_disabled.png")
SPIN_UP = asset_path("spin_up.png")
SPIN_DOWN = asset_path("spin_down.png")

INK = "#16202a"
INK_SOFT = "#46515c"
INK_FAINT = "#6b7683"
ACCENT = "#1f6feb"
OK = "#0a7d4f"
WARN = "#b76e00"
ERR = "#c62828"

# 描边：淡蓝灰（在浅色玻璃上可见），高光：白色
EDGE = "rgba(148, 170, 196, 0.55)"
EDGE_STRONG = "rgba(140, 163, 190, 0.75)"
HAIRLINE = "rgba(255, 255, 255, 0.85)"
SHADE = "rgba(118, 138, 166, 0.45)"


def app_qss() -> str:
    return f"""
    QWidget {{
        font-family: "Microsoft YaHei UI", "Segoe UI";
        font-size: 13px;
        color: {INK};
    }}

    /* ---------- 窗口根容器 ---------- */
    QMainWindow, QDialog, QWidget#Shell {{ background: transparent; }}

    /* 系统模糊可用时：几乎全透明，玻璃感来自系统模糊 + 控件自身的白玻璃层 */
    QWidget#Root {{
        /* 白 tint 把背后的桌面压成磨砂奶白：既保留轮廓，又保证深色文字可读 */
        background: qlineargradient(x1:0, y1:0, x2:0.35, y2:1,
            stop:0 rgba(252, 253, 255, 0.88),
            stop:0.55 rgba(249, 252, 255, 0.84),
            stop:1 rgba(245, 249, 255, 0.86));
        border: 1px solid {HAIRLINE};
        border-radius: 14px;
    }}
    /* 系统模糊不可用时的回退：实底，保证可读性 */
    QWidget#Root[glass="false"] {{
        background: rgba(246, 249, 253, 0.97);
    }}
    QWidget#Root[maximized="true"] {{
        border-radius: 0px;
    }}

    /* ---------- 标题栏 ---------- */
    QWidget#TitleBar {{
        background: rgba(255, 255, 255, 0.18);
        border-top-left-radius: 14px;
        border-top-right-radius: 14px;
        border-bottom: 1px solid rgba(148, 170, 196, 0.35);
    }}
    QLabel#AppTitle {{
        font-size: 14px;
        font-weight: 600;
        color: {INK};
        padding-left: 2px;
    }}
    QLabel#AppBadge {{
        color: {INK_SOFT};
        font-size: 11px;
        padding: 2px 9px;
        border: 1px solid {EDGE};
        border-radius: 9px;
        background: rgba(255, 255, 255, 0.55);
    }}

    /* ---------- 窗口按钮 ---------- */
    QToolButton#WinBtn, QToolButton#CloseBtn {{
        border: 1px solid transparent;
        border-radius: 8px;
        color: {INK_SOFT};
        background: transparent;
        font-size: 14px;
        min-width: 34px;
        min-height: 28px;
    }}
    QToolButton#WinBtn:hover {{
        background: rgba(255, 255, 255, 0.70);
        border-color: {HAIRLINE};
        color: {INK};
    }}
    QToolButton#WinBtn:pressed {{
        background: rgba(226, 234, 244, 0.85);
    }}
    QToolButton#CloseBtn:hover {{
        background: rgba(226, 88, 88, 0.92);
        border-color: rgba(255, 200, 200, 0.9);
        color: #ffffff;
    }}

    /* ---------- 玻璃按钮 ---------- */
    QPushButton {{
        color: {INK};
        border: 1px solid {HAIRLINE};
        border-bottom: 1px solid {SHADE};
        border-radius: 10px;
        padding: 7px 15px;
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 rgba(255, 255, 255, 0.80),
            stop:0.55 rgba(255, 255, 255, 0.46),
            stop:1 rgba(246, 250, 255, 0.40));
    }}
    QPushButton:hover {{
        border-color: #ffffff;
        border-bottom-color: rgba(108, 130, 160, 0.55);
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 rgba(255, 255, 255, 0.95),
            stop:1 rgba(240, 247, 255, 0.62));
    }}
    QPushButton:pressed {{
        border-bottom: 1px solid {HAIRLINE};
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 rgba(206, 220, 238, 0.95),
            stop:1 rgba(190, 208, 230, 0.80));
    }}
    QPushButton:disabled {{
        color: #9aa4af;
        border: 1px solid rgba(255, 255, 255, 0.45);
        border-bottom: 1px solid rgba(160, 178, 200, 0.25);
        background: rgba(255, 255, 255, 0.26);
    }}

    /* 主操作：蓝色玻璃 */
    QPushButton#Primary {{
        color: #ffffff;
        font-weight: 600;
        border: 1px solid rgba(255, 255, 255, 0.65);
        border-bottom: 1px solid rgba(12, 62, 140, 0.60);
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 rgba(92, 158, 250, 0.96),
            stop:0.55 rgba(46, 122, 236, 0.94),
            stop:1 rgba(26, 100, 218, 0.94));
    }}
    QPushButton#Primary:hover {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 rgba(116, 176, 255, 0.98),
            stop:1 rgba(38, 112, 232, 0.96));
    }}
    QPushButton#Primary:pressed {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 rgba(24, 92, 200, 0.97), stop:1 rgba(18, 78, 174, 0.97));
    }}
    QPushButton#Primary:disabled {{
        color: rgba(255, 255, 255, 0.80);
        border: 1px solid rgba(255, 255, 255, 0.45);
        background: rgba(152, 178, 210, 0.60);
    }}

    /* ---------- 输入类 ---------- */
    QLineEdit, QComboBox, QSpinBox, QPlainTextEdit, QTextEdit {{
        background: rgba(255, 255, 255, 0.76);
        border: 1px solid {EDGE};
        border-radius: 9px;
        padding: 5px 8px;
        selection-background-color: rgba(31, 111, 235, 0.26);
    }}
    QLineEdit:hover, QComboBox:hover, QSpinBox:hover {{
        border-color: {EDGE_STRONG};
    }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus,
    QPlainTextEdit:focus, QTextEdit:focus {{
        border: 1px solid rgba(31, 111, 235, 0.85);
        background: rgba(255, 255, 255, 0.92);
    }}
    /* 下拉按钮与箭头：覆盖 ::drop-down 会丢掉默认箭头，所以必须自己给图 */
    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: center right;
        width: 24px;
        border: none;
        background: transparent;
    }}
    QComboBox::down-arrow {{
        image: url({ARROW});
        width: 12px;
        height: 12px;
        margin-right: 6px;
    }}
    QComboBox::down-arrow:hover {{ image: url({ARROW}); }}
    QComboBox::down-arrow:on {{ image: url({ARROW}); }}
    QComboBox:disabled::down-arrow {{ image: url({ARROW_DISABLED}); }}
    QComboBox QAbstractItemView::item {{
        min-height: 26px;
        padding: 4px 8px;
    }}

    /* 数字框的上下按钮：默认按钮在玻璃风格里太突兀，换成同款细箭头 */
    QSpinBox {{ padding-right: 22px; }}
    QSpinBox::up-button, QSpinBox::down-button {{
        subcontrol-origin: border;
        width: 18px;
        border: none;
        background: transparent;
    }}
    QSpinBox::up-button {{ subcontrol-position: top right; margin-top: 2px; }}
    QSpinBox::down-button {{ subcontrol-position: bottom right; margin-bottom: 2px; }}
    QSpinBox::up-arrow {{ image: url({SPIN_UP}); width: 9px; height: 9px; }}
    QSpinBox::down-arrow {{ image: url({SPIN_DOWN}); width: 9px; height: 9px; }}
    QComboBox QAbstractItemView {{
        background: #f8fbff;
        border: 1px solid {EDGE_STRONG};
        border-radius: 8px;
        selection-background-color: rgba(31, 111, 235, 0.16);
        selection-color: {INK};
        outline: none;
        padding: 3px;
    }}
    QPlainTextEdit, QTextEdit {{
        background: rgba(255, 255, 255, 0.82);
    }}

    /* ---------- 分组面板 ---------- */
    QGroupBox {{
        border: 1px solid {EDGE};
        border-radius: 12px;
        margin-top: 14px;
        padding: 16px 12px 10px 12px;
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 rgba(255, 255, 255, 0.50),
            stop:1 rgba(248, 251, 255, 0.34));
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 1px 8px;
        color: {INK_SOFT};
        font-weight: 600;
        background: rgba(255, 255, 255, 0.75);
        border: 1px solid rgba(255, 255, 255, 0.85);
        border-radius: 7px;
    }}

    /* ---------- 标签页 ---------- */
    QTabWidget::pane {{
        border: 1px solid {EDGE};
        border-radius: 12px;
        background: rgba(255, 255, 255, 0.20);
        top: -1px;
    }}
    QTabBar::tab {{
        background: rgba(255, 255, 255, 0.38);
        border: 1px solid rgba(148, 170, 196, 0.40);
        border-bottom: none;
        border-top-left-radius: 10px;
        border-top-right-radius: 10px;
        padding: 8px 22px;
        margin-right: 4px;
        color: {INK_SOFT};
    }}
    QTabBar::tab:selected {{
        background: rgba(255, 255, 255, 0.92);
        color: {INK};
        font-weight: 600;
        border-color: {EDGE_STRONG};
    }}
    QTabBar::tab:hover:!selected {{
        background: rgba(255, 255, 255, 0.62);
    }}

    /* ---------- 列表 / 滚动区 ---------- */
    QListWidget {{
        background: rgba(255, 255, 255, 0.62);
        border: 1px solid {EDGE};
        border-radius: 9px;
        padding: 3px;
    }}
    QListWidget::item {{ padding: 3px; border-radius: 6px; }}
    QListWidget::item:selected {{
        background: rgba(31, 111, 235, 0.18);
        color: {INK};
    }}
    QScrollArea {{ background: transparent; border: none; }}
    QScrollArea > QWidget > QWidget {{ background: transparent; }}

    /* ---------- 进度条 ---------- */
    QProgressBar {{
        border: 1px solid {EDGE};
        border-radius: 8px;
        background: rgba(255, 255, 255, 0.62);
        text-align: center;
        color: {INK_SOFT};
        height: 20px;
    }}
    QProgressBar::chunk {{
        border-radius: 7px;
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 rgba(96, 160, 250, 0.95), stop:1 rgba(31, 111, 235, 0.92));
    }}

    /* ---------- 复选框 ---------- */
    QCheckBox {{ color: {INK_SOFT}; spacing: 6px; }}
    QCheckBox::indicator {{
        width: 15px; height: 15px;
        border-radius: 4px;
        border: 1px solid {EDGE};
        background: rgba(255, 255, 255, 0.80);
    }}
    QCheckBox::indicator:checked {{
        background: {ACCENT};
        border-color: {ACCENT};
    }}

    /* ---------- 滚动条 ---------- */
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
    QScrollBar::handle:vertical {{
        background: rgba(120, 140, 165, 0.50);
        border-radius: 5px; min-height: 28px;
    }}
    QScrollBar::handle:vertical:hover {{ background: rgba(96, 116, 142, 0.70); }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
    QScrollBar::handle:horizontal {{
        background: rgba(120, 140, 165, 0.50); border-radius: 5px; min-width: 28px;
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

    /* ---------- 日志面板 ---------- */
    QPlainTextEdit#LogView {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 rgba(22, 30, 40, 0.90), stop:1 rgba(14, 20, 28, 0.88));
        border: 1px solid rgba(255, 255, 255, 0.28);
        border-radius: 10px;
        color: #d7dfe8;
        padding: 6px;
    }}

    /* ---------- 其他 ---------- */
    QStatusBar {{ background: transparent; color: {INK_FAINT}; }}
    QSplitter::handle {{ background: transparent; height: 8px; }}
    QSizeGrip {{ width: 14px; height: 14px; background: transparent; }}

    QToolTip {{
        background: #f8fbff;
        color: {INK};
        border: 1px solid {EDGE_STRONG};
        padding: 5px 8px;
    }}
    """
