# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later
"""Hash complete checker output; publish only bounded, redacted excerpts."""

import base64
import hashlib
import re

_EXCERPT_LIMIT = 2048


def _bytes(value):
    return value if isinstance(value, bytes) else value.encode('utf-8', errors='replace')


def _excerpt(raw, secret_material):
    for key in secret_material:
        for value in (key, key.hex().encode(), base64.b64encode(key),
                      base64.urlsafe_b64encode(key), repr(key).encode()):
            raw = raw.replace(value, b'[REDACTED]')
    text = raw.decode('utf-8', errors='replace')
    # Include hashes, encoded keys and other unbroken key-length material.
    text = re.sub(r'\S{32,}', '[REDACTED]', text)
    return text[:_EXCERPT_LIMIT]


def output_evidence(stdout, stderr, secret_material=()):
    out, err = _bytes(stdout), _bytes(stderr)
    full = len(out).to_bytes(8, 'big') + out + len(err).to_bytes(8, 'big') + err
    return dict(
        stdout_sha256=hashlib.sha256(out).hexdigest(),
        stderr_sha256=hashlib.sha256(err).hexdigest(),
        output_sha256=hashlib.sha256(full).hexdigest(),
        stdout_excerpt=_excerpt(out, secret_material),
        stderr_excerpt=_excerpt(err, secret_material),
    )
