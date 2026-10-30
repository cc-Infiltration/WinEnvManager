"""变量管理器主窗口：四个屏幕、滑动转场、环境变量增删改查、备份与设置。"""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
from datetime import datetime

from PySide6.QtCore import (
    QEasingCurve,
    QPointF,
    QPoint,
    QParallelAnimationGroup,
    QPropertyAnimation,
    QRectF,
    Qt,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QFontMetrics,
    QIcon,
    QPainter,
    QPainterPath,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

import core as app_core
from ui import theme
from ui.theme import glyph
from ui.widgets import (
    AppBar,
    ClickableRow,
    EmptyState,
    Fab,
    Icon,
    IconButton,
    PathListEditor,
    ScopeRadio,
    SearchField,
    SelectVarRow,
    Snackbar,
    StyledDialog,
    Switch,
)

APP_VERSION = "1.0.0"

SCREENS = ["home", "find", "backup", "settings"]
SCREEN_TITLES = {
    "home": "变量管理器",
    "find": "查找",
    "backup": "备份",
    "settings": "设置",
}


def m3_ease() -> "QEasingCurve":
    """Material 3 emphasized easing：三阶贝塞尔 cubic-bezier(0.2, 0, 0, 1)。

    前快后缓，用于位移（页面滑动、胶囊指示器），观感利落不拖沓。
    """
    c = QEasingCurve(QEasingCurve.Type.BezierSpline)
    c.addCubicBezierSegment(QPointF(0.2, 0.0), QPointF(0.0, 1.0), QPointF(1.0, 1.0))
    return c


def m3_ease_std() -> "QEasingCurve":
    """Material 3 standard easing：三阶贝塞尔 cubic-bezier(0.4, 0, 0.2, 1)。

    对称 S 曲线，用于不透明度淡入淡出。
    """
    c = QEasingCurve(QEasingCurve.Type.BezierSpline)
    c.addCubicBezierSegment(QPointF(0.4, 0.0), QPointF(0.2, 1.0), QPointF(1.0, 1.0))
    return c


def glyph_icon(name: str, color: str, size: int = 20) -> QIcon:
    """把 Material 字形渲染为 QIcon（与普通文字混排时使用）。"""
    pixmap = QPixmap(size + 4, size + 4)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    font = theme.icon_font("round")
    font.setPixelSize(size)
    painter.setFont(font)
    painter.setPen(QColor(color))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, glyph(name))
    painter.end()
    return QIcon(pixmap)


# ---------------------------------------------------------------------------
# 屏幕容器（手动管理层叠与转场）
# ---------------------------------------------------------------------------


class ContentStack(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(f"ContentStack {{ background: {theme.SURFACE}; }}")
        self.pages: dict[str, QWidget] = {}

    def add_page(self, name: str, page: QWidget) -> None:
        page.setParent(self)
        page.setGeometry(self.rect())
        page.setVisible(False)
        self.pages[name] = page

    def resizeEvent(self, event) -> None:  # noqa: N802
        for page in self.pages.values():
            page.setGeometry(self.rect())
        super().resizeEvent(event)


# ---------------------------------------------------------------------------
# 底部导航栏（80dp，胶囊指示器滑动）
# ---------------------------------------------------------------------------

_NAV_ITEMS = [
    ("home", "首页", "home"),
    ("find", "查找", "search"),
    ("backup", "备份", "save"),
    ("settings", "设置", "settings"),
]


class NavBar(QWidget):
    changed = Signal(str)

    HEIGHT = 80

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(self.HEIGHT)
        self._current = 0
        self._items: list[tuple[ClickableRow, Icon, QLabel]] = []

        self._pill = QLabel(self)
        self._pill.setStyleSheet(
            f"background: {theme.SECONDARY_CONTAINER}; border-radius: 16px;"
        )
        self._pill.setFixedSize(64, 32)

        for index, (key, label, icon) in enumerate(_NAV_ITEMS):
            row = ClickableRow(radius=16, hover_color=theme.with_alpha(theme.ON_SURFACE, 12).name(QColor.NameFormat.HexArgb), parent=self)
            row.clicked.connect(lambda _=False, i=index: self._on_click(i))
            icon_w = Icon(icon, 24, theme.ON_SURFACE_VARIANT, style="outlined", parent=row)
            label_w = QLabel(label, row)
            label_w.setStyleSheet(
                f"font-size: 12px; font-weight: 500;"
                f"color: {theme.ON_SURFACE_VARIANT}; background: transparent;"
            )
            label_w.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._items.append((row, icon_w, label_w))

        self._pill_anim: QPropertyAnimation | None = None
        self._apply(0, animate=False)

    def _on_click(self, index: int) -> None:
        if index != self._current:
            self.set_active(index)
            self.changed.emit(_NAV_ITEMS[index][0])

    def set_active(self, index: int, animate: bool = True) -> None:
        self._apply(index, animate=animate)

    def _item_center_x(self, index: int) -> int:
        item_w = self.width() / len(_NAV_ITEMS)
        return int(index * item_w + item_w / 2)

    def _apply(self, index: int, animate: bool) -> None:
        self._current = index
        for i, (row, icon_w, label_w) in enumerate(self._items):
            item_w = self.width() / len(_NAV_ITEMS)
            x = int(i * item_w + (item_w - 88) / 2)
            row.setGeometry(x, 0, 88, self.HEIGHT)
            active = i == index
            icon_w.set_icon_name(_NAV_ITEMS[i][2], "round" if active else "outlined")
            icon_w.set_color(theme.ON_SECONDARY_CONTAINER if active else theme.ON_SURFACE_VARIANT)
            label_w.setStyleSheet(
                f"font-size: 12px; font-weight: 500;"
                f"color: {theme.ON_SURFACE if active else theme.ON_SURFACE_VARIANT};"
                "background: transparent;"
            )
            icon_w.move((88 - icon_w.width()) // 2, 18)
            label_w.setGeometry(0, 52, 88, 18)

        target = QPoint(self._item_center_x(index) - 32, 16)
        if animate:
            self._pill_anim = QPropertyAnimation(self._pill, b"pos", self)
            self._pill_anim.setDuration(380)
            self._pill_anim.setEasingCurve(m3_ease())
            self._pill_anim.setEndValue(target)
            self._pill_anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        else:
            self._pill.move(target)

    def resizeEvent(self, event) -> None:  # noqa: N802
        self._apply(self._current, animate=False)
        super().resizeEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(theme.SURFACE_CONTAINER))
        painter.end()


# ---------------------------------------------------------------------------
# 变量行 / 备份行
# ---------------------------------------------------------------------------


def _elided(text: str, width: int, font) -> str:
    metrics = QFontMetrics(font)
    return metrics.elidedText(text.replace("\n", " "), Qt.TextElideMode.ElideRight, width)


def _match_score(haystack: str, needle: str) -> int | None:
    """模糊匹配评分：完全相等 0 < 前缀 1 < 子串 2+位置 < 子序列 60+间隙；不命中返回 None。"""
    if haystack == needle:
        return 0
    idx = haystack.find(needle)
    if idx >= 0:
        return 1 if idx == 0 else 2 + min(idx, 10)
    # 子序列匹配：字符按顺序出现但不必连续（如 "pv" 命中 "PathVars"）
    pos = 0
    gap = 0
    for ch in needle:
        found = haystack.find(ch, pos)
        if found < 0:
            return None
        gap += found - pos
        pos = found + 1
    return 60 + min(gap, 20)


class VarRow(ClickableRow):
    def __init__(self, v: app_core.Var, on_edit, on_delete, parent=None) -> None:
        super().__init__(radius=14, hover_color=theme.SURFACE_CONTAINER_HIGH, parent=parent)
        self._var = v

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 8, 6)
        layout.setSpacing(12)

        scope_icon = "dns" if v.scope == app_core.SCOPE_SYSTEM else "person"
        layout.addWidget(Icon(scope_icon, 22, theme.ON_SURFACE_VARIANT))

        info = QVBoxLayout()
        info.setSpacing(2)
        name = QLabel(v.name, self)
        name.setStyleSheet(
            f"font-size: 16px; font-weight: 500; color: {theme.ON_SURFACE};"
            "background: transparent;"
        )
        value = QLabel(
            _elided(v.value if v.value else "（空值）", 560, self.font()), self
        )
        value.setStyleSheet(
            f"font-size: 14px; color: {theme.ON_SURFACE_VARIANT}; background: transparent;"
        )
        info.addWidget(name)
        info.addWidget(value)
        layout.addLayout(info, 1)

        edit_btn = IconButton("edit", "编辑")
        edit_btn.clicked.connect(lambda: on_edit(v))
        layout.addWidget(edit_btn)

        del_btn = IconButton("delete_outline", "删除", color=theme.ERROR)
        del_btn.clicked.connect(lambda: on_delete(v))
        layout.addWidget(del_btn)

        self.clicked.connect(lambda: on_edit(v))


