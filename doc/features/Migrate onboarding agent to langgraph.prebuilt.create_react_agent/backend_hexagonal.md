# Backend Hexagonal Architecture Analysis
## Issue #18: Migrate Onboarding Agent to langgraph.prebuilt.create_react_agent

## Request Summary

Migrate the current custom ReAct-pattern onboarding agent implementation to use LangGraph's `langgraph.prebuilt.create_react_agent`, which provides a standardized, pre-built ReAct pattern implementation. This simplifies the graph definition while maintaining all current functionality including system prompt injection, tool execution, and state persistence.

Current custom implementation:
- Manual ReAct loop definition with `process_input`, `inject_system_prompt`, `call_llm`, and `ToolNode`
- System prompt injection via dedicated node
- Custom conditional routing via `tools_condition`
- State management through `ConversationState` extending `MessagesState`

Migration target:
- Use `langgraph.prebuilt.create_react_agent` for built-in ReAct pattern
- Maintain all tool-calling and data collection behavior
- Preserve system prompt injection mechanism
- Keep all state fields and checkpointing behavior

## Relevant Files & Modules

### Core Onboarding Graph Files

- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/onboarding_graph.py` - Current custom ReAct implementation with manual nodes and edges
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/streaming_chat_graph.py` - Reference implementation of standard graph structure
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/chat_graph.py` - Basic chat graph (non-streaming)

### State Management

- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/state.py` - ConversationState extending MessagesState with onboarding fields (employee_name, employee_id, starter_kit, dietary_restrictions, meeting_scheduled, conversation_summary)

### Nodes

- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/call_llm.py` - LLM invocation with tool binding; accepts tools via config.configurable["tools"]
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/process_input.py` - Message validation before LLM
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/call_llm.py` - Note: Contains tool retrieval logic that distinguishes config-provided tools vs default tools

### Onboarding-Specific Tools

- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/read_data.py` - Query onboarding fields from state; supports optional field filtering
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/write_data.py` - Write validated data to state fields with Pydantic validation (employee_name, employee_id, starter_kit must pass validation)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/export_data.py` - Final export tool that validates completeness, generates LLM summary, persists to JSON, updates conversation_summary state field
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/rag_search.py` - Query knowledge base for Orbio policies/benefits

### System Prompts & Configuration

- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/prompts/onboarding_prompts.py` - ONBOARDING_SYSTEM_PROMPT that directs agent behavior for proactive data collection with explicit tool instructions

### WebSocket Integration

- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_router.py` - Endpoint handler at `/ws/onboarding` that retrieves graph from app state and passes tools
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py` - handle_websocket_chat function that streams events; receives graph.astream_events(), extracts tools via getattr(graph, '_tools', None), passes to config
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_schemas.py` - Message types for WebSocket protocol (PING, PONG, token, tool_start, tool_complete, complete, error)

### Application Initialization

- `/Users/pablolozano/Mac Projects August/genesis/backend/app/main.py` - Lifespan handler that:
  - Creates onboarding_tools list: [read_data, write_data, rag_search, export_data] (line 113)
  - Compiles onboarding_graph via create_onboarding_graph(checkpointer, onboarding_tools) (line 117)
  - Stores in app.state.onboarding_graph for WebSocket handler access

### LLM Provider Integration

- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/llm_provider.py` - ILLMProvider port with bind_tools() method
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/provider_factory.py` - get_llm_provider() factory function
- All LLM provider adapters implement bind_tools() delegation to LangChain's native method

### Domain Models & Ports

- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/conversation.py` - Conversation entity with id, user_id, title, created_at, updated_at
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/conversation_repository.py` - IConversationRepository port interface
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_conversation_repository.py` - MongoDB adapter

### Database & Checkpointing

- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/database/langgraph_checkpointer.py` - AsyncMongoDBSaver configuration
- Two database pattern: App DB (genesis_app) for conversation metadata, LangGraph DB (genesis_langgraph) for message history via checkpoints

### Tool Metadata & Registry

- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tool_metadata.py` - ToolRegistry and ToolMetadata classes; used by WebSocket handler to determine tool source (local vs MCP)

