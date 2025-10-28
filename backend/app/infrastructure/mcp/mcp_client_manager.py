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
    _session_contexts: List[Any] = []

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
                # Add timeout to prevent hanging
                await asyncio.wait_for(
                    cls._connect_server(server_config),
                    timeout=10.0  # 10 second timeout
                )
            except asyncio.TimeoutError:
                logger.error(f"Timeout connecting to MCP server '{server_config.get('name')}' after 10 seconds")
                # Continue with other servers (graceful degradation)
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

            # Also keep ClientSession as context manager
            session_obj = ClientSession(read, write)
            session = await session_obj.__aenter__()
            cls._session_contexts.append((session_obj, session))

            await session.initialize()

            cls._clients[server_name] = session
            await cls._discover_tools(session, server_name)

        elif transport == "sse":
            # SSE transport
            url = server_config["url"]
            sse_context = sse_client(url)
            read, write = await sse_context.__aenter__()
            cls._client_contexts.append(sse_context)

            # Also keep ClientSession as context manager
            session_obj = ClientSession(read, write)
            session = await session_obj.__aenter__()
            cls._session_contexts.append((session_obj, session))

            await session.initialize()

            cls._clients[server_name] = session
            await cls._discover_tools(session, server_name)

        else:
            logger.error(f"Unsupported transport: {transport}")

    @classmethod
    async def _discover_tools(cls, session: ClientSession, server_name: str) -> None:
        """Discover and register tools from an MCP server by creating LangChain StructuredTool instances."""
        try:
            # Get tool definitions from MCP server
            tools_response = await session.list_tools()
            
            for tool_def in tools_response.tools:
                # Create a LangChain StructuredTool
                from langchain_core.tools import StructuredTool
                from pydantic import create_model
                import json
                
                # Create Pydantic model for tool arguments from inputSchema
                if tool_def.inputSchema and tool_def.inputSchema.get('properties'):
                    fields = {}
                    for prop_name, prop_def in tool_def.inputSchema['properties'].items():
                        # Simple type mapping - could be improved
                        if prop_def.get('type') == 'string':
                            fields[prop_name] = (str, ...)
                        elif prop_def.get('type') == 'number':
                            fields[prop_name] = (float, ...)
                        elif prop_def.get('type') == 'integer':
                            fields[prop_name] = (int, ...)
                        elif prop_def.get('type') == 'boolean':
                            fields[prop_name] = (bool, ...)
                        else:
                            fields[prop_name] = (str, ...)  # Default to string
                    
                    ArgsModel = create_model(f"{tool_def.name}Args", **fields)
                else:
                    ArgsModel = create_model(f"{tool_def.name}Args")  # Empty model
                
                # Create async function that calls the MCP tool
                async def mcp_tool_func(**kwargs):
                    try:
                        # Preprocess arguments
                        processed_kwargs = {}
                        for k, v in kwargs.items():
                            if k == 'url' and isinstance(v, str) and not v.startswith(('http://', 'https://')):
                                processed_kwargs[k] = f'https://{v}'
                            else:
                                processed_kwargs[k] = v
                        
                        result = await session.call_tool(tool_def.name, processed_kwargs)
                        # Extract text content from result
                        if result.content and len(result.content) > 0:
                            content = result.content[0]
                            if hasattr(content, 'text'):
                                return content.text
                            else:
                                return str(content)
                        else:
                            return ""
                    except Exception as e:
                        logger.error(f"MCP tool '{tool_def.name}' execution failed: {e}")
                        return f"Error: {str(e)}"
                
                # Create StructuredTool
                tool = StructuredTool.from_function(
                    func=mcp_tool_func,
                    name=tool_def.name,
                    description=tool_def.description or f"MCP tool: {tool_def.name}",
                    args_schema=ArgsModel
                )
                
                cls._tools.append(tool)
                logger.info(f"Registered MCP tool: {tool_def.name}")

        except Exception as e:
            logger.error(f"Failed to load tools from server '{server_name}': {e}")
            # Continue gracefully (no tools from this server)

    @classmethod
    def get_tools(cls) -> List[Callable]:
        """Return all discovered MCP tools as Python callables."""
        return cls._tools.copy()

    @classmethod
    async def shutdown(cls) -> None:
        """Close all MCP client connections."""
        logger.info("Shutting down MCP client manager")

        # Clear references first to prevent new operations
        cls._clients.clear()
        cls._tools.clear()

        # Close session contexts first (inner context)
        for session_obj, session in cls._session_contexts:
            try:
                await session_obj.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error closing MCP session context: {e}")

        # Close client contexts (outer context)
        for context in cls._client_contexts:
            try:
                await context.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error closing MCP client context: {e}")

        # Clear context lists after attempting cleanup
        cls._client_contexts.clear()
        cls._session_contexts.clear()
        logger.info("MCP client manager shutdown complete")
