"""Squarified treemap layout algorithm (pure Python, no external libs).

Reference: Bruls, Huizing & van Wijk, "Squarified Treemaps" (2000).
"""
from __future__ import annotations
from dataclasses import dataclass

from src.models import FolderNode


@dataclass
class Rect:
    x: float
    y: float
    w: float
    h: float

    @property
    def area(self) -> float:
        return self.w * self.h


def layout(root: FolderNode, canvas: Rect) -> dict[FolderNode, Rect]:
    """Return a mapping of FolderNode → Rect for each direct child of root."""
    children = [c for c in root.children if c.size > 0]
    if not children:
        return {}

    total = sum(c.size for c in children)
    # Sort descending for squarification
    children = sorted(children, key=lambda n: n.size, reverse=True)

    result: dict[FolderNode, Rect] = {}
    _squarify(children, total, canvas, result)
    return result


def _squarify(
    nodes: list[FolderNode],
    total: float,
    rect: Rect,
    result: dict[FolderNode, Rect],
) -> None:
    """Recursively lay out nodes using the squarify algorithm."""
    if not nodes or total <= 0 or rect.w <= 0 or rect.h <= 0:
        return

    if len(nodes) == 1:
        result[nodes[0]] = Rect(rect.x, rect.y, rect.w, rect.h)
        return

    # Build row greedily: add items while worst aspect ratio improves
    row: list[FolderNode] = [nodes[0]]
    worst = _worst_ratio(row, total, rect)

    for node in nodes[1:]:
        candidate = row + [node]
        new_worst = _worst_ratio(candidate, total, rect)
        if new_worst <= worst:
            row = candidate
            worst = new_worst
        else:
            break

    # Lay out current row
    row_size = sum(n.size for n in row)
    _layout_row(row, row_size, total, rect, result)

    # Recurse into remaining space with remaining items and remaining total
    remaining = nodes[len(row):]
    remaining_rect = _remaining_rect(row_size, total, rect)
    _squarify(remaining, total - row_size, remaining_rect, result)


def _worst_ratio(row: list[FolderNode], total: float, rect: Rect) -> float:
    """Worst aspect ratio of rects that would be created for this row."""
    if not row or total <= 0:
        return float('inf')

    row_sum = sum(n.size for n in row)
    if row_sum <= 0:
        return float('inf')

    worst = 0.0
    if rect.w >= rect.h:
        # Horizontal strip: height = H * row_sum / total
        strip_h = rect.h * row_sum / total
        if strip_h <= 0:
            return float('inf')
        for n in row:
            w_i = rect.w * n.size / row_sum
            ratio = max(w_i / strip_h, strip_h / w_i) if w_i > 0 else float('inf')
            worst = max(worst, ratio)
    else:
        # Vertical strip: width = W * row_sum / total
        strip_w = rect.w * row_sum / total
        if strip_w <= 0:
            return float('inf')
        for n in row:
            h_i = rect.h * n.size / row_sum
            ratio = max(strip_w / h_i, h_i / strip_w) if h_i > 0 else float('inf')
            worst = max(worst, ratio)

    return worst


def _layout_row(
    row: list[FolderNode],
    row_size: float,
    total: float,
    rect: Rect,
    result: dict[FolderNode, Rect],
) -> None:
    """Place row nodes into a strip along the shorter edge of rect."""
    if total <= 0 or row_size <= 0:
        return

    row_sum = sum(n.size for n in row)
    if row_sum <= 0:
        return

    if rect.w >= rect.h:
        # Horizontal strip along the top
        strip_h = rect.h * row_size / total
        x = rect.x
        for node in row:
            w = rect.w * node.size / row_sum
            result[node] = Rect(x, rect.y, w, strip_h)
            x += w
    else:
        # Vertical strip along the left
        strip_w = rect.w * row_size / total
        y = rect.y
        for node in row:
            h = rect.h * node.size / row_sum
            result[node] = Rect(rect.x, y, strip_w, h)
            y += h


def _remaining_rect(row_size: float, total: float, rect: Rect) -> Rect:
    """Return the rectangle remaining after a strip is laid out."""
    if total <= 0:
        return rect

    if rect.w >= rect.h:
        strip_h = rect.h * row_size / total
        return Rect(rect.x, rect.y + strip_h, rect.w, rect.h - strip_h)
    else:
        strip_w = rect.w * row_size / total
        return Rect(rect.x + strip_w, rect.y, rect.w - strip_w, rect.h)
