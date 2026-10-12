# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later
"""Guidance on which extraction model to use. It only reads; it recommends and never changes models on its own."""

from __future__ import annotations

from superlocalmemory.core.model_catalog import best_local_llm


def local_model_finding(config, installed: list[str], ram_gb: float | None = None):
    chosen = config.llm.model
    have = {name.removesuffix(":latest") for name in installed if ":cloud" not in name}
    base = chosen.removesuffix(":latest")
    if base not in have:
        return (
            "WARN",
            f"{chosen} is not installed at the configured endpoint",
            "Choose an installed model with slm setup; no model was changed.",
        )
    best = best_local_llm(ram_gb, list(have))
    if best != base and best in have:
        return (
            "WARN",
            f"{chosen} is configured; {best} is the recommended installed model",
            f"Choose {best} explicitly with slm setup; no model was changed.",
        )
    return ("PASS", f"{chosen} is installed; no better installed recommendation", "")
