# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later
"""Metadata coverage for doctor and the single Memory health card."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from superlocalmemory.core.enrichment import status


def coverage(db):
    total = db.execute('SELECT COUNT(*) AS n FROM atomic_facts')[0]['n']
    counted = {
        'observation_dates': "observation_date IS NOT NULL AND observation_date!=''",
        'event_dates': "referenced_date IS NOT NULL AND referenced_date!=''",
        'valid_from': "valid_from IS NOT NULL AND valid_from!=''",
        'entities': "canonical_entities_json IS NOT NULL AND canonical_entities_json!='[]'",
        'kind_confirmed': "memory_kind_source IN ('caller','user')",
        'kind_model': "memory_kind_source LIKE 'model:%'",
        'kind_guessed': "memory_kind_source='rules'",
        'non_answer': 'COALESCE(non_answer,0)=1',
    }
    cols = {r['name'] for r in db.execute('PRAGMA table_info(atomic_facts)')}
    out = {'facts': total}
    for key, clause in counted.items():
        column = clause.split()[0].split('=')[0]
        if key == 'non_answer':
            column = 'non_answer'
        out[key] = (db.execute(f'SELECT COUNT(*) AS n FROM atomic_facts WHERE {clause}')
                    [0]['n'] if column in cols else 0)
    parents = db.execute('SELECT COUNT(*) AS n, '
                         "SUM(CASE WHEN json_valid(metadata_json) AND "
                         "json_extract(metadata_json,'$.tags') NOT IN ('','[]') THEN 1 ELSE 0 END)"
                         ' AS tags, '
                         "SUM(CASE WHEN json_valid(metadata_json) AND "
                         "json_extract(metadata_json,'$.project') NOT IN ('','[]') "
                         "THEN 1 ELSE 0 END)"
                         ' AS project FROM memories')[0]
    out.update(memories=parents['n'], tags=parents['tags'] or 0, project=parents['project'] or 0)
    return out


def report(db):
    current = status(db)
    counts = coverage(db)
    repairs = []
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='memory_health_repairs'"):
        repairs = [dict(r) for r in db.execute('SELECT * FROM memory_health_repairs '
                                              'ORDER BY rowid DESC LIMIT 20')]
    return {'enrichment': current, 'coverage': counts, 'repairs': repairs,
            'summary': f"Improving your memories: {current.get('processed', 0):,} "
                       f"of {current.get('total', counts['facts']):,}"}


def from_path(db_path):
    from types import SimpleNamespace

    conn = None
    # A read-only report must not initialize, migrate or start any services.
    try:
        conn = sqlite3.connect(f'{Path(db_path).absolute().as_uri()}?mode=ro', uri=True)
        conn.row_factory = sqlite3.Row
        db = SimpleNamespace(execute=lambda sql, params=(): conn.execute(sql, params).fetchall())
        return report(db)
    except (sqlite3.Error, OSError) as exc:
        return {'error': type(exc).__name__, 'enrichment': {'status': 'unavailable'},
                'coverage': {}, 'summary': 'Memory health is temporarily unavailable.'}
    finally:
        if conn is not None:
            conn.close()
