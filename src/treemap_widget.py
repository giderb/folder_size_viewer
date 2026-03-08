"""Custom QWidget that renders a treemap using QPainter — Dark Matter style."""
from __future__ import annotations
import colorsys
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PyQt6.QtWidgets import QApplication, QMenu, QToolTip, QWidget

from src.models import ColorScheme, FolderNode
from src.treemap import Rect, layout
from src.styles import (
    BORDER,
    CYAN,
    TEXT,
    TEXT_MID,
    VOID,
    load_fonts,
)

_GAP          = 3    # px inset between cells
_RADI         = 6    # corner radius
_TOOLBAR_INSET = 84  # px reserved at top for the floating toolbar (52h + 16 offset + 16 breathing)


class TreemapWidget(QWidget):
    node_clicked     = pyqtSignal(object)   # FolderNode
    resize_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._root: FolderNode | None = None
        self._layout: dict[FolderNode, QRectF] = {}
        self._scheme = ColorScheme()
        self._owner_colors: dict[str, QColor] = {}
        self._hovered_node: FolderNode | None = None
        self.setMouseTracking(True)
        self.setMinimumSize(400, 300)

        families = load_fonts()
        self._font_name  = QFont(families.get("outfit", "Segoe UI"), 12)
        self._font_name.setWeight(QFont.Weight.Medium)
        self._font_size  = QFont(families.get("jetbrains_mono", "Consolas"), 10)

    # ── Public API ────────────────────────────────────────────────────────────

    def set_root(self, root: FolderNode, scheme: ColorScheme) -> None:
        self._root = root
        self._scheme = scheme
        self._hovered_node = None
        self._rebuild_layout()
        self.update()

    def set_scheme(self, scheme: ColorScheme) -> None:
        self._scheme = scheme
        self.update()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _rebuild_layout(self) -> None:
        if self._root is None:
            self._layout = {}
            return
        # Leave a top strip clear so the floating toolbar never overlaps cell labels
        canvas = Rect(0, _TOOLBAR_INSET, self.width(), self.height() - _TOOLBAR_INSET)
        raw = layout(self._root, canvas)
        self._layout = {
            node: QRectF(r.x, r.y, r.w, r.h)
            for node, r in raw.items()
        }

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background: void black with subtle radial glow at center
        painter.fillRect(self.rect(), QColor(VOID))
        cx, cy = self.width() / 2, self.height() / 2
        rad_grad = QRadialGradient(QPointF(cx, cy), max(cx, cy))
        rad_grad.setColorAt(0, QColor(10, 10, 26, 120))
        rad_grad.setColorAt(1, QColor(6, 6, 18, 0))
        painter.fillRect(self.rect(), rad_grad)

        if not self._layout:
            self._draw_empty(painter)
            painter.end()
            return

        # Metadata for color scaling
        all_nodes = list(self._layout.keys())
        min_mod, max_mod = self._date_range(all_nodes, 'modified')
        min_cre, max_cre = self._date_range(all_nodes, 'created')
        min_size = min(n.size for n in all_nodes)
        max_size = max(n.size for n in all_nodes)

        for node, rect in self._layout.items():
            if rect.width() < 2 or rect.height() < 2:
                continue

            # Apply _GAP inset
            cell = rect.adjusted(_GAP, _GAP, -_GAP, -_GAP)
            if cell.width() < 2 or cell.height() < 2:
                continue

            visible = self._passes_filter(node)
            base_color = self._node_color(
                node, min_size, max_size, min_mod, max_mod, min_cre, max_cre
            )
            if not visible:
                base_color = base_color.darker(280)

            is_hovered = node is self._hovered_node

            self._draw_cell(painter, cell, base_color, is_hovered)
            self._draw_label(painter, node, cell)

        painter.end()

    def _draw_empty(self, painter: QPainter) -> None:
        families = load_fonts()
        font = QFont(families.get("outfit", "Segoe UI"), 15)
        painter.setFont(font)
        painter.setPen(QColor(TEXT_MID))
        painter.drawText(
            self.rect(),
            Qt.AlignmentFlag.AlignCenter,
            "Open a folder to explore",
        )

    def _draw_cell(
        self,
        painter: QPainter,
        cell: QRectF,
        base: QColor,
        hovered: bool,
    ) -> None:
        path = QPainterPath()
        path.addRoundedRect(cell, _RADI, _RADI)

        # Vertical gradient: top 30% lighter (glass sheen)
        grad = QLinearGradient(cell.topLeft(), cell.bottomLeft())
        lighter = base.lighter(145)
        grad.setColorAt(0.0, lighter)
        grad.setColorAt(0.3, base)
        grad.setColorAt(1.0, base.darker(115))

        painter.fillPath(path, grad)

        # Border
        if hovered:
            pen = QPen(QColor(CYAN), 2.0)
        else:
            pen = QPen(QColor(BORDER), 1.0)
        painter.setPen(pen)
        painter.drawPath(path)

        # Hover glow: extra translucent cyan highlight at top
        if hovered:
            glow_rect = QRectF(cell.x(), cell.y(), cell.width(), cell.height() * 0.25)
            glow_path = QPainterPath()
            glow_path.addRoundedRect(glow_rect, _RADI, _RADI)
            painter.fillPath(glow_path, QColor(0, 212, 255, 35))

    def _draw_label(self, painter: QPainter, node: FolderNode, cell: QRectF) -> None:
        if cell.width() < 80 or cell.height() < 40:
            return

        name = node.path.name or str(node.path)
        inner = cell.adjusted(5, 5, -5, -5)

        # Line 1: folder name (Outfit Medium 10pt)
        painter.setFont(self._font_name)
        fm1 = QFontMetrics(self._font_name)
        elided_name = fm1.elidedText(name, Qt.TextElideMode.ElideRight, int(inner.width()))
        painter.setPen(QColor(TEXT))
        name_rect = QRectF(inner.x(), inner.y(), inner.width(), fm1.height())
        painter.drawText(name_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided_name)

        # Line 2: size (JetBrains Mono 8pt)
        if cell.height() >= 56:
            painter.setFont(self._font_size)
            fm2 = QFontMetrics(self._font_size)
            size_str = _fmt_size(node.size)
            size_rect = QRectF(inner.x(), inner.y() + fm1.height() + 2, inner.width(), fm2.height())
            painter.setPen(QColor(TEXT_MID))
            painter.drawText(size_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, size_str)

    # ── Color logic ───────────────────────────────────────────────────────────

    def _node_color(self, node: FolderNode,
                    min_size: int, max_size: int,
                    min_mod: float, max_mod: float,
                    min_cre: float, max_cre: float) -> QColor:
        mode = self._scheme.mode

        if mode == 'size':
            t = _norm(node.size, min_size, max_size)
            return _size_gradient(t)

        if mode in ('modified', 'created'):
            ts = self._timestamp(node, mode)
            rng = (max_mod - min_mod) if mode == 'modified' else (max_cre - min_cre)
            lo = min_mod if mode == 'modified' else min_cre
            t = _norm(ts, lo, lo + rng) if rng > 0 else 0.5
            return _date_gradient(t)

        if mode == 'owner':
            owner = node.metadata.owner if node.metadata else 'unknown'
            return self._owner_color(owner)

        return QColor("#4a90d9")

    def _owner_color(self, owner: str) -> QColor:
        if owner not in self._owner_colors:
            idx = len(self._owner_colors)
            hue = (idx * 0.137) % 1.0
            r, g, b = colorsys.hsv_to_rgb(hue, 0.72, 0.82)
            self._owner_colors[owner] = QColor(int(r * 255), int(g * 255), int(b * 255))
        return self._owner_colors[owner]

    def _timestamp(self, node: FolderNode, field: str) -> float:
        if node.metadata is None:
            return 0.0
        dt: datetime = getattr(node.metadata, field)
        return dt.timestamp()

    def _date_range(self, nodes: list[FolderNode], field: str) -> tuple[float, float]:
        timestamps = [self._timestamp(n, field) for n in nodes if n.metadata]
        if not timestamps:
            return 0.0, 1.0
        return min(timestamps), max(timestamps)

    # ── Filter ────────────────────────────────────────────────────────────────

    def _passes_filter(self, node: FolderNode) -> bool:
        s = self._scheme
        if node.size < s.filter_min_size_mb * 1024 * 1024:
            return False
        if s.filter_owner and node.metadata:
            if s.filter_owner.lower() not in node.metadata.owner.lower():
                return False
        if node.metadata:
            if s.filter_modified_after and node.metadata.modified < s.filter_modified_after:
                return False
            if s.filter_modified_before and node.metadata.modified > s.filter_modified_before:
                return False
        return True

    # ── Mouse events ──────────────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            node = self._node_at(event.position())
            if node:
                self.node_clicked.emit(node)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        node = self._node_at(event.position())
        if node is not self._hovered_node:
            self._hovered_node = node
            self.update()
        if node:
            QToolTip.showText(event.globalPosition().toPoint(),
                              self._tooltip(node), self)
        else:
            QToolTip.hideText()
        super().mouseMoveEvent(event)

    def contextMenuEvent(self, event) -> None:
        node = self._node_at(event.pos())
        if not node:
            return
        menu = QMenu(self)
        open_act = menu.addAction("Open in Explorer")
        copy_act = menu.addAction("Copy Path")
        action = menu.exec(event.globalPos())
        if action == open_act:
            target = node.path if node.path.is_dir() else node.path.parent
            subprocess.Popen(["explorer", str(target)])
        elif action == copy_act:
            QApplication.clipboard().setText(str(node.path))

    def resizeEvent(self, event) -> None:
        self._rebuild_layout()
        self.resize_requested.emit()
        super().resizeEvent(event)

    def leaveEvent(self, event) -> None:
        if self._hovered_node is not None:
            self._hovered_node = None
            self.update()
        super().leaveEvent(event)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _node_at(self, pos) -> FolderNode | None:
        for node, rect in self._layout.items():
            cell = rect.adjusted(_GAP, _GAP, -_GAP, -_GAP)
            if cell.contains(pos.x(), pos.y()):
                return node
        return None

    def _tooltip(self, node: FolderNode) -> str:
        lines = [str(node.path), _fmt_size(node.size)]
        if node.metadata:
            lines.append(f"Owner: {node.metadata.owner}")
            lines.append(f"Modified: {node.metadata.modified.strftime('%Y-%m-%d %H:%M')}")
        return "\n".join(lines)


