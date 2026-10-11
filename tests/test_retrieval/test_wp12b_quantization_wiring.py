"""Persisted quantized-only facts participate in the production semantic path."""

from dataclasses import replace
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from superlocalmemory.core.config import PolarQuantConfig, SLMConfig
from superlocalmemory.core.engine_wiring import _init_quantization_aware_search, init_retrieval
from superlocalmemory.storage import schema
from superlocalmemory.storage.database import DatabaseManager
from superlocalmemory.storage.models import AtomicFact, MemoryRecord, Mode


@pytest.fixture
def wired(tmp_path):
    config = SLMConfig.for_mode(Mode.A, base_dir=tmp_path)
    config.embedding = replace(config.embedding, dimension=16)
    config.quantization = replace(config.quantization, polar=PolarQuantConfig(
        dimension=16, rotation_matrix_path=str(tmp_path / "rotation.npy")))
    db = DatabaseManager(tmp_path / "test.db")
    db.initialize(schema)
    vector_store = MagicMock(available=True)
    vector_store.search.return_value = []
    yield config, db, vector_store
    db.close()


@pytest.mark.parametrize("bit_width", [8, 4, 2])
def test_enabled_quantized_only_fact_is_used_by_wired_channel(wired, bit_width):
    config, db, vector_store = wired
    retrieval = init_retrieval(config, db, None, None, None, vector_store=vector_store)
    channel = retrieval._semantic
    qas = channel._qas
    assert qas is not None
    memory = MemoryRecord(content="Quantization is active.")
    db.store_memory(memory)
    fact = AtomicFact(memory_id=memory.memory_id, content=memory.content)
    db.store_fact(fact)
    db.execute("INSERT INTO fact_retention (fact_id, profile_id) VALUES (?, ?)",
               (fact.fact_id, "default"))
    query = np.random.default_rng(1).standard_normal(16)
    query /= np.linalg.norm(query)
    assert qas._quantized_store.compress_fact(fact.fact_id, "default", query, bit_width)
    assert db.get_fact(fact.fact_id, "default").embedding is None
    real_search = type(qas).search
    with patch.object(type(qas), "search", autospec=True) as used:
        used.side_effect = lambda self, **kw: real_search(self, **kw)
        results = channel.search(query.tolist(), "default")
    assert used.call_count == 1
    assert fact.fact_id in {fid for fid, _ in results}


def test_disabled_configuration_is_explicit(wired, caplog):
    config, db, vector_store = wired
    config.quantization = replace(config.quantization, enabled=False)
    with caplog.at_level("INFO"):
        assert _init_quantization_aware_search(vector_store, db, config) is None
    assert "disabled by configuration" in caplog.text


def test_initialization_failure_is_visible(wired, caplog):
    config, db, vector_store = wired
    with patch("superlocalmemory.math.polar_quant.PolarQuantEncoder",
               side_effect=ValueError("bad codec")):
        assert _init_quantization_aware_search(vector_store, db, config) is None
    assert "quantized tiers unavailable" in caplog.text.lower()
