"""Recovery-set inventory, bounded retention and dashboard statistics."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from superlocalmemory.server.config_file import read_config
from superlocalmemory.storage._durable_json import read_json


def points(root: Path) -> list[dict]:
    found = []
    for path in (root / "backups").glob("backup_*/recovery.json"):
        if path.is_symlink() or path.parent.is_symlink():
            continue
        try:
            record = json.loads(path.read_text())
            if path.parent.name != "backup_" + record["id"]:
                continue
            found.append(record)
        except (OSError, ValueError, KeyError):
            continue
    return sorted(found, key=lambda record: record["created"], reverse=True)


def prune(root: Path) -> None:
    from superlocalmemory.server.backup_bundle import _point_dir

    maximum = max(1, int(read_config(root / "backup_config.json").get("max_backups", 10)))
    pending = read_json(root / "backup-recovery-outcome.json") or {}
    protected = (
        {pending.get("id"), pending.get("safety_id")}
        if pending.get("state") in ("queued", "stopping", "restoring")
        else set()
    )
    for record in points(root)[maximum:]:
        if record["id"] not in protected:
            shutil.rmtree(_point_dir(root, record["id"]))


def stats(root: Path, legacy: dict) -> dict:
    records = points(root)
    last = max([str(legacy.get("last_backup") or ""), *[r["created"] for r in records]]) or None
    size = sum(entry["bytes"] for r in records for entry in r["files"]) / 1024**2
    return {
        **legacy,
        "backup_count": int(legacy.get("backup_count") or 0) + len(records),
        "recovery_count": len(records),
        "last_backup": last,
        "total_size_mb": round(float(legacy.get("total_size_mb") or 0) + size, 2),
    }
