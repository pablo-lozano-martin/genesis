# API Contract Analysis: Migrate Onboarding Agent to create_react_agent

## Request Summary

Migrate the onboarding agent from a custom ReAct-pattern graph implementation to LangGraph's prebuilt `create_react_agent` factory function. This involves analyzing the API contracts to ensure backward compatibility with the WebSocket endpoint, message schemas, and tool interfaces while leveraging the simplified prebuilt implementation.

## Relevant Files & Modules

### Files to Examine

#### API Layer - WebSocket Endpoints & Handlers
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_router.py` - WebSocket endpoint declarations including `/ws/onboarding` endpoint
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py` - WebSocket connection handler with event streaming logic for both chat and onboarding
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_schemas.py` - Message schemas for client-server WebSocket communication

#### Graph Implementation
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/onboarding_graph.py` - Current custom ReAct graph implementation to be migrated
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/streaming_chat_graph.py` - Existing streaming chat graph for reference pattern
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/chat_graph.py` - Simple chat graph without streaming

#### State & Configuration
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/state.py` - ConversationState schema used by all graphs
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/main.py` - App initialization that compiles graphs and registers tools

#### Node Implementations
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/call_llm.py` - LLM invocation node that binds tools and generates responses
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/process_input.py` - Input validation node

#### Tool Implementations & Metadata
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/read_data.py` - Query collected onboarding fields
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/write_data.py` - Write validated onboarding data with Pydantic schema
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/export_data.py` - Export completed onboarding to JSON with LLM-generated summary
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/rag_search.py` - RAG search tool for onboarding questions
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tool_metadata.py` - Tool registry for tracking local vs MCP tools
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/prompts/onboarding_prompts.py` - System prompt for onboarding agent behavior

#### WebSocket Authentication
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/security/websocket_auth.py` - JWT authentication for WebSocket connections

### Key Functions & Endpoints

#### WebSocket Endpoints (Router)
- `POST /ws/onboarding` in `websocket_router.py` - WebSocket endpoint for onboarding conversations (uses implicit path parameter via URL structure)

#### WebSocket Message Handlers
- `handle_websocket_chat()` in `websocket_handler.py` - Unified handler for both chat and onboarding, processes ClientMessage and streams ServerMessage types
- `ConnectionManager.send_message()` in `websocket_handler.py` - Sends JSON-serialized messages to WebSocket client

#### Graph Compilation Functions
- `create_onboarding_graph()` in `onboarding_graph.py` - Creates custom ReAct graph (to be replaced)
- `create_streaming_chat_graph()` in `streaming_chat_graph.py` - Existing prebuilt pattern for reference
- `create_chat_graph()` in `chat_graph.py` - Simpler graph without tool execution loop

#### Node Functions
- `call_llm()` in `call_llm.py` - Async function that invokes LLM with tools from config
- `process_user_input()` in `process_input.py` - Validates messages exist in state

#### Tool Functions (Used as Callables)
- `read_data(state, field_names)` - Query onboarding fields from state
- `write_data(state, field_name, value, comments)` - Write validated data to state
- `export_data(state, confirmation_message)` - Export to JSON file with LLM summary
- `rag_search(query)` - Search knowledge base for onboarding questions

## Current API Contract Overview

### Architecture Overview

The onboarding flow uses a LangGraph-first architecture with the following characteristics:

```
Client (Frontend)
    |
    v
WebSocket /ws/onboarding (FastAPI)
    |
    v
handle_websocket_chat() (unified handler)
    |
    v
onboarding_graph (LangGraph)
    |
    +-- process_input (node)
    +-- inject_system_prompt (node)
    +-- call_llm (node, tool binding)
    +-- ToolNode (prebuilt, executes tools)
    |
    v
Tool Execution (read_data, write_data, rag_search, export_data)
    |
    v
LangGraph CheckPointer (AsyncMongoDBSaver)
    |
    v
