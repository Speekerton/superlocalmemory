"""Every canonical fact has event time independent of knowledge time."""

import pytest

from superlocalmemory.storage import schema
from superlocalmemory.storage.database import DatabaseManager
from superlocalmemory.storage.models import AtomicFact, MemoryRecord


@pytest.mark.parametrize(
    ('event', 'observed', 'expected'),
    [('2026-03-02', '2026-04-01', '2026-03-02'),
     (None, '2026-04-01', '2026-04-01'),
     (None, None, '2026-04-01T12:00:00+00:00')],
)
def test_every_save_writes_the_time_the_fact_became_true(tmp_path, event, observed, expected):
    db = DatabaseManager(tmp_path / 'memory.db')
    db.initialize(schema)
    try:
        db.store_memory(MemoryRecord(memory_id='source', content='Zephyr started.'))
        fact = AtomicFact(memory_id='source', content='Zephyr started.',
                          referenced_date=event, observation_date=observed,
                          created_at='2026-04-01T12:00:00+00:00')
        db.store_fact(fact)
        validity = db.get_temporal_validity(fact.fact_id, 'default')
        assert validity['valid_from'] == expected
        assert validity['system_created_at']
    finally:
        db.close()
