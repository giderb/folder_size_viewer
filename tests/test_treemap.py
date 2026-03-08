from pathlib import Path

import pytest

from src.models import FolderNode
from src.treemap import layout, Rect


def make_node(name: str, size: int, children=None) -> FolderNode:
    return FolderNode(path=Path(name), size=size, children=children or [])


CANVAS = Rect(0, 0, 800, 600)


def test_empty_children_returns_empty_dict():
    root = make_node("root", 0)
    result = layout(root, CANVAS)
    assert result == {}


def test_single_child_fills_entire_rect():
    child = make_node("a", 100)
    root = make_node("root", 100, children=[child])
    result = layout(root, CANVAS)
    assert child in result
    r = result[child]
    assert abs(r.x - CANVAS.x) < 1
    assert abs(r.y - CANVAS.y) < 1
    assert abs(r.w - CANVAS.w) < 1
    assert abs(r.h - CANVAS.h) < 1


def test_two_children_areas_proportional():
    big = make_node("big", 300)
    small = make_node("small", 100)
    root = make_node("root", 400, children=[big, small])
    result = layout(root, CANVAS)
    assert big in result
    assert small in result
    big_area = result[big].w * result[big].h
    small_area = result[small].w * result[small].h
    # big should have ~3x the area of small
    ratio = big_area / small_area
    assert 2.5 < ratio < 3.5


def test_total_area_equals_canvas():
    children = [make_node(str(i), (i + 1) * 100) for i in range(5)]
    total_size = sum(c.size for c in children)
    root = make_node("root", total_size, children=children)
    result = layout(root, CANVAS)
    total_rect_area = sum(r.w * r.h for r in result.values())
    canvas_area = CANVAS.w * CANVAS.h
    assert abs(total_rect_area - canvas_area) < 1.0


def test_squarified_aspect_ratios_reasonable():
    """Squarified layout should keep aspect ratios below 5:1."""
    children = [make_node(str(i), (i + 1) * 50) for i in range(10)]
    total_size = sum(c.size for c in children)
    root = make_node("root", total_size, children=children)
    result = layout(root, CANVAS)
    for node, r in result.items():
        if r.w > 0 and r.h > 0:
            aspect = max(r.w / r.h, r.h / r.w)
            assert aspect < 5, f"Poor aspect ratio {aspect:.2f} for {node.path}"


def test_all_rects_within_canvas():
    children = [make_node(str(i), 100) for i in range(4)]
    root = make_node("root", 400, children=children)
    result = layout(root, CANVAS)
    for r in result.values():
        assert r.x >= CANVAS.x - 0.01
        assert r.y >= CANVAS.y - 0.01
        assert r.x + r.w <= CANVAS.x + CANVAS.w + 0.01
        assert r.y + r.h <= CANVAS.y + CANVAS.h + 0.01


def test_zero_size_children_excluded():
    real = make_node("real", 100)
    zero = make_node("zero", 0)
    root = make_node("root", 100, children=[real, zero])
    result = layout(root, CANVAS)
    assert real in result
    assert zero not in result
