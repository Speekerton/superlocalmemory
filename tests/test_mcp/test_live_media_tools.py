"""An existing MCP process discovers feature changes without re-importing."""

import pytest

from superlocalmemory.mcp.http_transport import SLMFastMCP


@pytest.mark.asyncio
async def test_media_tools_refresh_while_the_same_server_is_running(monkeypatch):
    from superlocalmemory.runtimes import features

    enabled = False
    monkeypatch.setattr(features, "media_enabled", lambda: enabled)
    server = SLMFastMCP("test")
    server.configure_tool_surface(frozenset({"recall", "get_media"}))

    @server.tool()
    def recall():
        return {}

    @server.tool()
    def get_media():
        return {}

    assert [t.name for t in await server.list_tools()] == ["recall"]
    enabled = True
    assert {t.name for t in await server.list_tools()} == {"recall", "get_media"}
    enabled = False
    assert [t.name for t in await server.list_tools()] == ["recall"]
    with pytest.raises(ValueError, match="not enabled"):
        await server.call_tool("get_media", {})


@pytest.mark.asyncio
async def test_explicit_small_allowlist_does_not_gain_media_tools(monkeypatch):
    from superlocalmemory.runtimes import features

    monkeypatch.setattr(features, "media_enabled", lambda: True)
    server = SLMFastMCP("test")
    server.configure_tool_surface(frozenset({"recall"}))

    @server.tool()
    def get_media():
        return {}

    assert await server.list_tools() == []
