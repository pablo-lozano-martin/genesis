# LLM Integration Analysis: Migrate Onboarding Agent to `create_react_agent`

**Issue:** Migrate onboarding agent from hand-built ReAct pattern to LangGraph's prebuilt `create_react_agent`

**Analysis Date:** 2025-10-30

---

## Request Summary

Migrate the onboarding agent from a manually-constructed ReAct graph to using LangGraph's prebuilt `create_react_agent` function. This involves understanding:
- How the current LLM is configured and invoked in the onboarding flow
- The `call_llm` node's responsibility for LLM invocation
- System prompt injection patterns via the `inject_system_prompt` node
- Model configuration and provider selection for onboarding
- How responses are handled and tool calls are routed
- Message formatting and conversation history management
- Key differences between the hand-built and prebuilt approaches

---

## Relevant Files & Modules

### Core Onboarding Graph Files
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/onboarding_graph.py` - Current hand-built ReAct graph implementation
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/call_llm.py` - LLM invocation node that calls provider and binds tools
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/prompts/onboarding_prompts.py` - System prompt with onboarding-specific guidance

### LLM Provider Integration
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/llm_provider.py` - Abstract `ILLMProvider` port interface (Hexagonal Architecture)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/provider_factory.py` - Factory for creating provider instances (OpenAI, Anthropic, Gemini, Ollama)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/openai_provider.py` - OpenAI provider implementation with `bind_tools()` method
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/anthropic_provider.py` - Anthropic provider implementation

### Onboarding-Specific Tools
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/read_data.py` - Tool to query collected onboarding fields from state
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/write_data.py` - Tool to write validated onboarding data to state (with Pydantic validation)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/export_data.py` - Tool to export finalized onboarding data and generate LLM summary
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/rag_search.py` - Tool to search Orbio knowledge base via RAG

### State Management
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/state.py` - `ConversationState` class extending `MessagesState` with onboarding-specific fields

### Graph Initialization & Configuration
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/main.py` - Application lifespan: graph compilation with checkpointer and tools (lines 112-117)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_router.py` - WebSocket endpoint for onboarding that retrieves graph from app state
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py` - Streaming handler that creates `RunnableConfig` with `llm_provider`, `thread_id`, and `tools` (lines 125-133)

### Configuration
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/config/settings.py` - Settings with `llm_provider` selection and provider-specific API keys/models (lines 45-62)

### Comparison Reference
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/chat_graph.py` - Similar hand-built ReAct graph (chat conversation)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/streaming_chat_graph.py` - Another hand-built ReAct graph with streaming support

### Tests
- `/Users/pablolozano/Mac Projects August/genesis/backend/tests/integration/test_onboarding_graph_workflow.py` - Integration tests validating system prompt injection, tool orchestration, and state persistence
- `/Users/pablolozano/Mac Projects August/genesis/backend/tests/unit/test_onboarding_graph_nodes.py` - Unit tests for individual graph nodes

---

## Current Integration Overview

### Architecture Pattern: Hexagonal Architecture with LangGraph-First Design

The system uses a **hexagonal (ports & adapters) architecture** where:
- **Port:** `ILLMProvider` interface (abstract contract) defines LLM operations
- **Adapters:** Provider implementations (OpenAI, Anthropic, Gemini, Ollama) satisfy the port
- **LangGraph:** Graphs are the primary orchestration layer, not controllers

### Provider Abstraction Layer

**Port Interface (`ILLMProvider`):**
Located at `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/llm_provider.py`

```python
class ILLMProvider(ABC):
    @abstractmethod
    async def generate(self, messages: List[BaseMessage]) -> BaseMessage:
        """Generate response from LLM based on conversation history"""

    @abstractmethod
    async def stream(self, messages: List[BaseMessage]) -> AsyncGenerator[str, None]:
        """Stream token-by-token responses"""

    @abstractmethod
    async def get_model_name(self) -> str:
        """Get the current model name"""

    @abstractmethod
    def bind_tools(self, tools: List[Callable], **kwargs: Any) -> 'ILLMProvider':
        """Bind tools to provider for tool calling"""
```

**Key Design Principle:** All providers implement the same interface, supporting seamless switching via `llm_provider` setting in `.env` (values: "openai", "anthropic", "gemini", "ollama").

### Provider Implementations

**OpenAI Provider** (`openai_provider.py`):
- Wraps `ChatOpenAI` from langchain_openai
- Configures: model name, API key, temperature=0.7, streaming=True
- `bind_tools()` method returns new provider instance with bound tools

**Anthropic Provider** (`anthropic_provider.py`):
- Wraps `ChatAnthropic` from langchain_anthropic
- Same interface implementation as OpenAI
- Supports Claude models

Both providers:
- Use LangChain's `ainvoke()` for async generation
- Use `astream()` for token streaming
- Return LangChain `BaseMessage` types (AIMessage with optional tool_calls)

### Current Hand-Built ReAct Implementation

**Graph Structure** (`onboarding_graph.py` lines 45-99):

