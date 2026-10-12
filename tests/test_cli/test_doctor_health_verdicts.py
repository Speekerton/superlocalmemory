"""An unreadable /health is a failed daemon; optional features never mask a proven one."""

import json
import threading
import time
from argparse import Namespace
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from superlocalmemory.cli import commands
from superlocalmemory.cli.doctor_daemon import CHECK_TIMEOUT, check_daemon
from superlocalmemory.infra.daemon_identity import build_descriptor, write_descriptor


def _serve(free_port, behavior):
    import os

    record = build_descriptor(port=free_port, version="test", pid=os.getpid())
    write_descriptor(record)
    stop = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            try:
                self.send_response(200)
                self.end_headers()
                if behavior == "stream" or (behavior == "features" and self.path != "/health"):
                    until = time.monotonic() + 3
                    while time.monotonic() < until and not stop.wait(0.05):
                        self.wfile.write(b" ")
                        self.wfile.flush()
                    return
                if behavior == "large":
                    self.wfile.write(b" " * 100_000)
                    return
                body = (record.public_health_fields() if self.path == "/health"
                        else {"media": {}})
                self.wfile.write(json.dumps(body).encode())
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", free_port), Handler)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01})
    thread.start()

    def close():
        stop.set()
        server.shutdown()
        server.server_close()
        thread.join(2)

    return close


@pytest.mark.parametrize("behavior", ["stream", "large"])
def test_unreadable_health_fails_with_exit_one(free_port, capsys, behavior):
    close = _serve(free_port, behavior)
    began = time.monotonic()
    try:
        result = check_daemon()
        assert time.monotonic() - began < CHECK_TIMEOUT + 0.3
        assert result.status == "FAIL"
        assert "health" in result.detail.lower()
        with pytest.raises(SystemExit) as exc:
            commands.cmd_doctor(Namespace(json=True, quick=True))
        assert exc.value.code == 1
    finally:
        close()
    checks = {c["name"]: c for c in json.loads(capsys.readouterr().out)["data"]["checks"]}
    assert checks["Daemon"]["status"] == "FAIL"


def test_feature_timeout_keeps_proven_daemon_pass(free_port, capsys):
    close = _serve(free_port, "features")
    began = time.monotonic()
    try:
        result = check_daemon()
        assert time.monotonic() - began < CHECK_TIMEOUT + 0.3
        assert result.status == "PASS"
        assert result.feature_warning
        try:
            commands.cmd_doctor(Namespace(json=True, quick=True))
        except SystemExit:
            pass
    finally:
        close()
    checks = {c["name"]: c for c in json.loads(capsys.readouterr().out)["data"]["checks"]}
    assert checks["Daemon"]["status"] == "PASS"
    assert checks["Daemon features"]["status"] == "WARN"
