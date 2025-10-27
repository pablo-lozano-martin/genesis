# API Contract Analysis: MCP Tool Support

## Request Summary

This analysis examines the WebSocket message protocols and API contracts needed to support exposing MCP (Model Context Protocol) tools to the frontend. The feature requires extending the existing tool execution event system to include tool metadata (name, description, parameters, source) so the frontend can:
1. Display available tools to users
2. Track which tools are MCP tools vs. local tools
3. Handle MCP tool execution events with complete metadata

## Relevant Files & Modules

### WebSocket Message Schemas
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_schemas.py` - WebSocket message type definitions with TOOL_START and TOOL_COMPLETE message schemas
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/services/websocketService.ts` - Frontend WebSocket service with message type handling and event callbacks

### WebSocket Handler & Routing
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py` - WebSocket chat handler that emits TOOL_START and TOOL_COMPLETE events during graph streaming
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/message_router.py` - Message REST API endpoint (retrieves persisted messages from LangGraph)

### Tool Definitions
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/__init__.py` - Tool module exports
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/add.py` - Example local tool
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/multiply.py` - Example local tool
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/web_search.py` - Example local tool
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/rag_search.py` - Example local tool

### LLM & Graph Integration
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/llm_provider.py` - ILLMProvider port interface with bind_tools() method
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/call_llm.py` - Node that binds tools to LLM provider
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/chat_graph.py` - Graph definition with ToolNode and tools_condition

### Frontend Chat Integration
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/contexts/ChatContext.tsx` - Chat state management with tool execution handlers
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/ToolExecutionCard.tsx` - Component displaying executed tools
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/hooks/useWebSocket.ts` - WebSocket hook connecting service to React components

## Current API Contract Overview

### WebSocket Protocol (Client → Server)

**Message Type: `message`**
```typescript
{
  type: "message",
  conversation_id: string,
  content: string
}
```

Sent by the client to submit a user message for LLM processing.

### WebSocket Protocol (Server → Client)

**Message Type: `token`**
```typescript
{
  type: "token",
  content: string
}
```

Streamed during LLM response generation. Contains partial response tokens.

**Message Type: `complete`**
```typescript
{
  type: "complete",
  message_id: string,
  conversation_id: string
}
```

Sent when LLM response completes. Indicates conversation iteration is finished.

**Message Type: `tool_start`**
```typescript
{
  type: "tool_start",
  tool_name: string,
  tool_input: string,           // JSON string
  timestamp: string              // ISO format
}
```

Sent when the LLM decides to call a tool and execution begins. Currently sent by the backend via `websocket_handler.py` lines 169-175.

**Message Type: `tool_complete`**
```typescript
{
  type: "tool_complete",
  tool_name: string,
  tool_result: string,           // String representation
  timestamp: string              // ISO format
}
```

Sent when tool execution finishes. Currently sent by the backend via `websocket_handler.py` lines 177-186.

**Message Type: `error`**
```typescript
{
  type: "error",
  message: string,
  code?: string
}
```

Sent when errors occur during processing.

### Current Tool Execution Flow

**Backend (Streaming):**
1. Graph processes `on_chat_model_end` event (line 161-166)
2. Extracts `tool_calls` from AIMessage if present
3. Caches first tool call in `current_tool_call` variable
4. On `on_tool_start` event (line 169-175):
   - Sends `ServerToolStartMessage` with `tool_name` and `tool_input`
5. On `on_tool_end` event (line 177-186):
   - Sends `ServerToolCompleteMessage` with `tool_name` and `tool_result`

**Frontend (Consumption):**
1. `websocketService.ts` (line 155-157):
   - Calls `onToolStart` callback with `(toolName, toolInput)`
2. `ChatContext.tsx` (line 53-64):
   - Creates `ToolExecution` object with status `"running"`
3. On `TOOL_COMPLETE` (line 159-161):
   - Calls `onToolComplete` callback with `(toolName, toolResult)`
4. `ChatContext.tsx` (line 66-76):
   - Updates execution status to `"completed"` with result
5. `ToolExecutionCard.tsx`:
   - Displays tool name, input (not shown), and result

### Current Schema Definitions

**Backend Pydantic Models** (`websocket_schemas.py`):
```python
class ServerToolStartMessage(BaseModel):
    type: Literal[MessageType.TOOL_START] = MessageType.TOOL_START
    tool_name: str
    tool_input: str              # JSON string
    timestamp: str