# ── Color helpers ─────────────────────────────────────────────────────────────

import math as _math


def _norm(value: float, lo: float, hi: float) -> float:
    """Sqrt-scaled normalisation — spreads mid-range values more visibly."""
    if hi == lo:
        return 0.5
    linear = max(0.0, min(1.0, (value - lo) / (hi - lo)))
    return _math.sqrt(linear)


def _lerp_color(a: tuple, b: tuple, t: float) -> QColor:
    return QColor(
        int(a[0] + t * (b[0] - a[0])),
        int(a[1] + t * (b[1] - a[1])),
        int(a[2] + t * (b[2] - a[2])),
    )


def _size_gradient(t: float) -> QColor:
    """3-stop: deep navy → ocean blue → electric cyan."""
    if t < 0.5:
        return _lerp_color((5, 5, 40), (10, 80, 180), t * 2)
    else:
        return _lerp_color((10, 80, 180), (0, 212, 255), (t - 0.5) * 2)


def _date_gradient(t: float) -> QColor:
    """3-stop: deep crimson → amber → emerald."""
    if t < 0.5:
        return _lerp_color((26, 0, 8), (180, 100, 0), t * 2)
    else:
        return _lerp_color((180, 100, 0), (0, 230, 118), (t - 0.5) * 2)


def _fmt_size(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"
