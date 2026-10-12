# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later
"""Conservative receipt/stub detection, independent of fact length."""

from __future__ import annotations

import re

_EMPTY = re.compile(r'^[\s\[\]{}(),;:]*$')
_SESSION = re.compile(r'^(?:\[\]\s*)?session\s+(?:ended|closed)(?:\s+at)?'
                      r'(?:\s+[\dT:+Z. /-]+)?[.!]?$', re.I)
_RECEIPT = re.compile(r'^(?:(?:receipt|operation|session|fact|memory|run)[ _-]?id\s*[:=]\s*'
                      r'|receipt\s*:\s*)[a-z0-9_-]{8,}[.!]?$', re.I)


def is_stub(text: str) -> bool:
    value = (text or '').strip()
    return bool(value and (_EMPTY.fullmatch(value) or _SESSION.fullmatch(value)
                           or _RECEIPT.fullmatch(value)))


def has_marker(db) -> bool:
    if getattr(db, '_non_answer_column_present', False):
        return True
    present = any(r['name'] == 'non_answer'
                  for r in db.execute('PRAGMA table_info(atomic_facts)'))
    if present:
        db._non_answer_column_present = True
    return present


def mark(db, fact_id, profile_id, content):
    if has_marker(db):
        db.execute('UPDATE atomic_facts SET non_answer=? WHERE fact_id=? AND profile_id=?',
                   (int(is_stub(content)), fact_id, profile_id))