MongoDB (State Persistence)
```

### WebSocket Endpoint Definition

**Endpoint**: `/ws/onboarding`
**Method**: WebSocket Upgrade (FastAPI WebSocket)
**Location**: `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_router.py`

**Authentication**:
- JWT token via query parameter: `/ws/onboarding?token=<jwt_token>`
- OR JWT token via Authorization header: `Authorization: Bearer <jwt_token>`

**Handler**: `websocket_onboarding_endpoint()` delegates to `handle_websocket_chat()` with:
- `websocket`: FastAPI WebSocket connection
- `user`: Authenticated User object
- `graph`: `websocket.app.state.onboarding_graph` (compiled LangGraph)
- `llm_provider`: LLM provider instance
- `conversation_repository`: MongoDB repository for conversation lookup

### Message Schemas

All WebSocket messages follow the schema definitions in `websocket_schemas.py`. The protocol uses discriminated union types via the `type` field.

#### Client Messages (Client → Server)

**ClientMessage**
```python
type: MessageType = Field(default=MessageType.MESSAGE)  # discriminator
conversation_id: str  # UUID of conversation
content: str  # User message (1+ chars)
```

**PingMessage**
```python
type: MessageType = Field(default=MessageType.PING)
```

#### Server Messages (Server → Client)

Union type: `ServerMessage = ServerTokenMessage | ServerCompleteMessage | ServerErrorMessage | PongMessage | ServerToolStartMessage | ServerToolCompleteMessage`

**ServerTokenMessage**
```python
type: MessageType = MessageType.TOKEN
content: str  # Partial token from LLM
```

**ServerCompleteMessage**
```python
type: MessageType = MessageType.COMPLETE
message_id: str  # Saved message UUID
conversation_id: str  # Conversation UUID
```

**ServerErrorMessage**
```python
type: MessageType = MessageType.ERROR
message: str  # Error description
code: Optional[str]  # Error code (e.g., "INVALID_FORMAT", "ACCESS_DENIED", "LLM_ERROR")
```

**PongMessage**
```python
type: MessageType = MessageType.PONG
```

**ServerToolStartMessage**
```python
type: Literal[MessageType.TOOL_START] = MessageType.TOOL_START
tool_name: str  # Name of tool (e.g., "read_data")
tool_input: str  # JSON string of arguments
source: Optional[str]  # "local" or "mcp"
timestamp: str  # ISO timestamp
```

**ServerToolCompleteMessage**
```python
type: Literal[MessageType.TOOL_COMPLETE] = MessageType.TOOL_COMPLETE
tool_name: str
tool_result: str  # String representation of result
source: Optional[str]  # "local" or "mcp"
timestamp: str  # ISO timestamp
```

### State Schema (ConversationState)

**Location**: `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/state.py`

Extends LangGraph's native `MessagesState`:

```python
class ConversationState(MessagesState):
    # From MessagesState (auto-managed):
    messages: List[BaseMessage]  # HumanMessage, AIMessage, SystemMessage, ToolMessage

    # Conversation metadata:
    conversation_id: str  # UUID
    user_id: str  # UUID

    # Onboarding-specific fields (collected via tools):
    employee_name: Optional[str]
    employee_id: Optional[str]
    starter_kit: Optional[str]  # One of: mouse, keyboard, backpack
    dietary_restrictions: Optional[str]
    meeting_scheduled: Optional[bool]
    conversation_summary: Optional[str]  # Set by export_data tool
```

### Graph Structure (Current Implementation)

**Location**: `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/onboarding_graph.py`

Current custom ReAct pattern implementation:

```
START
  |
  v
process_input
  |
  v
inject_system_prompt (custom node, prepends ONBOARDING_SYSTEM_PROMPT)
  |
  v
call_llm (binds onboarding tools: [read_data, write_data, rag_search, export_data])
  |
  v
tools_condition (prebuilt conditional)
  |
  +-- (has tool_calls) --> tools (ToolNode)
  |                          |
  |                          v
  |                       call_llm (loop back)
  |
  +-- (no tool_calls) --> END
