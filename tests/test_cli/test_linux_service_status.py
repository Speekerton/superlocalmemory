"""Installed and active are independent states of a Linux user service."""

import subprocess
from unittest.mock import MagicMock

import pytest

from superlocalmemory.cli import service_installer


@pytest.mark.parametrize(
    "unit_exists,returncode,stdout,installed,active",
    [
        (False, 3, "unknown", False, False),
        (False, 4, "inactive", False, False),
        (True, 3, "inactive", True, False),
        (True, 0, "active", True, True),
        (False, 0, "active", True, True),
        (False, 1, "active", False, False),
    ],
)
def test_linux_status(unit_exists, returncode, stdout, installed, active, tmp_path, monkeypatch):
    unit = tmp_path / "superlocalmemory.service"
    if unit_exists:
        unit.touch()
    monkeypatch.setattr(service_installer, "_linux_service_path", lambda: unit)
    result = subprocess.CompletedProcess([], returncode, stdout + "\n", "")
    run = MagicMock(return_value=result)
    monkeypatch.setattr(service_installer.subprocess, "run", run)
    status = service_installer.status_linux()
    assert status["installed"] is installed
    assert status["active"] is active
    run.assert_called_once()


@pytest.mark.parametrize("unit_exists", [False, True])
@pytest.mark.parametrize("error", [FileNotFoundError, subprocess.TimeoutExpired])
def test_linux_status_without_systemctl_keeps_file_evidence(
    unit_exists, error, tmp_path, monkeypatch,
):
    unit = tmp_path / "superlocalmemory.service"
    if unit_exists:
        unit.touch()
    monkeypatch.setattr(service_installer, "_linux_service_path", lambda: unit)
    failure = error("systemctl", 10) if error is subprocess.TimeoutExpired else error()
    monkeypatch.setattr(service_installer.subprocess, "run", MagicMock(side_effect=failure))
    status = service_installer.status_linux()
    assert status["installed"] is unit_exists
    assert status["active"] is False
