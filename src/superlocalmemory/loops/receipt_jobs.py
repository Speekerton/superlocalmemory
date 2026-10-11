# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later
"""Operator-owned gate registrations; no MCP tool can register or execute jobs.

Watchers reference a registration nonce. Only this boundary selects the check,
task revision, producer, freshness and permission to use pre-start evidence.
Register a new job for every changed task; the newest registration supersedes
older jobs for the same profile/watcher. Ordinary memory writes are irrelevant.
"""

import json
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from superlocalmemory.loops.artifact_revision import matches, snapshot
from superlocalmemory.loops.execution_receipts import command_digest, run_check

_SCHEMA = (
    "CREATE TABLE IF NOT EXISTS loop_gate_jobs ("
    "job_id TEXT PRIMARY KEY, profile_id TEXT NOT NULL, task_id TEXT NOT NULL, "
    "watcher_name TEXT NOT NULL, run_id TEXT NOT NULL, producer TEXT NOT NULL, "
    "command_digest TEXT NOT NULL, command_json TEXT NOT NULL, cwd TEXT NOT NULL, "
    "artifacts_json TEXT NOT NULL, revision_digest TEXT NOT NULL, "
    "registered_at TEXT NOT NULL, expires_at TEXT NOT NULL, "
    "allow_prestart_evidence INTEGER NOT NULL CHECK(allow_prestart_evidence IN (0,1)), "
    "FOREIGN KEY(profile_id) REFERENCES profiles(profile_id) ON DELETE CASCADE)"
)


def _store(db, job):
    db.execute(_SCHEMA)
    for operation in ("UPDATE", "DELETE"):
        guard = (
            " WHEN EXISTS (SELECT 1 FROM profiles WHERE profile_id=OLD.profile_id)"
            if operation == "DELETE" else ""
        )
        db.execute(
            f"CREATE TRIGGER IF NOT EXISTS loop_jobs_no_{operation.lower()} "
            f"BEFORE {operation} ON loop_gate_jobs{guard} BEGIN "
            "SELECT RAISE(ABORT,'gate registrations are operator-owned and immutable'); END"
        )
    fields = tuple(job)
    db.execute(
        f"INSERT INTO loop_gate_jobs ({','.join(fields)}) VALUES ({','.join('?' for _ in fields)})",
        tuple(job.values()),
    )


def register_job(
    db, *, profile_id, task_id, watcher_name, producer, command, cwd, artifact_paths,
    allow_prestart_evidence=False, ttl_seconds=3600,
):
    """Register the operator's current verification job before executing its check.

    artifact_paths must include every task/check input whose change can affect
    the verdict, including file-based check scripts. This operator API is not
    exposed through memory or MCP mutations.
    """
    for value in (profile_id, task_id, watcher_name, producer):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Gate identity fields must be nonempty strings")
    if not isinstance(command, (list, tuple)) or not command or not all(
        isinstance(arg, str) and arg and "\x00" not in arg for arg in command
    ):
        raise ValueError("Gate check must be a nonempty argv sequence")
    if type(allow_prestart_evidence) is not bool or not 0 < float(ttl_seconds) <= 86400:
        raise ValueError("Gate lifetime must be positive and at most one day")
    cwd = str(Path(cwd).resolve())
    artifacts, revision = snapshot(cwd, artifact_paths)
    now, nonce = datetime.now(UTC), uuid.uuid4().hex
    job = dict(
        job_id=nonce, profile_id=profile_id, task_id=task_id, watcher_name=watcher_name,
        run_id=nonce, producer=producer, command_digest=command_digest(command, cwd),
        command_json=json.dumps(list(command)), cwd=cwd, artifacts_json=artifacts,
        revision_digest=revision, registered_at=now.isoformat(),
        expires_at=(now + timedelta(seconds=float(ttl_seconds))).isoformat(),
        allow_prestart_evidence=int(allow_prestart_evidence),
    )
    _store(db, job)
    return job


def current_job(db, job_id, profile_id, watcher_name):
    rows = db.execute(
        "SELECT * FROM loop_gate_jobs WHERE profile_id=? AND watcher_name=? "
        "ORDER BY rowid DESC LIMIT 1", (profile_id, watcher_name),
    )
    if not rows:
        return None
    job = dict(rows[0])
    if job["job_id"] != job_id or datetime.now(UTC) >= datetime.fromisoformat(job["expires_at"]):
        return None
    return job if matches(job) else None


def run_registered_check(db, job_id, *, timeout=30):
    """Execute the registered argv and identity; callers cannot override them."""
    rows = db.execute("SELECT * FROM loop_gate_jobs WHERE job_id=?", (job_id,))
    if not rows:
        raise ValueError("No such operator gate job")
    job = dict(rows[0])
    if not current_job(db, job_id, job["profile_id"], job["watcher_name"]):
        raise ValueError("Gate job expired, superseded or its artifacts changed")
    receipt = run_check(
        db, profile_id=job["profile_id"], task_id=job["task_id"], run_id=job["run_id"],
        producer=job["producer"], command=json.loads(job["command_json"]), cwd=job["cwd"],
        timeout=timeout,
    )
    if not matches(job):
        raise ValueError("Checked artifacts changed during verification")
    return receipt
