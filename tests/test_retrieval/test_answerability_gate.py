# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
"""The answer-or-abstain gate, measured on a ~2,000-memory synthetic store.

Slow: builds the store with the real embedding model and asks every question
through the real recall pipeline with the real cross-encoder
(scripts/quality/answerability_eval.py). The gate: every nonsense question
abstains, and every real question finds its memory in the top 5.

This FAILS on the recall that shipped before the answerability work: ID-heavy
memories clear the evidence floor for random text, so nonsense is answered.
Set ``SLM_ANSWERABILITY_CACHE`` to a folder to reuse a built store between runs.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow
ROOT = Path(__file__).resolve().parents[2]


def _harness():
    name = "answerability_eval"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            name, ROOT / "scripts" / "quality" / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


@pytest.fixture(scope="module")
def report(tmp_path_factory):
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    os.environ["SLM_HUB_BASELINE_BACKFILL"] = "0"
    cache = os.environ.get("SLM_ANSWERABILITY_CACHE")
    work = tmp_path_factory.mktemp("answerability")
    return _harness().run(work, ["a"], Path(cache) if cache else None)


def test_every_nonsense_question_abstains(report) -> None:
    profile = report["profiles"][0]
    assert profile["nonsense_abstain_rate"] == 1.0, profile["failures"]["nonsense_answered"]


def test_every_real_question_finds_its_memory_in_the_top_five(report) -> None:
    profile = report["profiles"][0]
    assert profile["real_top5_hit_rate"] == 1.0, profile["failures"]["real_missed"]
