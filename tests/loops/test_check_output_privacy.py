"""Verifier N1: neither raw key bytes nor their encodings leave in evidence."""

import base64
import hashlib
import json

from superlocalmemory.loops.execution_guard import _key
from superlocalmemory.loops.receipt_jobs import run_registered_check
from tests.loops.test_hermetic_contract import register
from tests.mcp.test_loop_escape_integrity import ledger as ledger
from tests.mcp.test_loop_escape_integrity import tools
from tests.mcp.test_loop_receipt_races import receipt_db as receipt_db


def test_old_ancestor_key_path_is_unavailable(receipt_db, tmp_path):
    _, _, job = register(receipt_db, tmp_path, code=(
        "from pathlib import Path\n"
        "p = Path('../../admission.key')\n"
        "raise SystemExit(1 if p.exists() else 0)\n"))
    assert run_registered_check(receipt_db, job['job_id'])['verdict'] == 'PASS'
    assert not (tmp_path / 'slm/loop-checks/admission.key').exists()


async def test_known_key_full_output_hash_and_redacted_excerpt(
    receipt_db, tmp_path, ledger, caplog
):
    # Same-user code can find the key via an explicit absolute path. Its output
    # must still be safe; this is a redaction guarantee, not an OS sandbox.
    vault = tmp_path / 'slm/loop-admission/admission.key'
    code = (
        "import sys,base64\nfrom pathlib import Path\n"
        f"key=Path({str(vault)!r}).read_bytes()\n"
        "sys.stdout.buffer.write(key)\n"
        "sys.stdout.flush()\n"
        "print(key.hex()); print(base64.b64encode(key).decode()); print(repr(key))\n"
        "print('Z'*12000)\n"
        "sys.stderr.buffer.write(key)\n")
    _, _, job = register(receipt_db, tmp_path, code=code)
    key = _key(job['store_path'])
    receipt = run_registered_check(receipt_db, job['job_id'])
    evidence = json.loads(receipt['evidence'])
    full = key + (key.hex() + '\n' + base64.b64encode(key).decode() + '\n'
                  + repr(key) + '\n' + 'Z' * 12000 + '\n').encode()
    hash_matches = evidence.get('stdout_sha256') == hashlib.sha256(full).hexdigest()
    assert hash_matches
    representations = (key.hex(), base64.b64encode(key).decode(), repr(key),
                       key.decode('utf-8', errors='replace'))
    leaked = any(value in json.dumps(receipt) or value in receipt['evidence']
                 for value in representations)
    assert not leaked
    assert len(evidence['stdout_excerpt']) <= 2048 and len(evidence['stderr_excerpt']) <= 2048
    assert evidence['stderr_sha256'] == hashlib.sha256(key).hexdigest()
    assert len(evidence['output_sha256']) == 64
    assert vault.stat().st_mode & 0o777 == 0o600
    rows = receipt_db.execute('SELECT evidence FROM loop_execution_receipts')
    stored_leak = any(value in rows[0]['evidence'] for value in representations)
    assert not stored_leak
    fns = tools(receipt_db)
    result = await fns['slm_loop_run']('build', 'build', max_iterations=1,
                                      gate_contract={'job_id': job['job_id']})
    history = await fns['slm_loop_history']('build')
    show = await fns['slm_loop_show'](result['run_id'])
    response_leak = any(value in json.dumps([result, history, show]) or value in caplog.text
                        for value in representations)
    assert not response_leak


def test_existing_key_moves_without_invalidating_admission(receipt_db, tmp_path):
    from superlocalmemory.loops.execution_guard import verify_admission

    _, _, job = register(receipt_db, tmp_path)
    receipt = run_registered_check(receipt_db, job['job_id'])
    vault = tmp_path / 'slm/loop-admission/admission.key'
    old = tmp_path / 'slm/loop-checks/admission.key'
    vault.rename(old)
    _key(job['store_path'], create=True)
    assert vault.exists() and not old.exists()
    assert verify_admission(job, receipt)