```

```python
class ServerToolCompleteMessage(BaseModel):
    type: Literal[MessageType.TOOL_COMPLETE] = MessageType.TOOL_COMPLETE
    tool_name: str
    tool_result: str             # String representation
    timestamp: str
```

**Frontend TypeScript Interfaces** (`websocketService.ts`):
```typescript
export interface ServerToolStartMessage {
  type: typeof MessageType.TOOL_START;
  tool_name: string;
  tool_input: string;
  timestamp: string;
}

export interface ServerToolCompleteMessage {
  type: typeof MessageType.TOOL_COMPLETE;
  tool_name: string;
  tool_result: string;
  timestamp: string;
}
```

## Impact Analysis

### Affected Components

**Backend:**
1. **WebSocket Schemas** - Must add optional `source` field to TOOL_START and TOOL_COMPLETE messages to distinguish MCP vs. local tools
2. **WebSocket Handler** - Must extract tool source metadata when emitting TOOL_START/TOOL_COMPLETE
3. **Tool Registry** - Need mechanism to track tool source (local or MCP) for each tool
4. **LLM Node** - Must maintain metadata about which tools are MCP tools when binding

**Frontend:**
1. **WebSocket Service** - Can parse new `source` field without breaking changes (optional field)
2. **Chat Context** - Should extend `ToolExecution` type to include `source` field
3. **Tool UI Component** - Can display tool source indicator (e.g., "MCP" badge for external tools)

### Breaking Changes

**None if `source` field is optional.** The current websocket protocol can be extended with backward-compatible optional fields:
- Existing clients ignore unknown fields
- New clients can check for `source` field and default to `"local"` if missing
- No REST API changes needed (messages endpoint filters tool messages anyway)

### Data Flow Impact

**Current Flow:**
```
User Input
  ↓
WebSocket message
  ↓
Graph invocation
  ↓
LLM with bound tools [add, multiply, web_search, rag_search]
  ↓
Tool execution
  ↓
TOOL_START/TOOL_COMPLETE events
  ↓
Frontend displays execution
```

**With MCP Support:**
```
User Input
  ↓
WebSocket message
  ↓
Graph invocation
  ↓
LLM with bound tools [local tools + MCP tools]
  ↓
Tool execution
  ↓
TOOL_START/TOOL_COMPLETE events + source metadata
  ↓
Frontend displays execution with source indicator
```

## API Contract Recommendations

### 1. Extend Tool Event Schemas with Source Field

**Backend (`websocket_schemas.py`):**

Add optional `source` field to both message classes:

```python
class ServerToolStartMessage(BaseModel):
    """
    Server message indicating tool execution has started.

    Sent when the LLM decides to call a tool and before the tool executes.
    """
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
    """
    Server message indicating tool execution has completed.

    Sent when the tool finishes execution with results.
    """
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

**Rationale:**
- Optional field maintains backward compatibility
- Clear enum-like values: `"local"` vs `"mcp"`
- Allows frontend to visually distinguish tool origins
- Minimal schema change - only adds one new optional field

**Frontend (`websocketService.ts`):**

Extend TypeScript interfaces with optional source:

```typescript
export interface ServerToolStartMessage {
  type: typeof MessageType.TOOL_START;
  tool_name: string;
  tool_input: string;
  source?: "local" | "mcp";      // New optional field
  timestamp: string;
}

export interface ServerToolCompleteMessage {
  type: typeof MessageType.TOOL_COMPLETE;
  tool_name: string;
  tool_result: string;
  source?: "local" | "mcp";      // New optional field
  timestamp: string;
}
```

