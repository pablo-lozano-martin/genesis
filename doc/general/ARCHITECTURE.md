# Architecture Overview

Genesis uses hexagonal architecture (ports and adapters) to create clean separation between business logic and infrastructure.

## Hexagonal Architecture

```
┌─────────────────────────────────────────┐
│        Inbound Adapters                 │
│   (REST API, WebSocket)                 │
│   app/adapters/inbound/                 │
└───────────────┬─────────────────────────┘
                │
┌───────────────▼─────────────────────────┐
│          Core Domain                    │
│                                         │
│  Domain Models ──► Ports ──► Use Cases │
│  (Entities)      (Interfaces) (Logic)  │
│                                         │
│  app/core/domain/ ports/ use_cases/    │
└───────────────┬─────────────────────────┘
                │
┌───────────────▼─────────────────────────┐
│       Outbound Adapters                 │
│   (MongoDB, LLM Providers)              │
│   app/adapters/outbound/                │
└─────────────────────────────────────────┘
```

## Layer Responsibilities

### Core Domain (`app/core/`)

**Pure business logic with zero infrastructure dependencies.**

- **Domain Models** (`domain/`): User, Conversation entities
- **Ports** (`ports/`): Interfaces defining contracts
  - `IUserRepository`, `IConversationRepository`
  - `ILLMProvider`: Abstract LLM interface
  - `IAuthService`: Authentication interface
- **Use Cases** (`use_cases/`): Business logic implementations
  - `RegisterUser`, `AuthenticateUser`, `CreateConversation`
  - Note: Message handling is now done through LangGraph with native checkpointing

### Adapters

**Implementations of port interfaces.**

**Inbound** (`app/adapters/inbound/`):
- REST API routers (FastAPI)
- WebSocket handlers
- Translate HTTP/WebSocket to domain operations

**Outbound** (`app/adapters/outbound/`):
- **Repositories**: MongoDB implementations
  - `MongoUserRepository`, `MongoConversationRepository`
  - Note: Messages are stored in LangGraph checkpoints (no repository needed)
- **LLM Providers**: Multiple provider implementations using LangChain BaseMessage types
  - `OpenAIProvider`, `AnthropicProvider`, `GeminiProvider`, `OllamaProvider`
  - All implement `ILLMProvider` interface and work directly with BaseMessage

### Infrastructure (`app/infrastructure/`)

**Cross-cutting concerns.**

- **Config**: Environment variables, settings
- **Security**: JWT authentication, password hashing
- **Database**: Two-database MongoDB connection management
  - `AppDatabase`: User accounts and conversation metadata
  - `LangGraphDatabase`: Message history via checkpoints
- **Logging**: Centralized logging

### LangGraph (`app/langgraph/`)

**LangGraph-first conversation flow orchestration.**

- **State** (`state.py`): Extends LangGraph's native `MessagesState`
- **Nodes** (`nodes/`): Processing nodes
  - `process_user_input`: Creates HumanMessage from input
  - `call_llm`: LLM invocation with BaseMessage types
  - `format_response`: Creates AIMessage from response
  - Note: Message persistence is automatic via LangGraph checkpointing
- **Graphs** (`graphs/`): Flow definitions compiled with checkpointer
  - `chat_graph.py`: Main conversation flow
  - `streaming_chat_graph.py`: Streaming support via astream_events()
- **Checkpointer** (`langgraph_checkpointer.py`): AsyncMongoDBSaver integration

## Why Hexagonal Architecture?

**Benefits:**
- ✅ **Testable**: Core logic tested without database/APIs
- ✅ **Flexible**: Easy to swap MongoDB for PostgreSQL or change LLM providers
- ✅ **Clear**: Obvious separation of concerns
- ✅ **Maintainable**: Add features without refactoring

**Trade-offs:**
- More initial setup (interfaces, adapters)
- May feel over-engineered for simple use cases

**Verdict**: Worth it for maintainable, extensible systems.

## Two-Database Pattern

Genesis implements a clean separation between application data and AI execution state using two MongoDB databases:

