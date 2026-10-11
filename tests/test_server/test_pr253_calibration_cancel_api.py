"""PR-253 #6: per-run cancellation is exposed through the credential/MANAGE gate."""
from unittest.mock import Mock

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from superlocalmemory.server.routes import answer_check


def test_cancel_route_exists_and_cancels_job_after_both_gates(monkeypatch):
    app = FastAPI()
    job = Mock()
    job.cancel.return_value = {"state": "cancelling"}
    app.state.answer_calibration_job = job
    app.include_router(answer_check.router)
    seen = []
    monkeypatch.setattr(answer_check, "_require_credential", lambda r: seen.append("credential"))
    monkeypatch.setattr(answer_check, "_require_manage", lambda r: seen.append("manage"))
    with TestClient(app) as client:
        response = client.post("/api/v3/answer-check/calibration/cancel")
    assert response.status_code == 202
    assert seen == ["credential", "manage"]
    job.cancel.assert_called_once()


def test_viewer_cannot_cancel_with_valid_credential(monkeypatch):
    app = FastAPI()
    job = Mock()
    app.state.answer_calibration_job = job
    app.include_router(answer_check.router)
    monkeypatch.setattr(answer_check, "_require_credential", lambda r: None)

    def denied(request):
        raise HTTPException(403, "manage required")

    monkeypatch.setattr(answer_check, "_require_manage", denied)
    with TestClient(app) as client:
        assert client.post("/api/v3/answer-check/calibration/cancel").status_code == 403
    job.cancel.assert_not_called()
