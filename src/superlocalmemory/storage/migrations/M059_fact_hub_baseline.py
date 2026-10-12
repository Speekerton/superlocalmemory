# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later
"""M059: each fact's hub baseline, for recall that knows when it doesn't know.

One new table (``retrieval/hub_baseline.py``): a fact's mean cosine against a
fixed, versioned set of probe queries, in the embedding space it was measured
in. Rows are filled by a bounded, resumable background pass and at save time;
recall only reads them. Ids and numbers, never memory text. A trigger removes a
fact's row when the fact is deleted, so erasure leaves nothing behind.
"""

from __future__ import annotations

import sqlite3

NAME = "M059_fact_hub_baseline"
DB_TARGET = "memory"
#: Additive (one new table and one trigger on delete; an older build never
#: reads the table, and the trigger touches only that table), so going back to
#: 4.1.18 stays possible.
DOWNGRADE_FLOOR = 51
DDL = """
CREATE TABLE IF NOT EXISTS fact_hub_baseline (
    fact_id       TEXT PRIMARY KEY,
    profile_id    TEXT NOT NULL,
    space         TEXT NOT NULL,
    probe_version TEXT NOT NULL,
    baseline_mean REAL NOT NULL,
    baseline_topk REAL NOT NULL,
    computed_at   REAL NOT NULL
);
CREATE TRIGGER IF NOT EXISTS trg_hub_baseline_fact_erased
AFTER DELETE ON atomic_facts
BEGIN
    DELETE FROM fact_hub_baseline WHERE fact_id = OLD.fact_id;
END;
"""


def _has_facts(conn: sqlite3.Connection) -> bool:
    return bool(conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='atomic_facts'").fetchone())


_TABLE, _TRIGGER = (part.strip() for part in DDL.split("CREATE TRIGGER", 1))


def apply(conn: sqlite3.Connection) -> None:
    conn.execute(_TABLE.rstrip(";"))
    if _has_facts(conn):  # the trigger needs the table it watches
        conn.execute("CREATE TRIGGER " + _TRIGGER)


def verify(conn: sqlite3.Connection) -> bool:
    names = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE name IN "
        "('fact_hub_baseline', 'trg_hub_baseline_fact_erased')")}
    return "fact_hub_baseline" in names and (
        not _has_facts(conn) or "trg_hub_baseline_fact_erased" in names)


def repair(conn: sqlite3.Connection) -> None:
    apply(conn)