## Key Functions & Classes

### Graph Creation
- `create_onboarding_graph(checkpointer, tools)` in onboarding_graph.py - Factory function returning compiled graph with checkpointer
- `inject_system_prompt(state)` in onboarding_graph.py - Prepends ONBOARDING_SYSTEM_PROMPT to messages if not already present
- Graph stores tools as metadata: `compiled_graph._tools = tools` for WebSocket access

### Node Functions
- `call_llm(state, config)` - Receives tools from config.configurable["tools"]; binds via llm_provider.bind_tools(tools)
- `process_user_input(state)` - Validates messages exist before LLM
- `inject_system_prompt(state)` - Checks for existing SystemMessage and prepends if needed

### Tool Functions (Async)
- `read_data(state, field_names)` - Queries ConversationState fields; returns dict with status
- `write_data(state, field_name, value, comments)` - Validates via OnboardingDataSchema; returns success/error
- `export_data(state, confirmation_message)` - Orchestrates final export: validates required fields, calls LLM for summary, saves state field, writes JSON file

### WebSocket Handler
- `handle_websocket_chat(websocket, user, graph, llm_provider, conversation_repository)` - Streams via graph.astream_events(); extracts tools from graph._tools; passes config with tools to graph invocation
- Event handling: on_chat_model_stream (tokens), on_chat_model_end (tool_calls), on_tool_start/on_tool_end (tool execution)

### State Management
- `ConversationState` class extending `MessagesState` - Includes conversation_id, user_id, and onboarding fields
- MessagesState base provides add_messages reducer for native message management

## Current Architecture Overview

### Domain Core (Hexagonal Center)
**Location**: `/backend/app/core/`

**Domain Models**:
- `Conversation` entity with id, user_id, title, timestamps - represents conversation metadata
- Onboarding fields in ConversationState: employee_name, employee_id, starter_kit, dietary_restrictions, meeting_scheduled, conversation_summary

**Ports (Interfaces)**:
- `ILLMProvider` - LLM generation contract with generate(), stream(), get_model_name(), bind_tools()
- `IConversationRepository` - Conversation CRUD operations (get_by_id, create, update, delete, increment_message_count)
- `IVectorStore` - Vector database operations for RAG

**Use Cases / Business Logic**:
- Not explicitly modeled; currently orchestrated by LangGraph graphs and WebSocket handlers
- Tool execution logic (read_data, write_data, export_data) represents business rules for data collection

### Ports (Interfaces)
**Primary Ports (Inbound/Driving)**:
- `/ws/onboarding` WebSocket endpoint - Accepts user messages and streams responses
- REST API endpoints - User, conversation, message routes (not directly relevant to onboarding)

**Secondary Ports (Outbound/Driven)**:
- `ILLMProvider.generate()` - LLM provider port
- `IConversationRepository` - Conversation repository port
- AsyncMongoDBSaver checkpointer - LangGraph state persistence
- MongoDB (App DB) - Conversation metadata storage
- MongoDB (LangGraph DB) - Message history checkpoints

### Adapters

**Inbound Adapters** (`/backend/app/adapters/inbound/`):
- `websocket_router.py` - FastAPI WebSocket route handler that validates user and retrieves graph
- `websocket_handler.py` - handle_websocket_chat() orchestrates graph execution with event streaming
- `conversation_router.py` - REST endpoints for conversation CRUD
- `user_router.py` - REST endpoints for user management
- `auth_router.py` - Authentication endpoints
- `message_router.py` - Message endpoints

**Outbound Adapters** (`/backend/app/adapters/outbound/`):
- **LLM Providers**: OpenAI, Anthropic, Gemini, Ollama adapters implementing ILLMProvider
- **Repositories**: MongoConversationRepository, MongoUserRepository implementing repository ports
- **Vector Store**: ChromaVectorStore implementing IVectorStore
- **Tools**: read_data, write_data, export_data, rag_search as state-modifying functions
- **MCP Adapter**: MCPToolAdapter wrapping MCP tool definitions as callables

