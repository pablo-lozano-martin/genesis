# Data Flow Analysis: MCP Tool Execution in Genesis

## Request Summary

This analysis examines the complete data flow for MCP (Model Context Protocol) tool execution in Genesis, focusing on how tool metadata, invocations, and results flow through the WebSocket → LangGraph → LLM → ToolNode → WebSocket pipeline. The analysis covers event streaming, checkpoint persistence, tool namespacing, and optimal MCP tool discovery injection points.

## Relevant Files & Modules

### Files to Examine

**Core Architecture & State**
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/state.py` - ConversationState extending MessagesState
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/streaming_chat_graph.py` - Main graph with ToolNode and tools_condition
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/database/langgraph_checkpointer.py` - MongoDB checkpoint storage and serialization

**WebSocket & Event Streaming**
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py` - WebSocket event streaming with TOOL_START/TOOL_COMPLETE messages
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_schemas.py` - Event message types including ServerToolStartMessage and ServerToolCompleteMessage

**LLM Integration & Tool Binding**
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/call_llm.py` - LLM invocation node with tool binding
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/llm_provider.py` - ILLMProvider interface with bind_tools() contract
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/anthropic_provider.py` - Anthropic provider bind_tools implementation (reference for pattern)

**Tool Layer**
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/` - Tool definitions (add.py, multiply.py, web_search.py, rag_search.py)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/__init__.py` - Tool exports

**Supporting Infrastructure**
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/config/settings.py` - Configuration management
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/config/logging_config.py` - Centralized logging
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/process_input.py` - Input validation node

### Key Functions & Classes

**State & Persistence**
- `ConversationState` - Extends MessagesState with conversation_id and user_id
- `AsyncMongoDBSaver` - LangGraph checkpointer for state persistence with serialization
- `RunnableConfig` - Configuration object passed through graph invocation with configurable dict

**Graph Nodes**
- `process_user_input()` - Validates messages in state, creates HumanMessage
- `call_llm()` - Invokes provider with tools bound, returns AIMessage with tool_calls
- `ToolNode` - Executes tools and generates ToolMessages (LangGraph prebuilt)

**Message Types (LangChain)**
- `HumanMessage` - User input message
- `AIMessage` - LLM response with optional tool_calls list
- `ToolMessage` - Tool execution result with tool_call_id reference
- `BaseMessage` - Abstract base for all message types

**Event Stream Handlers**
- `ServerTokenMessage` - LLM token streamed to client
- `ServerToolStartMessage` - Tool execution starting (with tool_name and tool_input)
- `ServerToolCompleteMessage` - Tool execution completed (with tool_name and tool_result)

**LLM Provider Interface**
- `ILLMProvider.bind_tools()` - Binds callables to provider, returns new provider instance
- `ILLMProvider.generate()` - Generates single response from messages

## Current Data Flow Overview

### Conceptual Architecture

```
User (WebSocket Client)
        ↓
WebSocket Handler
├─ Receives ClientMessage
├─ Creates RunnableConfig with thread_id
├─ Invokes graph.astream_events()
└─ Streams ServerMessages back to client
        ↓
LangGraph Streaming Graph
├─ process_input node (validation)
├─ call_llm node (LLM invocation with tools bound)
├─ tools_condition (decides if tool calls needed)
├─ tools node (ToolNode executes tool callables)
└─ Checkpointer (persists state to MongoDB)
        ↓
LLM Provider (via ILLMProvider interface)
├─ bind_tools() binds Python callables
├─ generate() invokes LLM with messages and tool definitions
└─ Returns AIMessage with tool_calls if LLM decides to use tools
        ↓
Tool Execution
├─ ToolNode invokes callable with LLM-determined parameters
├─ Tool returns result as string/serializable
└─ ToolMessage created and added to messages
```

### Data Entry Points

**1. WebSocket Message (Client → Server)**
```
ClientMessage
├─ type: MessageType.MESSAGE
├─ conversation_id: str (verified against App DB)
├─ content: str (user message)
↓
Transformed to:
HumanMessage(content=client_message.content)
```

**Data Flow:**
- Client sends JSON ClientMessage via WebSocket
- Handler validates conversation ownership in App DB (authorization boundary)
- Creates RunnableConfig with thread_id=conversation.id and llm_provider
- Passes HumanMessage in input_data["messages"] to graph
- Message added to ConversationState.messages via MessagesState reducer

**2. Graph Invocation Configuration**
```
RunnableConfig
├─ configurable:
│  ├─ thread_id: str (conversation.id)
│  ├─ llm_provider: ILLMProvider (selected by factory)
│  └─ user_id: str
```

**Critical Role:** thread_id maps conversation to LangGraph checkpoint storage. All state mutations are persisted to this thread's checkpoint.

### Transformation Layers

**Layer 1: WebSocket Input → ConversationState**
```
ClientMessage (JSON)
    ↓ (websocket_handler.py)
HumanMessage(content)
    ↓ (added to input_data)
ConversationState.messages: [HumanMessage]
```

**Responsibility:** The handler is responsible for:
- Parsing JSON and validating ClientMessage schema
- Creating HumanMessage with user's text content
- Including conversation_id and user_id in state
- Creating RunnableConfig with proper thread_id mapping

**Layer 2: ConversationState → call_llm Node**
```
ConversationState
├─ messages: [HumanMessage] (from MessagesState)
├─ conversation_id: str
└─ user_id: str
    ↓ (call_llm.py)
Loads from state:
├─ messages (full history)
├─ Retrieves llm_provider from RunnableConfig
├─ Gets tools list [multiply, add, web_search, rag_search, ...]
    ↓
Calls llm_provider.bind_tools(tools, parallel_tool_calls=False)
    ↓
Invokes llm_provider_with_tools.generate(messages)
    ↓
Returns AIMessage with:
├─ content: str (text response)
└─ tool_calls: List[ToolCall] (if LLM decided to use tools)
```

**Responsibility:**
- Tool binding occurs here (critical data flow point)
- Tools are Python callables with type hints and docstrings
- LangChain's bind_tools() introspects callables to create tool schemas
- Provider delegates to LangChain for schema creation and formatting

**Layer 3: AIMessage with tool_calls → ToolNode**
```
AIMessage (with tool_calls)
├─ tool_calls: [
│  {
│    "id": str,
│    "name": str (tool name),
│    "args": Dict[str, Any] (LLM-determined parameters)
│  }
│]
    ↓ (tools_condition edge decides: tool_calls present?)
    ↓ YES → routes to tools node
