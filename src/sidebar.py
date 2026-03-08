"""Sidebar: color-mode selector, filters, and legend — Dark Matter style."""
from __future__ import annotations
from datetime import datetime, timezone

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath
from PyQt6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.models import ColorScheme
from src.styles import (
    BORDER,
    BORDER_BRIGHT,
    CYAN,
    SURFACE,
    TEXT,
    TEXT_DIM,
    TEXT_MID,
    VOID,
    load_fonts,
    make_button_style,
)

_SECTION_QSS = f"""
    QLabel {{
        color: {CYAN};
        font-size: 9pt;
        letter-spacing: 2px;
        font-weight: 600;
        background: transparent;
        padding-top: 10px;
    }}
"""

_INPUT_QSS = f"""
    QComboBox, QDateEdit, QLineEdit, QDoubleSpinBox {{
        background: #080818;
        border: 1px solid {BORDER};
        border-radius: 6px;
        color: {TEXT};
        padding: 5px 8px;
        font-size: 11pt;
        min-height: 28px;
    }}
    QComboBox:focus, QDateEdit:focus, QLineEdit:focus, QDoubleSpinBox:focus {{
        border-color: {CYAN};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 18px;
    }}
    QComboBox::down-arrow {{
        width: 8px;
        height: 8px;
    }}
    QComboBox QAbstractItemView {{
        background: #080818;
        color: {TEXT};
        selection-background-color: {BORDER};
        selection-color: {CYAN};
        border: 1px solid {BORDER};
    }}
    QDateEdit::up-button, QDateEdit::down-button {{
        width: 0; height: 0;
    }}
    QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
        border: none;
        background: transparent;
        width: 12px;
    }}
"""

_GROUPBOX_QSS = f"""
    QGroupBox {{
        border: 1px solid {BORDER};
        border-radius: 8px;
        margin-top: 8px;
        padding-top: 8px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 10px;
        color: {TEXT_MID};
        font-size: 8pt;
    }}
"""

_BODY_LABEL_QSS = f"color: {TEXT_MID}; font-size: 10pt; background: transparent;"


