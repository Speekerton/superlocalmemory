# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later
"""Fail closed on observable checker escape, including reparented processes."""

import os
import time

import psutil


def user_processes():
    """Read identities without launching a process that our sweep would kill."""
    found = {}
    for process in psutil.process_iter():
        try:
            if process.uids().real != os.getuid():
                continue
            if process.status() in (psutil.STATUS_ZOMBIE, psutil.STATUS_DEAD):
                continue
            identity = (process.pid, process.create_time())
            found[identity] = (process, process.name())
        except psutil.NoSuchProcess:
            continue
        except psutil.Error as error:
            raise ValueError('Cannot validate the user process table') from error
    return found


def sweep(before, began):
    """Record every observed survivor; termination cannot turn it into a PASS."""
    reason = None
    deadline = time.monotonic() + 1
    while True:
        current = user_processes()
        remaining = [value for identity, value in current.items()
                     if identity not in before and identity[1] >= began
                     and identity[0] != os.getpid()]
        if not remaining:
            return reason
        process, name = remaining[0]
        reason = reason or (
            f'a process started by the check is still running: {name} ({process.pid})')
        for process, _ in remaining:
            try:
                # psutil checks creation time before signalling to avoid PID reuse.
                process.kill()
            except psutil.NoSuchProcess:
                pass
            except psutil.Error:
                # The observed process already forbids PASS, even if it resists kill.
                pass
        if time.monotonic() >= deadline:
            return reason
        time.sleep(0.01)
