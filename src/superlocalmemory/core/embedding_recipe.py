# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
"""Versioned Nomic retrieval input. The suffix is part of the stored space ID.

Nomic requires task prefixes: https://huggingface.co/nomic-ai/nomic-embed-text-v1.5
Pattern normalization before tokenization follows the char-filter method:
https://www.elastic.co/docs/reference/text-analysis/analysis-pattern-replace-charfilter
Opaque identifiers are retained in the source/FTS, but removed from the dense
view. This is a measured SLM preprocessing choice, not a claim that BEIR
proposed this transform. BEIR motivates preserving the independent lexical
channel for out-of-domain text: https://arxiv.org/abs/2104.08663 .
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import replace
from typing import Any

TASK_SUFFIX = "@retrieval-v1"
NOMIC = "nomic-embed-text-v1.5"
_TOKEN = re.compile(r"\b[A-Za-z0-9][A-Za-z0-9_-]{23,}\b")


def task_model(model: str) -> str:
    base = model.removesuffix(TASK_SUFFIX)
    if base.rsplit("/", 1)[-1] != NOMIC:
        raise ValueError("Task prefixes are supported only for Nomic v1.5")
    return base + TASK_SUFFIX


def dense_text(text: str) -> str:
    """Remove long opaque codes, preserving ordinary words and source text."""

    def clean(match: re.Match) -> str:
        token = match.group()
        probabilities = [n / len(token) for n in Counter(token.lower()).values()]
        entropy = -sum(p * math.log2(p) for p in probabilities)
        is_hex = bool(re.fullmatch(r"[0-9a-fA-F-]+", token))
        mixed = any(c.isdigit() for c in token) and any(c.isalpha() for c in token)
        return "" if is_hex or (mixed and entropy >= 3.0) else token

    return " ".join(_TOKEN.sub(clean, text).split())


class RecipeEmbedder:
    """Add prompts once at the provider boundary, including bulk/catch-up writes."""

    def __init__(self, delegate: Any, model_name: str = "") -> None:
        self._delegate = delegate
        self.model_name = model_name or task_model("nomic-ai/" + NOMIC)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._delegate, name)

    def embed(self, text: str) -> list[float] | None:
        content = dense_text(text)
        return self._delegate.embed("search_document: " + content)

    def embed_query(self, text: str) -> list[float] | None:
        content = dense_text(text)
        if not content:
            return None  # identifiers remain searchable through exact FTS
        return self._delegate.embed("search_query: " + content)

    def embed_batch(self, texts: list[str]) -> list[list[float] | None]:
        return self._delegate.embed_batch(["search_document: " + dense_text(t) for t in texts])


def build_with_recipe(config: Any, build: Any) -> Any:
    model = config.embedding.model_name
    if not model.endswith(TASK_SUFFIX):
        return build(config)
    task_model(model)  # refuse an unsupported suffix rather than load the wrong model
    if config.embedding.provider not in {"", "sentence-transformers"}:
        raise ValueError("Nomic retrieval-v1 requires the sentence-transformers provider")
    base = replace(
        config.embedding,
        model_name=model.removesuffix(TASK_SUFFIX),
        provider="sentence-transformers", api_endpoint="", api_key="", deployment_name="",
    )
    # A shallow copy keeps all operational configuration on the private target.
    import copy

    target = copy.copy(config)
    target.embedding = base
    delegate = build(target)
    return RecipeEmbedder(delegate, model_name=model) if delegate is not None else None
