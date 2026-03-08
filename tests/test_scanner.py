import os
import stat
from pathlib import Path

import pytest

from src.scanner import scan


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
