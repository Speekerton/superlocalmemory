"""Prove isolated adapters persist through the actual SLM engine, without TCP."""

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load_bridge():
    path = ROOT / "ide/integrations/_engine_bridge.py"
    spec = importlib.util.spec_from_file_location("wp7_engine_bridge", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "name, package, filename, cls",
    [
        ("google-adk", "google_adk_superlocalmemory", "_v3_adk_store.py", "V3ADKStore"),
        ("crewai", "crewai_superlocalmemory", "_v3_crewai_store.py", "V3CrewAIStore"),
        (
            "semantic-kernel",
            "semantic_kernel_superlocalmemory",
            "_v3_record_store.py",
            "V3RecordStore",
        ),
    ],
)
def test_isolated_engine_persistence(tmp_path, name, package, filename, cls):
    bridge = load_bridge()
    module = ROOT / "ide/integrations" / name / package / filename
    db = tmp_path / "memory.db"
    store = bridge.RemoteStore(sys.executable, module, cls, db)
    if name == "google-adk":
        store.add_events("app", "user", "session", [{"text": "Ada prefers tea"}])
        assert (
            store.list_events_for_session("app", "user", "session")[0]["event"]["text"]
            == "Ada prefers tea"
        )
    elif name == "crewai":
        store.save({"id": "r1", "content": "Ada prefers tea", "embedding": [1.0, 0.0]})
        assert store.get_record("r1")["content"] == "Ada prefers tea"
    else:
        store.upsert("docs", "d1", {"id": "d1", "text": "Ada prefers tea"})
        assert store.get("docs", "d1")["text"] == "Ada prefers tea"
    store.close()
    assert store._process.poll() == 0
    store.close()  # idempotent
    store = bridge.RemoteStore(sys.executable, module, cls, db)
    try:
        count = (
            len(store.list_events_for_session("app", "user", "session"))
            if name == "google-adk"
            else store.count()
            if name == "crewai"
            else len(store.list_records("docs"))
        )
        assert count == 1
    finally:
        store.close()


def test_missing_engine_fails_explicitly(tmp_path):
    bridge = load_bridge()
    with pytest.raises((OSError, RuntimeError)):
        bridge.RemoteStore("/nonexistent/slm-python", Path(__file__), "Store", tmp_path / "db")
