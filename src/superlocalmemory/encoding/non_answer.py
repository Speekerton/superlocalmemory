# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later
"""Conservative receipt/stub detection, independent of fact length.

A fact is a stub only when the WHOLE text is machine bookkeeping: a label
followed by a machine-shaped id (8+ hex characters, a canonical UUID or a
ULID), or session boilerplate with its timestamp. Anything a person could
mean ("use port 8765", "memory id: grandma-recipe") stays answer material.
A user's decision ("this is an answer") is stored and always wins.
"""

from __future__ import annotations

import re

_EMPTY = re.compile(r'^[\s\[\]{}(),;:]*$')
_DATE = r'\d{4}-\d{2}-\d{2}(?:[T ]\d{1,2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?'
_SESSION = re.compile(r'^(?:\[\]\s*)?session\s+(?:ended|closed)(?:\s+at)?\s+'
                      + _DATE + r'[.!]?$', re.I)
_MACHINE_ID = (r'(?:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
               r'|[0-9a-f]{8,}'
               r'|[0-7][0-9a-hjkmnp-tv-z]{25})')
_RECEIPT = re.compile(r'^(?:receipt|operation|session|fact|memory|run)(?:[ _-]?id)?'
                      r'\s*[:=]\s*' + _MACHINE_ID + r'[.!]?$', re.I)
_USER_COLUMN = 'non_answer_user'


def is_empty_structure(text: str) -> bool:
    """Only brackets, braces and separators: nothing to remember at all."""
    return bool(_EMPTY.fullmatch(text or ''))


def is_stub(text: str) -> bool:
    value = (text or '').strip()
    return bool(value and (_EMPTY.fullmatch(value) or _SESSION.fullmatch(value)
                           or _RECEIPT.fullmatch(value)))


def _columns(db) -> frozenset:
    cached = getattr(db, '_non_answer_columns', None)
    if cached:
        return cached
    found = frozenset(r['name'] for r in db.execute('PRAGMA table_info(atomic_facts)')
                      if r['name'] in ('non_answer', _USER_COLUMN))
    if found == {'non_answer', _USER_COLUMN}:
        try:  # cached once complete; re-probed while a later migration is pending
            db._non_answer_columns = found
        except AttributeError:
            pass
    return found


def has_marker(db) -> bool:
    return 'non_answer' in _columns(db)


def user_decided(db, fact_id, profile_id) -> bool:
    """True when the user already said whether this fact is an answer."""
    if _USER_COLUMN not in _columns(db):
        return False
    rows = db.execute(f'SELECT {_USER_COLUMN} FROM atomic_facts WHERE fact_id=? '
                      'AND profile_id=?', (fact_id, profile_id))
    return bool(rows) and rows[0][_USER_COLUMN] is not None


def mark(db, fact_id, profile_id, content):
    """Flag a stub automatically, never over the user's own decision."""
    columns = _columns(db)
    if 'non_answer' not in columns:
        return
    guard = f' AND {_USER_COLUMN} IS NULL' if _USER_COLUMN in columns else ''
    db.execute(f'UPDATE atomic_facts SET non_answer=? WHERE fact_id=? AND profile_id=?{guard}',
               (int(is_stub(content)), fact_id, profile_id))


def user_unmark(db, fact_id, profile_id):
    """The user says this fact is an answer: clear the flag and remember why."""
    columns = _columns(db)
    if 'non_answer' not in columns:
        return
    extra = f', {_USER_COLUMN}=0' if _USER_COLUMN in columns else ''
    db.execute(f'UPDATE atomic_facts SET non_answer=0{extra} WHERE fact_id=? AND profile_id=?',
               (fact_id, profile_id))
