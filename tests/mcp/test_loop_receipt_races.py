"""BRN-08: real check interleavings must never publish rejected PASS evidence."""

import asyncio
import sys
import threading
import time
from types import SimpleNamespace

import pytest

from superlocalmemory.loops.receipt_jobs import register_job, run_registered_check
from tests.mcp.test_loop_independent_receipts import _threaded_receipt_connection
from tests.mcp.test_loop_receipt_replay import harness


@pytest.fixture
def receipt_db():
    conn = _threaded_receipt_connection()
    yield SimpleNamespace(execute=lambda sql, p=(): conn.execute(sql, p).fetchall())
    conn.close()


def receipts(db):
    if not db.execute("SELECT name FROM sqlite_master WHERE name='loop_execution_receipts'"):
        return []
    return db.execute("SELECT * FROM loop_execution_receipts")


def register(db, root, script, artifacts):
    return register_job(
        db, profile_id="default", task_id="build", watcher_name="build", producer="checker",
        command=[sys.executable, "-I", str(script)], cwd=root, artifact_paths=artifacts,
        allow_prestart_evidence=True,
    )


def wait_for(path):
    deadline = time.monotonic() + 5
    while not path.exists():
        if time.monotonic() > deadline:
            raise TimeoutError(path.name)
        time.sleep(.005)


def race_job(db, root):
    state, script = root / "state", root / "check.py"
    state.write_text("fail")
    script.write_text("""from pathlib import Path
import time
Path('started').touch()
deadline = time.monotonic() + 5
for marker in ('go',):
    while not Path(marker).exists():
        if time.monotonic() > deadline: raise SystemExit(2)
        time.sleep(.005)
passed = Path('state').read_text() == 'pass'
print('read pass' if passed else 'read fail', flush=True)
Path('read_done').touch()
while not Path('restored').exists():
    if time.monotonic() > deadline: raise SystemExit(2)
    time.sleep(.005)
raise SystemExit(0 if passed else 1)
""")
    return state, register(db, root, script, [state, script])


def writer(root, state, *, restore):
    errors = []

    def mutate():
        try:
            wait_for(root / "started")
            state.write_text("pass")
            (root / "go").touch()
            wait_for(root / "read_done")
            if restore:
                state.write_text("fail")
            (root / "restored").touch()
        except Exception as error:
            errors.append(error)

    thread = threading.Thread(target=mutate)
    thread.start()
    return thread, errors


@pytest.mark.asyncio
async def test_rejected_check_leaves_no_usable_pass(receipt_db, tmp_path):
    state, job = race_job(receipt_db, tmp_path)
    thread, errors = writer(tmp_path, state, restore=False)
    try:
        with pytest.raises(ValueError, match="changed during verification"):
            run_registered_check(receipt_db, job["job_id"])
    finally:
        thread.join(6)
    assert not errors and not thread.is_alive()
    state.write_text("fail")
    assert not receipts(receipt_db), "Rejected execution already published completion evidence"
    result = await harness(receipt_db)(
        "build", "build", max_iterations=1, gate_contract={"job_id": job["job_id"]},
    )
    assert result["status"] == "HALT" and not result["passed"], result


@pytest.mark.asyncio
async def test_pass_is_invisible_until_postvalidation_finishes(receipt_db, tmp_path, monkeypatch):
    from superlocalmemory.loops import receipt_jobs

    script = tmp_path / "check.py"
    script.write_text("print('real subprocess passed')")
    job = register(receipt_db, tmp_path, script, [script])
    entered, release = threading.Event(), threading.Event()
    original, calls = receipt_jobs.matches, 0

    def paused_validation(candidate):
        nonlocal calls
        calls += 1
        if calls == 2:
            entered.set()
            if not release.wait(5):
                raise TimeoutError("validation release")
            return False
        return original(candidate)

    monkeypatch.setattr(receipt_jobs, "matches", paused_validation)
    task = asyncio.create_task(asyncio.to_thread(run_registered_check, receipt_db, job["job_id"]))
    try:
        assert await asyncio.to_thread(entered.wait, 5)
        result = await harness(receipt_db)(
            "build", "build", max_iterations=1, gate_contract={"job_id": job["job_id"]},
        )
        assert result["status"] == "HALT" and not result["passed"], result
        assert not receipts(receipt_db)
    finally:
        release.set()
        with pytest.raises(ValueError, match="changed during verification"):
            await task
    assert not receipts(receipt_db)


@pytest.mark.parametrize("change", ["superseded", "expired"])
def test_postexecution_job_refusal_never_publishes(receipt_db, tmp_path, change):
    script = tmp_path / "check.py"
    script.write_text("""from pathlib import Path
import time
Path('started').touch()
deadline = time.monotonic() + 5
while not Path('release').exists():
    if time.monotonic() > deadline: raise SystemExit(2)
    time.sleep(.005)
print('passed')
""")
    job = register_job(
        receipt_db, profile_id="default", task_id="build", watcher_name="build",
        producer="checker", command=[sys.executable, "-I", str(script)], cwd=tmp_path,
        artifact_paths=[script], allow_prestart_evidence=True,
        ttl_seconds=.1 if change == "expired" else 3600,
    )
    errors = []

    def invalidate():
        try:
            wait_for(tmp_path / "started")
            if change == "superseded":
                register(receipt_db, tmp_path, script, [script])
            else:
                time.sleep(.15)
            (tmp_path / "release").touch()
        except Exception as error:
            errors.append(error)

    thread = threading.Thread(target=invalidate)
    thread.start()
    try:
        with pytest.raises(ValueError, match="expired or superseded during verification"):
            run_registered_check(receipt_db, job["job_id"])
    finally:
        thread.join(6)
    assert not errors and not thread.is_alive()
    assert not receipts(receipt_db)