```

**Tool Binding**: Done in `call_llm` node via `llm_provider.bind_tools(all_tools, parallel_tool_calls=False)`

**System Prompt Injection**: Via custom `inject_system_prompt()` node that checks if first message is SystemMessage and prepends it if not

**System Prompt Content**: `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/prompts/onboarding_prompts.py`
- Guides agent through: greet → collect data → validate → summarize → export
- Explicitly directs agent to use export_data for finalization (not rag_search or write_data)
- Defines tool usage: read_data (check status), write_data (save), rag_search (questions), export_data (finalize)

### Tool Interfaces

All tools are async functions that receive ConversationState as first parameter (LangGraph auto-passes state).

#### read_data(state, field_names=None)

**Purpose**: Query collected onboarding fields

**Returns**:
```python
{
    "status": "success",
    "employee_name": str or None,
    "employee_id": str or None,
    "starter_kit": str or None,
    "dietary_restrictions": str or None,
    "meeting_scheduled": bool or None,
    "conversation_summary": str or None
}
# Or on error:
{
    "status": "error",
    "message": str,
    "valid_fields": List[str]
}
```

#### write_data(state, field_name, value, comments=None)

**Purpose**: Write validated data to state

**Field Validation Rules**:
- `employee_name`: String, 1-255 characters
- `employee_id`: String, 1-50 characters
- `starter_kit`: One of ["mouse", "keyboard", "backpack"] (case-insensitive)
- `dietary_restrictions`: String, up to 500 characters
- `meeting_scheduled`: Boolean
- `conversation_summary`: String (no limit)

**Returns**:
```python
{
    "field_name": str,
    "value": str or bool or None,
    "status": "success",
    "message": "Data recorded"
}
# Or on validation error:
{
    "field_name": str,
    "value": Any,
    "status": "error",
    "message": str,  # Pydantic validation error
    "valid_values": List[str]  # For constrained fields
}
# Or on unknown field:
{
    "field_name": str,
    "status": "error",
    "message": "Unknown field '...'",
    "valid_fields": List[str]
}
```

#### export_data(state, confirmation_message=None)

**Purpose**: Finalize onboarding by validating required fields, generating LLM summary, and exporting to JSON

**Required Fields Check**:
- Must have: employee_name, employee_id, starter_kit
- Optional: dietary_restrictions, meeting_scheduled

**Summary Generation**:
1. Calls LLM with summary prompt
2. Generates 2-3 bullet point markdown summary
3. Saves to state["conversation_summary"]

**Export Location**: `/app/onboarding_data/{conversation_id}.json`

**Returns**:
```python
{
    "status": "success",
    "message": "Onboarding data exported successfully",
    "file_path": str,  # Path to JSON file
    "summary": str  # LLM-generated summary
}
# Or if missing required fields:
{
    "status": "error",
    "message": "Cannot export: missing required fields",
    "missing_fields": List[str],
    "required_fields": ["employee_name", "employee_id", "starter_kit"]
}
# Or if file write fails:
{
    "status": "error",
    "message": "Failed to write export file: ...",
    "file_path": str
}
```

#### rag_search(query)

**Purpose**: Search knowledge base for onboarding-related information

**Input**:
- `query`: String question about Orbio policies/benefits

**Returns**: Search results from ChromaDB vector store (see `rag_search.py` implementation)

### Error Response Formats

**HTTP-level errors** (FastAPI validation):
- 400: Invalid JSON format
- 401: Authentication failure
- 404: Conversation not found

**WebSocket Protocol Errors** (sent as ServerErrorMessage):
```python
ServerErrorMessage(
    message=str,  # Human-readable message
    code=Optional[str]  # Machine-readable code
)
```

**Common Error Codes**:
- `"INVALID_FORMAT"`: JSON parsing failed
- `"ACCESS_DENIED"`: User attempted to access conversation they don't own
- `"LLM_ERROR"`: LLM invocation failed
- `"INTERNAL_ERROR"`: Unexpected server error

**Tool-level errors** (returned via tool interface):
Tools return dictionaries with `status: "error"` and `message: str` fields, sometimes with additional context like `valid_fields` or `valid_values`.

### Validation & Data Flow

**Input Validation**:
1. WebSocket handler receives raw JSON text
2. Parses via `ClientMessage.model_validate()`
3. Extracts conversation_id
4. Checks conversation ownership via repository lookup
5. Verifies conversation.user_id == user.id

**Tool-Level Validation**:
- `write_data` uses Pydantic `OnboardingDataSchema` for field validation
- Invalid starter_kit values are rejected with list of valid options
- Invalid field names return list of valid_fields

**State Management**:
- ConversationState is persisted after each graph step via AsyncMongoDBSaver
- Tools directly modify state dict (state["employee_name"] = value)
- export_data explicitly sets state["conversation_summary"] before export

### Tool Binding & Configuration

**Tool Binding Location**: `call_llm` node in `call_llm.py`

**Current Logic**:
1. Check if tools provided in RunnableConfig (used by onboarding graph)
2. If yes, use those tools exclusively
3. If no, combine local tools + MCP tools

**Config Passing** (from `websocket_handler.py`):
```python
config = RunnableConfig(
    configurable={
        "thread_id": conversation.id,
        "llm_provider": llm_provider,
        "user_id": user.id,
        "tools": tools  # For specialized graphs like onboarding
    }
)
```

**App Initialization** (from `main.py`):
```python
onboarding_tools = [read_data, write_data, rag_search, export_data]
app.state.onboarding_graph = create_onboarding_graph(checkpointer, onboarding_tools)
```

## Impact Analysis

### Affected API Components

#### WebSocket Endpoint: `/ws/onboarding`

**Impact**: Minimal to none if migration done correctly

**Current Flow**:
1. Endpoint delegates to `handle_websocket_chat()` (shared with regular chat)
2. Handler receives pre-compiled `graph = websocket.app.state.onboarding_graph`
3. Handler invokes graph via `graph.astream_events()`
4. Message events are streamed to client

**Potential Breaking Points**:
- If `create_react_agent()` returns a different object type, stream compatibility breaks
- If tool binding mechanism differs, tool execution flow breaks
- If state management differs, checkpointing breaks

#### WebSocket Handler: `handle_websocket_chat()`

**Current Assumptions**:
- Graph returns events via `astream_events()` with v2 protocol
- Events include: `on_chat_model_stream`, `on_chat_model_end`, `on_tool_start`, `on_tool_end`
- Tool calls cached from AIMessage.tool_calls
- Tool source determined via registry lookup

**Potential Changes**:
- Event names might differ with create_react_agent
- Tool execution flow might change (affects tool_start/tool_complete message emission)
- State management might not be compatible with checkpoint-based persistence

#### Message Schemas

**No Expected Changes**: WebSocket message types are API contracts that should remain stable. The ServerMessage union types (ServerTokenMessage, ServerErrorMessage, ServerToolStartMessage, ServerToolCompleteMessage) are consumed by the frontend and must not break.

#### State Schema (ConversationState)

**Risk**: If `create_react_agent()` requires a different state type, ConversationState would need to be refactored

**Current Assumption**: State extends `MessagesState` and adds onboarding-specific fields

**Potential Issue**: If prebuilt factory uses different state management, integration point breaks

#### Tool Interfaces

**Risk**: If `create_react_agent()` tool binding mechanism differs, tool invocation breaks

**Current Pattern**:
```python
all_tools = [read_data, write_data, rag_search, export_data]
llm_provider_with_tools = llm_provider.bind_tools(all_tools, parallel_tool_calls=False)
```

**Question**: Does `create_react_agent()` accept pre-bound tools or does it handle binding internally?

#### System Prompt Injection

**Risk**: Custom `inject_system_prompt()` node might not fit with prebuilt factory

**Current Pattern**: Custom node that prepends SystemMessage if not present

**With create_react_agent**: May need to refactor how system prompt is injected

## API Contract Recommendations

### 1. Preserve WebSocket Message Schema

**Recommendation**: Do NOT change WebSocket message types. The ServerMessage union and all message type definitions must remain identical to maintain frontend compatibility.

**Rationale**: Frontend clients expect specific message formats (type, tool_name, tool_result, timestamp). Changing these breaks the WebSocket API contract.

**Implementation**: Keep `websocket_schemas.py` exactly as-is. Test that create_react_agent events map to same server message types.

### 2. Maintain State Contract

**Recommendation**: Ensure ConversationState structure remains compatible with create_react_agent output.

**Critical Fields**:
- `messages: List[BaseMessage]` - Must be populated and streamable
- `conversation_id: str` - Must be preserved for conversation tracking
- `user_id: str` - Must be preserved for authorization
- Onboarding fields (employee_name, etc.) - Must be gettable/settable by tools

**Verification**: After migration, state snapshots should be functionally identical to current implementation.

### 3. Tool Interface Compatibility

**Recommendation**: Verify that `create_react_agent()` can bind the four onboarding tools and invoke them correctly.

**Tool Contracts** (must remain unchanged):
- All tools must be async callables
- All tools must accept ConversationState as first parameter (LangGraph auto-injects)
- Return values must match documented schemas
- Validation errors must be in documented format

**Verification**:
1. Confirm tools execute in same order and manner
2. Confirm tool results are properly serialized back to agent
3. Confirm export_data can still modify state and write files

### 4. RunnableConfig & Tool Passing

**Recommendation**: Determine if `create_react_agent()` supports passing tools via RunnableConfig or if tools must be bound differently.

**Current Pattern**:
```python
config = RunnableConfig(configurable={"tools": [read_data, write_data, rag_search, export_data]})
graph.astream_events(input_data, config)
```

**Options**:
1. If `create_react_agent()` accepts tools in constructor, pass tools at graph creation time
2. If it supports RunnableConfig tools, keep current pattern
3. If neither, may need to refactor tool binding logic

**Impact on Handler**: If tool passing changes, `websocket_handler.py` must be updated to pass tools differently.

### 5. Event Streaming Compatibility

**Recommendation**: Test that `create_react_agent()` graph.astream_events() emits same events as custom graph.

**Critical Events** (must be present for handler to work):
- `on_chat_model_stream` - LLM token chunks
- `on_chat_model_end` - LLM response completion (contains tool_calls)
- `on_tool_start` - Tool execution start
- `on_tool_end` - Tool execution completion

**Risk**: If event names/structure differs, handler logic breaks. Handler relies on:
1. Caching tool_calls from on_chat_model_end.output.tool_calls
2. Using cached tool call for on_tool_start/on_tool_end messages
3. Extracting content from on_chat_model_stream chunks

**Verification Strategy**:
1. Create test graph using create_react_agent
2. Run test input through graph with astream_events()
3. Capture all event types and structure
4. Compare against current custom implementation
5. Update handler if event structure differs

### 6. System Prompt Injection

**Recommendation**: Determine how `create_react_agent()` handles system prompts.

**Current Approach**: Custom `inject_system_prompt()` node that prepends SystemMessage if not present

**With create_react_agent**:
- Option 1: Pass system_prompt parameter to factory function
- Option 2: Continue using custom node (if prebuilt supports custom nodes)
- Option 3: Inject at state initialization level

**Implementation Decision**: Check `create_react_agent()` signature and documentation for system prompt support.

### 7. Backward Compatibility for Frontend

**Recommendation**: Ensure migrate does NOT introduce breaking changes to WebSocket API.

**API Contracts Guaranteed**:
- `/ws/onboarding` endpoint URL remains same
- Authentication mechanism remains same (JWT token)
- ClientMessage schema remains same
- ServerMessage union types remain same
- Error codes remain same
- Tool event structure (tool_start, tool_complete) remains same

**Testing Strategy**:
1. Run existing frontend client against new graph
2. Verify all message types are recognized
3. Verify tool calls are displayed properly
4. Verify error handling works
5. Verify export_data completion is handled correctly

### 8. Tool Binding & Onboarding-Specific Tools

**Recommendation**: Ensure `create_react_agent()` can be constrained to onboarding tools only.

**Current Constraint**: onboarding_tools = [read_data, write_data, rag_search, export_data]

**Risk**: If `create_react_agent()` auto-binds other tools from config, export_data contract breaks (agent might not call it for finalization)

**Verification**:
1. Confirm only onboarding tools are available to agent
2. Confirm agent cannot access multiply, add, or other chat tools
3. Confirm system prompt direction to use export_data works

## Implementation Guidance

### Step 1: Research create_react_agent API

1. Fetch LangGraph documentation for `langgraph.prebuilt.create_react_agent`
2. Understand function signature and parameters
3. Understand state type requirements
4. Understand tool binding mechanism
5. Understand system prompt handling
6. Document any breaking differences from custom graph

### Step 2: Create Migration Test Graph

```python
# In new test file: backend/tests/unit/test_create_react_agent_onboarding.py

