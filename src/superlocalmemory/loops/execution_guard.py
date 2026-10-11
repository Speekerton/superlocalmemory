# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later
"""Hold file identities and non-restorable change markers across execution.

Content hashes alone miss ABA writes. POSIX ctime changes even when bytes and
mtime are restored; open handles prevent inode reuse. Namespace metadata also
covers alias/directory swaps that leave the original file untouched. Checks
must keep input directories stable: create outputs in a pre-existing directory
that is not an ancestor of a declared input. Non-POSIX hosts fail closed until
an equivalent change marker is implemented (Windows ctime is creation time).
This boundary assumes the operator's local filesystem maintains POSIX change
timestamps; privileged filesystem/clock tampering is outside service authority.
"""

import hashlib
import json
import os
import stat
from contextlib import ExitStack, contextmanager
from pathlib import Path

_ERROR = "Checked artifacts changed during verification"


def admission(job):
    """Versioned proof emitted only after all registered validations succeed."""
    return {
        "job_id": job["job_id"], "revision_digest": job["revision_digest"],
        "validation": "posix-identity-ctime-v1",
    }


def _stamp(info):
    return (
        info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size,
        info.st_mtime_ns, info.st_ctime_ns,
    )


def _digest(stream):
    stream.seek(0)
    digest = hashlib.sha256()
    while chunk := stream.read(1024 * 1024):
        digest.update(chunk)
    return digest.hexdigest()


def _namespace(job, records):
    root = Path(job["cwd"])
    paths = {root, *root.parents}
    for record in records:
        for name in (record["path"], record["resolved_path"]):
            path = Path(name)
            while path.is_relative_to(root):
                paths.add(path)
                if path == root:
                    break
                path = path.parent
    return {path: _stamp(path.lstat()) for path in paths}


def _verify(files, namespace):
    for stream, identity, digest in files:
        if (
            _stamp(os.fstat(stream.fileno())) != identity
            or _digest(stream) != digest
            or _stamp(os.fstat(stream.fileno())) != identity
        ):
            raise ValueError(_ERROR)
    for path, identity in namespace.items():
        if _stamp(path.lstat()) != identity:
            raise ValueError(f"{_ERROR}: input namespace {path}")


@contextmanager
def execution_guard(job):
    """Capture before reading any inputs; validate last, before publication."""
    if os.name != "posix":
        raise ValueError("Registered checks require POSIX change timestamps")
    records = json.loads(job["artifacts_json"])
    try:
        with ExitStack() as stack:
            namespace = _namespace(job, records)
            files = []
            for record in records:
                fd = os.open(record["resolved_path"], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
                stream = stack.enter_context(os.fdopen(fd, "rb", buffering=0))
                info = os.fstat(stream.fileno())
                if not stat.S_ISREG(info.st_mode):
                    raise ValueError(_ERROR)
                files.append((stream, _stamp(info), record["sha256"]))
            _verify(files, namespace)
            yield lambda: _verify(files, namespace)
    except OSError as error:
        raise ValueError(_ERROR) from error