```
┌──────────────────────────────────────────────────────┐
│                   WebSocket Handler                  │
│         Uses LangGraph graphs exclusively            │
│         Calls graph.astream() for streaming          │
│         Checkpointing is automatic                   │
└────────────────┬─────────────────┬───────────────────┘
                 │                 │
                 ↓                 ↓
    ┌─────────────────────┐  ┌──────────────────────┐
    │  App Database (MongoDB) │  │ LangGraph DB (MongoDB) │
    │  • users            │  │ • langgraph_checkpoints│
    │  • conversations    │  │ • langgraph_stores     │
    │    (metadata only)  │  │   (message history)    │
    └─────────────────────┘  └──────────────────────┘
```

### App Database (genesis_app)
**Purpose**: User accounts and conversation metadata

**Collections**:
- `users`: User authentication and profiles
- `conversations`: Conversation metadata (id, user_id, title, timestamps)
  - Note: `message_count` field is optional (for backward compatibility)

**Environment Variables**:
- `MONGODB_APP_URL`: Connection string for app database
- `MONGODB_APP_DB_NAME`: Database name (default: genesis_app)

### LangGraph Database (genesis_langgraph)
**Purpose**: AI conversation execution state and message history

**Collections** (managed by LangGraph):
- `langgraph_checkpoints`: Conversation states with message history
- `langgraph_stores`: Additional LangGraph storage

**Environment Variables**:
- `MONGODB_LANGGRAPH_URL`: Connection string for LangGraph database
- `MONGODB_LANGGRAPH_DB_NAME`: Database name (default: genesis_langgraph)

### Key Architectural Principles

1. **conversation.id = thread_id**: Simple 1:1 mapping between conversation metadata and LangGraph threads
2. **Authorization in App DB**: Conversation ownership always verified in App DB before accessing LangGraph state
3. **thread_id is internal**: NEVER exposed to frontend, always resolved via conversation.id
4. **Automatic persistence**: LangGraph checkpointer handles all message storage
5. **Native LangGraph types**: Use MessagesState and BaseMessage (HumanMessage, AIMessage, SystemMessage)

### Why Two Databases?

**Separation of Concerns**:
- App DB stores "who owns what" (authorization layer)
- LangGraph DB stores "what was said" (execution layer)

**Benefits**:
- ✅ Clear security boundary: conversation ownership separate from message content
- ✅ Scalability: Can scale databases independently
- ✅ Native LangGraph: Leverage built-in checkpointing and persistence
- ✅ Cleaner code: No manual message repository, LangGraph handles it all

**Trade-offs**:
- Slightly more complex deployment (two database connections)
- Must coordinate operations across both databases (e.g., cascade delete)

## Data Flow Examples

### User Registration
```
1. User submits form (Frontend)
   ↓
2. POST /api/auth/register (Inbound Adapter)
   ↓
3. RegisterUser.execute() (Use Case)
   ↓
4. IUserRepository.create() (Port)
   ↓
5. MongoUserRepository.create() (Outbound Adapter)
   ↓
6. MongoDB (Database)
```

### Chat Message (LangGraph-First)
```
1. User sends message via WebSocket (Frontend)
   ↓
2. WebSocket handler verifies ownership (App DB)
   ↓
3. Handler calls graph.astream_events(input, config)
   - config includes thread_id = conversation.id
   ↓
4. LangGraph executes graph:
   - process_user_input node → creates HumanMessage
   - call_llm node → uses ILLMProvider with BaseMessage
   - format_response node → creates AIMessage
   - Automatic checkpoint save to LangGraph DB
   ↓
5. Stream tokens to client via on_chat_model_stream events
   ↓
6. Frontend displays streaming response
   ↓
7. Message history automatically persisted in LangGraph DB
```

## Key Technology Decisions

### Why FastAPI?
- Modern async framework
- Automatic API documentation
- Type safety with Pydantic
- WebSocket support

### Why MongoDB?
- Flexible schema for evolving conversation structures
- Good performance for document-based data
- Easy nested conversation history storage
- Native async support with Beanie

**Alternative**: PostgreSQL with SQLAlchemy also works well with this architecture.

### Why LangGraph?
- Built for agentic AI workflows
- Clear state management
- Native streaming support
- Easy to extend with tools and multi-step reasoning

### Why React + TailwindCSS?
- Component-based architecture
- TypeScript support
- Fast development with Vite
- Utility-first styling

## Security

### Authentication
- JWT tokens for stateless authentication
- Bcrypt password hashing (12 rounds)
- OAuth2 password flow
- Token expiration (30 minutes default)

### Authorization
- User isolation (users only access their own data)
- Conversation ownership checks
- Protected WebSocket connections

