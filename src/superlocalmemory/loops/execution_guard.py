# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later
"""Authenticate registered measurements; live-tree metadata is not evidence."""

import hashlib
import hmac
import json
import os
import secrets
import stat
from pathlib import Path


def admission(job):
    """Public identity descriptor alone cannot mint an admitted receipt."""
    return {'job_id': job['job_id'], 'revision_digest': job['revision_digest'],
            'definition_digest': job['definition_digest'], 'validation': 'hermetic-copy-v1'}


def _key(store, *, create=False):
    path = Path(store) / 'admission.key'
    if create:
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(secrets.token_bytes(32))
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
            raise ValueError('Admission key must be an owner-only regular file')
        key = stream.read(33)
    if len(key) != 32:
        raise ValueError('Invalid admission key')
    return key


def _payload(receipt):
    value = dict(receipt)
    measurement = json.loads(value['evidence'])
    measurement['admission'].pop('signature', None)
    value['evidence'] = json.dumps(measurement, sort_keys=True)
    value.pop('evidence_digest', None)
    return json.dumps(value, sort_keys=True).encode()


def _sign_receipt(job, receipt):
    measurement = json.loads(receipt['evidence'])
    measurement['admission'] = admission(job)
    receipt['evidence'] = json.dumps(measurement, sort_keys=True)
    measurement['admission']['signature'] = hmac.new(
        _key(job['store_path']), _payload(receipt), hashlib.sha256).hexdigest()
    receipt['evidence'] = json.dumps(measurement, sort_keys=True)
    receipt['evidence_digest'] = hashlib.sha256(receipt['evidence'].encode()).hexdigest()


def verify_admission(job, receipt):
    try:
        proof = json.loads(receipt['evidence'])['admission']
        signature = proof.pop('signature')
        expected = admission(job)
        expected['revision_digest'] = proof.get('revision_digest')
        return (proof == expected and isinstance(signature, str)
                and hmac.compare_digest(signature, hmac.new(
                    _key(job['store_path']), _payload(receipt), hashlib.sha256).hexdigest()))
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return False