```
START
  ↓
process_input (validate messages exist)
  ↓
inject_system_prompt (prepend system message if not present)
  ↓
call_llm (invoke LLM with tools bound)
  ↓
tools_condition routing:
  ├─→ ToolNode (execute tool calls)
  │    ↓
  │   call_llm (loop back for next reasoning step)
  │    ↓
  └─→ (no tool calls) END
```

**Key Graph Nodes:**

1. **`process_user_input`** (`process_input.py`):
   - Validates that messages list exists in state
   - No modification, purely validation
   - Returns empty dict (no state update)

2. **`inject_system_prompt`** (`onboarding_graph.py` lines 18-42):
   - Checks if first message is `SystemMessage`
   - If not, prepends `ONBOARDING_SYSTEM_PROMPT`
   - Uses LangGraph's `MessagesState` message reducer (auto-prepend behavior)
   - Returns `{"messages": [system_message]}` or `{}` (no update if already present)
   - **Critical:** System prompt is injected EVERY call if not present (ensures role consistency)

3. **`call_llm`** (`call_llm.py` lines 17-74):
   - **Retrieves LLM provider** from `config["configurable"]["llm_provider"]` (passed via RunnableConfig)
   - **Gets tools** from `config["configurable"]["tools"]` (specialized tools for onboarding)
   - **Binds tools** to provider: `llm_provider.bind_tools(all_tools, parallel_tool_calls=False)`
   - **Invokes LLM** with entire message history: `await llm_provider_with_tools.generate(messages)`
   - Returns `{"messages": [ai_message]}` where `ai_message` may include `tool_calls`

4. **`ToolNode`** (prebuilt from LangGraph):
   - Executes tool calls based on AIMessage.tool_calls
   - Returns `ToolMessage` objects for each tool result
   - Messages are appended to state via `MessagesState` reducer

### Message Flow & Conversation History

**State Type:** `ConversationState` extends LangGraph's `MessagesState`

```python
class ConversationState(MessagesState):
    messages: List[BaseMessage]  # Auto-managed by MessagesState with add_messages reducer
    conversation_id: str
    user_id: str
    # Onboarding fields
    employee_name: Optional[str]
    employee_id: Optional[str]
    starter_kit: Optional[str]
    dietary_restrictions: Optional[str]
    meeting_scheduled: Optional[bool]
    conversation_summary: Optional[str]
```

**Message Management:**
- Messages use LangChain `BaseMessage` types: `HumanMessage`, `AIMessage`, `SystemMessage`, `ToolMessage`
- `MessagesState` automatically manages message append via `add_messages` reducer
- System prompt is injected as `SystemMessage` at position 0
- Tool calls and results are managed automatically

### LLM Invocation Configuration

**Configuration Path:**

1. **Application Startup** (`main.py` lines 112-117):
   ```python
   onboarding_tools = [read_data, write_data, rag_search, export_data]
   app.state.onboarding_graph = create_onboarding_graph(checkpointer, onboarding_tools)
   ```

2. **WebSocket Handler** (`websocket_handler.py` lines 125-133):
   ```python
   config = RunnableConfig(
       configurable={
           "thread_id": conversation.id,
           "llm_provider": llm_provider,  # Instance of ILLMProvider
           "user_id": user.id,
           "tools": tools  # Passed from graph._tools metadata
       }
   )
   ```

3. **LLM Provider Selection** (`provider_factory.py`):
   - Factory creates provider based on `settings.llm_provider` (env var)
   - Supported: "openai", "anthropic", "gemini", "ollama"
   - All providers implement `ILLMProvider` interface

### System Prompt Injection Pattern

**File:** `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/prompts/onboarding_prompts.py`

```python
ONBOARDING_SYSTEM_PROMPT = """You are an onboarding assistant for Orbio. Your role is to guide new employees through the onboarding process in a friendly, conversational way.

**Your responsibilities:**
1. Collect required information: employee_name, employee_id, starter_kit (mouse/keyboard/backpack)
2. Optionally collect: dietary_restrictions, meeting_scheduled
3. Answer user questions about Orbio using the rag_search tool
4. Complete onboarding by calling export_data tool (THE ONLY WAY TO FINALIZE)

**Tools available:**
- read_data: Check what fields have been collected
- write_data: Save collected data (handles validation)
- rag_search: Answer questions about Orbio policies/benefits
- export_data: CALL THIS to complete onboarding (do NOT use rag_search or write_data for finalization)

[... conversation flow and critical instructions ...]
"""
```

**Injection Mechanism** (`inject_system_prompt` node):
- Prepends system message before `call_llm` is invoked
- Ensures LLM has context for entire conversation (role, tools, responsibilities)
- Only injected once (checked on each call, skipped if already present)

### Request/Response Handling

**Request Format:**
- WebSocket client sends: `{"type": "message", "conversation_id": "...", "content": "..."}`
- Handler creates: `HumanMessage(content=client_message.content)`
- Graph receives: `{"messages": [HumanMessage(...)]}`

