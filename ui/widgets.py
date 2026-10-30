"""自定义控件：图标、涟漪行、单选圆点、开关、搜索栏、消息条、应用栏、对话框等。"""

from __future__ import annotations

import os

from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPointF,
    Property,
    QPropertyAnimation,
    QRectF,
    QSize,
    QTimer,
    QVariantAnimation,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ui import theme
from ui.theme import glyph

# ---------------------------------------------------------------------------
# 图标
# ---------------------------------------------------------------------------


class Icon(QLabel):
    def __init__(
        self,
        name: str,
        size: int = 24,
        color: str = theme.ON_SURFACE_VARIANT,
        style: str = "round",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._name = name
        self._style = style
        font = theme.icon_font(style)
        font.setPixelSize(size)
        self.setFont(font)
        self.setText(glyph(name, style))
        self.set_color(color)
        self.setFixedSize(size + 4, size + 4)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def set_color(self, color: str) -> None:
        self.setStyleSheet(f"color: {color}; background: transparent;")

    def set_icon_name(self, name: str, style: str | None = None) -> None:
        self._name = name
        if style:
            self._style = style
            font = self.font()
            font.setFamily(theme.icon_font(style).family())
            self.setFont(font)
        self.setText(glyph(name, self._style))


class IconButton(QPushButton):
    """48dp 圆形图标按钮。"""

    def __init__(
        self,
        name: str,
        tooltip: str = "",
        color: str = theme.ON_SURFACE_VARIANT,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setText(glyph(name))
        self.setObjectName("iconBtn")
        self.setFixedSize(48, 48)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        if color != theme.ON_SURFACE_VARIANT:
            self.setStyleSheet(f"color: {color};")
        if tooltip:
            self.setToolTip(tooltip)


# ---------------------------------------------------------------------------
# 涟漪可点击行
# ---------------------------------------------------------------------------


class ClickableRow(QWidget):
    """带涟漪与悬停反馈的可点击容器行。"""

    clicked = Signal()

    def __init__(
        self,
        radius: int = 14,
        hover_color: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._radius = radius
        self._hover = False
        self._press_pos: QPointF | None = None
        self._ripple = 0.0
        self._hover_color = hover_color or theme.SURFACE_CONTAINER_HIGH
        self._anim: QVariantAnimation | None = None
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

    # -- 涟漪 ------------------------------------------------------------

    def _start_ripple(self, pos: QPointF) -> None:
        self._press_pos = pos
        self._anim = QVariantAnimation(self)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setDuration(420)
        self._anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self._anim.valueChanged.connect(self._on_ripple_tick)
        self._anim.finished.connect(self._on_ripple_done)
        self._anim.start()

    def _on_ripple_tick(self, value: float) -> None:
        self._ripple = float(value)
        self.update()

    def _on_ripple_done(self) -> None:
        self._press_pos = None
        self._ripple = 0.0
        self.update()

    # -- 事件 ------------------------------------------------------------

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._start_ripple(event.position())
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self.rect().contains(event.position().toPoint())
        ):
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), self._radius, self._radius)
        painter.setClipPath(path)
        if self._hover:
            painter.fillRect(self.rect(), QColor(self._hover_color))
        if self._press_pos is not None:
            radius = (
                max(
                    self.width(),
                    self.height(),
                    (self._press_pos - QPointF(self.width(), self.height())).manhattanLength(),
                )
                * 1.15
            )
            color = theme.with_alpha(theme.PRIMARY, int(70 * (1 - self._ripple)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawEllipse(self._press_pos, radius * self._ripple, radius * self._ripple)
        painter.end()


# ---------------------------------------------------------------------------
# 单选圆点（20dp，选中 primary 圆环 + 圆点；可独立开关或排他组）
# ---------------------------------------------------------------------------


class ScopeRadio(QWidget):
    toggled = Signal(bool)

    def __init__(
        self,
        label: str,
        checked: bool = False,
        toggleable: bool = True,
        enabled: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._label = label
        self._checked = checked
        self._toggleable = toggleable
        self._hover = False
        self.setEnabled(enabled)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        self._dot = _RadioDot(self)
        self._dot.setFixedSize(20, 20)
        self._text = QLabel(label, self)
        self._text.setStyleSheet(
            f"color: {theme.ON_SURFACE if enabled else theme.OUTLINE};"
            "font-size: 16px; background: transparent;"
        )
        layout.addWidget(self._dot)
        layout.addWidget(self._text)

    def is_checked(self) -> bool:
        return self._checked

    def set_checked(self, value: bool) -> None:
        if value != self._checked:
            self._checked = value
            self._dot.set_checked(value)
            self.toggled.emit(value)
        else:
            self._dot.set_checked(value)
        self.update()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self.isEnabled():
            if self._toggleable or not self._checked:
                self.set_checked(not self._checked)
        super().mousePressEvent(event)

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        if self._hover and self.isEnabled():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(theme.with_alpha(theme.PRIMARY, 24))
            painter.drawEllipse(QRectF(self.rect()).adjusted(1, 1, -1, -1))
            painter.end()


class _RadioDot(QWidget):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._checked = parent._checked  # noqa: SLF001
        self._anim: QPropertyAnimation | None = None
        self._dot_scale = 1.0 if self._checked else 0.0
        self._parent_radio = parent

    def set_checked(self, value: bool) -> None:
        self._checked = value
        self._animate()

    def _animate(self) -> None:
        target = 1.0 if self._checked else 0.0
        self._anim = QPropertyAnimation(self, b"dotScale", self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.setStartValue(self._dot_scale)
        self._anim.setEndValue(target)
        self._anim.start()

    # 供 QPropertyAnimation 使用的自定义属性
    def _get_dot_scale(self) -> float:
        return self._dot_scale

    def _set_dot_scale(self, value: float) -> None:
        self._dot_scale = value
        self.update()

    dotScale = Property(float, _get_dot_scale, _set_dot_scale)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(0, 0, 20, 20)
        if self._checked:
            pen = QPen(QColor(theme.PRIMARY), 2)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(rect.adjusted(1, 1, -1, -1))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(theme.PRIMARY))
            r = 5.0 * self._dot_scale
            if r > 0.1:
                painter.drawEllipse(rect.adjusted(10 - r, 10 - r, -10 + r, -10 + r))
        else:
            painter.setPen(QPen(QColor(theme.ON_SURFACE_VARIANT), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(rect.adjusted(1, 1, -1, -1))
        painter.end()


# ---------------------------------------------------------------------------
# M3 开关
# ---------------------------------------------------------------------------


class Switch(QWidget):
    toggled = Signal(bool)

    _TRACK_W, _TRACK_H = 52, 32

    def __init__(self, checked: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._checked = checked
        self.setFixedSize(self._TRACK_W, self._TRACK_H)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._thumb = QWidget(self)
        self._thumb.setFixedSize(24, 24)
        self._thumb.setVisible(True)
        self._position_thumb(animate=False)

    def is_checked(self) -> bool:
        return self._checked

    def _thumb_x(self) -> int:
        return (self._TRACK_W - 26) if self._checked else 2

    def _position_thumb(self, animate: bool = True) -> None:
        x = self._thumb_x()
        y = (self._TRACK_H - self._thumb.height()) // 2
        if animate:
            anim = QPropertyAnimation(self._thumb, b"pos", self)
            anim.setDuration(200)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.setEndValue(QPoint(x, y))
            anim.start(anim.DeleteWhenStopped)
        else:
            self._thumb.move(x, y)
        self._thumb.setStyleSheet(
            f"background: {theme.ON_PRIMARY if self._checked else theme.OUTLINE};"
            "border-radius: 12px;"
        )

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._checked = not self._checked
            self._position_thumb()
            self.update()
            self.toggled.emit(self._checked)
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        track_color = theme.PRIMARY if self._checked else theme.SURFACE_CONTAINER_HIGHEST
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(track_color))
        painter.drawRoundedRect(
            QRectF(0, 0, self._TRACK_W, self._TRACK_H), 16, 16
        )
        painter.end()


# ---------------------------------------------------------------------------
# 搜索栏（56dp、全圆角、左搜索图标、右清空）
# ---------------------------------------------------------------------------


class SearchField(QFrame):
    text_changed = Signal(str)

    def __init__(self, placeholder: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(56)
        self.setStyleSheet(
            f"""
            SearchField {{
                background: {theme.SURFACE_CONTAINER_HIGH};
                border: 1px solid {theme.OUTLINE};
                border-radius: 28px;
            }}
            """
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 8, 4)
        layout.setSpacing(4)

        self._leading = Icon("search", 24, theme.ON_SURFACE_VARIANT)
        layout.addWidget(self._leading)

        self.edit = QLineEdit(self)
        self.edit.setPlaceholderText(placeholder)
        self.edit.setStyleSheet(
            "QLineEdit { background: transparent; border: none; font-size: 16px;"
            f" color: {theme.ON_SURFACE}; }}"
        )
        self.edit.setClearButtonEnabled(False)
        layout.addWidget(self.edit, 1)

        self.clear_btn = IconButton("close", "清空")
        self.clear_btn.setFixedSize(36, 36)
        self.clear_btn.setVisible(False)
        self.clear_btn.clicked.connect(self.clear)
        layout.addWidget(self.clear_btn)

        self.edit.textChanged.connect(self._on_text_changed)

    def _on_text_changed(self, text: str) -> None:
        self.clear_btn.setVisible(bool(text))
        self.text_changed.emit(text)

    def clear(self) -> None:
        self.edit.clear()

    def text(self) -> str:
        return self.edit.text()


# ---------------------------------------------------------------------------
# 消息条（48dp、圆角 8、inverseSurface，底部 16dp，数秒后消失）
# ---------------------------------------------------------------------------


class Snackbar(QFrame):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setFixedHeight(48)
        self.setVisible(False)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fade_out)

        self._effect = QGraphicsOpacityEffect(self)
        self._effect.setOpacity(0.0)
        self.setGraphicsEffect(self._effect)
        self._anim: QPropertyAnimation | None = None

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(16, 0, 8, 0)
        self._layout.setSpacing(8)
        self._label = QLabel(self)
        self._label.setStyleSheet("font-size: 14px; background: transparent;")
        self._layout.addWidget(self._label, 1)

    def show_toast(
        self,
        text: str,
        *,
        action_label: str | None = None,
        on_action=None,
        error: bool = False,
        duration_ms: int = 2000,
    ) -> None:
        bg = theme.ERROR_CONTAINER if error else theme.INVERSE_SURFACE
        fg = theme.ON_ERROR_CONTAINER if error else theme.INVERSE_ON_SURFACE
        self.setStyleSheet(
            f"Snackbar {{ background: {bg}; border-radius: 8px; }}"
            f"QLabel {{ color: {fg}; }}"
        )
        self._label.setText(text)

        # 重建动作按钮
        old = self._layout.takeAt(1)
        if old is not None and old.widget() is not None:
            old.widget().deleteLater()
        if action_label and on_action is not None:
            btn = QPushButton(action_label, self)
            btn.setObjectName("snackAction")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.clicked.connect(lambda: (self._fade_out(), on_action()))
            self._layout.addWidget(btn)

        self.reposition()
        self.setVisible(True)
        self.raise_()
        self._animate_opacity(0.0, 1.0, 160)
        self._timer.start(duration_ms)

    def reposition(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        self.adjustSize()
        width = min(max(self.sizeHint().width(), 320), parent.width() - 32)
        self.resize(width, 48)
        x = (parent.width() - width) // 2
        y = parent.height() - 48 - 16
        self.move(x, y)

    def _animate_opacity(self, start: float, end: float, duration: int) -> None:
        self._anim = QPropertyAnimation(self._effect, b"opacity", self)
        self._anim.setDuration(duration)
        self._anim.setStartValue(start)
        self._anim.setEndValue(end)
        self._anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    def _fade_out(self) -> None:
        self._timer.stop()
        self._animate_opacity(self._effect.opacity(), 0.0, 160)
        QTimer.singleShot(180, self.hide)


# ---------------------------------------------------------------------------
# 顶部应用栏（64dp、surface、titleLarge）
# ---------------------------------------------------------------------------


class AppBar(QFrame):
    def __init__(
        self,
        title: str,
        leading: QWidget | None = None,
        actions: list[QWidget] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setFixedHeight(64)
        self.setStyleSheet(f"AppBar {{ background: {theme.SURFACE}; }}")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(8)
        if leading is not None:
            layout.addWidget(leading)
        self._title = QLabel(title, self)
        self._title.setStyleSheet(
            f"font-size: 22px; font-weight: 400; color: {theme.ON_SURFACE};"
            "background: transparent;"
        )
        layout.addWidget(self._title)
        layout.addStretch(1)
        for action in actions or []:
            layout.addWidget(action)


# ---------------------------------------------------------------------------
# 空状态
# ---------------------------------------------------------------------------


class EmptyState(QWidget):
    def __init__(
        self,
        icon: str,
        title: str,
        subtitle: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(8)
        ic = Icon(icon, 44, theme.OUTLINE)
        ic.setFixedSize(48, 48)
        layout.addWidget(ic, 0, Qt.AlignmentFlag.AlignCenter)
        t = QLabel(title, self)
        t.setStyleSheet(
            f"font-size: 14px; font-weight: 500; color: {theme.ON_SURFACE_VARIANT};"
            "background: transparent;"
        )
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(t, 0, Qt.AlignmentFlag.AlignCenter)
        if subtitle:
            s = QLabel(subtitle, self)
            s.setStyleSheet(
                f"font-size: 12px; color: {theme.ON_SURFACE_VARIANT};"
                "background: transparent;"
            )
            s.setAlignment(Qt.AlignmentFlag.AlignCenter)
            s.setWordWrap(True)
            layout.addWidget(s, 0, Qt.AlignmentFlag.AlignCenter)


# ---------------------------------------------------------------------------
# 悬浮按钮（胶囊，带按下轻微缩放）
# ---------------------------------------------------------------------------


class Fab(QPushButton):
    def __init__(self, text: str, icon: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("fabBtn")
        self.setText(text)
        self.setIcon(theme.render_icon(icon, theme.ON_PRIMARY_CONTAINER))
        font = self.font()
        font.setPixelSize(15)
        font.setWeight(QFont.Weight.DemiBold)
        self.setFont(font)
        self.setFixedHeight(48)  # 与 QSS border-radius 24 匹配（半径不可超过高度一半）
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._press_anim: QPropertyAnimation | None = None
        self._base_size: tuple[int, int] | None = None

    def mousePressEvent(self, event) -> None:  # noqa: N802
        self._scale(0.96)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._scale(1.0)
        super().mouseReleaseEvent(event)

    def _scale(self, factor: float) -> None:
        if self._base_size is None:
            self._base_size = (self.width(), self.height())
        bw, bh = self._base_size
        w, h = int(bw * factor), int(bh * factor)
        self._press_anim = QPropertyAnimation(self, b"size", self)
        self._press_anim.setDuration(120)
        self._press_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._press_anim.setStartValue(self.size())
        self._press_anim.setEndValue(QSize(w, h))
        self._press_anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        # 缩放时保持中心（PySide6 的 QPoint 不可迭代解包）
        c = self.geometry().center()
        self.move(int(c.x() - w / 2), int(c.y() - h / 2))


# ---------------------------------------------------------------------------
# 圆角 28 对话框基类
# ---------------------------------------------------------------------------


class BlurOverlay(QWidget):
    """弹窗打开期间覆盖父窗口的毛玻璃遮罩：内容快照模糊 + 暗化，淡入淡出。"""

    def __init__(self, win: QWidget) -> None:
        super().__init__(win)
        self.setGeometry(win.rect())
        self._lbl = QLabel(self)
        self._lbl.setGeometry(self.rect())
        self._lbl.setScaledContents(True)
        self._lbl.setPixmap(self._bake_blur(win.grab()))

        # 整体不透明度动画（仅弹窗期间存在，弹窗关闭即销毁）
        self._fx = QGraphicsOpacityEffect(self)
        self._fx.setOpacity(0.0)
        self.setGraphicsEffect(self._fx)

        self._closing = False
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(lambda v: self._fx.setOpacity(float(v)))
        self._anim.finished.connect(self._on_fade_done)

    @staticmethod
    def _bake_blur(pix: QPixmap) -> QPixmap:
        """两段降采样回放模糊：一次烘焙成静态图，避免动画期间逐帧重算。"""
        w, h = max(1, pix.width()), max(1, pix.height())
        small = pix.scaled(
            max(1, w // 18), max(1, h // 18),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        return small.scaled(
            w, h,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    def fade_in(self) -> None:
        self._closing = False
        self.show()
        self.raise_()
        self._anim.stop()
        self._anim.setStartValue(self._fx.opacity())
        self._anim.setEndValue(1.0)
        self._anim.start()

    def fade_out(self) -> None:
        if self._closing:
            return
        self._closing = True
        self._anim.stop()
        self._anim.setStartValue(self._fx.opacity())
        self._anim.setEndValue(0.0)
        self._anim.start()

    def _on_fade_done(self) -> None:
        if not self._closing:
            return
        self.hide()
        self.setParent(None)
        self.deleteLater()

    def resizeEvent(self, event) -> None:  # noqa: N802
        self._lbl.setGeometry(self.rect())
        super().resizeEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 90))
        painter.end()


class StyledDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None,
        title: str,
        content: QWidget,
        actions: list[QPushButton],
    ) -> None:
        super().__init__(parent)
        self._blur: BlurOverlay | None = None
        self.setWindowTitle(title)
        self.setModal(True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 16)
        outer.setSpacing(16)
        title_label = QLabel(title, self)
        title_label.setStyleSheet(
            f"font-size: 22px; font-weight: 400; color: {theme.ON_SURFACE};"
            "background: transparent;"
        )
        outer.addWidget(title_label)
        outer.addWidget(content)
        if actions:
            self.actions_row(*actions)

    def actions_row(self, *buttons: QPushButton) -> None:
        """在对话框底部右侧追加一排按钮（M3 对话框动作区）。"""
        bottom = QHBoxLayout()
        bottom.setContentsMargins(0, 0, 0, 0)
        bottom.setSpacing(8)
        bottom.addStretch(1)
        for btn in buttons:
            bottom.addWidget(btn)
        self.layout().addLayout(bottom)

    # -- 弹窗背景模糊：打开时给父窗口盖毛玻璃遮罩，关闭时遮罩淡出销毁 --

    def showEvent(self, event) -> None:  # noqa: N802
        if self._blur is not None:
            self._blur.fade_in()
        else:
            parent = self.parent()
            if parent is not None and not parent.findChildren(BlurOverlay):
                # 仅首层弹窗挂遮罩；嵌套弹窗（行内编辑等）复用宿主已有遮罩，
                # 避免"模糊套模糊"的叠加渲染与销毁时序问题
                self._blur = BlurOverlay(parent)
                self._blur.fade_in()
        super().showEvent(event)

    def hideEvent(self, event) -> None:  # noqa: N802
        if self._blur is not None:
            overlay, self._blur = self._blur, None
            overlay.fade_out()
        super().hideEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(theme.OUTLINE_VARIANT), 1))
        painter.setBrush(QColor(theme.SURFACE_CONTAINER_HIGH))
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 28, 28)
        painter.end()


# ---------------------------------------------------------------------------
# 多值路径变量编辑器（表格化逐条展示，支持增删改与排序）
# ---------------------------------------------------------------------------

# 有效路径的提示色（沿用原生工具的绿/红语义）
PATH_VALID_COLOR = "#7BA07B"


class _PathRow(ClickableRow):
    """表格中的一行：序号 + 有效性图标 + 路径 + 编辑/移除。"""

    HEIGHT = 40

    def __init__(self, editor: "PathListEditor", index: int, entry: str, valid: bool) -> None:
        super().__init__(radius=10, hover_color=theme.SURFACE_CONTAINER_HIGHEST)
        self._editor = editor
        self._index = index
        self.setFixedHeight(self.HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 2, 4, 2)
        layout.setSpacing(8)

        idx = QLabel(f"{index + 1}", self)
        idx.setFixedWidth(20)
        idx.setAlignment(Qt.AlignmentFlag.AlignCenter)
        idx.setStyleSheet(
            f"font-size: 12px; color: {theme.ON_SURFACE_VARIANT}; background: transparent;"
        )
        layout.addWidget(idx)

        status = Icon("check_circle" if valid else "cancel", 18, PATH_VALID_COLOR if valid else theme.ERROR, parent=self)
        status.setFixedSize(20, 20)
        layout.addWidget(status)

        metrics = QFontMetrics(self.font())
        label = QLabel(
            metrics.elidedText(entry, Qt.TextElideMode.ElideMiddle, 380), self
        )
        label.setToolTip(entry)
        label.setStyleSheet(
            f"font-size: 14px; color: {theme.ON_SURFACE if valid else theme.ERROR};"
            "background: transparent;"
        )
        layout.addWidget(label, 1)

        edit_btn = IconButton("edit", "编辑此条目", parent=self)
        edit_btn.setFixedSize(32, 32)
        edit_btn.clicked.connect(lambda: editor.edit_entry(index))
        layout.addWidget(edit_btn)

        del_btn = IconButton("close", "移除此条目", color=theme.ERROR, parent=self)
        del_btn.setFixedSize(32, 32)
        del_btn.clicked.connect(lambda: editor.remove_entry(index))
        layout.addWidget(del_btn)

        self.clicked.connect(lambda: editor.open_entry(index))

    def paintEvent(self, event) -> None:  # noqa: N802
        editor = self._editor
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(self.rect()), self._radius, self._radius)
        painter.setClipPath(clip)
        if self._index % 2 == 1:  # 隔行底色，表格观感
            painter.fillRect(self.rect(), theme.with_alpha(theme.ON_SURFACE, 8))
        if editor.is_selected(self._index) and self.isEnabled():
            painter.fillRect(self.rect(), theme.with_alpha(theme.PRIMARY, 42))
        painter.end()
        super().paintEvent(event)


class PathListEditor(QWidget):
    """多值路径变量编辑器。

    与原生工具的多路径编辑一致：逐条展示、添加/编辑/删除/上移/下移/浏览
    文件夹，无效条目标红。保存时用 os.pathsep 合并回一个变量值。
    """

    VISIBLE_ROWS = 5

    def __init__(
        self,
        entries=(),
        checker=None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._entries: list[str] = [str(e) for e in entries]
        self._checker = checker or (lambda p: True)
        self._selected = -1
        # 可选回调：点击条目请求打开对应文件夹（宿主负责打开与"不存在"提示）
        self.on_open_entry = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        # 表头：序号 / 状态与路径 / 操作
        header = QWidget(self)
        hh = QHBoxLayout(header)
        hh.setContentsMargins(12, 0, 4, 0)
        hh.setSpacing(8)
        col_no = QLabel("#", header)
        col_no.setFixedWidth(20)
        col_no.setAlignment(Qt.AlignmentFlag.AlignCenter)
        col_no.setStyleSheet(
            f"font-size: 12px; color: {theme.OUTLINE}; background: transparent;"
        )
        col_path = QLabel("路径条目", header)
        col_path.setStyleSheet(
            f"font-size: 12px; font-weight: 500; color: {theme.OUTLINE};"
            "background: transparent;"
        )
        col_op = QLabel("操作", header)
        col_op.setStyleSheet(
            f"font-size: 12px; color: {theme.OUTLINE}; background: transparent;"
        )
        hh.addWidget(col_no)
        hh.addWidget(col_path, 1)
        hh.addWidget(col_op)
        root.addWidget(header)

        # 行区域（圆角容器 + 滚动）
        self._list_frame = QFrame(self)
        self._list_frame.setObjectName("pathListFrame")
        self._list_frame.setStyleSheet(
            f"QFrame#pathListFrame {{ background: {theme.SURFACE_CONTAINER_LOW};"
            f" border: 1px solid {theme.OUTLINE_VARIANT}; border-radius: 14px; }}"
        )
        frame_l = QVBoxLayout(self._list_frame)
        frame_l.setContentsMargins(4, 4, 4, 4)
        self._scroll = QScrollArea(self._list_frame)
        self._scroll.setWidgetResizable(True)
        self._rows_host = QWidget()
        self._rows_lay = QVBoxLayout(self._rows_host)
        self._rows_lay.setContentsMargins(0, 0, 0, 0)
        self._rows_lay.setSpacing(2)
        self._scroll.setWidget(self._rows_host)
        frame_l.addWidget(self._scroll)
        self._list_frame.setFixedHeight(
            self.VISIBLE_ROWS * _PathRow.HEIGHT + 16
        )
        root.addWidget(self._list_frame)

        # 工具栏：添加 / 浏览 | 上移 / 下移
        bar = QWidget(self)
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(4, 0, 4, 0)
        bl.setSpacing(4)

        add_btn = QPushButton("添加路径", bar)
        add_btn.setObjectName("textBtn")
        add_btn.setIcon(theme.render_icon("add", theme.PRIMARY))
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.clicked.connect(self.add_entry)
        bl.addWidget(add_btn)

        browse_btn = QPushButton("浏览文件夹", bar)
        browse_btn.setObjectName("textBtn")
        browse_btn.setIcon(theme.render_icon("folder_open", theme.PRIMARY))
        browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_btn.clicked.connect(self.browse_folder)
        bl.addWidget(browse_btn)

        bl.addStretch(1)

        self._up_btn = IconButton("arrow_upward", "上移选中条目", parent=bar)
        self._up_btn.clicked.connect(lambda: self.move_entry(-1))
        bl.addWidget(self._up_btn)

        self._down_btn = IconButton("arrow_downward", "下移选中条目", parent=bar)
        self._down_btn.clicked.connect(lambda: self.move_entry(1))
        bl.addWidget(self._down_btn)

        root.addWidget(bar)

        self._rebuild()

    # -- 数据 ------------------------------------------------------------

    def set_entries(self, entries) -> None:
        self._entries = [str(e) for e in entries]
        self._selected = -1
        self._rebuild()

    def entries(self) -> list[str]:
        return list(self._entries)

    def value(self) -> str:
        """合并为一个变量值（os.pathsep 连接）。"""
        return os.pathsep.join(self._entries)

    def count(self) -> int:
        return len(self._entries)

    def is_selected(self, index: int) -> bool:
        return index == self._selected

    def select_row(self, index: int) -> None:
        self._selected = index if 0 <= index < len(self._entries) else -1
        self._refresh_selection()

    def open_entry(self, index: int) -> None:
        """点击条目：选中并请求打开对应文件夹（由宿主执行与提示）。"""
        self.select_row(index)
        if self.on_open_entry is None:
            return
        entry = self._entries[index].strip() if 0 <= index < len(self._entries) else ""
        if entry:
            self.on_open_entry(entry)

    # -- 行为 ------------------------------------------------------------

    def add_entry(self) -> None:
        if not self.isEnabled():
            return
        text = self._prompt_entry("添加路径", "")
        if text is None:
            return
        self._entries.append(text)
        self._selected = len(self._entries) - 1
        self._rebuild()

    def edit_entry(self, index: int) -> None:
        if not self.isEnabled() or not (0 <= index < len(self._entries)):
            return
        text = self._prompt_entry("编辑路径", self._entries[index])
        if text is None:
            return
        self._entries[index] = text
        self._selected = index
        self._rebuild()

    def remove_entry(self, index: int) -> None:
        if not self.isEnabled() or not (0 <= index < len(self._entries)):
            return
        del self._entries[index]
        self._selected = min(self._selected, len(self._entries) - 1)
        self._rebuild()

    def move_entry(self, delta: int) -> None:
        if not self.isEnabled():
            return
        i = self._selected
        j = i + delta
        if not (0 <= i < len(self._entries)) or not (0 <= j < len(self._entries)):
            return
        self._entries[i], self._entries[j] = self._entries[j], self._entries[i]
        self._selected = j
        self._rebuild()

    def browse_folder(self) -> None:
        if not self.isEnabled():
            return
        folder = QFileDialog.getExistingDirectory(self.window(), "选择文件夹")
        if not folder:
            return
        if 0 <= self._selected < len(self._entries):
            self._entries[self._selected] = folder
        else:
            self._entries.append(folder)
            self._selected = len(self._entries) - 1
        self._rebuild()

    def _prompt_entry(self, title: str, initial: str) -> str | None:
        """弹出行内编辑框，确认返回路径文本，取消返回 None。"""
        edit = QLineEdit(initial)
        edit.setObjectName("dialogInput")
        edit.setPlaceholderText("输入路径，如 C:\\Program Files\\App")

        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.addWidget(edit)

        dlg = StyledDialog(self.window(), title, content, actions=[])
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("textBtn")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(dlg.reject)
        ok_btn = QPushButton("保存")
        ok_btn.setObjectName("filledBtn")
        ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        def accept() -> None:
            if not edit.text().strip():
                edit.setStyleSheet(
                    f"QLineEdit#dialogInput {{ border: 1px solid {theme.ERROR}; }}"
                )
                return
            dlg.accept()

        ok_btn.clicked.connect(accept)
        edit.returnPressed.connect(accept)
        dlg.actions_row(cancel_btn, ok_btn)
        dlg.resize(max(440, dlg.sizeHint().width()), dlg.sizeHint().height())
        if dlg.exec():
            return edit.text().strip()
        return None

    # -- 渲染 ------------------------------------------------------------

    def _rebuild(self) -> None:
        while self._rows_lay.count():
            item = self._rows_lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.hide()
                w.setParent(None)  # 立即脱离绘制层级，避免 deleteLater 延迟造成重影
                w.deleteLater()
        if not self._entries:
            hint = QLabel("暂无条目，点击下方“添加路径”开始", self._rows_host)
            hint.setFixedHeight(_PathRow.HEIGHT)
            hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hint.setStyleSheet(
                f"font-size: 13px; color: {theme.OUTLINE}; background: transparent;"
            )
            self._rows_lay.addWidget(hint)
            self._rows_lay.addStretch(1)
        for i, entry in enumerate(self._entries):
            row = _PathRow(self, i, entry, bool(self._checker(entry)))
            self._rows_lay.addWidget(row)
        self._rows_lay.addStretch(1)
        self._refresh_selection()

    def _refresh_selection(self) -> None:
        n = len(self._entries)
        has = 0 <= self._selected < n
        self._up_btn.setEnabled(self.isEnabled() and has and self._selected > 0)
        self._down_btn.setEnabled(
            self.isEnabled() and has and self._selected < n - 1
        )
        for i in range(self._rows_lay.count()):
            w = self._rows_lay.itemAt(i).widget()
            if isinstance(w, _PathRow):
                w.update()


class SelectVarRow(ClickableRow):
    """部分恢复清单中的一行：勾选框 + 范围图标 + 变量名 + 值预览。"""

    HEIGHT = 38

    def __init__(
        self,
        scope: str,
        name: str,
        value: str,
        checked: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(radius=10, hover_color=theme.SURFACE_CONTAINER_HIGHEST, parent=parent)
        self._scope = scope
        self._name = name
        self._checked = checked
        self.on_toggle = None  # 可选回调：勾选状态变化后调用
        self.setFixedHeight(self.HEIGHT)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 2, 8, 2)
        layout.setSpacing(8)

        self._check = Icon(
            "check_box" if checked else "check_box_outline_blank",
            20,
            theme.PRIMARY if checked else theme.OUTLINE,
            parent=self,
        )
        self._check.setFixedSize(22, 22)
        layout.addWidget(self._check)

        scope_icon = "dns" if scope == "system" else "person"
        layout.addWidget(Icon(scope_icon, 18, theme.ON_SURFACE_VARIANT, parent=self))

        name_label = QLabel(name, self)
        name_label.setStyleSheet(
            f"font-size: 14px; font-weight: 500; color: {theme.ON_SURFACE};"
            "background: transparent;"
        )
        layout.addWidget(name_label)

        metrics = QFontMetrics(self.font())
        preview = QLabel(metrics.elidedText(value or "（空值）", Qt.TextElideMode.ElideMiddle, 300), self)
        preview.setStyleSheet(
            f"font-size: 12px; color: {theme.ON_SURFACE_VARIANT}; background: transparent;"
        )
        layout.addWidget(preview, 1)

        self.clicked.connect(self.toggle)

    @property
    def checked(self) -> bool:
        return self._checked

    @property
    def var_scope(self) -> str:
        return self._scope

    @property
    def var_name(self) -> str:
        return self._name

    def set_checked(self, checked: bool) -> None:
        self._checked = checked
        self._check.set_icon_name(
            "check_box" if checked else "check_box_outline_blank"
        )
        self._check.set_color(theme.PRIMARY if checked else theme.OUTLINE)

    def toggle(self) -> None:
        if self.isEnabled():
            self.set_checked(not self._checked)
            if self.on_toggle is not None:
                self.on_toggle()
