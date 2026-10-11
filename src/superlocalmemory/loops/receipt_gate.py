# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later
"""Completion reads only independently executed, append-only receipts.

Neither recall relevance nor provenance attribution establishes independence.
Ordinary remember/metadata writes cannot populate the execution-receipt store.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import UTC, datetime

from superlocalmemory.loops.execution_guard import admission


def _time(value):
    dt = datetime.fromisoformat(value)
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt


def _admitted(contract, running_agent):
    return (
        isinstance(contract, dict) and set(contract) == {"job_id"}
        and isinstance(contract["job_id"], str)
        and bool(re.fullmatch(r"[a-f0-9]{32}", contract["job_id"]))
    )


def _valid(receipt, minimum, job):
    now = datetime.now(UTC)
    evidence = json.loads(receipt["evidence"])
    return (
        receipt["verdict"] == "PASS"
        and type(receipt["exit_code"]) is int
        and receipt["exit_code"] == 0
        and minimum <= _time(receipt["produced_at"]) <= now
        and hashlib.sha256(receipt["evidence"].encode()).hexdigest() == receipt["evidence_digest"]
        and isinstance(evidence, dict)
        and evidence.get("admission") == admission(job)
    )


def receipt_passes(engine, results, contract, running_agent, *, watcher_name="", started_at=None):
    """The locator's text and attribution are never execution evidence."""
    if not _admitted(contract, running_agent):
        return False
    fields = ("task_id", "run_id", "producer", "command_digest")
    db = getattr(engine, "_db", None) or engine.db
    try:
        from superlocalmemory.loops.receipt_jobs import current_job

        job = current_job(db, contract["job_id"], engine.profile_id, watcher_name)
        if job is None or job["producer"] == running_agent:
            return False
        minimum = _time(job["registered_at"])
        if not job["allow_prestart_evidence"]:
            minimum = max(minimum, _time(started_at) if started_at else datetime.now(UTC))
        rows = db.execute(
            "SELECT * FROM loop_execution_receipts WHERE profile_id=? AND "
            + " AND ".join(field + "=?" for field in fields)
            + " AND ?=(SELECT job_id FROM loop_gate_jobs WHERE profile_id=? "
            "AND watcher_name=? ORDER BY rowid DESC LIMIT 1)"
            + " ORDER BY julianday(produced_at) DESC,rowid DESC LIMIT 1",
            (engine.profile_id, *(job[field] for field in fields),
             job["job_id"], engine.profile_id, watcher_name),
        )
        return any(_valid(dict(row), minimum, job) for row in rows) and bool(
            current_job(db, job["job_id"], engine.profile_id, watcher_name)
        )
    except (sqlite3.Error, ValueError, TypeError, KeyError, OSError):
        return False
