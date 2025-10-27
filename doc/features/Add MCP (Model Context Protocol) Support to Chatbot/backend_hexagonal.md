# Backend Hexagonal Architecture Analysis: MCP (Model Context Protocol) Support

## Request Summary

Add MCP (Model Context Protocol) support to the Genesis chatbot for dynamic tool discovery and management. MCP enables external servers to provide tools, resources, and capabilities to the LLM at runtime, replacing the current hardcoded tool list approach. This requires integrating MCPClientManager into the infrastructure layer while maintaining clean separation between infrastructure (tool management) and domain logic (tool execution).

---

## Relevant Files & Modules

### Core System Files

#### Application Lifecycle
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/main.py` - FastAPI app entry point, lifespan management, database initialization
  - **Relevance**: Manages startup/shutdown events. MCPClientManager initialization should happen here during the `lifespan` context manager.

#### Infrastructure Configuration
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/config/settings.py` - Application settings and environment variables
  - **Relevance**: Configuration for MCP servers (URLs, authentication, connection parameters) should be defined here.
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/config/logging_config.py` - Centralized logging setup
  - **Relevance**: MCP client logging should use this system for consistent log output.

#### Infrastructure Database & Clients
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/database/chromadb_client.py` - ChromaDB vector database client
  - **Relevance**: Pattern to follow for implementing MCPClientManager as a similar infrastructure singleton client.
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/database/mongodb.py` - MongoDB connection manager
  - **Relevance**: Pattern for async initialization and lifecycle management.

### LangGraph Integration Files

#### Graph Definitions
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/streaming_chat_graph.py` - Streaming chat graph with tool support
  - **Relevance**: Currently hardcodes tools list (multiply, add, web_search, rag_search). Must be refactored to accept dynamic tools from MCPClientManager.
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/chat_graph.py` - Main chat graph definition
  - **Relevance**: Also hardcodes tools list. Must accept dynamic tools.

#### Graph Nodes
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/call_llm.py` - LLM invocation node
  - **Relevance**: Binds tools to LLM provider. Must bind dynamically discovered MCP tools instead of hardcoded list.
  - **Current**: `tools = [multiply, add, web_search, rag_search]` passed to `llm_provider.bind_tools(tools)`
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/process_input.py` - Input validation node
  - **Relevance**: Validates messages. No changes needed unless input format changes.

#### Graph State
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/state.py` - LangGraph conversation state
  - **Relevance**: May need to extend state to track which MCP tools are active for a conversation.

#### Tool Definitions (Current)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/add.py` - Simple addition tool
  - **Relevance**: Example of current tool format. MCP tools will have similar interface.
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/multiply.py` - Simple multiply tool
  - **Relevance**: Example of current tool format.
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/web_search.py` - Web search tool
  - **Relevance**: Example of tool using external service. MCP tools follow similar pattern.
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/rag_search.py` - RAG vector store search tool
  - **Relevance**: Example of tool accessing app state (app.state.vector_store). MCP tools must follow this pattern for consistency.
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/__init__.py` - Tools module exports
  - **Relevance**: Currently empty. May be used to export dynamic tools list.

### Core Domain Files

#### Port Interfaces
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/llm_provider.py` - ILLMProvider interface
  - **Relevance**: Defines `bind_tools()` method. No changes needed; MCP tools will be passed through this interface.

#### Domain Entities
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/document.py` - Document entity for RAG
  - **Relevance**: May inform design of MCP resource representation if MCP provides document-like resources.

### Adapter Files

#### Inbound Adapters (HTTP/WebSocket)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py` - WebSocket chat handler
  - **Relevance**: Passes graph and llm_provider to graph execution. May need to pass MCPClientManager or dynamically discovered tools.
  - **Current flow**: Sets up `RunnableConfig` with `thread_id`, `llm_provider`, `user_id`.

