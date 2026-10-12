"""Verifier L4: the actual check refusal belongs in run and history reasons."""

import sys

from tests.mcp.test_loop_escape_integrity import db as db
from tests.mcp.test_loop_escape_integrity import ledger as ledger
from tests.mcp.test_loop_escape_integrity import register, run, tools


async def test_failed_receipt_reason_in_run_history_and_show(db, tmp_path, ledger):
    cwd = tmp_path / 'work'
    cwd.mkdir()
    (cwd / 'check.py').write_text('raise SystemExit(7)\n')
    job = register(db, cwd, [sys.executable, '-I', 'check.py'], ['check.py'], [], tmp_path / 'slm')
    assert run(db, job)['verdict'] == 'FAIL'
    fns = tools(db)
    result = await fns['slm_loop_run']('build', 'build', max_iterations=1,
                                      gate_contract={'job_id': job['job_id']})
    history = await fns['slm_loop_history']('build')
    show = await fns['slm_loop_show'](result['run_id'])
    assert result['status'] == 'HALT'
    assert result['reason'] == result['receipt_reason'] == 'check FAILED (exit 7)'
    assert history['runs'][0]['reason'] == result['reason']
    assert any(result['reason'] in lap['detail'] for lap in show['laps'])


async def test_no_registration_reason_in_run_and_history(db, ledger):
    fns = tools(db)
    result = await fns['slm_loop_run']('build', 'build', max_iterations=1)
    history = await fns['slm_loop_history']('build')
    assert result['reason'] == 'operator-registered job_id required'
    assert history['runs'][0]['reason'] == result['reason']