class BackupRow(ClickableRow):
    def __init__(self, item: dict, on_restore, on_delete, parent=None) -> None:
        super().__init__(radius=14, hover_color=theme.SURFACE_CONTAINER_HIGH, parent=parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 8, 6)
        layout.setSpacing(12)
        layout.addWidget(Icon("history", 22, theme.ON_SURFACE_VARIANT))

        info = QVBoxLayout()
        info.setSpacing(2)

        name_row = QHBoxLayout()
        name_row.setSpacing(6)
        name = QLabel(item["name"], self)
        name.setStyleSheet(
            f"font-size: 16px; font-weight: 500; color: {theme.ON_SURFACE};"
            "background: transparent;"
        )
        name_row.addWidget(name)
        if str(item["name"]).startswith("auto_"):
            badge = QLabel("自动", self)
            badge.setStyleSheet(
                f"font-size: 11px; font-weight: 500; color: {theme.ON_SECONDARY_CONTAINER};"
                f"background: {theme.SECONDARY_CONTAINER}; border-radius: 8px;"
                "padding: 1px 8px;"
            )
            name_row.addWidget(badge)
        name_row.addStretch(1)
        info.addLayout(name_row)

        count_text = (
            f"{item['count']} 个变量" if item["count"] is not None else "未知大小"
        )
        when = datetime.fromtimestamp(item["mtime"]).strftime("%Y-%m-%d %H:%M")
        sub = QLabel(f"{when} · {count_text}", self)
        sub.setStyleSheet(
            f"font-size: 14px; color: {theme.ON_SURFACE_VARIANT}; background: transparent;"
        )
        info.addWidget(sub)
        layout.addLayout(info, 1)

        restore_btn = IconButton("restore", "恢复此备份")
        restore_btn.clicked.connect(lambda: on_restore(item))
        layout.addWidget(restore_btn)

        del_btn = IconButton("delete_outline", "删除此备份", color=theme.ERROR)
        del_btn.clicked.connect(lambda: on_delete(item))
        layout.addWidget(del_btn)


# ---------------------------------------------------------------------------
# 圆角容器（列表背景框）
# ---------------------------------------------------------------------------


class RoundedListFrame(QFrame):
    """圆角 28 的列表容器，支持右下角悬浮按钮。"""

    def __init__(self, bgcolor: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            f"RoundedListFrame {{ background: {bgcolor}; border-radius: 28px; }}"
        )
        self._fab: QWidget | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)

        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.rows_host = QWidget(self.scroll)
        self.rows_vbox = QVBoxLayout(self.rows_host)
        self.rows_vbox.setContentsMargins(4, 4, 4, 8)
        self.rows_vbox.setSpacing(2)
        self.rows_vbox.addStretch(1)
        self.scroll.setWidget(self.rows_host)
        outer.addWidget(self.scroll)

    def set_fab(self, fab: QWidget) -> None:
        self._fab = fab
        fab.setParent(self)
        fab.raise_()
        # 底部留出 FAB 高度 + 间距，避免悬浮按钮遮挡最后一行
        m = self.rows_vbox.contentsMargins()
        self.rows_vbox.setContentsMargins(m.left(), m.top(), m.right(), 80)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self._fab is not None:
            fab = self._fab
            fab.adjustSize()
            fab.move(self.width() - fab.width() - 16, self.height() - fab.height() - 16)

    def clear_rows(self) -> None:
        while self.rows_vbox.count() > 1:
            item = self.rows_vbox.takeAt(0)
            w = item.widget()
            if w is not None:
                w.hide()  # 立即隐藏，避免 deleteLater 延迟期间叠印
                w.deleteLater()

    def add_row(self, widget: QWidget, stretch: bool = False) -> None:
        self.rows_vbox.insertWidget(self.rows_vbox.count() - 1, widget, 0 if not stretch else 1)

    def add_stretch_row(self, widget: QWidget) -> None:
        self.rows_vbox.insertWidget(self.rows_vbox.count() - 1, widget, 1)


def section_header(text: str) -> QLabel:
    label = QLabel(text)
    label.setStyleSheet(
        f"font-size: 12px; font-weight: 500; color: {theme.ON_SURFACE_VARIANT};"
        "background: transparent;"
    )
    label.setContentsMargins(8, 8, 8, 4)
    return label


def section_card(title: str, rows: list[QWidget]) -> QFrame:
    card = QFrame()
    card.setStyleSheet(
        f"QFrame {{ background: {theme.SURFACE_CONTAINER_LOW}; border-radius: 20px; }}"
    )
    vbox = QVBoxLayout(card)
    vbox.setContentsMargins(8, 8, 8, 8)
    vbox.setSpacing(2)
    header = QLabel(title)
    header.setStyleSheet(
        f"font-size: 14px; font-weight: 500; color: {theme.ON_SURFACE_VARIANT};"
        "background: transparent;"
    )
    header.setContentsMargins(12, 8, 12, 6)
    vbox.addWidget(header)
    for row in rows:
        vbox.addWidget(row)
    return card


