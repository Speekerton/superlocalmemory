# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later
"""M057: invalidate temporal slices on source writes, not access accounting.

Dates remain unrestricted TEXT. Non-ISO values (including SQLite's dynamic
``now`` / ``subsec``) keep using the original SQL on every read. The counter
tracks them without rescanning the event table on each recall.
"""

from __future__ import annotations

import sqlite3

NAME = "M057_temporal_retrieval_version"
DB_TARGET = "memory"
#: Additive (a new table, a partial index and triggers). The triggers live in
#: the store, so writes by an older build still bump the version and the slice
#: cache cannot go stale after a downgrade and re-upgrade. Going back to 4.1.18
#: stays possible.
DOWNGRADE_FLOOR = 51


def _unsafe(prefix: str = "") -> str:
    value = f"COALESCE({prefix}referenced_date,{prefix}observation_date,{prefix}interval_start)"
    return (f"CASE WHEN {value} IS NOT NULL AND {value} NOT GLOB "
            "'[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]*' THEN 1 ELSE 0 END")


DDL = f"""
CREATE INDEX IF NOT EXISTS idx_temporal_uncacheable ON temporal_events(event_id)
    WHERE ({_unsafe()})=1;
CREATE TABLE IF NOT EXISTS temporal_retrieval_version (
    id INTEGER PRIMARY KEY CHECK(id=1), version INTEGER NOT NULL,
    uncacheable INTEGER NOT NULL
);
INSERT OR IGNORE INTO temporal_retrieval_version
    SELECT 1,0,COALESCE(SUM({_unsafe()}),0) FROM temporal_events;
CREATE TRIGGER IF NOT EXISTS trg_temporal_slice_insert AFTER INSERT ON temporal_events BEGIN
    UPDATE temporal_retrieval_version SET version=version+1,
        uncacheable=(SELECT COUNT(*) FROM temporal_events WHERE ({_unsafe()})=1) WHERE id=1;
END;
CREATE TRIGGER IF NOT EXISTS trg_temporal_slice_delete AFTER DELETE ON temporal_events BEGIN
    UPDATE temporal_retrieval_version SET version=version+1,
        uncacheable=(SELECT COUNT(*) FROM temporal_events WHERE ({_unsafe()})=1) WHERE id=1;
END;
CREATE TRIGGER IF NOT EXISTS trg_temporal_slice_update AFTER UPDATE ON temporal_events BEGIN
    UPDATE temporal_retrieval_version SET version=version+1,
        uncacheable=(SELECT COUNT(*) FROM temporal_events WHERE ({_unsafe()})=1) WHERE id=1;
END;
CREATE TRIGGER IF NOT EXISTS trg_temporal_slice_fact_delete AFTER DELETE ON atomic_facts BEGIN
    UPDATE temporal_retrieval_version SET version=version+1 WHERE id=1;
END;
CREATE TRIGGER IF NOT EXISTS trg_temporal_slice_fact_insert AFTER INSERT ON atomic_facts BEGIN
    UPDATE temporal_retrieval_version SET version=version+1 WHERE id=1;
END;
CREATE TRIGGER IF NOT EXISTS trg_temporal_slice_fact_update
AFTER UPDATE OF profile_id,scope,shared_with,created_at ON atomic_facts
WHEN NEW.profile_id IS NOT OLD.profile_id OR NEW.scope IS NOT OLD.scope
    OR NEW.shared_with IS NOT OLD.shared_with OR NEW.created_at IS NOT OLD.created_at BEGIN
    UPDATE temporal_retrieval_version SET version=version+1 WHERE id=1;
END;
"""

_TRIGGERS = tuple(f"trg_temporal_slice_{suffix}" for suffix in
                  ("insert", "delete", "update", "fact_delete", "fact_insert", "fact_update"))


def apply(conn: sqlite3.Connection) -> None:
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if {"temporal_events", "atomic_facts"} <= tables:
        statement = ""
        for line in DDL.splitlines(keepends=True):
            statement += line
            if sqlite3.complete_statement(statement):
                conn.execute(statement)
                statement = ""


def verify(conn: sqlite3.Connection) -> bool:
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if not {"temporal_events", "atomic_facts"} <= tables:
        return True
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'")}
    return ("temporal_retrieval_version" in tables and set(_TRIGGERS) <= names
            and bool(conn.execute("SELECT 1 FROM sqlite_master "
                                  "WHERE name='idx_temporal_uncacheable'").fetchone())
            and bool(conn.execute("SELECT 1 FROM temporal_retrieval_version WHERE id=1")
                     .fetchone()))


def repair(conn: sqlite3.Connection) -> None:
    apply(conn)
    exists = conn.execute("SELECT 1 FROM sqlite_master WHERE name='temporal_retrieval_version'")
    if exists.fetchone():
        conn.execute("UPDATE temporal_retrieval_version SET version=version+1,uncacheable="
                     f"(SELECT COALESCE(SUM({_unsafe()}),0) FROM temporal_events) WHERE id=1")
