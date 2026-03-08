from __future__ import annotations
import logging
import os
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from src.metadata import get_metadata
from src.models import FolderNode

logger = logging.getLogger(__name__)

_PROGRESS_INTERVAL = 500


def scan(root: Path) -> FolderNode:
    """Recursively scan root, returning a FolderNode tree with sizes."""
    return _scan_dir(root)


def _scan_dir(path: Path) -> FolderNode:
    children: list[FolderNode] = []
    total_size = 0

    try:
        entries = list(os.scandir(path))
    except OSError as exc:
        logger.warning("Cannot scan %s: %s", path, exc)
        return FolderNode(path=path, size=0, children=[])

    for entry in entries:
        try:
            is_link = entry.is_symlink()
        except OSError:
            continue
        if is_link:
            continue

        entry_path = Path(entry.path)
        try:
            is_dir  = entry.is_dir(follow_symlinks=False)
            is_file = entry.is_file(follow_symlinks=False)
        except OSError:
            continue

        if is_dir:
            child = _scan_dir(entry_path)
            children.append(child)
            total_size += child.size
        elif is_file:
            try:
                size = entry.stat().st_size
            except OSError:
                logger.warning("Cannot stat: %s", entry_path)
                size = 0
            children.append(FolderNode(path=entry_path, size=size, children=[]))
            total_size += size

    return FolderNode(path=path, size=total_size, children=children)


class ScanWorker(QThread):
    progress = pyqtSignal(str)       # status message
    finished = pyqtSignal(object)    # FolderNode root

    def __init__(self, root: Path, enrich_metadata: bool = True):
        super().__init__()
        self.root = root
        self.enrich_metadata = enrich_metadata
        self._count = 0

    def run(self) -> None:
        node = self._scan_dir(self.root)
        self.finished.emit(node)

    def _scan_dir(self, path: Path) -> FolderNode:
        children: list[FolderNode] = []
        total_size = 0

        self._count += 1
        if self._count % _PROGRESS_INTERVAL == 0:
            self.progress.emit(f"Scanning… {self._count:,} items")

        try:
            entries = list(os.scandir(path))
        except OSError as exc:
            logger.warning("Cannot scan %s: %s", path, exc)
            return FolderNode(path=path, size=0, children=[])

        for entry in entries:
            try:
                is_link = entry.is_symlink()
            except OSError:
                continue
            if is_link:
                continue

            entry_path = Path(entry.path)
            try:
                is_dir  = entry.is_dir(follow_symlinks=False)
                is_file = entry.is_file(follow_symlinks=False)
            except OSError:
                continue

            if is_dir:
                child = self._scan_dir(entry_path)
                children.append(child)
                total_size += child.size
            elif is_file:
                try:
                    size = entry.stat().st_size
                except OSError:
                    size = 0
                meta = get_metadata(entry_path) if self.enrich_metadata else None
                children.append(FolderNode(path=entry_path, size=size,
                                           children=[], metadata=meta))
                total_size += size

        meta = get_metadata(path) if self.enrich_metadata else None
        return FolderNode(path=path, size=total_size, children=children, metadata=meta)
