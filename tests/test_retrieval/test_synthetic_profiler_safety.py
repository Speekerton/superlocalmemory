"""Reject existing data before the profiler constructs a DatabaseManager."""

import pytest
from benchmark.recall_channels import synthetic_path


def test_unmarked_database_is_never_opened(tmp_path, monkeypatch):
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    directory = tmp_path / "profile"
    directory.mkdir()
    path = directory / "synthetic.db"
    path.write_bytes(b"must not be opened")
    with pytest.raises(ValueError, match="not seeded"):
        synthetic_path(directory, 100)
    assert path.read_bytes() == b"must not be opened"


def test_paths_and_symlinks_outside_tmpdir_are_rejected(tmp_path, monkeypatch):
    root = tmp_path / "sandbox"
    root.mkdir()
    monkeypatch.setenv("TMPDIR", str(root))
    with pytest.raises(ValueError, match="inside TMPDIR"):
        synthetic_path(tmp_path / "outside", 100)
    directory = root / "profile"
    directory.mkdir()
    (directory / "synthetic.db").symlink_to(tmp_path / "outside.db")
    with pytest.raises(ValueError, match="symlink"):
        synthetic_path(directory, 100)
