# Implementation Plan: Add MCP (Model Context Protocol) Support to Chatbot

## Executive Summary

This plan details the implementation of MCP (Model Context Protocol) support for the Genesis chatbot, enabling dynamic tool discovery and execution from MCP servers. The implementation maintains Genesis's hexagonal architecture, adds zero changes to the domain core, and provides full backward compatibility with existing Python tools.

**Scope**: Enable Genesis to discover and execute tools from MCP servers alongside existing native Python tools (add, multiply, web_search, rag_search).

**Architecture Decision**: MCP integration lives in the infrastructure layer (like ChromaDB), not as a domain port, to maintain simplicity while following hexagonal principles.

---

## Table of Contents

1. [Prerequisites & Configuration](#prerequisites--configuration)
2. [Implementation Phases](#implementation-phases)
3. [Phase 1: MCP Infrastructure Foundation](#phase-1-mcp-infrastructure-foundation)
4. [Phase 2: Tool Discovery & Conversion](#phase-2-tool-discovery--conversion)
5. [Phase 3: LangGraph Integration](#phase-3-langgraph-integration)
6. [Phase 4: Frontend Integration](#phase-4-frontend-integration)
7. [Phase 5: Testing & Validation](#phase-5-testing--validation)
8. [Testing Strategy](#testing-strategy)
9. [Deployment Guide](#deployment-guide)
10. [Risks & Mitigations](#risks--mitigations)

---

## Prerequisites & Configuration

### Dependencies

Add to `backend/requirements.txt`:
```txt
# Model Context Protocol
mcp>=1.0.0
```

### Configuration File Structure

**Location**: `backend/genesis_mcp.json`

The configuration file supports both stdio and HTTP transports:

```json
[
  {
    "name": "sqlite",
    "transport": "stdio",
    "command": "uvx",
    "args": ["mcp-server-sqlite", "--db-path", "./test.db"],
    "env": {}
  },
  {
    "name": "weather",
    "transport": "streamable-http",
    "url": "http://localhost:8001/mcp"
  }
]
```

**Environment Variables**:
```bash
# .env
MCP_ENABLED=true
MCP_CONFIG_PATH=./genesis_mcp.json
```

### Add to .gitignore

```bash
# backend/.gitignore
genesis_mcp.json
```

Create example file:
```bash
# backend/genesis_mcp.example.json
[
  {
    "name": "example-mcp-server",
    "transport": "stdio",
    "command": "uvx",
    "args": ["mcp-simple-tool"],
    "env": {}
  }
]
```

---

## Implementation Phases

### Overview

| Phase | Description | Estimated Time |
|-------|-------------|----------------|
| **Phase 1** | MCP Infrastructure Foundation | 4-6 hours |
| **Phase 2** | Tool Discovery & Conversion | 4-6 hours |
| **Phase 3** | LangGraph Integration | 3-4 hours |
| **Phase 4** | Frontend Integration | 2-3 hours |
| **Phase 5** | Testing & Validation | 6-8 hours |
| **Total** | | 19-27 hours |

---

## Phase 1: MCP Infrastructure Foundation

### Objective
Create the infrastructure layer for MCP client management, following the ChromaDBClient pattern.

### Files to Create

#### 1.1 MCP Settings Extension

**File**: `backend/app/infrastructure/config/settings.py`

Add to the `Settings` class:

```python
# MCP Settings
mcp_enabled: bool = False
mcp_config_path: str = "./genesis_mcp.json"

@property
def get_mcp_servers(self) -> list[dict]:
    """Load MCP servers from config file."""
    if not self.mcp_enabled:
        return []

    config_path = Path(self.mcp_config_path)
    if config_path.exists():
        try:
            return json.loads(config_path.read_text())
        except Exception as e:
            logger.error(f"Failed to load MCP config: {e}")
            return []
    return []
```

**Changes Required**:
- Import `Path` from `pathlib`
- Import `json`
- Import `logger` from `logging_config`

#### 1.2 MCP Client Manager

**File**: `backend/app/infrastructure/mcp/mcp_client_manager.py`

```python
# ABOUTME: MCP client manager for connecting to and managing MCP servers
# ABOUTME: Follows ChromaDBClient singleton pattern for lifecycle management

import asyncio
from typing import Dict, List, Optional, Callable
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client
from app.infrastructure.config.settings import settings
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)


class MCPClientManager:
    """Manages MCP client connections and tool discovery."""

    _instance = None
    _clients: Dict[str, ClientSession] = {}
    _tools: List[Callable] = []

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
                env=server_config.get("env", {})
            )
            # Connect and discover tools
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    await cls._discover_tools(session, server_name)

        elif transport == "streamable-http":
            # HTTP transport
            url = server_config["url"]
            async with streamablehttp_client(url) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
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
        # Close all active connections
        for name, client in cls._clients.items():
            try:
                logger.info(f"Closing connection to {name}")
                # MCP sessions are managed by context managers
            except Exception as e:
                logger.error(f"Error closing {name}: {e}")

        cls._clients.clear()
        cls._tools.clear()
        logger.info("MCP client manager shutdown complete")
```

#### 1.3 Module Init File

**File**: `backend/app/infrastructure/mcp/__init__.py`

```python
# ABOUTME: MCP infrastructure module for Model Context Protocol integration
# ABOUTME: Provides client management and tool discovery capabilities

from .mcp_client_manager import MCPClientManager

__all__ = ["MCPClientManager"]
```

#### 1.4 Application Lifecycle Integration

**File**: `backend/app/main.py`

Modify the `lifespan` function:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")

    # ... existing startup code (AppDatabase, ChromaDB, checkpointer) ...

    # Initialize MCP client manager (NEW)
    from app.infrastructure.mcp import MCPClientManager
    try:
        await MCPClientManager.initialize()
        app.state.mcp_manager = MCPClientManager
        logger.info("MCP client manager initialized")
    except Exception as e:
        logger.error(f"MCP initialization failed: {e}")
        app.state.mcp_manager = None

    # ... existing graph compilation ...

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down application")

    # Shutdown MCP (NEW)
    if hasattr(app.state, 'mcp_manager') and app.state.mcp_manager:
        await MCPClientManager.shutdown()

    # ... existing shutdown code ...
    logger.info("Application shutdown complete")
```

**Testing Checkpoint**: After Phase 1
- Application starts successfully with `MCP_ENABLED=false`
- Application starts successfully with `MCP_ENABLED=true` and valid config
- Application handles missing/invalid config gracefully
- Logs show MCP initialization attempt

---

## Phase 2: Tool Discovery & Conversion

### Objective
Convert MCP tool definitions to Python callables compatible with LangChain's bind_tools().

### Files to Create

#### 2.1 MCP Tool Adapter

**File**: `backend/app/langgraph/tools/mcp_adapter.py`

```python
# ABOUTME: MCP tool adapter converting MCP tool definitions to Python callables
# ABOUTME: Enables LangChain bind_tools() to work with MCP tools transparently

import json
import asyncio
from typing import Any, Dict, Optional, Callable
from pydantic import BaseModel
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)


class MCPToolDefinition(BaseModel):
    """Data transfer object for MCP tool schema."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Optional[Dict[str, Any]] = None


class MCPToolAdapter:
    """
    Wraps MCP tool definition as Python callable for LangChain binding.

    This adapter makes MCP tools appear as native Python functions with:
    - __name__ property (tool name)
    - __doc__ property (tool description)
    - Type hints extracted from MCP schema
    - Async __call__ method for execution
    """

    def __init__(
        self,
        definition: MCPToolDefinition,
        session: Any,  # MCP ClientSession
        namespace: str = ""
    ):
        self.definition = definition
        self.session = session
        self.namespace = namespace
        self._build_signature()

    async def __call__(self, **kwargs) -> str:
        """
        Execute MCP tool via the MCP session.

        Args:
            **kwargs: Tool parameters from LLM

        Returns:
            String representation of tool result
        """
        try:
            logger.info(f"Executing MCP tool: {self.definition.name} with args: {kwargs}")

            # Call MCP server via session
            result = await self.session.call_tool(self.definition.name, kwargs)

            # Extract result content
            if result.content:
                # Return first content item as string
                content = result.content[0]
                if hasattr(content, 'text'):
                    return content.text
                else:
                    return str(content)

            return "Tool executed successfully (no output)"

        except Exception as e:
            logger.error(f"MCP tool execution failed: {e}")
            return f"Error executing tool: {str(e)}"

    @property
    def __name__(self) -> str:
        """Tool name with optional namespace."""
        if self.namespace:
            return f"{self.namespace}:{self.definition.name}"
        return self.definition.name

    @property
    def __doc__(self) -> str:
        """Tool description from MCP schema."""
        return self.definition.description

    def _build_signature(self):
        """
        Extract Python function signature from MCP input_schema.

        This method would generate type hints for LangChain introspection.
        For MVP, we'll rely on the schema being passed to bind_tools directly.
        """
        # TODO: Advanced type hint generation from JSON Schema
        # For now, LangChain will use __name__ and __doc__
        pass
```

#### 2.2 Update MCP Client Manager for Tool Conversion

**File**: `backend/app/infrastructure/mcp/mcp_client_manager.py`

Update the `_discover_tools` method:

```python
@classmethod
async def _discover_tools(cls, session: ClientSession, server_name: str) -> None:
    """Discover and register tools from an MCP server."""
    from app.langgraph.tools.mcp_adapter import MCPToolAdapter, MCPToolDefinition

    tools_response = await session.list_tools()

    for tool_def in tools_response.tools:
        try:
            # Convert MCP tool to adapter
            definition = MCPToolDefinition(
                name=tool_def.name,
                description=tool_def.description or f"Tool: {tool_def.name}",
                input_schema=tool_def.inputSchema or {}
            )

            # Create adapter with namespace
            adapter = MCPToolAdapter(
                definition=definition,
                session=session,
                namespace=server_name
            )

            cls._tools.append(adapter)
            logger.info(f"Registered MCP tool: {adapter.__name__}")

        except Exception as e:
            logger.error(f"Failed to convert tool {tool_def.name}: {e}")
            # Continue with other tools (graceful degradation)
```

**Critical Issue**: MCP sessions need to be kept alive. Update `_connect_server`:

```python
@classmethod
async def _connect_server(cls, server_config: dict) -> None:
    """Connect to a single MCP server and discover its tools."""
    server_name = server_config.get("name", "unknown")
    transport = server_config.get("transport", "stdio")

    logger.info(f"Connecting to MCP server '{server_name}' via {transport}")

    # Store session for later tool execution
    if transport == "stdio":
        params = StdioServerParameters(
            command=server_config["command"],
            args=server_config.get("args", []),
            env=server_config.get("env", {})
        )

        # Keep session alive by storing it
        read, write = await stdio_client(params).__aenter__()
        session = ClientSession(read, write)
        await session.initialize()

        cls._clients[server_name] = session
        await cls._discover_tools(session, server_name)

    elif transport == "streamable-http":
        url = server_config["url"]
        read, write, _ = await streamablehttp_client(url).__aenter__()
        session = ClientSession(read, write)
        await session.initialize()

        cls._clients[server_name] = session
        await cls._discover_tools(session, server_name)
```

**Testing Checkpoint**: After Phase 2
- MCP tools are discovered and converted to adapters
- Adapters have correct `__name__` and `__doc__`
- Tool count matches expected from MCP server
- Graceful handling of invalid tool definitions

---

## Phase 3: LangGraph Integration

### Objective
Integrate MCP tools with LangGraph's call_llm node and ToolNode execution.

### Files to Modify

#### 3.1 Update call_llm Node

**File**: `backend/app/langgraph/nodes/call_llm.py`

Current code (lines 37-41):
```python
tools = [multiply, add, web_search, rag_search]

llm_provider_with_tools = llm_provider.bind_tools(tools, parallel_tool_calls=False)
```

Updated code:
```python
# Get local Python tools
local_tools = [multiply, add, web_search, rag_search]

# Get MCP tools from manager
mcp_tools = []
if hasattr(config["configurable"], "get"):
    from app.infrastructure.mcp import MCPClientManager
    try:
        mcp_manager = MCPClientManager()
        mcp_tools = mcp_manager.get_tools()
        if mcp_tools:
            logger.info(f"Binding {len(mcp_tools)} MCP tools to LLM")
    except Exception as e:
        logger.warning(f"Failed to load MCP tools: {e}")

# Combine all tools
all_tools = local_tools + mcp_tools

llm_provider_with_tools = llm_provider.bind_tools(all_tools, parallel_tool_calls=False)
```

**Note**: No changes needed to graph structure since ToolNode is created with hardcoded tools. MCP tools will be bound at LLM invocation time, and ToolNode will resolve them by name lookup in the bound tools.

#### 3.2 Update Graph Creation (Optional Enhancement)

**File**: `backend/app/langgraph/graphs/streaming_chat_graph.py`

Current hardcoded tools (line 44):
```python
tools = [multiply, add, web_search, rag_search]
```

For Phase 3, this can remain unchanged since ToolNode will execute any tool bound to the LLM. However, for better architecture:

```python
def create_streaming_chat_graph(checkpointer: AsyncMongoDBSaver, tools: Optional[List[Callable]] = None):
    """
    Create and compile the streaming chat graph with automatic checkpointing.

    Args:
        checkpointer: AsyncMongoDBSaver instance
        tools: Optional list of tools (defaults to local tools)
    """
    logger.info("Creating streaming chat conversation graph with checkpointer and tool execution")

    if tools is None:
        # Default to local tools
        tools = [multiply, add, web_search, rag_search]

    graph_builder = StateGraph(ConversationState)
    graph_builder.add_node("tools", ToolNode(tools))

    # ... rest of graph setup
```

Then in `main.py`:
```python
# Compile graphs with combined tools
from app.langgraph.tools.multiply import multiply
from app.langgraph.tools.add import add
from app.langgraph.tools.web_search import web_search
from app.langgraph.tools.rag_search import rag_search

local_tools = [multiply, add, web_search, rag_search]
mcp_tools = MCPClientManager.get_tools() if app.state.mcp_manager else []
all_tools = local_tools + mcp_tools

app.state.chat_graph = create_chat_graph(checkpointer, all_tools)
app.state.streaming_chat_graph = create_streaming_chat_graph(checkpointer, all_tools)
```

**Testing Checkpoint**: After Phase 3
- MCP tools appear in LLM's tool list
- LLM can select and invoke MCP tools
- ToolNode successfully executes MCP tool adapters
- Results return correctly as ToolMessages
- Checkpointing preserves MCP tool execution history

---

## Phase 4: Frontend Integration

### Objective
Add visual indicators to distinguish MCP tools from native tools in the UI.

### Files to Modify

#### 4.1 Extend WebSocket Message Schemas

**File**: `backend/app/adapters/inbound/websocket_schemas.py`

Add optional `source` field to tool messages:

```python
class ServerToolStartMessage(BaseModel):
    """Server message indicating tool execution has started."""
    type: Literal[MessageType.TOOL_START] = MessageType.TOOL_START
    tool_name: str = Field(..., description="Name of the tool being executed")
    tool_input: str = Field(..., description="JSON string of input arguments")
    source: Optional[str] = Field(
        default="local",
        description="Tool source: 'local' for Python tools, 'mcp' for MCP protocol tools"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="ISO timestamp of tool start"
    )


class ServerToolCompleteMessage(BaseModel):
    """Server message indicating tool execution has completed."""
    type: Literal[MessageType.TOOL_COMPLETE] = MessageType.TOOL_COMPLETE
    tool_name: str = Field(..., description="Name of the tool that completed")
    tool_result: str = Field(..., description="String representation of tool result")
    source: Optional[str] = Field(
        default="local",
        description="Tool source: 'local' for Python tools, 'mcp' for MCP protocol tools"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="ISO timestamp of tool completion"
    )
```

#### 4.2 Create Tool Metadata Registry

**File**: `backend/app/langgraph/tool_metadata.py`

```python
# ABOUTME: Tool metadata registry for tracking tool sources and schemas
# ABOUTME: Enables distinction between local and MCP tools for frontend consumption

from enum import Enum
from typing import Dict, Optional
from pydantic import BaseModel, Field


class ToolSource(str, Enum):
    """Enumeration of tool sources."""
    LOCAL = "local"
    MCP = "mcp"


class ToolMetadata(BaseModel):
    """Metadata about a tool."""
    name: str = Field(..., description="Tool name")
    description: Optional[str] = Field(None, description="Tool description")
    source: ToolSource = Field(..., description="Tool source (local or mcp)")

    class Config:
        use_enum_values = True


class ToolRegistry:
    """Registry of available tools with metadata."""

    def __init__(self):
        self._tools: Dict[str, ToolMetadata] = {}

    def register_tool(self, tool: ToolMetadata) -> None:
        """Register a tool in the registry."""
        self._tools[tool.name] = tool

    def get_tool_source(self, name: str) -> Optional[ToolSource]:
        """Get the source of a specific tool."""
        tool = self._tools.get(name)
        return tool.source if tool else None


# Global registry instance
_tool_registry = ToolRegistry()


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry."""
    return _tool_registry
```

#### 4.3 Register Tools in Registry

**File**: `backend/app/main.py`

In the `lifespan` function, after MCP initialization:

```python
# Register tools in metadata registry (NEW)
from app.langgraph.tool_metadata import get_tool_registry, ToolMetadata, ToolSource

tool_registry = get_tool_registry()

# Register local tools
for tool_name in ["multiply", "add", "web_search", "rag_search"]:
    tool_registry.register_tool(ToolMetadata(
        name=tool_name,
        description=f"Local Python tool: {tool_name}",
        source=ToolSource.LOCAL
    ))

# Register MCP tools
if app.state.mcp_manager:
    mcp_tools = MCPClientManager.get_tools()
    for tool in mcp_tools:
        tool_registry.register_tool(ToolMetadata(
            name=tool.__name__,
            description=tool.__doc__ or "",
            source=ToolSource.MCP
        ))

app.state.tool_registry = tool_registry
logger.info(f"Tool registry initialized with {len(tool_registry._tools)} tools")
```

#### 4.4 Update WebSocket Handler

**File**: `backend/app/adapters/inbound/websocket_handler.py`

Update tool event emission (around lines 169-186):

```python
from app.langgraph.tool_metadata import get_tool_registry

# Inside handle_websocket_chat function:
tool_registry = get_tool_registry()

# ... existing streaming code ...

# Emit TOOL_START when tool begins execution
elif event_type == "on_tool_start":
    if current_tool_call:
        tool_name = current_tool_call.get("name", "unknown")
        tool_source = tool_registry.get_tool_source(tool_name)

        tool_start_msg = ServerToolStartMessage(
            tool_name=tool_name,
            tool_input=json.dumps(current_tool_call.get("args", {})),
            source=tool_source.value if tool_source else "local"
        )
        await manager.send_message(websocket, tool_start_msg.model_dump())

# Emit TOOL_COMPLETE when tool finishes
elif event_type == "on_tool_end":
    if current_tool_call:
        tool_name = current_tool_call.get("name", "unknown")
        tool_source = tool_registry.get_tool_source(tool_name)
        tool_result = event["data"].get("output", "")

        tool_complete_msg = ServerToolCompleteMessage(
            tool_name=tool_name,
            tool_result=str(tool_result),
            source=tool_source.value if tool_source else "local"
        )
        await manager.send_message(websocket, tool_complete_msg.model_dump())
        current_tool_call = None
```

#### 4.5 Frontend Type Updates

**File**: `frontend/src/contexts/ChatContext.tsx`

Update `ToolExecution` interface:

```typescript
export interface ToolExecution {
  id: string;
  toolName: string;
  toolInput: string;
  toolResult?: string;
  status: "running" | "completed";
  startTime: string;
  endTime?: string;
  source?: "local" | "mcp";  // NEW
}
```

Update `handleToolStart`:

```typescript
const handleToolStart = useCallback((toolName: string, toolInput: string, source?: string) => {
  const execution: ToolExecution = {
    id: `${Date.now()}-${toolName}`,
    toolName,
    toolInput,
    status: "running",
    startTime: new Date().toISOString(),
    source: source || "local",  // NEW
  };
  currentToolExecutionRef.current = execution;
  setCurrentToolExecution(execution);
  setToolExecutions((prev) => [...prev, execution]);
}, []);
```

#### 4.6 Frontend WebSocket Service

**File**: `frontend/src/services/websocketService.ts`

Update message interfaces:

```typescript
export interface ServerToolStartMessage {
  type: typeof MessageType.TOOL_START;
  tool_name: string;
  tool_input: string;
  timestamp: string;
  source?: "local" | "mcp";  // NEW
}

export interface ServerToolCompleteMessage {
  type: typeof MessageType.TOOL_COMPLETE;
  tool_name: string;
  tool_result: string;
  timestamp: string;
  source?: "local" | "mcp";  // NEW
}
```

Update message handling (lines 155-161):

```typescript
case MessageType.TOOL_START:
  this.config.onToolStart?.(message.tool_name, message.tool_input, message.source);
  break;

case MessageType.TOOL_COMPLETE:
  this.config.onToolComplete?.(message.tool_name, message.tool_result, message.source);
  break;
```

#### 4.7 Frontend WebSocket Hook

**File**: `frontend/src/hooks/useWebSocket.ts`

Update callback signatures:

```typescript
export interface UseWebSocketOptions {
  url: string;
  token: string;
  autoConnect?: boolean;
  onToolStart?: (toolName: string, toolInput: string, source?: string) => void;  // NEW
  onToolComplete?: (toolName: string, toolResult: string, source?: string) => void;  // NEW
}
```

#### 4.8 Frontend Tool Display Component

**File**: `frontend/src/components/chat/ToolExecutionCard.tsx`

Update to show MCP badge:

```typescript
export const ToolExecutionCard: React.FC<ToolExecutionCardProps> = ({ execution }) => {
  const isMcpTool = execution.source === "mcp";

  return (
    <Card className={`my-1.5 border-l-2 ${isMcpTool ? "border-l-purple-500 bg-purple-50/50" : "border-l-blue-500 bg-blue-50/50"}`}>
      <div className="px-3 py-2">
        <div className="flex items-center gap-2">
          {execution.status === "running" && (
            <Loader2 className="h-3.5 w-3.5 animate-spin text-blue-600" />
          )}
          {execution.status === "completed" && (
            <Check className="h-3.5 w-3.5 text-green-600" />
          )}
          <Badge variant="outline" className={`font-mono text-xs ${isMcpTool ? "border-purple-300" : ""}`}>
            {execution.toolName}
          </Badge>
          {isMcpTool && (
            <Badge variant="secondary" className="text-xs bg-purple-100 text-purple-700">
              MCP
            </Badge>
          )}
          {execution.toolResult && (
            <span className="text-xs text-gray-600 font-mono">
              → {execution.toolResult}
            </span>
          )}
        </div>
      </div>
    </Card>
  );
};
```

**Testing Checkpoint**: After Phase 4
- MCP tool execution shows purple border and "MCP" badge
- Native tool execution shows blue border (no badge)
- WebSocket events include source metadata
- Frontend correctly distinguishes tool types

---

## Phase 5: Testing & Validation

### Objective
Comprehensive testing across all layers with >85% coverage.

### Test Files to Create

#### 5.1 Unit Tests: MCP Client

**File**: `backend/tests/unit/test_mcp_client_manager.py`

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.infrastructure.mcp import MCPClientManager
from app.infrastructure.config.settings import settings


@pytest.mark.asyncio
async def test_initialize_with_mcp_disabled():
    """Test that initialization is skipped when MCP is disabled."""
    with patch.object(settings, 'mcp_enabled', False):
        await MCPClientManager.initialize()
        assert len(MCPClientManager._tools) == 0


@pytest.mark.asyncio
async def test_initialize_with_no_servers():
    """Test graceful handling when no servers configured."""
    with patch.object(settings, 'mcp_enabled', True):
        with patch.object(settings, 'get_mcp_servers', []):
            await MCPClientManager.initialize()
            assert len(MCPClientManager._tools) == 0


@pytest.mark.asyncio
async def test_get_tools_returns_copy():
    """Test that get_tools returns a copy, not reference."""
    MCPClientManager._tools = [lambda: "test"]
    tools = MCPClientManager.get_tools()
    tools.append(lambda: "modified")

    assert len(MCPClientManager._tools) == 1
    assert len(tools) == 2


@pytest.mark.asyncio
async def test_shutdown_clears_state():
    """Test that shutdown clears all connections and tools."""
    MCPClientManager._clients = {"test": MagicMock()}
    MCPClientManager._tools = [lambda: "test"]

    await MCPClientManager.shutdown()

    assert len(MCPClientManager._clients) == 0
    assert len(MCPClientManager._tools) == 0
```

#### 5.2 Unit Tests: MCP Tool Adapter

**File**: `backend/tests/unit/test_mcp_tool_adapter.py`

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.langgraph.tools.mcp_adapter import MCPToolAdapter, MCPToolDefinition


def test_adapter_name_without_namespace():
    """Test tool name without namespace."""
    definition = MCPToolDefinition(
        name="search",
        description="Search tool",
        input_schema={}
    )
    adapter = MCPToolAdapter(definition, AsyncMock(), namespace="")

    assert adapter.__name__ == "search"


def test_adapter_name_with_namespace():
    """Test tool name with namespace prefix."""
    definition = MCPToolDefinition(
        name="search",
        description="Search tool",
        input_schema={}
    )
    adapter = MCPToolAdapter(definition, AsyncMock(), namespace="kb")

    assert adapter.__name__ == "kb:search"


def test_adapter_doc():
    """Test tool description extraction."""
    definition = MCPToolDefinition(
        name="search",
        description="Search the knowledge base",
        input_schema={}
    )
    adapter = MCPToolAdapter(definition, AsyncMock())

    assert adapter.__doc__ == "Search the knowledge base"


@pytest.mark.asyncio
async def test_adapter_call_success():
    """Test successful tool execution."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.content = [MagicMock(text="search results")]
    mock_session.call_tool.return_value = mock_result

    definition = MCPToolDefinition(
        name="search",
        description="Search tool",
        input_schema={}
    )
    adapter = MCPToolAdapter(definition, mock_session)

    result = await adapter(query="test")

    assert result == "search results"
    mock_session.call_tool.assert_called_once_with("search", {"query": "test"})


@pytest.mark.asyncio
async def test_adapter_call_error_handling():
    """Test error handling during tool execution."""
    mock_session = AsyncMock()
    mock_session.call_tool.side_effect = Exception("Connection error")

    definition = MCPToolDefinition(
        name="search",
        description="Search tool",
        input_schema={}
    )
    adapter = MCPToolAdapter(definition, mock_session)

    result = await adapter(query="test")

    assert "Error executing tool" in result
```

#### 5.3 Integration Tests: MCP Server Connection

**File**: `backend/tests/integration/test_mcp_server_connection.py`

```python
import pytest
from mcp.server.fastmcp import FastMCP


@pytest.fixture
async def mock_mcp_server():
    """Create a simple MCP server for testing."""
    mcp = FastMCP("TestServer")

    @mcp.tool()
    def test_add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    return mcp


@pytest.mark.integration
@pytest.mark.asyncio
async def test_connect_to_mock_server(mock_mcp_server):
    """Test connecting to a real mock MCP server."""
    # This test requires the mcp-simple-tool server to be running
    # For CI/CD, we'd start it as a subprocess

    from app.infrastructure.mcp import MCPClientManager

    # Configure MCP with test server
    test_config = [{
        "name": "test",
        "transport": "stdio",
        "command": "uvx",
        "args": ["mcp-simple-tool"]
    }]

    # Test would connect to server and discover tools
    # Implementation depends on test infrastructure setup
    pass
```

#### 5.4 Integration Tests: Full Conversation Flow

**File**: `backend/tests/integration/test_mcp_tools_in_conversation.py`

```python
import pytest
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
async def test_conversation_with_mcp_tool(client: AsyncClient):
    """Test full conversation flow using MCP tool."""
    # This test would:
    # 1. Create conversation
    # 2. Send message that triggers MCP tool
    # 3. Verify tool execution in response
    # 4. Check that tool result is in conversation history

    # Implementation depends on MCP test server setup
    pass
```

#### 5.5 Frontend Unit Tests

**File**: `frontend/src/components/chat/__tests__/ToolExecutionCard.test.tsx`

```typescript
import { render } from '@testing-library/react';
import { ToolExecutionCard } from '../ToolExecutionCard';
import { ToolExecution } from '@/contexts/ChatContext';

describe('ToolExecutionCard', () => {
  it('should render MCP tool with purple border and badge', () => {
    const execution: ToolExecution = {
      id: 'test-1',
      toolName: 'search_knowledge',
      toolInput: '{"query": "test"}',
      status: 'completed',
      toolResult: 'result',
      startTime: new Date().toISOString(),
      source: 'mcp'
    };

    const { container, getByText } = render(<ToolExecutionCard execution={execution} />);

    // Check for purple border
    const card = container.querySelector('[class*="border-l-purple-500"]');
    expect(card).toBeInTheDocument();

    // Check for MCP badge
    expect(getByText('MCP')).toBeInTheDocument();
  });

  it('should render native tool with blue border and no badge', () => {
    const execution: ToolExecution = {
      id: 'test-2',
      toolName: 'add',
      toolInput: '{"a": 1, "b": 2}',
      status: 'completed',
      toolResult: '3',
      startTime: new Date().toISOString(),
      source: 'local'
    };

    const { container, queryByText } = render(<ToolExecutionCard execution={execution} />);

    // Check for blue border
    const card = container.querySelector('[class*="border-l-blue-500"]');
    expect(card).toBeInTheDocument();

    // No MCP badge
    expect(queryByText('MCP')).not.toBeInTheDocument();
  });
});
```

---

## Testing Strategy

### Test Pyramid

```
     E2E (5%)
   Manual Testing

  Integration (25%)
Real MCP Test Server

    Unit (70%)
 Mocked Dependencies
```

### Coverage Goals

- **Unit Tests**: 95%+ of MCP client/adapter code
- **Integration Tests**: 90%+ of MCP integration paths
- **Overall Target**: 85%+ combined coverage
- **Critical Path**: 100% of tool execution flow

### Test Execution Plan

1. **Local Development**:
   ```bash
   pytest tests/unit/test_mcp*.py -v
   ```

2. **Integration Tests** (requires mcp-simple-tool):
   ```bash
   uvx mcp-simple-tool &  # Start test server
   pytest tests/integration/test_mcp*.py -v
   kill %1  # Stop test server
   ```

3. **Full Test Suite**:
   ```bash
   pytest --cov=app --cov-report=html
   ```

4. **Frontend Tests**:
   ```bash
   cd frontend
   npm test -- --coverage
   ```

---

## Deployment Guide

### Step 1: Install Dependencies

```bash
cd backend
pip install mcp>=1.0.0
```

### Step 2: Create Example Config

```bash
cp genesis_mcp.example.json genesis_mcp.json
```

Edit `genesis_mcp.json` with your MCP servers.

### Step 3: Configure Environment

```bash
# .env
MCP_ENABLED=true
MCP_CONFIG_PATH=./genesis_mcp.json
```

### Step 4: Test with Simple MCP Server

```bash
# Terminal 1: Start test MCP server
uvx mcp-simple-tool

# Terminal 2: Start Genesis backend
python -m uvicorn app.main:app --reload
```

### Step 5: Verify in Logs

```
INFO: MCP client manager initialized
INFO: Discovered tool: simple-tool:fetch
INFO: Registered MCP tool: simple-tool:fetch
INFO: Tool registry initialized with 5 tools
```

### Step 6: Test in Frontend

1. Open chat UI
2. Send message: "Use the fetch tool to get https://example.com"
3. Verify:
   - Tool execution card appears with purple border
   - "MCP" badge is visible
   - Tool executes successfully

---

## Risks & Mitigations

### Risk 1: MCP Server Unavailability

**Impact**: High - Tools unavailable if server is down

**Mitigation**:
- Graceful degradation (continue with local tools)
- Health checks at startup
- Clear error logging
- Retry logic with exponential backoff (future enhancement)

### Risk 2: Tool Name Collisions

**Impact**: Medium - Conflicts between local and MCP tools

**Mitigation**:
- Mandatory namespacing for MCP tools (`server:tool_name`)
- Registry validates unique names
- Clear error if collision detected

### Risk 3: MCP Session Management

**Impact**: High - Sessions must stay alive for tool execution

**Mitigation**:
- Store sessions in `_clients` dict
- Proper context manager usage
- Cleanup on shutdown
- Connection pooling for HTTP transport

### Risk 4: Type Hint Generation

**Impact**: Medium - LangChain may not properly introspect MCP tools

**Mitigation**:
- Rely on LangChain's schema-based binding
- Fall back to generic schema if type hints fail
- Test with all LLM providers (OpenAI, Anthropic, Gemini, Ollama)

### Risk 5: Frontend Backward Compatibility

**Impact**: Low - Older clients may not handle source field

**Mitigation**:
- Make source field optional with default value
- Frontend defaults to "local" if missing
- No breaking changes to existing messages

### Risk 6: Startup Time

**Impact**: Medium - Multiple MCP connections slow startup

**Mitigation**:
- Parallel connection initialization (asyncio.gather)
- Configurable timeout per server
- Continue startup even if some servers fail
- Log warnings instead of errors

---

## Documentation Updates

### Files to Update

#### 1. Architecture Documentation

**File**: `doc/general/ARCHITECTURE.md`

Add new section:

```markdown
## MCP (Model Context Protocol) Integration

Genesis supports dynamic tool discovery and execution via MCP servers, extending the chatbot's capabilities beyond native Python tools.

### Architecture

MCP integration lives in the infrastructure layer (like ChromaDBClient), not as a domain port:

```
Infrastructure Layer:
├── MCPClientManager (singleton, lifecycle management)
├── MCPToolAdapter (converts MCP tools to Python callables)
└── Tool Registry (tracks tool sources for frontend)

LangGraph Integration:
├── call_llm node (binds MCP tools to provider)
└── ToolNode (executes MCP tools via adapters)
```

### Configuration

MCP servers are configured in `genesis_mcp.json`:

```json
[
  {
    "name": "server-name",
    "transport": "stdio" | "streamable-http",
    "command": "uvx",
    "args": ["mcp-server-name"],
    "url": "http://..." (for HTTP transport)
  }
]
```

Environment variables:
- `MCP_ENABLED`: Enable/disable MCP support
- `MCP_CONFIG_PATH`: Path to config file

### Tool Discovery Flow

1. Application startup → MCPClientManager.initialize()
2. Connect to configured MCP servers
3. Discover tools via MCP protocol
4. Convert to Python callables (MCPToolAdapter)
5. Register in tool registry with source metadata
6. Bind to LLM provider alongside native tools

### Tool Execution Flow

1. LLM decides to call tool
2. LangGraph ToolNode invokes adapter
3. Adapter calls MCP server via session
4. Result returned as ToolMessage
5. Frontend displays with MCP badge indicator
```

#### 2. Development Documentation

**File**: `doc/general/DEVELOPMENT.md`

Add new section:

```markdown
## MCP Development

### Setting Up MCP Servers

1. Create `genesis_mcp.json`:
   ```bash
   cp genesis_mcp.example.json genesis_mcp.json
   ```

2. Add your MCP servers to the config

3. Enable MCP:
   ```bash
   echo "MCP_ENABLED=true" >> .env
   ```

### Testing with mcp-simple-tool

```bash
# Terminal 1: Start test server
uvx mcp-simple-tool

# Terminal 2: Configure Genesis
cat > genesis_mcp.json <<EOF
[{
  "name": "test-server",
  "transport": "stdio",
  "command": "uvx",
  "args": ["mcp-simple-tool"]
}]
EOF

# Start Genesis
uvicorn app.main:app --reload
```

### Creating Custom MCP Servers

See: https://modelcontextprotocol.io/quickstart/server

### Debugging MCP Integration

Enable debug logging:
```bash
LOG_LEVEL=DEBUG uvicorn app.main:app
```

Check MCP initialization:
```bash
curl http://localhost:8000/api/health
# Look for "MCP client manager initialized" in logs
```
```

---

## Success Criteria

### Phase 1 Complete
- ✅ Application starts with MCP enabled
- ✅ MCPClientManager initializes successfully
- ✅ Graceful handling of missing config

### Phase 2 Complete
- ✅ MCP tools discovered and converted
- ✅ Tools have correct __name__ and __doc__
- ✅ Registry tracks tool sources

### Phase 3 Complete
- ✅ MCP tools bound to LLM provider
- ✅ LLM can select and invoke MCP tools
- ✅ Tool results return correctly

### Phase 4 Complete
- ✅ Frontend displays MCP badge
- ✅ Visual distinction between tool types
- ✅ WebSocket events include source

### Phase 5 Complete
- ✅ 85%+ test coverage
- ✅ All unit tests pass
- ✅ Integration tests with test server pass
- ✅ Manual testing validates UI

### Production Ready
- ✅ Documentation updated
- ✅ Example config provided
- ✅ Error handling robust
- ✅ Logging comprehensive
- ✅ Performance acceptable (<5s startup with 5 servers)

---

## Appendix A: File Checklist

### New Files Created

**Backend Infrastructure:**
- [ ] `backend/app/infrastructure/mcp/__init__.py`
- [ ] `backend/app/infrastructure/mcp/mcp_client_manager.py`

**Backend Tools:**
- [ ] `backend/app/langgraph/tools/mcp_adapter.py`
- [ ] `backend/app/langgraph/tool_metadata.py`

**Configuration:**
- [ ] `backend/genesis_mcp.example.json`
- [ ] Add `genesis_mcp.json` to `.gitignore`

**Tests:**
- [ ] `backend/tests/unit/test_mcp_client_manager.py`
- [ ] `backend/tests/unit/test_mcp_tool_adapter.py`
- [ ] `backend/tests/integration/test_mcp_server_connection.py`
- [ ] `backend/tests/integration/test_mcp_tools_in_conversation.py`
- [ ] `frontend/src/components/chat/__tests__/ToolExecutionCard.test.tsx`

### Files Modified

**Backend:**
- [ ] `backend/app/infrastructure/config/settings.py`
- [ ] `backend/app/main.py`
- [ ] `backend/app/langgraph/nodes/call_llm.py`
- [ ] `backend/app/adapters/inbound/websocket_schemas.py`
- [ ] `backend/app/adapters/inbound/websocket_handler.py`
- [ ] `backend/requirements.txt`

**Frontend:**
- [ ] `frontend/src/contexts/ChatContext.tsx`
- [ ] `frontend/src/services/websocketService.ts`
- [ ] `frontend/src/hooks/useWebSocket.ts`
- [ ] `frontend/src/components/chat/ToolExecutionCard.tsx`

**Documentation:**
- [ ] `doc/general/ARCHITECTURE.md`
- [ ] `doc/general/DEVELOPMENT.md`

---

## Appendix B: MCP Protocol Reference

### Supported Transports

1. **stdio** - Standard input/output communication
   - Use for local process-based MCP servers
   - Example: `uvx mcp-server-sqlite`

2. **streamable-http** - HTTP with SSE streaming
   - Use for remote HTTP-based MCP servers
   - Example: `http://localhost:8000/mcp`

### MCP Tool Schema Format

```json
{
  "name": "tool_name",
  "description": "Tool description",
  "inputSchema": {
    "type": "object",
    "properties": {
      "param1": {"type": "string", "description": "..."},
      "param2": {"type": "integer", "default": 10}
    },
    "required": ["param1"]
  }
}
```

### MCP Server Commands

```bash
# List available MCP tools from Python SDK
uvx mcp list

# Test server connection
uvx mcp inspect <server-config>

# Run specific MCP server
uvx mcp-server-sqlite --db-path ./test.db
uvx mcp-simple-tool
```

---

## Appendix C: Troubleshooting Guide

### Issue: MCP tools not appearing in tool list

**Check**:
1. `MCP_ENABLED=true` in .env
2. `genesis_mcp.json` exists and is valid JSON
3. MCP server is reachable (test with `uvx mcp inspect`)
4. Backend logs show "Registered MCP tool: ..."

**Fix**:
```bash
# Verify config
cat genesis_mcp.json | jq .

# Check logs
tail -f logs/genesis.log | grep MCP
```

### Issue: MCP tool execution fails

**Check**:
1. MCP session is still alive
2. Tool parameters match schema
3. MCP server is responding

**Fix**:
```bash
# Test MCP server directly
uvx mcp inspect genesis_mcp.json

# Check MCP server logs
```

### Issue: Frontend not showing MCP badge

**Check**:
1. WebSocket message includes `source` field
2. ChatContext receives source parameter
3. ToolExecutionCard renders conditionally

**Fix**:
```javascript
// In browser console
console.log(execution.source);  // Should be "mcp" or "local"
```

---

## Next Steps After Implementation

### Potential Enhancements

1. **Dynamic Tool Discovery**
   - Background task to refresh tools periodically
   - Hot-reload without restart

2. **Tool Permissions**
   - Per-user tool authorization
   - Role-based tool access

3. **MCP Tool Marketplace**
   - UI for browsing available MCP servers
   - One-click tool installation

4. **Advanced Namespacing**
   - Custom namespace patterns
   - Tool aliasing

5. **Performance Monitoring**
   - Tool execution metrics
   - MCP server health dashboard

6. **Caching**
   - Cache tool results for identical parameters
   - TTL-based invalidation

---

**Plan Version**: 1.0
**Last Updated**: 2025-10-27
**Author**: AI Analysis + Human Review
**Status**: Ready for Implementation