**Response Handling** (`websocket_handler.py` lines 154-220):
- Graph streams events via `graph.astream_events(input_data, config, version="v2")`
- Event types tracked:
  - `on_chat_model_stream`: LLM token chunks (streamed to client as "token" messages)
  - `on_chat_model_end`: End of LLM response (cached tool call info)
  - `on_tool_start`: Tool execution begins (emit "tool_start" to client)
  - `on_tool_end`: Tool execution completes (emit "tool_complete" to client)

**Tool Call Management:**
- AIMessage includes `tool_calls` list (parallel_tool_calls=False, so only one tool per call)
- ToolNode executes tools and returns ToolMessage results
- Graph loops back to `call_llm` until no more tool calls

### Tools Available in Onboarding Graph

**Tools passed to graph** (`main.py` line 113):
```python
onboarding_tools = [read_data, write_data, rag_search, export_data]
```

Each tool receives the `ConversationState` as first parameter (LangGraph tool pattern):

1. **`read_data(state, field_names=None)`** - Query collected fields
2. **`write_data(state, field_name, value, comments=None)`** - Write validated data
3. **`rag_search(state, query)`** - Search knowledge base (similar to chat graphs)
4. **`export_data(state, confirmation_message=None)`** - Export and generate summary

All tools return dictionaries with `{"status": "success"/"error", ...}` format.

### Streaming & Event Handling

**Streaming Architecture:**
- Graph compiled with checkpointer (automatic state persistence)
- WebSocket handler uses `graph.astream_events()` for token-level streaming
- Events are typed and handled individually
- Streaming bypasses the need for manual message formatting

---

## Impact Analysis: Migrating to `create_react_agent`

### What `create_react_agent` Provides

**LangGraph Prebuilt Function:**
```python
from langgraph.prebuilt import create_react_agent

agent = create_react_agent(
    model,              # LangChain ChatModel instance
    tools,              # List of callable tools
    prompt=None,        # Optional system prompt (string or MessageTemplate)
    checkpointer=None   # Optional state persistence
)
```

**Key Built-In Behavior:**
- Automatically creates agent nodes for reasoning (LLM invocation) and acting (tool execution)
- Implements ReAct loop: Reason → Act → Repeat until no tool calls
- Handles message formatting internally
- Returns compiled graph ready for invocation with `graph.invoke()` or `graph.astream_events()`
- Supports optional prompt injection via `prompt` parameter

### Critical Differences from Hand-Built Approach

| Aspect | Hand-Built (Current) | `create_react_agent` |
|--------|----------------------|---------------------|
| **Graph Creation** | Manual `StateGraph` with nodes | Prebuilt factory function |
| **Tool Binding** | Done in `call_llm` node at runtime | Done at agent creation time |
| **LLM Model** | Passed via `RunnableConfig.configurable["llm_provider"]` | Passed directly to function |
| **Prompt Injection** | Separate `inject_system_prompt` node | `prompt` parameter to function |
| **Message Management** | Custom node implementation | Built-in handling |
| **Streaming Events** | `graph.astream_events()` works with custom nodes | Same interface works |
| **Checkpointing** | Passed to `compile(checkpointer=...)` | Passed to `create_react_agent(checkpointer=...)` |
| **Provider Abstraction** | ILLMProvider interface required | Expects LangChain ChatModel (must adapt) |

### Key Migration Challenges

#### Challenge 1: Provider Abstraction vs LangChain ChatModel

**Current:** Graph receives `ILLMProvider` instances via config, which wraps LangChain models

**Problem:** `create_react_agent` expects a LangChain `ChatModel` instance directly, not a custom provider interface

**Solution:** Must bridge the gap by either:
1. **Option A (Recommended):** Pass the underlying LangChain model (`provider.model`) to `create_react_agent`
   - Loses provider abstraction at this point
   - Requires refactoring `ILLMProvider` to expose underlying model
   - Simplest migration path

2. **Option B (Complex):** Create an adapter that wraps `ILLMProvider` as a LangChain `ChatModel`
   - Preserves provider abstraction throughout
   - Requires implementing all `ChatModel` abstract methods
   - More maintenance burden

**Recommended:** Option A with abstraction maintained at WebSocket handler level (model is still selected by `llm_provider` setting)

#### Challenge 2: Dynamic Tool Configuration

**Current:** Tools are passed to graph creation AND via `RunnableConfig.configurable["tools"]` at runtime

**Problem:** `create_react_agent` binds tools at creation time, not at invocation time

**Current Onboarding Tools Logic:**
- Onboarding graph uses specific tools: `[read_data, write_data, rag_search, export_data]`
- Chat graphs use different tools: `[multiply, add, rag_search, read_data, write_data]`
- Both are created at startup with these tools

**Impact:** No challenge here - tools can be passed to `create_react_agent` at creation time

#### Challenge 3: System Prompt Management

**Current:** `inject_system_prompt` node prepends system message before LLM invocation

**Problem:** `create_react_agent` accepts `prompt` parameter but handles injection internally