ToolNode execution:
├─ For each tool_call in AIMessage.tool_calls:
│  ├─ Looks up tool callable by name
│  ├─ Invokes with args: callable(**tool_call.args)
│  └─ Creates ToolMessage(tool_call_id, result)
    ↓
Returns Dict[messages]: [ToolMessage, ...]
```

**Responsibility:**
- ToolNode is LangGraph prebuilt, expects tools list at graph compile time
- Tools list must be in same order and with same callables as bound to provider
- Tool name matching is critical - tool_call.name must match callable.__name__
- ToolMessage references tool_call_id for traceability in conversation history

**Layer 4: Messages → Checkpoint Serialization**
```
ConversationState.messages: List[BaseMessage]
├─ HumanMessage
├─ AIMessage (with tool_calls)
├─ ToolMessage (from ToolNode execution)
└─ [more messages in history...]
    ↓ (langgraph_checkpointer.py)
Checkpoint Write Cycle:
├─ AsyncMongoDBSaver.put() called by LangGraph
├─ Serializes BaseMessage objects to JSON
├─ Schema: stored in langgraph_checkpoints collection
├─ Index: thread_id = conversation.id
└─ Result: Entire conversation history persisted atomically
```

**Critical Detail:**
- ToolMessage is automatically serialized with tool_call_id and content
- No special handling needed - LangGraph handles BaseMessage serialization
- Checkpoints are thread-based: one checkpoint per conversation
- Each graph invocation creates new checkpoint row with incremented version

### Persistence Layer

**MongoDB Structure (LangGraph DB)**
```
langgraph_checkpoints collection:
{
  "thread_id": "conversation-uuid",
  "checkpoint_id": "checkpoint-uuid",
  "checkpoint_ns": "default",
  "parent_checkpoint_id": "prev-checkpoint-uuid",
  "timestamp": ISO8601,
  "channel_values": {
    "messages": [
      {
        "type": "human",
        "content": "user message",
        "id": "..."
      },
      {
        "type": "ai",
        "content": "response text",
        "tool_calls": [
          {
            "id": "call_xyz",
            "name": "search_web",
            "args": {"query": "..."}
          }
        ]
      },
      {
        "type": "tool",
        "content": "search results...",
        "tool_call_id": "call_xyz",
        "name": "search_web"
      }
    ]
  },
  "metadata": {
    "step_index": 2,
    "source": "loop",
    "writes": {"messages": [...]}
  }
}
```

**Data Persistence Properties:**
- Thread-scoped: Isolation per conversation
- Versioned: Each invocation creates new checkpoint
- Atomic: All state changes in single write
- Traceable: parent_checkpoint_id links to previous state
- Complete: Full message history preserved including tool metadata

### Data Exit Points

**1. WebSocket Event Streaming (Server → Client)**

Event stream is consumed via `graph.astream_events()` in websocket_handler.py:

```
on_chat_model_stream:
├─ event["data"]["chunk"]: ChatModelStreamChunk
└─ chunk.content: str (LLM token)
    ↓
Transformed to:
ServerTokenMessage(content=chunk.content)
    ↓
Streamed to client via WebSocket
```

**Event Properties:**
- Fires multiple times during LLM generation (one per token)
- Contains partial content for streaming UI updates
- No tool information at this stage

```
on_chat_model_end:
├─ event["data"]["output"]: AIMessage
├─ output.tool_calls: [ToolCall, ...] (cached for TOOL_START event)
└─ Stored in current_tool_call variable
    ↓
This event does NOT generate ServerMessage
(Used to capture tool metadata for subsequent tool events)
```

**Critical Role:** This event is WHERE TOOL METADATA ENTERS THE FLOW:
- AIMessage.tool_calls contains all tool information
- Name, args, id are extracted here
- Cached for use in on_tool_start and on_tool_end events

```
on_tool_start:
├─ current_tool_call: captured from on_chat_model_end
├─ Extracts: name and args
    ↓
Transformed to:
ServerToolStartMessage(
  tool_name=current_tool_call["name"],
  tool_input=json.dumps(current_tool_call["args"]),
  timestamp=datetime.utcnow().isoformat()
)
    ↓
Streamed to client via WebSocket
```

**Client receives:**
- Tool name for UI display (e.g., "Searching web...")
- Input parameters in JSON format
- Timestamp for progress indication
- Client shows loading badge with tool name

```
on_tool_end:
├─ event["data"]["output"]: str (tool execution result)
├─ current_tool_call: still cached from on_chat_model_end
    ↓
Transformed to:
ServerToolCompleteMessage(
  tool_name=current_tool_call["name"],
  tool_result=str(tool_result),
  timestamp=datetime.utcnow().isoformat()
)
    ↓
Streamed to client via WebSocket
```

**Client receives:**
- Tool execution result as string
- Tool name for matching with TOOL_START
- Completion timestamp
- Client updates UI to show results, marks as completed

**Data Flow Diagram:**
```
User sends message
    ↓
WebSocket Handler
├─ Receives ClientMessage
├─ Creates RunnableConfig(thread_id, llm_provider)
├─ Invokes graph.astream_events()
│
├─→ on_chat_model_stream event
│   ├─ Token: "The" → ServerTokenMessage → Client
│   ├─ Token: " " → ServerTokenMessage → Client
│   ├─ Token: "results" → ServerTokenMessage → Client
│   └─ (Streamed to UI for display)
│
├─→ on_chat_model_end event
│   ├─ AIMessage with tool_calls
│   └─ Cache tool_call metadata (name, args, id)
│
├─→ on_tool_start event
│   ├─ Use cached tool_call name and args
│   └─ ServerToolStartMessage → Client (shows "Tool running...")
│
├─→ ToolNode executes
│   ├─ Invokes callable with LLM args
│   ├─ Gets result string
│   └─ Creates ToolMessage
│
├─→ on_tool_end event
│   ├─ Use cached tool_call name
│   └─ ServerToolCompleteMessage → Client (shows results)
│
├─→ on_chat_model_stream event (LLM final response)
│   ├─ Streams final response tokens
│   └─ ServerTokenMessage → Client
│
└─→ Checkpointing
    ├─ AsyncMongoDBSaver.put()
    ├─ Serializes all messages including ToolMessage
    └─ Persists to langgraph_checkpoints
