"""Pictures keep their source identity even when their words match."""
from types import SimpleNamespace
from uuid import uuid4

import pytest

from superlocalmemory.media import open_media_store
from superlocalmemory.storage import schema
from superlocalmemory.storage.database import DatabaseManager
from superlocalmemory.storage.models import AtomicFact, MemoryRecord
from superlocalmemory.storage.source_identity import store_source_fact

from .test_ingest import env as _env  # noqa: F401
from .test_ingest import png, save


@pytest.fixture
def env(tmp_path, monkeypatch):
    root = tmp_path / "slm"
    monkeypatch.setenv("SLM_DATA_DIR", str(root))
    store = open_media_store(create=True, data_root=root)
    try:
        yield _env.__wrapped__(root, store)
    finally:
        store.close()


class SourceRuntime:
    def __init__(self, db):
        self.db = db

    def remember(self, request, actor, **kwargs):
        mid, fid = uuid4().hex, uuid4().hex
        record = MemoryRecord(memory_id=mid, content=request.content,
                              profile_id=request.profile_id, scope=request.scope,
                              metadata=dict(request.metadata))
        fact = AtomicFact(fact_id=fid, memory_id=mid, content=request.content,
                          profile_id=request.profile_id, scope=request.scope)
        fid = store_source_fact(self.db, record, fact)
        return SimpleNamespace(payload={"status": "queryable", "fact_ids": [fid],
                                        "memory_id": record.memory_id, "operation_id": "test"})


@pytest.mark.parametrize("tags", [("a", "b"), ("b", "a")])
def test_different_wordless_images_keep_two_facts_and_correct_sources(env, tmp_path, tags):
    import hashlib

    original = env.client.prepare_image

    def unique_thumbnail(*args, **kwargs):
        from pathlib import Path
        info = original(*args, **kwargs)
        Path(info["thumb_path"]).write_bytes(hashlib.sha256(Path(args[0]).read_bytes()).digest())
        return info

    env.client.prepare_image = unique_thumbnail
    db = DatabaseManager(tmp_path / "identity.db")
    db.initialize(schema)
    env.runtime = SourceRuntime(db)
    try:
        a = save(env, png(tags[0]), profile_id="default")
        b = save(env, png(tags[1]), profile_id="default")
        assert a.status == b.status == "stored"
        assert a.memory_id != b.memory_id
        rows = db.execute("SELECT memory_id, metadata_json FROM memories")
        assert len(db.execute("SELECT fact_id FROM atomic_facts")) == 2
        import json
        sources = {r["memory_id"]: json.loads(r["metadata_json"])["_slm_source"] for r in rows}
        assert sources[a.memory_id]["media_id"] == a.media_id
        assert sources[b.memory_id]["media_id"] == b.media_id
        assert sources[a.memory_id]["content_sha256"] != sources[b.memory_id]["content_sha256"]
        for receipt, tag in zip((a, b), tags):
            row = env.store.get_item(receipt.media_id)
            assert row["anchor_memory_id"] == receipt.memory_id
            assert row["thumb_webp"] == hashlib.sha256(png(tag)).digest()
    finally:
        db.close()


def test_wordless_picture_stores_grounded_caption(env):
    original = env.client.prepare_image

    def described(*args, **kwargs):
        return {**original(*args, **kwargs),
                "visual_summary": "Image with predominantly blue pixels."}

    env.client.prepare_image = described
    save(env)
    assert "predominantly blue" in env.runtime.requests[0].content