### LangGraph Layer (Orchestration)
**Graph Structure**:
```
START
  ↓
process_input (validates messages)
  ↓
inject_system_prompt (prepends ONBOARDING_SYSTEM_PROMPT)
  ↓
call_llm (invokes LLM with tools from config)
  ↓
tools_condition (routes to ToolNode or END)
  ├─ (if tool_calls) → ToolNode → call_llm (loop)
  └─ (no tool_calls) → END
```

**State Management**:
- ConversationState extends MessagesState
- Inherits add_messages reducer for automatic message appending
- Custom fields: conversation_id, user_id, employee_name, employee_id, starter_kit, dietary_restrictions, meeting_scheduled, conversation_summary
- Automatic persistence via AsyncMongoDBSaver to genesis_langgraph database

**Tools Binding**:
- Tools passed to graph creation: [read_data, write_data, rag_search, export_data]
- Stored as metadata: compiled_graph._tools
- Retrieved in WebSocket handler: tools = getattr(graph, '_tools', None)
- Passed via RunnableConfig: config.configurable["tools"]
- call_llm node binds tools: llm_provider.bind_tools(all_tools, parallel_tool_calls=False)

### Key Architectural Decisions

1. **System Prompt Injection**: Via dedicated node that checks for existing SystemMessage before prepending - ensures consistent agent behavior throughout conversation

2. **Tool Scope**: Onboarding graph uses only [read_data, write_data, rag_search, export_data], not general-purpose tools (multiply, add) - aligns with onboarding task specificity

3. **Tools as Configuration**: Tools passed via RunnableConfig rather than hardcoded in graph - enables tool flexibility and simplifies graph creation

4. **Separate Graph Instances**: streaming_chat_graph (default chat) vs onboarding_graph (specialized) - allows different tool sets and behaviors per workflow

5. **State Fields for Domain Data**: Onboarding data stored as ConversationState fields - automatically persisted via checkpointer, eliminating need for explicit repository writes during onboarding

6. **WebSocket Event Streaming**: Uses graph.astream_events() with version="v2" for structured event handling - enables token-by-token streaming and tool execution visibility

## Impact Analysis

### Components Affected by Migration to create_react_agent

#### 1. Graph Definition (HIGH IMPACT)
**Current File**: `backend/app/langgraph/graphs/onboarding_graph.py`

**Current Implementation**:
- Explicit graph_builder with manual nodes and edges
- Dedicated `inject_system_prompt` node
- Explicit `tools_condition` routing
- Manual ToolNode instantiation

**Migration Changes**:
- Replace StateGraph with create_react_agent builder
- System prompt injection may be handled differently (via bind/prompt or removed if LLM accepts system_prompt parameter)
- Conditional routing handled by create_react_agent internally
- ToolNode abstracted away

**Risk**: Loss of explicit control over graph flow if create_react_agent doesn't support custom system prompt injection pattern

#### 2. System Prompt Mechanism (CRITICAL)
**Current Mechanism**: `inject_system_prompt` node checks first message and prepends SystemMessage

**Why This Matters**: The system prompt is critical - it directs the agent to:
- Proactively guide conversation
- Use specific tools in specific ways (especially export_data call)
- Handle validation errors from write_data
- Complete onboarding rather than continue indefinitely

**create_react_agent Implications**:
- Built-in ReAct pattern may require different system prompt injection
- May support `system_prompt` parameter in initialization
- May need custom instruction wrapping if not directly injectable
- Test that agent still directs users through onboarding (not just responds passively)

#### 3. Tool Configuration (MEDIUM IMPACT)
**Current Pattern**:
```python
tools_param = [read_data, write_data, rag_search, export_data]
graph = create_onboarding_graph(checkpointer, tools_param)
# In node: config["configurable"]["tools"] → call_llm → llm_provider.bind_tools()
```

