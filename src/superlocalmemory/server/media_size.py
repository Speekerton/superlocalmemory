"""Measure the installed media environment without following links."""

from __future__ import annotations

import os
import stat
from pathlib import Path


def installed_bytes(root: Path) -> int:
    total = 0
    seen = set()
    for folder, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = [d for d in dirs if not (Path(folder) / d).is_symlink()]
        for name in files:
            try:
                entry = (Path(folder) / name).lstat()
            except OSError:
                continue
            identity = (entry.st_dev, entry.st_ino)
            if stat.S_ISREG(entry.st_mode) and identity not in seen:
                total += entry.st_size
                seen.add(identity)
    return total
