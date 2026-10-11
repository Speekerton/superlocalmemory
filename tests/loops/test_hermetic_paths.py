"""Private storage and command paths cannot escape the hermetic workspace."""

import sys

import pytest

from superlocalmemory.loops import receipt_jobs
from superlocalmemory.loops.private_workspace import private_dir
from tests.mcp.test_loop_receipt_races import receipt_db as receipt_db


def register(db, work, data_root, command=None):
    work.mkdir(parents=True, exist_ok=True)
    (work / 'check.py').write_text("raise SystemExit(1)")
    (work / 'state').write_text('fail')
    return receipt_jobs.register_job(
        db, profile_id='default', task_id='build', watcher_name='build', producer='checker',
        command=command or [sys.executable, str(work / 'check.py')], cwd=work,
        check_paths=['check.py'], artifact_paths=['state'], data_root=data_root,
    )


@pytest.mark.parametrize('kind', ['same_store', 'traversal', 'ancestor_link'])
def test_store_cannot_be_redirected_inside_project(receipt_db, tmp_path, kind):
    work = tmp_path / ('loop-checks' if kind == 'same_store' else 'work')
    work.mkdir()
    if kind == 'same_store':
        root = tmp_path
    elif kind == 'traversal':
        (tmp_path / 'elsewhere').mkdir()
        root = tmp_path / 'elsewhere' / '..' / 'work' / 'slm'
    else:
        (tmp_path / 'redirect').symlink_to(work, target_is_directory=True)
        root = tmp_path / 'redirect' / 'slm'
    with pytest.raises(ValueError, match='outside|symlink|no-follow'):
        register(receipt_db, work, root)
    assert not (work / 'admission.key').exists()
    assert not (work / 'slm').exists()


def test_private_creation_never_follows_ancestor_symlink(tmp_path):
    outside = tmp_path / 'outside'
    outside.mkdir()
    (tmp_path / 'link').symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match='symlink|no-follow'):
        private_dir(tmp_path / 'link' / 'store')
    assert not list(outside.iterdir())


def test_command_traversal_is_rejected_at_registration(receipt_db, tmp_path):
    work = tmp_path / 'work'
    path = work / '..' / 'work' / 'check.py'
    with pytest.raises(ValueError, match='command.*travers|confined'):
        register(receipt_db, work, tmp_path / 'slm', [sys.executable, str(path)])


def test_option_file_argument_is_relocated_to_pinned_copy(receipt_db, tmp_path):
    work = tmp_path / 'work'
    work.mkdir()
    script = work / 'check.py'
    script.write_text("import sys\nfrom pathlib import Path\n"
                      "assert Path(sys.argv[1].split('=', 1)[1]).read_text() == 'good'")
    config = work / 'config.ini'
    config.write_text('good')
    job = receipt_jobs.register_job(
        receipt_db, profile_id='default', task_id='build', watcher_name='build', producer='checker',
        command=[sys.executable, str(script), '--config=' + str(config)], cwd=work,
        check_paths=[script, config], artifact_paths=[], data_root=tmp_path / 'slm',
    )
    config.write_text('bad')
    assert receipt_jobs.run_registered_check(receipt_db, job['job_id'])['verdict'] == 'PASS'


def test_check_descendants_are_stopped_on_timeout(receipt_db, tmp_path):
    work = tmp_path / 'work'
    work.mkdir()
    marker = tmp_path / 'survived'
    child = f"import time; from pathlib import Path; time.sleep(.6); Path({str(marker)!r}).touch()"
    script = work / 'check.py'
    script.write_text('import subprocess, sys, time\n'
                      f'subprocess.Popen([sys.executable, "-c", {child!r}])\ntime.sleep(3)')
    job = receipt_jobs.register_job(
        receipt_db, profile_id='default', task_id='build', watcher_name='build', producer='checker',
        command=[sys.executable, str(script)], cwd=work, check_paths=[script],
        artifact_paths=[], data_root=tmp_path / 'slm',
    )
    import time

    start = time.monotonic()
    assert receipt_jobs.run_registered_check(receipt_db, job['job_id'], timeout=.15)['verdict'] == 'FAIL'
    assert time.monotonic() - start < 2
    time.sleep(.8)
    assert not marker.exists()
