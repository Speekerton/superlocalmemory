# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later
"""Execute a check, sweep observable survivors, and retain measured output."""

import os
import signal
import subprocess
import time
from typing import NamedTuple

import psutil

from superlocalmemory.loops.private_workspace import execution_environment
from superlocalmemory.loops.process_sweep import sweep, user_processes


class ExecutionResult(NamedTuple):
    exit_code: int
    stdout: bytes
    stderr: bytes
    reason: str | None = None


def execute(command, cwd, timeout):
    try:
        before = user_processes()
    except ValueError as error:
        return ExecutionResult(-1, b'', b'', str(error))
    began = time.time()
    try:
        process = subprocess.Popen(
            command, cwd=cwd, stdin=subprocess.DEVNULL, shell=False,
            env=execution_environment(cwd), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            start_new_session=True,
        )
    except OSError:
        return ExecutionResult(-1, b'', b'', 'Independent check did not complete')
    reason = None
    try:
        # Use the OS creation timestamp, including its native clock resolution.
        # Prep-time processes are outside the check; forked children share this clock.
        began = psutil.Process(process.pid).create_time()
    except psutil.Error:
        reason = 'Cannot validate the checker process start time'
    try:
        stdout, stderr = process.communicate(timeout=timeout)
        exit_code = process.returncode if reason is None else -1
    except subprocess.TimeoutExpired as error:
        stdout, stderr = error.output or b'', error.stderr or b''
        exit_code, reason = -1, 'Independent check timed out'
    finally:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
    try:
        escaped = sweep(before, began)
    except ValueError as error:
        escaped = str(error)
    if escaped:
        exit_code, reason = -1, escaped
    # Drain after the sweep has terminated escaped pipe holders as well.
    try:
        stdout, stderr = process.communicate(timeout=0.2)
    except subprocess.TimeoutExpired as error:
        stdout, stderr = error.output or b'', error.stderr or b''
    finally:
        process.stdout.close()
        process.stderr.close()
    return ExecutionResult(exit_code, stdout, stderr, reason)
