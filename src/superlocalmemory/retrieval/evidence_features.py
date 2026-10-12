# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Evidence features: what each signal says about one recalled memory.

WHY
---
Whether recall should answer at all used to be decided by one signal, the raw
cosine at the evidence floor (``time_window.has_primary_evidence``). Several
stronger signals were computed and then thrown away before that decision: the
cross-encoder's raw score (normalised within the batch, so the best of several
unrelated memories always read 1.0), how much of the question a memory's words
actually cover (any single BM25 hit counted as full evidence), whether an
entity the question names is one the memory carries, and the nonsense-phrase
check in ``query_lexicon.oov_phrase``, which nothing called.

This module only MEASURES. Each recalled result carries these numbers on
``RetrievalResult.evidence`` and the response carries the question-level ones on
``RecallResponse.query_evidence``; recall trace shows both. Nothing here changes
ranking or whether recall abstains -- that decision is made elsewhere, from
these numbers, once it has been calibrated.

THE FEATURES (per result)
-------------------------
``cosine``            raw cosine between the question and the memory vectors
``hub_baseline``      the memory's mean cosine to its closest fixed probe queries
                      (``retrieval/hub_baseline.py``); None until computed
``hub_corrected``     ``cosine - hub_baseline`` (CSLS style); None without both
``hub_baseline_mean`` / ``hub_corrected_mean``  the same over ALL probes
``ce_raw``            the cross-encoder's own score, before any normalisation
``ce_batch_norm``     the same score min-max normalised in this recall's batch
``bm25_raw``          the BM25 score before the channel's saturating transform
``keyword_coverage``  share of the question's content words found in the memory
``entity_hit``        the question names an entity the memory carries

Pure functions of values recall already has: no I/O, no model call.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

import numpy as np

#: Bump when a feature's definition changes; logged features name it.
FEATURES_VERSION = "evidence-features-v1"

# The words a question is made of but that say nothing about its subject.
_QUESTION_WORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being", "am",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "must", "can", "could", "of", "in", "to", "for",
    "with", "on", "at", "from", "by", "as", "into", "about", "and", "but", "or",
    "not", "so", "if", "then", "than", "that", "this", "these", "those", "it",
    "its", "i", "me", "my", "we", "our", "us", "you", "your", "he", "him", "his",
    "she", "her", "they", "them", "their", "what", "which", "who", "whom",
    "whose", "when", "where", "why", "how", "there", "here", "any", "some",
    "all", "much", "many", "after", "before", "since", "until", "now", "ever",
})
# Unicode words, keeping identifier and version punctuation inside a token
# (ensure_daemon, v0.3.4, asdk_app_6ac9e8, OPS-4471) as one term.
_TERM_RE = re.compile(r"\w+(?:[._:/-]\w+)*", re.UNICODE)
_BM25_SATURATION = 5.0  # bm25_channel._BM25_SATURATION; inverted below


def query_terms(text: str) -> list[str]:
    """The question's content terms, lowercased, in order, without repeats."""
    seen: dict[str, None] = {}
    for term in _TERM_RE.findall(text.lower()):
        if term not in _QUESTION_WORDS and term not in seen:
            seen[term] = None
    return list(seen)


def _content_terms(text: str) -> set[str]:
    terms: set[str] = set()
    for term in _TERM_RE.findall(text.lower()):
        terms.add(term)
        # "asdk_app_6ac9e8" also contains "asdk", "app" and "6ac9e8"; a question
        # naming any whole piece of an identifier matches that piece.
        terms.update(p for p in re.split(r"[._:/-]", term) if p)
    return terms


def keyword_coverage(terms: Sequence[str], content: str) -> float:
    """Share of ``terms`` present as whole terms in ``content`` (0.0 when none)."""
    if not terms:
        return 0.0
    have = _content_terms(content)
    return sum(1 for t in terms if t in have) / len(terms)


def entity_hit(query: str, entities: Iterable[str]) -> bool:
    """True when the question names, as whole words, an entity the memory carries."""
    lowered = " " + " ".join(_TERM_RE.findall(query.lower())) + " "
    for entity in entities:
        words = _TERM_RE.findall(str(entity).lower())
        if words and len(" ".join(words)) >= 3 and f" {' '.join(words)} " in lowered:
            return True
    return False


def cosine(a: Sequence[float] | None, b: Sequence[float] | None) -> float | None:
    if a is None or b is None or len(a) == 0 or len(a) != len(b):
        return None
    va = np.asarray(a, dtype=np.float64)
    vb = np.asarray(b, dtype=np.float64)
    na, nb = float(np.linalg.norm(va)), float(np.linalg.norm(vb))
    if na <= 0.0 or nb <= 0.0:
        return None
    return float(np.dot(va, vb) / (na * nb))


def bm25_raw(unit_score: float | None) -> float | None:
    """Undo the BM25 channel's ``s / (s + k)``: the score FTS5 actually gave."""
    if unit_score is None or unit_score <= 0.0:
        return 0.0 if unit_score is not None else None
    if unit_score >= 1.0:
        return None
    return _BM25_SATURATION * unit_score / (1.0 - unit_score)


def build(
    *,
    query: str,
    terms: Sequence[str],
    query_vector: Sequence[float] | None,
    fact: Any,
    channel_scores: Mapping[str, float] | None,
    ce_raw: float | None = None,
    ce_batch_norm: float | None = None,
    hub_baseline: float | None = None,
    hub_baseline_mean: float | None = None,
) -> dict:
    """Every evidence feature for one result, as plain JSON-safe values."""
    cs = channel_scores or {}
    cos = cosine(query_vector, getattr(fact, "embedding", None))
    entities = [*(getattr(fact, "canonical_entities", None) or ()),
                *(getattr(fact, "entities", None) or ())]
    raw_bm25 = bm25_raw(cs.get("bm25")) if "bm25" in cs else 0.0
    return {
        "cosine": _r(cos),
        "hub_baseline": _r(hub_baseline),
        "hub_corrected": _corrected(cos, hub_baseline),
        "hub_baseline_mean": _r(hub_baseline_mean),
        "hub_corrected_mean": _corrected(cos, hub_baseline_mean),
        "ce_raw": _r(ce_raw),
        "ce_batch_norm": _r(ce_batch_norm),
        "bm25_raw": _r(raw_bm25),
        "keyword_coverage": _r(keyword_coverage(terms, getattr(fact, "content", "") or "")),
        "entity_hit": entity_hit(query, entities),
    }


def query_evidence(query: str, terms: Sequence[str] | None = None) -> dict:
    """Question-level evidence: the unused nonsense check, and its term count."""
    from superlocalmemory.retrieval.query_lexicon import oov_phrase, vocabulary

    try:
        vocab = vocabulary()
    except Exception:  # never let a cache read break recall
        vocab = None
    return {
        "features_version": FEATURES_VERSION,
        "oov_phrase": bool(oov_phrase(query, vocab)),
        "vocabulary_available": vocab is not None,
        "query_terms": len(query_terms(query) if terms is None else terms),
    }


def _corrected(cos: float | None, baseline: float | None) -> float | None:
    return None if cos is None or baseline is None else _r(cos - baseline)


def _r(value: float | None) -> float | None:
    return None if value is None else round(float(value), 6)
