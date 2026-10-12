# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory V4 | https://qualixar.com | https://varunpratap.com

"""``recovery-needed.json``: the stores may be mixed, so nothing may start on them.

Written BEFORE a restore's first destructive write (phase ``writing``, with
the writing process's pid) and removed only after success or a clean rollback
(PR 251 round 4, R1). A process that dies in between, by crash, kill or power
loss, therefore leaves the marker behind with a dead pid, and every start path
(daemon start-up, ``ensure_daemon``, ``slm serve start``) refuses without
needing anyone to read the restore status first.

A failed rollback turns it into phase ``needs_recovery``, naming the kept
pre-restore copy. Only a successful ``slm backup restore-safety-copy`` or the
owner's explicit ``slm backup clear-recovery-needed`` removes it.
"""

from __future__ import annotations

import os
import shutil
from datetime import UTC, datetime
from pathlib import Path

from superlocalmemory.storage._durable_json import read_json, write_json_atomic

NAME = "recovery-needed.json"
RECOVER_COMMAND = "slm backup restore-safety-copy"
CLEAR_COMMAND = "slm backup clear-recovery-needed"


def _path(root: Path) -> Path:
    return Path(root) / NAME


def read(root: Path) -> dict | None:
    """The marker, or None. A marker that exists but cannot be read still counts."""
    path = _path(root)
    if not path.exists():
        return None
    try:
        return read_json(path) or {"phase": "needs_recovery"}
    except Exception:  # noqa: BLE001 - unreadable is treated as set, never as clear
        return {"phase": "needs_recovery"}


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def begin(root: Path, safety_id: str | None) -> dict | None:
    """Mark that a restore is about to write; returns the earlier marker, if any."""
    previous = read(root)
    write_json_atomic(_path(root), {
        "phase": "writing", "worker_pid": os.getpid(), "safety_id": safety_id,
        "previous": previous, "at": _now()})
    return previous


def end_clean(root: Path, previous: dict | None) -> None:
    """The stores are consistent again: drop the marker, or put the earlier one back."""
    if previous is None:
        _path(root).unlink(missing_ok=True)
    else:
        write_json_atomic(_path(root), previous)


def needs_recovery(root: Path, reason: str, safety_id: str | None,
                   kept_copy: str | None) -> None:
    write_json_atomic(_path(root), {
        "phase": "needs_recovery", "reason": reason, "safety_id": safety_id,
        "kept_copy": kept_copy, "at": _now()})


def kept_copies(marker: dict | None) -> list[str]:
    """Every pre-restore copy a marker (and the markers it replaced) kept."""
    found: list[str] = []
    while marker:
        if marker.get("kept_copy"):
            found.append(str(marker["kept_copy"]))
        marker = marker.get("previous")
    return found


def remove_copies(root: Path, copies: list[str]) -> None:
    """Delete kept pre-restore copies; only ``backups/.pre-restore-*`` folders qualify."""
    backups = (Path(root) / "backups").resolve()
    for copy in copies:
        path = Path(copy)
        if (path.name.startswith(".pre-restore-") and path.is_dir()
                and path.resolve().parent == backups):
            shutil.rmtree(path, ignore_errors=True)


def clear(root: Path) -> bool:
    """Remove the marker and the pre-restore copies it kept. True if one existed."""
    marker = read(root)
    if marker is None:
        return False
    remove_copies(root, kept_copies(marker))
    _path(root).unlink(missing_ok=True)
    return True


def _alive(pid) -> bool:
    try:
        os.kill(int(pid), 0)
    except (ProcessLookupError, ValueError, TypeError):
        return False
    except PermissionError:
        return True
    return True


def refusal(root: Path) -> str | None:
    """The start-up refusal a marker means, or None when there is no marker."""
    marker = read(root)
    if marker is None:
        return None
    if marker.get("phase") == "writing" and _alive(marker.get("worker_pid")):
        return "A restore is replacing the memory store; start again when it finishes."
    copies = kept_copies(marker)
    kept = f" The stores as they were before it are kept in {copies[0]}." if copies else ""
    return ("The last restore stopped part-way and the stores may be mixed, so the "
            f"service will not start on them.{kept} Run `{RECOVER_COMMAND}` to put the "
            f"safety copy back (or, only if you have repaired the stores yourself, "
            f"`{CLEAR_COMMAND}`), then `slm serve start`.")
