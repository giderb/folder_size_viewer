"""MainWindow: orchestrates scanning, layout, and navigation."""
from __future__ import annotations
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QLabel,
    QMainWindow,
    QSplitter,
    QStatusBar,
    QToolBar,
    QWidget,
)

from src.models import ColorScheme, FolderNode
from src.scanner import ScanWorker
from src.sidebar import Sidebar
from src.treemap_widget import TreemapWidget, _fmt_size


class MainWindow(QMainWindow):
    def __init__(self, start_path: Path | None = None):
        super().__init__()
        self.setWindowTitle("Folder Size Viewer")
        self.resize(1200, 750)

        self._history: list[FolderNode] = []
        self._root: FolderNode | None = None
        self._current: FolderNode | None = None
        self._worker: ScanWorker | None = None

        self._build_ui()

        if start_path:
            self._start_scan(start_path)

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # Toolbar
        tb = QToolBar("Navigation")
        tb.setMovable(False)
        self.addToolBar(tb)

        self._open_btn = tb.addAction("Open…")
        self._open_btn.triggered.connect(self._open_dialog)
        self._back_btn = tb.addAction("← Back")
        self._back_btn.triggered.connect(self._go_back)
        self._home_btn = tb.addAction("⌂ Home")
        self._home_btn.triggered.connect(self._go_home)
        self._refresh_btn = tb.addAction("↺ Refresh")
        self._refresh_btn.triggered.connect(self._refresh)

        tb.addSeparator()
        self._breadcrumb = QLabel("")
        self._breadcrumb.setTextFormat(Qt.TextFormat.PlainText)
        tb.addWidget(self._breadcrumb)

        self._update_nav_buttons()

        # Central splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(splitter)

        self._treemap = TreemapWidget()
        self._treemap.node_clicked.connect(self._on_node_clicked)
        splitter.addWidget(self._treemap)

        self._sidebar = Sidebar()
        self._sidebar.filter_changed.connect(self._on_filter_changed)
        splitter.addWidget(self._sidebar)

        splitter.setStretchFactor(0, 1)
        splitter.setSizes([940, 260])

        # Status bar
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("Open a folder to start.")

    # ── Scanning ──────────────────────────────────────────────────────────────

    def _open_dialog(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Folder")
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
        self._breadcrumb.setText(str(path))
        self._status.showMessage(f"Scanning {path}…")

        self._worker = ScanWorker(path)
        self._worker.progress.connect(self._status.showMessage)
        self._worker.finished.connect(self._on_scan_finished)
        self._worker.start()

    def _on_scan_finished(self, root: FolderNode) -> None:
        self._root = root
        self._current = root
        self._history.clear()
        self._display(root)
        size_str = _fmt_size(root.size)
        self._status.showMessage(f"Done — Total: {size_str}")

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
        self._breadcrumb.setText(str(node.path))
        self._treemap.set_root(node, self._sidebar.current_scheme())
        self._update_nav_buttons()

    def _update_nav_buttons(self) -> None:
        has_history = bool(self._history)
        self._back_btn.setEnabled(has_history)
        self._home_btn.setEnabled(self._root is not None and self._current is not self._root)

    # ── Filter ────────────────────────────────────────────────────────────────

    def _on_filter_changed(self, scheme: ColorScheme) -> None:
        self._treemap.set_scheme(scheme)