```

## Impact Analysis: MCP Tool Integration

### Components Affected by MCP Addition

#### 1. Tool Definition Layer (backend/app/langgraph/tools/)

**Current State:**
- Simple Python functions with type hints and docstrings
- Examples: `add(a: int, b: int) -> int`, `rag_search(query: str) -> str`
- Directly imported and used in lists

**MCP Impact:**
- Native Python tools remain unchanged
- MCP tools need adapter wrapper layer
- Adapter must be Python-callable for LangChain compatibility
- Adapter must have `__name__`, `__doc__`, and type hints

**Data Flow Change:**
```
Python Tools (existing):
└─ Python function → LangChain bind_tools() → Provider schema

MCP Tools (new):
└─ MCP Tool Definition (JSON schema)
   → MCPToolAdapter (Python callable wrapper)
   → LangChain bind_tools() → Provider schema
```

**Key Transformation Points:**
- MCP schema extraction: input_schema → type hints
- Name preservation: mcp_tool.name → adapter.__name__
- Description preservation: mcp_tool.description → adapter.__doc__
- Parameter mapping: JSON schema properties → async function signature

#### 2. Tool Binding in call_llm Node

**Current Implementation (line 37-41 in call_llm.py):**
```python
tools = [multiply, add, web_search, rag_search]
llm_provider_with_tools = llm_provider.bind_tools(tools, parallel_tool_calls=False)
ai_message = await llm_provider_with_tools.generate(messages)
```

**MCP Integration Point:**
```python
# Load Python tools
python_tools = [multiply, add, web_search, rag_search]

# Load MCP tools from registry (NEW)
mcp_registry = config["configurable"].get("mcp_registry")  # From RunnableConfig
mcp_tools = []
if mcp_registry:
    mcp_tools = await mcp_registry.get_tools()  # Returns MCPToolAdapter instances

# Combine tools
all_tools = python_tools + mcp_tools

# Bind all tools transparently
llm_provider_with_tools = llm_provider.bind_tools(all_tools, parallel_tool_calls=False)
ai_message = await llm_provider_with_tools.generate(messages)
```

**Data Flow Implication:**
- Tool binding now asynchronous (MCP tool discovery is I/O)
- call_llm node needs to be async (already is)
- RunnableConfig must include mcp_registry reference
- Tools list is dynamic, determined per invocation or cached

**Critical Design Decision:**
- Should MCP tools be discovered once at graph creation or per invocation?
- **Recommendation:** Discover at call_llm node invocation time for:
  - Latest tool definitions from MCP servers
  - Graceful handling of server unavailability
  - Per-conversation tool availability control

#### 3. ToolNode Execution

**Current Behavior:**
- Receives ToolNode(tools) list at graph compile time
- All tools pre-bound in graph definition
- Lookup by name at tool execution time

**MCP Challenge:**
- MCP tools are not known at graph compile time
- Tool names are dynamic and namespaced
- Need runtime tool discovery mechanism

**Two Solutions:**

**Option A: Static Registration (Simpler)**
```
Graph compile time:
ToolNode([multiply, add, web_search, rag_search, mcp_search, mcp_lookup])

All tools registered in graph, including MCP adapters
Requires knowing MCP tools before graph creation
Tool count fixed per deployment
```

**Option B: Dynamic Tool Loading (More Flexible)**
```
Graph compile time:
ToolNode with custom executor that:
├─ Receives tool_call with name
├─ Looks up name in dynamic registry
└─ Executes found callable

Allows MCP tools to be discovered at runtime
Tools can be added without redeploying graph
Requires registry passed in RunnableConfig
```

**Recommendation:** Start with Option A (static), migrate to Option B if needed for:
- Hot-reloading of tools
- Per-conversation tool availability
- Multi-tenant tool isolation

#### 4. RunnableConfig Extended

**Current Usage (websocket_handler.py, lines 123-129):**
```python
config = RunnableConfig(
    configurable={
        "thread_id": conversation.id,
        "llm_provider": llm_provider,
        "user_id": user.id
    }
)
```

**MCP Extension:**
```python
config = RunnableConfig(
    configurable={
        "thread_id": conversation.id,
        "llm_provider": llm_provider,
        "user_id": user.id,
        "mcp_registry": mcp_registry,  # NEW
        "mcp_enabled": True  # NEW
    }
)
```

**Data Flow Impact:**
- Configuration object carries MCP context through entire graph execution
- call_llm node accesses mcp_registry from config
- Tool discovery happens within node execution (has access to config)
- Checkpointing unaffected (config not persisted, only state)

#### 5. Message Serialization in Checkpoints

**Current: Tool messages are persisted automatically**
```json
{
  "type": "tool",
  "content": "search result text...",
  "tool_call_id": "call_abc123",
  "name": "web_search"
}
```

**MCP Impact: No changes needed**
- ToolMessage serialization is unchanged
- tool_call_id still references AIMessage.tool_calls[n].id
- Tool name is preserved as-is
- Tool result is string (same as Python tools)

**Namespacing Consideration:**
If MCP tools are namespaced (e.g., "mcp:search:web"), the name field will preserve this:
```json
{
  "tool_call_id": "call_xyz",
  "name": "mcp:search:web",  # Namespaced name preserved
  "content": "..."
}
```

**No serialization changes required** - JSON schema supports any string for name.

#### 6. WebSocket Event Streaming

**Current Flow:**
```
on_tool_start:
├─ current_tool_call["name"]: "web_search"
└─ ServerToolStartMessage(tool_name="web_search", ...)

on_tool_end:
├─ current_tool_call["name"]: "web_search"
└─ ServerToolCompleteMessage(tool_name="web_search", ...)
```

**MCP Extension:**
```
on_tool_start:
├─ current_tool_call["name"]: "mcp:search:web" (namespaced)
└─ ServerToolStartMessage(tool_name="mcp:search:web", ...)

on_tool_end:
├─ current_tool_call["name"]: "mcp:search:web"
└─ ServerToolCompleteMessage(tool_name="mcp:search:web", ...)
```

**Key Data Flow Point:**
- Tool names flow directly from AIMessage.tool_calls to WebSocket events
- If MCP tools use namespacing, names automatically propagate
- Client receives full tool name for proper routing
- No transformation needed in event streaming

## Data Flow Recommendations

### Proposed MCP Architecture

**1. MCP Tool Adapter DTOs**

Location: `backend/app/langgraph/tools/mcp_adapter.py`

Purpose: Bridge MCP tool definitions to Python-callable wrappers

```python
# DTO for incoming MCP tool definition
class MCPToolDefinition(BaseModel):
    """Data transfer object for MCP tool schema from server."""
    name: str  # Tool name from MCP server
    description: str  # Tool description
    input_schema: Dict[str, Any]  # JSON Schema of input parameters
    output_schema: Optional[Dict[str, Any]] = None

