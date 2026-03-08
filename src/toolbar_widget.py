"""Floating pill-shaped toolbar that overlays the treemap canvas."""
from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt, pyqtSignal
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
)
from PyQt6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from src.styles import (
    BORDER_BRIGHT,
    CYAN,
    SURFACE,
    TEXT,
    TEXT_DIM,
    TEXT_MID,
    load_fonts,
)

_PILL_H = 52
_PILL_W = 600
_RADIUS = 26

_BTN_QSS = f"""
    QPushButton {{
        background: transparent;
        color: {TEXT_MID};
        border: none;
        border-radius: 7px;
        padding: 6px 14px;
        font-size: 11pt;
    }}
    QPushButton:hover {{
        background: #1e1e3f;
        color: {TEXT};
    }}
    QPushButton:disabled {{
        color: #44445a;
    }}
    QPushButton:focus {{
        color: {CYAN};
        outline: none;
    }}
"""


class ToolbarWidget(QWidget):
    """Translucent pill toolbar that floats over the treemap."""

    open_clicked    = pyqtSignal()
    back_clicked    = pyqtSignal()
    home_clicked    = pyqtSignal()
    refresh_clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(_PILL_W, _PILL_H)

        families = load_fonts()
        self._ui_font   = QFont(families.get("outfit", "Segoe UI"), 11)
        self._mono_font = QFont(families.get("jetbrains_mono", "Consolas"), 10)

        self._build_ui()
        self._apply_shadow()

    # ── Construction ──────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(2)

        self._open_btn    = self._make_btn("Open…")
        self._back_btn    = self._make_btn("← Back")
        self._home_btn    = self._make_btn("⌂ Home")
        self._refresh_btn = self._make_btn("↺ Refresh")

        self._open_btn.clicked.connect(self.open_clicked)
        self._back_btn.clicked.connect(self.back_clicked)
        self._home_btn.clicked.connect(self.home_clicked)
        self._refresh_btn.clicked.connect(self.refresh_clicked)

        layout.addWidget(self._open_btn)
        layout.addWidget(self._back_btn)
        layout.addWidget(self._home_btn)
        layout.addWidget(self._refresh_btn)

        # Thin separator
        sep = QLabel("|")
        sep.setStyleSheet(f"color: {BORDER_BRIGHT}; padding: 0 4px;")
        layout.addWidget(sep)

        self._breadcrumb = QLabel("")
        self._breadcrumb.setFont(self._mono_font)
        self._breadcrumb.setStyleSheet(f"color: {TEXT_DIM}; background: transparent;")
        self._breadcrumb.setMaximumWidth(310)
        layout.addWidget(self._breadcrumb, stretch=1)

    def _make_btn(self, label: str) -> QPushButton:
        btn = QPushButton(label)
        btn.setFont(self._ui_font)
        btn.setStyleSheet(_BTN_QSS)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        return btn

    def _apply_shadow(self) -> None:
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setColor(QColor(0, 212, 255, 100))  # cyan, 40% opacity
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 0)
        self.setGraphicsEffect(shadow)

    # ── Painting ──────────────────────────────────────────────────────────────

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        path.addRoundedRect(QRectF(0.5, 0.5, _PILL_W - 1, _PILL_H - 1), _RADIUS, _RADIUS)

        # Fill: dark glass
        painter.fillPath(path, QBrush(QColor(13, 13, 31, 224)))  # rgba ~0.88 alpha

        # Border
        painter.setPen(QPen(QColor(BORDER_BRIGHT), 1.0))
        painter.drawPath(path)

        painter.end()

    # ── Public API ────────────────────────────────────────────────────────────

    def set_breadcrumb(self, text: str) -> None:
        fm = self._breadcrumb.fontMetrics()
        elided = fm.elidedText(text, Qt.TextElideMode.ElideLeft, 310)
        self._breadcrumb.setText(elided)

    def set_breadcrumb_active(self, active: bool) -> None:
        color = TEXT_MID if active else TEXT_DIM
        self._breadcrumb.setStyleSheet(
            f"color: {color}; background: transparent; font-family: 'JetBrains Mono', monospace;"
        )

    def set_back_enabled(self, enabled: bool) -> None:
        self._back_btn.setEnabled(enabled)

    def set_home_enabled(self, enabled: bool) -> None:
        self._home_btn.setEnabled(enabled)

    # ── Positioning helper ────────────────────────────────────────────────────

    def reposition(self, treemap_rect) -> None:
        """Center the pill horizontally over *treemap_rect*, 16px from top."""
        cx = treemap_rect.x() + treemap_rect.width() // 2
        x = cx - _PILL_W // 2
        y = treemap_rect.y() + 16
        self.move(x, y)
        self.raise_()
