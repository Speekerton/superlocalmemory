# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later
"""Private storage and portable refusal for unavailable no-follow primitives."""

import os
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path


def platform_reason():
    if (os.open not in os.supports_dir_fd or not hasattr(os, 'O_NOFOLLOW')
            or not hasattr(os, 'O_DIRECTORY')):
        return ('Hermetic registered checks are unsupported on this platform: '
                'secure no-follow directory handles are required (including on Windows)')
    return None


def private_dir(path):
    path = Path(path)
    if not path.exists():
        if not path.parent.exists():
            private_dir(path.parent)
        path.mkdir(mode=0o700, exist_ok=True)
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode):
        raise ValueError('Private check storage cannot contain symlinks')
    os.chmod(path, 0o700)
    return path


def private_file(path):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    return os.fdopen(fd, 'wb')


@contextmanager
def temporary(parent=None):
    if parent is not None:
        private_dir(parent)
    with tempfile.TemporaryDirectory(prefix='slm-check-', dir=parent) as name:
        path = private_dir(name)
        yield path


def execution_environment(cwd):
    root = private_dir(Path(cwd) / '.slm-runtime')
    paths = {name: str(private_dir(root / directory)) for name, directory in (
        ('HOME', 'home'), ('TMPDIR', 'tmp'), ('XDG_CACHE_HOME', 'cache'),
        ('XDG_CONFIG_HOME', 'config'), ('XDG_DATA_HOME', 'data'),
    )}
    paths.update(PATH=os.defpath, TMP=paths['TMPDIR'], TEMP=paths['TMPDIR'],
                 USERPROFILE=paths['HOME'], PYTHONNOUSERSITE='1',
                 PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
    return paths
