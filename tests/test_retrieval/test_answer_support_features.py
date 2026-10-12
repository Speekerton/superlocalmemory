# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
"""The evidence the answer-support gate reads: rare terms, script, query profile."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from superlocalmemory.retrieval import evidence_features as ef
from superlocalmemory.retrieval import hub_baseline as hb


def test_latin_script_is_judged_on_letters_only() -> None:
    assert ef.is_latin("How long does ensure_daemon wait?")
    assert ef.is_latin("Wann läuft die nächtliche Sicherung?")
    assert ef.is_latin("asdk_app_6ac9e8 v0.3.4")
    assert ef.is_latin("12345 ???")
    assert not ef.is_latin("日志保留多久？")
    assert not ef.is_latin("डेटाबेस का बैकअप कब लिया जाता है?")
    assert not ef.is_latin("ステージング環境のポートは何番ですか？")


def test_rare_terms_are_identifiers_and_words_no_dictionary_knows() -> None:
    terms = ["v0.3.4", "snazzle", "release", "kestrel", "läuft", "right-to-be-forgotten",
             "p1", "ci", "bananas"]
    assert ef.rare_terms(terms, vocab=frozenset()) == ["v0.3.4", "snazzle", "kestrel", "p1"]
    # A word the model's vocabulary knows is not rare either.
    assert ef.rare_terms(["kestrel"], vocab=frozenset({"kestrel"})) == []
    assert ef.rare_terms([], vocab=None) == []


def test_rare_miss_is_the_share_of_rare_terms_the_memory_lacks() -> None:
    content = "Hub v0.3.4 fixed the resultType bug."
    assert ef.rare_miss(["v0.3.4", "snazzle"], content) == pytest.approx(0.5)
    assert ef.rare_miss(["v0.3.4"], content) == 0.0
    assert ef.rare_miss(["asdk_app_ffff"], "rcpt asdk_app_6ac9 ok") == 1.0
    assert ef.rare_miss([], content) == 0.0


def test_build_records_rare_miss_only_when_rare_terms_are_given() -> None:
    fact = SimpleNamespace(content="Hub v0.3.4 fixed it", embedding=None,
                           canonical_entities=[], entities=[])
    out = ef.build(query="v0.3.4 snazzle", terms=["v0.3.4", "snazzle"], query_vector=None,
                   fact=fact, channel_scores={}, rare=["v0.3.4", "snazzle"])
    assert out["rare_miss"] == pytest.approx(0.5)
    plain = ef.build(query="v0.3.4", terms=["v0.3.4"], query_vector=None, fact=fact,
                     channel_scores={})
    assert plain["rare_miss"] == 0.0


def test_query_evidence_reports_script_rare_terms_and_query_profile(monkeypatch) -> None:
    from superlocalmemory.retrieval import query_lexicon

    monkeypatch.setattr(query_lexicon, "vocabulary", lambda: frozenset())
    q = ef.query_evidence("v0.3.4 snazzle", nonsense_similarity=0.41234567)
    assert q["latin_script"] is True
    assert q["rare_terms"] == 2
    assert q["nonsense_similarity"] == pytest.approx(0.412346)
    assert ef.query_evidence("日志保留多久？")["latin_script"] is False
    assert ef.query_evidence("what is this")["nonsense_similarity"] is None


def _probe_matrix(dim: int = 4) -> np.ndarray:
    rows = np.zeros((96, dim), dtype=np.float32)
    rows[:, 0] = 1.0
    rows[32:64, 0] = 0.0
    rows[32:64, 1] = 1.0  # the "ordinary words, no meaning" probes
    return rows


def test_query_profile_is_the_mean_cosine_to_the_meaningless_sentences() -> None:
    probes = _probe_matrix()
    assert hb.query_profile([0.0, 1.0, 0.0, 0.0], probes) == pytest.approx(1.0)
    assert hb.query_profile([1.0, 0.0, 0.0, 0.0], probes) == pytest.approx(0.0)
    assert hb.query_profile(None, probes) is None
    assert hb.query_profile([1.0, 0.0], probes) is None  # another space
    assert hb.query_profile([1.0, 0.0, 0.0, 0.0], None) is None


def test_baseline_of_one_vector_matches_the_stored_form() -> None:
    probes = _probe_matrix()
    topk, mean = hb.baseline_of([1.0, 0.0, 0.0, 0.0], probes)
    (stored_mean, stored_top), = hb.baselines([[1.0, 0.0, 0.0, 0.0]], probes)
    assert (topk, mean) == pytest.approx((stored_top, stored_mean))
    assert hb.baseline_of(None, probes) is None
    assert hb.baseline_of([1.0, 0.0], probes) is None


class _Embedder:
    def __init__(self):
        from superlocalmemory.core.config import EmbeddingConfig

        self._config = EmbeddingConfig(model_name="test/model", dimension=4)
        self.calls = 0

    def embed_batch(self, texts):
        self.calls += 1
        return [[1.0, float(i % 3), 0.0, 0.5] for i, _ in enumerate(texts)]


def test_cached_never_embeds_and_matrix_fills_the_cache() -> None:
    bank = hb.ProbeBank()
    emb = _Embedder()
    space = "space-under-test"
    assert bank.cached(space) is None
    assert emb.calls == 0
    m = bank.matrix(emb, space)
    assert m is not None and m.shape == (96, 4)
    assert bank.cached(space) is m
    assert emb.calls == 1


def _engine_with(probes, stored):
    from superlocalmemory.retrieval.engine import RetrievalEngine

    eng = RetrievalEngine.__new__(RetrievalEngine)
    eng._reranker = None
    eng._query_embedding_cache = {"v0.3.4 snazzle": [0.0, 1.0, 0.0, 0.0]}
    eng._hub_baselines = lambda ids, profile: stored
    eng._probe_matrix = lambda: probes
    return eng


def _result(fid, content, embedding):
    from superlocalmemory.storage.models import RetrievalResult

    fact = SimpleNamespace(fact_id=fid, content=content, embedding=embedding,
                           canonical_entities=[], entities=[])
    return RetrievalResult(fact=fact, score=0.7, channel_scores={"semantic": 0.9})


def test_attach_measures_a_missing_baseline_and_the_query_profile() -> None:
    probes = _probe_matrix()
    eng = _engine_with(probes, {"f1": (0.5, 0.25)})
    results = [_result("f1", "hub v0.3.4 fix", [0.0, 1.0, 0.0, 0.0]),
               _result("f2", "release notes", [1.0, 0.0, 0.0, 0.0])]
    q = eng._attach_evidence("v0.3.4 snazzle", results, {}, "default")
    assert q["nonsense_similarity"] == pytest.approx(1.0)
    assert q["rare_terms"] == 2
    assert results[0].evidence["hub_baseline"] == pytest.approx(0.5)  # stored wins
    assert results[0].evidence["rare_miss"] == pytest.approx(0.5)
    topk, _mean = hb.baseline_of([1.0, 0.0, 0.0, 0.0], probes)
    assert results[1].evidence["hub_baseline"] == pytest.approx(topk, abs=1e-6)
    assert results[1].evidence["rare_miss"] == 1.0


def test_attach_without_probes_leaves_the_profile_and_baseline_missing() -> None:
    eng = _engine_with(None, {})
    results = [_result("f1", "hub v0.3.4 fix", [0.0, 1.0, 0.0, 0.0])]
    q = eng._attach_evidence("v0.3.4 snazzle", results, {}, "default")
    assert q["nonsense_similarity"] is None
    assert results[0].evidence["hub_baseline"] is None


def test_warm_probes_embeds_once_and_fails_open(monkeypatch) -> None:
    bank = hb.ProbeBank()
    monkeypatch.setattr(hb, "PROBES", bank)
    monkeypatch.setattr(hb, "space_of", lambda emb: "space-under-test" if emb else None)
    emb = _Embedder()
    assert hb.warm_probes(emb) is True
    assert hb.warm_probes(emb) is True
    assert emb.calls == 1
    assert hb.warm_probes(None) is False

    class _Broken(_Embedder):
        def embed_batch(self, texts):
            raise RuntimeError("model gone")

    monkeypatch.setattr(hb, "PROBES", hb.ProbeBank())
    assert hb.warm_probes(_Broken()) is False


def test_daemon_warmup_embeds_the_probes(monkeypatch) -> None:
    from superlocalmemory.server import recall_warmup

    seen = []
    monkeypatch.setattr(hb, "warm_probes", lambda emb: seen.append(emb) or True)
    engine = SimpleNamespace(_embedder="E", profile_id="default")
    assert recall_warmup.warm_hub_probes(engine) is True
    assert seen == ["E"]


def test_cosine_falls_back_to_the_semantic_channel_when_no_vector_is_loaded() -> None:
    fact = SimpleNamespace(content="x", embedding=None, canonical_entities=[], entities=[])
    out = ef.build(query="q", terms=["q"], query_vector=[1.0, 0.0], fact=fact,
                   channel_scores={"semantic": 0.9})
    assert out["cosine"] == pytest.approx(0.8)
