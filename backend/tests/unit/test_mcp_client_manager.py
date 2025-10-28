# ABOUTME: Unit tests for MCPClientManager singleton and lifecycle management
# ABOUTME: Tests initialization, tool discovery, and graceful degradation

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.infrastructure.mcp.mcp_client_manager import MCPClientManager


@pytest.fixture
def reset_mcp_manager():
    """Reset MCPClientManager singleton state before each test."""
    MCPClientManager._instance = None
    MCPClientManager._clients = {}
    MCPClientManager._tools = []
    MCPClientManager._client_contexts = []
    yield
    # Cleanup after test
    MCPClientManager._instance = None
    MCPClientManager._clients = {}
    MCPClientManager._tools = []
    MCPClientManager._client_contexts = []


@pytest.mark.asyncio
async def test_initialize_with_mcp_disabled(reset_mcp_manager):
    """Test that initialization is skipped when MCP is disabled."""
    with patch("app.infrastructure.mcp.mcp_client_manager.settings") as mock_settings:
        mock_settings.mcp_enabled = False

        await MCPClientManager.initialize()

        assert len(MCPClientManager._tools) == 0
        assert len(MCPClientManager._clients) == 0


@pytest.mark.asyncio
async def test_initialize_with_no_servers(reset_mcp_manager):
    """Test graceful handling when no servers configured."""
    with patch("app.infrastructure.mcp.mcp_client_manager.settings") as mock_settings:
        mock_settings.mcp_enabled = True
        mock_settings.get_mcp_servers = []

        await MCPClientManager.initialize()

        assert len(MCPClientManager._tools) == 0
        assert len(MCPClientManager._clients) == 0


@pytest.mark.asyncio
async def test_initialize_with_timeout(reset_mcp_manager):
    """Test that timeout prevents hanging during server connection."""
    with patch("app.infrastructure.mcp.mcp_client_manager.settings") as mock_settings:
        mock_settings.mcp_enabled = True
        mock_settings.get_mcp_servers = [{
            "name": "test-server",
            "transport": "stdio",
            "command": "python",
            "args": ["-m", "nonexistent_module"]
        }]

        # Initialize should complete without hanging
        await MCPClientManager.initialize()

        # Should have 0 tools due to timeout/error
        assert len(MCPClientManager._tools) == 0


@pytest.mark.asyncio
async def test_get_tools_returns_copy(reset_mcp_manager):
    """Test that get_tools returns a copy, not reference."""
    test_tool = lambda: "test"
    MCPClientManager._tools = [test_tool]

    tools = MCPClientManager.get_tools()
    tools.append(lambda: "modified")

    # Original should be unchanged
    assert len(MCPClientManager._tools) == 1
    assert len(tools) == 2


@pytest.mark.asyncio
async def test_shutdown_clears_state(reset_mcp_manager):
    """Test that shutdown clears all connections and tools."""
    # Setup some mock state
    MCPClientManager._clients = {"test": MagicMock()}
    MCPClientManager._tools = [lambda: "test"]
    MCPClientManager._client_contexts = [MagicMock()]

    await MCPClientManager.shutdown()

    assert len(MCPClientManager._clients) == 0
    assert len(MCPClientManager._tools) == 0
    assert len(MCPClientManager._client_contexts) == 0


@pytest.mark.asyncio
async def test_singleton_pattern(reset_mcp_manager):
    """Test that MCPClientManager follows singleton pattern."""
    instance1 = MCPClientManager()
    instance2 = MCPClientManager()

    assert instance1 is instance2


@pytest.mark.asyncio
async def test_connection_error_graceful_degradation(reset_mcp_manager):
    """Test graceful degradation when server connection fails."""
    with patch("app.infrastructure.mcp.mcp_client_manager.settings") as mock_settings:
        mock_settings.mcp_enabled = True
        mock_settings.get_mcp_servers = [
            {
                "name": "failing-server",
                "transport": "stdio",
                "command": "nonexistent_command",
                "args": []
            },
            {
                "name": "another-failing-server",
                "transport": "stdio",
                "command": "also_nonexistent",
                "args": []
            }
        ]

        # Should not raise exception, just log errors
        await MCPClientManager.initialize()

        # Should complete with 0 tools but not crash
        assert len(MCPClientManager._tools) == 0
        assert len(MCPClientManager._clients) == 0
