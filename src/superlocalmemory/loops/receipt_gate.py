# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later
"""Completion reads only independently executed, append-only receipts.

Neither recall relevance nor provenance attribution establishes independence.
Ordinary remember/metadata writes cannot populate the execution-receipt store.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
from datetime import UTC, datetime


def _time(value):
    dt = datetime.fromisoformat(value)
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt


def _admitted(contract, running_agent):
    if not isinstance(contract, dict):
        return False
    required = (
        "task_id",
        "run_id",
        "producer",
        "min_timestamp",
        "command_digest",
    )
    if any(not isinstance(contract.get(k), str) or not contract[k] for k in required):
        return False
    digest = contract.get("evidence_digest")
    if digest not in (None, "") and (
        not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest)
    ):
        return False
    return contract["producer"] != running_agent and bool(
        re.fullmatch(r"[a-f0-9]{64}", contract["command_digest"])
    )


def _valid(receipt, contract):
    now, minimum = datetime.now(UTC), _time(contract["min_timestamp"])
    return (
        receipt["verdict"] == "PASS"
        and type(receipt["exit_code"]) is int
        and receipt["exit_code"] == 0
        and minimum <= _time(receipt["produced_at"]) <= now
        and hashlib.sha256(receipt["evidence"].encode()).hexdigest() == receipt["evidence_digest"]
        and (
            not contract.get("evidence_digest")
            or receipt["evidence_digest"] == contract["evidence_digest"]
        )
    )


def receipt_passes(engine, results, contract, running_agent):
    """The locator's text and attribution are never execution evidence."""
    if not _admitted(contract, running_agent):
        return False
    fields = ("task_id", "run_id", "producer", "command_digest")
    db = getattr(engine, "_db", None) or engine.db
    try:
        rows = db.execute(
            "SELECT * FROM loop_execution_receipts WHERE profile_id=? AND "
            + " AND ".join(field + "=?" for field in fields)
            + " ORDER BY julianday(produced_at) DESC,rowid DESC LIMIT 1",
            (engine.profile_id, *(contract[field] for field in fields)),
        )
        return any(_valid(dict(row), contract) for row in rows)
    except (sqlite3.Error, ValueError, TypeError, KeyError):
        return False