**Migration Pattern**:
- create_react_agent likely takes tools as parameter directly
- May eliminate need for config.configurable["tools"] intermediate
- call_llm node may not need to exist or work differently

**Impact on WebSocket Handler**:
- Current: `tools = getattr(graph, '_tools', None)` and passes via config
- New: May not need metadata storage; create_react_agent handles internally
- WebSocket handler may still need tools for event streaming (tool_start, tool_complete messages)

#### 4. Node Structure (MEDIUM IMPACT)
**Nodes to Remove/Replace**:
- `inject_system_prompt` - create_react_agent may handle or require different approach
- Potentially simplify `process_input` if create_react_agent handles

**Nodes to Keep/Verify**:
- Message creation flow (handled by create_react_agent internally)
- Tool execution (handled by create_react_agent internally)

#### 5. State Management (LOW IMPACT)
**ConversationState Compatibility**:
- create_react_agent expects MessagesState or compatible
- ConversationState already extends MessagesState ✓
- Onboarding fields (employee_name, etc.) should persist unchanged ✓
- No changes needed to state definition

**Checkpointing**:
- create_react_agent.compile() accepts checkpointer parameter
- No changes needed ✓

#### 6. WebSocket Integration (MEDIUM IMPACT)
**Current Flow**:
1. websocket_router retrieves graph from app.state.onboarding_graph
2. websocket_handler.handle_websocket_chat receives graph
3. Extracts tools: `getattr(graph, '_tools', None)`
4. Passes config with tools to graph.astream_events()
5. Streams events: on_chat_model_stream, on_tool_start, on_tool_end

**Migration Changes**:
- Graph retrieval unchanged ✓
- Tools extraction: May need different approach if create_react_agent doesn't store metadata
- Config passing: Simplified if tools no longer needed in configurable dict
- Event streaming: Should work unchanged with create_react_agent

**Potential Issue**: Tool source detection (local vs MCP) relies on getting tool list - may need refactoring if tools not accessible

#### 7. Application Initialization (MEDIUM IMPACT)
**Current main.py**:
```python
onboarding_tools = [read_data, write_data, rag_search, export_data]
app.state.onboarding_graph = create_onboarding_graph(checkpointer, onboarding_tools)
```

**Migration Pattern**:
```python
app.state.onboarding_graph = create_react_agent(
    llm_or_model,
    tools=[read_data, write_data, rag_search, export_data],
    system_prompt=ONBOARDING_SYSTEM_PROMPT,  # or similar
    checkpointer=checkpointer,
    # ... other params
)
```

**Changes Needed**:
- Import create_react_agent from langgraph.prebuilt
- Determine how to inject system prompt
- Adjust tool passing mechanism
- Ensure checkpointer compatibility

## Architectural Recommendations

### 1. Proposed Ports
No new ports needed. Existing ports remain:
- `ILLMProvider` - Already supports bind_tools() ✓
- `IConversationRepository` - Unchanged ✓
- Checkpointer as dependency injection - Unchanged ✓

### 2. Proposed Adapters

#### Primary: OnboardingGraphAdapter
**Responsibility**: Abstract graph creation from main.py

**Current Pattern**:
```python
# In main.py lifespan
app.state.onboarding_graph = create_onboarding_graph(checkpointer, onboarding_tools)
```

**Recommendation** - Create adapter for testability:
```python
# backend/app/adapters/outbound/graph_adapters/onboarding_graph_adapter.py
class OnboardingGraphAdapter:
    @staticmethod
    def create_graph(checkpointer, tools, system_prompt):
        """Create compiled onboarding ReAct graph using create_react_agent."""
        # Hide graph construction details
        # Return compiled graph ready for WebSocket
```

**Benefits**:
- Centralizes graph creation logic
- Easier to test different create_react_agent configurations
- Decouples graph implementation from main.py
- Clear responsibility boundary

### 3. Domain Changes
**None required**. The onboarding data model (employee_name, employee_id, etc.) remains unchanged.

The tools themselves (read_data, write_data, export_data) are adapters (infrastructure layer), not domain logic. They implement business rules through validation schemas and state mutations.