### 2. Create Tool Metadata Registry

To track tool sources, create a new registry module that maintains metadata about all available tools:

**New file: `backend/app/langgraph/tool_metadata.py`**

```python
# ABOUTME: Tool metadata registry for tracking tool sources and schemas
# ABOUTME: Enables distinction between local and MCP tools for frontend consumption

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class ToolSource(str, Enum):
    """Enumeration of tool sources."""
    LOCAL = "local"          # Python functions in codebase
    MCP = "mcp"              # Model Context Protocol tools


class ToolParameter(BaseModel):
    """Definition of a tool parameter."""
    name: str
    type: str                # JSON Schema type (string, number, boolean, etc.)
    description: Optional[str] = None
    required: bool = True


class ToolMetadata(BaseModel):
    """Metadata about a tool for frontend discovery and execution."""
    name: str = Field(..., description="Tool name")
    description: Optional[str] = Field(None, description="Tool description")
    source: ToolSource = Field(..., description="Tool source (local or mcp)")
    parameters: List[ToolParameter] = Field(default_factory=list)

    class Config:
        use_enum_values = True


class ToolRegistry:
    """Registry of available tools with metadata."""

    def __init__(self):
        self._tools: Dict[str, ToolMetadata] = {}

    def register_tool(self, tool: ToolMetadata) -> None:
        """Register a tool in the registry."""
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[ToolMetadata]:
        """Get metadata for a specific tool."""
        return self._tools.get(name)

    def get_all_tools(self) -> List[ToolMetadata]:
        """Get metadata for all registered tools."""
        return list(self._tools.values())

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

**Rationale:**
- Provides single source of truth for tool metadata
- Makes it easy for WebSocket handler to determine tool source
- Enables future API endpoint for frontend to discover available tools
- Extensible for future MCP tool properties (e.g., input schema, required scopes)

### 3. Update WebSocket Handler to Include Tool Source

**In `backend/app/adapters/inbound/websocket_handler.py`:**

Modify the tool event emission to include source metadata (around lines 169-186):

```python
from app.langgraph.tool_metadata import get_tool_registry

# ... existing code ...

# Inside handle_websocket_chat function, before the astream_events loop:
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

**Rationale:**
- Minimal change to existing handler
- Enriches tool events with source metadata
- Falls back to `"local"` if tool not in registry (safe default)

### 4. Extend Frontend Tool Execution Tracking

**In `frontend/src/contexts/ChatContext.tsx`:**

Update `ToolExecution` interface to include source:

```typescript
export interface ToolExecution {
  id: string;
  toolName: string;
  toolInput: string;
  toolResult?: string;
  source?: "local" | "mcp";     // New optional field
  status: "running" | "completed";
  startTime: string;
  endTime?: string;
}
```

Update `handleToolStart` to capture source:

```typescript
const handleToolStart = useCallback((toolName: string, toolInput: string, source?: "local" | "mcp") => {
  const execution: ToolExecution = {
    id: `${Date.now()}-${toolName}`,
    toolName,
    toolInput,
    source: source || "local",    // Capture source from event
    status: "running",
    startTime: new Date().toISOString(),
  };
  currentToolExecutionRef.current = execution;
  setCurrentToolExecution(execution);
  setToolExecutions((prev) => [...prev, execution]);
}, []);
```

Update WebSocket hook to pass source to callback:

```typescript
// In websocketService.ts handleMessage:
case MessageType.TOOL_START:
  // Pass source to callback (undefined if not present)
  this.config.onToolStart?.(message.tool_name, message.tool_input, message.source);
  break;

case MessageType.TOOL_COMPLETE:
  this.config.onToolComplete?.(message.tool_name, message.tool_result, message.source);
  break;
```

