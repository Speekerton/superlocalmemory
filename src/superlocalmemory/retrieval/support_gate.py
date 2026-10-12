# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Does anything in memory support this question? One decision, every signal.

WHY
---
Recall used to decide "answer or abstain" on one signal, the raw cosine at the
evidence floor, and memories made mostly of ids and hashes sit close to every
question in the embedding space, so random text "found" them. The stronger
signals were computed and then thrown away. Here each recalled memory gets one
number -- the probability that it answers the question -- from all of them
(``support_recipe.FEATURES``), and recall answers only when at least one memory
reaches the recipe's threshold.

Per memory, not per question: the evidence that a memory answers has to come
from one memory. "v0.3.4 snazzle" finds the v0.3.4 note by its keyword and a
hub stub by its cosine; neither memory alone supports the whole question.

Deterministic and readable: a weighted sum and a logistic, with every number in
``support_recipe``. Pure: no I/O, no model call. Callers decide what to do with
the verdict (``core/score_contract.py``).
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from superlocalmemory.retrieval import support_recipe as sr

REASON_UNSUPPORTED = "unsupported"
REASON_NO_RESULTS = "no_results"
#: What a person reads when recall abstains.
ABSTAIN_NOTE = "Nothing in memory supports this question."


@dataclass(frozen=True)
class Assessment:
    supported: bool
    best: float | None
    threshold: float
    probabilities: tuple[float, ...]
    version: str
    reason: str | None
    #: Inputs that were imputed for at least one memory (a cold model, a store
    #: still filling in its baselines): the verdict is weaker, and says so.
    imputed: tuple[str, ...] = ()


def _num(value: Any) -> float | None:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)) and math.isfinite(value):
        return float(value)
    return None


def imputed(evidence: Mapping[str, Any], query_evidence: Mapping[str, Any]) -> tuple[str, ...]:
    """The recipe inputs that had no measurement for this memory."""
    out = []
    if _num(evidence.get("hub_corrected")) is None:
        out.append("hub_corrected")
    if _num(evidence.get("ce_raw")) is None or not query_evidence.get("latin_script", True):
        out.append("cross_encoder")
    if _num(query_evidence.get("nonsense_similarity")) is None:
        out.append("nonsense_similarity")
    return tuple(out)


def features(evidence: Mapping[str, Any], query_evidence: Mapping[str, Any],
             recipe: sr.SupportRecipe = sr.ACTIVE) -> dict[str, float]:
    """The recipe's inputs for one memory, with documented imputations."""
    hub = _num(evidence.get("hub_corrected"))
    if hub is None:
        cos = _num(evidence.get("cosine"))
        hub = (cos if cos is not None else 0.0) - recipe.hub_missing_baseline
    ce = _num(evidence.get("ce_raw"))
    if ce is None or not query_evidence.get("latin_script", True):
        ce = recipe.ce_missing
    lo, hi = recipe.ce_clip
    profile = _num(query_evidence.get("nonsense_similarity"))
    return {
        "hub_corrected": hub,
        "keyword_coverage": _num(evidence.get("keyword_coverage")) or 0.0,
        "cross_encoder": min(hi, max(lo, ce)),
        "log_bm25": math.log1p(max(0.0, _num(evidence.get("bm25_raw")) or 0.0)),
        "entity_hit": _num(evidence.get("entity_hit")) or 0.0,
        "oov_phrase": _num(query_evidence.get("oov_phrase")) or 0.0,
        "rare_miss": _num(evidence.get("rare_miss")) or 0.0,
        "nonsense_similarity": (profile if profile is not None
                                else recipe.nonsense_similarity_missing),
    }


def logit(evidence: Mapping[str, Any], query_evidence: Mapping[str, Any],
          recipe: sr.SupportRecipe = sr.ACTIVE, *, verdict: Any = None) -> float:
    f = features(evidence, query_evidence, recipe)
    z = recipe.intercept + sum(w * f[name] for name, w in recipe.weights.items())
    if evidence.get("metadata_hit") and f["rare_miss"] == 0.0:
        z += recipe.metadata_bonus
    if verdict is not None and getattr(verdict, "insufficient", False):
        z += recipe.laya_unsupported
    return z


def probability(evidence: Mapping[str, Any], query_evidence: Mapping[str, Any],
                recipe: sr.SupportRecipe = sr.ACTIVE, *, verdict: Any = None) -> float:
    if not evidence:
        return 0.0  # nothing measured is never support
    z = logit(evidence, query_evidence, recipe, verdict=verdict)
    return 1.0 / (1.0 + math.exp(-max(-60.0, min(60.0, z))))


def assess(results: Sequence[Any], query_evidence: Mapping[str, Any], *,
           verdict: Any = None, recipe: sr.SupportRecipe = sr.ACTIVE) -> Assessment:
    """The gate's verdict over recall's results (``evidence`` on each)."""
    qe = query_evidence or {}
    probs = tuple(round(probability(getattr(r, "evidence", None) or {}, qe, recipe,
                                    verdict=verdict), 6) for r in results)
    best = max(probs) if probs else None
    supported = best is not None and best >= recipe.threshold
    gaps = sorted({name for r in results if getattr(r, "evidence", None)
                   for name in imputed(r.evidence, qe)})
    reason = None if supported else (REASON_UNSUPPORTED if probs else REASON_NO_RESULTS)
    return Assessment(supported=supported, best=best, threshold=recipe.threshold,
                      probabilities=probs, version=recipe.version, reason=reason,
                      imputed=tuple(gaps))


__all__ = ["ABSTAIN_NOTE", "Assessment", "REASON_NO_RESULTS", "REASON_UNSUPPORTED",
           "assess", "features", "imputed", "logit", "probability"]