### 4. Dependency Flow (Visual)

**Current Architecture**:
```
┌─────────────────────────────────────────────┐
│  WebSocket Handler (/ws/onboarding)        │
│  - Authenticates user                       │
│  - Retrieves graph from app.state           │
│  - Extracts tools via metadata              │
└────────────┬────────────────────────────────┘
             │
             ↓
┌─────────────────────────────────────────────┐
│  LangGraph Onboarding Graph                 │
│  ┌───────────────────────────────────────┐  │
│  │ process_input → inject_prompt →      │  │
│  │ call_llm → tools_condition → END     │  │
│  │      ↑                          │     │  │
│  │      └──── ToolNode ────────────┘     │  │
│  └───────────────────────────────────────┘  │
│  Dependencies:                               │
│  - ConversationState (MessagesState)        │
│  - AsyncMongoDBSaver (checkpointer)         │
│  - ILLMProvider (via RunnableConfig)        │
│  - Tools: [read_data, write_data, ...]      │
└────────────┬────────────────────────────────┘
             │
    ┌────────┴────────┐
    ↓                 ↓
┌──────────────┐  ┌──────────────────┐
│ LLM Provider │  │ Domain Tools     │
│ (OpenAI, etc)│  │ - read_data     │
└──────────────┘  │ - write_data    │
                  │ - rag_search    │
                  │ - export_data   │
                  └──────────────────┘
             │
    ┌────────┴────────┐
    ↓                 ↓
┌──────────────┐  ┌──────────────────┐
│ MongoDBSaver │  │ State Persistence│
│ (LangGraph)  │  │ (Checkpoints)    │
└──────────────┘  └──────────────────┘
```

**Post-Migration (with create_react_agent)**:
```
┌─────────────────────────────────────────────┐
│  WebSocket Handler (/ws/onboarding)        │
│  - Authenticates user                       │
│  - Retrieves graph from app.state           │
│  - May not need tool extraction if internal │
└────────────┬────────────────────────────────┘
             │
             ↓
┌─────────────────────────────────────────────┐
│  LangGraph Prebuilt ReAct Agent            │
│  ┌───────────────────────────────────────┐  │
│  │ create_react_agent handles:           │  │
│  │ - System prompt injection              │  │
│  │ - ReAct loop (think/act/observe)      │  │
│  │ - Tool execution                       │  │
│  │ - Conditional routing                  │  │
│  └───────────────────────────────────────┘  │
│  Dependencies:                               │
│  - ConversationState (MessagesState)        │
│  - AsyncMongoDBSaver (checkpointer)         │
│  - Model/LLM (may be different param style) │
│  - Tools: [read_data, write_data, ...]      │
└────────────┬────────────────────────────────┘
             │
    ┌────────┴────────┐
    ↓                 ↓
┌──────────────┐  ┌──────────────────┐
│ LLM Provider │  │ Domain Tools     │
│ (OpenAI, etc)│  │ - read_data     │
└──────────────┘  │ - write_data    │
                  │ - rag_search    │
                  │ - export_data   │
                  └──────────────────┘
```

**Dependency Direction**: Dependencies flow inward toward domain ✓
- create_react_agent depends on tools (adapters)
- Tools depend on ConversationState (domain)
- No domain logic depends on graph implementation

## Implementation Guidance

### Phase 1: Research & Planning
1. **Understand create_react_agent API**:
   - Fetch LangGraph documentation for create_react_agent signature
   - Identify how to pass system prompt
   - Understand required vs optional parameters
   - Check compatibility with AsyncMongoDBSaver checkpointer

2. **Design System Prompt Injection**:
   - Determine if system_prompt parameter exists
   - If not, explore wrapping via prompt templates
   - Ensure ONBOARDING_SYSTEM_PROMPT content remains unchanged
   - Plan testing strategy for agent behavior

3. **Plan Tool Integration**:
   - Verify tools parameter accepts list of callables
   - Check if metadata storage still needed
   - Identify how tool source detection will work

