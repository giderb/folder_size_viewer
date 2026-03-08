"""Custom QWidget that renders a treemap using QPainter."""
from __future__ import annotations
import colorsys
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from PyQt6.QtCore import QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFontMetrics, QPainter, QPen
from PyQt6.QtWidgets import QApplication, QMenu, QToolTip, QWidget

from src.models import ColorScheme, FolderNode
from src.treemap import Rect, layout


class TreemapWidget(QWidget):
    node_clicked = pyqtSignal(object)   # FolderNode
    resize_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._root: FolderNode | None = None
        self._layout: dict[FolderNode, QRectF] = {}
        self._scheme = ColorScheme()
        self._owner_colors: dict[str, QColor] = {}
        self.setMouseTracking(True)
        self.setMinimumSize(400, 300)

    # ── Public API ────────────────────────────────────────────────────────────

    def set_root(self, root: FolderNode, scheme: ColorScheme) -> None:
        self._root = root
        self._scheme = scheme
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
        canvas = Rect(0, 0, self.width(), self.height())
        raw = layout(self._root, canvas)
        self._layout = {
            node: QRectF(r.x, r.y, r.w, r.h)
            for node, r in raw.items()
        }

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.fillRect(self.rect(), QColor("#1e1e2e"))

        if not self._layout:
            painter.setPen(QColor("#888"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No data")
            return

        # Collect metadata for color scaling
        all_nodes = list(self._layout.keys())
        min_mod, max_mod = self._date_range(all_nodes, 'modified')
        min_cre, max_cre = self._date_range(all_nodes, 'created')
        min_size = min(n.size for n in all_nodes)
        max_size = max(n.size for n in all_nodes)

        pen = QPen(QColor("#111"), 1)
        painter.setPen(pen)

        for node, rect in self._layout.items():
            if rect.width() < 2 or rect.height() < 2:
                continue

            visible = self._passes_filter(node)
            color = self._node_color(node, min_size, max_size, min_mod, max_mod,
                                     min_cre, max_cre)
            if not visible:
                color = color.darker(200)

            painter.fillRect(rect, color)
            painter.drawRect(rect)
            self._draw_label(painter, node, rect)

        painter.end()

    def _draw_label(self, painter: QPainter, node: FolderNode, rect: QRectF) -> None:
        if rect.width() < 40 or rect.height() < 16:
            return
        name = node.path.name or str(node.path)
        fm = QFontMetrics(painter.font())
        text = fm.elidedText(name, Qt.TextElideMode.ElideRight, int(rect.width()) - 6)
        painter.setPen(QColor("#fff"))
        painter.drawText(rect.adjusted(3, 3, -3, -3), Qt.AlignmentFlag.AlignTop, text)

    # ── Color logic ───────────────────────────────────────────────────────────

    def _node_color(self, node: FolderNode,
                    min_size: int, max_size: int,
                    min_mod: float, max_mod: float,
                    min_cre: float, max_cre: float) -> QColor:
        mode = self._scheme.mode

        if mode == 'size':
            t = _norm(node.size, min_size, max_size)
            return _blue_gradient(t)

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
            r, g, b = colorsys.hsv_to_rgb(hue, 0.6, 0.75)
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

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _node_at(self, pos) -> FolderNode | None:
        for node, rect in self._layout.items():
            if rect.contains(pos.x(), pos.y()):
                return node
        return None

    def _tooltip(self, node: FolderNode) -> str:
        lines = [str(node.path), _fmt_size(node.size)]
        if node.metadata:
            lines.append(f"Owner: {node.metadata.owner}")
            lines.append(f"Modified: {node.metadata.modified.strftime('%Y-%m-%d %H:%M')}")
        return "\n".join(lines)


# ── Color helpers ─────────────────────────────────────────────────────────────

def _norm(value: float, lo: float, hi: float) -> float:
    if hi == lo:
        return 0.5
    return max(0.0, min(1.0, (value - lo) / (hi - lo)))


def _blue_gradient(t: float) -> QColor:
    """Light blue (small) → dark blue (large)."""
    r = int(30 + (1 - t) * 100)
    g = int(80 + (1 - t) * 80)
    b = int(180 + (1 - t) * 60)
    return QColor(r, g, b)


def _date_gradient(t: float) -> QColor:
    """Green (recent, t=1) → red (old, t=0)."""
    r = int((1 - t) * 200 + 20)
    g = int(t * 180 + 20)
    b = 40
    return QColor(r, g, b)


def _fmt_size(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"
