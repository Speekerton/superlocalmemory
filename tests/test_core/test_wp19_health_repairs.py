"""Automatic safe repairs: dry run first, one safety copy per store, exact undo."""

import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest

from superlocalmemory.storage import schema
from superlocalmemory.storage.database import DatabaseManager
from superlocalmemory.storage.models import AtomicFact, MemoryRecord


@pytest.fixture
def store(tmp_path):
    from superlocalmemory.storage.migrations.M059_memory_description import apply
    db = DatabaseManager(tmp_path / 'memory.db')
    db.initialize(schema)
    with sqlite3.connect(db.db_path) as conn:
        apply(conn)
        conn.execute(
            'CREATE TABLE IF NOT EXISTS fact_retention (fact_id TEXT PRIMARY KEY, '
            'profile_id TEXT NOT NULL, retention_score REAL NOT NULL DEFAULT 1.0, '
            'memory_strength REAL NOT NULL DEFAULT 1.0, access_count INTEGER NOT NULL DEFAULT 0, '
            'last_accessed_at TEXT, last_computed_at TEXT NOT NULL DEFAULT (datetime(\'now\')), '
            "lifecycle_zone TEXT NOT NULL DEFAULT 'active')")
    for i in range(3):
        text = f'Zephyr uses PostgreSQL for record {i}.'
        db.store_memory(MemoryRecord(memory_id=f'm{i}', content=text))
        db.store_fact(AtomicFact(fact_id=f'f{i}', memory_id=f'm{i}', content=text))
    # f0 and f1 are hidden although their score says they are in use.
    for fid, zone, score in (('f0', 'archive', 0.95), ('f1', 'forgotten', 0.9),
                             ('f2', 'archive', 0.1)):
        db.execute("INSERT OR REPLACE INTO fact_retention(fact_id,profile_id,retention_score,"
                   "lifecycle_zone,last_computed_at) VALUES (?,?,?,?,'2026-04-01')",
                   (fid, 'default', score, zone))
        db.execute("UPDATE atomic_facts SET lifecycle='archived' WHERE fact_id=?", (fid,))
    yield SimpleNamespace(_db=db)
    db.close()


def snapshot(db):
    return {t: [dict(r) for r in db.execute(f'SELECT * FROM {t} ORDER BY rowid')]
            for t in ('atomic_facts', 'fact_retention')}


def test_refile_hidden_dry_run_changes_nothing_then_apply_is_undoable(store):
    from superlocalmemory.core.health_repairs import repair_action, undo_action
    db = store._db
    before = snapshot(db)
    planned = repair_action(store, 'refile-hidden', dry_run=True)
    assert planned['found'] == 2 and planned['fixed'] == 0
    assert snapshot(db) == before
    applied = repair_action(store, 'refile-hidden', dry_run=False)
    assert applied['fixed'] == 2
    zones = {r['fact_id']: r['lifecycle_zone'] for r in db.execute('SELECT * FROM fact_retention')}
    assert zones == {'f0': 'active', 'f1': 'active', 'f2': 'archive'}
    row = db.execute('SELECT * FROM memory_health_repairs WHERE run_id=?', (applied['run_id'],))[0]
    assert (row['action'], row['found'], row['fixed']) == ('refile-hidden', 2, 2)
    undo_action(store, applied['run_id'])
    assert snapshot(db) == before
    assert db.execute('SELECT status FROM memory_health_repairs WHERE run_id=?',
                      (applied['run_id'],))[0]['status'] == 'undone'


def test_automatic_repairs_take_one_safety_copy_and_yield_to_foreground(store):
    from superlocalmemory.core.enrichment import EnrichmentRunner
    from superlocalmemory.core.health_repairs import run_safe_repairs
    db = store._db
    busy = True
    run_safe_repairs(store, idle=lambda: not busy)
    assert db.execute('SELECT COUNT(*) AS n FROM memory_health_repairs')[0]['n'] == 0
    busy = False
    store._memory_health_checked = 0.0
    run_safe_repairs(store, idle=lambda: not busy)
    assert db.execute("SELECT fixed FROM memory_health_repairs WHERE action='refile-hidden'")[0][
        'fixed'] == 2
    snapshots = Path(db.db_path).parent / 'pre-migration-snapshots'
    copies = sorted(snapshots.glob('*-pre-migration.db'))
    assert len(copies) == 1
    # Enrichment reuses the same pre-change copy instead of taking another.
    runner = EnrichmentRunner(db, idle=lambda: True)
    for _ in range(5):
        if runner.run_batch(limit=10)['status'] == 'completed':
            break
    assert sorted(snapshots.glob('*-pre-migration.db')) == copies


def test_unknown_repair_is_refused(store):
    from superlocalmemory.core.health_repairs import repair_action
    with pytest.raises(ValueError):
        repair_action(store, 'drop-everything')


def test_a_finished_pass_is_followed_only_by_new_facts(store):
    from superlocalmemory.core.enrichment import EnrichmentRunner
    db = store._db
    runner = EnrichmentRunner(db, idle=lambda: True)
    for _ in range(5):
        done = runner.run_batch(limit=10)
        if done['status'] == 'completed':
            break
    assert done['processed'] == 3
    # A day later only what was saved since is looked at again.
    db.execute("UPDATE enrichment_runs SET updated_at='2026-01-01T00:00:00+00:00'")
    db.store_memory(MemoryRecord(memory_id='m9', content='Atlas is our project.'))
    db.store_fact(AtomicFact(fact_id='f9', memory_id='m9', content='Atlas is our project.'))
    nxt = runner.run_batch(limit=10)
    assert nxt['run_id'] != done['run_id']
    assert (nxt['total'], nxt['processed']) == (1, 1)
