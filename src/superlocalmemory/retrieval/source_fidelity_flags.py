# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Exclude legacy live-but-marked damage from recall without rewriting storage.

New extraction failures are quarantined before commit. Older live facts must
also stay out of answers when the source check finds damage; they remain in
the read-only fidelity review listing. Explicit user releases are respected.
Kept results retain their order, scores and evidence. No model is called.
"""

from __future__ import annotations

import logging
from typing import Any

from superlocalmemory.core.source_fidelity_guard import FLAGGED_PREFIX, RELEASED_PREFIX
from superlocalmemory.encoding.source_fidelity import check_fact_against_source

logger = logging.getLogger(__name__)


def _unverified(db: Any, profile_id: str, fact_ids: list[str]) -> dict[str, str]:
    marks = ",".join("?" for _ in fact_ids)
    rows = db.execute(
        "SELECT f.fact_id, f.profile_id, f.content, f.observation_date, "
        "m.content AS source, m.speaker, m.role FROM atomic_facts f "
        "JOIN memories m ON m.memory_id = f.memory_id "
        f"WHERE f.fact_id IN ({marks})",
        tuple(fact_ids),
    )
    released = {
        (str(dict(r)["profile_id"]), str(dict(r)["object_id"])) for r in db.execute(
            "SELECT profile_id,object_id FROM derivation_lineage "
            f"WHERE object_type = 'fact' AND object_id IN ({marks}) "
            "AND unresolved_reason LIKE ?",
            (*fact_ids, RELEASED_PREFIX + "%"),
        )
    }
    flags: dict[str, str] = {}
    for row in rows:
        data = dict(row)
        fact_id, fact, source = str(data["fact_id"]), data["content"] or "", data["source"] or ""
        if (str(data["profile_id"]), fact_id) in released or not fact or not source:
            continue
        from superlocalmemory.encoding.speaker_spans import with_actor

        report = check_fact_against_source(
            fact, with_actor(source, data["speaker"] or "", data["role"] or "user"),
            reference_date=data["observation_date"],
        )
        if not report.ok:
            flags[fact_id] = FLAGGED_PREFIX + "+".join(report.reasons)
    return flags


def flag_unverified(results: list, db: Any, profile_id: str) -> list:
    """Keep supported results and user releases; omit known source failures."""
    try:
        fact_ids = [r.fact.fact_id for r in results if getattr(r, "fact", None) is not None]
        if not fact_ids or db is None:
            return results
        flags = _unverified(db, profile_id, fact_ids)
    except Exception as exc:  # noqa: BLE001 - fail open, never cost a recall
        logger.debug("source fidelity flags skipped: %s", type(exc).__name__)
        return results
    if not flags:
        return results
    return [r for r in results
            if getattr(getattr(r, "fact", None), "fact_id", "") not in flags]


__all__ = ["flag_unverified"]
