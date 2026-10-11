"""Wall time, bounded payloads and cleanup for real diagnostic IO."""

import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import psutil
import pytest

from superlocalmemory.cli.doctor_daemon import HEALTH_TIMEOUT, check_daemon
from superlocalmemory.infra.daemon_identity import build_descriptor, write_descriptor


@pytest.mark.parametrize("behavior", ["silent", "stream", "large", "features", "healthy"])
def test_whole_diagnostic_has_one_deadline(free_port, behavior):
    record = build_descriptor(port=free_port, version="test", pid=os.getpid())
    write_descriptor(record)
    stop = threading.Event()
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append(self.path)
            try:
                if behavior == "silent":
                    stop.wait(2)
                    return
                self.send_response(200)
                self.end_headers()
                if behavior == "stream" or (behavior == "features" and self.path != "/health"):
                    until = time.monotonic() + 2
                    while time.monotonic() < until and not stop.wait(0.05):
                        self.wfile.write(b" ")
                        self.wfile.flush()
                    return
                payload = (b" " * 100_000 if behavior == "large" else
                           json.dumps(record.public_health_fields() if self.path == "/health"
                                      else {"media": {"restart_required": True}}).encode())
                self.wfile.write(payload)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", free_port), Handler)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01})
    thread.start()
    children = {p.pid for p in psutil.Process().children()}
    began = time.monotonic()
    try:
        result = check_daemon()
        elapsed = time.monotonic() - began
        assert elapsed < HEALTH_TIMEOUT + 0.2, f"diagnostic took {elapsed:.3f}s"
        assert requests.count("/health") == 1
        assert {p.pid for p in psutil.Process().children()} == children
        if behavior == "healthy":
            assert result.status == "PASS"
        else:
            assert result.status in {"WARN", "FAIL"}
            assert any(word in result.detail.lower() for word in ("deadline", "within", "large"))
    finally:
        stop.set()
        server.shutdown()
        server.server_close()
        thread.join(2)
        assert not thread.is_alive()


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="POSIX named pipe")
def test_descriptor_read_is_inside_deadline(tmp_path):
    os.mkfifo(tmp_path / "daemon.json")
    # Permit the old reader to finish after 1s so RED does not hang pytest.
    def unblock():
        time.sleep(1)
        try:
            fd = os.open(tmp_path / "daemon.json", os.O_WRONLY | os.O_NONBLOCK)
        except OSError:
            return  # A bounded worker has already closed its reader.
        os.write(fd, b"{}")
        os.close(fd)

    thread = threading.Thread(target=unblock)
    thread.start()
    began = time.monotonic()
    try:
        result = check_daemon()
        assert time.monotonic() - began < HEALTH_TIMEOUT + 0.2
        assert result.status in {"WARN", "FAIL"}
    finally:
        thread.join(2)
