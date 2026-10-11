"""Doctor diagnoses daemon availability without starting it or waiting for boot."""

import json
import os
from argparse import Namespace
from dataclasses import replace
from unittest.mock import MagicMock

import psutil
import pytest

from superlocalmemory.cli import commands, daemon
from superlocalmemory.infra.daemon_identity import build_descriptor, write_descriptor


@pytest.fixture
def probes(monkeypatch):
    health = MagicMock(return_value=None)
    monkeypatch.setattr(daemon, "_fetch_health", health)
    # Any old readiness helper would wait or probe more than once.
    def forbidden(*a, **k):
        raise AssertionError("doctor must not start or wait for the daemon")

    for name in ("ensure_daemon", "is_daemon_running", "_verified_legacy_health"):
        monkeypatch.setattr(daemon, name, forbidden)
    request = MagicMock(return_value={})
    monkeypatch.setattr(daemon, "daemon_request", request)
    monkeypatch.setattr("superlocalmemory.cli.features_cmd.daemon_request", request)
    monkeypatch.setattr("superlocalmemory.core.component_healer.heal_missing",
                        lambda *a, **k: {"healed": 0, "attempted": 0, "failed": 0})
    # Full doctor tests should not load a model or run a real worker.
    proc = MagicMock()
    monkeypatch.setattr("subprocess.Popen", lambda *a, **k: proc)
    monkeypatch.setattr(commands, "_readline_with_timeout", lambda *a: ('{"ok": true}', None))
    return health, request


def report(capsys, **flags):
    try:
        commands.cmd_doctor(Namespace(json=True, **flags))
    except SystemExit as exc:
        assert exc.code == 1
    data = json.loads(capsys.readouterr().out)["data"]
    return next(c for c in data["checks"] if c["name"] == "Daemon")


@pytest.mark.parametrize("flags", [{}, {"quick": True}, {"deep": True}, {"fix": True}])
def test_missing_daemon_is_visible_in_every_mode(probes, capsys, flags):
    row = report(capsys, **flags)
    assert row["status"] in {"WARN", "FAIL"}
    assert row["fix"] == "slm serve start"
    probes[0].assert_not_called()
    probes[1].assert_not_called()


def test_live_healthy_daemon_passes_one_short_probe(probes, capsys, free_port):
    record = build_descriptor(port=free_port, version="4.1.25", pid=os.getpid())
    write_descriptor(record)
    probes[0].return_value = record.public_health_fields()
    assert report(capsys, quick=True)["status"] == "PASS"
    probes[0].assert_called_once_with(free_port, timeout=0.5)
    if probes[1].called:
        assert probes[1].call_args.kwargs["verify_health"] is False
        assert probes[1].call_args.kwargs["expected_descriptor"] == record


def test_dead_record_fails_with_restart(probes, capsys, free_port, monkeypatch):
    record = build_descriptor(port=free_port, version="4.1.25", pid=os.getpid())
    write_descriptor(record)
    monkeypatch.setattr("psutil.Process", MagicMock(side_effect=psutil.NoSuchProcess(999)))
    row = report(capsys, quick=True)
    assert row["status"] == "FAIL"
    assert "dead" in row["detail"] or "no longer running" in row["detail"]
    assert row["fix"] == "slm restart"
    probes[0].assert_not_called()


@pytest.mark.parametrize("reply", [None, {"service": "foreign"}])
def test_live_but_unhealthy_or_foreign_daemon_fails(probes, capsys, free_port, reply):
    write_descriptor(build_descriptor(port=free_port, version="4.1.25", pid=os.getpid()))
    probes[0].return_value = reply
    row = report(capsys, quick=True)
    assert row["status"] == "FAIL" and row["fix"] == "slm restart"
    assert probes[0].call_count == 1
    probes[1].assert_not_called()


def test_recycled_pid_never_counts_as_the_daemon(probes, capsys, free_port, monkeypatch):
    record = build_descriptor(port=free_port, version="4.1.25", pid=os.getpid())
    write_descriptor(replace(record, process_start_token="test:old-process"))
    monkeypatch.setattr("superlocalmemory.cli.doctor_daemon.process_start_token_for",
                        lambda pid: "test:new-process")
    probes[0].return_value = record.public_health_fields()
    row = report(capsys, quick=True)
    assert row["status"] == "FAIL" and row["fix"] == "slm restart"
    assert "reused" in row["detail"]
    probes[0].assert_not_called()


def test_broken_descriptor_is_reported(probes, capsys, tmp_path):
    (tmp_path / "daemon.json").write_text("{bad json")
    row = report(capsys, quick=True)
    assert row["status"] == "FAIL" and row["fix"] == "slm restart"
    probes[0].assert_not_called()


def test_inspection_failure_warns_and_other_checks_continue(probes, capsys, monkeypatch):
    monkeypatch.setattr(daemon, "read_descriptor", MagicMock(side_effect=OSError("unreadable")))
    row = report(capsys, quick=True)
    assert row["status"] == "WARN"
    assert row["fix"] == "slm serve start"


def test_daemon_row_is_also_printed_in_text(probes, capsys):
    try:
        commands.cmd_doctor(Namespace(json=False, quick=True))
    except SystemExit as exc:
        assert exc.code == 1
    out = capsys.readouterr().out
    assert "[WARN] Daemon:" in out and "slm serve start" in out


@pytest.mark.parametrize("healthy", [False, True])
def test_old_record_creation_time_drift_needs_health_proof(
    probes, free_port, monkeypatch, healthy,
):
    from superlocalmemory.cli.doctor_daemon import check_daemon

    record = build_descriptor(port=free_port, version="4.1.25", pid=os.getpid())
    record = replace(record, process_start_token=None, process_create_time=0)
    write_descriptor(record)
    monkeypatch.setattr("superlocalmemory.cli.doctor_daemon.process_start_token_for",
                        lambda pid: None)
    probes[0].return_value = record.public_health_fields() if healthy else None
    check = check_daemon()
    assert check.status == ("PASS" if healthy else "FAIL")
    if not healthy:
        assert "identity" in check.detail
        assert check.fix == "slm restart"
    assert probes[0].call_count == 1


def test_zombie_record_is_dead_without_health(probes, free_port, monkeypatch):
    from superlocalmemory.cli.doctor_daemon import check_daemon

    write_descriptor(build_descriptor(port=free_port, version="4.1.25", pid=os.getpid()))
    process = MagicMock()
    process.status.return_value = psutil.STATUS_ZOMBIE
    monkeypatch.setattr("psutil.Process", lambda pid: process)
    check = check_daemon()
    assert check.status == "FAIL" and "no longer running" in check.detail
    probes[0].assert_not_called()
