"""Detached restore: stop the owning daemon, restore offline, restart it."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from pathlib import Path

from superlocalmemory.server.backup_bundle import create_point, restore_point, verify_point
from superlocalmemory.storage._durable_json import write_json_atomic

logger = logging.getLogger(__name__)


def control(root: Path, action: str) -> None:
    env = {**os.environ, "SLM_DATA_DIR": str(root)}
    result = subprocess.run(
        [sys.executable, "-m", "superlocalmemory.cli.main", "serve", action],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=120,
    )
    if result.returncode:
        raise RuntimeError("Daemon lifecycle action failed")


def wait_stopped(pid: int) -> None:
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.2)
    raise RuntimeError("Daemon did not stop; restore refused")


def run(root: Path, point_id: str, pid: int) -> None:
    outcome = root / "backup-recovery-outcome.json"
    stopped = False
    restored = False
    restore_started = False
    safety_id = None
    try:
        verify_point(root, point_id)
        write_json_atomic(outcome, {"state": "stopping", "id": point_id})
        control(root, "stop")
        wait_stopped(pid)
        stopped = True
        safety_id = create_point(root)["id"]
        write_json_atomic(outcome, {"state": "restoring", "id": point_id, "safety_id": safety_id})
        restore_started = True
        restore_point(root, point_id)
        restored = True
        control(root, "start")
        write_json_atomic(
            outcome,
            {
                "state": "complete",
                "id": point_id,
                "safety_id": safety_id,
                "message": "Recovery backup restored and the daemon restarted.",
            },
        )
    except Exception:
        logger.exception("Backup recovery failed")
        write_json_atomic(
            outcome,
            {
                "state": "failed",
                "id": point_id,
                "safety_id": safety_id,
                "message": (
                    "Recovery could not finish. The service remains stopped "
                    "if restore safety "
                    "could not be established. Safety copies are kept."
                ),
            },
        )
        if stopped and (restored or not restore_started):
            try:
                control(root, "start")
            except Exception:
                logger.exception("Restart after failed recovery did not finish")


if __name__ == "__main__":
    run(Path(sys.argv[1]), sys.argv[2], int(sys.argv[3]))
