from __future__ import annotations
import logging
import os
from pathlib import Path

from src.models import FolderNode

logger = logging.getLogger(__name__)


def scan(root: Path) -> FolderNode:
    """Recursively scan root, returning a FolderNode tree with sizes."""
    return _scan_dir(root)


def _scan_dir(path: Path) -> FolderNode:
    children: list[FolderNode] = []
    total_size = 0

    try:
        entries = list(os.scandir(path))
    except PermissionError:
        logger.warning("Permission denied: %s", path)
        return FolderNode(path=path, size=0, children=[])

    for entry in entries:
        # Skip symlinks
        if entry.is_symlink():
            continue

        entry_path = Path(entry.path)
        if entry.is_dir(follow_symlinks=False):
            child = _scan_dir(entry_path)
            children.append(child)
            total_size += child.size
        elif entry.is_file(follow_symlinks=False):
            try:
                size = entry.stat().st_size
            except OSError:
                logger.warning("Cannot stat: %s", entry_path)
                size = 0
            children.append(FolderNode(path=entry_path, size=size, children=[]))
            total_size += size

    return FolderNode(path=path, size=total_size, children=children)


class ScanWorker:
    """QThread-compatible worker — imported by main_window after PyQt6 is available."""

    def __init__(self, root: Path):
        self.root = root
