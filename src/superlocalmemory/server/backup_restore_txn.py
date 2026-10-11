# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory V4 | https://qualixar.com | https://varunpratap.com

"""An offline restore as one unit: hold the store, change everything or nothing.

``backup_bundle.restore_point`` restores the databases atomically (the backup
coordinator keeps pre-restore copies and rolls back), then merges settings and
copies media originals. Those later steps can fail after the databases have
changed. This module wraps the whole thing:

* The writer lease (``memory.db.writer.lock``, the file the write coordinator
  claims) is held for the whole run, with this process recorded as holder, so
  a daemon started by a hook or a CLI call cannot claim the store and write
  part-way through. ``restore_in_progress`` lets daemon start-up refuse early,
  before migrations run.
* Before writing, the settings files are copied byte for byte and the media
  files present are listed. On any failure the safety point (taken a moment
  earlier, after the stop) is restored, media files the failed restore added
  are removed, and the settings bytes are put back. Only if that rollback also
  fails is the store left for ``slm backup restore-safety-copy``.
"""

from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from superlocalmemory.storage._durable_json import read_json

OUTCOME_NAME = "backup-recovery-outcome.json"
IN_PROGRESS = ("queued", "stopping", "restoring", "restarting")
RECOVER_COMMAND = "slm backup restore-safety-copy"
_LEASE_WAIT_S = 15.0


class StoreBusy(RuntimeError):
    """Another process holds the store's writer lease; nothing was changed."""


class RolledBack(RuntimeError):
    """The restore failed and the safety copy was put back."""


class RollbackFailed(RuntimeError):
    """The restore failed and putting the safety copy back failed too."""


def _lease_path(root: Path) -> Path:
    from superlocalmemory.storage._restore_boot import _lease_path as lease_for

    return lease_for(Path(root) / "memory.db")


@contextmanager
def writer_lease(root: Path, wait_s: float = _LEASE_WAIT_S) -> Iterator[None]:
    """Hold the store's writer lease, recorded as this process, for the block."""
    from superlocalmemory.core.file_lock import LockHeldError, exclusive_lock

    path = _lease_path(root)
    deadline = time.monotonic() + wait_s
    while True:
        lock = exclusive_lock(path, timeout_s=0.0)
        try:
            fd = lock.__enter__()
            break
        except LockHeldError:
            if time.monotonic() >= deadline:
                raise StoreBusy("Another SuperLocalMemory process has the store open") from None
            time.sleep(0.2)
    try:
        record = {"owner_id": "backup-restore", "pid": os.getpid(),
                  "database": str(Path(root) / "memory.db"),
                  "claimed_at_ms": int(time.time() * 1000)}
        os.ftruncate(fd, 0)
        os.lseek(fd, 0, os.SEEK_SET)
        os.write(fd, json.dumps(record, sort_keys=True).encode("utf-8") + b"\n")
        yield
    finally:
        try:  # no record naming a live process once the lease is free
            os.ftruncate(fd, 0)
        finally:
            lock.__exit__(None, None, None)


def _alive(pid) -> bool:
    try:
        os.kill(int(pid), 0)
    except (ProcessLookupError, ValueError, TypeError):
        return False
    except PermissionError:
        return True
    return True


def restore_in_progress(root: Path) -> str | None:
    """Why a daemon must not start now, or None. Never raises."""
    try:
        status = read_json(Path(root) / OUTCOME_NAME) or {}
    except Exception:  # noqa: BLE001 - an unreadable note never blocks start-up
        return None
    if status.get("state") in ("stopping", "restoring") and _alive(status.get("worker_pid")):
        return "A dashboard restore is replacing the memory store; start again when it finishes."
    return None


def _snapshot(root: Path) -> dict[str, bytes | None]:
    from superlocalmemory.core.config import CURRENT_MODE_FILE
    from superlocalmemory.server.backup_bundle import SETTINGS

    saved: dict[str, bytes | None] = {}
    for name in (*SETTINGS, CURRENT_MODE_FILE):
        path = Path(root) / name
        saved[name] = path.read_bytes() if path.is_file() else None
    return saved


def _put_back(root: Path, saved: dict[str, bytes | None]) -> None:
    from superlocalmemory.infra.private_files import create_private_file

    for name, data in saved.items():
        path = Path(root) / name
        if data is None:
            path.unlink(missing_ok=True)
            continue
        tmp = path.with_name(path.name + ".rollback")
        create_private_file(tmp)
        tmp.write_bytes(data)
        os.replace(tmp, path)


def _media_files(root: Path) -> set[Path]:
    base = Path(root) / "media"
    if not base.is_dir():
        return set()
    return {p for p in base.rglob("*") if p.is_file() and not p.is_symlink()}


def restore_atomically(root: Path, point_id: str, safety_id: str) -> None:
    """Restore ``point_id``; on failure put ``safety_id`` and the old settings back."""
    from superlocalmemory.server import backup_bundle

    root = Path(root)
    settings, media = _snapshot(root), _media_files(root)
    try:
        backup_bundle.restore_point(root, point_id)
        return
    except Exception as exc:
        cause = exc
    try:
        backup_bundle.restore_point(root, safety_id, settings=False)
        for added in _media_files(root) - media:
            added.unlink(missing_ok=True)
        _put_back(root, settings)
    except Exception as exc:
        raise RollbackFailed(str(exc)) from cause
    raise RolledBack(str(cause)) from cause


def recover_safety_copy(root: Path, safety_id: str) -> dict:
    """Put a safety copy back with the service stopped (the CLI path)."""
    from superlocalmemory.server.backup_bundle import create_point, verify_point

    verify_point(root, safety_id)
    with writer_lease(root, wait_s=0.0):
        before = create_point(root)["id"]
        restore_atomically(root, safety_id, before)
    return {"restored": safety_id, "safety_id": before}


LOG_NAME = "backup-recovery.log"
_STALE_S = 15 * 60


def log_path(root: Path) -> Path:
    return Path(root) / "logs" / LOG_NAME


def _dead(status: dict, mtime: float | None) -> bool:
    pid = status.get("worker_pid")
    if pid is not None:
        return not _alive(pid)
    return mtime is not None and time.time() - mtime > _STALE_S


def settle(status: dict, root: Path, mtime: float | None = None) -> dict:
    """Turn an in-progress status whose worker has died into an honest failure.

    The worker holds the writer lease through the operating system, so its
    death already released the store; this releases the queue (a dead
    "restoring" no longer answers every later restore with 409) and says what
    the operator should do, pointing at the worker's log.
    """
    if status.get("state") not in IN_PROGRESS or not _dead(status, mtime):
        return status
    stage = status.get("state")
    details = f"Details are in {log_path(root)}."
    if stage == "restoring":
        message = ("The recovery stopped part-way because its process ended, so the stores "
                   "may be partly restored. Stop the service (`slm serve stop`) and run "
                   f"`{RECOVER_COMMAND}` to put the safety copy back. {details}")
    elif stage == "restarting":
        message = ("The backup was restored but the restart may not have finished. "
                   f"If the dashboard does not respond, run `slm serve start`. {details}")
    else:
        message = ("Recovery stopped before restoring anything, so nothing was changed. "
                   f"If the service is not running, start it with `slm serve start`. {details}")
    status.update({"state": "failed", "message": message, "interrupted_at": stage})
    return status