# Adapter wrapper making MCP tool callable
class MCPToolAdapter:
    """Transforms MCP schema to Python callable for LangChain binding."""

    def __init__(
        self,
        definition: MCPToolDefinition,
        mcp_client: 'MCPClient',
        namespace: str = ""
    ):
        self.definition = definition
        self.mcp_client = mcp_client
        self.namespace = namespace
        self._build_signature()

    async def __call__(self, **kwargs) -> str:
        """Execute MCP tool via HTTP, return result as string."""
        # Validate parameters against schema
        # Call MCP server with parameters
        # Serialize result to string for ToolMessage

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
        """Extract Python signature from MCP input_schema for type hints."""
        # Convert JSON Schema to Python function signature
        # Store as callable signature for LangChain introspection
```

**Data Flow:**
```
MCP Server Response (JSON)
    ↓
MCPToolDefinition (DTO)
    ↓
MCPToolAdapter (Python callable)
    ↓
Type hint extraction
    ↓
LangChain bind_tools() introspection
    ↓
Provider-specific schema generation
```

**2. MCP Client Integration Layer**

Location: `backend/app/infrastructure/mcp/`

Structure:
```
infrastructure/mcp/
├── __init__.py
├── mcp_client.py          # Async HTTP client
├── mcp_config.py          # Configuration DTOs
├── mcp_tool_registry.py   # Discovery and caching
└── mcp_errors.py          # Error mapping
```

**MCP Client Data Flow:**
```
MCPClient
├─ Async HTTP POST to MCP server endpoint
├─ JSON-RPC request/response
├─ Timeout handling with configurable timeout
└─ Returns raw JSON response

↓

MCPToolRegistry
├─ Calls MCPClient.discover_tools()
├─ Caches MCPToolDefinition objects
├─ Creates MCPToolAdapter instances
└─ Maintains in-memory registry
```

**3. Configuration Extension**

Location: `backend/app/infrastructure/config/settings.py`

```python
class MCPServerConfig(BaseModel):
    """Configuration for a single MCP server."""
    name: str
    url: str
    auth_token: Optional[str] = None
    timeout: int = 30
    enabled: bool = True
    namespace: str = ""  # Tool namespace for multi-server scenarios

class MCPSettings(BaseModel):
    """MCP-specific configuration."""
    mcp_enabled: bool = False
    mcp_servers: List[MCPServerConfig] = []
    mcp_discovery_cache_ttl: int = 3600  # Seconds
    mcp_tool_execution_timeout: int = 30  # Per-tool timeout

# In main Settings class
class Settings(BaseSettings):
    # ... existing settings ...
    mcp: MCPSettings = MCPSettings()
```

**Environment Variables:**
```bash
MCP_ENABLED=true
MCP_SERVERS='[{"name":"knowledge","url":"http://localhost:3000","namespace":"kb"}]'
MCP_DISCOVERY_CACHE_TTL=3600
MCP_TOOL_EXECUTION_TIMEOUT=30
```

**Data Flow:**
```
Environment Variables / .env
    ↓ (BaseSettings parsing)
Settings.mcp: MCPSettings
    ↓ (contains)
List[MCPServerConfig]
    ↓ (used by)
MCPToolRegistry initialization
    ↓ (discovers tools and)
Creates MCPToolAdapter instances
```

### Tool Registration and Discovery

**Recommended Approach: Static Registration with Caching**

**At Application Startup:**
```
1. FastAPI app.on_event("startup")
   ├─ Read MCP_SERVERS from settings
   ├─ Create MCPToolRegistry with server configs
   ├─ Discover tools from each server
   ├─ Cache MCPToolDefinition objects
   ├─ Create MCPToolAdapter instances
   └─ Store registry in app.state (for access in graph)

2. Store registry in app.state:
   app.state.mcp_registry = mcp_registry
```

**In WebSocket Handler:**
```
config = RunnableConfig(
    configurable={
        "thread_id": conversation.id,
        "llm_provider": llm_provider,
        "user_id": user.id,
        "mcp_registry": app.state.mcp_registry  # Pass to graph
    }
)
```

**In call_llm Node:**
```
async def call_llm(state: ConversationState, config: RunnableConfig):
    mcp_registry = config["configurable"].get("mcp_registry")

    # Build tool list
    python_tools = [multiply, add, web_search, rag_search]
    mcp_tools = []

    if mcp_registry:
        try:
            mcp_tools = mcp_registry.get_tools()  # Returns MCPToolAdapter instances
        except Exception as e:
            logger.warning(f"MCP tool discovery failed: {e}")

    all_tools = python_tools + mcp_tools
    llm_provider_with_tools = llm_provider.bind_tools(all_tools, parallel_tool_calls=False)
    ai_message = await llm_provider_with_tools.generate(messages)

    return {"messages": [ai_message]}
```

**Data Flow Diagram:**
```
App Startup
    ↓
MCPToolRegistry initialized
├─ Loads MCPServerConfig list
├─ Connects to MCP servers
├─ Discovers tools: MCPToolDefinition objects
├─ Creates adapters: MCPToolAdapter instances
└─ Caches in registry
    ↓
Request → WebSocket Handler
    ↓
RunnableConfig includes mcp_registry
    ↓
call_llm node
├─ Retrieves mcp_registry from config
├─ Calls mcp_registry.get_tools()
├─ Gets MCPToolAdapter instances
├─ Combines with Python tools
└─ Binds all to provider
    ↓
Provider schema generation
    ↓
LLM receives tool definitions
    ↓
LLM can invoke any tool (Python or MCP)
```

### Tool Namespacing Strategy

**Problem:** Multiple MCP servers may have tools with same name (e.g., "search")

**Solution: Automatic Namespacing**

```python
class MCPToolRegistry:
    def __init__(self, servers: List[MCPServerConfig]):
        self.servers = servers
        self.adapters: Dict[str, MCPToolAdapter] = {}

    async def discover_tools(self):
        """Discover tools from all MCP servers with namespacing."""
        for server in self.servers:
            tools = await server.client.discover_tools()
            for tool in tools:
                # Use server namespace if provided, else server name
                namespace = server.namespace or server.name
                adapter = MCPToolAdapter(tool, server.client, namespace=namespace)

                # Full name: "namespace:tool_name"
                full_name = adapter.__name__  # e.g., "kb:search"
                self.adapters[full_name] = adapter
