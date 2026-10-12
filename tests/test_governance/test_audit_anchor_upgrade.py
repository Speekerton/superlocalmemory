"""Only pre-anchor stores receive the one-time upgrade anchor."""
import sqlite3
from pathlib import Path

import pytest

from superlocalmemory.compliance.audit import AuditChain


def test_legacy_chain_gets_one_anchor_and_upgrade_event(tmp_path):
    db = tmp_path / 'audit.db'
    chain = AuditChain(db)
    chain.log('legacy-event')
    Path(str(db) + '.anchor').unlink()
    with sqlite3.connect(db) as conn:
        conn.execute('DROP TABLE IF EXISTS audit_anchor_state')
    upgraded = AuditChain(db)
    assert upgraded.verify_report()['ok'] is True
    events = upgraded.query(operation='anchor_initialized_on_upgrade')
    assert len(events) == 1
    assert AuditChain(db).count(operation='anchor_initialized_on_upgrade') == 1


@pytest.mark.parametrize('truncate', [False, True])
def test_removed_anchor_is_never_reinitialized(tmp_path, truncate):
    db = tmp_path / 'audit.db'
    chain = AuditChain(db)
    chain.log('protected-event')
    Path(str(db) + '.anchor').unlink()
    if truncate:
        with sqlite3.connect(db) as conn:
            conn.execute('DELETE FROM audit_chain')
    reopened = AuditChain(db)
    assert reopened.verify_report()['ok'] is False
    assert not Path(str(db) + '.anchor').exists()
    assert reopened.count(operation='anchor_initialized_on_upgrade') == 0
