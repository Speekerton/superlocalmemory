"""Read-only daemon diagnostics: local evidence and one short health probe."""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, field

from superlocalmemory.infra.daemon_identity import DaemonDescriptor
from superlocalmemory.infra.process_identity import compare_start_tokens, process_start_token_for

HEALTH_TIMEOUT = 0.5
# Includes interpreter startup, local evidence, health and optional features.
CHECK_TIMEOUT = 1.0
MAX_HEALTH_BYTES = 64 * 1024


@dataclass(frozen=True)
class DaemonCheck:
    status: str
    detail: str
    fix: str = ""
    # Retain a proven identity for other read-only checks, without exposing it.
    descriptor: DaemonDescriptor | None = field(default=None, repr=False)
    media_status: dict = field(default_factory=dict)
    # Optional /api/v3/features trouble, reported on its own line. It never
    # changes the verdict of a daemon whose /health was proven.
    feature_warning: str = ""


class ProbeTimeout(Exception):
    """A loopback request ran out of time before it answered."""


def check_daemon() -> DaemonCheck:
    """Bound *all* diagnostic IO, including file reads, by one deadline.

    Socket timeouts only bound inactivity. A disposable read-only interpreter
    lets us interrupt trickling headers/bodies or a blocked descriptor read on
    every platform, without leaving a background thread or child behind.
    """
    deadline = time.monotonic() + CHECK_TIMEOUT
    timed_out = False
    try:
        with subprocess.Popen(
            [sys.executable, "-m", "superlocalmemory.cli.doctor_daemon", str(deadline)],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True,
        ) as worker:
            try:
                output, _ = worker.communicate(timeout=max(0, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                timed_out = True
                worker.kill()
                output, _ = worker.communicate()  # reap; returns everything it wrote
        events = _parse_events(output)
        final = next((e for e in events if e.get("event") == "final"), None)
        if final is not None and not timed_out:
            return _check_from(final)
        if timed_out:
            return _after_deadline(events)
        raise ValueError("diagnostic worker failed")
    except Exception:
        return DaemonCheck("WARN", "Daemon availability could not be inspected", "slm serve start")


def _parse_events(output: str | None) -> list[dict]:
    events = []
    for line in (output or "").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


def _check_from(event: dict) -> DaemonCheck:
    fields = {k: event[k] for k in ("status", "detail", "fix", "media_status", "feature_warning")
              if k in event}
    return DaemonCheck(**fields)


def _after_deadline(events: list[dict]) -> DaemonCheck:
    """Turn what the worker proved before the deadline into an honest verdict."""
    proven = next((e for e in events if e.get("event") == "health_ok"), None)
    if proven is not None:
        # /health already proved this exact daemon; only the optional probe overran.
        proven = dict(proven, feature_warning=(
            f"Optional feature status did not finish within the {CHECK_TIMEOUT:g}s deadline"))
        return _check_from(proven)
    if any(e.get("event") == "stage" and e.get("stage") == "health" for e in events):
        # The daemon was reached but its /health reply never completed: not healthy.
        return DaemonCheck(
            "FAIL", "Daemon /health reply was unreadable (it did not finish within "
            f"the {CHECK_TIMEOUT:g}s deadline)", "slm restart",
        )
    return DaemonCheck(
        "WARN", f"Daemon diagnostic exceeded its {CHECK_TIMEOUT:g}s deadline", "slm restart",
    )


def _fetch_json(record: DaemonDescriptor, path: str, timeout: float) -> dict | None:
    """One direct loopback request, no redirects/proxies, capped and closed."""
    import os
    import urllib.request

    from superlocalmemory.core import outbound_http

    headers = {}
    if path != "/health":
        headers = {"X-SLM-Daemon-Capability": record.capability,
                   "X-SLM-Target-Instance": record.instance_id}
        user_session = os.environ.get("SLM_USER_SESSION", "").strip()
        if user_session:
            headers["X-SLM-User-Session"] = user_session
    request = urllib.request.Request(f"http://127.0.0.1:{record.port}{path}", headers=headers)
    try:
        with outbound_http.urlopen(request, timeout=max(0.001, timeout)) as response:
            payload = response.read(MAX_HEALTH_BYTES + 1)
            if len(payload) > MAX_HEALTH_BYTES:
                raise ValueError("Daemon diagnostic response is too large")
            result = json.loads(payload)
            return result if isinstance(result, dict) else None
    except json.JSONDecodeError:
        return None
    except (TimeoutError, socket.timeout):
        raise ProbeTimeout from None
    except OSError as exc:
        if isinstance(getattr(exc, "reason", None), (TimeoutError, socket.timeout)):
            raise ProbeTimeout from None
        return None


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


def _inspect_daemon(deadline: float | None = None, emit=None) -> DaemonCheck:
    """Inspect without auto-start, startup waits, or readiness-helper retries."""
    from superlocalmemory.cli import daemon

    deadline = deadline if deadline is not None else time.monotonic() + CHECK_TIMEOUT
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
        if emit is not None:
            emit({"event": "stage", "stage": "health"})
        try:
            health = _fetch_json(
                record, "/health", min(HEALTH_TIMEOUT, deadline - time.monotonic()),
            )
        except ProbeTimeout:
            health = None
        except ValueError:
            return DaemonCheck(
                "FAIL", f"Daemon pid {record.pid} sent an oversized or unreadable /health "
                "reply", "slm restart",
            )
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
        proven = DaemonCheck("PASS", f"Running and healthy (pid {record.pid})", descriptor=record)
        if emit is not None:
            emit({"event": "health_ok", **_public(proven)})
        feature_warning = ""
        features = None
        try:
            features = _fetch_json(
                record, "/api/v3/features", min(HEALTH_TIMEOUT, deadline - time.monotonic()),
            )
        except ProbeTimeout:
            feature_warning = f"Optional feature status did not answer within {HEALTH_TIMEOUT:g}s"
        except ValueError:
            feature_warning = "Optional feature status reply was oversized"
        media = (features or {}).get("media") or {}
        return DaemonCheck(
            "PASS", proven.detail, descriptor=record, feature_warning=feature_warning,
            media_status={"restart_required": bool(media.get("restart_required"))},
        )
    except Exception:
        # Keep reporting other checks. Never print private descriptor/exception data.
        return DaemonCheck("WARN", "Daemon availability could not be inspected", "slm serve start")


def _public(result: DaemonCheck) -> dict:
    # Only public diagnostic data crosses the pipe. Never serialize credentials.
    return {"status": result.status, "detail": result.detail, "fix": result.fix,
            "media_status": result.media_status, "feature_warning": result.feature_warning}


def _emit(event: dict) -> None:
    print(json.dumps(event), flush=True)


if __name__ == "__main__":
    _emit({"event": "final", **_public(_inspect_daemon(float(sys.argv[1]), emit=_emit))})
