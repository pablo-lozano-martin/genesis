# ABOUTME: MCP client manager for connecting to and managing MCP servers
# ABOUTME: Follows ChromaDBClient singleton pattern for lifecycle management

import asyncio
from typing import Dict, List, Optional, Callable, Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client
from app.infrastructure.config.settings import settings
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)


class MCPClientManager:
    """Manages MCP client connections and tool discovery."""

    _instance = None
    _clients: Dict[str, ClientSession] = {}
    _tools: List[Callable] = []
    _client_contexts: List[Any] = []

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    async def initialize(cls) -> None:
        """Initialize connections to all configured MCP servers."""
        if not settings.mcp_enabled:
            logger.info("MCP is disabled, skipping initialization")
            return

        mcp_servers = settings.get_mcp_servers
        if not mcp_servers:
            logger.warning("No MCP servers configured")
            return

        logger.info(f"Initializing {len(mcp_servers)} MCP server(s)")

        for server_config in mcp_servers:
            try:
                await cls._connect_server(server_config)
            except Exception as e:
                logger.error(f"Failed to connect to MCP server '{server_config.get('name')}': {e}")
                # Continue with other servers (graceful degradation)

        logger.info(f"MCP initialization complete. {len(cls._tools)} tools available")

    @classmethod
    async def _connect_server(cls, server_config: dict) -> None:
        """Connect to a single MCP server and discover its tools."""
        server_name = server_config.get("name", "unknown")
        transport = server_config.get("transport", "stdio")

        logger.info(f"Connecting to MCP server '{server_name}' via {transport}")

        # Create server parameters based on transport type
        if transport == "stdio":
            # Stdio transport
            params = StdioServerParameters(
                command=server_config["command"],
                args=server_config.get("args", []),
                env=server_config.get("env", None)
            )

            # Keep session alive by storing context managers
            stdio_context = stdio_client(params)
            read, write = await stdio_context.__aenter__()
            cls._client_contexts.append(stdio_context)

            session = ClientSession(read, write)
            await session.initialize()

            cls._clients[server_name] = session
            await cls._discover_tools(session, server_name)

        elif transport == "sse":
            # SSE transport
            url = server_config["url"]
            sse_context = sse_client(url)
            read, write = await sse_context.__aenter__()
            cls._client_contexts.append(sse_context)

            session = ClientSession(read, write)
            await session.initialize()

            cls._clients[server_name] = session
            await cls._discover_tools(session, server_name)

        else:
            logger.error(f"Unsupported transport: {transport}")

    @classmethod
    async def _discover_tools(cls, session: ClientSession, server_name: str) -> None:
        """Discover and register tools from an MCP server."""
        tools_response = await session.list_tools()

        for tool_def in tools_response.tools:
            logger.info(f"Discovered tool: {server_name}:{tool_def.name}")
            # Tool conversion will be handled in Phase 2
            # For now, just log discovery

    @classmethod
    def get_tools(cls) -> List[Callable]:
        """Return all discovered MCP tools as Python callables."""
        return cls._tools.copy()

    @classmethod
    async def shutdown(cls) -> None:
        """Close all MCP client connections."""
        logger.info("Shutting down MCP client manager")

        # Close all active context managers
        for context in cls._client_contexts:
            try:
                await context.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"Error closing MCP context: {e}")

        cls._clients.clear()
        cls._tools.clear()
        cls._client_contexts.clear()
        logger.info("MCP client manager shutdown complete")
