# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later
"""Safe idle repairs, using the product's native repair and undo machinery."""

from __future__ import annotations

import time
import uuid
from pathlib import Path

from superlocalmemory.core.description_metadata import VERSION
from superlocalmemory.core.enrichment import EnrichmentRunner, now
from superlocalmemory.storage import enrichment_ledger as ledger

ACTIONS = ('refile-hidden', 'qjl-sketches', 'entity-links')


def _record(db, run_id, action, found, fixed=0, *, error=None, native=None):
    db.execute("UPDATE enrichment_runs SET status='completed',updated_at=? WHERE run_id=?",
               (now(), run_id))
    db.execute('INSERT INTO memory_health_repairs(run_id,action,status,found,fixed,error,'
               'native_run_id,created_at) VALUES (?,?,?,?,?,?,?,?)',
               (run_id, action, 'error' if error else 'completed', found, fixed,
                error, native, now()))


def _new_run(db, action):
    run_id, stamp = uuid.uuid4().hex, now()
    point = EnrichmentRunner(db, idle=lambda: True)._backup()
    db.execute('INSERT INTO enrichment_runs(run_id,enrichment_version,action,status,'
               'upper_rowid,total,backup_point,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)',
               (run_id, VERSION, action, 'running', 0, 0, point, stamp, stamp))
    return run_id


def _changes(db, run_id, table, before, fields):
    for old in before:
        after = db.execute(f'SELECT * FROM {table} WHERE fact_id=? AND profile_id=?',
                           (old['fact_id'], old['profile_id']))
        if not after:
            continue
        after = dict(after[0])
        for field in fields:
            if old[field] != after[field]:
                ledger.record(db, run_id, old['profile_id'], table, old['fact_id'],
                              field, old[field], after[field], fact_id=old['fact_id'])


def _refile(engine, dry_run, idle):
    from superlocalmemory.core.lifecycle_state import set_fact_lifecycle_zone
    from superlocalmemory.core.memory_health import refile_hidden

    db = engine._db
    plan = refile_hidden(db.db_path, dry_run=True)
    if dry_run or not plan.fact_ids or not idle():
        return {'found': len(plan.fact_ids), 'fixed': 0}
    run_id = _new_run(db, 'refile-hidden')
    fixed = 0
    for fact_id in plan.fact_ids[:25]:
        if not idle():
            break
        with db.transaction():
            retention = [dict(r) for r in db.execute(
                'SELECT * FROM fact_retention WHERE fact_id=?', (fact_id,))]
            if not retention or retention[0]['lifecycle_zone'] not in ('archive', 'forgotten')                     or retention[0]['retention_score'] <= 0.8:
                continue
            facts = [dict(r) for r in db.execute('SELECT * FROM atomic_facts WHERE fact_id=?',
                                                (fact_id,))]
            set_fact_lifecycle_zone(db, [fact_id], 'active')
            _changes(db, run_id, 'atomic_facts', facts, ('lifecycle',))
            _changes(db, run_id, 'fact_retention', retention,
                     ('lifecycle_zone', 'last_computed_at'))
            fixed += 1
    _record(db, run_id, 'refile-hidden', len(plan.fact_ids), fixed)
    return {'found': len(plan.fact_ids), 'fixed': fixed, 'run_id': run_id}


def _quantizer(engine):
    from dataclasses import replace

    from superlocalmemory.math.polar_quant import PolarQuantEncoder
    from superlocalmemory.math.qjl import QJLEncoder
    from superlocalmemory.storage.quantized_store import QuantizedEmbeddingStore

    cfg = engine._config.quantization
    polar = PolarQuantEncoder(replace(cfg.polar, dimension=engine._config.embedding.dimension))
    return QuantizedEmbeddingStore(engine._db, polar, QJLEncoder(cfg.qjl), cfg), cfg


