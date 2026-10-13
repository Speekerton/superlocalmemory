# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Never move text onto a managed model the answer check was not fitted for.

Recall decides "this is in your memory" with the answer-support recipe
(retrieval/support_recipe.py), which is fitted per text model. "Upgrade memory
engine" moved the author's text to EmbeddingGemma 2 before any recipe existed
for it, and recall refused correct answers on the whole store (13 Oct 2026).

Only the managed models are guarded: they are the ones SuperLocalMemory offers
and upgrades to by itself. A model a person configures (OpenAI, Ollama) is
their choice and keeps today's recipe, as before.
"""

from __future__ import annotations

from typing import Any

MANAGED_PROVIDER = "slm-media"


def refusal_for(target: Any) -> str | None:
    """Why text may not move to ``target`` yet, or None when it may."""
    from superlocalmemory.retrieval import support_recipe

    if getattr(target, "provider", "") != MANAGED_PROVIDER:
        return None
    model = str(getattr(target, "model_name", "") or "")
    if support_recipe.for_model(model) is not None:
        return None
    return (f"{model} is not yet measured for telling a real answer from \"not in memory\", "
            "so moving your text to it could make recall refuse answers it has. Pictures and "
            "documents can use it already. To switch text anyway, use force "
            "(slm embedder switch --force).")


__all__ = ["MANAGED_PROVIDER", "refusal_for"]