### Phase 2: Implementation
1. **Create OnboardingGraphAdapter** (new file):
   ```python
   # backend/app/adapters/outbound/graph_adapters/onboarding_graph_adapter.py
   from langgraph.prebuilt import create_react_agent
   from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver
   from app.langgraph.prompts.onboarding_prompts import ONBOARDING_SYSTEM_PROMPT

   class OnboardingGraphAdapter:
       @staticmethod
       def create_graph(checkpointer, tools, llm_model):
           """Create onboarding ReAct graph using create_react_agent."""
           return create_react_agent(
               llm_model,
               tools=tools,
               system_prompt=ONBOARDING_SYSTEM_PROMPT,
               checkpointer=checkpointer,
               # ... additional params as needed
           )
   ```

2. **Update main.py lifespan**:
   - Replace create_onboarding_graph import
   - Use OnboardingGraphAdapter.create_graph()
   - Simplify tool passing if no longer needed in metadata

3. **Update onboarding_graph.py** (or deprecate):
   - If complete replacement, remove create_onboarding_graph function
   - Remove inject_system_prompt node
   - Remove manual StateGraph construction
   - Keep file for documentation if helpful

4. **Verify WebSocket Handler**:
   - Test graph.astream_events() still works with create_react_agent
   - Adjust tool extraction if needed
   - Verify tool source detection still works (may need fallback for MCP)

### Phase 3: Testing
1. **Unit Tests**:
   - Test graph creation with OnboardingGraphAdapter
   - Test system prompt is properly injected
   - Test tool binding

2. **Integration Tests**:
   - WebSocket flow with create_react_agent graph
   - Event streaming (tokens, tool execution)
   - State persistence across turns

3. **Behavioral Tests**:
   - Agent proactively guides through onboarding (due to system prompt)
   - export_data correctly finalizes conversation
   - read_data and write_data work within ReAct loop
   - rag_search functions for knowledge base queries

4. **Regression Tests**:
   - Compare behavior with current implementation
   - Verify message history checkpointing works
   - Test tool execution order and results

### Phase 4: Migration
1. Feature branch: `migrate/onboarding-to-create-react-agent`
2. Incremental commits:
   - Add adapter pattern
   - Implement create_react_agent usage
   - Remove old graph construction
   - Update tests
3. Code review focusing on:
   - System prompt behavior unchanged
   - Tool execution unchanged
   - State persistence unchanged
4. Merge to main

## Risks and Considerations

### 1. System Prompt Behavior (HIGH RISK)
**Risk**: create_react_agent may not support the current system prompt injection pattern

**Current Behavior**:
- inject_system_prompt node checks first message is SystemMessage
- Prepends ONBOARDING_SYSTEM_PROMPT to ensure agent behavior

**What Could Go Wrong**:
- create_react_agent may not allow custom system message injection
- System prompt placement in message history could change
- Agent behavior could diverge from current implementation

**Mitigation**:
- Test system prompt in create_react_agent parameter thoroughly
- Compare agent responses (with same model/temperature) between old and new
- Have fallback manual graph if create_react_agent doesn't support system_prompt
- Document exact system prompt behavior expectations

### 2. Tool Metadata Loss (MEDIUM RISK)
**Risk**: If create_react_agent doesn't expose tools via metadata, WebSocket tool source detection may break

**Current**: `graph._tools` accessed by WebSocket handler for tool source (local vs MCP)

**Impact**: Tool visualization in frontend may not distinguish MCP tools

**Mitigation**:
- Check if create_react_agent stores tools internally
- Create fallback tool source detection (default to local if not found)
- Store tool list separately if needed: `app.state.onboarding_tools`
- Test MCP tools still appear and execute correctly

### 3. Graph Structure Rigidity (MEDIUM RISK)
**Risk**: create_react_agent may not match current graph structure exactly

**Current Flow**: process_input → inject_prompt → call_llm → [ToolNode | END]

**create_react_agent Flow**: Unknown, depends on implementation

