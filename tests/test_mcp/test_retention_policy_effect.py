"""BRN-09: setting retention must change compaction and maintenance decisions."""

from types import SimpleNamespace

import pytest

from superlocalmemory.mcp.tools_v28 import register_v28_tools
from tests.mcp.test_loop_tools import _Capture
from tests.test_learning.test_forgetting_protections import PID, age, scheduler
from tests.test_learning.test_forgetting_scheduler import db_with_facts as _fixture_db_with_facts

db_with_facts = _fixture_db_with_facts


@pytest.mark.asyncio
async def test_tool_policy_changes_compaction_and_decay(db_with_facts, monkeypatch):
    db = db_with_facts
    age(db)
    engine = SimpleNamespace(_db=db, profile_id=PID)
    monkeypatch.setitem(
        register_v28_tools.__globals__,
        "authorize_mcp_mutation",
        lambda *a, **k: SimpleNamespace(complete=lambda: None),
    )
    server = _Capture()
    register_v28_tools(server, lambda: engine)
    tools = server.fns
    before = await tools["compact_memories"]()
    assert all(t["proposed"] == "archived" for t in before["transitions"])
    assert (await tools["set_retention_policy"](9999, 10000))["success"]
    after = await tools["compact_memories"]()
    assert all(t["proposed"] != "archived" for t in after["transitions"])
    scheduler(db).run_decay_cycle(PID, force=True)
    assert db.execute('SELECT COUNT(*) FROM atomic_facts WHERE lifecycle="archived"')[0][0] == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("cold,archive", [(-1, 90), (90, 30), (0, -1)])
async def test_invalid_policy_is_refused(db_with_facts, monkeypatch, cold, archive):
    db = db_with_facts
    monkeypatch.setitem(
        register_v28_tools.__globals__,
        "authorize_mcp_mutation",
        lambda *a, **k: SimpleNamespace(complete=lambda: None),
    )
    server = _Capture()
    register_v28_tools(server, lambda: SimpleNamespace(_db=db, profile_id=PID))
    result = await server.fns["set_retention_policy"](cold, archive)
    assert not result["success"]
    assert db.get_config("retention_cold_days") is None


@pytest.mark.asyncio
async def test_manual_compaction_keeps_recently_rewarded_fact(db_with_facts):
    db = db_with_facts
    age(db)
    db.execute("ALTER TABLE action_outcomes ADD COLUMN reward REAL")
    db.execute("ALTER TABLE action_outcomes ADD COLUMN settled_at TEXT")
    db.execute(
        "INSERT INTO action_outcomes (outcome_id,profile_id,fact_ids_json,reward,settled_at) "
        "VALUES ('o',?,'[\"fact_009\"]',.9,datetime('now'))",
        (PID,),
    )
    server = _Capture()
    register_v28_tools(server, lambda: SimpleNamespace(_db=db, profile_id=PID))
    result = await server.fns["compact_memories"]()
    assert not any(t["fact_id"] == "fact_009" for t in result["transitions"])
