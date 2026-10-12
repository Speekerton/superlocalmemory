# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
"""A stored memory gets its hub baseline at save; the engine owns the backfill."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from superlocalmemory.core.config import EmbeddingConfig, SLMConfig
from superlocalmemory.core.engine import MemoryEngine
from superlocalmemory.retrieval import hub_baseline as hb
from superlocalmemory.storage.models import Mode

DIM = 768


def _vector(text: str) -> list[float]:
    seed = hashlib.sha256(text.encode()).digest()
    return [((seed[i % 32] + i) % 17) / 17.0 + 0.01 for i in range(DIM)]


def _embedder() -> MagicMock:
    m = MagicMock()
    m._config = EmbeddingConfig(model_name="nomic-ai/nomic-embed-text-v1.5", dimension=DIM)
    m.is_available = True
    m.embed.side_effect = _vector
    m.embed_batch.side_effect = lambda texts: [_vector(t) for t in texts]
    m.compute_fisher_params.side_effect = lambda v: (v, [1.0] * len(v))
    return m


def _engine(tmp_path: Path, monkeypatch, backfill: str) -> MemoryEngine:
    monkeypatch.setenv("SLM_HUB_BASELINE_BACKFILL", backfill)
    hb.PROBES._cache.clear()
    eng = MemoryEngine(SLMConfig(
        mode=Mode.A, base_dir=tmp_path, db_path=tmp_path / "memory.db",
        active_profile="default",
        embedding=EmbeddingConfig(model_name="nomic-ai/nomic-embed-text-v1.5", dimension=DIM)))
    eng._config.retrieval.use_cross_encoder = False
    with patch("superlocalmemory.core.engine_wiring.init_embedder", return_value=_embedder()):
        eng._ensure_init()
    return eng


@pytest.fixture
def engine(tmp_path, monkeypatch) -> Iterator[MemoryEngine]:
    eng = _engine(tmp_path, monkeypatch, "0")
    yield eng
    eng.close()


def test_a_stored_memory_has_its_baseline_before_store_returns(engine) -> None:
    fact_ids = engine.store("The nightly backup keeps seven copies.")
    assert fact_ids
    got = hb.read(engine._db, fact_ids, hb.space_of(engine._embedder))
    assert set(got) == set(fact_ids)


def test_backfill_is_off_when_asked_and_owned_by_the_engine_otherwise(
        tmp_path, monkeypatch, engine) -> None:
    assert engine._hub_backfill is None
    other = _engine(tmp_path / "on", monkeypatch, "1")
    try:
        task = other._hub_backfill
        assert isinstance(task, hb.Backfill) and task.thread is not None
    finally:
        other.close()
    assert other._hub_backfill is None
    task.thread.join(3.0)
    assert not task.thread.is_alive()