Update callback signatures in WebSocketConfig:

```typescript
export interface WebSocketConfig {
  // ... existing fields ...
  onToolStart?: (toolName: string, toolInput: string, source?: "local" | "mcp") => void;
  onToolComplete?: (toolName: string, toolResult: string, source?: "local" | "mcp") => void;
}
```

**Rationale:**
- Minimal disruption to existing component structure
- Optional parameters maintain backward compatibility
- Allows frontend to filter/display tools by source

### 5. Add Optional Tool Metadata Discovery Endpoint

**Future capability (not required for initial MCP support):**

Consider adding REST endpoint for frontend to discover available tools:

```
GET /api/tools

Response:
{
  "tools": [
    {
      "name": "add",
      "description": "Simple addition tool",
      "source": "local",
      "parameters": [
        {"name": "a", "type": "integer", "required": true},
        {"name": "b", "type": "integer", "required": true}
      ]
    },
    {
      "name": "web_search",
      "description": "Search the web using DuckDuckGo",
      "source": "local",
      "parameters": [...]
    }
  ]
}
```

This would require:
- New router in `backend/app/adapters/inbound/`
- Serialization of tool registry to response
- Optional authentication (could be public or user-specific)

**This endpoint is NOT required for initial MCP support** but enables future UI features like:
- Tool browser/help panel
- Tool filtering by source
- Parameter validation on frontend before execution

## Implementation Guidance

### Phase 1: Schema Extension (Minimal Change)
1. Add optional `source` field to `ServerToolStartMessage` and `ServerToolCompleteMessage` in `websocket_schemas.py`
2. Update frontend TypeScript interfaces in `websocketService.ts` to match
3. Test backward compatibility (clients without source field handling should still work)

### Phase 2: Tool Registry & Handler Update
1. Create `tool_metadata.py` with registry and metadata models
2. Update `websocket_handler.py` to query registry and include source in events
3. Initialize registry with local tools on startup
4. Write unit tests for registry and handler

### Phase 3: Frontend Integration
1. Update `ToolExecution` interface and callbacks to accept source parameter
2. Update WebSocket hook and service to pass source through chain
3. Update `ChatContext` to track source in state
4. Enhance `ToolExecutionCard` to display source badge (optional UI improvement)

### Phase 4: MCP Tool Registration
1. When MCP tools are loaded, register them with source=`"mcp"` in registry
2. Verify end-to-end flow: MCP tool execution → TOOL_START with source → Frontend display

## Testing Strategy

### Backend Testing

**Unit Tests for Tool Metadata:**
```python
# tests/unit/test_tool_metadata.py

def test_register_tool():
    registry = ToolRegistry()
    tool = ToolMetadata(
        name="test_tool",
        description="Test tool",
        source=ToolSource.LOCAL
    )
    registry.register_tool(tool)
    assert registry.get_tool("test_tool") == tool

def test_get_all_tools():
    registry = ToolRegistry()
    # Register multiple tools
    assert len(registry.get_all_tools()) == expected_count

def test_get_tool_source():
    registry = ToolRegistry()
    # Register tool
    source = registry.get_tool_source("test_tool")
    assert source == ToolSource.LOCAL
```

**Integration Tests for WebSocket Events:**
```python
# tests/integration/test_websocket_tool_events.py

@pytest.mark.asyncio
async def test_tool_start_includes_source():
    # Start WebSocket
    # Trigger tool execution
    # Assert TOOL_START message includes source field
    assert message.get("source") in ["local", "mcp"]

@pytest.mark.asyncio
async def test_tool_complete_includes_source():
    # Similar test for TOOL_COMPLETE
    pass

@pytest.mark.asyncio
async def test_backward_compatibility():
    # Verify messages work without source field
    # (for pre-MCP clients)
    pass
```

### Frontend Testing