# Test 1: Create agent with onboarding tools
def test_create_react_agent_with_onboarding_tools():
    # Create agent using create_react_agent
    # Pass tools: [read_data, write_data, rag_search, export_data]
    # Verify agent type and basic properties
    pass

# Test 2: Verify event streaming compatibility
async def test_create_react_agent_astream_events():
    # Create agent
    # Run test input through astream_events()
    # Capture all event types
    # Verify on_chat_model_stream present
    # Verify on_tool_start/on_tool_end present
    pass

# Test 3: Verify state management
async def test_create_react_agent_state_persistence():
    # Run onboarding flow through agent
    # Verify ConversationState is updated correctly
    # Verify onboarding fields are writable by tools
    pass

# Test 4: Verify tool execution flow
async def test_create_react_agent_tool_calls():
    # Create agent with test tools that track calls
    # Verify tools are called in expected order
    # Verify tool results are returned to agent
    pass
```

### Step 3: Update create_onboarding_graph()

1. Replace custom StateGraph builder with `create_react_agent()`
2. Pass tools: onboarding_tools (read_data, write_data, rag_search, export_data)
3. Handle system prompt injection:
   - Option A: Pass as system_prompt parameter if supported
   - Option B: Create SystemMessage separately and prepend to initial state
   - Option C: Keep custom inject_system_prompt node if prebuilt allows custom nodes
4. Ensure checkpointer is passed for state persistence
5. Store tools as metadata: `compiled_graph._tools = tools`

**Example Implementation**:
```python
from langgraph.prebuilt import create_react_agent