**Solutions:**
1. Pass `prompt=ONBOARDING_SYSTEM_PROMPT` to `create_react_agent` (String treated as system message)
2. Use `prompt=[SystemMessage(content=ONBOARDING_SYSTEM_PROMPT), ...]` for template control
3. Remove `inject_system_prompt` node entirely - let prebuilt handle it

**Recommendation:** Use prebuilt's prompt mechanism, remove `inject_system_prompt` node

#### Challenge 4: RunnableConfig Configuration Pattern

**Current:** WebSocket handler passes `llm_provider`, `thread_id`, `user_id`, `tools` via config

**Prebuilt Behavior:** `create_react_agent` doesn't use `configurable["tools"]` or `configurable["llm_provider"]`

**Solution:**
- Keep `thread_id` and `user_id` in config (graph still needs them for state management)
- Remove `llm_provider` and `tools` from config - they're fixed at graph creation
- Modify graph creation to accept LLM provider as parameter

---

## LLM Integration Recommendations

### Recommended Migration Strategy

**Goal:** Migrate to `create_react_agent` while maintaining provider abstraction and configuration flexibility

### Phase 1: Adapt Provider Interface for LangChain Model Exposure

**File:** `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/llm_provider.py`

**Change:** Add method to expose underlying LangChain model
```python
class ILLMProvider(ABC):
    # ... existing methods ...

    @abstractmethod
    def get_model(self) -> ChatModel:
        """
        Get the underlying LangChain ChatModel instance.

        Used by LangGraph prebuilt agents that expect native LangChain models.

        Returns:
            Underlying ChatModel (ChatOpenAI, ChatAnthropic, etc.)
        """
        pass
```

**Implementation in OpenAI Provider:**
```python
def get_model(self) -> ChatModel:
    """Return the underlying ChatOpenAI model."""
    return self.model
```

**Same for Anthropic, Gemini, Ollama providers.**

### Phase 2: Create New Graph Factory for `create_react_agent`

**File:** Create `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/onboarding_graph_prebuilt.py`

**Structure:**
```python
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage
from typing import Optional, List, Callable
from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver
from app.langgraph.prompts.onboarding_prompts import ONBOARDING_SYSTEM_PROMPT
from app.langgraph.tools import read_data, write_data, rag_search, export_data
from app.core.ports.llm_provider import ILLMProvider
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)

def create_onboarding_graph_prebuilt(
    llm_provider: ILLMProvider,
    checkpointer: AsyncMongoDBSaver,
    tools: Optional[List[Callable]] = None
):
    """
    Create onboarding graph using LangGraph's prebuilt create_react_agent.

    Advantages over hand-built approach:
    - Simpler implementation: fewer nodes, less boilerplate
    - Automatically handles ReAct loop (reason → act → repeat)
    - Prompt injection built-in
    - Streaming support maintained via astream_events()

    Args:
        llm_provider: ILLMProvider instance (provider abstraction)
        checkpointer: AsyncMongoDBSaver for state persistence
        tools: Optional list of tools (defaults to onboarding tools)

    Returns:
        Compiled LangGraph agent ready for invocation
    """
    if tools is None:
        tools = [read_data, write_data, rag_search, export_data]

    # Get underlying LangChain model from provider abstraction
    model = llm_provider.get_model()

    # Create system prompt (string is automatically treated as system message)
    prompt = ONBOARDING_SYSTEM_PROMPT

    # Create prebuilt agent with built-in ReAct loop
    agent = create_react_agent(
        model=model,
        tools=tools,
        prompt=prompt,
        checkpointer=checkpointer
    )

    logger.info("Onboarding graph created with create_react_agent")
    return agent
```

### Phase 3: Update Application Startup

**File:** `/Users/pablolozano/Mac Projects August/genesis/backend/app/main.py`

**Current Code (lines 112-117):**
```python
onboarding_tools = [read_data, write_data, rag_search, export_data]
app.state.onboarding_graph = create_onboarding_graph(checkpointer, onboarding_tools)
```

**Updated Code:**
```python
# Get default LLM provider for graph initialization
from app.adapters.outbound.llm_providers.provider_factory import get_llm_provider
llm_provider = get_llm_provider()

# Create graphs with new prebuilt agent
from app.langgraph.graphs.onboarding_graph_prebuilt import create_onboarding_graph_prebuilt
onboarding_tools = [read_data, write_data, rag_search, export_data]
app.state.onboarding_graph = create_onboarding_graph_prebuilt(
    llm_provider,
    checkpointer,
    onboarding_tools
)
```

**Note:** Provider is selected at startup via `settings.llm_provider` (env var), so same provider is used throughout application lifetime. To support runtime provider switching, see Alternative Approach below.

### Phase 4: Update WebSocket Handler Configuration

**File:** `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py`

**Current Code (lines 125-133):**
```python
config = RunnableConfig(
    configurable={
        "thread_id": conversation.id,
        "llm_provider": llm_provider,
        "user_id": user.id,
        "tools": tools
    }
)
```

**Updated Code:**
```python
config = RunnableConfig(
    configurable={
        "thread_id": conversation.id,
        "user_id": user.id
        # Removed: llm_provider, tools (fixed at graph creation time)
    }
)
```