## Tool-Calling Architecture

Genesis supports tool-calling through LangGraph's ToolNode, enabling the AI to invoke functions during conversations. Tools are simple Python functions with type hints and docstrings.

### Components

**Tool Definitions** (`backend/app/langgraph/tools/`):
- Simple Python functions with type hints and docstrings
- Examples: `add(a: int, b: int) -> int`, `multiply(a: int, b: int) -> int`
- Automatically converted to LangChain tool schemas

**LLM Provider Integration**:
- All providers implement `ILLMProvider.bind_tools(tools, **kwargs)`
- Delegates to LangChain's native `model.bind_tools()`
- Returns new provider instance with tools bound
- Supports `parallel_tool_calls` parameter to control execution

**Graph Structure**:
```
START → process_input → call_llm → tools_condition
                                      ↓ (if tool_calls)
                                    ToolNode → call_llm → END
                                      ↓ (if no tool_calls)
                                     END
```

**WebSocket Event Streaming**:
- `on_chat_model_stream`: LLM tokens
- `on_chat_model_end`: Captures tool_calls from AIMessage
- `on_tool_start`: Tool execution begins (emits TOOL_START message)
- `on_tool_end`: Tool execution completes (emits TOOL_COMPLETE message)
- Frontend receives tool metadata for real-time UI updates

**State Persistence**:
- ToolMessage objects automatically checkpointed by LangGraph
- Full conversation history includes tool calls and results
- No special handling needed for tool persistence

### Adding New Tools

1. Create tool file in `backend/app/langgraph/tools/`
2. Define function with type hints and docstring:
   ```python
   def search_web(query: str) -> str:
       """Search the web for information."""
       # Implementation
       return "search results"
   ```
3. Export in `__init__.py`
4. Register in `streaming_chat_graph.py` tools list
5. Register in `call_llm.py` tools list

### Frontend Transparency

Tool executions display as cards inline with messages:
- Tool name badge with status indicator (running/completed)
- Final result display (no intermediate states)
- Blue border-left for visual distinction
- Green badge on completion
- Automatic cleanup on message completion

**Message Flow**:
1. User sends message requiring tool use
2. LLM decides to call tool (AIMessage with tool_calls)
3. Frontend receives TOOL_START (shows "Running..." badge)
4. ToolNode executes tool
5. Frontend receives TOOL_COMPLETE (shows result and "Completed" badge)
6. LLM generates final response incorporating tool result
7. Tool execution cards cleared on message completion

## MCP (Model Context Protocol) Integration

Genesis supports dynamic tool discovery and execution via MCP servers, extending the chatbot's capabilities beyond native Python tools without code changes.

### Architecture Decision

MCP integration lives in the **infrastructure layer** (like ChromaDBClient), **not as a domain port**, to maintain simplicity while following hexagonal principles. This avoids over-engineering for a cross-cutting infrastructure concern.

### Components

**MCPClientManager** (`backend/app/infrastructure/mcp/mcp_client_manager.py`):
- Singleton pattern for lifecycle management
- Connects to MCP servers during app startup
- Discovers tools from all configured servers
- Maintains persistent sessions for tool execution
- Graceful degradation on connection failures
- 10-second timeout per server to prevent hanging

**MCPToolAdapter** (`backend/app/langgraph/tools/mcp_adapter.py`):
- Wraps MCP tool definitions as Python callables
- Makes MCP tools compatible with LangChain's `bind_tools()`
- Provides `__name__` and `__doc__` properties for introspection
- Implements async `__call__` for tool execution via MCP session
- Namespace support to prevent tool name conflicts (e.g., `server:tool_name`)

**ToolRegistry** (`backend/app/langgraph/tool_metadata.py`):
- Tracks tool sources (local vs mcp) for frontend display
- Registers all tools at startup with metadata
- Used by WebSocket handler to include source in messages

**Configuration** (`backend/genesis_mcp.json`):
```json
[
  {
    "name": "fetch",
    "transport": "stdio",
    "command": "python",
    "args": ["-m", "mcp_server_fetch"],
    "env": {}
  }
]
```

### Tool Discovery Flow

