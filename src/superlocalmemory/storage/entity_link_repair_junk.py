# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""The entities an entity link repair leaves with no fact, and their removal.

On a clone of the author's store the first repair left thousands of entities
that no fact links to any more: the chained ones it emptied, and old junk
("2026-04-29 16:57", "LIVE", 16-hex fact ids) the new rules never link. An
entity is removed, with its aliases, when after the repair no fact links to
it and either the repair emptied it or its name fails the validity rules
(encoding/entity_validity). Rows derived from the entity alone -- its entity
profile, consolidated summary and community membership -- go with it (on the
clone 2,100 of 2,122 such entities had an entity profile, so keeping every
entity with one kept nearly all the junk). One that something not derived
from it still names -- a temporal event of a fact the repair does not
relink, a scene, a community summary -- is kept and counted. Every row
removed goes to the run's undo record first.
"""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING

from superlocalmemory.encoding.entity_validity import valid_name

if TYPE_CHECKING:
    from superlocalmemory.storage.entity_link_repair import ProfilePlan

#: Tables whose rows name an entity by id (column) or in a JSON list (True);
#: such a row keeps the entity.
_REFERENCES: tuple[tuple[str, str, bool], ...] = (
    ("memory_scenes", "entity_ids_json", True),
    ("community_summaries", "entity_ids_json", True),
)
#: Rows derived from one entity alone: removed with it (undo record kept).
_DERIVED = ("entity_profiles", "consolidated_summaries", "entity_communities",
            "fact_entity_associations", "entity_aliases")


def _table(conn: sqlite3.Connection, name: str) -> bool:
    return bool(conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                             (name,)).fetchone())


def _ids(raw: object) -> list[str]:
    try:
        values = json.loads(str(raw or "[]"))
    except (TypeError, ValueError):
        return []
    return [str(v) for v in values if v] if isinstance(values, list) else []


def _referenced(conn: sqlite3.Connection, profile_id: str, relinked: set[str]) -> set[str]:
    """Entity ids something other than the facts' links still names."""
    out: set[str] = set()
    for table, column, is_json in _REFERENCES:
        if not _table(conn, table):
            continue
        cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
        where = " WHERE profile_id = ?" if "profile_id" in cols else ""
        args = (profile_id,) if where else ()
        for (value,) in conn.execute(f"SELECT {column} FROM {table}{where}", args):
            out.update(_ids(value) if is_json else [str(value)])
    if _table(conn, "temporal_events"):
        for entity_id, fact_id in conn.execute(
                "SELECT entity_id, fact_id FROM temporal_events WHERE profile_id = ?",
                (profile_id,)):
            if str(fact_id) not in relinked:  # a relinked fact's events are moved
                out.add(str(entity_id))
    return out


def plan_junk(conn: sqlite3.Connection, plan: ProfilePlan,
              entities: list[tuple[str, str]]) -> None:
    """Fill ``plan.junk`` and ``plan.junk_kept_referenced`` (read-only)."""
    old_of = {f.fact_id: _ids(f.old_json) for f in plan.facts}
    before: dict[str, int] = {}
    after: dict[str, int] = {}
    for fact_id, links in plan.links.items():
        for entity_id in set(old_of.get(fact_id, links)):
            before[entity_id] = before.get(entity_id, 0) + 1
        for entity_id in set(links):
            after[entity_id] = after.get(entity_id, 0) + 1
    candidates = [e for e, name in entities
                  if not after.get(e) and (before.get(e) or not valid_name(name))]
    if not candidates:
        return
    referenced = _referenced(conn, plan.profile_id, set(old_of))
    plan.junk = [e for e in candidates if e not in referenced]
    plan.junk_kept_referenced = len(candidates) - len(plan.junk)


def remove_junk(conn: sqlite3.Connection, plan: ProfilePlan, undo) -> int:
    """Delete the planned junk entities and their aliases, undo record first."""
    if not plan.junk:
        return 0
    from superlocalmemory.storage.entity_link_repair_apply import _chunks, _select

    entities = _select(conn, "canonical_entities", "entity_id IN ({marks})", plan.junk)
    undo.put(plan.profile_id, "junk_entities", entities)
    for table in _DERIVED:
        if _table(conn, table):
            rows = _select(conn, table, "entity_id IN ({marks})", plan.junk)
            undo.put(plan.profile_id, f"junk_rows:{table}", rows)
    removed = 0
    for part in _chunks(plan.junk):
        marks = ",".join("?" * len(part))
        for table in _DERIVED:
            if _table(conn, table):
                conn.execute(f"DELETE FROM {table} WHERE entity_id IN ({marks})", part)
        removed += conn.execute(f"DELETE FROM canonical_entities WHERE entity_id IN ({marks})",
                                part).rowcount
    return removed


def restore_junk(conn: sqlite3.Connection, parts: dict[str, list]) -> int:
    """Undo: put the removed entities and the rows removed with them back."""
    kinds = [("junk_entities", "canonical_entities")] + [
        (f"junk_rows:{t}", t) for t in _DERIVED] + [("junk_aliases", "entity_aliases")]
    restored = 0
    for kind, table in kinds:
        rows = [row for _p, row in parts.get(kind, [])]
        for row in rows:
            cols = list(row)
            n = conn.execute(f"INSERT OR IGNORE INTO {table} ({','.join(cols)}) VALUES "
                             f"({','.join('?' * len(cols))})", tuple(row.values())).rowcount
            restored += n if table == "canonical_entities" else 0
    return restored


def unproject(entity_ids: list[str]) -> None:
    """Drop removed entities from the graph projection, best effort (the
    daemon's projection only; nothing to do when SLM is not running)."""
    from superlocalmemory.encoding.entity_resolver import _unproject_entity

    for entity_id in entity_ids:
        _unproject_entity(entity_id)


__all__ = ["plan_junk", "remove_junk", "restore_junk", "unproject"]
