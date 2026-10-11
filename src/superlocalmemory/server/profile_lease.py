"""Transfer already-admitted foreground work without re-entering admission."""

import threading
from contextlib import contextmanager
from contextvars import ContextVar

_REQUEST_LEASE = ContextVar("slm_request_lease", default=None)


class OperationLease:
    """One counted admission; forks keep its generation alive independently."""

    def __init__(self, runtime, snapshot):
        self.runtime = runtime
        self.snapshot = snapshot
        self._lock = threading.Lock()
        self._released = False

    def fork(self):
        return self.runtime.retain_operation(self)

    def release(self):
        with self._lock:
            if not self._released:
                self._released = True
                self.runtime.release_operation()


def current_request_lease():
    return _REQUEST_LEASE.get()


def release_late_lease(task):
    """Release shielded native-thread admission even after repeated cancellation."""
    if not task.cancelled() and task.exception() is None:
        task.result().release()


@contextmanager
def bind_request_lease(lease):
    token = _REQUEST_LEASE.set(lease)
    try:
        yield
    finally:
        _REQUEST_LEASE.reset(token)
