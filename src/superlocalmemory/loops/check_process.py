# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later
"""A bounded process group cannot leave checker descendants in private copies."""

import os
import signal
import subprocess
import time

from superlocalmemory.loops.private_workspace import execution_environment
from superlocalmemory.loops.process_sweep import sweep, user_processes


def execute(command, cwd, timeout):
    try:
        before = user_processes()
    except ValueError as error:
        return -1, '', str(error)
    began = time.time()
    try:
        process = subprocess.Popen(
            command, cwd=cwd, stdin=subprocess.DEVNULL, shell=False,
            env=execution_environment(cwd), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, errors='replace', start_new_session=True,
        )
    except OSError:
        return -1, '', 'Independent check did not complete'
    try:
        stdout, stderr = process.communicate(timeout=timeout)
        result = process.returncode, stdout, stderr
    except subprocess.TimeoutExpired:
        result = -1, '', 'Independent check timed out'
    finally:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
        process.stdout.close()
        process.stderr.close()
    try:
        reason = sweep(before, began)
    except ValueError as error:
        reason = str(error)
    if reason:
        return -1, '', reason
    return result
