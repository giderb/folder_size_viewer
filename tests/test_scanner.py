import os
import stat
from pathlib import Path

import pytest

from src.scanner import scan, scan_parallel


def test_empty_dir(tmp_path):
    node = scan(tmp_path)
    assert node.path == tmp_path
    assert node.size == 0
    assert node.children == []


def test_single_file(tmp_path):
    f = tmp_path / "file.txt"
    f.write_bytes(b"hello")
    node = scan(tmp_path)
    assert node.size == 5
    assert len(node.children) == 1
    assert node.children[0].path == f
    assert node.children[0].size == 5


def test_recursive_size(tmp_path):
    (tmp_path / "a.txt").write_bytes(b"a" * 100)
    sub = tmp_path / "subdir"
    sub.mkdir()
    (sub / "b.txt").write_bytes(b"b" * 200)
    node = scan(tmp_path)
    assert node.size == 300


def test_nested_structure(tmp_path):
    (tmp_path / "root.txt").write_bytes(b"r" * 10)
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "child.txt").write_bytes(b"c" * 20)
    node = scan(tmp_path)
    # Find the subdir node
    subdir_nodes = [c for c in node.children if c.path == sub]
    assert len(subdir_nodes) == 1
    assert subdir_nodes[0].size == 20


def test_symlinks_not_followed(tmp_path):
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    big_file = real_dir / "big.bin"
    big_file.write_bytes(b"x" * 1000)

    link = tmp_path / "link_to_real"
    try:
        link.symlink_to(real_dir)
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks not supported on this system")

    node = scan(tmp_path)
    # Only real subdir contributes to size, symlink is skipped
    assert node.size == 1000


def test_permission_error_skipped_gracefully(tmp_path):
    """Permission errors should not crash the scanner."""
    sub = tmp_path / "restricted"
    sub.mkdir()
    (sub / "secret.txt").write_bytes(b"s" * 50)

    # Make directory unreadable
    original_mode = sub.stat().st_mode
    try:
        sub.chmod(0o000)
        node = scan(tmp_path)
        # Should not raise; restricted dir may have size 0 or be skipped
        assert node is not None
    except PermissionError:
        pytest.skip("Cannot set permissions on this system")
    finally:
        sub.chmod(original_mode)


# ── Parallel scanner tests ──────────────────────────────────────────


def test_parallel_empty_dir(tmp_path):
    node = scan_parallel(tmp_path)
    assert node.path == tmp_path
    assert node.size == 0
    assert node.children == []


def test_parallel_single_file(tmp_path):
    f = tmp_path / "file.txt"
    f.write_bytes(b"hello")
    node = scan_parallel(tmp_path)
    assert node.size == 5
    assert len(node.children) == 1
    assert node.children[0].path == f
    assert node.children[0].size == 5


def test_parallel_recursive_size(tmp_path):
    (tmp_path / "a.txt").write_bytes(b"a" * 100)
    sub = tmp_path / "subdir"
    sub.mkdir()
    (sub / "b.txt").write_bytes(b"b" * 200)
    node = scan_parallel(tmp_path)
    assert node.size == 300


def test_parallel_nested_structure(tmp_path):
    (tmp_path / "root.txt").write_bytes(b"r" * 10)
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "child.txt").write_bytes(b"c" * 20)
    node = scan_parallel(tmp_path)
    subdir_nodes = [c for c in node.children if c.path == sub]
    assert len(subdir_nodes) == 1
    assert subdir_nodes[0].size == 20


def test_parallel_symlinks_skipped(tmp_path):
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    (real_dir / "big.bin").write_bytes(b"x" * 1000)

    link = tmp_path / "link_to_real"
    try:
        link.symlink_to(real_dir)
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks not supported on this system")

    node = scan_parallel(tmp_path)
    assert node.size == 1000


def test_parallel_permission_error(tmp_path):
    sub = tmp_path / "restricted"
    sub.mkdir()
    (sub / "secret.txt").write_bytes(b"s" * 50)

    original_mode = sub.stat().st_mode
    try:
        sub.chmod(0o000)
        node = scan_parallel(tmp_path)
        assert node is not None
    except PermissionError:
        pytest.skip("Cannot set permissions on this system")
    finally:
        sub.chmod(original_mode)


def test_parallel_matches_sequential(tmp_path):
    """Parallel and sequential scans must produce identical sizes."""
    # Build a complex tree
    for i in range(5):
        d = tmp_path / f"dir{i}"
        d.mkdir()
        for j in range(3):
            (d / f"file{j}.txt").write_bytes(b"x" * (10 * (i + 1) * (j + 1)))
            sub = d / f"sub{j}"
            sub.mkdir()
            (sub / "deep.bin").write_bytes(b"d" * (50 * (i + 1)))

    (tmp_path / "root.txt").write_bytes(b"r" * 42)

    seq = scan(tmp_path)
    par = scan_parallel(tmp_path)
    assert seq.size == par.size

    # Compare subdir sizes (order-independent)
    seq_sizes = sorted((c.path.name, c.size) for c in seq.children if c.children)
    par_sizes = sorted((c.path.name, c.size) for c in par.children if c.children)
    assert seq_sizes == par_sizes


def test_parallel_many_subdirs(tmp_path):
    """10+ top-level subdirs with files — verify correct aggregation."""
    expected = 0
    for i in range(12):
        d = tmp_path / f"dir{i:02d}"
        d.mkdir()
        size = (i + 1) * 100
        (d / "data.bin").write_bytes(b"\x00" * size)
        expected += size

    node = scan_parallel(tmp_path)
    assert node.size == expected
    assert len(node.children) == 12


def test_parallel_max_workers_respected(tmp_path):
    """Passing max_workers=2 still produces correct results."""
    for i in range(4):
        d = tmp_path / f"d{i}"
        d.mkdir()
        (d / "f.txt").write_bytes(b"w" * 25)

    node = scan_parallel(tmp_path, max_workers=2)
    assert node.size == 100


def test_parallel_fallback_single_subdir(tmp_path):
    """Single subdir falls back to sequential (no pool overhead)."""
    sub = tmp_path / "only_child"
    sub.mkdir()
    (sub / "file.txt").write_bytes(b"z" * 77)
    (tmp_path / "root.txt").write_bytes(b"r" * 33)

    node = scan_parallel(tmp_path)
    assert node.size == 110
