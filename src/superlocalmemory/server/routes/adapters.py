# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Ingestion adapter management API — enable/disable/start/stop from dashboard.

v3.4.4: Users can manage Gmail, Calendar, Transcript adapters entirely from
the dashboard UI — no CLI needed. The best product experience.

Endpoints:
  GET  /api/adapters         — list all adapters with status
  POST /api/adapters/enable  — enable an adapter
  POST /api/adapters/disable — disable an adapter
  POST /api/adapters/start   — start a running adapter
  POST /api/adapters/stop    — stop a running adapter
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["adapters"])


class AdapterAction(BaseModel):
    name: str


class AdapterSetup(AdapterAction):
    path: str


@router.post("/api/adapters/configure")
async def configure_adapter_api(body: AdapterSetup, request: Request):
    from pathlib import Path

    from fastapi import HTTPException

    from superlocalmemory.ingestion.adapter_manager import _load_config, _save_config
    from superlocalmemory.server.rbac_enforce import require_manage

    require_manage(request)
    if body.name not in ("gmail", "calendar", "transcript"):
        raise HTTPException(422, "Choose a supported adapter.")
    path = Path(body.path).expanduser()
    if not path.is_absolute() or not path.exists():
        raise HTTPException(422, "Choose an existing absolute folder or file path.")
    if body.name == "transcript" and not path.is_dir():
        raise HTTPException(422, "Transcripts need a folder.")
    if body.name != "transcript" and not path.is_file():
        raise HTTPException(422, "Choose an MBOX or ICS file.")
    field = {"transcript": "watch_dir", "gmail": "mbox_path", "calendar": "ics_path"}[body.name]
    config = _load_config()
    config.setdefault(body.name, {}).update({field: str(path), "tier": "auto"})
    _save_config(config)
    return {"ok": True, "message": "Setup saved. Retry Start."}


@router.get("/api/adapters")
async def list_adapters_api():
    """List all adapters with their enabled/running status."""
    from superlocalmemory.ingestion.adapter_manager import list_adapters
    adapters = list_adapters()
    return {"adapters": adapters}


@router.post("/api/adapters/enable")
async def enable_adapter_api(body: AdapterAction):
    """Enable an adapter (doesn't start it yet)."""
    from superlocalmemory.ingestion.adapter_manager import enable_adapter
    return enable_adapter(body.name)


@router.post("/api/adapters/disable")
async def disable_adapter_api(body: AdapterAction):
    """Disable and stop an adapter."""
    from superlocalmemory.ingestion.adapter_manager import disable_adapter
    return disable_adapter(body.name)


@router.post("/api/adapters/start")
async def start_adapter_api(body: AdapterAction):
    """Start a running adapter subprocess."""
    from superlocalmemory.ingestion.adapter_manager import start_adapter
    return start_adapter(body.name)


@router.post("/api/adapters/stop")
async def stop_adapter_api(body: AdapterAction):
    """Stop a running adapter."""
    from superlocalmemory.ingestion.adapter_manager import stop_adapter
    return stop_adapter(body.name)
