"""Verifier N7: ancestor pytest configuration must never decide a check."""

import sys

import pytest

from superlocalmemory.loops import private_workspace
from tests.mcp.test_loop_escape_integrity import db as db
from tests.mcp.test_loop_escape_integrity import register, run, watch

PY = sys.executable


@pytest.mark.parametrize("plant", ["conftest_only", "ini_only_addopts", "ini_and_conftest",
                                   "pinned_ini_then_ancestor_conftest"])
async def test_N7_ancestor_config_variants(db, tmp_path, plant, monkeypatch):
    home = tmp_path / "fakehome"
    droot = home / ".superlocalmemory"
    droot.mkdir(parents=True)
    monkeypatch.setattr(private_workspace.tempfile, "gettempdir", lambda: str(home))
    monkeypatch.setenv("PYTEST_ADDOPTS", "--co")
    monkeypatch.setenv("PYTEST_PLUGINS", "untrusted_plugin")
    cwd = tmp_path / "proj"
    cwd.mkdir()
    (cwd / "state").write_text("fail")
    (cwd / "test_state.py").write_text(
        "from pathlib import Path\n\ndef test_state():\n"
        "    assert Path('state').read_text() == 'pass'\n")
    checks = ["test_state.py"]
    if plant == "pinned_ini_then_ancestor_conftest":
        (cwd / "pytest.ini").write_text("[pytest]\n")
        checks.append("pytest.ini")
    job = register(db, cwd, [PY, "-m", "pytest", "-q", "-p", "no:cacheprovider", "test_state.py"],
                   checks, ["state"], droot)
    honest = run(db, job)
    if plant in ("conftest_only", "ini_and_conftest", "pinned_ini_then_ancestor_conftest"):
        (home / "conftest.py").write_text("import os\nos._exit(0)\n")
    if plant in ("ini_only_addopts", "ini_and_conftest", "pinned_ini_then_ancestor_conftest"):
        (home / "pytest.ini").write_text("[pytest]\naddopts = --co\n")
    cheat = run(db, job)
    result = await watch(db, job["job_id"])
    assert honest["verdict"] == "FAIL"
    assert cheat["verdict"] == "FAIL"
    assert result["status"] != "DONE"


async def test_explicit_pinned_config_can_load_pinned_plugin(db, tmp_path):
    cwd = tmp_path / 'work'
    cwd.mkdir()
    (cwd / 'custom.ini').write_text('[pytest]\naddopts = -p local_plugin\n')
    (cwd / 'local_plugin.py').write_text(
        'import pytest\n@pytest.fixture\ndef value():\n    return 42\n')
    (cwd / 'test_value.py').write_text('def test_value(value):\n    assert value == 42\n')
    job = register(db, cwd, [PY, '-m', 'pytest', '-c', 'custom.ini', 'test_value.py'],
                   ['custom.ini', 'local_plugin.py', 'test_value.py'], [], tmp_path / 'slm')
    assert run(db, job)['verdict'] == 'PASS'
    assert (await watch(db, job['job_id']))['status'] == 'DONE'


async def test_generated_config_is_validated_after_execution(db, tmp_path):
    cwd = tmp_path / 'work'
    cwd.mkdir()
    (cwd / 'test_value.py').write_text(
        "from pathlib import Path\n"
        "Path('.slm-pytest/pytest.ini').write_text('[pytest]\\naddopts = --co\\n')\n"
        "def test_value():\n    assert True\n")
    job = register(db, cwd, [PY, '-m', 'pytest', 'test_value.py'],
                   ['test_value.py'], [], tmp_path / 'slm')
    outcome = run(db, job)
    assert 'generated pytest configuration' in outcome['refused']
    assert (await watch(db, job['job_id']))['status'] == 'HALT'


async def test_explicit_unpinned_config_is_refused(db, tmp_path):
    cwd = tmp_path / 'work'
    cwd.mkdir()
    config = tmp_path / 'external.ini'
    config.write_text('[pytest]\naddopts = --co\n')
    (cwd / 'test_value.py').write_text('def test_value():\n    assert False\n')
    job = register(db, cwd, [PY, '-m', 'pytest', '-c', str(config), 'test_value.py'],
                   ['test_value.py'], [], tmp_path / 'slm')
    assert 'pinned definition' in run(db, job)['refused']
    assert (await watch(db, job['job_id']))['status'] == 'HALT'
