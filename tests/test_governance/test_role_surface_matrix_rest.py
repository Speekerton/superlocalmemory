# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
"""Role x surface matrix, REST and dashboard reads (4.1.25 WP-9).

Who: anonymous (no credential), the machine owner without a session (install
token), a viewer, a member and an admin of workspace ``default`` (A), an admin
of workspace ``sales`` only (B), and an account that is a viewer of A but an
admin of B. The other half (HTTP MCP, stdio MCP) is in
``test_role_surface_matrix_mcp.py``.

The walks below go over every GET route the daemon registers, so a new route
that forgets to check the workspace it reads fails here. Each finding the
matrix closes is named next to its test:

* OPS-25: a route that honours ``?profile=`` / ``?profile_id=`` was checked
  against the active workspace only.
* OPS-09: the workspace list named every workspace and counted its memories.
* OPS-24: a signed-out (or expired, revoked) viewer session became the owner.
* G-M6: Optimize settings answered a logged-out caller.
* G-M5: a viewer could not list correction cases and was told it tried to write.
"""

# ruff: noqa: F811  (imported pytest fixtures are re-declared as test parameters)

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from superlocalmemory.server.read_gates import USER_READ_OPEN, USER_READ_SELF_GATED_PREFIXES
from tests.test_server.test_company_mode_get_routes import STREAMING_ROUTES, _concrete, _get_paths
from tests.test_server.test_rbac_company_mode_credential import (
    LOOPBACK,
    app_and_engine,  # noqa: F401  (pytest fixture)
)

#: Reads every role that belongs to a workspace may make there (positive control).
CORE_READS = ("/api/memories", "/api/v3/timeline", "/api/tiers/stats", "/api/profiles")


def _users(rbac):
    made = {}
    for name in ("viewer_a", "member_a", "admin_a", "admin_b", "dual"):
        made[name] = rbac.create_user(name, "password-1234", display_name=name)["user_id"]
    rbac.set_membership("default", made["viewer_a"], "viewer")
    rbac.set_membership("default", made["member_a"], "member")
    rbac.set_membership("default", made["admin_a"], "admin")
    rbac.set_membership("sales", made["admin_b"], "admin")
    rbac.set_membership("default", made["dual"], "viewer")
    rbac.set_membership("sales", made["dual"], "admin")
    return made


@pytest.fixture
def matrix(app_and_engine):
    """Two workspaces with content, five accounts, sessions for each."""
    from superlocalmemory.core.security_primitives import ensure_install_token
    from superlocalmemory.server.routes.optimize import router as optimize_router

    app = app_and_engine
    if not any(p.startswith("/api/optimize") for p in _get_paths(app)):
        app.include_router(optimize_router)
    db = app.state.engine._db
    db.execute("INSERT OR IGNORE INTO profiles (profile_id, name) VALUES ('sales','sales')")
    rbac = app.state.rbac
    ids = _users(rbac)
    token = ensure_install_token()
    who = {name: {"X-SLM-User-Session": rbac.create_session(uid), "X-Install-Token": token}
           for name, uid in ids.items()}
    who["owner"] = {"X-Install-Token": token}
    who["anonymous"] = {}
    client = TestClient(app, base_url="http://127.0.0.1:8765", client=LOOPBACK,
                        raise_server_exceptions=False)
    return app, client, who, ids


def _company(app):
    app.state.rbac.set_require_login(True)


def _user_open(path: str) -> bool:
    return path in USER_READ_OPEN or path.startswith(USER_READ_SELF_GATED_PREFIXES)


# -- OPS-25: naming another workspace -----------------------------------------------


@pytest.mark.parametrize("login_required", [True, False], ids=["company", "login-optional"])
@pytest.mark.parametrize("who_name", ["viewer_a", "member_a", "admin_a"])
def test_no_get_route_serves_a_workspace_the_user_cannot_read(matrix, login_required, who_name):
    app, client, who, _ = matrix
    if login_required:
        _company(app)
    answered = []
    for path in _get_paths(app):
        if _user_open(path) or path in STREAMING_ROUTES:
            continue
        for key in ("profile", "profile_id"):
            r = client.get(_concrete(path), params={key: "sales"}, headers=who[who_name])
            if r.status_code not in (401, 403, 404, 405, 422):
                answered.append((path, key, r.status_code))
    assert not answered, f"{who_name} read another workspace: {answered}"


def test_a_default_viewer_cannot_read_sales_through_timeline_insights_or_tiers(matrix):
    """The audit's exact reproduction (OPS-25)."""
    app, client, who, _ = matrix
    _company(app)
    for path, params in (
        ("/api/v3/timeline", {"profile": "sales"}),
        ("/api/v3/insights/changed_this_week", {"profile": "sales"}),
        ("/api/v3/insights/opinions", {"profile": "sales"}),
        ("/api/tiers/stats", {"profile_id": "sales"}),
    ):
        r = client.get(path, params=params, headers=who["viewer_a"])
        assert r.status_code == 403, (path, r.status_code, r.text[:200])