#### Outbound Adapters
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/provider_factory.py` - LLM provider factory
  - **Relevance**: Creates provider instances. No direct changes, but MCPClientManager will be initialized similarly.
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/openai_provider.py` - OpenAI provider
  - **Relevance**: Implements `bind_tools()`. Shows current tool binding pattern.
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/anthropic_provider.py` - Anthropic provider
  - **Relevance**: Also implements `bind_tools()`.
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/gemini_provider.py` - Gemini provider
  - **Relevance**: Also implements `bind_tools()`.
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/ollama_provider.py` - Ollama provider
  - **Relevance**: Also implements `bind_tools()`.

---

## Current Architecture Overview

### Hexagonal Architecture Layers

```
┌─────────────────────────────────────┐
│  Inbound Adapters (HTTP/WebSocket) │
│  - websocket_handler.py             │
│  - Receives messages, calls graph   │
└────────────────┬────────────────────┘
                 │
┌────────────────▼────────────────────┐
│      Core Domain (Isolated)         │
│  - LLM Provider Port (ILLMProvider) │
│  - Tool interface definition        │
│  - Message entities (BaseMessage)   │
└────────────────┬────────────────────┘
                 │
┌────────────────▼────────────────────┐
│   Outbound Adapters                 │
│  - LLM Providers (OpenAI, etc.)     │
│  - Vector Store (ChromaDB)          │
│  - Repositories (MongoDB)           │
│  - [NEW] MCPClientManager           │
└─────────────────────────────────────┘
```

### Domain Core

**Pure business logic, zero infrastructure dependencies:**

- **ILLMProvider Interface** (`core/ports/llm_provider.py`):
  - `async generate(messages: List[BaseMessage]) -> BaseMessage`
  - `async stream(messages: List[BaseMessage]) -> AsyncGenerator[str, None]`
  - `def bind_tools(tools: List[Callable], **kwargs) -> ILLMProvider`
  - **Key principle**: Tools are passed as arguments, not hardcoded in the domain

- **BaseMessage Types** (LangChain):
  - HumanMessage, AIMessage, SystemMessage
  - ToolMessage for tool results
  - No domain-specific tool representation

### Ports (Interfaces)

**Primary (Driving) Ports:**
- **HTTP Routers**: REST API entry points
- **WebSocket Handler**: Real-time chat communication
- **Graph Execution**: Triggered by WebSocket handler, returns streaming events

**Secondary (Driven) Ports:**
- **ILLMProvider**: Abstract LLM provider interface (already exists)
- **IVectorStore**: Document retrieval interface (already exists)
- **IUserRepository**: User persistence interface (already exists)
- **IConversationRepository**: Conversation persistence interface (already exists)
- **[NEW] IToolRegistry or IMCPClientManager**: Dynamic tool management interface (needs design)

### Adapters (Infrastructure)

**Current Tool Registration (Hardcoded):**
```python
# In streaming_chat_graph.py
tools = [multiply, add, web_search, rag_search]

# In call_llm.py
tools = [multiply, add, web_search, rag_search]
llm_provider_with_tools = llm_provider.bind_tools(tools, parallel_tool_calls=False)
```

**Current Tool Execution Flow:**
1. Tools are hardcoded in graph definitions
2. Tools are bound to LLM provider in call_llm node
3. LangGraph ToolNode executes tool calls
4. WebSocket handler streams tool execution events

**Infrastructure Layer Organization:**
```
app/infrastructure/
├── config/
│   ├── settings.py (environment variables)
│   └── logging_config.py
├── database/
│   ├── chromadb_client.py (vector store client - PATTERN TO FOLLOW)
│   ├── mongodb.py
│   └── langgraph_checkpointer.py
├── security/
│   ├── auth_service.py
│   └── dependencies.py
└── [NEW] mcp/
    └── mcp_client_manager.py (MCP client management - TO IMPLEMENT)
