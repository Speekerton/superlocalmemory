"""Shared health routes require owner permission and durable undo identities."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from superlocalmemory.server.routes import memory_health


def client(monkeypatch):
    app = FastAPI()
    app.include_router(memory_health.router)
    app.state.engine = SimpleNamespace(_db=Mock())
    monkeypatch.setattr(memory_health, 'report', lambda db: {'enrichment': {'status': 'running'}})
    return TestClient(app)


def test_health_read_obeys_manage_permission(monkeypatch):
    def refuse(*args, **kwargs):
        raise HTTPException(403, 'Owner permission required')
    monkeypatch.setattr(memory_health, 'require_permission', refuse)
    with client(monkeypatch) as session:
        assert session.get('/api/memory-health').status_code == 403


def test_cli_and_dashboard_share_pause_action(monkeypatch):
    monkeypatch.setattr(memory_health, 'require_permission', lambda *a, **k: None)
    monkeypatch.setattr(memory_health.write_identity, 'require_write_actor', lambda *a, **k: 'owner')
    paused = Mock(return_value={'status': 'paused'})
    monkeypatch.setattr(memory_health.EnrichmentRunner, 'pause', paused)
    with client(monkeypatch) as session:
        response = session.post('/api/memory-health/action',
                                json={'action': 'pause', 'run_id': 'synthetic-run'})
        assert response.status_code == 200
        assert response.json()['status'] == 'paused'
        paused.assert_called_once_with('synthetic-run')
