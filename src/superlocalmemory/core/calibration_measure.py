# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
"""Evaluate actual candidate SETS; operational skips never become negative labels."""

from __future__ import annotations

import time

from superlocalmemory.core.calibration_candidates import raw_semantic, source_score
from superlocalmemory.core.calibration_control import await_idle
from superlocalmemory.core.recall_gate import background_work
from superlocalmemory.retrieval.calibration_metrics import calibrate
from superlocalmemory.retrieval.judge_recipe import (
    RECIPE_SET_V2,
    clean_documents,
    document_from_fact,
)
from superlocalmemory.retrieval.laya_set_recipe import calibration_probability, request_for
from superlocalmemory.storage.embedding_spaces import signature_of


def _sample(engine, judge, example, stop):
    from superlocalmemory.core.answer_check_scope import skip_answer_check

    await_idle(stop)
    with stop.operation(), background_work(), skip_answer_check():
        from superlocalmemory.storage.models import Mode

        response = engine._retrieval_engine.recall(
            example["question"], engine._config.profile_id, mode=Mode.A, limit=judge.top_k
        )  # local channels only: no LLM expansion, bandit plays, hooks or outcomes
        raw_facts, scores = raw_semantic(engine, example["question"], judge.top_k)
        if example["answered"]:
            scores = source_score(engine, example["question"], example["fact_id"])
    documents = [document_from_fact(r.fact) for r in response.results[: judge.top_k]]
    sources = {r.fact.fact_id for r in response.results[:judge.top_k]}
    if not documents:
        documents = [document_from_fact(fact) for fact in raw_facts]
        sources = {fact.fact_id for fact in raw_facts}
    documents = clean_documents(documents)
    shown = request_for(RECIPE_SET_V2, example["question"], [d.content for d in documents])
    answered = example["answered"] and example["answer"] in shown["documents"][0]
    if example["answered"] and (example["fact_id"] not in sources or not answered):
        return False, None, scores  # a missing source is not a proved negative label
    await_idle(stop)
    probability = (
        calibration_probability(judge, example["question"], documents) if documents else None
    )
    return answered, probability, scores


def _fit(identity, positive, negative, semantic_p, semantic_n, skipped):
    if len(positive) < 28 or len(negative) < 14:
        raise ValueError("Too few judged labels (need 28 answered / 14 absent); nothing replaced")
    result = {
        "judge": calibrate(positive, negative),
        "answered": len(positive),
        "unanswered": len(negative),
        "skipped": skipped,
        "embedding_status": "insufficient_source_scores",
    }
    holdout = result["judge"]["held_out"]
    if ((holdout["keep_rate"] + holdout["reject_rate"]) / 2 <= 0.5
            or min(holdout["keep_rate"], holdout["reject_rate"]) < 0.5):
        raise ValueError("Poor held-out discrimination; previous calibration kept")
    if len(semantic_p) >= 28 and len(semantic_n) >= 14:
        fit = calibrate(semantic_p, semantic_n)
        heldout = fit["held_out"]
        usable = ((heldout["keep_rate"] + heldout["reject_rate"]) / 2 > 0.5
                  and min(heldout["keep_rate"], heldout["reject_rate"]) >= 0.5)
        result["embedding_status"] = "measured" if usable else "poor_holdout"
        result["semantic"] = {
            "usable": usable,
            "signature": identity,
            "raw_floor": fit["threshold"],
            "answered": len(semantic_p),
            "unanswered": len(semantic_n),
            "metrics": fit,
            "measured_at": time.time(),
        }
    return result


def measure_examples(engine, judge, examples, stop, progress):
    identity = signature_of(engine._config.embedding)
    positive, negative, semantic_p, semantic_n = [], [], [], []
    skipped = 0
    for index, example in enumerate(examples):
        if stop.is_set():
            break
        if signature_of(engine._config.embedding) != identity:
            raise ValueError("Embedding space changed during calibration; nothing replaced")
        if engine._retrieval_engine._sufficiency_judge is not judge:
            raise ValueError("Answer check changed during calibration; nothing replaced")
        answered, probability, scores = _sample(engine, judge, example, stop)
        if probability is None:
            skipped += 1
        else:
            (positive if answered else negative).append(probability)
        # Embedding measurement is independent of judge availability and uses
        # the actual source label, not whether a clipped reader saw the quote.
        if scores:
            (semantic_p if example["answered"] else semantic_n).append(max(scores))
        progress(
            done=index + 1,
            total=len(examples),
            skipped=skipped,
            detail="Measuring held-out answer and absent-question sets",
        )
        stop.wait(0.01)
    return _fit(identity, positive, negative, semantic_p, semantic_n, skipped)
