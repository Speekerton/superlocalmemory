"""Dashboard-only adapters for hosts outside the portable editor writers."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from superlocalmemory.cli.deployment import security_environment
from superlocalmemory.infra.data_root import canonical_data_root


def configure_hermes(profile: str) -> bool:
    import yaml

    path = Path.home() / ".hermes" / "config.yaml"
    config = yaml.safe_load(path.read_text()) if path.exists() else {}
    if config is None:
        config = {}
    if not isinstance(config, dict) or not isinstance(config.get("mcp_servers", {}), dict):
        raise ValueError("Hermes settings must contain an MCP server mapping")
    block = {
        "command": sys.executable,
        "args": ["-m", "superlocalmemory.cli.main", "mcp"],
        "env": {
            "SLM_MCP_PROFILE": profile,
            "SLM_MCP_HOST": "hermes",
            "SLM_DATA_DIR": str(canonical_data_root()),
            **security_environment(),
        },
    }
    updated = {
        **config,
        "mcp_servers": {**config.get("mcp_servers", {}), "superlocalmemory": block},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".slm.tmp")
    temporary.write_text(yaml.safe_dump(updated, sort_keys=False))
    os.chmod(temporary, 0o600)
    temporary.replace(path)
    return True


def configure_claude_code(profile: str) -> bool:
    executable = shutil.which("claude")
    if not executable:
        raise ValueError("Claude Code is not installed. Install the app, then refresh this page.")
    # Use the host's supported config command rather than editing its files.
    env = {**os.environ, "SLM_MCP_PROFILE": profile, "SLM_MCP_HOST": "claude-code"}
    args = [
        executable,
        "mcp",
        "add",
        "superlocalmemory",
        "--scope",
        "user",
        "--transport",
        "stdio",
        "--env",
        f"SLM_DATA_DIR={canonical_data_root()}",
        "--env",
        f"SLM_MCP_PROFILE={profile}",
        "--env",
        "SLM_MCP_HOST=claude-code",
        "--",
        sys.executable,
        "-m",
        "superlocalmemory.cli.main",
        "mcp",
    ]
    policy = [part for key, value in security_environment().items()
              for part in ("--env", f"{key}={value}")]
    args[args.index("--"):args.index("--")] = policy
    result = subprocess.run(args, env=env, capture_output=True, timeout=30, check=False)
    return result.returncode == 0