class Sidebar(QWidget):
    filter_changed = pyqtSignal(object)  # ColorScheme

    def __init__(self, parent=None, color_mode: str = "size"):
        super().__init__(parent)
        self.setFixedWidth(290)

        # Dark glass background with left border
        self.setStyleSheet(f"""
            Sidebar {{
                background: {SURFACE};
                border-left: 1px solid {BORDER};
            }}
        """)

        self._build_ui(color_mode)

    def _build_ui(self, color_mode: str = "size") -> None:
        families = load_fonts()
        ui_font  = QFont(families.get("outfit", "Segoe UI"), 11)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setSpacing(4)
        layout.setContentsMargins(12, 12, 12, 12)

        # ── Color by section ──────────────────────────────────────────────────
        color_lbl = QLabel("COLOR BY")
        color_lbl.setStyleSheet(_SECTION_QSS)
        layout.addWidget(color_lbl)

        self._color_combo = QComboBox()
        self._color_combo.addItems(["Size", "Modified date", "Created date", "Owner"])
        self._color_combo.setFont(ui_font)
        self._color_combo.setStyleSheet(_INPUT_QSS)
        idx = {"size": 0, "modified": 1, "created": 2, "owner": 3}.get(color_mode, 0)
        self._color_combo.setCurrentIndex(idx)
        self._color_combo.currentIndexChanged.connect(self._emit)
        layout.addWidget(self._color_combo)

        # ── Filter section ────────────────────────────────────────────────────
        filter_lbl = QLabel("FILTERS")
        filter_lbl.setStyleSheet(_SECTION_QSS)
        layout.addWidget(filter_lbl)

        filter_box = QGroupBox()
        filter_box.setStyleSheet(_GROUPBOX_QSS)
        fb_layout = QVBoxLayout(filter_box)
        fb_layout.setSpacing(4)
        fb_layout.setContentsMargins(8, 8, 8, 8)

        def _lbl(text: str) -> QLabel:
            l = QLabel(text)
            l.setFont(ui_font)
            l.setStyleSheet(_BODY_LABEL_QSS)
            return l

        fb_layout.addWidget(_lbl("Modified after:"))
        self._mod_after = QDateEdit()
        self._mod_after.setFont(ui_font)
        self._mod_after.setStyleSheet(_INPUT_QSS)
        self._mod_after.setCalendarPopup(True)
        self._mod_after.setSpecialValueText("(any)")
        self._mod_after.setDate(self._mod_after.minimumDate())
        fb_layout.addWidget(self._mod_after)

        fb_layout.addWidget(_lbl("Modified before:"))
        self._mod_before = QDateEdit()
        self._mod_before.setFont(ui_font)
        self._mod_before.setStyleSheet(_INPUT_QSS)
        self._mod_before.setCalendarPopup(True)
        self._mod_before.setSpecialValueText("(any)")
        self._mod_before.setDate(self._mod_before.minimumDate())
        fb_layout.addWidget(self._mod_before)

        fb_layout.addWidget(_lbl("Owner contains:"))
        self._owner_edit = QLineEdit()
        self._owner_edit.setFont(ui_font)
        self._owner_edit.setStyleSheet(_INPUT_QSS)
        self._owner_edit.setPlaceholderText("e.g. DOMAIN\\user")
        fb_layout.addWidget(self._owner_edit)

        fb_layout.addWidget(_lbl("Min size (MB):"))
        self._min_size = QDoubleSpinBox()
        self._min_size.setFont(ui_font)
        self._min_size.setStyleSheet(_INPUT_QSS)
        self._min_size.setRange(0, 1_000_000)
        self._min_size.setSingleStep(1.0)
        fb_layout.addWidget(self._min_size)

        self._apply_btn = QPushButton("Apply")
        self._apply_btn.setFont(ui_font)
        self._apply_btn.setStyleSheet(make_button_style(primary=True))
        self._apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_btn.clicked.connect(self._emit)
        fb_layout.addWidget(self._apply_btn)

        self._reset_btn = QPushButton("Reset")
        self._reset_btn.setFont(ui_font)
        self._reset_btn.setStyleSheet(make_button_style(primary=False))
        self._reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._reset_btn.clicked.connect(self._reset)
        fb_layout.addWidget(self._reset_btn)

        layout.addWidget(filter_box)

        # ── Legend section ────────────────────────────────────────────────────
        legend_lbl = QLabel("LEGEND")
        legend_lbl.setStyleSheet(_SECTION_QSS)
        layout.addWidget(legend_lbl)

        self._legend = LegendWidget()
        layout.addWidget(self._legend)
        self._color_combo.currentIndexChanged.connect(self._legend.set_mode)
        self._legend.set_mode(idx)

        layout.addStretch()

    # ── Unchanged signal / data logic ─────────────────────────────────────────

    def _mode_str(self) -> str:
        mapping = {0: 'size', 1: 'modified', 2: 'created', 3: 'owner'}
        return mapping.get(self._color_combo.currentIndex(), 'size')

    def _emit(self) -> None:
        self.filter_changed.emit(self._build_scheme())

    def _reset(self) -> None:
        self._mod_after.setDate(self._mod_after.minimumDate())
        self._mod_before.setDate(self._mod_before.minimumDate())
        self._owner_edit.clear()
        self._min_size.setValue(0.0)
        self._emit()

    def _build_scheme(self) -> ColorScheme:
        min_date = self._mod_after.minimumDate()

        after_qdate  = self._mod_after.date()
        before_qdate = self._mod_before.date()

        mod_after = None
        if after_qdate != min_date:
            mod_after = datetime(after_qdate.year(), after_qdate.month(),
                                 after_qdate.day(), tzinfo=timezone.utc)

        mod_before = None
        if before_qdate != min_date:
            mod_before = datetime(before_qdate.year(), before_qdate.month(),
                                  before_qdate.day(), tzinfo=timezone.utc)

        return ColorScheme(
            mode=self._mode_str(),
            filter_owner=self._owner_edit.text().strip(),
            filter_modified_after=mod_after,
            filter_modified_before=mod_before,
            filter_min_size_mb=self._min_size.value(),
        )

    def current_scheme(self) -> ColorScheme:
        return self._build_scheme()


class LegendWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._mode = 0
        self.setFixedHeight(90)

        families = load_fonts()
        self._mono_font = QFont(families.get("jetbrains_mono", "Consolas"), 10)

    def set_mode(self, index: int) -> None:
        self._mode = index
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        bar_h = h - 22

        grad = QLinearGradient(0, 0, w, 0)

        if self._mode == 0:  # size: deep navy → electric cyan
            grad.setColorAt(0, QColor(5, 5, 32))
            grad.setColorAt(1, QColor(0, 212, 255))
            lo_label, hi_label = "Small", "Large"
        elif self._mode in (1, 2):  # dates: crimson → emerald
            grad.setColorAt(0, QColor(26, 0, 8))
            grad.setColorAt(1, QColor(0, 230, 118))
            lo_label, hi_label = "Old", "Recent"
        else:  # owner: vivid rainbow
            for i in range(7):
                grad.setColorAt(i / 6, QColor.fromHsvF(i / 7, 0.72, 0.82))
            lo_label, hi_label = "Owner A", "Owner Z"

        # Rounded gradient bar
        bar_path = QPainterPath()
        bar_path.addRoundedRect(QLinearGradient(0, 0, 0, 0).finalStop().x(),
                                0, w, bar_h, 4, 4)
        bar_path = QPainterPath()
        bar_path.addRoundedRect(0, 0, w, bar_h, 4, 4)
        painter.fillPath(bar_path, grad)

        # Labels
        painter.setFont(self._mono_font)
        fm = painter.fontMetrics()
        painter.setPen(QColor(TEXT_MID))
        painter.drawText(0, h - 4, lo_label)
        painter.drawText(w - fm.horizontalAdvance(hi_label), h - 4, hi_label)
        painter.end()
