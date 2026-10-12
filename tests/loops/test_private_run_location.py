"""Operator temp settings cannot place check copies back inside task inputs."""

import pytest

from superlocalmemory.loops import private_workspace
from superlocalmemory.loops.receipt_jobs import run_registered_check
from tests.loops.test_hermetic_contract import register
from tests.mcp.test_loop_receipt_races import receipt_db as receipt_db


@pytest.mark.parametrize('location', ['project', 'store'])
def test_run_root_cannot_be_agent_workspace_or_store(
    receipt_db, tmp_path, monkeypatch, location
):
    work, _, job = register(receipt_db, tmp_path)
    parent = work if location == 'project' else tmp_path / 'slm'
    monkeypatch.setattr(private_workspace.tempfile, 'gettempdir', lambda: str(parent))
    with pytest.raises(ValueError, match='outside the project and data root'):
        run_registered_check(receipt_db, job['job_id'])
