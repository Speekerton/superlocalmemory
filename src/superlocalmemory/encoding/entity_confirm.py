# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Mode B/C: ask the local model about name pairs the rules cannot settle.

Only ``BORDERLINE`` pairs from ``entity_match`` come here (a one-letter
difference in a short word, an acronym, a longer form of one word). A pair the
rules call different -- other numbers, another word -- is never asked about.

The old prompt gave the model every mention and the first fifty entity names
and accepted any mapping it returned, so a small model could file "Priya"
under "gdrive". Here each pair is a closed yes/no question, and anything but a
clear yes for that exact pair number is a no.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

#: Pairs asked about in one call; the rest stay separate entities.
MAX_PAIRS_PER_CALL = 10

_SYSTEM = "You decide whether two names refer to the same real-world thing. Be strict."


def _prompt(pairs: list[tuple[str, str]]) -> str:
    lines = "".join(f"\n- {i + 1}: \"{a}\" | \"{b}\"" for i, (a, b) in enumerate(pairs))
    return (
        "For each numbered pair, answer true only if both names certainly name the "
        "same person, product, place or thing. Different people with similar names, "
        "different products of one company, and different versions or editions are "
        f"false. When unsure, answer false.{lines}\n\n"
        'Reply with only a JSON object mapping each number to true or false, e.g. '
        '{"1": false, "2": true}'
    )


def _is_yes(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return isinstance(value, str) and value.strip().lower() in ("true", "yes", "same")


def confirm_pairs(llm: Any, pairs: list[tuple[str, str]]) -> list[bool]:
    """One answer per pair; a failed or unclear call answers no for all."""
    if llm is None or not pairs:
        return [False] * len(pairs)
    asked = pairs[:MAX_PAIRS_PER_CALL]
    try:
        response = llm.generate(prompt=_prompt(asked), system=_SYSTEM,
                                max_tokens=16 + 12 * len(asked), temperature=0.0)
        match = re.search(r"\{[^{}]*\}", str(response or ""))
        answers = json.loads(match.group()) if match else {}
    except Exception as exc:  # noqa: BLE001 -- a model failure must not fail a save
        logger.warning("entity pair confirmation failed: %s", exc)
        answers = {}
    if not isinstance(answers, dict):
        answers = {}
    verdicts = [_is_yes(answers.get(str(i + 1))) for i in range(len(asked))]
    return verdicts + [False] * (len(pairs) - len(asked))


__all__ = ["MAX_PAIRS_PER_CALL", "confirm_pairs"]
