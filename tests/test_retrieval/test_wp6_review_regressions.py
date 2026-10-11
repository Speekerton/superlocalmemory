"""Raw evidence and model-space calibration regressions."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest


def test_raw_semantic_evidence_is_not_fisher_probability(monkeypatch):
    from superlocalmemory.retrieval.semantic_channel import SemanticChannel
    from superlocalmemory.storage.models import AtomicFact

    fact = AtomicFact(fact_id="noise", embedding=[0.0, 1.0], fisher_variance=[1.0, 1.0])
    db = Mock()
    db.get_all_facts.return_value = [fact]
    channel = SemanticChannel(db)
    monkeypatch.setattr(channel, "_fisher_weight", lambda count: 1.0)
    monkeypatch.setattr(channel, "_compute_fisher_sim", lambda *args: 0.99)
    assert channel.search([1.0, 0.0], "default")[0][1] == pytest.approx(0.5)


def test_eg2_uses_store_measurement_instead_of_provisional_floor(tmp_path, monkeypatch):
    import json

    from superlocalmemory.retrieval.text_floor import text_semantic_floor
    from superlocalmemory.runtimes.media_models import EG2_REPO

    monkeypatch.setenv("SLM_DATA_DIR", str(tmp_path))
    payload = {
        "schema": "superlocalmemory.answer-check-calibration/v1",
        "entries": [
            {
                "backend": "laya",
                "recipe_id": "sufficiency-v1",
                "threshold": 0.6,
                "answered": 28,
                "unanswered": 14,
            }
        ],
        "semantic": [
            {"signature": EG2_REPO + "::768", "raw_floor": 0.72, "answered": 28, "unanswered": 14}
        ],
    }
    (tmp_path / "answer_check_calibration.json").write_text(json.dumps(payload))
    assert text_semantic_floor(SimpleNamespace(model_name=EG2_REPO, dimension=768), 0.60) == 0.72
