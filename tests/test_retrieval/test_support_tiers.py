# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
"""Three tiers: supported, related (a real question, close memories), none."""

from __future__ import annotations

from types import SimpleNamespace

from superlocalmemory.core.score_contract import finalize_score_contract
from superlocalmemory.retrieval import support_gate as sg
from superlocalmemory.retrieval import support_tiers as st
from superlocalmemory.storage.models import AtomicFact, RecallResponse, RetrievalResult

REAL_Q = {"oov_phrase": False, "orphan_terms": 0.25, "nonsense_similarity": 0.33}
NONSENSE_Q = {"oov_phrase": False, "orphan_terms": 0.67, "nonsense_similarity": 0.33}


def _r(fid, evidence, content="x" * 600):
    r = RetrievalResult(fact=AtomicFact(fact_id=fid, memory_id=f"m-{fid}", content=content))
    r.evidence = dict(evidence)
    return r


CLOSE = {"hub_corrected": 0.2, "subject_coverage": 0.3, "rare_miss": 0.0}
FAR = {"hub_corrected": 0.02, "subject_coverage": 0.0, "rare_miss": 1.0}


def test_a_question_reads_as_nonsense_on_gibberish_orphans_or_its_profile() -> None:
    assert not st.question_is_nonsense(REAL_Q)
    assert st.question_is_nonsense(NONSENSE_Q)
    assert st.question_is_nonsense({**REAL_Q, "oov_phrase": True})
    assert st.question_is_nonsense({**REAL_Q, "nonsense_similarity": 0.45})
    assert not st.question_is_nonsense({})  # nothing measured: not called nonsense


def test_real_evidence_is_a_standout_cosine_or_the_rare_terms_and_half_the_words() -> None:
    assert st.real_evidence(CLOSE)
    assert st.real_evidence({"hub_corrected": 0.0, "subject_coverage": 0.5, "rare_miss": 0.0})
    assert not st.real_evidence(FAR)
    assert not st.real_evidence({"hub_corrected": 0.0, "subject_coverage": 0.5, "rare_miss": 0.5})


def test_related_takes_at_most_three_close_memories_best_first() -> None:
    results = [_r(str(i), CLOSE) for i in range(5)] + [_r("far", FAR)]
    probs = (0.1, 0.25, 0.2, 0.05, 0.15, 0.27)
    assert st.related_indexes(results, probs, REAL_Q) == [1, 2, 4]
    assert st.related_indexes(results, probs, NONSENSE_Q) == []
    assert st.related_indexes([_r("far", FAR)], (0.2,), REAL_Q) == []


def _support(*probs, threshold=0.5):
    best = max(probs) if probs else None
    ok = best is not None and best >= threshold
    return sg.Assessment(supported=ok, best=best, threshold=threshold, probabilities=probs,
                         version="t", reason=None if ok else sg.REASON_UNSUPPORTED)


def _response(qe, *results):
    return RecallResponse(query="q", results=list(results), query_evidence=dict(qe))


def test_nonsense_is_tier_none_with_the_gentle_reason() -> None:
    r = finalize_score_contract(_response(NONSENSE_Q, _r("a", CLOSE)), support=_support(0.2),
                                include_related=True)
    assert r.results == [] and r.support_tier == st.NONE
    assert r.abstention_note == st.NONE_NOTE == "That isn't in SuperLocalMemory."


def test_related_is_shown_only_to_callers_that_ask_and_labelled() -> None:
    rs = [_r(str(i), CLOSE) for i in range(4)]
    shown = finalize_score_contract(_response(REAL_Q, *rs), support=_support(.2, .3, .1, .25),
                                    include_related=True)
    assert shown.support_tier == st.RELATED
    assert [x.fact.fact_id for x in shown.results] == ["1", "3", "0"]
    assert all(x.tier == st.RELATED and x.weak for x in shown.results)
    assert shown.abstention_note == st.RELATED_NOTE and shown.abstained
    hidden = finalize_score_contract(_response(REAL_Q, *[_r(str(i), CLOSE) for i in range(4)]),
                                     support=_support(.2, .3, .1, .25))
    assert hidden.results == [] and hidden.support_tier == st.RELATED
    assert hidden.abstention_note == st.RELATED_HIDDEN_NOTE


def test_supported_results_are_labelled_supported_or_weak() -> None:
    r = finalize_score_contract(_response(REAL_Q, _r("a", CLOSE), _r("b", FAR)),
                                support=_support(0.9, 0.1))
    assert r.support_tier == st.SUPPORTED
    assert [x.tier for x in r.results] == [st.SUPPORTED, "weak"]


def test_show_weak_keeps_everything_labelled_with_the_tier_note() -> None:
    r = finalize_score_contract(_response(NONSENSE_Q, _r("a", CLOSE)), support=_support(0.2),
                                show_weak=True)
    assert len(r.results) == 1 and r.results[0].tier == "weak"
    assert r.abstention_note.startswith(st.NONE_NOTE) and r.weak_shown


def test_the_envelope_carries_the_tier_and_short_previews_for_related() -> None:
    from superlocalmemory.server.recall_serializer import (
        recall_response_metadata,
        serialize_recall_response,
    )

    r = finalize_score_contract(_response(REAL_Q, _r("a", CLOSE)), support=_support(0.2),
                                include_related=True)
    meta = recall_response_metadata(r)
    assert meta["tier"] == st.RELATED and meta["support"]["tier"] == st.RELATED
    items, _ = serialize_recall_response(r, limit=5)
    assert items[0]["tier"] == st.RELATED
    assert len(items[0]["content"]) <= st.PREVIEW_CHARS + 1
    assert SimpleNamespace  # keep the import used for future fakes