```
1. App Startup
   ↓
2. MCPClientManager.initialize()
   ↓
3. For each server in genesis_mcp.json:
   - Connect via stdio/SSE transport (with 10s timeout)
   - Discover tools via MCP protocol
   - Convert to MCPToolAdapter instances
   - Register in ToolRegistry with source="mcp"
   ↓
4. Merge MCP tools + local tools
   ↓
5. Bind all tools to LLM provider
   ↓
6. Pass to ToolNode for execution
```

### Tool Execution Flow

```
1. LLM decides to call tool (AIMessage with tool_calls)
   ↓
2. ToolNode invokes tool by name
   ↓
3. If MCP tool:
   - MCPToolAdapter.__call__() invoked
   - Calls MCP server via persistent session
   - Returns result as string
   ↓
4. Result wrapped in ToolMessage
   ↓
5. Checkpointed by LangGraph
   ↓
6. Frontend displays with MCP badge (purple border)
```

### Frontend Distinction

MCP tools are visually distinguished from local tools:

**MCP Tools**:
- Purple left border (`border-l-purple-500`)
- Purple "MCP" badge
- Purple border on tool name badge

**Local Tools**:
- Blue left border (`border-l-blue-500`)
- No badge
- Standard blue border on tool name badge

### Configuration

**Environment Variables**:
- `MCP_ENABLED`: Enable/disable MCP support (default: false)
- `MCP_CONFIG_PATH`: Path to MCP config file (default: ./genesis_mcp.json)

**Docker Compose**:
```yaml
environment:
  - MCP_ENABLED=${MCP_ENABLED:-false}
  - MCP_CONFIG_PATH=${MCP_CONFIG_PATH:-./genesis_mcp.json}
```

### Supported Transports

1. **stdio**: Local process-based MCP servers
   - Command: `python`, `node`, or any executable
   - Args: Module name or script path
   - Environment: Custom env vars

2. **SSE (Server-Sent Events)**: Remote HTTP-based MCP servers
   - URL: HTTP(S) endpoint
   - Streaming: Persistent connection

### Error Handling

**Graceful Degradation**:
- MCP disabled → Application works with local tools only
- No config file → Application starts normally
- Server connection timeout (10s) → Skip that server, continue with others
- Server connection fails → Log error, continue with remaining servers
- Tool execution error → Return error message to LLM, don't crash

**Logging**:
- Server connection attempts logged at INFO level
- Tool discovery logged at INFO level
- Connection failures logged at ERROR level
- Tool execution logged at INFO level

### Lifecycle Management

**Startup** (`main.py:lifespan`):
```python
# After ChromaDB, before graph compilation
await MCPClientManager.initialize()
app.state.mcp_manager = MCPClientManager
```

**Shutdown** (`main.py:lifespan`):
```python
# During cleanup
if app.state.mcp_manager:
    await MCPClientManager.shutdown()
```

### Adding MCP Servers

1. Install MCP server: `pip install mcp-server-fetch`
2. Add to `backend/genesis_mcp.json`:
   ```json
   {
     "name": "fetch",
     "transport": "stdio",
     "command": "python",
     "args": ["-m", "mcp_server_fetch"]
   }
   ```
3. Enable MCP: `MCP_ENABLED=true` in `.env`
4. Restart application

No code changes required! Tools are automatically discovered and available.

### Benefits

- ✅ **Dynamic discovery**: Add tools via configuration, no code changes
- ✅ **Ecosystem access**: Leverage growing MCP server ecosystem
- ✅ **Environment-specific**: Different tools per dev/staging/production
- ✅ **Easy testing**: Swap between test and production servers
- ✅ **Graceful degradation**: Application works even if MCP unavailable
- ✅ **Visual distinction**: Frontend clearly shows MCP vs local tools

### Trade-offs

- Adds startup time (connection to MCP servers)
- Requires external MCP server processes/services
- Tool naming must be managed to avoid conflicts (via namespacing)
- MCP protocol is less mature than native Python tools

## Extension Points

The architecture makes it easy to add:

### RAG (Retrieval-Augmented Generation)
1. Create `IVectorStore` port
2. Implement vector database adapter
3. Add retrieval node to LangGraph
4. Update use cases

### ~~Tool Calling~~ ✅ IMPLEMENTED
See "Tool-Calling Architecture" section above for implementation details.

### Multi-modal Support
1. Extend `Message` model for images/audio
2. Update LLM providers for multi-modal models
3. Add file upload handling
4. Update frontend components

All extensions fit naturally without modifying core business logic.
