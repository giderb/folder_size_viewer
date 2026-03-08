from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal


@dataclass
class FileMetadata:
    owner: str
    created: datetime
    modified: datetime


@dataclass(eq=False)
class FolderNode:
    path: Path
    size: int  # bytes, recursive total
    children: list[FolderNode] = field(default_factory=list)
    metadata: FileMetadata | None = None

    def __hash__(self):
        return id(self)


@dataclass
class ColorScheme:
    mode: Literal['size', 'modified', 'created', 'owner'] = 'size'
    filter_owner: str = ''
    filter_modified_after: datetime | None = None
    filter_modified_before: datetime | None = None
    filter_min_size_mb: float = 0.0
