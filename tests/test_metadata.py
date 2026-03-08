import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.metadata import get_metadata

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows only")


def test_returns_metadata_for_file(tmp_path):
    f = tmp_path / "test.txt"
    f.write_bytes(b"hello")
    meta = get_metadata(f)
    assert meta is not None
    assert isinstance(meta.modified, datetime)
    assert isinstance(meta.created, datetime)
    assert isinstance(meta.owner, str)
    assert len(meta.owner) > 0


def test_modified_date_matches_stat(tmp_path):
    f = tmp_path / "test.txt"
    f.write_bytes(b"data")
    stat = f.stat()
    meta = get_metadata(f)
    assert meta is not None
    expected_mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
    delta = abs((meta.modified - expected_mtime).total_seconds())
    assert delta < 2.0


def test_created_date_matches_stat(tmp_path):
    f = tmp_path / "test.txt"
    f.write_bytes(b"data")
    stat = f.stat()
    meta = get_metadata(f)
    assert meta is not None
    expected_ctime = datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc)
    delta = abs((meta.created - expected_ctime).total_seconds())
    assert delta < 2.0


def test_inaccessible_returns_none(tmp_path):
    """Non-existent path returns None gracefully."""
    missing = tmp_path / "nonexistent.txt"
    meta = get_metadata(missing)
    assert meta is None


def test_works_for_directory(tmp_path):
    sub = tmp_path / "subdir"
    sub.mkdir()
    meta = get_metadata(sub)
    assert meta is not None
    assert isinstance(meta.owner, str)
