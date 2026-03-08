"""MainWindow: orchestrates scanning, layout, and navigation — Dark Matter UI."""
from __future__ import annotations
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QIcon
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QSplitter,
    QWidget,
)

from src.models import ColorScheme, FolderNode
from src.scanner import ScanWorker
from src.sidebar import Sidebar
from src.toolbar_widget import ToolbarWidget
from src.treemap_widget import TreemapWidget, _fmt_size
from src.styles import (
    BORDER,
    CYAN,
    SURFACE,
    TEXT,
    TEXT_MID,
    APP_STYLESHEET,
    load_fonts,
)


class _StatusBar(QWidget):
    """Custom status bar: pulsing dot + status text on left, total size on right."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(34)
        self.setStyleSheet(f"""
            _StatusBar, QWidget {{
                background: {SURFACE};
                border-top: 1px solid {BORDER};
            }}
        """)

        families = load_fonts()
        ui_font   = QFont(families.get("outfit", "Segoe UI"), 11)
        mono_font = QFont(families.get("jetbrains_mono", "Consolas"), 10)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(6)

        self._dot = QLabel("●")
        self._dot.setFont(ui_font)
        self._dot.setStyleSheet(f"color: {CYAN}; background: transparent;")
        layout.addWidget(self._dot)

        self._msg = QLabel("Open a folder to start.")
        self._msg.setFont(ui_font)
        self._msg.setStyleSheet(f"color: {TEXT_MID}; background: transparent;")
        layout.addWidget(self._msg, stretch=1)

        self._size_lbl = QLabel("")
        self._size_lbl.setFont(mono_font)
        self._size_lbl.setStyleSheet(f"color: {CYAN}; background: transparent;")
        layout.addWidget(self._size_lbl)

        # Pulsing dot animation
        self._pulse_state = True
        self._pulse_timer = QTimer(self)
        self._pulse_timer.setInterval(800)
        self._pulse_timer.timeout.connect(self._tick_pulse)
        self._pulse_timer.start()

    def _tick_pulse(self) -> None:
        self._pulse_state = not self._pulse_state
        if self._pulse_state:
            self._dot.setStyleSheet(f"color: {CYAN}; background: transparent;")
        else:
            self._dot.setStyleSheet("color: rgba(0, 212, 255, 80); background: transparent;")

    def show_message(self, text: str) -> None:
        self._msg.setText(text)

    def set_total_size(self, text: str) -> None:
        self._size_lbl.setText(text)


class MainWindow(QMainWindow):
    def __init__(self, start_path: Path | None = None, color_mode: str = "size"):
        super().__init__()
        self.setWindowTitle("Folder Size Viewer")
        self.resize(1200, 750)

        if getattr(sys, 'frozen', False):
            _icon_path = Path(sys._MEIPASS) / "icon.png"
        else:
            _icon_path = Path(__file__).parent / "icon.png"
        if _icon_path.exists():
            self.setWindowIcon(QIcon(str(_icon_path)))

        # Apply global Dark Matter stylesheet
        self.setStyleSheet(APP_STYLESHEET)

        self._history: list[FolderNode] = []
        self._root: FolderNode | None = None
        self._current: FolderNode | None = None
        self._worker: ScanWorker | None = None

        self._build_ui(color_mode)

        if start_path:
            self._start_scan(start_path)

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self, color_mode: str = "size") -> None:
        # Central splitter (treemap + sidebar)
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(self._splitter)

        self._treemap = TreemapWidget()
        self._treemap.node_clicked.connect(self._on_node_clicked)
        self._treemap.resize_requested.connect(self._reposition_toolbar)
        self._splitter.addWidget(self._treemap)

        self._sidebar = Sidebar(color_mode=color_mode)
        self._sidebar.filter_changed.connect(self._on_filter_changed)
        self._splitter.addWidget(self._sidebar)

        self._splitter.setStretchFactor(0, 1)
        self._splitter.setSizes([910, 290])
        self._splitter.splitterMoved.connect(self._reposition_toolbar)

        # Custom status bar (embedded widget at bottom)
        self._status_bar = _StatusBar()
        # We can't use setStatusBar() with a plain QWidget; embed it via layout
        container = QWidget()
        v_layout = __import__('PyQt6.QtWidgets', fromlist=['QVBoxLayout']).QVBoxLayout(container)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(0)
        v_layout.addWidget(self._splitter)
        v_layout.addWidget(self._status_bar)
        self.setCentralWidget(container)

        # Floating pill toolbar — parented to MainWindow so it overlays everything
        self._toolbar = ToolbarWidget(self)
        self._toolbar.open_clicked.connect(self._open_dialog)
        self._toolbar.back_clicked.connect(self._go_back)
        self._toolbar.home_clicked.connect(self._go_home)
        self._toolbar.refresh_clicked.connect(self._refresh)

        self._update_nav_buttons()

        # Initial position (will be corrected once window is shown)
        self._toolbar.show()
        self._reposition_toolbar()

    # ── Toolbar positioning ───────────────────────────────────────────────────

    def _reposition_toolbar(self) -> None:
        tm_rect = self._treemap.geometry()
        # Map treemap rect to main window coords
        top_left = self._treemap.mapTo(self, tm_rect.topLeft() - tm_rect.topLeft())
        import PyQt6.QtCore as _qc
        mapped = _qc.QRect(
            self._treemap.mapTo(self, _qc.QPoint(0, 0)),
            self._treemap.size(),
        )
        self._toolbar.reposition(mapped)

    # ── Scanning ──────────────────────────────────────────────────────────────

    def _open_dialog(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            "Select Folder",
            options=QFileDialog.Option.DontResolveSymlinks,
        )
        if path:
            self._start_scan(Path(path))

    def _start_scan(self, path: Path) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait()

        self._history.clear()
        self._root = None
        self._current = None
        self._treemap.set_root(FolderNode(path=path, size=0), self._sidebar.current_scheme())
        self._toolbar.set_breadcrumb(str(path))
        self._toolbar.set_breadcrumb_active(False)
        self._status_bar.show_message(f"Scanning {path}…")

        self._worker = ScanWorker(path)
        self._worker.progress.connect(self._status_bar.show_message)
        self._worker.finished.connect(self._on_scan_finished)
        self._worker.start()

    def _on_scan_finished(self, root: FolderNode) -> None:
        self._root = root
        self._current = root
        self._history.clear()
        self._display(root)
        size_str = _fmt_size(root.size)
        self._status_bar.show_message(f"Done — Total: {size_str}")
        self._status_bar.set_total_size(size_str)
        self._toolbar.set_breadcrumb_active(True)

    # ── Navigation ────────────────────────────────────────────────────────────

    def _on_node_clicked(self, node: FolderNode) -> None:
        if not node.children:
            return
        self._history.append(self._current)
        self._current = node
        self._display(node)

    def _go_back(self) -> None:
        if self._history:
            self._current = self._history.pop()
            self._display(self._current)

    def _go_home(self) -> None:
        if self._root:
            self._history.clear()
            self._current = self._root
            self._display(self._root)

    def _refresh(self) -> None:
        if self._root:
            self._start_scan(self._root.path)

    def _display(self, node: FolderNode) -> None:
        self._toolbar.set_breadcrumb(str(node.path))
        self._treemap.set_root(node, self._sidebar.current_scheme())
        self._update_nav_buttons()

    def _update_nav_buttons(self) -> None:
        has_history = bool(self._history)
        self._toolbar.set_back_enabled(has_history)
        self._toolbar.set_home_enabled(self._root is not None and self._current is not self._root)

    # ── Filter ────────────────────────────────────────────────────────────────

    def _on_filter_changed(self, scheme: ColorScheme) -> None:
        self._treemap.set_scheme(scheme)

    # ── Resize ────────────────────────────────────────────────────────────────

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._reposition_toolbar()