def test_the_owner_of_sales_still_reads_sales(matrix):
    app, client, who, _ = matrix
    _company(app)
    r = client.get("/api/tiers/stats", params={"profile_id": "sales"}, headers=who["admin_b"])
    assert r.status_code == 200, r.text[:300]


@pytest.mark.parametrize("who_name", ["viewer_a", "member_a", "admin_a"])
def test_members_of_a_workspace_still_read_it(matrix, who_name):
    app, client, who, _ = matrix
    _company(app)
    for path in CORE_READS:
        r = client.get(path, headers=who[who_name])
        assert r.status_code == 200, (who_name, path, r.status_code, r.text[:200])


def test_an_admin_of_sales_only_cannot_read_default(matrix):
    app, client, who, _ = matrix
    _company(app)
    for path in ("/api/memories", "/api/v3/timeline", "/api/tiers/stats"):
        assert client.get(path, headers=who["admin_b"]).status_code == 403, path


# -- OPS-09: the workspace list ------------------------------------------------------


def test_the_workspace_list_names_only_the_callers_workspaces(matrix):
    app, client, who, _ = matrix
    _company(app)
    def names(caller):
        listed = client.get("/api/profiles", headers=who[caller]).json()["profiles"]
        return {p["name"] for p in listed}

    seen = {name: names(name) for name in ("viewer_a", "admin_b", "dual")}
    assert seen == {"viewer_a": {"default"}, "admin_b": {"sales"}, "dual": {"default", "sales"}}
    body = client.get("/api/profiles", headers=who["admin_b"]).json()
    assert body["active_profile"] == ""  # the active workspace is not theirs to name


def test_the_owner_still_sees_every_workspace_in_personal_mode(matrix):
    app, client, who, _ = matrix
    listed = client.get("/api/profiles", headers=who["owner"]).json()["profiles"]
    names = {p["name"] for p in listed}
    assert {"default", "sales"} <= names


# -- OPS-24: an ended session is never the owner -------------------------------------


def test_a_signed_out_viewer_session_is_refused_not_promoted(matrix):
    """Login optional, accounts enrolled: the audit's reproduction, end to end."""
    app, client, who, _ = matrix
    viewer = who["viewer_a"]
    body = {"content": "a note the viewer must not write"}
    assert client.post("/remember", json=body, headers=viewer).status_code == 403
    assert client.post("/api/rbac/logout", headers=viewer).status_code == 200

    after = client.post("/remember", json=body, headers=viewer)
    assert after.status_code == 401, after.text[:200]
    assert client.get("/api/memories", headers=viewer).status_code == 401
    assert client.post("/api/tiers/evaluate", headers=viewer).status_code == 401
    whoami = client.get("/api/rbac/whoami", headers=viewer).json()
    assert whoami["session_invalid"] is True


def test_an_expired_or_forged_session_is_refused_in_personal_mode_too(matrix):
    app, client, who, _ = matrix
    forged = {**who["owner"], "X-SLM-User-Session": "not-a-session"}
    assert client.get("/api/memories", headers=forged).status_code == 401
    assert client.post("/remember", json={"content": "x"}, headers=forged).status_code == 401


def test_without_a_session_the_owner_is_unchanged_when_login_is_optional(matrix):
    app, client, who, _ = matrix
    assert client.get("/api/memories", headers=who["owner"]).status_code == 200
    assert client.get("/api/memories").status_code == 200


# -- G-M6 / G-M5 ---------------------------------------------------------------------


def test_optimize_settings_need_a_session_in_company_mode(matrix):
    app, client, who, _ = matrix
    _company(app)
    for path in ("/api/optimize/config", "/api/optimize/stats", "/api/optimize/savings"):
        assert client.get(path, headers=who["owner"]).status_code == 401, path
        assert client.get(path).status_code == 401, path
        assert client.get(path, headers=who["admin_a"]).status_code == 200, path


def test_a_viewer_lists_corrections_but_cannot_act_on_them(matrix):
    app, client, who, _ = matrix
    _company(app)
    listed = client.get("/api/corrections", headers=who["viewer_a"])
    assert listed.status_code == 200, listed.text[:200]
    assert client.get("/api/overtaken-corrections", headers=who["viewer_a"]).status_code == 200
    foreign = client.get("/api/corrections", params={"profile_id": "sales"},
                         headers=who["viewer_a"])
    assert foreign.status_code == 403
    acted = client.post("/api/overtaken-corrections/c1/restore", json={},
                        headers=who["viewer_a"])
    assert acted.status_code == 403
    assert "write" in acted.json().get("error", acted.json().get("detail", ""))
