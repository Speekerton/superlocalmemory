"""Reject malformed approval, and recover a verified artifact after restart."""

import json

import pytest

from superlocalmemory.evolution.blind_verifier import parse_verification_response
from superlocalmemory.evolution.evolution_store import EvolutionStore
from superlocalmemory.evolution.types import (
    EvolutionRecord,
    EvolutionStatus,
    EvolutionType,
    TriggerType,
)


@pytest.mark.parametrize("passed", ["false", "true", 1, None])
def test_verifier_requires_a_boolean(passed):
    result = parse_verification_response(json.dumps({"passed": passed, "confidence": 0.9}))
    assert result.passed is False


def test_artifact_directory_reconstructed_from_verified_transition(tmp_path):
    path = tmp_path / "memory.db"
    store = EvolutionStore(path)
    record = EvolutionRecord("r1", "review", None, EvolutionType.FIX, TriggerType.DEGRADATION)
    store.insert_record(record, "default")
    store.append_transition(
        "r1",
        "default",
        EvolutionStatus.CANDIDATE,
        EvolutionStatus.VERIFIED_QUARANTINED,
        metadata={"quarantine_dir_name": "review-v123"},
    )
    loaded = EvolutionStore(path).get_record("r1", "default")
    assert loaded.quarantine_dir_name == "review-v123"
    assert loaded.blind_verified is True
    assert EvolutionStore(path).get_record("r1", "other") is None
