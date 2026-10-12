"""Idle health work yields to users, RAM pressure and background transitions."""

from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import Mock

from superlocalmemory.core.recall_gate import begin_recall, end_recall


def test_health_service_uses_ram_gate_and_never_runs_during_foreground(monkeypatch):
    from superlocalmemory.server.memory_health_service import MemoryHealthService
    engine = SimpleNamespace(_db=Mock(), _llm=None, _retrieval_engine=None)
    state = SimpleNamespace(engine=engine, profile_runtime=None)
    service = MemoryHealthService(state, idle=lambda: True)
    batch = Mock()
    monkeypatch.setattr(service, '_improve', batch)
    calls = []

    @contextmanager
    def reservation(*args, **kwargs):
        calls.append(kwargs)
        yield
    monkeypatch.setattr('superlocalmemory.core.ram_lock.ram_reservation', reservation)
    begin_recall()
    try:
        assert service.tick() is False
        batch.assert_not_called()
    finally:
        end_recall()
    assert service.tick()
    assert calls[0]['timeout_s'] == 0
    batch.assert_called_once()


def test_health_service_respects_background_pause_and_ram_refusal(monkeypatch):
    from superlocalmemory.server.memory_health_service import MemoryHealthService
    runtime = SimpleNamespace(background_paused=True, transitioning=False)
    state = SimpleNamespace(engine=SimpleNamespace(_db=Mock()), profile_runtime=runtime)
    service = MemoryHealthService(state, idle=lambda: True)
    batch = Mock()
    monkeypatch.setattr(service, '_improve', batch)
    assert not service.tick()
    runtime.background_paused = False

    @contextmanager
    def refusal(*args, **kwargs):
        raise RuntimeError('low RAM')
        yield
    monkeypatch.setattr('superlocalmemory.core.ram_lock.ram_reservation', refusal)
    assert not service.tick()
    batch.assert_not_called()
    assert service.health()['detail']