**Rationale:** `create_react_agent` binds model and tools at creation time, so they don't need to be passed via config.

### Phase 5: Remove Hand-Built Nodes

**Actions:**
1. Delete or archive `inject_system_prompt` node (handled by prebuilt)
2. Delete or archive `call_llm` node (replaced by prebuilt's agent node)
3. Keep `process_user_input` only if needed for validation (can be removed if prebuilt handles input validation)

**Impact:** Graph complexity significantly reduced:
- From 4 nodes (process_input, inject_system_prompt, call_llm, tools) to 1 prebuilt agent
- Fewer state transitions, simpler testing

### Phase 6: Update Tests

**Files affected:**
- `/Users/pablolozano/Mac Projects August/genesis/backend/tests/integration/test_onboarding_graph_workflow.py`
- `/Users/pablolozano/Mac Projects August/genesis/backend/tests/unit/test_onboarding_graph_nodes.py`

**Test Updates:**
```python
from app.langgraph.graphs.onboarding_graph_prebuilt import create_onboarding_graph_prebuilt

async def test_onboarding_system_prompt_injected():
    """Verify prebuilt agent includes system prompt in model invocation."""
    # Create mock provider with real system prompt
    mock_provider = AsyncMock(spec=ILLMProvider)
    mock_model = AsyncMock()  # LangChain ChatModel mock
    mock_provider.get_model.return_value = mock_model

    # create_react_agent will call model with system prompt prepended
    # Test that system prompt is included in message history
    ...
```

---

## Proposed Interfaces

### 1. Enhanced ILLMProvider Interface

**Location:** `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/llm_provider.py`

**Addition:**
```python
from langchain_core.language_model import LanguageModel

class ILLMProvider(ABC):
    # ... existing methods ...

    @abstractmethod
    def get_model(self) -> LanguageModel:
        """Get underlying LangChain model for use with LangGraph prebuilt agents."""
        pass
```

**Rationale:** Allows provider abstraction to coexist with LangGraph's requirement for LangChain models

### 2. Graph Factory Pattern

**Location:** New file `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/onboarding_graph_prebuilt.py`

**Function Signature:**
```python
def create_onboarding_graph_prebuilt(
    llm_provider: ILLMProvider,
    checkpointer: AsyncMongoDBSaver,
    tools: Optional[List[Callable]] = None
) -> CompiledGraph:
    """Create onboarding agent using prebuilt create_react_agent."""
```

**Rationale:** Encapsulates prebuilt graph creation with consistent interface

---

## Configuration Changes

### Environment Variables (No Changes Required)

**File:** `.env` (or `docker-compose.yml`)

```env
LLM_PROVIDER=anthropic  # or openai, gemini, ollama
ANTHROPIC_API_KEY=...
ANTHROPIC_MODEL=claude-3-sonnet-20240229
```

**Behavior:** Same as before - provider selection is environment-driven

### Application Startup Configuration

**File:** `/Users/pablolozano/Mac Projects August/genesis/backend/app/main.py` (lifespan function)

**Change:** Initialize LLM provider before graph creation

```python
from app.adapters.outbound.llm_providers.provider_factory import get_llm_provider
from app.langgraph.graphs.onboarding_graph_prebuilt import create_onboarding_graph_prebuilt

# During startup
llm_provider = get_llm_provider()
app.state.onboarding_graph = create_onboarding_graph_prebuilt(llm_provider, checkpointer)
```

### RunnableConfig Changes

**WebSocket Handler:** Simplify config by removing provider and tools

```python
# Before
config = RunnableConfig(
    configurable={
        "thread_id": conversation.id,
        "llm_provider": llm_provider,
        "user_id": user.id,
        "tools": tools
    }
)

# After
config = RunnableConfig(
    configurable={
        "thread_id": conversation.id,
        "user_id": user.id
    }
)
```

---

## Data Flow

### Current Hand-Built Approach

```
WebSocket Input
  ↓
WebSocket Handler
  ├─ Create HumanMessage
  ├─ Create RunnableConfig:
  │  ├─ thread_id (for checkpointing)
  │  ├─ llm_provider (ILLMProvider instance)
  │  ├─ user_id
  │  └─ tools (onboarding-specific tools)
  ↓
Graph.astream_events(input_data, config)
  ├─ START → process_input
  ├─ process_input → inject_system_prompt
  │  └─ Prepends SystemMessage(ONBOARDING_SYSTEM_PROMPT)
  ├─ inject_system_prompt → call_llm
  │  ├─ Get llm_provider from config
  │  ├─ Get tools from config
  │  ├─ Bind tools: provider.bind_tools(tools)
  │  ├─ Invoke: llm_provider.generate(messages)
  │  └─ Return AIMessage (may include tool_calls)
  ├─ tools_condition routes:
  │  ├─ If tool_calls: ToolNode → call_llm (loop)
  │  └─ If no tool_calls: END
  ↓
Event Stream
  ├─ on_chat_model_stream: LLM tokens → Token messages
  ├─ on_chat_model_end: Cache tool calls
  ├─ on_tool_start: Emit tool start event
  ├─ on_tool_end: Emit tool complete event
  ↓
WebSocket Output
```

### New Prebuilt Approach

```
WebSocket Input
  ↓
WebSocket Handler
  ├─ Create HumanMessage
  ├─ Create RunnableConfig:
  │  ├─ thread_id (for checkpointing)
  │  └─ user_id
  │     (Note: llm_provider and tools not needed - fixed at graph creation)
  ↓
Graph.astream_events(input_data, config)
  ├─ START → prebuilt agent node
  │  ├─ (Internally: system prompt prepended)
  │  ├─ (Internally: tools bound to model)
  │  ├─ Invoke LLM with full message history
  │  └─ Return AIMessage (may include tool_calls)
  ├─ ReAct loop (internal to prebuilt):
  │  ├─ If tool_calls: Execute tools → ToolMessage
  │  ├─ Append ToolMessage to history
  │  ├─ Loop back to agent node
  │  └─ If no tool_calls: END
  ↓
Event Stream
  ├─ Same event types as before
  ├─ on_chat_model_stream: LLM tokens → Token messages
  ├─ on_chat_model_end: Cache tool calls
  ├─ on_tool_start: Emit tool start event
  ├─ on_tool_end: Emit tool complete event
  ↓
WebSocket Output
```

**Key Differences:**
- Fewer intermediate nodes (system prompt and tool binding are internal)
- Simpler graph structure (prebuilt handles ReAct loop)
- Event handling at WebSocket layer is unchanged (same astream_events interface)
- Message flow is identical to user (no changes needed in frontend)

---

## Implementation Guidance

### Step-by-Step Approach

#### Step 1: Add `get_model()` Method to ILLMProvider

**File:** `backend/app/core/ports/llm_provider.py`

1. Add abstract method to interface
2. Implement in all provider adapters (OpenAI, Anthropic, Gemini, Ollama)
3. Return the underlying LangChain model instance

**Verification:**
```python
provider = get_llm_provider()
model = provider.get_model()
assert hasattr(model, 'ainvoke')  # Ensure it's a valid LangChain model
```

#### Step 2: Create New Prebuilt Graph Factory

**File:** `backend/app/langgraph/graphs/onboarding_graph_prebuilt.py`

1. Import `create_react_agent` from `langgraph.prebuilt`
2. Create function that accepts `llm_provider`, `checkpointer`, `tools`
3. Extract model: `model = llm_provider.get_model()`
4. Call prebuilt factory: `agent = create_react_agent(model, tools, prompt, checkpointer)`
5. Return compiled agent

**Testing:**
```python
from app.adapters.outbound.llm_providers.provider_factory import get_llm_provider
provider = get_llm_provider()
agent = create_onboarding_graph_prebuilt(provider, checkpointer)
assert hasattr(agent, 'invoke')
assert hasattr(agent, 'astream_events')
```

#### Step 3: Update Application Startup

**File:** `backend/app/main.py` (lifespan function)

1. Import new factory: `from app.langgraph.graphs.onboarding_graph_prebuilt import create_onboarding_graph_prebuilt`
2. Create LLM provider: `llm_provider = get_llm_provider()`
3. Replace graph creation:
   ```python
   # OLD
   app.state.onboarding_graph = create_onboarding_graph(checkpointer, onboarding_tools)

   # NEW
   app.state.onboarding_graph = create_onboarding_graph_prebuilt(
       llm_provider,
       checkpointer,
       onboarding_tools
   )
   ```

#### Step 4: Update WebSocket Handler

**File:** `backend/app/adapters/inbound/websocket_handler.py`

1. Remove `llm_provider` and `tools` from config:
   ```python
   # OLD
   config = RunnableConfig(
       configurable={
           "thread_id": conversation.id,
           "llm_provider": llm_provider,
           "user_id": user.id,
           "tools": tools
       }
   )

   # NEW
   config = RunnableConfig(
       configurable={
           "thread_id": conversation.id,
           "user_id": user.id
       }
   )
   ```

#### Step 5: Clean Up Old Implementation

1. Archive or delete `inject_system_prompt` node function
2. Delete `call_llm` node if not used by other graphs
3. Consider removing `process_user_input` if prebuilt validates input
4. Keep `onboarding_graph.py` but mark as deprecated if keeping multiple versions

#### Step 6: Update Tests

1. Update imports to use new prebuilt factory
2. Adjust test setup to pass `llm_provider` to graph creation
3. Verify system prompt is included (prebuilt does this internally)
4. Verify tool calls are routed correctly (prebuilt handles this)
5. Verify streaming events work (astream_events interface unchanged)

**Test Template:**
```python
async def test_onboarding_prebuilt_system_prompt():
    """Verify system prompt is included in prebuilt agent."""
    provider = get_llm_provider()
    graph = create_onboarding_graph_prebuilt(provider, checkpointer, tools)

    result = await graph.ainvoke(
        {"messages": [HumanMessage(content="Hello")]},
        RunnableConfig(configurable={"thread_id": "test-123"})
    )

    # System prompt should be first message
    assert isinstance(result["messages"][0], SystemMessage)
    assert "onboarding assistant" in result["messages"][0].content.lower()
```

---

## Risks and Considerations

### Risk 1: Provider Abstraction Boundary

**Issue:** `create_react_agent` requires LangChain `ChatModel`, not our `ILLMProvider`

**Impact:** Slight erosion of provider abstraction at graph creation point

**Mitigation:**
- Keep abstraction at WebSocket handler level (provider selection still via config)
- Document that LLM model is bound at startup, not runtime
- If runtime provider switching needed, must recreate graph

**Acceptable Risk Level:** LOW - Provider selection remains environment-driven

### Risk 2: Prompt Immutability

**Issue:** System prompt is bound at graph creation time, not injected per-request

**Impact:** Cannot change system prompt between requests without recreating graph

**Mitigation:**
- Onboarding system prompt is stable (no per-user customization)
- If customization needed, implement custom prompt template in prebuilt's `prompt` parameter
- Could support custom prompts via graph factory parameter

**Acceptable Risk Level:** LOW - Current use case doesn't require dynamic prompts

### Risk 3: Tool Binding at Creation Time

**Issue:** Tools are bound at graph creation, not request time

**Impact:** Cannot add/remove tools dynamically per-request (current implementation also has this limitation)

**Mitigation:**
- Onboarding tools are fixed: [read_data, write_data, rag_search, export_data]
- This matches current startup behavior
- Tools already specified in main.py before graph creation

**Acceptable Risk Level:** NONE - Matches current behavior

### Risk 4: Message History Growth

**Issue:** System prompt is prepended by prebuilt, plus conversation grows with tool calls

**Impact:** Longer message histories could increase LLM API costs (token counts)

**Mitigation:**
- Same as current implementation (MessagesState already manages this)
- Message management is identical between approaches
- Consider future message summarization if history becomes too long

**Acceptable Risk Level:** LOW - No change from current behavior

### Rate Limiting & Cost Implications

**OpenAI:**
- No change in API calls (same LLM invocations)
- Slightly fewer intermediate requests (no separate prompt injection call)
- Cost same or slightly lower

**Anthropic:**
- Same API call pattern
- Tool calls routed same way
- Cost identical

**Other Providers:**
- Behavior depends on underlying ChatModel implementation
- Prebuilt abstraction ensures compatibility

**Recommendation:** Monitor token usage in logs before/after migration

### Testing Considerations

**What Changes:**
- Node-level unit tests for `call_llm` and `inject_system_prompt` won't apply
- Integration tests must verify prebuilt behavior instead

**What Stays Same:**
- Graph invocation interface (ainvoke, astream_events)
- Message types and flow
- Tool execution and routing
- Checkpointing behavior
- WebSocket event streaming

---

## Testing Strategy

### Unit Tests

**Test 1: Provider Model Exposure**
```python
def test_provider_exposes_langchain_model():
    """Verify all providers implement get_model()."""
    for provider_name in ["openai", "anthropic", "gemini", "ollama"]:
        provider = create_provider_by_name(provider_name)
        model = provider.get_model()
        assert hasattr(model, 'ainvoke')
        assert hasattr(model, 'astream')
```

**Test 2: Graph Factory Signature**
```python
async def test_prebuilt_graph_factory_creates_runnable():
    """Verify prebuilt graph factory returns valid LangGraph."""
    provider = get_llm_provider()
    graph = create_onboarding_graph_prebuilt(provider, checkpointer)

    assert hasattr(graph, 'invoke')
    assert hasattr(graph, 'ainvoke')
    assert hasattr(graph, 'astream_events')
```

### Integration Tests

**Test 1: System Prompt Included**
```python
async def test_system_prompt_in_prebuilt_agent():
    """Verify system prompt is included without separate node."""
    provider = get_llm_provider()
    graph = create_onboarding_graph_prebuilt(provider, checkpointer, tools)

    input_data = {
        "messages": [HumanMessage(content="Hello")],
        "conversation_id": "test-123",
        "user_id": "user-456"
    }
    config = RunnableConfig(configurable={"thread_id": "test-123"})

    result = await graph.ainvoke(input_data, config)

    # Check system message exists
    system_msgs = [m for m in result["messages"] if isinstance(m, SystemMessage)]
    assert len(system_msgs) > 0
    assert "onboarding" in system_msgs[0].content.lower()
```

**Test 2: Tool Execution in Loop**
```python
async def test_prebuilt_tool_loop():
    """Verify prebuilt handles multi-turn tool calls."""
    provider = get_llm_provider()
    graph = create_onboarding_graph_prebuilt(provider, checkpointer, tools)

    # Mock LLM to return tool calls on first invocation, text on second
    mock_messages = [
        AIMessage(content="", tool_calls=[{"name": "read_data", "args": {}}]),
        AIMessage(content="All data collected!")
    ]

    # Run graph and verify tools were executed
    # (tool node should execute read_data and append ToolMessage)
```

**Test 3: Streaming Events**
```python
async def test_prebuilt_astream_events():
    """Verify streaming events work with prebuilt agent."""
    provider = get_llm_provider()
    graph = create_onboarding_graph_prebuilt(provider, checkpointer, tools)

    input_data = {
        "messages": [HumanMessage(content="Hello")],
        "conversation_id": "test-123",
        "user_id": "user-456"
    }
    config = RunnableConfig(configurable={"thread_id": "test-123"})

    event_types = []
    async for event in graph.astream_events(input_data, config, version="v2"):
        event_types.append(event["event"])

    # Verify expected event types
    assert "on_chat_model_stream" in event_types
    assert "on_chat_model_end" in event_types
```

### End-to-End Tests

**Test 1: Full Onboarding Flow**
```python
async def test_full_onboarding_with_prebuilt():
    """Test complete onboarding flow: collect data → export."""
    # Start with empty state
    # Send messages to guide onboarding
    # Verify export_data tool is called at end
    # Verify JSON file created
```

**Test 2: WebSocket Integration**
```python
async def test_websocket_with_prebuilt_graph():
    """Test WebSocket streaming with prebuilt agent."""
    # Connect WebSocket
    # Send message
    # Verify token events streamed
    # Verify tool events streamed
    # Verify completion event
```

### Backward Compatibility

**Requirement:** No breaking changes to WebSocket protocol

- Client sends: `{"type": "message", "conversation_id": "...", "content": "..."}`
- Server still sends: token, tool_start, tool_complete, complete events
- Event format unchanged
- No changes to frontend code needed

**Testing:** Run WebSocket tests against both old and new implementations, verify identical event streams

---

## Alternative Approach: Runtime Provider Switching

**Scenario:** If application needs to support switching LLM providers at runtime (not startup)

**Limitation:** `create_react_agent` binds model at creation time

**Solution:** Keep hand-built approach but simplify:

```python
def create_onboarding_graph(
    checkpointer: AsyncMongoDBSaver,
    tools: Optional[List[Callable]] = None
):
    """
    Simplified hand-built graph that accepts provider via config.

    Allows runtime provider switching without recreating graph.
    """
    graph_builder = StateGraph(ConversationState)

    # Single agent node that gets provider from config at runtime
    async def agent(state: ConversationState, config: RunnableConfig) -> dict:
        provider = config["configurable"]["llm_provider"]
        model = provider.get_model()
        messages = state["messages"]

        # Bind tools and invoke
        model_with_tools = model.bind_tools(tools)
        response = await model_with_tools.ainvoke(messages)

        return {"messages": [response]}

    # ... rest of graph ...
```

This keeps provider abstraction without prebuilt, but also loses prebuilt benefits. **Not recommended** unless runtime provider switching is required.

---

## Summary of Changes

### Files to Modify
1. **`app/core/ports/llm_provider.py`** - Add `get_model()` method to interface
2. **`app/adapters/outbound/llm_providers/openai_provider.py`** - Implement `get_model()`
3. **`app/adapters/outbound/llm_providers/anthropic_provider.py`** - Implement `get_model()`
4. **`app/adapters/outbound/llm_providers/gemini_provider.py`** - Implement `get_model()`
5. **`app/adapters/outbound/llm_providers/ollama_provider.py`** - Implement `get_model()`
6. **`app/main.py`** - Update graph creation to use prebuilt factory
7. **`app/adapters/inbound/websocket_handler.py`** - Simplify RunnableConfig

### Files to Create
1. **`app/langgraph/graphs/onboarding_graph_prebuilt.py`** - New prebuilt graph factory

### Files to Remove/Archive
1. **`app/langgraph/nodes/call_llm.py`** - Replaced by prebuilt
2. **`app/langgraph/graphs/onboarding_graph.py`** - Keep old version in archive/deprecated

### Tests to Update
1. **`tests/integration/test_onboarding_graph_workflow.py`** - Update to use prebuilt factory
2. **`tests/unit/test_onboarding_graph_nodes.py`** - Remove node-level tests for deleted nodes

---

## Key Takeaways

### What Stays the Same
- System prompt content and guidance (ONBOARDING_SYSTEM_PROMPT)
- Onboarding tools (read_data, write_data, rag_search, export_data)
- WebSocket streaming interface and events
- Provider abstraction at configuration level
- State management and checkpointing
- Message history and conversation persistence

### What Changes
- Graph construction: manual nodes → prebuilt factory
- LLM invocation: custom `call_llm` node → prebuilt agent node
- System prompt injection: separate node → built-in to prebuilt
- Tool binding: per-request in config → at graph creation
- Code complexity: fewer files, fewer nodes, simpler testing

### Why Migrate
- Simpler implementation (proven by LangGraph team)
- Less custom code to maintain
- Better integration with LangGraph ecosystem
- Reduced testing surface (fewer nodes to test)
- Aligns with LangGraph best practices

### Key Implementation Decision
Use the **interface method approach** (`get_model()` on `ILLMProvider`) to expose LangChain models while maintaining provider abstraction throughout the application. This preserves the architecture's principles while enabling prebuilt integration.

