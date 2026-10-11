# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""SuperLocalMemory V3 — Entity Resolution.

Maps variant mentions ("Alice", "Ms. Smith", "she") to canonical entities.
Persists ALL resolution results to DB — the #1 fix from the V1 audit where
entity resolution ran but results were silently discarded.

Tiers, strongest evidence first (rules and their sources: entity_match.py):
  a) Exact match in canonical_entities (case-insensitive)
  b) Trusted alias match in entity_aliases (case-insensitive)
  c) The same name once normalized, or one typo in one word, compared with
     canonical names only -- never with aliases, so merges cannot chain
  d) Mode B/C only: a borderline pair the local model confirms
Before 4.1.25 tier (c) was whole-string Jaro-Winkler >= 0.85 against names and
aliases alike; its aliases (source 'jaro_winkler') are no longer trusted.

Part of Qualixar | Author: Varun Pratap Bhardwaj
License: AGPL-3.0-or-later
"""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING

from superlocalmemory.encoding import entity_match as em
from superlocalmemory.encoding.entity_mentions import STOP_WORDS
from superlocalmemory.encoding.entity_name_cache import CanonicalNames
from superlocalmemory.storage.models import CanonicalEntity, EntityAlias, _new_id, _now

if TYPE_CHECKING:
    from superlocalmemory.llm.backbone import LLMBackbone
    from superlocalmemory.storage.database import DatabaseManager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Kept for callers that still read them; no merge decision uses them since
# 4.1.25 (a whole-string score cannot see a differing version or word).
JARO_WINKLER_AUTO_MERGE: float = 0.85
JARO_WINKLER_LLM_FLOOR: float = 0.70
PRONOUNS: frozenset[str] = frozenset({
    "he", "she", "they", "him", "her", "them", "his", "hers", "their",
    "himself", "herself", "themselves", "it", "its", "i", "me", "my",
    "we", "us", "our", "you", "your",
})

# Heuristic entity type patterns
_ORG_MARKERS = ("Inc", "Corp", "LLC", "Ltd", "University", "Hospital", "Bank",
                "Foundation", "Institute", "Company", "Group", "Agency")
_PLACE_MARKERS = ("City", "State", "County", "Island", "River", "Mountain",
                  "Lake", "Park", "Street", "Avenue", "Road", "District")
_EVENT_MARKERS = ("Festival", "Conference", "Summit", "Workshop", "Meeting",
                  "Election", "War", "Match", "Game", "Concert", "Wedding")
# v3.4.10: Skill entity type — skills, commands, agents, plugins
_SKILL_MARKERS_RE = re.compile(r'\b(?:skill|command|agent|plugin|hook|mcp)\b', re.IGNORECASE)
_SKILL_NAMESPACE_RE = re.compile(r"^[\w-]+:[\w-]+$")  # e.g., "superpowers:brainstorming"


# ---------------------------------------------------------------------------
# Jaro-Winkler similarity — pure Python fallback
# ---------------------------------------------------------------------------

def jaro_winkler(s1: str, s2: str, prefix_weight: float = 0.1) -> float:
    """Jaro-Winkler similarity in [0, 1]. 1 = identical.

    Pure Python implementation. Capped at 200 chars for O(n^2) safety.
    """
    s1, s2 = s1[:200], s2[:200]
    if not s1 or not s2:
        return 0.0
    if s1 == s2:
        return 1.0

    len1, len2 = len(s1), len(s2)
    match_dist = max(len1, len2) // 2 - 1
    if match_dist < 0:
        match_dist = 0

    s1_matched = [False] * len1
    s2_matched = [False] * len2
    matches = transpositions = 0

    for i in range(len1):
        lo = max(0, i - match_dist)
        hi = min(i + match_dist + 1, len2)
        for j in range(lo, hi):
            if s2_matched[j] or s1[i] != s2[j]:
                continue
            s1_matched[i] = s2_matched[j] = True
            matches += 1
            break

    if matches == 0:
        return 0.0

    k = 0
    for i in range(len1):
        if not s1_matched[i]:
            continue
        while not s2_matched[k]:
            k += 1
        if s1[i] != s2[k]:
            transpositions += 1
        k += 1

    jaro = (
        matches / len1 + matches / len2
        + (matches - transpositions / 2) / matches
    ) / 3.0

    prefix = sum(
        1 for i in range(min(4, len1, len2)) if s1[i] == s2[i]
    )
    return jaro + prefix * prefix_weight * (1.0 - jaro)


_COMMON_WORDS = frozenset({
    # Months / time words (biggest source of garbage entities)
    "january", "february", "march", "april", "may", "june", "july",
    "august", "september", "october", "november", "december",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "today", "tomorrow", "yesterday", "morning", "evening", "night",
    # English stop words that get capitalized at sentence start
    "a", "an", "the", "all", "not", "no", "yes", "and", "or", "but",
    "if", "is", "are", "was", "were", "be", "been", "being", "have",
    "has", "had", "do", "does", "did", "will", "would", "shall", "should",
    "can", "could", "just", "also", "only", "very", "too", "so", "then",
    "than", "that", "this", "these", "those", "here", "there", "where",
    "when", "what", "which", "who", "whom", "how", "why", "each", "every",
    "both", "few", "more", "most", "other", "some", "such", "any", "many",
    "much", "own", "same", "new", "old", "first", "last", "next", "now",
    "still", "already", "always", "never", "often", "sometimes", "about",
    "above", "after", "again", "against", "along", "among", "around",
    "before", "below", "between", "beyond", "during", "except", "from",
    "into", "near", "off", "onto", "out", "over", "past", "since",
    "through", "under", "until", "upon", "with", "within", "without",
    # Technical stop words (common in dev sessions)
    "phase", "test", "gap", "dashboard", "remaining", "session", "results",
    "tools", "projects", "prompts", "integration", "cli", "engagement",
    "mode", "error", "step", "fix", "build", "check", "run", "start",
    "stop", "config", "status", "version", "query", "data", "file", "path",
    "node", "edge", "table", "index", "schema", "model", "type", "class",
    "function", "module", "package", "import", "export", "default", "pattern",
    "memory", "profile", "context", "pipeline", "worker", "daemon",
    "server", "client", "route", "endpoint", "handler", "hook",
    "feature", "release", "update", "upgrade", "deploy", "debug", "log",
    "output", "input", "key", "value", "true", "false", "null", "none",
    "ready", "done", "todo", "complete", "pending", "active", "failed",
    "success", "warning", "critical", "high", "medium", "low",
    "total", "count", "list", "item", "entry", "record", "row", "column",
    "source", "target", "origin", "destination", "backup", "restore",
    "create", "read", "delete", "remove", "add", "set", "get", "put",
    "push", "pull", "fetch", "send", "receive", "request", "response",
    "enable", "disable", "open", "close", "load", "save", "reset",
    # Abstract nouns often misclassified as people
    "completeness", "correctness", "limitations", "requirements",
    "dependencies", "performance", "security", "quality", "coverage",
    "progress", "analysis", "research", "implementation", "verification",
    "overview", "summary", "details", "notes", "changes", "issues",
    "approach", "strategy", "solution", "problem", "question", "answer",
})


def _guess_entity_type(name: str) -> str:
    """Heuristic entity type classification from name string.

    v3.4.10: Aggressive false-positive prevention. "person" is assigned ONLY
    when the name looks like a real human name (2-3 capitalized words, none
    in the stop list). Everything else defaults to "concept".
    """
    # Reject very short or very long names
    if len(name) <= 2 or len(name) > 100:
        return "concept"

    # Reject pure numbers, dates, version strings
    if re.match(r"^[\d.v\-/]+$", name):
        return "concept"

    if any(m in name for m in _ORG_MARKERS):
        return "organization"
    if any(m in name for m in _PLACE_MARKERS):
        return "place"
    if any(m in name for m in _EVENT_MARKERS):
        return "event"

    # v3.4.10: Skill entities — namespaced skills always skill type
    if _SKILL_NAMESPACE_RE.match(name):
        return "skill"

    # Check ALL words against the stop list (not just the full name)
    words = name.lower().split()
    if any(w in _COMMON_WORDS for w in words):
        return "concept"

    # v3.4.10: Skill entities — word-boundary match AFTER common-word filter
    if _SKILL_MARKERS_RE.search(name):
        return "skill"

    # Multi-word entity: "person" only if 2-3 capitalized words, no stop words
    if re.match(r"^[A-Z][a-z]+ [A-Z][a-z]+( [A-Z][a-z]+)?$", name):
        if not any(p in _COMMON_WORDS for p in words):
            return "person"

    # Single capitalized word — almost never a person in our context
    # Only known first names should get "person" but we can't maintain
    # a name dictionary, so default to "concept"
    if re.match(r"^[A-Z][a-z]+$", name):
        return "concept"

    # Contains dots/slashes/hyphens/underscores = technical term
    if re.search(r"[./\-_]", name):
        return "concept"

    # ALL-CAPS or mixed case with numbers = technical/concept
    if re.match(r"^[A-Z]+$", name) or re.search(r"\d", name):
        return "concept"

    return "concept"


# ---------------------------------------------------------------------------
# Entity Resolver
# ---------------------------------------------------------------------------

def _unproject_entity(entity_id: str) -> bool:
    """Remove an entity node from the graph projection, if there is one.

    The projection is a separate storage engine, so deleting the row from
    SQLite reaches nothing there. An entity node left behind still carries the
    name it was created with, which is exactly the thing an erasure was asked
    to remove.

    Returns False when a projection exists and refused, so a caller that
    reports completeness can report this honestly. No projection at all is not
    a failure -- there is nothing to remove.
    """
    try:
        from superlocalmemory.core.backend_orchestrator import get_orchestrator
    except Exception:  # noqa: BLE001
        return True
    try:
        orchestrator = get_orchestrator()
        graph = orchestrator.get_graph_backend() if orchestrator else None
        if graph is None:
            return True
        remove = getattr(graph, "remove_entity", None)
        if remove is None:
            return True
        remove(entity_id)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "the graph projection still holds entity %s (%s)", entity_id[:12], exc,
        )
        return False


def _usable_mention(raw: str) -> str | None:
    """The mention as a name worth resolving, or None for pronouns, stop
    words, numbers and fragments too short or long to be a name."""
    name = raw.strip()
    if not name or name.lower() in PRONOUNS:
        return None
    if len(name) <= 2 or len(name) > 100:
        return None
    words = name.lower().split()
    if len(words) == 1 and (name.lower() in _COMMON_WORDS or name.lower() in STOP_WORDS):
        return None
    if len(words) > 1 and all(w in _COMMON_WORDS or len(w) <= 2 for w in words):
        return None
    if re.match(r"^[\d.v\-/]+$", name):
        return None
    return name


class EntityResolver:
    """Resolves raw entity mentions to persisted canonical entities.

    Every resolution is persisted — canonical entities and aliases are stored
    immediately, ensuring downstream graph building and retrieval use the
    resolved identities.
    """

    def __init__(
        self,
        db: DatabaseManager,
        llm: LLMBackbone | None = None,
    ) -> None:
        self._db = db
        self._llm = llm
        self._names = CanonicalNames(db)

    # -- Public API ---------------------------------------------------------

    def resolve(
        self,
        raw_entities: list[str],
        profile_id: str,
    ) -> dict[str, str]:
        """Resolve raw mentions to canonical entity IDs, for a save.

        Returns mapping: raw_name -> canonical entity_id. Tiers, strongest
        evidence first (``entity_match`` has the rules and their sources):
        exact name, a trusted alias, the same name once normalized, a typo of
        one word of a canonical name; in Mode B/C a borderline pair confirmed
        by the model. Anything else is a new entity. All new entities and
        aliases are persisted before returning.
        """
        if not raw_entities:
            return {}
        resolution: dict[str, str] = {}
        pending: list[tuple[str, str, str, str]] = []
        for raw in raw_entities:
            name = _usable_mention(raw)
            if name is None:
                continue
            entity_id = self._exact(name, profile_id)
            if entity_id is None:
                verdict, match_id, canonical, why = self._names.best(name, profile_id)
                if verdict == em.SAME and match_id:
                    entity_id = match_id
                    self._persist_alias(entity_id, name, 1.0 if why == "normalized" else 0.9,
                                        why, profile_id)
                elif verdict == em.BORDERLINE and self._llm is not None and match_id:
                    pending.append((raw, name, match_id, canonical))
                    continue
            if entity_id is not None:
                self._touch_last_seen(entity_id, profile_id)
                resolution[raw] = entity_id
                continue
            resolution[raw] = self._create_entity(name, profile_id)
        if pending:
            resolution.update(self._confirm(pending, profile_id))
        return resolution

    def _exact(self, name: str, profile_id: str) -> str | None:
        """The entity with this exact name, or a trusted alias of it."""
        entity = self._db.get_entity_by_name(name, profile_id)
        if entity is not None:
            return entity.entity_id
        return self._alias_lookup(name, profile_id)

    def _confirm(self, pending: list[tuple[str, str, str, str]],
                 profile_id: str) -> dict[str, str]:
        """Mode B/C: the model's yes merges a borderline pair; no creates."""
        from superlocalmemory.encoding.entity_confirm import confirm_pairs

        answers = confirm_pairs(self._llm, [(name, canonical)
                                            for _r, name, _e, canonical in pending])
        out: dict[str, str] = {}
        for (raw, name, entity_id, _canonical), same in zip(pending, answers):
            if same:
                self._persist_alias(entity_id, name, 0.9, "llm_confirmed", profile_id)
                self._touch_last_seen(entity_id, profile_id)
                out[raw] = entity_id
            else:
                existing = self._db.get_entity_by_name(name, profile_id)
                out[raw] = (existing.entity_id if existing is not None
                            else self._create_entity(name, profile_id))
        return out

    def lookup(
        self,
        raw_entities: list[str],
        profile_id: str,
    ) -> dict[str, str]:
        """Known entities named in a question, read-only.

        For recall. Finds a name by exact match, a trusted alias, or the same
        rules a save merges by (never a borderline pair, never an alias made
        by the old whole-string rule). Never creates an entity, saves an
        alias, updates last-seen, or asks the language model: a question must
        not change the store, and a model call here would spend the recall
        budget. A name that is unknown, or only uncertainly close, is left out.
        """
        found: dict[str, str] = {}
        index = self._lookup_rows(profile_id)
        for raw in raw_entities or ():
            name = _usable_mention(raw)
            if name is None:
                continue
            entity_id = self._lookup_one(name, profile_id, index)
            if entity_id is not None:
                found[raw] = entity_id
        return found

    def lookup_plain_words(self, words: list[str], profile_id: str) -> dict[str, str]:
        """Entities a lower-case question word names exactly (no spelling
        rules): see ``entity_match.plain_word_may_name``. Read-only."""
        from superlocalmemory.encoding import entity_lookup_index as eli

        index = self._lookup_rows(profile_id)
        found: dict[str, str] = {}
        for word in words or ():
            name = _usable_mention(word)
            if name is None:
                continue
            hit = eli.plain_word_hit(index, name) if index is not None else None
            if hit is None and index is None:
                entity = self._db.get_entity_by_name(name, profile_id)
                ok = entity is not None and em.plain_word_may_name(entity.canonical_name)
                hit = entity.entity_id if ok else None
            if hit is not None:
                found[word] = str(hit)
        return found

    def _lookup_rows(self, profile_id: str):
        """The kept name rows (encoding/entity_lookup_index), or None."""
        from superlocalmemory.encoding import entity_lookup_index as eli

        holder = self.__dict__.get("_lookup_index")
        if holder is None:
            holder = self.__dict__.setdefault("_lookup_index", eli.EntityLookupIndex(self._db))
        try:
            return holder.get(profile_id)
        except Exception as exc:  # noqa: BLE001 -- the original queries still answer
            logger.debug("entity lookup index unavailable: %s", exc)
            return None

    def _lookup_one(self, name: str, profile_id: str, index) -> str | None:
        """Exact name, then a trusted alias, then a save's merge rules."""
        from superlocalmemory.encoding import entity_lookup_index as eli

        key = eli.sql_lower(name)
        hit = index.by_name.get(key) if index is not None else eli.AMBIGUOUS
        if hit is eli.AMBIGUOUS:
            entity = self._db.get_entity_by_name(name, profile_id)
            hit = entity.entity_id if entity is not None else None
        if hit is not None:
            return str(hit)
        hit = index.by_alias.get(key) if index is not None else eli.AMBIGUOUS
        if hit is eli.AMBIGUOUS:
            hit = self._alias_lookup(name, profile_id)
        if hit is not None:
            return str(hit)
        if index is not None and name in index.same:
            return index.same[name]
        verdict, entity_id, _c, _w = self._names.best(name, profile_id)
        hit = entity_id if verdict == em.SAME else None
        if index is not None:
            index.same[name] = hit
        return hit

    def create_speaker_entities(
        self,
        speaker_a: str,
        speaker_b: str,
        profile_id: str,
    ) -> None:
        """Pre-create canonical entities for conversation speakers.

        Called at session start so that speaker names are immediately
        resolvable during fact extraction. Fixes B03 (speaker entities
        not available during first-turn encoding).
        """
        for speaker in (speaker_a, speaker_b):
            name = speaker.strip()
            if not name or name.lower() in PRONOUNS:
                continue
            existing = self._db.get_entity_by_name(name, profile_id)
            if existing is None:
                self._create_entity(name, profile_id, entity_type="person")

    def get_canonical_name(self, raw_name: str, profile_id: str) -> str:
        """Quick lookup: returns canonical name or original if not found."""
        name = raw_name.strip()
        if not name:
            return raw_name

        entity = self._db.get_entity_by_name(name, profile_id)
        if entity is not None:
            return entity.canonical_name

        entity_id = self._alias_lookup(name, profile_id)
        if entity_id is not None:
            rows = self._db.execute(
                "SELECT canonical_name FROM canonical_entities WHERE entity_id = ?",
                (entity_id,),
            )
            if rows:
                return str(dict(rows[0])["canonical_name"])

        return raw_name

    def merge_entities(
        self,
        entity_id_keep: str,
        entity_id_merge: str,
        profile_id: str,
    ) -> None:
        """Merge two entities: move all aliases and facts to keep, delete merge.

        Reassigns aliases, updates canonical_entities_json in atomic_facts,
        and removes the merged entity record.
        """
        # Move aliases from merge -> keep
        aliases = self._db.get_aliases_for_entity(entity_id_merge, profile_id)
        for alias in aliases:
            new_alias = EntityAlias(
                alias_id=_new_id(),
                entity_id=entity_id_keep,
                alias=alias.alias,
                confidence=alias.confidence,
                source=f"merge_from:{entity_id_merge}",
            )
            self._db.store_alias(new_alias, profile_id)

        # Also add the merged entity's canonical name as an alias of keep
        rows = self._db.execute(
            "SELECT canonical_name FROM canonical_entities WHERE entity_id = ?",
            (entity_id_merge,),
        )
        if rows:
            merged_name = str(dict(rows[0])["canonical_name"])
            self._persist_alias(entity_id_keep, merged_name, 1.0, "merge", profile_id)

        # Update atomic_facts: replace entity_id_merge with entity_id_keep
        # in canonical_entities_json column
        fact_rows = self._db.execute(
            "SELECT fact_id, canonical_entities_json FROM atomic_facts "
            "WHERE profile_id = ? AND canonical_entities_json LIKE ?",
            (profile_id, f'%"{entity_id_merge}"%'),
        )
        for row in fact_rows:
            d = dict(row)
            try:
                entities = json.loads(d["canonical_entities_json"])
                updated = [
                    entity_id_keep if eid == entity_id_merge else eid
                    for eid in entities
                ]
                # Deduplicate while preserving order
                seen: set[str] = set()
                deduped = []
                for eid in updated:
                    if eid not in seen:
                        seen.add(eid)
                        deduped.append(eid)
                self._db.execute(
                    "UPDATE atomic_facts SET canonical_entities_json = ? "
                    "WHERE fact_id = ?",
                    (json.dumps(deduped), d["fact_id"]),
                )
                # The fact now names the kept entity; index it under that id
                # (storage/entity_index.py). The merged id's rows go with the
                # entity row below, by its foreign key.
                from superlocalmemory.storage.entity_index import (
                    record_fact_entities,
                )

                record_fact_entities(
                    self._db, d["fact_id"], profile_id, [entity_id_keep],
                )
            except (json.JSONDecodeError, TypeError):
                continue

        # Delete the merged entity (tenant-scoped)
        self._db.execute(
            "DELETE FROM entity_aliases WHERE entity_id = ? AND profile_id = ?",
            (entity_id_merge, profile_id),
        )
        self._db.execute(
            "DELETE FROM canonical_entities WHERE entity_id = ? AND profile_id = ?",
            (entity_id_merge, profile_id),
        )
        # The merged-away node has its own copy in the graph projection, and
        # deleting the row above does not reach it. Left there it keeps its own
        # name and its own edges, so the two halves of a merged entity stay
        # visible to a graph query as two entities.
        _unproject_entity(entity_id_merge)
        logger.info(
            "Merged entity %s into %s (profile=%s)",
            entity_id_merge, entity_id_keep, profile_id,
        )

    # -- Internal: lookups --------------------------------------------------

    def _alias_lookup(self, name: str, profile_id: str) -> str | None:
        """Look up entity_id via a trusted alias (case-insensitive)."""
        rows = self._db.execute(
            "SELECT ea.entity_id FROM entity_aliases ea "
            "JOIN canonical_entities ce ON ce.entity_id = ea.entity_id "
            "WHERE LOWER(ea.alias) = LOWER(?) AND ce.profile_id = ? AND "
            + em.trusted_alias_sql("ea.source"),
            (name, profile_id),
        )
        if rows:
            return str(dict(rows[0])["entity_id"])
        return None

    # -- Internal: persistence ----------------------------------------------

    def _create_entity(
        self,
        name: str,
        profile_id: str,
        entity_type: str | None = None,
    ) -> str:
        """Create a new canonical entity + self-alias. Returns entity_id."""
        etype = entity_type or _guess_entity_type(name)
        now = _now()
        entity = CanonicalEntity(
            entity_id=_new_id(),
            profile_id=profile_id,
            canonical_name=name,
            entity_type=etype,
            first_seen=now,
            last_seen=now,
            fact_count=0,
        )
        self._db.store_entity(entity)

        # Store name as its own alias for uniform lookup
        self._persist_alias(entity.entity_id, name, 1.0, "canonical", profile_id)
        self._names.added(profile_id, entity.entity_id, name)

        logger.debug(
            "Created entity '%s' [%s] (type=%s, profile=%s)",
            name, entity.entity_id, etype, profile_id,
        )
        return entity.entity_id

    def _persist_alias(
        self,
        entity_id: str,
        alias_text: str,
        confidence: float,
        source: str,
        profile_id: str,
    ) -> None:
        """Store an alias under a profile, skipping duplicates within it."""
        # Check if alias already exists for this entity IN THIS PROFILE. The
        # dedup must be profile-scoped or one profile's alias suppresses
        # another profile's identical alias for a same-id entity.
        existing = self._db.execute(
            "SELECT alias_id FROM entity_aliases "
            "WHERE entity_id = ? AND profile_id = ? AND LOWER(alias) = LOWER(?)",
            (entity_id, profile_id, alias_text),
        )
        if existing:
            return
        alias = EntityAlias(
            alias_id=_new_id(),
            entity_id=entity_id,
            alias=alias_text,
            confidence=confidence,
            source=source,
        )
        self._db.store_alias(alias, profile_id)

    def _touch_last_seen(self, entity_id: str, profile_id: str = "default") -> None:
        """Record a last_seen touch (DEFERRED, non-blocking).

        last_seen is dashboard-only bookkeeping (entities/graph "last seen"
        columns); it never feeds recall ranking.  Writing it INLINE made recall
        a WRITER that waited on the global write lock — the root of the
        "recall is 8 s" regression.  We now record it in memory and flush from a
        single background thread in coalesced batches, so recall stays
        READ-ONLY on its hot path.  The dashboard stays correct within the flush
        interval (~2 s).  The profile_id guard (L-01) is preserved in the
        deferred UPDATE (see storage/deferred_writes.py).
        """
        try:
            from superlocalmemory.storage.deferred_writes import (
                get_deferred_last_seen,
            )
            get_deferred_last_seen(self._db).touch(entity_id, profile_id, _now())
        except Exception:
            # Bookkeeping must never break entity resolution.
            pass
