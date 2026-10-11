# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""One cached entity graph for one scope, and the knobs that bound the cache.

Split out of retrieval/entity_channel so the channel, the RCU builder
(retrieval/adjacency_rcu) and the write follower (retrieval/graph_catchup)
share one definition without importing each other.

MEMORY BUDGET
-------------
A slot keeps the walk's array view (retrieval/graph_adjacency) and nothing
else of size: the dict-of-lists adjacency, the per-fact entity lists and the
metrics dicts the loader builds are dropped once the arrays exist. On the
owner's store (25.6k nodes, 611k edges, 3.5k entities) that is about 20 MB of
CSR arrays plus ~8 MB of node and entity maps, ~30 MB a scope, against several
hundred MB when the dict adjacency was kept. ``SLM_ADJ_CACHE_PROFILES`` scopes
(default 3) bound the cache at ~90 MB; a write's delta allocates one more
copy of the arrays for the length of the splice.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


def adj_ttl_seconds() -> float:
    """How old a full graph build may get before one is redone beside recall.

    v3.8.5 raised this from 300 s to 3600 s when the rebuild still ran on a
    recall's clock. It now only ever runs in the background
    (retrieval/graph_catchup.maybe_compact), and only when the store changed
    since the build in a way the change log cannot describe edge by edge
    (pruned or re-weighted links, recomputed PageRank). 0 disables it.
    """
    try:
        return max(0.0, float(os.environ.get("SLM_ENTITY_ADJ_TTL_S", "3600")))
    except (TypeError, ValueError):
        return 3600.0


def adj_cache_profiles() -> int:
    """How many profile scopes the adjacency LRU keeps warm (>= 1).

    Keyed by (profile, include_global, include_shared): each scope is a
    different graph. Read at call time so a test or operator can retune it.
    """
    try:
        return max(1, int(os.environ.get("SLM_ADJ_CACHE_PROFILES", "3")))
    except (TypeError, ValueError):
        return 3


@dataclass(frozen=True)
class AdjSlot:
    """One cached adjacency load for one (profile, include_global, include_shared).

    Immutable: a write produces a NEW slot (retrieval/graph_catchup), so a
    reader holding this one keeps a consistent graph for its whole walk.
    """

    adj: dict[str, list[tuple[str, float]]]
    entity_to_facts: Any  # entity id -> facts (node indices once slimmed)
    fact_to_entities: Any
    visible_fact_ids: Any  # set-like: the snapshot's node ids
    edge_count: int
    fact_count: int
    loaded_at: float
    graph_metrics: dict[str, dict]
    graph_metrics_profile: str
    adjacency_source_name: str
    snapshot: Any  # graph_adjacency view; typed loosely to avoid an import cycle
    #: Change-log head (storage/fact_search_changes) fully applied; None when
    #: the store has no log -- the slot is then rebuilt on any count change.
    seq: int | None = None
    #: Change-log head whose REMOVALS are applied (>= seq). Removals are never
    #: deferred; additions may be, when a backlog is too large for a recall.
    removed_seq: int | None = None
    #: graph_edges rowid up to which new links are applied.
    edge_rowid: int = 0
    #: monotonic time additions were first deferred; None when caught up.
    behind_since: float | None = None
    #: monotonic time of the full build this slot descends from.
    built_at: float = 0.0
    #: Store signature at that build: (log head, edge rowid, graph version).
    built_sig: tuple | None = None
    #: Rows spliced in since that build (bounds duplicate-edge growth).
    spliced: int = 0
    #: Newest fact_importance computed_at at the build, and when it was compared.
    metrics_sig: str | None = None
    metrics_checked_at: float = 0.0
    #: (device, inode) of memory.db at the build: a restored file is a new store.
    store_id: tuple[int, int] | None = None


__all__ = ["AdjSlot", "adj_cache_profiles", "adj_ttl_seconds"]
