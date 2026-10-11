"""PR-245 recheck #1: concurrent legacy adoption must never stop another root."""

import plistlib
from types import SimpleNamespace

import pytest

from superlocalmemory.cli import service_installer as service
from tests.test_cli.test_legacy_service_migration import (
    sandbox,  # noqa: F401 -- shared sandbox fixture, all OS operations mocked
    write_definition,
)


def destructive(argv, platform, name):
    actions = {"macos": {"unload"}, "linux": {"stop", "disable"},
               "windows": {"/End", "/Delete"}}[platform]
    return name in " ".join(argv) and bool(actions.intersection(argv))


@pytest.mark.parametrize("platform", ["macos", "linux", "windows"])
@pytest.mark.parametrize("operation", ["install", "uninstall"])
def test_manager_query_swap_never_mutates_foreign_service(
    sandbox, monkeypatch, platform, operation,
):
    name, path = write_definition(sandbox, platform)
    foreign = sandbox.root / "foreign"
    foreign.mkdir()
    original = path.read_text()
    replacement = original.replace(str(sandbox.root), str(foreign))
    run = service.subprocess.run
    queried, swapped, foreign_mutations = 0, False, []

    def swap(argv, **kwargs):
        nonlocal queried, swapped
        result = run(argv, **kwargs)
        query = {"macos": "list", "linux": "show", "windows": "/Query"}[platform]
        if query in argv and name in argv:
            queried += 1
            if platform == "macos" or queried == 2:
                # Return the old ownership snapshot while the effective job and
                # definition have both been replaced by the other installer.
                path.write_text(replacement)
                swapped = True
        if swapped and destructive(argv, platform, name):
            foreign_mutations.append(argv)
        return result

    monkeypatch.setattr(service.subprocess, "run", swap)
    assert getattr(service, f"{operation}_{platform}")() is False
    assert swapped
    assert foreign_mutations == []
    assert path.read_text() == replacement
    if platform == "macos":
        assert plistlib.loads(path.read_bytes())["EnvironmentVariables"]["SLM_DATA_DIR"] == str(foreign)


def test_exact_reviewer_launchctl_list_interleaving(sandbox, monkeypatch):
    _, path = write_definition(sandbox, "macos")
    foreign = sandbox.root / "B"
    foreign.mkdir()
    payload = plistlib.loads(path.read_bytes())
    payload["EnvironmentVariables"]["SLM_DATA_DIR"] = str(foreign)
    replacement = plistlib.dumps(payload)
    loaded_root, unloaded_roots = str(sandbox.root), []

    def manager(argv, **kwargs):
        nonlocal loaded_root
        if "list" in argv:
            path.write_bytes(replacement)
            loaded_root = str(foreign)
        if "unload" in argv:
            unloaded_roots.append(loaded_root)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(service.subprocess, "run", manager)
    assert service.uninstall_macos() is False
    assert unloaded_roots == []
    assert path.read_bytes() == replacement
