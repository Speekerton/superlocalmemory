# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
"""The answer-support recipe is chosen by the text model it was fitted on.

answer-support-v2 was fitted on nomic cosines only. On the author's store, after
"Upgrade memory engine" moved text to EmbeddingGemma 2, it scored a correct
memory at 0.008 against a 0.30 bar and recall said "That isn't in
SuperLocalMemory" to questions it had answered that morning (13 Oct 2026).

So: a model with a fitted recipe uses it; nothing may move text onto a managed
model that has none (the upgrade plan says why, an explicit switch needs
force); and every other model keeps today's recipe, so a patch release changes
no one else's recall.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from superlocalmemory.core import engine_upgrade, support_fit_guard
from superlocalmemory.core.config import EmbeddingConfig
from superlocalmemory.core.support_stage import recipe_for
from superlocalmemory.retrieval import support_recipe as sr

NOMIC = "nomic-ai/nomic-embed-text-v1.5"
GEMMA = "google/embeddinggemma-2"


@pytest.fixture
def no_gemma_fit(monkeypatch):
    """Whatever this build ships, measure the rule as if Gemma had no fit."""
    monkeypatch.setattr(sr, "_BY_MODEL", {NOMIC: sr.ANSWER_SUPPORT_V2})


def test_nomic_has_its_fitted_recipe():
    assert sr.for_model(NOMIC) is sr.ANSWER_SUPPORT_V2
    assert sr.for_model(f"{NOMIC}::768") is sr.ANSWER_SUPPORT_V2
    assert sr.for_model("nomic-embed-text-v1.5") is sr.ANSWER_SUPPORT_V2


def test_a_model_never_fitted_has_none(no_gemma_fit):
    assert sr.for_model(GEMMA) is None
    assert sr.for_model("") is None


def test_recall_uses_the_live_models_recipe(monkeypatch):
    other = sr.ANSWER_SUPPORT_V1
    monkeypatch.setattr(sr, "_BY_MODEL", {NOMIC: sr.ANSWER_SUPPORT_V2, GEMMA: other})
    engine = SimpleNamespace(_embedder=SimpleNamespace(model_name=GEMMA))
    assert recipe_for(engine) is other


def test_any_other_model_keeps_todays_recipe(no_gemma_fit):
    for embedder in (SimpleNamespace(model_name="text-embedding-3-small"), None):
        assert recipe_for(SimpleNamespace(_embedder=embedder)) is sr.ACTIVE


def test_moving_text_to_an_unfitted_managed_model_is_refused(no_gemma_fit):
    target = EmbeddingConfig(model_name=GEMMA, dimension=768, provider="slm-media")
    reason = support_fit_guard.refusal_for(target)
    assert reason and "force" in reason


def test_fitted_or_unmanaged_targets_are_not_refused(no_gemma_fit):
    assert support_fit_guard.refusal_for(EmbeddingConfig(model_name=NOMIC)) is None
    openai = EmbeddingConfig(model_name="text-embedding-3-small", dimension=1536, provider="openai")
    assert support_fit_guard.refusal_for(openai) is None


def test_the_upgrade_plan_says_why_it_cannot_start(no_gemma_fit):
    live = EmbeddingConfig(model_name=NOMIC, dimension=768, provider="sentence-transformers")
    p = engine_upgrade.plan(live, 1000, "ready", media_enabled=True)
    assert p["available"] is False
    assert p["reason"] == support_fit_guard.refusal_for(engine_upgrade.upgrade_target(live))


def test_the_upgrade_plan_opens_once_the_model_is_fitted(monkeypatch):
    monkeypatch.setattr(sr, "_BY_MODEL", {NOMIC: sr.ANSWER_SUPPORT_V2, GEMMA: sr.ANSWER_SUPPORT_V2})
    live = EmbeddingConfig(model_name=NOMIC, dimension=768, provider="sentence-transformers")
    assert engine_upgrade.plan(live, 1000, "ready", media_enabled=True)["available"] is True


def test_an_explicit_switch_is_refused_unless_forced(no_gemma_fit):
    import json

    from superlocalmemory.server.routes.embedding_reindex import unfitted_refusal

    target = EmbeddingConfig(model_name=GEMMA, dimension=768, provider="slm-media")
    refused = unfitted_refusal({"model_name": GEMMA}, target)
    assert refused is not None and refused.status_code == 409
    assert json.loads(refused.body)["error"] == "not_fitted"
    assert unfitted_refusal({"model_name": GEMMA, "force": True}, target) is None


def test_the_cli_sends_force_only_when_asked(monkeypatch):
    from argparse import Namespace

    from superlocalmemory.cli import embedder_cmd

    bodies = []
    monkeypatch.setattr(embedder_cmd, "daemon_request",
                        lambda method, path, body=None, **kw: bodies.append(body) or {
                            "success": True, "job": {"job_id": 1, "kind": "switch",
                                                     "state": "queued", "from": "a::1", "to": "b::2",
                                                     "done": 0, "total": 1}})
    base = dict(embedder_command="switch", json=False, model=GEMMA, dimension=0,
                provider="", endpoint="", no_wait=True)
    embedder_cmd.cmd_embedder(Namespace(**base))
    embedder_cmd.cmd_embedder(Namespace(**base, force=True))
    assert "force" not in bodies[0]
    assert bodies[1]["force"] is True