def create_onboarding_graph(checkpointer, tools=None):
    if tools is None:
        from app.langgraph.tools import read_data, write_data, rag_search, export_data
        tools = [read_data, write_data, rag_search, export_data]

    # Create agent using prebuilt factory
    agent = create_react_agent(
        model=llm_provider,  # Or pass via config?
        tools=tools,
        state_schema=ConversationState,
        system_prompt=ONBOARDING_SYSTEM_PROMPT,
        # Check what other params are supported
    )

    # Compile with checkpointer
    compiled = agent.compile(checkpointer=checkpointer)

    # Store tools for access in handler
    compiled._tools = tools

    return compiled
```

### Step 4: Update websocket_handler.py if Needed

**Scenarios**:
1. If event structure changes, update event handling logic
2. If tool execution changes, update tool_start/tool_complete message emission
3. If config requirements change, update RunnableConfig creation

**Test Against**:
- Existing unit tests (should still pass)
- Integration tests with real WebSocket
- Frontend client compatibility

### Step 5: Update main.py Graph Initialization

Only minimal changes expected:
1. Still call `create_onboarding_graph(checkpointer, onboarding_tools)`
2. Still store in `app.state.onboarding_graph`
3. Still used by websocket_handler

### Step 6: Verify Tool Binding at call_llm Node

Check if tool binding logic in `call_llm.py` needs updates:
1. If `create_react_agent()` auto-handles tool binding, may need to adjust call_llm logic
2. If tools come from state/config, no changes needed
3. If system prompt comes from agent, may not need to set up tools in call_llm

## Risks and Considerations

### 1. Backward Compatibility Risk (HIGH)

**Risk**: Frontend expects specific WebSocket message types and tool event structure. Changing event names or fields breaks frontend.

**Mitigation**:
- Preserve websocket_schemas.py exactly
- Test event stream compatibility before deployment
- Run frontend integration tests with new graph
- Have fallback to custom graph if prebuilt breaks compatibility

### 2. State Management Risk (HIGH)

**Risk**: If `create_react_agent()` uses different state management, checkpointing might not work.

**Mitigation**:
- Verify state is persisted after each graph step
- Test state recovery from checkpoint after graph restart
- Verify onboarding fields are still writable by tools

### 3. Tool Execution Risk (MEDIUM)

**Risk**: Tool binding or execution flow might differ, affecting how tools are called and results returned.

**Mitigation**:
- Test each tool independently with prebuilt agent
- Verify tool results are properly serialized back to agent
- Verify export_data can still modify state and write files
- Test complete onboarding flow end-to-end

### 4. System Prompt Risk (MEDIUM)

**Risk**: System prompt injection mechanism might differ, affecting agent behavior and finalization logic.

**Mitigation**:
- Verify system prompt is actually used by agent
- Test that agent follows prompt direction to use export_data for finalization
- Monitor LLM decision-making behavior with new system prompt integration

### 5. Configuration & Initialization Risk (LOW)

**Risk**: create_react_agent() signature might require different parameters than custom graph builder.

**Mitigation**:
- Check documentation carefully
- Create isolated test to understand API
- Update main.py accordingly
- Test app startup and graph compilation

### 6. Event Streaming Compatibility Risk (MEDIUM)

**Risk**: astream_events() event names/structure might differ, breaking websocket_handler event processing.

**Mitigation**:
- Capture actual events from prebuilt agent before migrating handler
- Create event compatibility test
- Update handler if structure differs
- Ensure token streaming still works
- Ensure tool events still emit correctly

### 7. Tool Constraint Risk (MEDIUM)

**Risk**: create_react_agent() might auto-include tools beyond onboarding set, affecting agent behavior.

**Mitigation**:
- Verify only [read_data, write_data, rag_search, export_data] are available
- If auto-inclusion happens, verify it doesn't interfere with onboarding flow
- Test that agent still calls export_data for finalization

## Testing Strategy

### Unit Tests (Keep & Extend)

**Existing**: `backend/tests/unit/test_websocket_schemas.py`
- Verify schemas still validate correctly
- Add tests for message serialization/deserialization

**New Tests**:
- `test_create_react_agent_basic.py` - Verify agent creation
- `test_create_react_agent_tools.py` - Verify tool binding and execution
- `test_create_react_agent_events.py` - Verify event streaming

### Integration Tests (Update & Add)

**Update Existing**:
- `backend/tests/integration/test_onboarding_graph_workflow.py` - Ensure complete flow still works
- `backend/tests/integration/test_onboarding_persistence.py` - Ensure state persists

**New**:
- `test_create_react_agent_websocket_compatibility.py` - Verify WebSocket handler still works
- `test_create_react_agent_vs_custom_graph.py` - Compare outputs

### End-to-End Tests

1. WebSocket Client → New Graph → WebSocket Server → Verify Messages
2. Onboarding Flow: Collect Data → Use Tools → Export → Verify JSON File
3. Tool Execution: Verify read_data, write_data, rag_search, export_data all work
4. Error Handling: Test validation errors, missing fields, access denied

### Frontend Integration Tests

1. Connect frontend client to new graph endpoint
2. Run through onboarding flow via UI
3. Verify tool calls display correctly
4. Verify data is collected and exported
5. Verify error messages display correctly

### Regression Tests

1. Verify chat endpoint `/ws/chat` still works (custom graph unchanged)
2. Verify conversation history still persists
3. Verify other tools still work (multiply, add, RAG search)

## Summary of API Contracts

### Preserved API Contracts (MUST NOT BREAK)

1. **WebSocket Endpoint**: `/ws/onboarding` endpoint signature and authentication
2. **Client Messages**: ClientMessage schema (type, conversation_id, content)
3. **Server Messages**: ServerTokenMessage, ServerCompleteMessage, ServerErrorMessage, ServerToolStartMessage, ServerToolCompleteMessage
4. **Error Codes**: INVALID_FORMAT, ACCESS_DENIED, LLM_ERROR, INTERNAL_ERROR
5. **State Fields**: All ConversationState fields must be gettable/settable
6. **Tool Interfaces**: read_data, write_data, export_data, rag_search signatures and return types
7. **Tool Validation**: Write_data field validation rules must remain same
8. **Export Location**: /app/onboarding_data/{conversation_id}.json

### Implementation Details (CAN BE CHANGED)

1. Graph structure (custom nodes vs prebuilt)
2. Event handling (if event types are mapped correctly)
3. System prompt injection mechanism (if result is same)
4. Tool binding mechanism (if tools execute the same)

### Key Questions to Answer Before Implementation

1. Does `create_react_agent()` accept ConversationState as state_schema?
2. Does it support async tools?
3. Does it handle tool binding internally or accept pre-bound tools?
4. How is system prompt passed (parameter or state injection)?
5. Are events emitted via astream_events() with same names as custom graph?
6. Does it support checkpointing with AsyncMongoDBSaver?
7. Can we constrain tools to onboarding set only?
8. Does state management work with custom fields (employee_name, etc)?

---

**Document Status**: Initial API Contract Analysis
**Date**: 2025-10-30
**Scope**: WebSocket API, message schemas, state contract, tool interfaces, event streaming
**Focus**: Backward compatibility and breaking change identification
