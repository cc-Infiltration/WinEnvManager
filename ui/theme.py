"""主题：Purple 深色配色（Material 3 角色名）、全局 QSS、Material 图标字体加载。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QIcon, QPainter, QPixmap

# ---------------------------------------------------------------------------
# 配色：全部通过 M3 角色名引用（Purple 深色方案）
# ---------------------------------------------------------------------------

PRIMARY = "#D2BCFC"
ON_PRIMARY = "#32226F"
PRIMARY_CONTAINER = "#4C3889"
ON_PRIMARY_CONTAINER = "#E9DDFF"

SECONDARY = "#CDC1E1"
ON_SECONDARY = "#332D41"
SECONDARY_CONTAINER = "#4B425D"
ON_SECONDARY_CONTAINER = "#E9DDFD"

TERTIARY = "#FFB1C8"
ON_TERTIARY = "#51112B"
TERTIARY_CONTAINER = "#6C3644"
ON_TERTIARY_CONTAINER = "#FDDAE1"

ERROR = "#F2B8B5"
ON_ERROR = "#601410"
ERROR_CONTAINER = "#8C1D18"
ON_ERROR_CONTAINER = "#F9DEDC"

SURFACE = "#141317"
ON_SURFACE = "#E4E1E7"
ON_SURFACE_VARIANT = "#C9C4D1"
OUTLINE = "#938F9B"
OUTLINE_VARIANT = "#494550"

INVERSE_SURFACE = "#E4E1E7"
INVERSE_ON_SURFACE = "#313034"
INVERSE_PRIMARY = "#6750A4"

SURFACE_LOWEST = "#0F0E13"
SURFACE_CONTAINER_LOW = "#1C1B1F"
SURFACE_CONTAINER = "#201F23"
SURFACE_CONTAINER_HIGH = "#2B292D"
SURFACE_CONTAINER_HIGHEST = "#363438"

# 派生交互态（在角色基础上略作提亮/压暗，不引入新色相）
PRIMARY_HOVER = "#DCCDFD"
PRIMARY_PRESSED = "#C6AFF9"
TONAL_HOVER = "#574C6B"
TONAL_PRESSED = "#63567A"
CONTAINER_HOVER = "#5C4899"
CONTAINER_PRESSED = "#443380"

FONTS_DIR = Path(__file__).parent / "assets" / "fonts"

ICON_FAMILIES: dict[str, str] = {}
ICON_CODEPOINTS: dict[str, int] = {}


def load_material_fonts() -> None:
    """加载 Material Icons 字体（圆角填充 + 描边）与码点表。"""
    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    files = {
        "round": "MaterialIconsRound-Regular.otf",
        "outlined": "MaterialIconsOutlined-Regular.otf",
    }
    for key, filename in files.items():
        path = FONTS_DIR / filename
        if path.exists():
            font_id = QFontDatabase.addApplicationFont(str(path))
            families = QFontDatabase.applicationFontFamilies(font_id)
            if families:
                ICON_FAMILIES[key] = families[0]

    codepoints_path = FONTS_DIR / "MaterialIcons-Regular.codepoints"
    if codepoints_path.exists():
        for line in codepoints_path.read_text("utf-8").splitlines():
            parts = line.split()
            if len(parts) == 2:
                try:
                    ICON_CODEPOINTS[parts[0]] = int(parts[1], 16)
                except ValueError:
                    continue


def icon_font(style: str = "round") -> QFont:
    family = ICON_FAMILIES.get(style) or ICON_FAMILIES.get("round")
    font = QFont(family or "")
    font.setPixelSize(24)
    return font


def glyph(name: str, style: str = "round") -> str:
    """图标名 → 字体字形字符；未知名称回退为帮助图标。"""
    code = ICON_CODEPOINTS.get(name)
    if code is None:
        code = ICON_CODEPOINTS.get("help_outline", ord("?"))
    return chr(code)


def with_alpha(hex_color: str, alpha: int) -> QColor:
    c = QColor(hex_color)
    c.setAlpha(max(0, min(255, alpha)))
    return c


def render_icon(name: str, color: str, size: int = 22) -> QIcon:
    """把 Material 字形渲染为 QIcon（按钮 setIcon 用）。"""
    pixmap = QPixmap(size + 4, size + 4)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    font = icon_font("round")
    font.setPixelSize(size)
    painter.setFont(font)
    painter.setPen(QColor(color))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, glyph(name))
    painter.end()
    return QIcon(pixmap)


def build_qss() -> str:
    """全局样式表：按钮胶囊形、深色控件、细滚动条等。"""
    return f"""
    QWidget {{
        color: {ON_SURFACE};
        font-size: 14px;
        background: {SURFACE};
    }}
    QWidget:disabled {{ color: {OUTLINE}; }}
    QToolTip {{
        background: {SURFACE_CONTAINER_HIGHEST};
        color: {ON_SURFACE};
        border: 1px solid {OUTLINE_VARIANT};
        padding: 4px 8px;
        border-radius: 4px;
    }}

    /* 图标按钮（48dp 圆形热区） */
    QPushButton#iconBtn {{
        background: transparent;
        border: 1px solid transparent;
        border-radius: 24px;
        font-family: "{ICON_FAMILIES.get('round', '')}";
        font-size: 22px;
        color: {ON_SURFACE_VARIANT};
    }}
    QPushButton#iconBtn:hover {{ background: {SURFACE_CONTAINER_HIGH}; }}
    QPushButton#iconBtn:pressed {{ background: {SURFACE_CONTAINER_HIGHEST}; }}

    /* 填充按钮（胶囊） */
    QPushButton#filledBtn {{
        background: {PRIMARY};
        color: {ON_PRIMARY};
        border: 1px solid transparent;
        border-radius: 20px;
        padding: 10px 24px;
        font-size: 14px;
        font-weight: 600;
    }}
    QPushButton#filledBtn:hover {{ background: {PRIMARY_HOVER}; }}
    QPushButton#filledBtn:pressed {{ background: {PRIMARY_PRESSED}; }}

    /* 色调按钮（胶囊） */
    QPushButton#tonalBtn {{
        background: {SECONDARY_CONTAINER};
        color: {ON_SECONDARY_CONTAINER};
        border: 1px solid transparent;
        border-radius: 20px;
        padding: 10px 24px;
        font-size: 14px;
        font-weight: 600;
    }}
    QPushButton#tonalBtn:hover {{ background: {TONAL_HOVER}; }}
    QPushButton#tonalBtn:pressed {{ background: {TONAL_PRESSED}; }}

    /* 悬浮操作按钮（胶囊） */
    QPushButton#fabBtn {{
        background: {PRIMARY_CONTAINER};
        color: {ON_PRIMARY_CONTAINER};
        border: 1px solid transparent;
        border-radius: 24px;
        padding: 12px 22px 12px 18px;
        font-size: 14px;
        font-weight: 600;
    }}
    QPushButton#fabBtn:hover {{ background: {CONTAINER_HOVER}; }}
    QPushButton#fabBtn:pressed {{ background: {CONTAINER_PRESSED}; }}

    /* 文本按钮 */
    QPushButton#textBtn {{
        background: transparent;
        color: {PRIMARY};
        border: 1px solid transparent;
        border-radius: 14px;
        padding: 8px 16px;
        font-size: 14px;
        font-weight: 600;
    }}
    QPushButton#textBtn:hover {{ background: rgba(210, 188, 252, 30); }}

    /* 消息条动作按钮 */
    QPushButton#snackAction {{
        background: transparent;
        color: {INVERSE_PRIMARY};
        border: 1px solid transparent;
        border-radius: 14px;
        padding: 4px 12px;
        font-size: 14px;
        font-weight: 600;
    }}
    QPushButton#snackAction:hover {{ background: rgba(103, 80, 164, 40); }}

    /* 对话框输入框 */
    QLineEdit#dialogInput, QPlainTextEdit#dialogInput {{
        background: {SURFACE_CONTAINER};
        border: 1px solid {OUTLINE_VARIANT};
        border-radius: 12px;
        padding: 8px 12px;
        font-size: 14px;
        color: {ON_SURFACE};
        selection-background-color: {PRIMARY_CONTAINER};
    }}
    QLineEdit#dialogInput:focus, QPlainTextEdit#dialogInput:focus {{
        border: 1px solid {PRIMARY};
    }}
    QLineEdit#dialogInput:error {{
        border: 1px solid {ERROR};
    }}

    /* 菜单 */
    QMenu {{
        background: {SURFACE_CONTAINER_HIGH};
        border: 1px solid {OUTLINE_VARIANT};
        border-radius: 12px;
        padding: 6px;
    }}
    QMenu::item {{
        color: {ON_SURFACE};
        padding: 8px 24px;
        border-radius: 8px;
        font-size: 14px;
    }}
    QMenu::item:selected {{ background: {SECONDARY_CONTAINER}; }}
    QMenu::separator {{
        height: 1px;
        background: {OUTLINE_VARIANT};
        margin: 4px 8px;
    }}

    /* 滚动条 */
    QScrollArea {{ border: none; background: transparent; }}
    QScrollArea > QWidget > QWidget {{ background: transparent; }}
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 4px 2px;
    }}
    QScrollBar::handle:vertical {{
        background: {OUTLINE_VARIANT};
        border-radius: 4px;
        min-height: 32px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {OUTLINE}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 8px;
        margin: 2px 4px;
    }}
    QScrollBar::handle:horizontal {{
        background: {OUTLINE_VARIANT};
        border-radius: 4px;
        min-width: 32px;
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: none; }}
    """