**Impact**: Behavior could differ subtly (e.g., node order, retry logic, max iterations)

**Mitigation**:
- Verify create_react_agent has max iterations/depth limit
- Test onboarding completes without infinite loops
- Compare performance (tokens used, iterations) before/after
- Monitor production metrics if applicable

### 4. Checkpointer Compatibility (LOW-MEDIUM RISK)
**Risk**: create_react_agent may have different checkpointer expectations

**Current**: Passed to graph_builder.compile(checkpointer=...)

**Migration**: Ensure checkpointer parameter works same way with create_react_agent

**Mitigation**:
- Test with AsyncMongoDBSaver explicitly
- Verify state persists correctly across turns
- Check error handling for checkpoint failures
- Monitor LangGraph DB collections

### 5. State Field Persistence (LOW RISK)
**Risk**: Custom state fields (employee_name, etc.) may not persist correctly

**Current**: ConversationState extends MessagesState with custom fields

**Mitigation**: ✓ No action needed
- MessagesState reducer handles messages
- Custom fields should work unchanged
- AsyncMongoDBSaver checkpoints full state including custom fields
- Test persistence explicitly

### 6. Tool Execution Order (MEDIUM RISK)
**Risk**: create_react_agent's internal ReAct loop may execute tools differently

**Current**: Single tool execution per cycle, loops back to call_llm via tools edge

**Potential Issue**: Different parallel_tool_calls behavior, retry logic, or execution order

**Mitigation**:
- Test export_data completes and finalizes conversation
- Verify read_data accurately returns collected fields
- Test validation errors from write_data are handled correctly
- Monitor tool execution sequences in logs

## Testing Strategy

### Unit Tests
**File**: `backend/app/tests/unit/langgraph/graphs/test_onboarding_graph_migration.py`

```python
# Test create_react_agent graph creation
def test_onboarding_graph_creation():
    """Verify OnboardingGraphAdapter creates valid graph."""
    # Create graph with mock LLM and checkpointer
    # Assert graph is compiled and has expected methods
    # Assert tools are bound

# Test system prompt injection
@pytest.mark.asyncio
async def test_system_prompt_in_graph():
    """Verify system prompt is injected correctly."""
    # Initialize graph with ONBOARDING_SYSTEM_PROMPT
    # Invoke with initial message
    # Assert first message in state is SystemMessage with correct content

# Test tool binding
def test_tools_bound_to_graph():
    """Verify all onboarding tools are bound."""
    # Create graph
    # Assert tools accessible (via internal state or metadata)
    # Assert tools list includes read_data, write_data, rag_search, export_data
```

### Integration Tests
**File**: `backend/app/tests/integration/langgraph/test_onboarding_flow_migration.py`

```python
# Test WebSocket flow with new graph
@pytest.mark.asyncio
async def test_ws_onboarding_with_create_react_agent():
    """Test complete WebSocket onboarding flow."""
    # Create WebSocket connection
    # Send onboarding message
    # Verify agent responses and tool calls
    # Assert state persists

# Test tool execution within graph
@pytest.mark.asyncio
async def test_tool_execution_sequence():
    """Verify tools execute in correct sequence."""
    # Send message that requires multiple tools
    # Assert tool_start and tool_end events received
    # Assert tool results correctly integrated

# Test state persistence
@pytest.mark.asyncio
async def test_state_persists_across_turns():
    """Verify checkpointer persists state."""
    # Send message with read_data call
    # Verify state field is set
    # Reconnect with same thread_id
    # Assert field persists
```

### Behavioral Tests
**File**: `backend/app/tests/e2e/test_onboarding_migration.py`

