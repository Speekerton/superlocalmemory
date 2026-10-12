# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later
"""One owned idle worker for automatic memory health, including enrichment."""

from __future__ import annotations

import contextlib
import logging
import threading

from superlocalmemory.core.enrichment import EnrichmentRunner
from superlocalmemory.core.recall_gate import background_work, in_flight

logger = logging.getLogger(__name__)


class MemoryHealthService:
    name = 'memory-health'

    def __init__(self, state, *, idle):
        self.state = state
        self.idle = idle
        self._stop = threading.Event()
        self._thread = None
        self._detail = ''

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name='slm-memory-health', daemon=True)
        self._thread.start()

    def stop(self, timeout_s=10.0):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout_s)
        return self._thread is None or not self._thread.is_alive()

    def health(self):
        alive = self._thread is not None and self._thread.is_alive()
        return {'state': 'running' if alive else 'stopped', 'detail': self._detail}

    def can_work(self):
        runtime = getattr(self.state, 'profile_runtime', None)
        paused = runtime is not None and (
            runtime.background_paused or getattr(runtime, 'transitioning', False))
        foreground = (getattr(runtime, '_active_operations', 0)
                      > getattr(runtime, '_background_active', 0))
        return not (self._stop.is_set() or paused or foreground or in_flight()) and self.idle()

    def tick(self):
        if not self.can_work():
            return False
        engine = getattr(self.state, 'engine', None)
        if engine is None or getattr(engine, '_db', None) is None:
            return False
        runtime = getattr(self.state, 'profile_runtime', None)
        lease = runtime.operation_nowait() if runtime and hasattr(runtime, 'operation_nowait')             else contextlib.nullcontext(True)
        try:
            from superlocalmemory.core.ram_lock import ram_reservation
            with lease as admitted:
                if admitted is None or not self.can_work():
                    return False
                with ram_reservation('memory-health', timeout_s=0, required_mb=64):
                    with background_work(preempt_requested=lambda: not self.can_work()):
                        self._improve(engine)
            self._detail = ''
            return True
        except Exception as exc:
            self._detail = type(exc).__name__
            logger.debug('Memory health is waiting (%s)', self._detail)
            return False

    def _improve(self, engine):
        # This classifier can only ask the already-running local judge or local
        # Ollama. The user's optional hosted-kind backend is never invoked here.
        from superlocalmemory.core.memory_kind_config import MemoryKindConfig
        from superlocalmemory.core.memory_kind_wiring import live_judge
        from superlocalmemory.encoding.local_description_kinds import LocalDescriptionKinds
        from superlocalmemory.encoding.memory_kind_classifier import KindClassifier
        from superlocalmemory.storage.models import Mode

        delegate = KindClassifier(config=MemoryKindConfig(backend='laya'), mode=Mode.A,
                                  judge_supplier=lambda: live_judge(engine), llm_available=False)
        classifier = LocalDescriptionKinds(delegate=delegate,
                                           llm_supplier=lambda: getattr(engine, '_llm', None))
        runner = EnrichmentRunner(engine._db, idle=self.can_work, classifier=classifier)
        runner.run_batch(limit=25)
        if self.can_work():
            from superlocalmemory.core.health_repairs import run_safe_repairs
            run_safe_repairs(engine, idle=self.can_work)

    def _loop(self):
        while not self._stop.wait(5.0):
            self.tick()


def start_memory_health(application, registry, idle):
    service = MemoryHealthService(application.state, idle=idle)
    application.state.memory_health_service = service
    registry.register(service)
    registry.start(service.name)
    return service