def settings_row(
    icon: str, title: str, subtitle: str, trailing: QWidget | None = None
) -> QWidget:
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(12, 8, 12, 8)
    layout.setSpacing(12)
    layout.addWidget(Icon(icon, 22, theme.ON_SURFACE_VARIANT))
    info = QVBoxLayout()
    info.setSpacing(2)
    t = QLabel(title, row)
    t.setStyleSheet(
        f"font-size: 16px; font-weight: 500; color: {theme.ON_SURFACE};"
        "background: transparent;"
    )
    s = QLabel(subtitle, row)
    s.setStyleSheet(
        f"font-size: 13px; color: {theme.ON_SURFACE_VARIANT}; background: transparent;"
    )
    s.setWordWrap(True)
    info.addWidget(t)
    info.addWidget(s)
    layout.addLayout(info, 1)
    if trailing is not None:
        layout.addWidget(trailing)
    return row


# ---------------------------------------------------------------------------
# 主窗口
# ---------------------------------------------------------------------------


class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("变量管理器")
        self.resize(900, 640)
        self.setMinimumSize(900, 640)

        app_core.ensure_dirs()
        self.settings = app_core.load_settings()
        self.admin = app_core.is_admin()
        self._cache: dict[str, list[app_core.Var]] = {
            app_core.SCOPE_USER: [],
            app_core.SCOPE_SYSTEM: [],
        }

        # 状态
        self.home_sys = True
        self.home_user = True
        self.find_user = True
        self.find_sys = True
        self.find_desc = False
        self.current = "home"
        self._animating = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.stack = ContentStack(self)
        root.addWidget(self.stack, 1)

        self._build_home()
        self._build_find()
        self._build_backup()
        self._build_settings()

        self.nav = NavBar(self)
        self.nav.changed.connect(self._on_nav)
        root.addWidget(self.nav)

        self.snackbar = Snackbar(self)

        self._reload_vars()
        self._refresh_home()
        self._refresh_find()
        self._refresh_backups()
        self._show_page("home", animate=False)

    # ------------------------------------------------------------------
    # 数据
    # ------------------------------------------------------------------

    def _reload_vars(self) -> None:
        for scope in (app_core.SCOPE_USER, app_core.SCOPE_SYSTEM):
            try:
                self._cache[scope] = app_core.list_vars(scope)
            except RuntimeError:
                self._cache[scope] = []

    def _after_mutation(self, broadcast: bool = True) -> None:
        self._reload_vars()
        self._refresh_home()
        self._refresh_find()
        if broadcast and self.settings.get("broadcast", True):
            app_core.broadcast_change()
        QApplication.processEvents()

    def toast(
        self,
        text: str,
        *,
        action_label: str | None = None,
        on_action=None,
        error: bool = False,
        duration_ms: int = 2000,
    ) -> None:
        self.snackbar.show_toast(
            text,
            action_label=action_label,
            on_action=on_action,
            error=error,
            duration_ms=duration_ms,
        )

    # ------------------------------------------------------------------
    # 转场
    # ------------------------------------------------------------------

    def _enter_offset(self, name: str) -> QPoint:
        w, h = self.stack.width(), self.stack.height()
        if name == "find":
            return QPoint(0, -int(h * 0.5))
        if name in ("backup", "settings"):
            return QPoint(int(w * 0.6), 0)
        return QPoint(0, 0)

    def _show_page(self, target: str, animate: bool = True) -> None:
        if target == "backup":
            # 每次进入备份页都从磁盘重建列表，杜绝已删除备份的陈旧显示
            self._refresh_backups()
        if target == self.current and animate:
            return
        previous = self.current
        incoming = self.stack.pages[target]
        outgoing = self.stack.pages[previous] if animate else None

        if not animate:
            for name, page in self.stack.pages.items():
                page.setVisible(name == target)
                page.move(QPoint(0, 0))
                if name == target:
                    # 无特效即完全不透明，避免常驻离屏渲染
                    page.setGraphicsEffect(None)
            self.current = target
            return

        if self._animating:
            return
        self._animating = True
        incoming.raise_()
        incoming.setVisible(True)
        incoming.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        if outgoing is not None:
            outgoing.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        start = self._enter_offset(target)
        incoming.move(start)
        self._set_opacity(incoming, 0.0)

        group = QParallelAnimationGroup(self)

        move_in = QPropertyAnimation(incoming, b"pos", group)
        move_in.setDuration(420)
        move_in.setEasingCurve(m3_ease())
        move_in.setEndValue(QPoint(0, 0))
        group.addAnimation(move_in)

        fade_in = QPropertyAnimation(self._effect_of(incoming), b"opacity", group)
        fade_in.setDuration(380)
        fade_in.setEasingCurve(m3_ease_std())
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        group.addAnimation(fade_in)

        if outgoing is not None:
            move_out = QPropertyAnimation(outgoing, b"pos", group)
            move_out.setDuration(420)
            move_out.setEasingCurve(m3_ease())
            move_out.setEndValue(self._enter_offset(previous))
            group.addAnimation(move_out)

            fade_out = QPropertyAnimation(self._effect_of(outgoing), b"opacity", group)
            fade_out.setDuration(300)
            fade_out.setEasingCurve(m3_ease_std())
            fade_out.setStartValue(1.0)
            fade_out.setEndValue(0.0)
            group.addAnimation(fade_out)

        def on_finished() -> None:
            if outgoing is not None:
                outgoing.setVisible(False)
                outgoing.move(self._enter_offset(previous))
                outgoing.setAttribute(
                    Qt.WidgetAttribute.WA_TransparentForMouseEvents, False
                )
            incoming.move(QPoint(0, 0))
            self._set_opacity(incoming, 1.0)
            # 转场结束即卸载透明度特效：特效会强制页面离屏渲染，
            # 导致滚动内容在某些环境下出现"滚轮转了但画面不动"的问题
            incoming.setGraphicsEffect(None)
            if outgoing is not None:
                outgoing.setGraphicsEffect(None)
            self.current = target
            self._animating = False

        group.finished.connect(on_finished)
        group.start(QParallelAnimationGroup.DeletionPolicy.DeleteWhenStopped)
        self.current = target

    def _effect_of(self, page: QWidget) -> QGraphicsOpacityEffect:
        effect = page.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(page)
            effect.setOpacity(1.0)
            page.setGraphicsEffect(effect)
        return effect

    def _set_opacity(self, page: QWidget, value: float) -> None:
        self._effect_of(page).setOpacity(value)

    def _on_nav(self, key: str) -> None:
        self._show_page(key)

    # ------------------------------------------------------------------
    # 首页
    # ------------------------------------------------------------------

    def _build_home(self) -> None:
        page = QFrame(self.stack)
        page.setStyleSheet(f"QFrame {{ background: {theme.SURFACE}; }}")
        self.stack.add_page("home", page)

        vbox = QVBoxLayout(page)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        refresh_btn = IconButton("refresh", "刷新")
        refresh_btn.clicked.connect(self._on_refresh)
        home_title = "变量管理器（管理员）" if self.admin else "变量管理器"
        vbox.addWidget(AppBar(home_title, actions=[refresh_btn]))

        radio_row = QWidget()
        h = QHBoxLayout(radio_row)
        h.setContentsMargins(16, 4, 16, 8)
        h.setSpacing(8)
        self.home_radio_sys = ScopeRadio("系统", checked=True)
        self.home_radio_user = ScopeRadio("用户", checked=True)
        self.home_radio_sys.toggled.connect(lambda _: self._refresh_home_wrap())
        self.home_radio_user.toggled.connect(lambda _: self._refresh_home_wrap())
        h.addWidget(self.home_radio_sys)
        h.addWidget(self.home_radio_user)
        h.addStretch(1)
        vbox.addWidget(radio_row)

        self.home_frame = RoundedListFrame(theme.SURFACE_CONTAINER_LOW)
        fab = Fab("新建变量", "add")
        fab.clicked.connect(lambda: self._open_var_dialog(None))
        self.home_frame.set_fab(fab)
        vbox.addWidget(self.home_frame, 1)

    def _refresh_home_wrap(self) -> None:
        self.home_sys = self.home_radio_sys.is_checked()
        self.home_user = self.home_radio_user.is_checked()
        self._refresh_home()

    def _on_refresh(self) -> None:
        self._reload_vars()
        self._refresh_home()
        self._refresh_find()
        self._refresh_backups()
        self.toast("已刷新")

    def _refresh_home(self) -> None:
        frame = self.home_frame
        frame.clear_rows()
        sections: list[tuple[str, str]] = []
        if self.home_sys:
            sections.append((app_core.SCOPE_SYSTEM, "系统变量"))
        if self.home_user:
            sections.append((app_core.SCOPE_USER, "用户变量"))

        if not sections:
            frame.add_stretch_row(
                EmptyState(
                    "radio_button_unchecked",
                    "未选择任何范围",
                    "选中“系统”或“用户”以查看对应的环境变量",
                )
            )
            return

        total = 0
        for scope, label in sections:
            frame.add_row(section_header(label))
            for v in self._cache[scope]:
                frame.add_row(VarRow(v, self._open_var_dialog, self._delete_var))
                total += 1
        if total == 0:
            frame.clear_rows()
            frame.add_stretch_row(
                EmptyState("tune", "暂无环境变量", "点击右下角“新建变量”创建")
            )

    # ------------------------------------------------------------------
    # 查找页
    # ------------------------------------------------------------------

    def _build_find(self) -> None:
        page = QFrame(self.stack)
        page.setStyleSheet(f"QFrame {{ background: {theme.SURFACE_CONTAINER_LOW}; }}")
        self.stack.add_page("find", page)

        vbox = QVBoxLayout(page)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        sort_btn = IconButton("menu", "排序方式")
        sort_btn.clicked.connect(self._show_sort_menu)
        more_btn = IconButton("more_vert", "更多")
        more_btn.clicked.connect(self._show_more_menu)
        vbox.addWidget(AppBar("查找", leading=sort_btn, actions=[more_btn]))

        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(16, 4, 16, 8)
        h.setSpacing(8)
        self.find_radio_user = ScopeRadio("用户", checked=True)
        self.find_radio_sys = ScopeRadio("系统", checked=True)
        self.find_radio_user.toggled.connect(lambda _: self._refresh_find_wrap())
        self.find_radio_sys.toggled.connect(lambda _: self._refresh_find_wrap())
        h.addWidget(self.find_radio_user)
        h.addWidget(self.find_radio_sys)
        self.search_field = SearchField("搜索变量")
        self.search_field.text_changed.connect(lambda _: self._refresh_find())
        h.addWidget(self.search_field, 1)
        vbox.addWidget(row)

        self.find_frame = RoundedListFrame(theme.SURFACE_CONTAINER)
        vbox.addWidget(self.find_frame, 1)

    def _show_sort_menu(self) -> None:
        menu = QMenu(self)
        menu.addAction("按名称 A→Z", lambda: self._set_sort(False))
        menu.addAction("按名称 Z→A", lambda: self._set_sort(True))
        menu.exec(sort_btn_pos := self.cursor().pos())
        menu.deleteLater()

    def _show_more_menu(self) -> None:
        menu = QMenu(self)
        menu.addAction("复制全部为文本", self._copy_find_results)
        menu.exec(self.cursor().pos())
        menu.deleteLater()

    def _set_sort(self, desc: bool) -> None:
        self.find_desc = desc
        self._refresh_find()

    def _refresh_find_wrap(self) -> None:
        self.find_user = self.find_radio_user.is_checked()
        self.find_sys = self.find_radio_sys.is_checked()
        self._refresh_find()

    def _find_pool(self) -> list[app_core.Var]:
        pool: list[app_core.Var] = []
        if self.find_user:
            pool.extend(self._cache[app_core.SCOPE_USER])
        if self.find_sys:
            pool.extend(self._cache[app_core.SCOPE_SYSTEM])
        q = self.search_field.text().strip().casefold()
        if not q:
            pool.sort(key=lambda v: v.name.casefold(), reverse=self.find_desc)
            return pool
        # 模糊匹配：名称命中优先于值命中（+100），同分内按名称排序
        scored: list[tuple[int, str, app_core.Var]] = []
        for v in pool:
            name = v.name.casefold()
            s = _match_score(name, q)
            if s is None:
                vs = _match_score(v.value.casefold(), q)
                if vs is None:
                    continue
                s = vs + 100
            scored.append((s, name, v))
        # 稳定排序两段式：先按名称排出 find_desc 顺序，再按分数稳定排
        scored.sort(key=lambda t: t[1], reverse=self.find_desc)
        scored.sort(key=lambda t: t[0])
        return [t[2] for t in scored]

    def _refresh_find(self) -> None:
        frame = self.find_frame
        frame.clear_rows()
        pool = self._find_pool()
        if not pool:
            query = self.search_field.text().strip()
            if query:
                empty = EmptyState("search_off", "未找到匹配的变量", "换个关键词试试")
            elif not (self.find_user or self.find_sys):
                empty = EmptyState(
                    "radio_button_unchecked", "未选择任何范围", "选中“用户”或“系统”以搜索"
                )
            else:
                empty = EmptyState("tune", "暂无环境变量")
            frame.add_stretch_row(empty)
            return
        for v in pool:
            frame.add_row(VarRow(v, self._open_var_dialog, self._delete_var))

    def _copy_find_results(self) -> None:
        pool = self._find_pool()
        if not pool:
            self.toast("没有可复制的结果", error=True)
            return
        lines = [
            f"[{'系统' if v.scope == app_core.SCOPE_SYSTEM else '用户'}] {v.name}={v.value}"
            for v in pool
        ]
        QApplication.clipboard().setText("\n".join(lines))
        self.toast(f"已复制 {len(pool)} 个变量到剪贴板")

    # ------------------------------------------------------------------
    # 变量编辑 / 删除
    # ------------------------------------------------------------------

    def _open_var_dialog(self, v: app_core.Var | None) -> None:
        is_new = v is None
        name_edit = QLineEdit(v.name if v else "")
        name_edit.setObjectName("dialogInput")
        name_edit.setPlaceholderText("变量名")
        value_edit = QPlainTextEdit(v.value if v else "")
        value_edit.setObjectName("dialogInput")
        value_edit.setPlaceholderText("变量值（多路径变量会自动切换为表格编辑）")
        value_edit.setFixedHeight(120)
        path_editor = PathListEditor(
            app_core.split_path_value(v.value) if v else [],
            checker=app_core.check_path_entry,
        )
        path_editor.on_open_entry = self._open_path_entry
        path_editor.setVisible(False)
        error_label = QLabel("", None)
        error_label.setStyleSheet(
            f"font-size: 12px; color: {theme.ERROR}; background: transparent;"
        )
        error_label.setVisible(False)

        # PATH 类变量（名称含 PATH 或值呈多路径形式）使用表格逐条编辑
        multi_mode = {"on": False}

        def set_multi(on: bool) -> None:
            if multi_mode["on"] == on:
                return
            multi_mode["on"] = on
            if on:
                path_editor.set_entries(
                    app_core.split_path_value(value_edit.toPlainText())
                )
                value_edit.setVisible(False)
                path_editor.setVisible(True)
            else:
                value_edit.setPlainText(path_editor.value())
                path_editor.setVisible(False)
                value_edit.setVisible(True)
            # 已显示的对话框切换模式后按新内容自适应高度
            parent = content.parentWidget()
            while parent is not None and not isinstance(parent, StyledDialog):
                parent = parent.parentWidget()
            if parent is not None and parent.isVisible():
                parent.adjustSize()

        def on_name_changed(text: str) -> None:
            if not multi_mode["on"] and app_core.is_path_var(text):
                set_multi(True)

        def on_value_changed() -> None:
            if not multi_mode["on"] and app_core.is_multi_path_value(
                value_edit.toPlainText()
            ):
                set_multi(True)

        name_edit.textChanged.connect(on_name_changed)
        value_edit.textChanged.connect(on_value_changed)

        content = QWidget()
        box = QVBoxLayout(content)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(12)
        box.addWidget(name_edit)
        box.addWidget(value_edit)
        box.addWidget(path_editor)

        # 已存在的 PATH 类 / 多值变量直接进入表格模式
        if v is not None and (
            app_core.is_path_var(v.name) or app_core.is_multi_path_value(v.value)
        ):
            set_multi(True)

        scope_state = {"scope": v.scope if v else app_core.SCOPE_USER}
        radios: list[ScopeRadio] = []

        if is_new:
            box.addWidget(
                self._field_label("保存到"),
            )
            pair_row = QWidget()
            ph = QHBoxLayout(pair_row)
            ph.setContentsMargins(0, 0, 0, 0)
            ph.setSpacing(8)
            r_user = ScopeRadio("用户", checked=scope_state["scope"] == "user", toggleable=False)
            r_sys = ScopeRadio(
                "系统",
                checked=scope_state["scope"] == "system",
                toggleable=False,
                enabled=self.admin,
            )
            radios = [r_user, r_sys]

            def make_sync(other: ScopeRadio, token: str):
                def sync(checked: bool) -> None:
                    if checked:
                        scope_state["scope"] = token
                        other.set_checked(False)

                return sync

            r_user.toggled.connect(make_sync(r_sys, "user"))
            r_sys.toggled.connect(make_sync(r_user, "system"))
            ph.addWidget(r_user)
            ph.addWidget(r_sys)
            ph.addStretch(1)
            box.addWidget(pair_row)
            if not self.admin:
                box.addWidget(
                    self._field_label(
                        "当前以普通权限运行，仅可创建用户变量", small=True
                    )
                )
        elif v.scope == app_core.SCOPE_SYSTEM and not self.admin:
            name_edit.setEnabled(False)
            value_edit.setEnabled(False)
            path_editor.setEnabled(False)
            box.addWidget(
                self._field_label("修改系统变量需要管理员权限（可在“设置”页获取）", small=True)
            )

        box.addWidget(error_label)

        dialog = StyledDialog(
            self,
            "新建变量" if is_new else "编辑变量",
            content,
            actions=[],
        )
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("textBtn")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(dialog.reject)
        save_btn = QPushButton("保存")
        save_btn.setObjectName("filledBtn")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        def save() -> None:
            name = name_edit.text().strip()
            value = (
                path_editor.value() if multi_mode["on"] else value_edit.toPlainText()
            )
            scope = scope_state["scope"]
            if is_new and scope == app_core.SCOPE_SYSTEM and not self.admin:
                dialog.reject()
                self.toast("写入系统变量需要管理员权限", error=True)
                return
            err = app_core.validate_name(
                name,
                scope,
                self._cache[app_core.SCOPE_USER] + self._cache[app_core.SCOPE_SYSTEM],
                editing=None if is_new else v.name,
            )
            if err:
                error_label.setText(err)
                error_label.setVisible(True)
                name_edit.setStyleSheet(
                    f"QLineEdit#dialogInput {{ border: 1px solid {theme.ERROR}; }}"
                )
                return
            try:
                new_name = name
                app_core.set_var(scope, new_name, value, kind=v.kind if v else None)
                if not is_new and (
                    v.scope != scope or new_name.casefold() != v.name.casefold()
                ):
                    app_core.delete_var(v.scope, v.name)
            except RuntimeError as exc:
                dialog.reject()
                self.toast(str(exc), error=True)
                return
            dialog.accept()
            # 读回校验：确保写入真实生效，系统编辑器与新进程可见
            written = app_core.read_var(scope, new_name)
            if written is None or written[0] != value:
                self._after_mutation()
                self.toast(f"保存 {name} 未生效，请检查权限后重试", error=True)
                return
            self._after_mutation()
            self.toast(f"已保存 {name}（已同步系统，新进程可见）")

        save_btn.clicked.connect(save)
        dialog.actions_row(cancel_btn, save_btn)

        # 加宽以完整显示 PATH 表格的"操作"列；高度限制在屏幕可用范围内，避免按钮区被截断
        screen_h = self.screen().availableGeometry().height()
        dialog.resize(
            max(640, int(self.width() * 0.72)),
            min(dialog.sizeHint().height(), screen_h - 72),
        )
        dialog.exec()

    @staticmethod
    def _field_label(text: str, small: bool = False) -> QLabel:
        label = QLabel(text)
        color = theme.ON_SURFACE_VARIANT
        size = 12 if small else 14
        weight = 400 if small else 500
        label.setStyleSheet(
            f"font-size: {size}px; font-weight: {weight}; color: {color};"
            "background: transparent;"
        )
        return label

    def _open_path_entry(self, entry: str) -> None:
        """打开路径条目对应的文件夹；不存在时 Snackbar 提示（与删除提示一致）。"""
        target = os.path.expandvars(entry.strip().strip('"'))
        try:
            if os.path.isdir(target):
                os.startfile(target)  # noqa: S606
                return
            if os.path.isfile(target):
                # 文件条目：打开所在文件夹并高亮该文件
                subprocess.Popen(["explorer", "/select,", target])  # noqa: S603
                return
        except OSError:
            pass
        self.toast(f"路径不存在：{entry}", error=True)

    def _delete_var(self, v: app_core.Var) -> None:
        if v.scope == app_core.SCOPE_SYSTEM and not self.admin:
            self.toast("删除系统变量需要管理员权限（可在“设置”页获取）", error=True)
            return
        try:
            app_core.delete_var(v.scope, v.name)
        except RuntimeError as exc:
            self.toast(str(exc), error=True)
            return
        self._after_mutation()

        def undo() -> None:
            try:
                app_core.set_var(v.scope, v.name, v.value, kind=v.kind)
            except RuntimeError as exc:
                self.toast(str(exc), error=True)
                return
            self._after_mutation()
            self.toast(f"已恢复 {v.name}")

        self.toast(f"已删除 {v.name}", action_label="撤销", on_action=undo)

    # ------------------------------------------------------------------
    # 备份页
    # ------------------------------------------------------------------

    def _build_backup(self) -> None:
        page = QFrame(self.stack)
        page.setStyleSheet(f"QFrame {{ background: {theme.SURFACE}; }}")
        self.stack.add_page("backup", page)

        vbox = QVBoxLayout(page)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        folder_btn = IconButton("folder_open", "打开备份文件夹")
        folder_btn.clicked.connect(self._open_backup_folder)
        vbox.addWidget(AppBar("备份", actions=[folder_btn]))

        btn_row = QWidget()
        h = QHBoxLayout(btn_row)
        h.setContentsMargins(16, 4, 16, 12)
        h.setSpacing(12)
        create_btn = QPushButton(" 创建备份")
        create_btn.setObjectName("filledBtn")
        create_btn.setIcon(glyph_icon("save", theme.ON_PRIMARY))
        create_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        create_btn.clicked.connect(self._create_backup_dialog)
        export_btn = QPushButton(" 导出当前变量")
        export_btn.setObjectName("tonalBtn")
        export_btn.setIcon(glyph_icon("upload", theme.ON_SECONDARY_CONTAINER))
        export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        export_btn.clicked.connect(self._export_dialog)
        import_btn = QPushButton(" 导入备份文件")
        import_btn.setObjectName("tonalBtn")
        import_btn.setIcon(glyph_icon("download", theme.ON_SECONDARY_CONTAINER))
        import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        import_btn.clicked.connect(self._import_pick)
        h.addWidget(create_btn)
        h.addWidget(export_btn)
        h.addWidget(import_btn)
        h.addStretch(1)
        vbox.addWidget(btn_row)

        self.backup_frame = RoundedListFrame(theme.SURFACE_CONTAINER_LOW)
        vbox.addWidget(self.backup_frame, 1)

    def _refresh_backups(self) -> None:
        frame = self.backup_frame
        frame.clear_rows()
        items = app_core.list_backups()
        if not items:
            frame.add_stretch_row(
                EmptyState("history", "暂无备份", "点击“导出当前变量”创建第一个备份")
            )
            return
        for item in items:
            frame.add_row(BackupRow(item, self._restore_backup_item, self._delete_backup))

    def _open_backup_folder(self) -> None:
        app_core.ensure_dirs()
        try:
            os.startfile(str(app_core.BACKUPS_DIR))
        except OSError as exc:
            self.toast(f"无法打开文件夹：{exc}", error=True)

    def _create_backup_dialog(self) -> None:
        """手动创建备份：可填写描述，与原生工具的“创建备份”一致。"""
        edit = QLineEdit()
        edit.setObjectName("dialogInput")
        edit.setPlaceholderText("备份描述（可选），如：改 PATH 前")

        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.addWidget(edit)

        dialog = StyledDialog(self, "创建备份", content, actions=[])
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("textBtn")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(dialog.reject)
        go_btn = QPushButton("创建")
        go_btn.setObjectName("filledBtn")
        go_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        def do_create() -> None:
            dialog.accept()
            try:
                path = app_core.create_backup(edit.text().strip())
            except OSError as exc:
                self.toast(f"创建备份失败：{exc}", error=True)
                return
            self._refresh_backups()
            self.toast(f"已创建备份（{len(app_core.load_backup(path))} 个变量）")

        go_btn.clicked.connect(do_create)
        edit.returnPressed.connect(do_create)
        dialog.actions_row(cancel_btn, go_btn)
        dialog.resize(max(440, dialog.sizeHint().width()), dialog.sizeHint().height())
        dialog.exec()

    def _export_dialog(self) -> None:
        choice = {"scope": "all"}
        content = QWidget()
        box = QVBoxLayout(content)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(8)

        def make_radio(label: str, token: str, enabled: bool = True) -> ScopeRadio:
            r = ScopeRadio(label, checked=token == "all", toggleable=False, enabled=enabled)

            def sync(checked: bool) -> None:
                if checked:
                    choice["scope"] = token

            r.toggled.connect(sync)
            return r

        radios = [
            make_radio("全部（用户 + 系统）", "all"),
            make_radio("仅系统变量", "system", enabled=self.admin),
            make_radio("仅用户变量", "user"),
        ]
        for i, r in enumerate(radios):
            box.addWidget(r)

        def exclusive(index: int) -> None:
            for j, other in enumerate(radios):
                if j != index:
                    other.set_checked(False)

        for i, r in enumerate(radios):
            r.toggled.connect(lambda checked, idx=i: exclusive(idx) if checked else None)

        if not self.admin:
            box.addWidget(
                self._field_label("未以管理员身份运行，系统变量不可导出", small=True)
            )

        dialog = StyledDialog(self, "导出备份", content, actions=[])

        def do_export() -> None:
            pool = self._export_pool(choice["scope"])
            if not pool:
                dialog.reject()
                self.toast("所选范围为空，未导出", error=True)
                return
            suggested = f"env_backup_{datetime.now():%Y%m%d_%H%M%S}.json"
            path, _ = QFileDialog.getSaveFileName(
                self, "导出备份", str(app_core.BACKUPS_DIR / suggested), "JSON (*.json)"
            )
            if not path:
                return
            dialog.reject()
            try:
                app_core.export_backup(path, pool)
            except OSError as exc:
                self.toast(f"导出失败：{exc}", error=True)
                return
            self._refresh_backups()
            self.toast(f"已导出 {len(pool)} 个变量")

        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("textBtn")
        cancel_btn.clicked.connect(dialog.reject)
        go_btn = QPushButton("导出")
        go_btn.setObjectName("filledBtn")
        go_btn.clicked.connect(do_export)
        dialog.actions_row(cancel_btn, go_btn)
        dialog.exec()

    def _export_pool(self, choice: str) -> list[app_core.Var]:
        if choice == "all":
            return (
                self._cache[app_core.SCOPE_USER] + self._cache[app_core.SCOPE_SYSTEM]
            )
        if choice == "user":
            return list(self._cache[app_core.SCOPE_USER])
        return list(self._cache[app_core.SCOPE_SYSTEM])

    def _import_pick(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择备份文件", "", "JSON (*.json)")
        if not path:
            return
        try:
            vars_ = app_core.load_backup(path)
        except (OSError, ValueError) as exc:
            self.toast(f"读取备份失败：{exc}", error=True)
            return
        if not vars_:
            self.toast("备份中没有有效的变量", error=True)
            return
        self._confirm_restore(vars_)

    def _restore_backup_item(self, item: dict) -> None:
        try:
            vars_ = app_core.load_backup(item["path"])
        except (OSError, ValueError) as exc:
            self.toast(f"读取备份失败：{exc}", error=True)
            return
        if not vars_:
            self.toast("备份中没有有效的变量", error=True)
            return
        self._confirm_restore(vars_)

    def _confirm_restore(self, vars_: list[app_core.Var]) -> None:
        n_user = sum(1 for v in vars_ if v.scope == app_core.SCOPE_USER)
        n_sys = sum(1 for v in vars_ if v.scope == app_core.SCOPE_SYSTEM)
        hint = (
            "同名变量会被覆盖为备份中的值。可取消勾选，仅恢复所选条目。"
            if self.admin
            else "当前无管理员权限，系统变量将被跳过；可取消勾选，仅恢复所选条目。"
        )

        content = QWidget()
        box = QVBoxLayout(content)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(8)

        h = QLabel(hint)
        h.setStyleSheet(
            f"font-size: 13px; color: {theme.ON_SURFACE_VARIANT}; background: transparent;"
        )
        h.setWordWrap(True)
        box.addWidget(h)

        # 工具栏：全选 / 全不选 / 已选计数
        bar = QWidget()
        bh = QHBoxLayout(bar)
        bh.setContentsMargins(0, 0, 0, 0)
        bh.setSpacing(4)
        all_btn = QPushButton("全选")
        all_btn.setObjectName("textBtn")
        all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        none_btn = QPushButton("全不选")
        none_btn.setObjectName("textBtn")
        none_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        count_label = QLabel("")
        count_label.setStyleSheet(
            f"font-size: 13px; font-weight: 500; color: {theme.PRIMARY}; background: transparent;"
        )
        bh.addWidget(all_btn)
        bh.addWidget(none_btn)
        bh.addStretch(1)
        bh.addWidget(count_label)
        box.addWidget(bar)

        # 变量清单（按 范围 分组，支持勾选部分恢复）
        list_frame = QFrame()
        list_frame.setStyleSheet(
            f"QFrame {{ background: {theme.SURFACE_CONTAINER_LOW};"
            f" border: 1px solid {theme.OUTLINE_VARIANT}; border-radius: 14px; }}"
        )
        list_l = QVBoxLayout(list_frame)
        list_l.setContentsMargins(4, 4, 4, 4)
        scroll = QScrollArea(list_frame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        host = QWidget()
        host_v = QVBoxLayout(host)
        host_v.setContentsMargins(4, 4, 4, 4)
        host_v.setSpacing(2)

        rows: list[SelectVarRow] = []

        def refresh_count() -> None:
            n = sum(1 for r in rows if r.checked)
            count_label.setText(f"已选 {n} / {len(rows)}")
            go_btn.setText(f"恢复所选 {n} 项" if n != len(rows) else "全部恢复")
            go_btn.setEnabled(n > 0)

        def add_group(label: str, items: list[app_core.Var]) -> None:
            if not items:
                return
            header = QLabel(f"{label}（{len(items)}）")
            header.setStyleSheet(
                f"font-size: 12px; font-weight: 500; color: {theme.OUTLINE};"
                "background: transparent;"
            )
            header.setContentsMargins(8, 6, 8, 2)
            host_v.addWidget(header)
            for v in items:
                allowed = self.admin or v.scope == app_core.SCOPE_USER
                row = SelectVarRow(
                    v.scope,
                    v.name,
                    v.value,
                    checked=allowed,
                )
                if not allowed:
                    row.setEnabled(False)
                    row.setToolTip("无管理员权限，系统变量将被跳过")
                row.on_toggle = refresh_count
                rows.append(row)
                host_v.addWidget(row)
            host_v.addSpacing(6)

        add_group("系统变量", [v for v in vars_ if v.scope == app_core.SCOPE_SYSTEM])
        add_group("用户变量", [v for v in vars_ if v.scope == app_core.SCOPE_USER])
        host_v.addStretch(1)

        scroll.setWidget(host)
        list_l.addWidget(scroll)
        list_frame.setFixedHeight(300)
        box.addWidget(list_frame, 1)

        dialog = StyledDialog(self, "恢复备份", content, actions=[])

        def select_all(checked: bool) -> None:
            for r in rows:
                if r.isEnabled():
                    r.set_checked(checked)
            refresh_count()

        all_btn.clicked.connect(lambda: select_all(True))
        none_btn.clicked.connect(lambda: select_all(False))

        def do_restore() -> None:
            selected = [v for v in vars_ if _lookup_checked(rows, v)]
            dialog.accept()
            if not selected:
                return
            self._apply_restore(selected)

        def _lookup_checked(rs: list[SelectVarRow], v: app_core.Var) -> bool:
            for r in rs:
                if r.var_scope == v.scope and r.var_name == v.name:
                    return r.checked
            return False

        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("textBtn")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(dialog.reject)
        go_btn = QPushButton("全部恢复")
        go_btn.setObjectName("filledBtn")
        go_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        go_btn.clicked.connect(do_restore)
        dialog.actions_row(cancel_btn, go_btn)
        refresh_count()
        dialog.resize(max(560, self.width() // 2), dialog.sizeHint().height())
        dialog.exec()

    def _apply_restore(self, vars_: list[app_core.Var]) -> None:
        admin = self.admin
        created = updated = skipped = 0
        failed: list[str] = []
        for v in vars_:
            if v.scope == app_core.SCOPE_SYSTEM and not admin:
                skipped += 1
                continue
            existing = next(
                (
                    x
                    for x in self._cache[v.scope]
                    if x.name.casefold() == v.name.casefold()
                ),
                None,
            )
            if existing and existing.value == v.value and existing.kind == v.kind:
                skipped += 1
                continue
            try:
                app_core.set_var(v.scope, v.name, v.value, kind=v.kind)
            except RuntimeError:
                skipped += 1
                failed.append(f"{'系统' if v.scope == app_core.SCOPE_SYSTEM else '用户'}：{v.name}")
                continue
            if existing:
                updated += 1
            else:
                created += 1
        self._after_mutation()
        msg = f"恢复完成：新建 {created}，更新 {updated}"
        if skipped:
            msg += f"，跳过 {skipped}"
        if failed:
            detail = "、".join(failed[:3]) + ("…" if len(failed) > 3 else "")
            self.toast(f"{msg}；失败：{detail}", error=True, duration_ms=4000)
        else:
            self.toast(msg)

    def _confirm_dialog(
        self,
        title: str,
        text: str,
        ok_label: str = "确定",
        danger: bool = False,
    ) -> bool:
        """通用确认对话框：返回 True 表示用户确认执行。

        danger=True 时确认按钮使用错误色，用于删除类操作。
        """
        content = self._field_label(text, small=True)
        dialog = StyledDialog(self, title, content, actions=[])
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("textBtn")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(dialog.reject)
        ok_btn = QPushButton(ok_label)
        ok_btn.setObjectName("filledBtn")
        ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if danger:
            ok_btn.setStyleSheet(
                f"QPushButton#filledBtn {{ background: {theme.ERROR_CONTAINER}; }}"
            )
        ok_btn.clicked.connect(dialog.accept)
        dialog.actions_row(cancel_btn, ok_btn)
        dialog.resize(max(420, dialog.sizeHint().width()), dialog.sizeHint().height())
        return bool(dialog.exec())

    def _delete_backup(self, item: dict) -> None:
        """删除备份：确认对话框防误删；删除后 Snackbar 提供撤销（自动清理不经过此流程）。"""
        if not self._confirm_dialog(
            "删除备份", f"确定删除备份“{item['name']}”吗？", ok_label="删除", danger=True
        ):
            return
        path = item["path"]
        try:
            raw = app_core.read_backup_raw(path)
        except (OSError, ValueError):
            raw = None
        try:
            app_core.delete_backup(path)
        except OSError as exc:
            self.toast(f"删除失败：{exc}", error=True)
            return
        self._refresh_backups()

        def undo() -> None:
            if raw is None:
                self.toast("无法撤销：原文件内容未能读取", error=True)
                return
            try:
                app_core.write_backup_raw(path, raw)
            except OSError as exc:
                self.toast(f"撤销失败：{exc}", error=True)
                return
            self._refresh_backups()
            self.toast("已撤销删除，备份已恢复")

        self.toast(f"已删除 {item['name']}", action_label="撤销", on_action=undo)

    # ------------------------------------------------------------------
    # 设置页
    # ------------------------------------------------------------------

    def _build_settings(self) -> None:
        page = QFrame(self.stack)
        page.setStyleSheet(f"QFrame {{ background: {theme.SURFACE}; }}")
        self.stack.add_page("settings", page)

        vbox = QVBoxLayout(page)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)
        vbox.addWidget(AppBar("设置"))

        scroll = QScrollArea(page)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        host = QWidget(scroll)
        host_v = QVBoxLayout(host)
        host_v.setContentsMargins(16, 4, 16, 16)
        host_v.setSpacing(12)

        self.broadcast_switch = Switch(bool(self.settings.get("broadcast", True)))
        self.broadcast_switch.toggled.connect(self._on_broadcast_toggle)
        host_v.addWidget(
            section_card(
                "通用",
                [
                    settings_row(
                        "campaign",
                        "修改后广播系统设置变更",
                        "让资源管理器与新终端立即读取最新环境变量",
                        trailing=self.broadcast_switch,
                    )
                ],
            )
        )

        if self.admin:
            chip = QLabel("已以管理员身份运行")
            chip.setStyleSheet(
                f"font-size: 12px; color: {theme.ON_SURFACE_VARIANT};"
                f"background: {theme.SURFACE_CONTAINER};"
                "border-radius: 8px; padding: 6px 10px;"
            )
        else:
            chip = QPushButton(" 以管理员身份重启")
            chip.setObjectName("tonalBtn")
            chip.setIcon(glyph_icon("restart_alt", theme.ON_SECONDARY_CONTAINER))
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            chip.clicked.connect(self._restart_as_admin)
        host_v.addWidget(
            section_card(
                "权限",
                [
                    settings_row(
                        "security",
                        "系统变量写入权限",
                        "以管理员身份运行后可新建、修改、删除系统变量",
                        trailing=chip,
                    )
                ],
            )
        )

        data_row = settings_row(
            "folder_open",
            "打开数据文件夹",
            str(app_core.APP_DIR),
        )
        data_click = ClickableRow(radius=14, hover_color=theme.SURFACE_CONTAINER_HIGH)
        lay = QVBoxLayout(data_click)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(data_row)
        data_click.clicked.connect(self._open_backup_folder)
        host_v.addWidget(section_card("数据", [data_click]))

        host_v.addWidget(
            section_card(
                "关于",
                [
                    settings_row(
                        "info_outline",
                        f"变量管理器 {APP_VERSION}",
                        "Material 3 深色模式 · 环境变量直接写入系统注册表，备份保存在本机",
                    )
                ],
            )
        )
        host_v.addStretch(1)

        scroll.setWidget(host)
        vbox.addWidget(scroll, 1)

    def _on_broadcast_toggle(self, checked: bool) -> None:
        self.settings["broadcast"] = bool(checked)
        try:
            app_core.save_settings(self.settings)
        except OSError as exc:
            self.toast(f"保存设置失败：{exc}", error=True)
            self.broadcast_switch.set_checked(not checked)

    def _restart_as_admin(self) -> None:
        if self.admin:
            self.toast("当前已是管理员身份")
            return
        script = os.path.abspath(sys.argv[0])
        rc = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, f'"{script}"', None, 1
        )
        if rc > 32:
            self.close()
        else:
            self.toast("未能启动管理员实例（可能已取消授权）", error=True)

    # ------------------------------------------------------------------
    # 布局
    # ------------------------------------------------------------------

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self.snackbar.reposition()
