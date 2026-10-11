# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later
"""Bind pytest configuration to a pinned file or a generated empty config."""

import json
from pathlib import Path

from superlocalmemory.loops.artifact_revision import copy_inputs
from superlocalmemory.loops.private_workspace import private_dir, private_file, temporary

_CONFIGS = ('pytest.ini', '.pytest.ini', 'pytest.toml', '.pytest.toml',
            'pyproject.toml', 'tox.ini', 'setup.cfg')


def _pytest(command):
    if Path(command[0]).name in ('pytest', 'py.test'):
        return True
    return any(command[i:i + 2] == ['-m', 'pytest'] for i in range(1, len(command) - 1))


def _options(command):
    clean, config = [], None
    args = iter(command)
    for arg in args:
        if arg == '--':
            clean.extend([arg, *args])
            break
        if arg in ('-c', '--config-file', '--rootdir'):
            value = next(args, None)
            if value is None:
                raise ValueError('Pytest configuration option needs a value')
            if arg != '--rootdir':
                config = value
        elif arg.startswith(('--config-file=', '--rootdir=')):
            if arg.startswith('--config-file='):
                config = arg.split('=', 1)[1]
        elif arg.startswith('-c') and len(arg) > 2:
            config = arg[2:]
        else:
            clean.append(arg)
    return clean, config


def prepare_pytest(command, run_dir, job):
    if not _pytest(command):
        return command
    clean, config = _options(command)
    pinned = {row['path'] for row in json.loads(job['definition_json'])}
    if config is not None:
        path = Path(config)
        if path.is_absolute():
            try:
                config = path.relative_to(run_dir).as_posix()
            except ValueError as error:
                raise ValueError('Pytest config must be in the pinned definition') from error
        else:
            config = path.as_posix()
        if config not in pinned:
            raise ValueError('Pytest config must be in the pinned definition')
    else:
        config = next((name for name in _CONFIGS if name in pinned), None)
    if config is None:
        config = '.slm-pytest/pytest.ini'
        private_dir(Path(run_dir) / '.slm-pytest')
        with private_file(Path(run_dir) / config) as stream:
            stream.write(b'[pytest]\n')
        with temporary() as copy:
            manifest, _ = copy_inputs(run_dir, [config], copy)
        job['_generated_config_manifest'] = manifest
    position = clean.index('--') if '--' in clean else len(clean)
    options = ['-c', str(Path(run_dir) / config), '--rootdir', str(run_dir)]
    return clean[:position] + options + clean[position:]


def validate_pytest_configuration(job, run_dir):
    expected = job.get('_generated_config_manifest')
    if expected is not None:
        names = [row['path'] for row in json.loads(expected)]
        with temporary() as copy:
            actual, _ = copy_inputs(run_dir, names, copy)
        if actual != expected:
            raise ValueError('Check modified its generated pytest configuration')
