# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
"""OOV-only Nomic phrases require lexical evidence, including on legacy stores.

This is a retrieval policy, not a new query vector: rejected phrases still run
keyword retrieval. Normal questions with known vocabulary remain eligible for
zero-overlap semantic retrieval. Cache lookup is read-only/offline; no weights
or tokenizer runtime are loaded into the parent process. BEIR's lexical/dense
OOD comparison motivates retaining that independent lexical path:
https://arxiv.org/abs/2104.08663 . The exact policy is measured by SLM's harness.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

_MODEL = "nomic-ai/nomic-embed-text-v1.5"
_WORD = re.compile(r"[A-Za-z]+")


def vocabulary() -> frozenset[str] | None:
    try:
        from huggingface_hub import try_to_load_from_cache
        path = try_to_load_from_cache(_MODEL, "vocab.txt")
        if not isinstance(path, str):
            return None
        return _read_vocabulary(path)
    except (ImportError, OSError, ValueError):
        return None  # no cache is never a reason to reject a query


def oov_phrase(query: str, vocab: frozenset[str] | None) -> bool:
    words = _WORD.findall(query)
    # Do not guess at single identifiers, numbers or non-Latin languages.
    plain = " ".join(words)
    if len(words) < 3 or not re.fullmatch(r"[A-Za-z\s?!.,'-]+", query):
        return False
    return bool(plain and vocab and not any(word.lower() in vocab for word in words))


def requires_lexical(embedder, query: str) -> bool:
    config = getattr(embedder, "_config", None)
    name = getattr(config, "model_name", None)
    if not isinstance(name, str):
        return False
    if name.removesuffix("@retrieval-v1").rsplit("/", 1)[-1] != _MODEL.split("/")[-1]:
        return False
    return oov_phrase(query, vocabulary())


@lru_cache(maxsize=1)
def _read_vocabulary(path: str) -> frozenset[str]:
    return frozenset(Path(path).read_text(encoding="utf-8").splitlines())