```python
# Test proactive agent behavior
@pytest.mark.asyncio
async def test_agent_proactively_guides_onboarding():
    """Verify agent guides through onboarding process."""
    # Start conversation
    # Assert agent asks for required fields (employee_name, employee_id, starter_kit)
    # Assert agent uses write_data to save responses
    # Assert agent uses export_data to finalize

# Test knowledge base access
@pytest.mark.asyncio
async def test_rag_search_for_questions():
    """Verify agent can answer questions about Orbio."""
    # Ask question about company policy
    # Assert agent uses rag_search tool
    # Assert response includes knowledge base information

# Test validation handling
@pytest.mark.asyncio
async def test_validation_error_handling():
    """Verify agent retries invalid data."""
    # Send invalid starter_kit value
    # Assert write_data returns validation error
    # Assert agent asks for valid option
    # Assert agent eventually records valid value
```

### Regression Tests
**File**: `backend/app/tests/regression/test_onboarding_old_vs_new.py`

```python
# Compare behavior between old and new implementation
@pytest.mark.asyncio
async def test_old_vs_new_export_behavior():
    """Verify export_data behavior unchanged."""
    # Run same onboarding flow through both graphs
    # Assert final exported JSON structure identical
    # Assert conversation_summary generated same way

@pytest.mark.asyncio
async def test_old_vs_new_tool_sequence():
    """Verify tool execution order consistent."""
    # Compare astream_events output
    # Assert same tools called in same order
    # Assert same state fields set
```

### Performance Tests
**File**: `backend/app/tests/performance/test_onboarding_migration.py`

```python
# Monitor performance implications
@pytest.mark.asyncio
async def test_token_efficiency():
    """Compare token usage between implementations."""
    # Complete onboarding with both graphs
    # Assert token counts similar (within 10% variance)

@pytest.mark.asyncio
async def test_inference_latency():
    """Verify no significant latency increase."""
    # Measure response times
    # Assert P95 latency acceptable
```

## Testing Approach - Architectural Focus

The testing strategy emphasizes **architectural boundaries**:

1. **Domain Logic Testing**:
   - Onboarding data model (employee_name, etc.) isolated
   - Validation rules tested independently of graph

2. **Adapter Testing**:
   - read_data, write_data, export_data as adapters tested in isolation
   - Tool interfaces verified

3. **Graph Testing**:
   - Graph creation tested
   - Event streaming tested
   - No leaking of graph internals to application code

4. **Integration Testing**:
   - WebSocket adapter tested with graph
   - Checkpointer integration verified
   - End-to-end flows validated

## Summary of Architectural Concerns

### Preserved ✓
- Domain model (ConversationState with onboarding fields)
- State persistence (AsyncMongoDBSaver checkpointing)
- Tool execution pattern (read_data, write_data, export_data, rag_search)
- WebSocket integration (astream_events, token streaming, tool events)
- Hexagonal architecture layers (domain → adapters → infrastructure)
- Dependency direction (inward toward domain)

### Changed
- Graph construction method (StateGraph → create_react_agent)
- System prompt injection mechanism (dedicated node → parameter-based)
- Node structure (simplified by prebuilt implementation)
- Potential metadata storage (may change tool access pattern)

### New Responsibilities
- OnboardingGraphAdapter factory (if created for cleaner architecture)
- Testing of create_react_agent compatibility
- Documentation of system prompt behavior with new implementation

### Still Required
- Onboarding tools implementation (read_data, write_data, export_data, rag_search)
- State definition (ConversationState)
- WebSocket handler (may need minimal changes)
- Checkpointer setup
- Tool registry (if maintained for tool source tracking)

## Questions for Implementation

1. **Does create_react_agent accept a system_prompt parameter?**
   - If yes, straightforward migration
   - If no, explore prompt_template or custom instructions wrapping

2. **How does create_react_agent handle max iterations?**
   - Ensure onboarding doesn't loop indefinitely
   - Test agent can reach export_data

3. **Does create_react_agent support metadata storage (like _tools)?**
   - If no, adjust WebSocket handler to store tools separately

4. **What parameters does create_react_agent require vs accept?**
   - LLM/model parameter format
   - Tools parameter format
   - Checkpointer compatibility

5. **How does event streaming work with create_react_agent?**
   - Does astream_events() work unchanged?
   - Are event types identical?

6. **Does ConversationState work without modifications?**
   - Test MessagesState compatibility
   - Verify custom fields persist
