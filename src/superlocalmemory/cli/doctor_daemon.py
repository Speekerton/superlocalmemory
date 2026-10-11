"""Read-only daemon diagnostics: local evidence and one short health probe."""

from __future__ import annotations

from dataclasses import dataclass, field

from superlocalmemory.infra.daemon_identity import DaemonDescriptor
from superlocalmemory.infra.process_identity import compare_start_tokens, process_start_token_for

HEALTH_TIMEOUT = 0.5


@dataclass(frozen=True)
class DaemonCheck:
    status: str
    detail: str
    fix: str = ""
    # Retain a proven identity for other read-only checks, without exposing it.
    descriptor: DaemonDescriptor | None = field(default=None, repr=False)


def _process_evidence(record: DaemonDescriptor) -> str:
    import psutil

    try:
        process = psutil.Process(record.pid)
        if not process.is_running() or process.status() == psutil.STATUS_ZOMBIE:
            return "dead"
        token_match = compare_start_tokens(
            record.process_start_token, process_start_token_for(record.pid),
        )
        if token_match is False:
            return "reused"
        if token_match is None and abs(process.create_time() - record.process_create_time) > 1.0:
            # Legacy/Windows records use creation time. Clock drift is possible;
            # the single health probe may still prove this exact daemon.
            return "identity_changed"
        return "alive"
    except psutil.NoSuchProcess:
        return "dead"


def check_daemon() -> DaemonCheck:
    """Inspect without auto-start, startup waits, or readiness-helper retries."""
    from superlocalmemory.cli import daemon

    try:
        record = daemon.read_descriptor()
        if record is None:
            if daemon.descriptor_path().exists():
                return DaemonCheck(
                    "FAIL", "Daemon descriptor is unreadable or invalid", "slm restart",
                )
            return DaemonCheck("WARN", "Daemon is not running (no descriptor)", "slm serve start")
        evidence = _process_evidence(record)
        if evidence == "dead":
            return DaemonCheck(
                "FAIL", f"Recorded daemon process (pid {record.pid}) is no longer running",
                "slm restart",
            )
        if evidence == "reused":
            return DaemonCheck(
                "FAIL", f"Recorded daemon exited; pid {record.pid} was reused by another process",
                "slm restart",
            )
        health = daemon._fetch_health(record.port, timeout=HEALTH_TIMEOUT)
        matches = health is not None and daemon.descriptor_matches_health(record, health)
        if evidence == "identity_changed" and not matches:
            return DaemonCheck(
                "FAIL", f"Pid {record.pid} no longer matches the recorded daemon identity; "
                "the daemon may have exited or its creation time drifted, "
                "and health could not prove ownership", "slm restart",
            )
        if health is None:
            return DaemonCheck(
                "FAIL", f"Daemon pid {record.pid} did not answer /health "
                f"within {HEALTH_TIMEOUT:g}s",
                "slm restart",
            )
        if not matches:
            return DaemonCheck(
                "FAIL", "Daemon health does not match the recorded identity", "slm restart",
            )
        return DaemonCheck("PASS", f"Running and healthy (pid {record.pid})", descriptor=record)
    except Exception:
        # Keep reporting other checks. Never print private descriptor/exception data.
        return DaemonCheck("WARN", "Daemon availability could not be inspected", "slm serve start")
