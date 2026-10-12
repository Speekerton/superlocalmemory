"""Operational receipts are durable but cannot become answers."""

import pytest

from superlocalmemory.storage import schema
from superlocalmemory.storage.database import DatabaseManager
from superlocalmemory.storage.models import AtomicFact, MemoryRecord


@pytest.mark.parametrize('text', ['[] session ended 2026-04-01', '[]',
                                  'receipt: 0123abcd4567ef89'])
def test_stubs_are_saved_and_only_explicitly_listed(tmp_path, text):
    from superlocalmemory.storage.migrations.M059_memory_description import apply
    db = DatabaseManager(tmp_path / 'memory.db')
    db.initialize(schema)
    try:
        import sqlite3
        with sqlite3.connect(db.db_path) as conn:
            apply(conn)
        db.store_memory(MemoryRecord(memory_id='source', content=text))
        fact = AtomicFact(memory_id='source', content=text)
        db.store_fact(fact)
        assert db.get_fact(fact.fact_id) is not None
        assert db.get_all_facts('default') == []
        assert db.search_facts_fts('session OR receipt', 'default') == []
        assert [f.fact_id for f in db.get_all_facts('default', include_non_answer=True)] == [fact.fact_id]
    finally:
        db.close()


def test_short_meaningful_facts_remain_answer_material(tmp_path):
    from superlocalmemory.encoding.non_answer import is_stub
    assert not is_stub('I prefer tea.')
    assert not is_stub('Zephyr uses PostgreSQL.')
    assert not is_stub('The session ended with a decision to use PostgreSQL.')