```

**Data Flow with Namespacing:**
```
MCP Server Config:
├─ name: "knowledge"
├─ namespace: "kb"
└─ url: "http://localhost:3000"
    ↓
Discovered Tool:
├─ name: "search"
└─ description: "Search knowledge base"
    ↓
MCPToolAdapter:
├─ __name__ = "kb:search"  (namespaced)
├─ __doc__ = "Search knowledge base"
└─ __call__ → HTTP to MCP server
    ↓
LangChain bind_tools():
├─ Extracts tool name: "kb:search"
├─ Generates provider schema with full name
└─ LLM receives: {"name": "kb:search", "description": "...", ...}
    ↓
AIMessage.tool_calls:
├─ [{"id": "call_xyz", "name": "kb:search", "args": {...}}]
    ↓
ToolNode lookup:
├─ Searches adapters["kb:search"]
├─ Executes MCPToolAdapter
└─ Creates ToolMessage with name="kb:search"
    ↓
WebSocket Event:
├─ ServerToolStartMessage(tool_name="kb:search")
├─ ServerToolCompleteMessage(tool_name="kb:search")
```

**Client-Side Implications:**
- Client receives full namespaced tool names
- Can display as "KB: Search" or "kb:search" in UI
- Tool identification is unambiguous across servers

### Where to Inject MCP Tool Discovery

**Injection Points (in order of execution):**

**1. Application Startup (OPTIMAL for static discovery)**
```
Location: main.py app.on_event("startup")
Timing: Once at application start
Data Flow: Settings → MCPToolRegistry → app.state
Benefits:
├─ Tools available immediately
├─ Single discovery pass
├─ Efficient (no per-request overhead)
└─ Fails fast if MCP servers unreachable
```

**Recommended Implementation:**
```python
# In main.py or startup.py
@app.on_event("startup")
async def startup_event():
    # ... existing startup code ...

    if settings.mcp.mcp_enabled:
        logger.info("Initializing MCP tool registry")
        try:
            mcp_registry = MCPToolRegistry(settings.mcp.mcp_servers)
            await mcp_registry.discover_tools()
            app.state.mcp_registry = mcp_registry
            logger.info(f"Loaded {len(mcp_registry.adapters)} MCP tools")
        except Exception as e:
            logger.error(f"MCP initialization failed: {e}")
            app.state.mcp_registry = None
```

**2. WebSocket Handler (for per-connection context)**
```
Location: websocket_handler.py handle_websocket_chat()
Timing: Per WebSocket connection
Data Flow: app.state.mcp_registry → RunnableConfig
Benefits:
├─ Can pass to graph invocation
├─ Available in all nodes
└─ Enables per-connection tool filtering (if needed)
```

**Recommended Implementation:**
```python
# In websocket_handler.py
async def handle_websocket_chat(...):
    # ... existing code ...

    config = RunnableConfig(
        configurable={
            "thread_id": conversation.id,
            "llm_provider": llm_provider,
            "user_id": user.id,
            "mcp_registry": manager.app.state.get("mcp_registry")  # Pass registry
        }
    )
```

**3. call_llm Node (for per-invocation tool loading)**
```
Location: langgraph/nodes/call_llm.py
Timing: Per LLM invocation
Data Flow: RunnableConfig → call_llm node → tool binding
Benefits:
├─ Can handle dynamic tool discovery
├─ Can filter tools per conversation/user
├─ Graceful error handling per invocation
└─ Latest tool definitions used
```

**Recommended Implementation:**
```python
# In call_llm.py
async def call_llm(state: ConversationState, config: RunnableConfig) -> dict:
    messages = state["messages"]
    conversation_id = state["conversation_id"]

    # Get Python tools
    python_tools = [multiply, add, web_search, rag_search]

    # Get MCP tools from registry
    mcp_registry = config["configurable"].get("mcp_registry")
    mcp_tools = []
    if mcp_registry:
        try:
            mcp_tools = mcp_registry.get_tools()
            logger.info(f"Using {len(mcp_tools)} MCP tools")
        except Exception as e:
            logger.warning(f"MCP tools unavailable: {e}")

    # Combine and bind
    all_tools = python_tools + mcp_tools
    llm_provider = config["configurable"]["llm_provider"]
    llm_provider_with_tools = llm_provider.bind_tools(all_tools, parallel_tool_calls=False)
    ai_message = await llm_provider_with_tools.generate(messages)

    return {"messages": [ai_message]}
```

**4. Graph Compilation (for static tool binding - REQUIRES changes)**
```
Location: langgraph/graphs/streaming_chat_graph.py
Timing: Once at application startup
Data Flow: Tool list → graph nodes
Drawback:
├─ Requires knowing tools before graph creation
├─ MCP tools must be discovered before compiling graph
└─ No runtime tool discovery possible
```

**NOT RECOMMENDED** - Use application startup injection (Option 1) instead.

### Data Transformation: MCP Schema → Python Callable

**Input: MCP Tool Definition**
```json
{
  "name": "search_knowledge_base",
  "description": "Search the company knowledge base",
  "input_schema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Search query"
      },
      "limit": {
        "type": "integer",
        "description": "Max results",
        "default": 10
      },
      "filters": {
        "type": "object",
        "description": "Search filters",
        "properties": {
          "category": {"type": "string"},
          "date_range": {"type": "string"}
        }
      }
    },
    "required": ["query"]
  }
}
```

**Transformation Process:**

**Step 1: Extract Parameters**
```
Query the input_schema.properties:
├─ query: string (required) → str (no default)
├─ limit: integer (optional) → int (default=10)
└─ filters: object (optional) → Dict[str, Any] (default=None)
```

**Step 2: Generate Type Hints**
```python
# JSON Schema type → Python type mapping
SCHEMA_TYPE_MAP = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "array": List,
    "object": Dict
}
```

**Step 3: Build Function Signature**
```python
async def search_knowledge_base(
    query: str,
    limit: int = 10,
    filters: Optional[Dict[str, Any]] = None
) -> str:
    """Search the company knowledge base."""
    pass
