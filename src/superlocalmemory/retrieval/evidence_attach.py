# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Put each recalled memory's evidence features on it (``evidence_features``).

Reads what recall already has -- the question's vector (cached for this
question), the stored hub baselines and the cross-encoder's raw scores -- plus
the probe vectors when this process has embedded them (``hub_baseline.PROBES``;
never embedded here). A memory the background pass has not reached yet gets its
hub baseline measured on the spot from its own stored vector, so a store that
is still filling in is not judged on raw cosine.

Fail-open: a feature that cannot be computed is recorded as missing, and an
error never reaches the caller. No score or order changes here.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, Sequence
from typing import Any

import numpy as np

from superlocalmemory.retrieval import evidence_features as ef
from superlocalmemory.retrieval import hub_baseline

logger = logging.getLogger(__name__)


def attach(
    query: str,
    results: Sequence[Any],
    *,
    query_vector: Sequence[float] | None,
    ce_scores: Mapping[str, tuple[float, float]],
    stored_baselines: Callable[[list[str]], Mapping[str, tuple[float, float]]],
    probes: np.ndarray | None,
) -> dict:
    """Record every result's features; return the question's own."""
    try:
        terms = ef.query_terms(query)
        rare = ef.rare_terms(terms, ef.model_vocabulary())
        q_evidence = ef.query_evidence(
            query, terms, rare=rare,
            nonsense_similarity=hub_baseline.query_profile(query_vector, probes))
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("query evidence: %s", exc)
        return {}
    if not results:
        return q_evidence
    try:
        stored = stored_baselines([r.fact.fact_id for r in results])
        for r in results:
            raw, norm = ce_scores.get(r.fact.fact_id, (None, None))
            topk, mean = _baseline(r.fact, stored, probes)
            r.evidence = ef.build(
                query=query, terms=terms, query_vector=query_vector, fact=r.fact,
                channel_scores=r.channel_scores, ce_raw=raw, ce_batch_norm=norm,
                hub_baseline=topk, hub_baseline_mean=mean, rare=rare,
            )
    except Exception as exc:
        logger.debug("result evidence: %s", exc)
    return q_evidence


def _baseline(fact: Any, stored: Mapping[str, tuple[float, float]],
              probes: np.ndarray | None) -> tuple[float | None, float | None]:
    found = stored.get(fact.fact_id)
    if found is not None:
        return found
    measured = hub_baseline.baseline_of(getattr(fact, "embedding", None), probes)
    return measured if measured is not None else (None, None)


__all__ = ["attach"]
