"""Sidebar: color-mode selector, filters, and legend."""
from __future__ import annotations
from datetime import datetime, timezone

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QLinearGradient, QPainter, QPixmap
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


class Sidebar(QWidget):
    filter_changed = pyqtSignal(object)  # ColorScheme

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(260)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setSpacing(8)

        # ── Color by ──────────────────────────────────────────────────────────
        layout.addWidget(QLabel("<b>Color by:</b>"))
        self._color_combo = QComboBox()
        self._color_combo.addItems(["Size", "Modified date", "Created date", "Owner"])
        self._color_combo.currentIndexChanged.connect(self._emit)
        layout.addWidget(self._color_combo)

        # ── Filter group ──────────────────────────────────────────────────────
        filter_box = QGroupBox("Filter")
        fb_layout = QVBoxLayout(filter_box)
        fb_layout.setSpacing(4)

        fb_layout.addWidget(QLabel("Modified after:"))
        self._mod_after = QDateEdit()
        self._mod_after.setCalendarPopup(True)
        self._mod_after.setSpecialValueText("(any)")
        self._mod_after.setDate(self._mod_after.minimumDate())
        fb_layout.addWidget(self._mod_after)

        fb_layout.addWidget(QLabel("Modified before:"))
        self._mod_before = QDateEdit()
        self._mod_before.setCalendarPopup(True)
        self._mod_before.setSpecialValueText("(any)")
        self._mod_before.setDate(self._mod_before.minimumDate())
        fb_layout.addWidget(self._mod_before)

        fb_layout.addWidget(QLabel("Owner contains:"))
        self._owner_edit = QLineEdit()
        self._owner_edit.setPlaceholderText("e.g. DOMAIN\\user")
        fb_layout.addWidget(self._owner_edit)

        fb_layout.addWidget(QLabel("Min size (MB):"))
        self._min_size = QDoubleSpinBox()
        self._min_size.setRange(0, 1_000_000)
        self._min_size.setSingleStep(1.0)
        fb_layout.addWidget(self._min_size)

        btn_row = QWidget()
        btn_layout = QVBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        self._apply_btn = QPushButton("Apply")
        self._apply_btn.clicked.connect(self._emit)
        self._reset_btn = QPushButton("Reset")
        self._reset_btn.clicked.connect(self._reset)
        btn_layout.addWidget(self._apply_btn)
        btn_layout.addWidget(self._reset_btn)
        fb_layout.addWidget(btn_row)

        layout.addWidget(filter_box)

        # ── Legend ────────────────────────────────────────────────────────────
        layout.addWidget(QLabel("<b>Legend</b>"))
        self._legend = LegendWidget()
        layout.addWidget(self._legend)
        self._color_combo.currentIndexChanged.connect(self._legend.set_mode)

        layout.addStretch()

    def _mode_str(self) -> str:
        mapping = {0: 'size', 1: 'modified', 2: 'created', 3: 'owner'}
        return mapping.get(self._color_combo.currentIndex(), 'size')

    def _emit(self) -> None:
        scheme = self._build_scheme()
        self.filter_changed.emit(scheme)

    def _reset(self) -> None:
        self._mod_after.setDate(self._mod_after.minimumDate())
        self._mod_before.setDate(self._mod_before.minimumDate())
        self._owner_edit.clear()
        self._min_size.setValue(0.0)
        self._emit()

    def _build_scheme(self) -> ColorScheme:
        min_date = self._mod_after.minimumDate()

        after_qdate = self._mod_after.date()
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
        self.setFixedHeight(60)

    def set_mode(self, index: int) -> None:
        self._mode = index
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        w, h = self.width(), self.height()

        grad = QLinearGradient(0, 0, w, 0)

        if self._mode == 0:  # size: light→dark blue
            grad.setColorAt(0, QColor(130, 160, 240))
            grad.setColorAt(1, QColor(30, 80, 180))
            lo_label, hi_label = "Small", "Large"
        elif self._mode in (1, 2):  # dates: old→recent (red→green)
            grad.setColorAt(0, QColor(200, 20, 40))
            grad.setColorAt(1, QColor(20, 180, 40))
            lo_label, hi_label = "Old", "Recent"
        else:  # owner: show a rainbow hint
            for i in range(6):
                grad.setColorAt(i / 5, QColor.fromHsvF(i / 6, 0.6, 0.75))
            lo_label, hi_label = "Owner A", "Owner Z"

        painter.fillRect(0, 0, w, h - 18, grad)
        painter.setPen(QColor("#ccc"))
        painter.drawText(0, h - 4, lo_label)
        fm = painter.fontMetrics()
        painter.drawText(w - fm.horizontalAdvance(hi_label), h - 4, hi_label)
        painter.end()