```

**Step 4: Create Adapter Instance**
```python
adapter = MCPToolAdapter(
    definition=mcp_tool_definition,
    mcp_client=mcp_client,
    namespace="kb"
)

# Adapter properties:
adapter.__name__  # "kb:search_knowledge_base"
adapter.__doc__   # "Search the company knowledge base"
adapter.__call__  # async function with type hints
```

**Step 5: LangChain Introspection**
```
LangChain's tool_schemas module:
├─ Inspects adapter.__name__ → tool name
├─ Inspects adapter.__doc__ → description
├─ Inspects type hints → parameter types
└─ Builds JSON Schema for provider
```

**Output: Provider-Specific Tool Schema**

**For Anthropic:**
```json
{
  "name": "kb:search_knowledge_base",
  "description": "Search the company knowledge base",
  "input_schema": {
    "type": "object",
    "properties": {
      "query": {"type": "string", "description": "Search query"},
      "limit": {"type": "integer", "description": "Max results", "default": 10},
      "filters": {
        "type": "object",
        "description": "Search filters",
        "properties": {
          "category": {"type": "string"},
          "date_range": {"type": "string"}
        }
      }
    },
    "required": ["query"]
  }
}
```

**For OpenAI:**
```json
{
  "type": "function",
  "function": {
    "name": "kb:search_knowledge_base",
    "description": "Search the company knowledge base",
    "parameters": {
      "type": "object",
      "properties": {
        "query": {"type": "string", "description": "Search query"},
        "limit": {"type": "integer", "description": "Max results", "default": 10},
        "filters": {"type": "object", "description": "Search filters"}
      },
      "required": ["query"]
    }
  }
}
```

**Data Persistence:** MCP tool definitions are not persisted separately. Tool execution results are persisted as ToolMessages in checkpoints (no changes needed).

## Implementation Guidance

### Step-by-Step Data Flow Integration

**Phase 1: Foundation Setup**

1. **Create MCP Configuration Layer**
   - File: `backend/app/infrastructure/config/mcp_settings.py`
   - Data: MCPServerConfig, MCPSettings DTOs
   - Responsibility: Parse and validate MCP configuration from environment
   - Data Flow: Environment → Pydantic models → Settings

2. **Create MCP Client**
   - File: `backend/app/infrastructure/mcp/mcp_client.py`
   - Data: HTTP async client for MCP server communication
   - Responsibility: Discover tools, invoke tools, handle errors
   - Data Flow: MCPClient → MCP Server (HTTP) → MCPToolDefinition (JSON)

3. **Create Tool Adapter**
   - File: `backend/app/langgraph/tools/mcp_adapter.py`
   - Data: MCPToolAdapter class wrapping MCP definition
   - Responsibility: Transform MCP schema to Python callable
   - Data Flow: MCPToolDefinition → MCPToolAdapter → LangChain bind_tools()

4. **Create Tool Registry**
   - File: `backend/app/infrastructure/mcp/mcp_tool_registry.py`
   - Data: In-memory cache of MCPToolAdapter instances
   - Responsibility: Discover tools from MCP servers, provide tool list
   - Data Flow: MCPClient.discover() → MCPToolAdapter instances → Registry

**Phase 2: Application Integration**

5. **Update Application Startup**
   - File: `backend/app/main.py`
   - Data: Initialize registry in app.state
   - Responsibility: Discover tools at startup, make available to graph
   - Data Flow: Settings → MCPToolRegistry → app.state.mcp_registry

6. **Update WebSocket Handler**
   - File: `backend/app/adapters/inbound/websocket_handler.py`
   - Data: Pass mcp_registry in RunnableConfig
   - Responsibility: Make registry available to graph nodes
   - Data Flow: app.state → RunnableConfig → call_llm node

7. **Update call_llm Node**
   - File: `backend/app/langgraph/nodes/call_llm.py`
   - Data: Retrieve mcp_tools from registry
   - Responsibility: Combine Python and MCP tools, bind to provider
   - Data Flow: mcp_registry.get_tools() → all_tools → bind_tools()

8. **Update ToolNode** (if using dynamic discovery)
   - File: `backend/app/langgraph/graphs/streaming_chat_graph.py`
   - Data: May need custom tool executor
   - Responsibility: Lookup tools by namespaced name at execution time
   - Data Flow: tool_call.name → Registry lookup → MCPToolAdapter execution

**Phase 3: Data Persistence & Events**

9. **Verify Checkpoint Serialization**
   - File: `backend/app/infrastructure/database/langgraph_checkpointer.py`
   - Data: Ensure ToolMessage serialization handles namespaced names
   - Responsibility: Persist tool calls and results with full names
   - Data Flow: ToolMessage (with namespaced name) → MongoDB checkpoint

10. **Verify WebSocket Event Streaming**
    - File: `backend/app/adapters/inbound/websocket_handler.py`
    - Data: Tool names in TOOL_START and TOOL_COMPLETE messages
    - Responsibility: Stream namespaced tool names to client
    - Data Flow: AIMessage.tool_calls → ServerToolStartMessage/Complete

### Critical Data Flow Points to Verify

**1. Tool Name Resolution**
```
LLM calls: {"name": "kb:search", "args": {...}}
    ↓
ToolNode execution:
    ├─ Looks up "kb:search" in registered tools
    ├─ Finds MCPToolAdapter instance
    └─ Executes adapter.__call__(**args)
```
**Verify:** Tool name exactly matches adapter.__name__ property

**2. Parameter Validation**
```
MCP Tool Schema:
    "properties": {"query": {"type": "string"}}
    ↓
Adapter Type Hints:
    async def __call__(self, query: str) -> str
    ↓
LLM calls with:
    {"query": "search term"}
    ↓
Execution:
    await adapter(query="search term")
```
**Verify:** Type hints extracted correctly from JSON schema

**3. Result Serialization**
```
MCP Server Response:
    {"results": [{"title": "...", "url": "..."}]}
    ↓
MCPToolAdapter.__call__ returns:
    str (JSON serialization of results)
    ↓
ToolMessage.content:
    "[{\"title\": \"...\", \"url\": \"...\"}]"
    ↓
Checkpoint serialization:
    persists as string content
