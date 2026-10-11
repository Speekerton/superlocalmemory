"""BRN-23/24: one original, tenant/TTL ownership, durable model savings."""

from types import SimpleNamespace

import pytest

from superlocalmemory.mcp.tools_optimize import register_optimize_tools
from superlocalmemory.optimize.compress.ccr import CCRStore
from superlocalmemory.optimize.compress.router import CompressRouter
from superlocalmemory.optimize.metrics.counters import MetricsCollector
from superlocalmemory.optimize.metrics.persistence import MetricsPersistence
from superlocalmemory.optimize.storage.db import CacheDB
from tests.test_mcp.test_tools_optimize import _MockServer


@pytest.fixture
def compression(tmp_path, monkeypatch):
    db = CacheDB(tmp_path / "cache.db")
    ccr = CCRStore()
    ccr._db = db
    router = CompressRouter()
    router._get_config = lambda: SimpleNamespace(
        compress_enabled=True, compress_mode="aggressive", compress_prose=True
    )
    router._get_llmlingua_compressor = lambda: SimpleNamespace(
        compress=lambda text: "short summary"
    )
    router._ccr_store = ccr
    metrics = MetricsCollector()
    router.set_metrics(metrics)
    monkeypatch.setattr(CompressRouter, "get_instance", lambda: router)
    monkeypatch.setattr(CCRStore, "get_instance", lambda: ccr)
    monkeypatch.setattr(CacheDB, "get_default", lambda: db)
    monkeypatch.setattr(MetricsCollector, "get_instance", lambda: metrics)
    monkeypatch.setenv("SLM_AGENT_ID", "caller")
    server = _MockServer()
    register_optimize_tools(server)
    return server._tools, db, metrics


@pytest.mark.asyncio
@pytest.mark.parametrize("reversible", [False, True])
async def test_single_original_owned_by_mcp_tenant_and_ttl(compression, reversible):
    tools, db, _ = compression
    result = await tools["slm_compress"](
        "A long narrative sentence. " * 80, reversible=reversible, ttl_seconds=1
    )
    assert result["strategy"] == "llmlingua2_prose", result
    assert db.ccr_count() == int(reversible)
    if reversible:
        assert (await tools["slm_retrieve"](result["ccr_id"]))["ok"]
        assert db.ccr_get(result["ccr_id"], tenant_id="default") is None
        db._db.execute("UPDATE llmcache_ccr_originals SET ttl_expires=0")
        assert not (await tools["slm_retrieve"](result["ccr_id"]))["ok"]


@pytest.mark.asyncio
async def test_model_compression_updates_durable_savings(compression):
    tools, db, metrics = compression
    await tools["slm_compress"]("A long narrative sentence. " * 80)
    stats = await tools["slm_optimize_stats"]()
    assert stats["compress_runs"] == 1
    assert stats["tokens_saved_compress"] > 0
    loaded = MetricsCollector()
    MetricsPersistence().load(loaded, db)
    from superlocalmemory.optimize.metrics.mcp_compression import snapshot_with_mcp

    assert snapshot_with_mcp(db, loaded.snapshot()).compress_runs == 1


@pytest.mark.asyncio
async def test_mcp_compression_preserves_existing_proxy_totals(compression):
    from superlocalmemory.optimize.storage.db import MetricsSnapshot

    tools, db, _ = compression
    db.metrics_flush(MetricsSnapshot(hits=17, misses=3, compress_runs=8, tokens_saved_compress=100))
    await tools["slm_compress"]("A long narrative sentence. " * 80)
    stats = await tools["slm_optimize_stats"]()
    assert stats["cache_proxy_hits"] == 17
    assert stats["cache_proxy_misses"] == 3
    assert stats["compress_runs"] == 9
    assert stats["tokens_saved_compress"] > 100
