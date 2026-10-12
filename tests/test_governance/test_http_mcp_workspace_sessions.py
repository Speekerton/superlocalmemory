# ruff: noqa: F811
"""HTTP MCP sessions share storage, never an active workspace."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.test_governance.test_role_surface_matrix_mcp import store  # noqa: F401


def test_concurrent_http_sessions_pin_tools_and_resources(store, monkeypatch):
    from superlocalmemory.core.caller_session import CallerSessionASGI
    from superlocalmemory.mcp import server as srv
    from superlocalmemory.server.caller_workspace import CallerWorkspaceMiddleware
    from superlocalmemory.storage.models import AtomicFact, MemoryRecord

    rbac, ids = store
    rbac.set_require_login(True)
    engine = srv.get_engine()
    for profile in ("default", "sales"):
        memory = MemoryRecord(profile_id=profile, content=f"{profile}-sentinel")
        engine._db.store_memory(memory)
        engine._db.store_fact(
            AtomicFact(
                memory_id=memory.memory_id, profile_id=profile, content=f"{profile}-sentinel"
            )
        )
    monkeypatch.setattr("superlocalmemory.cli.daemon.is_daemon_running", lambda: False)
    mcp_app = srv.server.streamable_http_app(
        streamable_http_path="/", stateless_http=True, json_response=True
    )

    @asynccontextmanager
    async def lifespan(_):
        async with mcp_app.router.lifespan_context(mcp_app):
            yield

    app = FastAPI(lifespan=lifespan)
    app.state.rbac = rbac
    app.state.engine = engine
    app.add_middleware(CallerWorkspaceMiddleware, app_state=app.state)
    app.mount("/mcp", CallerSessionASGI(mcp_app))
    sessions = {name: rbac.create_session(ids[name]) for name in ("admin_b", "viewer_a")}
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
        "MCP-Protocol-Version": "2025-06-18",
    }
    with TestClient(app, base_url="http://127.0.0.1:9911") as client:

        def rpc(user, method, params):
            return client.post(
                "/mcp/",
                headers={**headers, "X-SLM-User-Session": sessions[user]},
                json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
            ).json()

        for user, target in (("admin_b", "sales"), ("viewer_a", "default")):
            switched = rpc(
                user, "tools/call", {"name": "switch_profile", "arguments": {"profile_id": target}}
            )
            assert switched["result"]["isError"] is False, switched
        denied = rpc(
            "viewer_a",
            "tools/call",
            {"name": "switch_profile", "arguments": {"profile_id": "sales"}},
        )
        assert denied["result"]["isError"] is True
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = {
                user: pool.submit(rpc, user, "resources/read", {"uri": "slm://recent"})
                for user in sessions
            }
            results = {user: future.result() for user, future in futures.items()}
        for user, own, foreign in (
            ("admin_b", "sales", "default"),
            ("viewer_a", "default", "sales"),
        ):
            text = results[user]["result"]["contents"][0]["text"]
            assert f"{own}-sentinel" in text
            assert f"{foreign}-sentinel" not in text
            recent = rpc(user, "tools/call", {"name": "list_recent", "arguments": {}})
            assert recent["result"]["isError"] is False, recent
            assert f"{own}-sentinel" in str(recent)
            assert f"{foreign}-sentinel" not in str(recent)
    assert engine.profile_id == "default"
    assert engine._config.active_profile == "default"


def test_personal_http_connections_switch_without_moving_each_other(store, monkeypatch):
    from superlocalmemory.core.caller_session import CallerSessionASGI
    from superlocalmemory.mcp import server as srv
    from superlocalmemory.mcp.http_transport import SLMFastMCP
    from superlocalmemory.mcp.tools_core import register_core_tools
    from superlocalmemory.server.caller_workspace import CallerWorkspaceMiddleware

    rbac, _ = store
    rbac.set_require_login(False)
    engine = srv.get_engine()
    monkeypatch.setattr("superlocalmemory.cli.daemon.is_daemon_running", lambda: False)
    probe = SLMFastMCP("personal connection scope")
    register_core_tools(probe, srv.get_engine)

    @probe.tool()
    async def active_workspace() -> dict:
        return {"profile_id": srv.get_engine().profile_id}

    mcp_app = probe.streamable_http_app(
        streamable_http_path="/", stateless_http=True, json_response=True
    )

    @asynccontextmanager
    async def lifespan(_):
        async with mcp_app.router.lifespan_context(mcp_app):
            yield

    app = FastAPI(lifespan=lifespan)
    app.state.rbac = rbac
    app.state.engine = engine
    app.add_middleware(CallerWorkspaceMiddleware, app_state=app.state)
    app.mount("/mcp", CallerSessionASGI(mcp_app))
    jars = {"first": "", "second": ""}
    with TestClient(app, base_url="http://127.0.0.1:9911", client=("127.0.0.1", 5000)) as client:

        def rpc(connection, name, arguments=None, *, refused=False):
            client.cookies.clear()
            response = client.post(
                "/mcp/",
                headers={
                    "Accept": "application/json, text/event-stream",
                    "Content-Type": "application/json",
                    "MCP-Protocol-Version": "2025-06-18",
                    "Cookie": jars[connection],
                },
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {"name": name, "arguments": arguments or {}},
                },
            )
            cookie = response.headers.get("set-cookie", "").split(";")[0]
            jars[connection] = cookie or jars[connection]
            result = response.json()["result"]
            assert result["isError"] is refused, result
            import json

            return json.loads(result["content"][0]["text"])

        assert rpc("first", "active_workspace")["profile_id"] == "default"
        assert rpc("second", "active_workspace")["profile_id"] == "default"
        assert rpc("first", "switch_profile", {"profile_id": "sales"})["success"] is True
        assert rpc("first", "active_workspace")["profile_id"] == "sales"
        assert rpc("second", "active_workspace")["profile_id"] == "default"
        rbac.set_require_login(True)
        assert rpc("first", "active_workspace", refused=True)["code"] == "NOT_AUTHORIZED"
    assert engine.profile_id == "default"


def test_remote_peer_cannot_select_a_personal_owner_binding(store):
    from types import SimpleNamespace

    from superlocalmemory.server.caller_workspace import (
        resolve_caller_workspace,
        session_workspaces,
    )

    rbac, _ = store
    state = SimpleNamespace(rbac=rbac, engine=SimpleNamespace(profile_id="default"))
    binding = "sandbox-workspace-binding"
    session_workspaces(state).bind("owner:" + binding, "sales")
    for client, forwarding in (
        ("203.0.113.10", []),
        ("127.0.0.1", [(b"x-forwarded-for", b"203.0.113.10")]),
    ):
        scope = {
            "type": "http",
            "path": "/mcp/",
            "client": (client, 5000),
            "headers": [(b"cookie", ("slm_mcp_workspace=" + binding).encode()), *forwarding],
        }
        pin = resolve_caller_workspace(scope, state)
        assert pin.profile_id == "default" and pin.bound is False


def test_context_pool_recall_forwards_the_pinned_workspace(monkeypatch):
    from superlocalmemory.mcp import _pool_adapter
    from superlocalmemory.server.caller_workspace import CallerWorkspace
    from superlocalmemory.server.profile_runtime import pin_request_workspace

    captured = {}

    class Pool:
        def recall(self, **kwargs):
            captured.update(kwargs)
            return {"ok": True, "results": []}

    monkeypatch.setattr(_pool_adapter, "_pool", lambda: Pool())
    with pin_request_workspace(CallerWorkspace("sales", bound=True)):
        _pool_adapter.pool_recall("session context")
    assert captured["profile_id"] == "sales"
