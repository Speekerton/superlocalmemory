"""Root-scoped, process-identity checked presence for initialized stdio sessions.

An installed config is not a connection. Records begin at the MCP handshake,
end with the transport, and are ignored when the recorded process has died or
its PID was reused. They contain release and tool names, never credentials.
"""

from __future__ import annotations

import json
import os
import re
import time
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

HOST_NAMES = {
    "claude-code": "Claude Code",
    "claude-desktop": "Claude Desktop",
    "codex": "Codex",
    "hermes": "Hermes",
    "antigravity": "Antigravity",
    "cursor": "Cursor",
    "continue": "Continue",
    "opencode": "OpenCode",
    "windsurf": "Windsurf",
    "gemini-cli": "Gemini CLI",
    "vscode-copilot": "VS Code / Copilot",
    "zed": "Zed",
    "jetbrains": "JetBrains",
    "local-app": "Other local app",
}


def installed_version() -> str:
    try:
        return version("superlocalmemory")
    except PackageNotFoundError:
        from superlocalmemory import __version__

        return __version__


def process_identity(pid: int) -> str | None:
    """Prove a process instance without trusting PID existence alone."""
    try:
        import psutil

        from superlocalmemory.infra.process_identity import process_start_token_for

        process = psutil.Process(pid)
        if not process.is_running() or process.status() == psutil.STATUS_ZOMBIE:
            return None
        return process_start_token_for(pid) or f"created:{process.create_time()!r}"
    except (ImportError, OSError, ValueError, psutil.Error):
        return None


def _path(root: Path, session: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", session):
        raise ValueError("Invalid local MCP session")
    return root / "mcp-processes" / f"{session}.json"


def register(
    root: Path, session: str, *, pid: int, host: str, version: str, tools: list[str]
) -> None:
    identity = process_identity(pid)
    if identity is None:
        raise RuntimeError("Cannot establish local MCP process identity")
    path = _path(root, session)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    row = {
        "session_id": session,
        "pid": pid,
        "process_identity": identity,
        "host": host if host in HOST_NAMES else "local-app",
        "code_version": version,
        "tools": sorted(set(tools)),
        "connected_at": time.time(),
    }
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(row), encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(path)


def unregister(root: Path, session: str) -> None:
    _path(root, session).unlink(missing_ok=True)
    _path(root, session).with_suffix(".reconnect").unlink(missing_ok=True)


def _live_row(path: Path) -> dict[str, Any] | None:
    try:
        row = json.loads(path.read_text(encoding="utf-8"))
        pid = row["pid"]
        if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
            return None
        if row.get("session_id") != path.stem or row.get("host") not in HOST_NAMES:
            return None
        expected = row.get("process_identity")
        if not expected or process_identity(pid) != expected:
            return None
        if not isinstance(row.get("tools"), list) or not isinstance(row.get("code_version"), str):
            return None
        return row
    except (OSError, ValueError, KeyError, TypeError):
        return None


def snapshot(root: Path, *, installed_version: str | None = None) -> dict[str, Any]:
    current = installed_version or globals()["installed_version"]()
    apps = []
    for path in sorted((root / "mcp-processes").glob("*.json")):
        row = _live_row(path)
        if row is not None:
            apps.append(
                {
                    **row,
                    "name": HOST_NAMES[row["host"]],
                    "stale_version": row["code_version"] != current,
                    "version_reported": True,
                    "connection_evidence": "initialized-session",
                }
            )
    from superlocalmemory.infra.mcp_legacy import discover

    apps.extend(discover(root, {row["pid"] for row in apps}))
    hosts = [
        {"host": host, "name": name, "count": sum(a["host"] == host for a in apps)}
        for host, name in HOST_NAMES.items()
        if any(a["host"] == host for a in apps)
    ]
    return {
        "apps": apps,
        "hosts": hosts,
        "count": len(apps),
        "confirmed_count": sum(a["connection_evidence"] == "initialized-session" for a in apps),
        "stale_count": sum(a["stale_version"] for a in apps),
        "unreported_count": sum(a.get("version_reported") is False for a in apps),
        "installed_version": current,
    }


def request_reconnect(root: Path, session: str) -> bool:
    path = _path(root, session)
    row = _live_row(path)
    if row is None:
        from superlocalmemory.infra.mcp_legacy import reconnect

        return reconnect(root, session)
    path.with_suffix(".reconnect").write_text(row["process_identity"], encoding="utf-8")
    return True


def reconnect_requested(root: Path, session: str) -> bool:
    path = _path(root, session)
    row = _live_row(path)
    try:
        return (
            row is not None
            and path.with_suffix(".reconnect").read_text() == row["process_identity"]
        )
    except OSError:
        return False


def host_from_client(params: Any, *, ancestors: list[str] | None = None) -> str:
    explicit = os.environ.get("SLM_MCP_HOST", "")
    if explicit in HOST_NAMES:
        return explicit
    info = getattr(params, "client_info", None)
    client = getattr(info, "name", "") or ""
    names = [client, *(ancestors if ancestors is not None else _ancestor_names())]
    return infer_host(names)


def infer_host(names: list[str]) -> str:
    for name in names:
        text = str(name).lower().replace("_", " ")
        if "claude" in text:
            return "claude-desktop" if "desktop" in text or text == "claude" else "claude-code"
        for host in HOST_NAMES:
            if host not in {"claude-code", "claude-desktop", "local-app"} and host in text:
                return host
    return "local-app"


def _ancestor_names() -> list[str]:
    try:
        import psutil

        return [p.name() for p in psutil.Process().parents()[:8]]
    except (ImportError, OSError, psutil.Error):
        return []
