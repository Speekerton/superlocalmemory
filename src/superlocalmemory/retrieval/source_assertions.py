# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
"""Conservative assertion boundaries for extractive source overrides."""
import re

_UNCERTAIN = re.compile(
    r"\b(not|never|no|neither|nor|without|unknown|if|unless|may|might|could|would|"
    r"said|says|claims?|whether|reportedly|false|denied|incorrect|suppose|"
    r"draft|rejected|proposal|proposed|example|quoted|read|wrote|pending|undecided)\b", re.I,
)
_QUOTES = re.compile(r'''["“”‘’`]|(?<!\w)'|'(?!\w)''')


def affirmative_sentences(memory):
    # A quote can span several sentences. Conservatively leave such documents
    # to the classifier instead of losing the context at a sentence boundary.
    if _QUOTES.search(memory):
        return ()
    return tuple(
        sentence.rstrip(".! ").strip()
        for sentence in re.findall(r"[^.!?\n]+(?:[.!?]+|$)", memory)
        if "?" not in sentence and not _UNCERTAIN.search(sentence)
    )