```

### LangGraph Integration

**Current Tool Registration:**
- Tools are imported directly in graph files
- List is hardcoded at graph creation time
- No mechanism for runtime tool discovery

**Tool Binding in call_llm.py:**
```python
llm_provider_with_tools = llm_provider.bind_tools(tools, parallel_tool_calls=False)
ai_message = await llm_provider_with_tools.generate(messages)
```

**Graph Creation Pattern:**
```python
def create_streaming_chat_graph(checkpointer: AsyncMongoDBSaver):
    graph_builder = StateGraph(ConversationState)

    # Hardcoded tools list
    tools = [multiply, add, web_search, rag_search]

    graph_builder.add_node("tools", ToolNode(tools))
    # ... rest of graph setup
```

---

## Impact Analysis

### Components Affected by MCP Integration

#### 1. **Application Initialization (main.py)**
- **Current**: Initializes ChromaDBClient, LLM provider, graph in lifespan
- **Changes Needed**:
  - Initialize MCPClientManager before graph creation
  - Pass initialized tools to graph creation functions
  - Handle MCP client lifecycle (startup/shutdown)

#### 2. **Configuration Management (settings.py)**
- **Current**: LLM provider settings, database URLs, logging config
- **Changes Needed**:
  - Add MCP server configurations (URLs, authentication)
  - Add MCP feature flags (enable/disable)
  - Tool discovery settings (timeout, retry logic)

#### 3. **Graph Creation (streaming_chat_graph.py, chat_graph.py)**
- **Current**: Takes `checkpointer` parameter, hardcodes tools
- **Changes Needed**:
  - Accept `tools` parameter or retrieve from MCPClientManager
  - Support dynamic tool list at graph compilation time
  - Handle tool updates gracefully

#### 4. **LLM Invocation (call_llm.py node)**
- **Current**: Hardcoded tool list passed to `bind_tools()`
- **Changes Needed**:
  - Retrieve tools from MCPClientManager (via config or app state)
  - Merge static tools (multiply, add, rag_search) with MCP tools
  - Maintain tool binding signature (doesn't change for LLM provider)

#### 5. **WebSocket Handler (websocket_handler.py)**
- **Current**: Receives graph, llm_provider, conversation_repository
- **Changes Needed**:
  - May need to receive MCPClientManager or pass tools through config
  - Alternatively, MCPClientManager available through app.state
  - No changes needed if tools are resolved from app.state

#### 6. **Tool Execution (ToolNode in LangGraph)**
- **Current**: Executes hardcoded tools
- **Changes Needed**:
  - LangGraph ToolNode will execute MCP tools transparently
  - MCP tools will be callable Python functions (interface remains same)
  - WebSocket handler's tool event streaming works unchanged

### Dependency Flow

**Current (Static):**
```
main.py → creates graph(checkpointer)
       → graph has tools=[multiply, add, web_search, rag_search]
       → websocket calls graph.astream_events()
       → tools are bound to LLM provider during call_llm node
```

**Proposed (Dynamic):**
```
main.py → initializes MCPClientManager
       → discovers tools from MCP servers
       → creates graph(checkpointer, tools)
       → graph has tools=[multiply, add, web_search, rag_search, ...MCP tools]
       → websocket calls graph.astream_events()
       → tools are bound to LLM provider during call_llm node
