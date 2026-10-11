"""Guard failure paths and descriptor lifetime stay fail closed."""

import os
from types import SimpleNamespace

import pytest

from superlocalmemory.loops import execution_guard as guard
from superlocalmemory.loops.artifact_revision import snapshot


def job(root):
    state = root / "state"
    state.write_text("fail")
    artifacts, revision = snapshot(root, [state])
    return state, {"cwd": str(root), "artifacts_json": artifacts, "revision_digest": revision}


def test_unsupported_change_markers_refuse_execution(tmp_path, monkeypatch):
    _, registered = job(tmp_path)
    monkeypatch.setattr(guard, "os", SimpleNamespace(name="nt"))
    with pytest.raises(ValueError, match="POSIX change timestamps"):
        with guard.execution_guard(registered):
            pytest.fail("Unsupported host admitted a registered check")


def test_mutation_during_initial_hash_is_refused_and_handles_close(tmp_path, monkeypatch):
    state, registered = job(tmp_path)
    streams, digest, fdopen = [], guard._digest, os.fdopen

    def opened(*args, **kwargs):
        stream = fdopen(*args, **kwargs)
        streams.append(stream)
        return stream

    def mutate_while_hashing(stream):
        result = digest(stream)
        before = state.stat()
        state.write_text("pass")
        state.write_text("fail")
        os.utime(state, ns=(before.st_atime_ns, before.st_mtime_ns))
        return result

    monkeypatch.setattr(guard.os, "fdopen", opened)
    monkeypatch.setattr(guard, "_digest", mutate_while_hashing)
    with pytest.raises(ValueError, match="changed during verification"):
        with guard.execution_guard(registered):
            pytest.fail("Input read race admitted execution")
    assert streams and all(stream.closed for stream in streams)


def test_disappearing_input_during_window_refuses_validation(tmp_path):
    state, registered = job(tmp_path)
    with pytest.raises(ValueError, match="changed during verification"):
        with guard.execution_guard(registered) as validate:
            state.unlink()
            validate()


def test_nonregular_replacement_is_refused_without_blocking(tmp_path, monkeypatch):
    state, registered = job(tmp_path)
    namespace = guard._namespace

    def replace_with_fifo(*args):
        result = namespace(*args)
        state.unlink()
        os.mkfifo(state)
        return result

    monkeypatch.setattr(guard, "_namespace", replace_with_fifo)
    with pytest.raises(ValueError, match="changed during verification"):
        with guard.execution_guard(registered):
            pytest.fail("Nonregular input admitted execution")
