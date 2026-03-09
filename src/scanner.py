from __future__ import annotations
import logging
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from src.metadata import get_metadata
from src.models import FolderNode

logger = logging.getLogger(__name__)

_PROGRESS_INTERVAL = 500


def scan(root: Path) -> FolderNode:
    """Recursively scan root, returning a FolderNode tree with sizes."""
    return _scan_dir(root)


def scan_parallel(root: Path, max_workers: int | None = None) -> FolderNode:
    """Scan root using multiple processes for top-level subdirectories."""
    if max_workers is None:
        max_workers = min(os.cpu_count() or 1, 8)

    children: list[FolderNode] = []
    total_size = 0
    subdirs: list[Path] = []

    try:
        entries = list(os.scandir(root))
    except OSError as exc:
        logger.warning("Cannot scan %s: %s", root, exc)
        return FolderNode(path=root, size=0, children=[])

    # Separate files (stat in main process) and subdirs (fan out)
    for entry in entries:
        try:
            is_link = entry.is_symlink()
        except OSError:
            continue
        if is_link:
            continue

        entry_path = Path(entry.path)
        try:
            is_dir = entry.is_dir(follow_symlinks=False)
            is_file = entry.is_file(follow_symlinks=False)
        except OSError:
            continue

        if is_dir:
            subdirs.append(entry_path)
        elif is_file:
            try:
                size = entry.stat().st_size
            except OSError:
                logger.warning("Cannot stat: %s", entry_path)
                size = 0
            children.append(FolderNode(path=entry_path, size=size, children=[]))
            total_size += size

    # Fallback: if 0-1 subdirs, no pool overhead needed
    if len(subdirs) <= 1:
        for sd in subdirs:
            child = _scan_dir(sd)
            children.append(child)
            total_size += child.size
    else:
        with ProcessPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(_scan_dir, sd): sd for sd in subdirs}
            for future in futures:
                child = future.result()
                children.append(child)
                total_size += child.size

    return FolderNode(path=root, size=total_size, children=children)


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

    def run(self) -> None:
        self.progress.emit("Scanning…")
        node = self._parallel_scan(self.root)
        if self.enrich_metadata:
            self.progress.emit("Enriching metadata…")
            self._enrich_tree(node)
        self.finished.emit(node)

    def _parallel_scan(self, root: Path) -> FolderNode:
        """Parallel scan with per-subdir progress reporting."""
        max_workers = min(os.cpu_count() or 1, 8)
        children: list[FolderNode] = []
        total_size = 0
        subdirs: list[Path] = []

        try:
            entries = list(os.scandir(root))
        except OSError as exc:
            logger.warning("Cannot scan %s: %s", root, exc)
            return FolderNode(path=root, size=0, children=[])

        for entry in entries:
            try:
                is_link = entry.is_symlink()
            except OSError:
                continue
            if is_link:
                continue

            entry_path = Path(entry.path)
            try:
                is_dir = entry.is_dir(follow_symlinks=False)
                is_file = entry.is_file(follow_symlinks=False)
            except OSError:
                continue

            if is_dir:
                subdirs.append(entry_path)
            elif is_file:
                try:
                    size = entry.stat().st_size
                except OSError:
                    size = 0
                children.append(FolderNode(path=entry_path, size=size, children=[]))
                total_size += size

        n_subdirs = len(subdirs)
        if n_subdirs <= 1:
            for sd in subdirs:
                child = _scan_dir(sd)
                children.append(child)
                total_size += child.size
                self.progress.emit(f"Scanning… 1/1 subdirs")
        else:
            done = 0
            with ProcessPoolExecutor(max_workers=max_workers) as pool:
                futures = {pool.submit(_scan_dir, sd): sd for sd in subdirs}
                for future in futures:
                    child = future.result()
                    children.append(child)
                    total_size += child.size
                    done += 1
                    self.progress.emit(f"Scanning… {done}/{n_subdirs} subdirs")

        return FolderNode(path=root, size=total_size, children=children)

    @staticmethod
    def _enrich_tree(node: FolderNode) -> None:
        """Post-scan metadata enrichment (runs in QThread, not worker processes)."""
        node.metadata = get_metadata(node.path)
        for child in node.children:
            ScanWorker._enrich_tree(child)