**TypeScript Type Checking:**
```typescript
// Test source field is optional
const msg: ServerToolStartMessage = {
  type: MessageType.TOOL_START,
  tool_name: "test",
  tool_input: "{}",
  timestamp: new Date().toISOString()
  // source is optional - should compile
};

const msgWithSource: ServerToolStartMessage = {
  ...msg,
  source: "mcp"
};
```

**React Component Tests:**
```typescript
// Test ToolExecution with and without source
const execution: ToolExecution = {
  id: "1",
  toolName: "test",
  toolInput: "{}",
  status: "completed",
  startTime: new Date().toISOString()
  // source is optional
};

// Test ToolExecutionCard renders with source
render(<ToolExecutionCard execution={{...execution, source: "mcp"}} />);
// Should show MCP badge or indicator
```

### End-to-End Testing

1. **Local tool execution** (without source field):
   - Send message → Tool executes → Frontend displays without source

2. **MCP tool execution** (with source field):
   - Send message → Tool executes → Frontend displays with "MCP" indicator

3. **Mixed tool execution**:
   - LLM calls both local and MCP tools → Both events received with correct source

## Risks and Considerations

### Risk 1: Backward Compatibility with Older Clients
**Issue:** Clients not expecting optional `source` field might fail JSON parsing
**Mitigation:** Make `source` truly optional in schema and provide default value
**Impact:** Low - JSON parsing is lenient with extra/missing optional fields

### Risk 2: Tool Registry Initialization Timing
**Issue:** MCP tools might be registered after graph is already invoked
**Mitigation:** Load MCP tools on startup before first graph invocation
**Impact:** Medium - Requires coordination between startup sequence and tool loading

### Risk 3: Tool Name Collisions
**Issue:** Local tool and MCP tool could have same name
**Mitigation:** Namespace MCP tools (e.g., `mcp:namespace:tool_name`) or require unique names
**Impact:** Medium - Design decision needed for MCP tool naming convention

### Risk 4: Missing Tool Metadata
**Issue:** Tool executes but not found in registry (e.g., dynamically loaded tools)
**Mitigation:** Default to `source="local"` if tool not in registry
**Impact:** Low - Graceful fallback, worst case shows wrong source

### Risk 5: Schema Changes to Existing Messages
**Issue:** Adding fields changes API contract
**Mitigation:** Make `source` optional with default value, not required
**Impact:** Low - Backward compatible change

## Assumptions

1. **Tool names are globally unique** across local and MCP tools (or will be namespaced)
2. **Tool registry is initialized before graph invocation** occurs
3. **Frontend can handle optional fields** in WebSocket messages (standard JSON parsing)
4. **MCP tool loading** follows same pattern as local tool binding (list of callables)
5. **Tool source is static** (doesn't change during conversation)

## Questions for Clarification

1. **Tool Naming Convention for MCP:** Should MCP tools be namespaced (e.g., `mcp:provider:tool`) or have unique names?
2. **MCP Tool Discovery:** Should frontend have API endpoint to query available tools, or just track via events?
3. **Tool Availability:** Should all MCP tools always be available, or only some based on user/conversation?
4. **Parameter Validation:** Should MCP tool parameter schemas be exposed to frontend for UI-level validation?
5. **Tool Authorization:** Do MCP tools need per-user authorization/scoping, or system-level availability?

## Summary

The API contract changes needed for MCP support are **minimal and backward-compatible:**

- **Single optional field** (`source`) added to existing TOOL_START and TOOL_COMPLETE messages
- **New tool registry** module to track tool sources (local vs. MCP)
- **Minor handler updates** to query registry and include source in events
- **Frontend extensions** to track and optionally display source

This approach allows:
- Gradual MCP tool integration without breaking existing clients
- Clear distinction between tool sources for UI/tracking purposes
- Future extensibility for tool discovery and metadata querying
- Clean separation of concerns using registry pattern

The implementation is straightforward because MCP tool execution flows through the same LangGraph paths as local tools once converted to Python callables via the MCP-to-Python adapter layer.
