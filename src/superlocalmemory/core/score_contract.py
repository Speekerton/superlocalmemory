# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file

"""Truthful public retrieval score contract.

Retrieval produces an ordering, not an answer probability.  This module keeps
query relevance, stored assertion confidence, trust, and internal ranking
utility distinct while preserving the V3.6 aliases for one compatibility
release.
"""

from __future__ import annotations

import math
from typing import Any

from superlocalmemory.retrieval.sufficiency import SufficiencyVerdict
from superlocalmemory.storage.models import RecallResponse

#: Appended to the abstain note when the caller asked to see the weak matches.
WEAK_NOTE = " These are the closest weak matches, shown because show_weak was set."
#: When no channel found anything at all (a channel may also have been down;
#: ``channel_status`` says).
NO_MATCH_NOTE = "Nothing in memory matched this question."


def _bounded(value: object, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    if not math.isfinite(number):
        number = default
    return min(1.0, max(0.0, number))


def finalize_score_contract(
    response: RecallResponse, verdict: SufficiencyVerdict | None = None, *,
    support: Any = None, show_weak: bool = False, keep_results: bool = False,
) -> RecallResponse:
    """Finalize aliases, rank positions, and response abstention metadata.

    ``support`` (a ``retrieval.support_gate.Assessment``), when given, decides
    whether recall answers (4.1.25). When nothing clears its threshold recall
    abstains and returns NOTHING with a plain reason -- except pinned memories,
    which always show; ``keep_results`` (the caller named an explicit filter)
    keeps today's results; ``show_weak`` keeps them labelled as weak. The
    answer check's verdict is one of the gate's inputs; its own word is kept
    in ``answer_check_insufficient``.

    ``score`` IS NOT THE ORDERING KEY, and a caller that sorts by it will get a
    different answer than the one this returns. That is deliberate, and it is
    load-bearing:

    * ``score`` answers "how well does this match the query" — a property of the
      result and the query alone.
    * ``rank_position``, assigned here from the order of the list, answers "what
      is recommended, and in what order". Ranking also weighs whether a memory
      has helped before and whether the session was just looking at it, neither
      of which is a property of the query.

    So the two can disagree, and the top result can legitimately carry a lower
    ``score`` than the one beneath it. Consumers should present the list in the
    order given, or sort by ``rank_position``; ``ranking_score`` carries the
    internal utility for anyone who needs to re-derive it.

    This ordering is NOT recomputed here. Re-sorting by ``score`` at this point
    would silently undo every ranking pass that ran before it.
    """
    if support is not None:
        _apply_support(response, support, verdict, show_weak=show_weak,
                       keep_results=keep_results)
    for position, result in enumerate(response.results or (), start=1):
        relevance = _bounded(
            result.relevance_score
            if result.relevance_score is not None
            else result.score
        )
        memory_confidence = _bounded(
            result.memory_confidence
            if result.memory_confidence is not None
            else getattr(result.fact, "confidence", 0.0)
        )
        result.relevance_score = relevance
        result.score = relevance
        result.memory_confidence = memory_confidence
        result.confidence = memory_confidence
        result.rank_position = position
        semantic = result.channel_scores.get("semantic")
        result.match_confidence = _bounded(2 * semantic - 1) if semantic is not None else None
        result.confidence_basis = "raw_semantic_evidence" if semantic is not None else "unmeasured"

    response.score_contract_version = "2"
    if verdict is None or not response.results:
        response.calibration_status = "uncalibrated"
        response.calibration_id = None
        response.answer_confidence = None
        response.abstained = not bool(response.results)
    else:
        # 4.1.18: a separate decision on whether the results answer the
        # question. The ranking score cannot make it — measured on a real store
        # it was the same for right answers, wrong ones and questions with no
        # answer in memory. Results are never removed: abstention is a signal
        # for the caller, and a caller that ignores it sees what it saw before.
        response.calibration_status = verdict.calibration_status
        response.calibration_id = verdict.calibration_id
        response.answer_confidence = round(verdict.answer_confidence, 4)
        response.abstained = verdict.insufficient
    if support is not None:
        response.abstained = response.support_status != "supported"
    if response.abstained:
        response.abstention_reason = _abstention_reason(response, verdict, support)
        if not response.abstention_note and not response.results:
            from superlocalmemory.retrieval.support_gate import ABSTAIN_NOTE
            response.abstention_note = (NO_MATCH_NOTE if response.abstention_reason
                                        == "no_candidates" else ABSTAIN_NOTE)
    else:
        response.abstention_reason = None
    return response


def _abstention_reason(response: RecallResponse, verdict: Any, support: Any) -> str:
    if verdict is not None and getattr(verdict, "insufficient", False):
        return "judged_insufficient"
    if support is not None and response.support_status == "unsupported" and (
            support.probabilities):
        return "unsupported"
    if response.results:
        return "judged_insufficient"
    return "evidence_floor" if response.no_confident_match else "no_candidates"


def _apply_support(response: RecallResponse, support: Any, verdict: Any, *,
                   show_weak: bool, keep_results: bool) -> None:
    """Label each result with its support; drop them all when none supports."""
    from superlocalmemory.retrieval.support_gate import ABSTAIN_NOTE

    for result, p in zip(response.results or (), support.probabilities):
        result.support = p
        result.weak = p < support.threshold
    if verdict is not None:
        response.answer_check_insufficient = bool(getattr(verdict, "insufficient", False))
    response.support_status = "supported" if support.supported else "unsupported"
    response.support_best = support.best
    response.support_threshold = support.threshold
    response.support_version = support.version
    if support.supported:
        return
    response.abstention_note = ABSTAIN_NOTE
    if show_weak and response.results:
        response.weak_shown = True
        response.abstention_note = ABSTAIN_NOTE + WEAK_NOTE
    elif not keep_results:
        response.results = [r for r in response.results or ()
                            if getattr(r.fact, "pinned", False)]
    response.no_confident_match = response.no_confident_match or not response.results


__all__ = ["finalize_score_contract"]
