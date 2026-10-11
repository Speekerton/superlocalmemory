# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later
"""Operator-selected file revisions bind execution evidence to checked bytes."""

import hashlib
import json
from pathlib import Path


def snapshot(cwd, paths):
    root = Path(cwd).resolve()
    records = []
    for name in paths:
        path = Path(name)
        path = path if path.is_absolute() else root / path
        path = path.absolute()
        resolved = path.resolve()
        if not resolved.is_relative_to(root) or not resolved.is_file():
            raise ValueError("Gate artifacts must be files in the approved working directory")
        records.append({
            "path": str(path), "resolved_path": str(resolved),
            "sha256": hashlib.sha256(resolved.read_bytes()).hexdigest(),
        })
    if not records:
        raise ValueError("Register at least one checked artifact")
    encoded = json.dumps(sorted(records, key=lambda r: r["path"]), sort_keys=True)
    return encoded, hashlib.sha256(encoded.encode()).hexdigest()


def matches(job):
    if str(Path(job["cwd"]).resolve()) != job["cwd"]:
        return False
    records = json.loads(job["artifacts_json"])
    encoded, digest = snapshot(job["cwd"], [record["path"] for record in records])
    return encoded == job["artifacts_json"] and digest == job["revision_digest"]
