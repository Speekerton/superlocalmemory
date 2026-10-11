# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Recall's read-only entity name lookup, without scanning the tables each time.

``EntityResolver.lookup`` (recall only; never saving) found each name in a
question by an exact match, then an alias, then the closest spelling, and each
step scanned a whole table: ``LOWER(canonical_name) = LOWER(?)`` has no index,
and the spelling match read every name and alias and scored them all. On a
22k-fact store that was 46 ms of a recall, every recall.

This keeps those rows in memory per profile while nothing has been committed
to the store (storage/store_signature) and answers the same way:

* exact name and alias keys are lowered the way SQLite's ``LOWER`` does (ASCII
  only), so a name matches here exactly when it matched there;
* a key held by more than one entity is answered by the original query, so
  which row wins never depends on a query plan;
* the spelling match applies a save's merge rules (``entity_match``) to the
  canonical names only (``entity_name_cache``); its answer per name is kept
  while the rows are.

Aliases written by the pre-4.1.25 whole-string fuzzy merge are not loaded:
they may be links of a chain ("Plorth" -> "Plot" -> "Lost").
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

from superlocalmemory.encoding import entity_match as em
from superlocalmemory.storage import store_signature

_ASCII_LOWER = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")

#: The original queries the spelling match ran; their row order is reused.
_NAMES_SQL = "SELECT entity_id, canonical_name FROM canonical_entities WHERE profile_id = ?"
_ALIASES_SQL = ("SELECT ea.entity_id, ea.alias FROM entity_aliases ea "
                "JOIN canonical_entities ce ON ce.entity_id = ea.entity_id "
                "WHERE ce.profile_id = ? AND " + em.trusted_alias_sql("ea.source"))

AMBIGUOUS = object()


def sql_lower(text: str) -> str:
    """SQLite's built-in LOWER(): ASCII letters only."""
    return text.translate(_ASCII_LOWER)


def _keyed(rows: list[tuple[str, str]]) -> dict[str, object]:
    out: dict[str, object] = {}
    for entity_id, text in rows:
        key = sql_lower(text)
        prev = out.get(key)
        if prev is None:
            out[key] = entity_id
        elif prev is not AMBIGUOUS and prev != entity_id:
            out[key] = AMBIGUOUS
    return out


@dataclass
class _Index:
    names: list[tuple[str, str]]
    aliases: list[tuple[str, str]]
    by_name: dict[str, object]
    by_alias: dict[str, object]
    same: dict[str, str | None] = field(default_factory=dict)
    plain: dict[str, str] | None = None


class EntityLookupIndex:
    """Per-profile name rows, valid while the store signature is unchanged."""

    def __init__(self, db: Any) -> None:
        self._db = db
        self._lock = threading.Lock()
        self._parts: dict[str, tuple[Any, _Index]] = {}

    def get(self, profile_id: str) -> _Index | None:
        sig = store_signature.of_db(self._db)
        if sig is None:
            return None
        with self._lock:
            hit = self._parts.get(profile_id)
            if hit is not None and hit[0] == sig:
                return hit[1]
        names = [(str(dict(r)["entity_id"]), str(dict(r)["canonical_name"] or ""))
                 for r in self._db.execute(_NAMES_SQL, (profile_id,))]
        aliases = [(str(dict(r)["entity_id"]), str(dict(r)["alias"] or ""))
                   for r in self._db.execute(_ALIASES_SQL, (profile_id,))]
        index = _Index(names, aliases, _keyed(names), _keyed(aliases))
        with self._lock:
            self._parts[profile_id] = (sig, index)
            while len(self._parts) > 8:  # a few profiles at most
                self._parts.pop(next(iter(self._parts)))
        return index


def plain_word_hit(index: _Index, word: str) -> str | None:
    """A canonical name a lower-case question word spells exactly (case and
    punctuation aside), when such a word may name it at all."""
    if index.plain is None:
        plain: dict[str, str] = {}
        for entity_id, name in index.names:
            if em.plain_word_may_name(name):
                plain.setdefault(em.name_key(name).compact, entity_id)
        index.plain = plain
    key = em.name_key(word).compact
    return index.plain.get(key) if key else None


__all__ = ["AMBIGUOUS", "EntityLookupIndex", "plain_word_hit", "sql_lower"]