```

### Key Architectural Decisions

1. **MCPClientManager Location**: Infrastructure layer (like ChromaDBClient)
   - Handles external MCP server communication (infrastructure concern)
   - Not part of domain logic
   - Lifecycle managed in main.py like ChromaDBClient

2. **Tool Representation**: Keep as Python callables
   - MCP tools converted to Python functions with type hints
   - No change to tool binding in LLM providers
   - Transparent to domain logic

3. **Tool Registry**: Static discovery at startup vs. dynamic at runtime
   - **Recommended**: Static discovery at startup (simpler, more predictable)
   - Store discovered tools in MCPClientManager singleton
   - Retrieve and bind during graph compilation

4. **Backward Compatibility**: Keep static tools alongside MCP tools
   - Current hardcoded tools (multiply, add, rag_search, web_search) remain
   - MCP tools added to same list
   - No changes to existing tool structure

---

## Architectural Recommendations

### Proposed Ports

#### 1. **IMCPClientManager Interface** (New Port)
- **Location**: `backend/app/core/ports/mcp_client_manager.py`
- **Purpose**: Abstract interface for MCP client management (port)
- **Methods**:
  ```python
  @abstractmethod
  async def initialize(self) -> None:
      """Initialize connections to MCP servers"""
      pass

  @abstractmethod
  async def shutdown(self) -> None:
      """Close all MCP server connections"""
      pass

  @abstractmethod
  def get_tools(self) -> List[Callable]:
      """Return all discovered tools as Python callables"""
      pass

  @abstractmethod
  def get_tool(self, name: str) -> Optional[Callable]:
      """Get a specific tool by name"""
      pass
  ```

**Rationale**:
- Keeps MCP implementation details out of domain logic
- Allows swapping MCP implementation without changing graph/domain code
- Follows hexagonal architecture principle of depending on abstractions

### Proposed Adapters

#### 1. **MCPClientManager Adapter** (New Implementation)
- **Location**: `backend/app/adapters/outbound/mcp/mcp_client_manager.py`
- **Purpose**: Concrete implementation of IMCPClientManager using mcp library
- **Responsibilities**:
  - Initialize connections to MCP servers (from settings)
  - Convert MCP tools to Python callables
  - Cache tools for efficient retrieval
  - Handle reconnection logic
  - Log tool discovery and errors

**Key Design**:
```python
class MCPClientManager(IMCPClientManager):
    """Manages MCP client connections and tool discovery."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.clients: Dict[str, MCPClient] = {}
        self.tools_cache: Dict[str, Callable] = {}

    async def initialize(self) -> None:
        """Connect to all configured MCP servers"""
        for server_config in self.settings.mcp_servers:
            # Connect to server
            # List available tools
            # Convert to Python callables
            # Cache tools

    def get_tools(self) -> List[Callable]:
        """Return all cached tools"""
        return list(self.tools_cache.values())

    async def shutdown(self) -> None:
        """Close all client connections"""
        for client in self.clients.values():
            await client.close()
```

#### 2. **MCP Tool Converter** (Utility)
- **Location**: `backend/app/adapters/outbound/mcp/tool_converter.py`
- **Purpose**: Convert MCP tool schemas to Python callables with proper signatures
- **Handles**:
  - Converting MCP tool definitions to Python functions
  - Preserving type hints and docstrings
  - Creating proper AsyncIO wrappers for async MCP calls
  - Error handling and logging

### Domain Changes

**No changes to domain core required:**
- Tools remain abstract (passed as arguments)
- ILLMProvider interface unchanged
- Message types unchanged
- Use cases unchanged

**Rationale**: Domain layer only cares about "LLM can call tools", not WHERE tools come from.

### Infrastructure Changes

#### 1. **Settings Extension** (settings.py)
```python
# Add MCP configuration
mcp_servers: List[Dict[str, Any]] = []  # List of MCP server configs
mcp_enabled: bool = False
mcp_discovery_timeout: int = 5  # seconds
mcp_tool_prefix: str = "mcp_"  # Prefix for MCP tools

# Example:
# MCP_SERVERS=[{"type": "stdio", "command": "tool-server"}]
```

#### 2. **MCPClientManager Initialization** (main.py lifespan)
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... existing startup code ...

    # Initialize MCP client manager
    mcp_manager = MCPClientManager(settings)
    await mcp_manager.initialize()
    app.state.mcp_manager = mcp_manager

    # Get tools from MCP (will be combined with static tools in graphs)
    mcp_tools = mcp_manager.get_tools()

    # Create graphs with combined tools
    all_tools = get_all_tools(static_tools, mcp_tools)
    app.state.chat_graph = create_chat_graph(checkpointer, all_tools)
    app.state.streaming_chat_graph = create_streaming_chat_graph(checkpointer, all_tools)

    yield

    # ... existing shutdown code ...
    await mcp_manager.shutdown()
```

#### 3. **Graph Creation Updates** (streaming_chat_graph.py, chat_graph.py)
```python
def create_streaming_chat_graph(checkpointer: AsyncMongoDBSaver, tools: List[Callable]):
    """Create and compile the streaming chat graph with provided tools."""

    graph_builder = StateGraph(ConversationState)

    # Use provided tools instead of hardcoded list
    graph_builder.add_node("tools", ToolNode(tools))

    # ... rest of graph setup unchanged ...

    return graph_builder.compile(checkpointer=checkpointer)
```

#### 4. **Call LLM Node Update** (call_llm.py)
```python
async def call_llm(state: ConversationState, config: RunnableConfig) -> dict:
    """Call the LLM provider to generate a response."""

    messages = state["messages"]
    conversation_id = state["conversation_id"]

    # Retrieve tools from RunnableConfig (passed from graph)
    tools = config.get("configurable", {}).get("tools", [])

    # Fallback to app state if not in config
    if not tools:
        from app.main import app
        mcp_manager = getattr(app.state, 'mcp_manager', None)
        static_tools = [multiply, add, web_search, rag_search]
        mcp_tools = mcp_manager.get_tools() if mcp_manager else []
        tools = static_tools + mcp_tools

    llm_provider = config["configurable"]["llm_provider"]
    llm_provider_with_tools = llm_provider.bind_tools(tools, parallel_tool_calls=False)

    ai_message = await llm_provider_with_tools.generate(messages)

    return {"messages": [ai_message]}
```

### Dependency Flow

**Direction (Critical for Hexagonal Architecture):**
```
Dependencies point INWARD toward domain core

main.py (Application)
  ↓
MCPClientManager (Infrastructure Adapter)
  ↓
IMCPClientManager (Port/Interface - Domain aware)

WebSocket Handler (Inbound Adapter)
  ↓
ILLMProvider (Port/Interface - Domain aware)
  ↓
LLM Provider Implementations (Outbound Adapters)
```

**Tool Flow at Runtime:**
```
1. main.py startup
   → Initialize MCPClientManager
   → Discover tools from MCP servers
   → Combine with static tools

2. WebSocket message received
   → Handler calls graph.astream_events()
   → config includes tools list

3. call_llm node executes
   → Retrieves tools from config
   → Binds tools to LLM provider
   → Generates response

4. ToolNode executes (if tool called)
   → LangGraph executes tool
   → Returns result as ToolMessage
```

---

## Implementation Guidance

### Phase 1: Infrastructure Foundation

1. **Create MCPClientManager class** (`backend/app/adapters/outbound/mcp/mcp_client_manager.py`)
   - Implement core MCP client initialization
   - Add tool discovery from MCP servers
   - Convert MCP tools to Python callables
   - Handle lifecycle (init/shutdown)

2. **Create IMCPClientManager port** (`backend/app/core/ports/mcp_client_manager.py`)
   - Define abstract interface
   - Keep domain layer independent

3. **Add MCP configuration** (settings.py)
   - MCP server list
   - Feature flags
   - Timeout settings

4. **Update main.py lifespan**
   - Initialize MCPClientManager during startup
   - Store in app.state
   - Shutdown on application close

### Phase 2: Integration with LangGraph

1. **Update graph creation functions**
   - Accept `tools` parameter
   - Modify ToolNode initialization
   - Keep checkpointer handling unchanged

2. **Update call_llm node**
   - Retrieve tools from config or app state
   - Bind dynamically discovered tools to LLM provider
   - Maintain existing LLM invocation logic

3. **Update WebSocket handler** (if needed)
   - May need to pass tools through RunnableConfig
   - Or retrieve from app.state in call_llm node

### Phase 3: Testing & Refinement

1. **Unit tests for MCPClientManager**
   - Mock MCP server connections
   - Test tool discovery
   - Test error handling

2. **Integration tests**
   - Test full flow: startup → discovery → graph compilation → tool execution
   - Test tool binding to LLM providers
   - Test error scenarios

3. **Manual testing**
   - Test with real MCP servers
   - Test tool execution through WebSocket
   - Test backward compatibility with static tools

---

## Risks and Considerations

### Architectural Risks

1. **Tool Discovery Complexity**
   - **Risk**: MCP servers may provide tools with conflicting names or signatures
   - **Mitigation**: Implement tool namespace/prefixing (e.g., `mcp_server_name_tool_name`)
   - **Code location**: MCPClientManager tool converter

2. **Startup Time**
   - **Risk**: Discovering tools from multiple MCP servers during startup may slow initialization
   - **Mitigation**:
     - Set reasonable discovery timeouts (configurable)
     - Log discovery progress
     - Consider lazy loading if servers are slow
   - **Code location**: main.py lifespan, settings.py

3. **Dependency Inversion Violation**
   - **Risk**: If MCPClientManager directly creates tools without port abstraction, violates hexagonal principles
   - **Mitigation**: Use IMCPClientManager interface, keep MCP details in adapter layer
   - **Code location**: Enforce in architecture review

### Integration Risks

1. **Tool Binding Compatibility**
   - **Risk**: MCP tools may not bind correctly with all LLM providers
   - **Mitigation**: Test binding with all supported LLM providers
   - **Code location**: call_llm.py tool binding logic

2. **Tool Execution in LangGraph**
   - **Risk**: MCP tools may have async incompatibilities with LangGraph ToolNode
   - **Mitigation**: Ensure all MCP tools are properly converted to sync callables
   - **Code location**: Tool converter (tool_converter.py)

3. **Tool State Management**
   - **Risk**: MCP tool state may not be properly persisted in LangGraph checkpoints
   - **Mitigation**: Tools should be stateless or manage their own persistence
   - **Code location**: Tool converter, call_llm.py

### Operational Risks

1. **MCP Server Reliability**
   - **Risk**: If MCP server is down, tool discovery fails, affecting startup
   - **Mitigation**:
     - Handle connection failures gracefully
     - Implement retry logic
     - Allow startup with partial tool discovery
     - Log warnings but don't crash
   - **Code location**: MCPClientManager.initialize()

2. **Tool Versioning**
   - **Risk**: MCP server may update tool schemas, breaking existing conversations
   - **Mitigation**: Version tools, track which version was used per conversation
   - **Code location**: Consider extending ConversationState if needed

### Dependency Management

1. **MCP Library**
   - Add mcp package to requirements.txt
   - Pin version for stability
   - Monitor for updates/security patches

2. **Circular Dependencies**
   - **Check**: Ensure MCPClientManager doesn't import domain use cases
   - **Check**: Ensure domain never imports MCPClientManager directly
   - **Verify**: Only adapters/main.py import MCPClientManager

---

## Testing Strategy

### Unit Tests

**MCPClientManager**:
```python
# Test tool discovery
async def test_discover_tools_from_mcp_server()
async def test_tool_conversion_preserves_signatures()
async def test_handle_server_connection_failure()

# Test tool retrieval
def test_get_tools_returns_callable_list()
def test_get_tool_by_name()

# Test lifecycle
async def test_initialize_connects_to_servers()
async def test_shutdown_closes_connections()
```

**Tool Converter**:
```python
# Test signature conversion
def test_convert_mcp_tool_to_callable()
def test_preserve_type_hints()
def test_preserve_docstrings()
def test_async_tool_wrapping()

# Test error handling
def test_handle_invalid_tool_schema()
```

### Integration Tests

**Graph Creation with MCP Tools**:
```python
# Test graph compilation
async def test_create_streaming_graph_with_mcp_tools()
async def test_create_chat_graph_with_mcp_tools()

# Test tool binding
async def test_llm_provider_binds_mcp_tools()
async def test_tool_node_executes_mcp_tool()
```

**End-to-End**:
```python
# Test full flow
async def test_websocket_chat_with_mcp_tool_execution()

# Test backward compatibility
async def test_static_tools_still_work()
async def test_mixed_static_and_mcp_tools()
```

### Architectural Tests

**Dependency Verification**:
```python
def test_domain_has_no_mcp_imports()
def test_mcp_manager_is_only_in_infrastructure()
def test_core_ports_agnostic_to_mcp()
```

**Test Execution Boundary**:
```python
# Ensure tools respect architectural layers
async def test_mcp_tools_execute_in_langgraph_only()
async def test_mcp_tools_not_called_from_domain()
```

---

## Key Architectural Considerations & Dependencies

### Dependency Direction (Critical)

```
✅ ALLOWED:
  main.py → MCPClientManager (initialization)
  MCPClientManager → IMCPClientManager (implements port)
  call_llm.py → MCPClientManager (retrieve tools)

❌ FORBIDDEN:
  Domain core → MCPClientManager (would create coupling)
  ILLMProvider → MCPClientManager (would violate port abstraction)
  Use cases → MCPClientManager (domain shouldn't know about tool discovery)
```

### Separation of Concerns

1. **MCPClientManager** (Infrastructure):
   - Handles MCP server communication
   - Manages client lifecycle
   - Converts tools to Python callables
   - Not domain-aware

2. **call_llm node** (LangGraph):
   - Retrieves tools (from MCPClientManager or config)
   - Binds to LLM provider
   - Invokes LLM
   - No domain logic

3. **LLM Providers** (Adapters):
   - Bind tools transparently
   - No changes needed
   - Tool binding signature unchanged

4. **Domain Core** (Pure Logic):
   - Remains untouched
   - Tools passed as arguments only
   - No knowledge of MCP

### Pattern Consistency

**Follow ChromaDBClient Pattern:**
- Singleton initialization in main.py lifespan
- Stored in app.state
- Async initialization/shutdown
- Centralized logging

**Extend Tool Pattern:**
- Tools remain Python callables
- Type hints preserved
- Docstrings preserved
- Callable interface unchanged

### Key Dependencies to Track

1. **Settings.py** → MCPClientManager (configuration)
2. **main.py** → MCPClientManager (lifecycle)
3. **MCPClientManager** → mcp library (external)
4. **call_llm.py** → MCPClientManager (tool retrieval)
5. **streaming_chat_graph.py** → MCPClientManager (tool list)
6. **chat_graph.py** → MCPClientManager (tool list)

**None of these are circular or violate hexagonal principles**.

---

## Summary

This MCP integration maintains clean hexagonal architecture by:

1. **Placing MCPClientManager in infrastructure layer** (like ChromaDBClient)
2. **Using IMCPClientManager port abstraction** to keep domain independent
3. **Keeping tool representation unchanged** (Python callables with type hints)
4. **Following existing patterns** (singleton initialization, app.state storage, async lifecycle)
5. **Making minimal changes to domain core** (none - domain stays pure)
6. **Supporting backward compatibility** (static tools work alongside MCP tools)

The architecture remains clean because:
- Dependency direction is inward (toward domain)
- Domain knows nothing about MCP implementation
- All tool discovery happens in infrastructure layer
- LLM providers remain unchanged
- Tool binding interface unchanged
- Testing can verify each layer independently

**Start with infrastructure foundation (MCPClientManager, settings), then integrate into graph creation and LLM invocation.**
