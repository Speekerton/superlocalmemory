# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory V4 | https://qualixar.com | https://varunpratap.com

"""A plain file copy of everything a restore may change, and putting it back.

The rollback of a dashboard restore must not depend on the code that just
failed (PR 251 re-review N1): re-running a restore against the safety point
repeats a failure that repeats, such as an unreadable media catalog. This copy
is taken with the service stopped and the writer lease held, so the files are
quiescent; putting it back is ``os.replace`` and ``unlink``, nothing more.

Covered: every managed store with its ``-wal``/``-shm`` files, the ``lance/``
vector index folder, the settings files and the mode file, and the set of
content-addressed media originals (files the failed restore added are removed;
``uploads.db`` and other non-original files under ``media/`` are never touched).
"""

from __future__ import annotations

import os
import shutil
import time
from pathlib import Path

_SIDECARS = ("", "-wal", "-shm")


def _settings_names() -> tuple[str, ...]:
    from superlocalmemory.core.config import CURRENT_MODE_FILE
    from superlocalmemory.server.backup_bundle import SETTINGS

    return (*SETTINGS, CURRENT_MODE_FILE)


def _originals(root: Path) -> set[Path]:
    from superlocalmemory.media import files

    base = Path(root) / "media"
    if not base.is_dir():
        return set()
    return {p for p in base.rglob("*") if p.is_file() and not p.is_symlink()
            and files.is_original(p.relative_to(base).as_posix())}


class PreRestoreCopy:
    """Take with :meth:`take`; then :meth:`roll_back` or :meth:`discard`."""

    def __init__(self, root: Path, folder: Path) -> None:
        self.root, self.folder = Path(root), Path(folder)
        self.present: set[str] = set()
        self.originals: set[Path] = set()

    @classmethod
    def take(cls, root: Path) -> PreRestoreCopy:
        from superlocalmemory.infra.backup import MANAGED_DATABASES

        root = Path(root)
        folder = root / "backups" / f".pre-restore-{time.time_ns()}"
        folder.mkdir(parents=True, mode=0o700)
        copy = cls(root, folder)
        names = [s + x for s in MANAGED_DATABASES for x in _SIDECARS] + list(_settings_names())
        for name in names:
            if (root / name).is_file():
                shutil.copy2(root / name, folder / name)
                copy.present.add(name)
        if (root / "lance").is_dir():
            shutil.copytree(root / "lance", folder / "lance", symlinks=True)
            copy.present.add("lance")
        copy.originals = _originals(root)
        return copy

    def roll_back(self) -> None:
        """Put every covered file back as it was. Settings first: they are smallest."""
        from superlocalmemory.infra.backup import MANAGED_DATABASES

        for name in _settings_names():
            self._restore_file(name)
        for store in MANAGED_DATABASES:
            for suffix in _SIDECARS:
                self._restore_file(store + suffix)
        self._restore_lance()
        for added in _originals(self.root) - self.originals:
            added.unlink(missing_ok=True)

    def _restore_file(self, name: str) -> None:
        live = self.root / name
        if name not in self.present:
            live.unlink(missing_ok=True)
            return
        staged = live.with_name(live.name + ".rollback")
        shutil.copy2(self.folder / name, staged)
        os.replace(staged, live)

    def _restore_lance(self) -> None:
        live = self.root / "lance"
        if live.exists():
            shutil.rmtree(live)
        if "lance" in self.present:
            shutil.copytree(self.folder / "lance", live, symlinks=True)

    def discard(self) -> None:
        shutil.rmtree(self.folder, ignore_errors=True)