```
**Verify:** Results are serializable to string without loss

**4. Checkpoint Persistence with MCP**
```
Conversation history:
├─ HumanMessage("search for X")
├─ AIMessage(tool_calls=[{"name": "kb:search", "args": {"query": "X"}}])
├─ ToolMessage(tool_call_id="call_1", name="kb:search", content="[...]")
├─ AIMessage("Here's what I found...")
└─ (persisted as checkpoint)
    ↓
Next invocation (same conversation):
    graph.ainvoke({"messages": [...]}, config)
    ↓
LangGraph loads from checkpoint:
    all previous messages including ToolMessages
    ↓
Graph execution sees full history
```
**Verify:** ToolMessages with MCP tool names load correctly from MongoDB

**5. WebSocket Event Streaming with MCP**
```
on_chat_model_end:
    AIMessage.tool_calls: [{"name": "kb:search", "args": {...}}]
    ↓ cache tool_call
    ↓
on_tool_start:
    ServerToolStartMessage(tool_name="kb:search", ...)
    ↓
on_tool_end:
    ServerToolCompleteMessage(tool_name="kb:search", tool_result="...")
```
**Verify:** Tool names with namespace propagate correctly through events

## Risks and Considerations

### Data Flow Integrity Risks

**1. Tool Name Collision**
- **Risk:** Multiple MCP servers with same tool name
- **Impact:** Incorrect tool execution, wrong parameters passed
- **Mitigation:** Mandatory namespacing, validation in adapter creation
- **Data Flow Point:** MCPToolRegistry.discover_tools() must enforce unique names

**2. Parameter Type Mismatch**
- **Risk:** JSON schema doesn't translate cleanly to Python types (e.g., "object" type)
- **Impact:** LangChain schema generation fails, tool not available to LLM
- **Mitigation:** Schema validation, type hint generation with fallback to str/Any
- **Data Flow Point:** MCPToolAdapter._build_signature() must handle edge cases

**3. MCP Server Timeout**
- **Risk:** MCP tool invocation hangs, blocks LangGraph execution
- **Impact:** WebSocket client hangs, eventual timeout
- **Mitigation:** Per-tool timeout in MCPToolAdapter with async timeout
- **Data Flow Point:** MCPToolAdapter.__call__() must have configurable timeout

**4. Tool Discovery Failure**
- **Risk:** MCP server unreachable at startup
- **Impact:** Tools unavailable for entire application lifetime
- **Mitigation:** Graceful degradation, retry logic, health checks
- **Data Flow Point:** Application startup must handle MCPToolRegistry initialization failure

**5. Checkpoint Compatibility**
- **Risk:** ToolMessages with MCP tool names may not deserialize from old checkpoints
- **Impact:** Existing conversations break if tool definitions change
- **Mitigation:** Schema versioning, migration path for tool name changes
- **Data Flow Point:** Checkpoint deserialization must handle both old and new tool names

### Performance & Scalability Risks

**6. Tool Discovery Overhead**
- **Risk:** Discovering tools from multiple MCP servers at startup is slow
- **Impact:** Application startup delayed, cold start issues in serverless
- **Mitigation:** Parallel discovery, caching, TTL-based refresh
- **Data Flow Point:** MCPToolRegistry.discover_tools() use concurrent HTTP requests

**7. Tool Execution Latency**
- **Risk:** MCP tool calls add HTTP latency to conversation flow
- **Impact:** Slower response times for conversations using MCP tools
- **Mitigation:** Async execution (already handled), connection pooling, monitoring
- **Data Flow Point:** MCPClient must use connection pooling and keep-alive

**8. Memory Consumption**
- **Risk:** Large number of MCP tools in registry consumes memory
- **Impact:** Scaling to many MCP servers problematic
- **Mitigation:** Lazy loading, per-conversation tool filtering
- **Data Flow Point:** Consider pagination or on-demand loading for large tool sets

### Security Risks

**9. Credential Exposure**
- **Risk:** MCP auth tokens logged or exposed in error messages
- **Impact:** Unauthorized access to MCP servers
- **Mitigation:** Never log credentials, use environment variables, mask in errors
- **Data Flow Point:** MCPToolRegistry initialization and error handling

**10. Arbitrary Tool Execution**
- **Risk:** LLM calls tools with malicious parameters
- **Impact:** Information disclosure, resource exhaustion
- **Mitigation:** Parameter validation in adapter, rate limiting per tool
- **Data Flow Point:** MCPToolAdapter.__call__() must validate before HTTP call

## Testing Strategy

### Unit Tests for MCP Adapter

**Test 1: Schema Transformation**
```python
async def test_mcp_schema_to_type_hints():
    """Verify MCP schema correctly converts to Python type hints."""
    schema = {
        "properties": {
            "query": {"type": "string"},
            "limit": {"type": "integer", "default": 10}
        },
        "required": ["query"]
    }
    definition = MCPToolDefinition(
        name="search",
        description="Search",
        input_schema=schema
    )
    adapter = MCPToolAdapter(definition, mock_client)

    # Verify signature
    sig = inspect.signature(adapter.__call__)
    assert sig.parameters["query"].annotation == str
    assert sig.parameters["limit"].annotation == int
    assert sig.parameters["limit"].default == 10
```

**Data Flow Verification:** Schema → Type hints extraction → LangChain introspection

**Test 2: Tool Invocation with MCP**
```python
async def test_mcp_tool_execution():
    """Verify MCP tool calls MCP server and returns string result."""
    mock_client = AsyncMock(spec=MCPClient)
    mock_client.invoke.return_value = '{"results": []}'

    adapter = MCPToolAdapter(definition, mock_client)
    result = await adapter(query="test")

    assert result == '{"results": []}'
    mock_client.invoke.assert_called_once_with("search", {"query": "test"})
```

**Data Flow Verification:** Adapter.__call__() → MCPClient.invoke() → Result serialization

**Test 3: Tool Naming with Namespace**
```python
async def test_namespaced_tool_name():
    """Verify tool names include namespace."""
    adapter = MCPToolAdapter(definition, mock_client, namespace="kb")

    assert adapter.__name__ == "kb:search"
    assert "Search" in adapter.__doc__
```

**Data Flow Verification:** Namespace + tool name → adapter.__name__

### Integration Tests with LangGraph

**Test 4: Tool Binding**
```python
async def test_langgraph_bind_mcp_tools():
    """Verify MCP tools bind correctly to LLM provider."""
    mcp_adapter = MCPToolAdapter(definition, mock_client)
    python_tools = [add, multiply]
    all_tools = python_tools + [mcp_adapter]

    provider = AnthropicProvider()
    provider_with_tools = provider.bind_tools(all_tools)

    # Verify schema generation
    assert "kb:search" in [tool.name for tool in provider.model.tools]