def _qjl(engine, dry_run, idle):
    from superlocalmemory.storage.qjl_repair import _original_snapshot, _repair_one, repair_rows
    db = engine._db
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='polar_embeddings'"):
        return {'found': 0, 'fixed': 0}
    store, cfg = _quantizer(engine)
    profiles = db.execute('SELECT DISTINCT profile_id FROM polar_embeddings')
    plans = [(r['profile_id'], row) for r in profiles
             for row in repair_rows(db, r['profile_id'], cfg)]
    if dry_run or not plans or not idle():
        return {'found': len(plans), 'fixed': 0}
    run_id, fixed, errors = _new_run(db, 'qjl-sketches'), 0, 0
    for profile, row in plans[:25]:
        if not idle():
            break
        original = _original_snapshot(db, row['fact_id'], profile, store._polar._d)
        if original is None:
            errors += 1
            continue
        try:
            with db.transaction():
                snapshots = {table: [dict(r) for r in db.execute(
                    f'SELECT * FROM {table} WHERE fact_id=? AND profile_id=?',
                    (row['fact_id'], profile))]
                    for table in ('polar_embeddings', 'embedding_quantization_metadata')}
                _repair_one(db, store, row, profile, original[1], original[0])
                for table, fields in (
                    ('polar_embeddings', ('qjl_bits',)),
                    ('embedding_quantization_metadata', ('compressed_size_bytes',)),
                ):
                    _changes(db, run_id, table, snapshots[table], fields)
            fixed += 1
        except (ValueError, TypeError):
            errors += 1
    _record(db, run_id, 'qjl-sketches', len(plans), fixed,
            error='Some sketches need a new embedding' if errors else None)
    return {'found': len(plans), 'fixed': fixed, 'errors': errors, 'run_id': run_id}


def _entities(engine, dry_run, idle):
    import sqlite3
    from contextlib import closing

    from superlocalmemory.storage.entity_link_repair import plan
    from superlocalmemory.storage.entity_link_repair_apply import apply

    db = engine._db
    with closing(sqlite3.connect(f'{Path(db.db_path).absolute().as_uri()}?mode=ro', uri=True)) as conn:
        proposed = plan(conn)
        found = sum(len(p.facts) + len(p.aliases) + len(p.junk) for p in proposed.profiles)
    if dry_run or not found or not idle():
        return {'found': found, 'fixed': 0}
    # The shared pre-change safety copy (taken once per store), then the
    # native repair, whose own run ledger is what undo replays.
    run_id = _new_run(db, 'entity-links')
    result = apply(db.db_path, max_changes=25, idle=idle)
    fixed = sum(result.get(k, 0) for k in ('facts_relinked', 'aliases_removed',
                                          'aliases_kept_relabelled', 'junk_entities_removed'))
    _record(db, run_id, 'entity-links', found, fixed, native=result.get('run_id'))
    return {'found': found, 'fixed': fixed, 'run_id': run_id}


def repair_action(engine, action, *, dry_run=True, idle=lambda: True):
    if action not in ACTIONS:
        raise ValueError('Unknown memory health action')
    return {'action': action, **{'refile-hidden': _refile, 'qjl-sketches': _qjl,
                                 'entity-links': _entities}[action](engine, dry_run, idle)}


def run_safe_repairs(engine, *, idle):
    last = getattr(engine, '_memory_health_checked', 0.0)
    if time.monotonic() - last < 1800:
        return
    engine._memory_health_checked = time.monotonic()
    for action in ACTIONS:
        if not idle():
            return
        try:
            result = repair_action(engine, action, dry_run=True, idle=idle)
            if result['found'] and idle():
                applied = repair_action(engine, action, dry_run=False, idle=idle)
                # Continue bounded repair batches on the next idle tick.
                if applied.get('fixed') and applied['fixed'] < result['found']:
                    engine._memory_health_checked = 0.0
                return
        except Exception as exc:
            _record(engine._db, uuid.uuid4().hex, action, 0, error=type(exc).__name__)


def undo_action(engine, run_id):
    rows = engine._db.execute('SELECT * FROM memory_health_repairs WHERE run_id=?', (run_id,))
    if rows and rows[0]['native_run_id']:
        from superlocalmemory.storage.entity_link_repair_apply import undo
        result = undo(engine._db.db_path, rows[0]['native_run_id'])
    else:
        result = EnrichmentRunner(engine._db, idle=lambda: False).undo(run_id)
    engine._db.execute("UPDATE memory_health_repairs SET status='undone' WHERE run_id=?", (run_id,))
    return result