```

**Data Flow Verification:** MCPToolAdapter → bind_tools() → Provider schema with MCP tool

**Test 5: Tool Execution in Graph**
```python
async def test_langgraph_executes_mcp_tool():
    """Verify LangGraph can invoke MCP tool during conversation."""
    # Setup
    mcp_registry = MCPToolRegistry([server_config])
    graph = create_streaming_chat_graph(checkpointer)

    config = RunnableConfig(
        configurable={
            "thread_id": "conv-1",
            "llm_provider": provider,
            "mcp_registry": mcp_registry
        }
    )

    # Execute
    result = await graph.ainvoke(
        {"messages": [HumanMessage("Search knowledge base")]},
        config
    )

    # Verify
    messages = result["messages"]
    assert any(isinstance(m, ToolMessage) for m in messages)
    mcp_tool_msg = next(m for m in messages if isinstance(m, ToolMessage))
    assert "kb:search" in mcp_tool_msg.name or mcp_tool_msg.tool_call_id
```

**Data Flow Verification:** RunnableConfig with mcp_registry → Graph execution → MCP tool invocation → ToolMessage

### End-to-End WebSocket Tests

**Test 6: WebSocket Events with MCP**
```python
async def test_websocket_mcp_tool_events():
    """Verify WebSocket streams TOOL_START/COMPLETE for MCP tools."""
    # Setup WebSocket connection
    async with websocket_connect(...) as ws:
        # Send message requiring MCP tool
        await ws.send_text(json.dumps({
            "type": "message",
            "conversation_id": "conv-1",
            "content": "Search knowledge base"
        }))

        events = []
        async for msg in ws:
            data = json.loads(msg)
            if data["type"] in ["tool_start", "tool_complete"]:
                events.append(data)
            if data["type"] == "complete":
                break

        # Verify tool events
        tool_start = next(e for e in events if e["type"] == "tool_start")
        tool_complete = next(e for e in events if e["type"] == "tool_complete")

        assert tool_start["tool_name"] == "kb:search"
        assert tool_complete["tool_name"] == "kb:search"
```

**Data Flow Verification:** MCP tool execution → on_tool_start event → ServerToolStartMessage → WebSocket → Client

### Checkpoint Persistence Tests

**Test 7: MCP Tool Checkpointing**
```python
async def test_mcp_tool_checkpoint_persistence():
    """Verify MCP tool calls and results are persisted in checkpoints."""
    # Execute conversation with MCP tool
    result = await graph.ainvoke(
        {"messages": [HumanMessage("Search")]},
        config
    )

    # Retrieve checkpoint
    checkpoint = await checkpointer.get(thread_id="conv-1")

    # Verify ToolMessage persisted with correct name
    messages = checkpoint["channel_values"]["messages"]
    tool_msgs = [m for m in messages if m["type"] == "tool"]

    assert len(tool_msgs) > 0
    assert any("kb:search" in m.get("name", "") for m in tool_msgs)
```

**Data Flow Verification:** ToolMessage → Checkpoint serialization → MongoDB → Checkpoint retrieval

## Key Assumptions & Clarifications Needed

### Assumptions Made

1. **MCP servers are HTTP-based** - Current analysis assumes JSON-RPC over HTTP. Verify if other transports needed.

2. **Tool results are JSON-serializable** - MCP tool outputs are converted to strings. Verify this handles all MCP response formats.

3. **Static tool discovery at startup** - Recommended approach. Clarify if dynamic discovery needed immediately.

4. **Namespacing is beneficial** - Using namespace:toolname format for multi-server scenarios. Confirm naming convention acceptable.

5. **Type hint extraction is sufficient** - LangChain's introspection works with dynamically-generated type hints. May need testing.

### Information Gaps for Pablo

1. **MCP Protocol Specifics**
   - What is exact JSON-RPC format for MCP tool definitions?
   - How are error responses formatted?
   - What authentication mechanisms should be supported initially?

2. **Tool Discovery Frequency**
   - Should tools be discovered once at startup or periodically refreshed?
   - Should there be per-conversation tool filtering?
   - Are there security implications of tool visibility?

3. **Performance Expectations**
   - What is acceptable latency for MCP tool calls?
   - Should there be caching of tool results?
   - Rate limiting requirements per MCP server?

4. **Backward Compatibility**
   - Should existing Python tools remain in parallel?
   - Any migration path concerns for conversations using old tools?
   - Version compatibility for MCP server changes?

## Summary

The data flow for MCP tool integration in Genesis follows clean data transformation principles:

**Data Enters Via:**
- WebSocket ClientMessage → RunnableConfig with mcp_registry → Graph invocation

**Data Transforms At:**
- MCP schema (JSON) → MCPToolAdapter (Python callable) → LangChain schema → Provider-specific format
- Tool names optionally namespaced for disambiguation
- Parameters extracted from JSON schema and converted to Python type hints

**Data Persists As:**
- ToolMessage objects with full tool names in LangGraph checkpoints
- No schema changes needed - existing serialization handles namespaced names

**Data Exits Via:**
- WebSocket events (TOOL_START/TOOL_COMPLETE) with namespaced tool names
- Stream events flow directly from AIMessage.tool_calls to ServerMessages

**Key Data Flow Points:**
1. **Discovery:** Application startup → MCPToolRegistry → app.state
2. **Binding:** RunnableConfig → call_llm node → bind_tools() with all tools
3. **Execution:** AIMessage.tool_calls → ToolNode lookup → MCPToolAdapter.__call__()
4. **Persistence:** ToolMessage → AsyncMongoDBSaver → MongoDB checkpoint
5. **Streaming:** on_tool_start/end events → ServerMessages → WebSocket → Client

**No Changes Required To:**
- ILLMProvider interface (works transparently with callable adapters)
- LangGraph state persistence (ToolMessage serialization unchanged)
- WebSocket event schema (tool_name field handles any string)
- Checkpoint structure (no new fields needed)

**New Components Required:**
- MCPToolAdapter (bridge MCP schema to Python callable)
- MCPClient (HTTP communication with MCP servers)
- MCPToolRegistry (discovery and caching)
- MCPSettings (configuration management)
- Application startup integration (registry initialization)
- call_llm node update (retrieve and bind MCP tools)
