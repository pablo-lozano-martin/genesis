# Data Flow Analysis: Onboarding Agent Migration to create_react_agent

## Request Summary

Issue #18 proposes migrating the current onboarding agent from a manually-constructed ReAct pattern (using StateGraph with ToolNode and tools_condition) to LangGraph's prebuilt `create_react_agent` function. The migration aims to simplify the graph construction while maintaining the same data flow behavior: proactive agent-driven data collection through natural conversation, tool-based state mutations, and JSON export.

---

## Relevant Files & Modules

### Core Graph Files
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/onboarding_graph.py` - Current ReAct-based onboarding graph with system prompt injection
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/streaming_chat_graph.py` - Streaming chat graph for reference (uses ToolNode pattern)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/chat_graph.py` - Non-streaming chat graph for reference

### State & Domain
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/state.py` - ConversationState extends MessagesState with onboarding fields
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/user.py` - User domain model
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/conversation.py` - Conversation domain model

### Tools (Data Collection & Export)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/write_data.py` - Validates and writes onboarding fields to state (employee_name, employee_id, starter_kit, etc.)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/read_data.py` - Queries collected fields from state for agent decision-making
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/export_data.py` - Exports complete data, generates LLM summary, saves JSON to /app/onboarding_data/{conversation_id}.json
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/rag_search.py` - Retrieves knowledge base documents for answering questions

### Prompts & Configuration
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/prompts/onboarding_prompts.py` - System prompt guiding ReAct agent behavior
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tool_metadata.py` - Tool registry for tracking tool sources

### WebSocket & API Layer
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_router.py` - WebSocket endpoint (/ws/onboarding) setup
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py` - WebSocket message handling and streaming via astream_events()
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_schemas.py` - Message protocol schemas

### LLM & Checkpointing
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/provider_factory.py` - LLM provider factory
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/database/mongodb.py` - MongoDB connection setup
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/state_retrieval.py` - Helper to retrieve messages from checkpoints

### Tests
- `/Users/pablolozano/Mac Projects August/genesis/backend/tests/unit/test_onboarding_state.py` - State schema tests
- `/Users/pablolozano/Mac Projects August/genesis/backend/tests/integration/test_onboarding_graph_workflow.py` - Graph workflow tests (system prompt injection, tool orchestration, state persistence)

### Key Functions & Classes
- `create_onboarding_graph()` - Constructs ReAct graph with system prompt injection
- `inject_system_prompt()` - Node that prepends ONBOARDING_SYSTEM_PROMPT if not present
- `ConversationState` - TypedDict extending MessagesState with onboarding fields
- `write_data()` - Tool async function with Pydantic validation
- `read_data()` - Tool async function for state queries
- `export_data()` - Tool async function for data finalization and JSON export
- `rag_search()` - Tool async function for knowledge base queries
- `handle_websocket_chat()` - WebSocket handler that streams events from graph
- `call_llm()` - Node that invokes LLM with tools from config

---

## Current Data Flow Overview

### Architecture Pattern
The onboarding system uses **LangGraph-first architecture** with automatic checkpointing to MongoDB. Data flows through typed state (ConversationState) at every step, with message history and onboarding fields persisted automatically by the checkpointer.

### Current Graph Structure (ReAct Pattern)
```
START
  ↓
process_input (validates messages exist in state)
  ↓
inject_system_prompt (prepends SystemMessage if needed)
  ↓
call_llm (invokes LLM with tools, via RunnableConfig)
  ↓
tools_condition (conditional edge)
  ├─ YES: tools → ToolNode (executes write_data, read_data, export_data, rag_search)
  │  └─ tools → call_llm (loops back for next reasoning step)
  └─ NO: END (no more tool calls)
```

### Data Entry Points

#### 1. WebSocket Message Input
- **Source**: `/ws/onboarding` WebSocket endpoint in `websocket_router.py`
- **Flow**:
  - Client sends `{"type": "message", "conversation_id": "uuid", "content": "..."}` via WebSocket
  - `websocket_handler.py` validates against `ClientMessage` schema
  - Creates `HumanMessage(content=...)` in `handle_websocket_chat()`
  - Passes to graph as input state: `{"messages": [HumanMessage], "conversation_id": "...", "user_id": "..."}`
- **Data Representation**: Raw text string becomes `HumanMessage` (LangChain BaseMessage type)

#### 2. Initial State Injection
- **Source**: `handle_websocket_chat()` in `websocket_handler.py`
- **Components**:
  - `conversation_id`: UUID from database (AppDatabase)
  - `user_id`: UUID from JWT token via authentication
  - `messages`: List containing single HumanMessage
  - All onboarding fields default to None on first invocation
- **Persistence Context**: RunnableConfig passes `thread_id=conversation.id` to checkpointer for resumption

---

## Transformation Layers

### Layer 1: Input Validation (process_input node)
- **Input**: ConversationState with messages field
- **Validation**: Ensures messages list is not empty
- **Output**: Empty dict (no state mutation), passes control to next node
- **Data Integrity**: Fails with ValueError if no messages (protects against malformed input)

### Layer 2: System Prompt Injection (inject_system_prompt node)
- **Input**: ConversationState.messages (list of BaseMessage)
- **Check**: Is first message a SystemMessage?
- **Action**: If NO, prepend `SystemMessage(content=ONBOARDING_SYSTEM_PROMPT)`
- **Output**: `{"messages": [system_message]}` (MessagesState reducer prepends this)
- **Design Rationale**: System prompt ensures LLM acts as proactive onboarding agent throughout entire conversation
- **Immutability**: Doesn't modify user messages, only adds system instruction once

### Layer 3: LLM Invocation (call_llm node)
- **Input**: ConversationState.messages (includes system prompt + conversation history)
- **Tool Binding**:
  - Tools come from graph metadata (`graph._tools`) or RunnableConfig (`configurable.tools`)
  - For onboarding: `[read_data, write_data, rag_search, export_data]`
  - All tools are async functions with structured inputs
- **LLM Processing**:
  - `llm_provider.bind_tools(tools, parallel_tool_calls=False)` - single tool per turn
  - Calls `llm_provider_with_tools.generate(messages)` - returns AIMessage or AIMessage with tool_calls
- **Output**: `{"messages": [ai_message]}` - AIMessage appended to messages list
- **Tool Call Representation**: AIMessage can contain `tool_calls` list with structure: `{"name": "...", "args": {...}, "id": "..."}`

### Layer 4: Tool Execution (ToolNode + tools_condition)
- **Conditional Edge**: `tools_condition` routes based on AIMessage.tool_calls presence
  - If tool_calls exist: Route to ToolNode
  - If no tool_calls: Route to END
- **ToolNode Execution**:
  - Receives AIMessage with tool_calls
  - Executes each tool (sequentially due to `parallel_tool_calls=False`)
  - Creates ToolMessage for each result
  - Returns `{"messages": [tool_message1, tool_message2, ...]}`
- **Tool Result Transformation**:
  - Tool outputs (dicts) become ToolMessage.content (JSON strings)
  - Each ToolMessage linked to AIMessage via tool_call id

### Layer 5: State Mutations via Tools

#### write_data Tool
- **Input**: `(state: ConversationState, field_name: str, value: Any)`
- **Validation**: Pydantic schema validates field existence and value constraints
  - Numeric constraints (min_length, max_length)
  - Enum validation for starter_kit: ["mouse", "keyboard", "backpack"]
  - Boolean type checking for meeting_scheduled
- **Mutation**: Direct state mutation: `state[field_name] = validated_value`
- **Output**: Success dict: `{"field_name": "...", "value": "...", "status": "success"}`
- **Error Handling**: Returns error dict with valid_values for retry guidance
- **Side Effects**: State persisted automatically by checkpointer after tool execution

#### read_data Tool
- **Input**: `(state: ConversationState, field_names: Optional[List[str]] = None)`
- **Query Logic**: Returns current values for requested fields (all if None specified)
- **Output**: Dict with field names and values: `{"employee_name": "...", "status": "success"}`
- **No Side Effects**: Pure query, doesn't modify state

#### rag_search Tool
- **Input**: `(query: str)`
- **Retrieval**: Vector similarity search on ChromaDB knowledge base
- **Output**: Formatted string with top-k documents and relevance scores
- **No State Mutation**: Provides context for LLM reasoning only
- **Error Handling**: Returns "Knowledge base service not available" if vector store missing

#### export_data Tool
- **Input**: `(state: ConversationState, confirmation_message: Optional[str] = None)`
- **Completeness Check**: Validates required fields present (employee_name, employee_id, starter_kit)
- **Summary Generation**:
  - Calls LLM with prompt describing collected data
  - LLM returns markdown summary (2-3 bullet points)
- **State Mutation**: `state["conversation_summary"] = summary_text`
- **File Export**:
  - Creates JSON file at `/app/onboarding_data/{conversation_id}.json`
  - Includes all fields, timestamp, user_id, conversation_id
- **Output**: Success dict with file_path and summary, or error dict with missing_fields

---

## Persistence Layer

### Automatic Checkpointing via AsyncMongoDBSaver

**Connection Path**:
- Database: MongoDB instance specified in environment (typically mongodb://localhost:27017 or Docker container)
- Collections: `langgraph` database stores all checkpoints

**What Gets Persisted**:
- Complete ConversationState (all fields)
- Entire messages list (all BaseMessage types: HumanMessage, AIMessage, ToolMessage, SystemMessage)
- Thread ID: conversation_id (maps to LangGraph thread_id in config)
- Timestamps and checkpoint metadata

**When Checkpointing Occurs**:
1. After each node execution
2. After each tool execution (tool results create ToolMessage)
3. Automatically on state updates from tools
4. No explicit save() calls needed - LangGraph handles this

**State Retrieval**:
- `graph.aget_state(config)` - Get current state for a conversation
- State persistence enabled by `graph.compile(checkpointer=checkpointer)`
- RunnableConfig with `thread_id` maps to specific conversation checkpoint

**Resumption Flow**:
1. User reconnects with same conversation_id
2. RunnableConfig passes `thread_id: conversation_id`
3. Checkpointer loads last state
4. Next invocation continues from checkpoint
5. No message loss between sessions

---

## Data Exit Points

### 1. WebSocket Token Streaming
- **Source**: `graph.astream_events()` in `handle_websocket_chat()`
- **Event Types**:
  - `on_chat_model_stream`: LLM tokens (chunk.content)
  - `on_chat_model_end`: Full AIMessage (check for tool_calls)
  - `on_tool_start`: Tool execution beginning (uses cached current_tool_call)
  - `on_tool_end`: Tool result completion
- **Transformation**: Events → WebSocket messages via schemas
  - `ServerTokenMessage(content="token")` - Individual tokens
  - `ServerToolStartMessage(tool_name, tool_input, source)` - Tool invocation
  - `ServerToolCompleteMessage(tool_name, tool_result, source)` - Tool completion
  - `ServerCompleteMessage(conversation_id)` - End of response
- **Frontend Consumption**: Frontend receives token stream and rebuilds complete response

### 2. Export Data File
- **Source**: `export_data` tool, called by agent via tool_calls
- **File Path**: `/app/onboarding_data/{conversation_id}.json` (Docker volume mount)
- **Contents**:
  ```json
  {
    "conversation_id": "uuid",
    "user_id": "uuid",
    "employee_name": "string",
    "employee_id": "string",
    "starter_kit": "mouse|keyboard|backpack",
    "dietary_restrictions": "string|null",
    "meeting_scheduled": "bool|null",
    "conversation_summary": "markdown string",
    "exported_at": "ISO 8601 timestamp"
  }
  ```
- **Persistence**: Direct file I/O (not in MongoDB)
- **Accessibility**: Via Docker host mount at `./onboarding_data/`

### 3. Message History Access
- **Source**: `get_conversation_messages()` in `state_retrieval.py`
- **Path**: RunnableConfig → graph.aget_state() → checkpoint retrieval
- **Return**: List[BaseMessage] from checkpoint (system, human, AI, tool messages)
- **Frontend Usage**: Historical message context (filtered to exclude ToolMessages)

---

## State Structure in ConversationState

```python
class ConversationState(MessagesState):
    """
    Extends LangGraph's MessagesState with onboarding-specific fields.
    """
    # From MessagesState (inherited)
    messages: List[BaseMessage]  # Auto-managed by reducer

    # Conversation metadata
    conversation_id: str
    user_id: str

    # Onboarding data fields (collected via tools)
    employee_name: Optional[str] = None
    employee_id: Optional[str] = None
    starter_kit: Optional[str] = None
    dietary_restrictions: Optional[str] = None
    meeting_scheduled: Optional[bool] = None
    conversation_summary: Optional[str] = None
```

**State Field Lifecycle**:
1. **Initial**: conversation_id, user_id set from API; all onboarding fields None
2. **During Conversation**: Agent uses write_data tool to populate onboarding fields
3. **Persistence**: Checkpointer saves full state after each tool execution
4. **Export**: export_data reads all fields, generates summary, creates JSON file
5. **Final**: conversation_summary populated; state persisted to checkpoint

**Messages Field Special Handling**:
- Inherits MessagesState reducer behavior (add_messages)
- Automatically appends new messages (doesn't replace entire list)
- Preserves message history for multi-turn conversations
- Includes system messages, human messages, AI messages, tool messages

---

## Impact Analysis: Migration to create_react_agent

### What create_react_agent Does

LangGraph's `create_react_agent()` is a prebuilt factory that:
- Constructs a ReAct graph internally
- Returns a compiled graph ready to invoke
- Handles tool binding and conditional routing automatically
- Maintains the same ReAct loop (think → act → think) as manual construction

### Expected Graph Structure from create_react_agent

```
Based on LangGraph documentation, create_react_agent likely produces:
START
  ↓
agent node (equivalent to call_llm)
  ↓
tools_condition
  ├─ YES: tools (ToolNode)
  │  └─ agent (loops back)
  └─ NO: END
```

### Data Flow Compatibility

**Compatible Aspects** (No Changes Needed):
- ✅ ConversationState remains unchanged - create_react_agent accepts any state schema
- ✅ Tools don't change - they work with any ReAct loop
- ✅ Tool signatures stay same - `(state, **kwargs) → dict`
- ✅ Message handling unchanged - BaseMessage types persist
- ✅ Checkpointer integration same - compiled graph accepts checkpointer
- ✅ RunnableConfig flow same - tools receive state via parameter
- ✅ WebSocket streaming same - astream_events() works with any compiled graph

**Potentially Breaking Aspects**:
1. **System Prompt Injection**
   - Current: Dedicated `inject_system_prompt` node in graph
   - Problem: create_react_agent likely doesn't expose system prompt injection point
   - Solution: Must be handled at LLM provider level or via different mechanism (see below)

2. **Tool Access in call_llm**
   - Current: Tools passed via RunnableConfig `configurable.tools`
   - Risk: create_react_agent may auto-discover tools differently
   - Mitigation: May need to bind tools during graph creation instead

3. **Graph Metadata Storage**
   - Current: `compiled_graph._tools = tools` stores tools for later access
   - Risk: create_react_agent may not expose _tools attribute
   - Impact: WebSocket handler uses `graph._tools` to pass to call_llm - may break

### Migration Challenges

#### Challenge 1: System Prompt Injection Removal
**Current Approach**:
```python
def inject_system_prompt(state: ConversationState) -> dict:
    if not (state.get("messages") and isinstance(state["messages"][0], SystemMessage)):
        return {"messages": [SystemMessage(content=ONBOARDING_SYSTEM_PROMPT)]}
    return {}
```

**Problem**: create_react_agent doesn't expose a dedicated prompt injection node

**Solutions** (in priority order):
1. **Use LLMProvider's system message injection**
   - Modify LLMProvider to accept a system_prompt parameter
   - Every call to llm_provider includes system prompt in initial messages
   - Pros: Clean, LLM-agnostic, reusable
   - Cons: Requires changes to provider interface

2. **Wrap create_react_agent output with custom system prompt node**
   - Get graph from create_react_agent
   - Add inject_system_prompt node at START before agent node
   - Re-compile the graph
   - Pros: Minimal changes, explicit control
   - Cons: Modifies prebuilt graph structure, requires graph manipulation

3. **Embed system prompt in initial state before graph invocation**
   - WebSocket handler checks if first message is system message
   - If not, prepends SystemMessage before calling graph.ainvoke()
   - Pros: Simplest, no graph changes
   - Cons: System logic moves outside graph, harder to debug

**Recommendation**: Solution #2 (wrap prebuilt graph) maintains explicit control and keeps graph structure clear. If create_react_agent provides hook for system messages, use that instead.

#### Challenge 2: Tool Configuration Passing
**Current**:
```python
# In create_onboarding_graph
compiled_graph._tools = tools  # Store for later access

# In call_llm node
config_tools = config.get("configurable", {}).get("tools")
if config_tools is not None:
    all_tools = config_tools
```

**Problem**: create_react_agent likely expects tools at graph creation, not via config

**Solution**:
```python
# Instead of:
graph = create_onboarding_graph(checkpointer, tools=[read_data, write_data, ...])

# Will become:
graph = create_react_agent(
    model=llm_provider_with_tools,
    tools=[read_data, write_data, ...],
    checkpointer=checkpointer
)
```

**Migration Steps**:
1. Get LLMProvider instance
2. Bind onboarding tools to LLM at graph creation
3. Pass bound LLM to create_react_agent
4. Remove tools from RunnableConfig in WebSocket handler
5. Remove `call_llm` node modifications that look for config.tools

#### Challenge 3: State Schema Compatibility
**Current**: create_onboarding_graph accepts ConversationState

**Risk**: create_react_agent may have specific state schema requirements

**Verification Needed**: Check LangGraph docs for:
- Does create_react_agent accept custom state schemas?
- If yes, ConversationState works unchanged
- If no, may need to extend returned graph or modify state approach

#### Challenge 4: WebSocket Handler Integration
**Current**:
```python
tools = getattr(graph, '_tools', None)
config = RunnableConfig(configurable={"tools": tools})
```

**After Migration**:
```python
# If tools are bound at graph creation, this config line can be removed:
config = RunnableConfig(configurable={"thread_id": conversation.id, "llm_provider": llm_provider})
```

**Impact**: Simplifies WebSocket handler, removes graph metadata access

---

## Employee Data Flow (Complete Journey)

### 1. Initial Collection (WebSocket to State)
```
Client Input: "My name is John Doe, ID is EMP-123, I want a keyboard"
     ↓
HumanMessage: Created in websocket_handler
     ↓
Graph Input State:
  {
    "messages": [HumanMessage(content="My name is...")],
    "conversation_id": "conv-xyz",
    "user_id": "user-abc",
    "employee_name": None,  # Not yet collected
    "employee_id": None,
    "starter_kit": None
  }
     ↓
call_llm: LLM receives all previous messages + new HumanMessage
     ↓
LLM Output: AIMessage with tool_calls for write_data
     ↓
write_data Executions (3 calls, sequential):
  1. write_data(state, "employee_name", "John Doe")
     → Validates: len(name) in [1, 255] ✓
     → Result: {"status": "success", "value": "John Doe"}
     → State Update: state["employee_name"] = "John Doe"

  2. write_data(state, "employee_id", "EMP-123")
     → Validates: len(id) in [1, 50] ✓
     → Result: {"status": "success", "value": "EMP-123"}
     → State Update: state["employee_id"] = "EMP-123"

  3. write_data(state, "starter_kit", "keyboard")
     → Validates: value.lower() in ["mouse", "keyboard", "backpack"] ✓
     → Result: {"status": "success", "value": "keyboard"}
     → State Update: state["starter_kit"] = "keyboard"
     ↓
Tool Results Wrapped: ToolMessage for each write_data call
     ↓
Checkpoint: State persisted with all three fields populated
     ↓
LLM Sees Tool Results: AIMessage with tool_calls → ToolMessages → new AIMessage
```

### 2. Validation & Retry (Error Path)
```
User Input: "I want a laptop"
     ↓
write_data(state, "starter_kit", "laptop")
     → Validation Error: "laptop" not in ["mouse", "keyboard", "backpack"]
     → Result: {
         "status": "error",
         "message": "Invalid starter_kit value 'laptop'...",
         "valid_values": ["mouse", "keyboard", "backpack"]
       }
     ↓
ToolMessage: Contains error details
     ↓
LLM Receives Error: Sees valid_values in error message
     ↓
LLM Reasoning: "The user wants a laptop, but only [mouse, keyboard, backpack] are valid..."
     ↓
LLM Next Tool Call: write_data with value="keyboard" (corrected)
```

### 3. Verification & Export (Completion Path)
```
Agent: "Let me verify what we've collected..."
     ↓
read_data(state, ["employee_name", "employee_id", "starter_kit"])
     → Returns: {
         "employee_name": "John Doe",
         "employee_id": "EMP-123",
         "starter_kit": "keyboard",
         "status": "success"
       }
     ↓
Agent: "Everything looks good! Let me finalize..."
     ↓
export_data(state)
     → Checks: All required fields present ✓
     → Generates Summary: LLM call with collected data
     → Summary Result: "- Employee John Doe (EMP-123) onboarded\n- Hardware: keyboard\n..."
     → State Update: state["conversation_summary"] = summary
     → File Creation: /app/onboarding_data/conv-xyz.json with all fields
     → Result: {
         "status": "success",
         "file_path": "/app/onboarding_data/conv-xyz.json",
         "summary": "- Employee..."
       }
     ↓
Final Checkpoint: State persisted with summary
     ↓
WebSocket: ServerCompleteMessage sent to frontend
```

---

## Checkpointer Integration & State Persistence Patterns

### Connection Lifecycle

#### 1. Graph Creation (Startup)
```python
# In main.py or app initialization
from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver

checkpointer_context = AsyncMongoDBSaver.from_conn_string(
    "mongodb://localhost:27017/genesis_langgraph"
)
checkpointer = await checkpointer_context.__aenter__()

graph = create_onboarding_graph(checkpointer, tools=[...])
app.state.onboarding_graph = graph
```

#### 2. Per-Invocation Configuration
```python
# In websocket_handler.py when handling message
config = RunnableConfig(
    configurable={
        "thread_id": conversation.id,  # Maps to conversation_id
        "llm_provider": llm_provider,
        "user_id": user.id,
        "tools": tools  # Will change after migration
    }
)
```

#### 3. State Persistence (Automatic)
```
Each node/tool execution:
  1. Node computes result dict
  2. MessagesState reducer merges messages
  3. Other fields merged into state
  4. Checkpointer.put() called by LangGraph
  5. MongoDB persists full state snapshot
```

#### 4. State Retrieval (Resumption)
```python
# Next user message same conversation
config = RunnableConfig(configurable={"thread_id": conversation.id, ...})
graph.ainvoke(new_input, config)
# Checkpointer loads previous state
# Graph starts from checkpoint, not fresh state
```

### Multi-Turn Persistence Example

**Turn 1**:
```
Input: {"messages": [HumanMessage("What's required?")]}
Tool Calls: read_data()
State After: messages=[Human, System, AI], (fields unchanged)
Checkpoint: Saved with 3 messages
```

**Turn 2** (Same conversation_id):
```
Load From Checkpoint: Retrieves state with 3 messages
Input: {"messages": [HumanMessage("My name is Alice")]}
MessagesState Reducer: Appends new HumanMessage
Process Input: 4 messages in state now
Tool Calls: write_data("employee_name", "Alice")
State After: messages=[Human, System, AI, Human, AI], employee_name="Alice"
Checkpoint: Saved with 5 messages and employee_name
```

**Turn 3** (Resume Again):
```
Load From Checkpoint: 5 messages, employee_name="Alice" restored
Input: {"messages": [HumanMessage("My ID is EMP-456")]}
Tool Calls: write_data("employee_id", "EMP-456")
State After: Messages appended, both employee_name and employee_id persisted
```

### Checkpoint Schema (MongoDB Structure)

```
Collection: checkpoints
Document Structure:
{
  "thread_id": "conv-xyz",  # Maps to conversation_id
  "checkpoint_id": "1724003200.0-0",  # Timestamp + sequence
  "timestamp": "2024-10-30T...",
  "values": {  # Full ConversationState
    "messages": [
      {"type": "system", "content": "You are an onboarding assistant..."},
      {"type": "human", "content": "My name is John..."},
      {"type": "ai", "content": "...", "tool_calls": [...]},
      {"type": "tool", "content": "{...}", "tool_call_id": "..."},
      ...
    ],
    "conversation_id": "conv-xyz",
    "user_id": "user-abc",
    "employee_name": "John Doe",
    "employee_id": "EMP-123",
    "starter_kit": "keyboard",
    "dietary_restrictions": null,
    "meeting_scheduled": null,
    "conversation_summary": null
  },
  "next_id": 2,
  "config": {...}
}
```

---

## Message Flow & Transformation

### Message Types in Conversation
1. **SystemMessage** - ONBOARDING_SYSTEM_PROMPT (injected once at start)
2. **HumanMessage** - User inputs from WebSocket (created per turn)
3. **AIMessage** - LLM responses (may contain tool_calls or just content)
4. **ToolMessage** - Results from tool execution (linked to tool_call id)

### Message Transformation Pipeline

```
Raw Text (WebSocket)
  ↓
ClientMessage (validated Pydantic)
  ↓
HumanMessage(content=...) [LangChain type]
  ↓
State: {"messages": [previous messages, HumanMessage]}
  ↓
call_llm invokes LLM with all messages as context
  ↓
AIMessage response (may include tool_calls)
  ↓
tools_condition checks AIMessage.tool_calls
  ↓
ToolNode executes each tool, wraps result in ToolMessage
  ↓
ToolMessage: {"content": json.dumps(tool_result), "tool_call_id": "..."}
  ↓
Next iteration: call_llm receives [System, Human, AI, Tool, Human, AI, ...] messages
  ↓
Checkpoint persists entire message chain
```

### WebSocket Event Streaming

```
graph.astream_events() event stream → WebSocket messages

Events received:
  - "on_chat_model_stream": chunk.content
    → ServerTokenMessage(type="token", content="<token>")

  - "on_chat_model_end": output (AIMessage with tool_calls)
    → Cache tool_call info for upcoming tool events

  - "on_tool_start": tool execution begins
    → ServerToolStartMessage(tool_name, tool_input, source)

  - "on_tool_end": tool result available
    → ServerToolCompleteMessage(tool_name, tool_result, source)

  - Final: No more events
    → ServerCompleteMessage(conversation_id)
```

---

## Data Validation & Error Handling

### Validation Layers

#### 1. Input Message Validation
- **Location**: `process_user_input` node
- **Check**: `messages` list not empty
- **Failure**: Raises ValueError, caught by WebSocket handler
- **Response**: ServerErrorMessage(code="INTERNAL_ERROR")

#### 2. ClientMessage Schema Validation
- **Location**: `handle_websocket_chat` WebSocket handler
- **Schema**: Pydantic ClientMessage
  - `type: MessageType.MESSAGE`
  - `conversation_id: str` (required)
  - `content: str` (min_length=1, required)
- **Failure**: JSON decode error or validation error
- **Response**: ServerErrorMessage(code="INVALID_FORMAT")

#### 3. Onboarding Field Validation
- **Location**: `write_data` tool
- **Schema**: OnboardingDataSchema (Pydantic)
  - `employee_name`: min_length=1, max_length=255
  - `employee_id`: min_length=1, max_length=50
  - `starter_kit`: Must be in ["mouse", "keyboard", "backpack"] (case-insensitive)
  - `dietary_restrictions`: max_length=500
  - `meeting_scheduled`: Must be boolean
  - `conversation_summary`: No constraints
- **Failure**: ValidationError from Pydantic
- **Response**: `{"status": "error", "message": "...", "valid_values": [...]}`
- **Agent Retry**: LLM sees error details, retries with corrected value
- **Persistence**: Failed attempt logged but state unchanged

#### 4. Export Data Validation
- **Location**: `export_data` tool
- **Check**: Required fields present
  - `employee_name` not None
  - `employee_id` not None
  - `starter_kit` not None
- **Failure**: Missing required field
- **Response**: `{"status": "error", "missing_fields": [...], "required_fields": [...]}`
- **Agent Routing**: Agent collects missing fields before next export attempt

#### 5. Conversation Authorization
- **Location**: `handle_websocket_chat` WebSocket handler
- **Check**: `conversation_repository.get_by_id(conversation_id)` → verify `conversation.user_id == user.id`
- **Failure**: Access denied
- **Response**: ServerErrorMessage(code="ACCESS_DENIED")
- **Purpose**: Prevents users from accessing other users' conversations

---

## Export Data Flow in Detail

### File Export Architecture

#### 1. Trigger Point
- **Source**: Agent calls `export_data` tool via tool_calls
- **Precondition**: All required fields (employee_name, employee_id, starter_kit) must be present
- **Decision**: Agent decides when to call export_data based on:
  - User confirmation: "Yes, finalize the onboarding"
  - System prompt guidance: "When user confirms, call export_data"

#### 2. Data Collection Phase
```python
# In export_data tool
required_fields = {
    "employee_name": state.get("employee_name"),
    "employee_id": state.get("employee_id"),
    "starter_kit": state.get("starter_kit")
}

optional_fields = {
    "dietary_restrictions": state.get("dietary_restrictions"),
    "meeting_scheduled": state.get("meeting_scheduled")
}

# Validate completeness
missing_required = [k for k, v in required_fields.items() if v is None]
if missing_required:
    return {"status": "error", "missing_fields": missing_required}
```

#### 3. Summary Generation Phase
```python
# LLM call to summarize conversation
summary_prompt = f"""Summarize this onboarding conversation...
Employee Information:
- Name: {required_fields['employee_name']}
- ID: {required_fields['employee_id']}
- Starter Kit: {required_fields['starter_kit']}
..."""

summary_response = await llm_provider.generate([HumanMessage(summary_prompt)])
summary_text = summary_response.content
```

#### 4. State Update Phase
```python
# Update state with generated summary
state["conversation_summary"] = summary_text
# Automatically persisted by checkpointer after tool execution
```

#### 5. File Creation Phase
```python
# Create JSON export
export_dir = Path("/app/onboarding_data")
export_dir.mkdir(exist_ok=True)

export_data_dict = {
    "conversation_id": conversation_id,
    "user_id": user_id,
    "employee_name": required_fields["employee_name"],
    "employee_id": required_fields["employee_id"],
    "starter_kit": required_fields["starter_kit"],
    "dietary_restrictions": optional_fields["dietary_restrictions"],
    "meeting_scheduled": optional_fields["meeting_scheduled"],
    "conversation_summary": summary_text,
    "exported_at": datetime.utcnow().isoformat()
}

filepath = export_dir / f"{conversation_id}.json"
with open(filepath, "w") as f:
    json.dump(export_data_dict, f, indent=2)
```

#### 6. Result Return Phase
```python
return {
    "status": "success",
    "message": "Onboarding data exported successfully",
    "file_path": str(filepath),
    "summary": summary_text
}
```

### Data Persistence in JSON File
- **Location**: Docker volume at `/app/onboarding_data/{conversation_id}.json`
- **Ownership**: Accessible to any service with volume mount
- **Format**: Human-readable JSON with proper indentation
- **Timestamp**: ISO 8601 UTC timestamp for tracking
- **Completeness**: All collected data in single file (no normalization)

---

## Offboarding Data Flow Comparison

### Offboarding Graph Status
**Current State**: No offboarding graph currently exists in the codebase

**Assumptions for Migration Planning**:
- If offboarding were to be implemented, it would likely use same pattern as chat_graph or streaming_chat_graph
- Onboarding uses custom ReAct pattern with system prompt injection (unique to onboarding)
- Offboarding would probably not need system prompt injection (no proactive collection pattern needed)

### If Offboarding Migrated to create_react_agent

**Compatibility**:
- Would be simpler than onboarding (no system prompt injection needed)
- Could directly use create_react_agent without wrapper
- Same state persistence patterns apply
- Same WebSocket handler works for both

**Key Differences from Onboarding**:
- Likely no dedicated system prompt (agent role defined differently)
- Different tools (exit_survey, confirm_departing, export_exit_checklist)
- Different state fields (departure_date, forwarding_address, equipment_return_status, etc.)
- No multi-step data collection (likely more of a checklist/verification flow)

---

## Implementation Guidance

### Phase 1: Research & Verification
1. **Verify create_react_agent signature and requirements**
   - Check LangGraph docs: Does it accept custom state schemas?
   - Does it expose system message injection point?
   - What is the exact signature? `create_react_agent(model, tools, checkpointer=None, ...)`

2. **Test with simple example**
   - Create minimal test graph using create_react_agent
   - Verify message persistence works
   - Verify tool execution works
   - Verify state schema compatibility

3. **Identify system prompt injection approach**
   - Option A: LLMProvider modification (requires provider changes)
   - Option B: Wrapper node approach (wrap prebuilt graph)
   - Option C: Pre-state injection (system message before invocation)
   - Recommend testing all three approaches

### Phase 2: Refactoring
1. **Create new factory function**: `create_onboarding_graph_react_agent()`
   - Uses create_react_agent internally
   - Handles system prompt injection (chosen approach from Phase 1)
   - Returns compiled graph with checkpointer

2. **Update imports** in main.py:
   - Switch from `create_onboarding_graph` to new factory
   - Keep graph stored in `app.state.onboarding_graph`

3. **Remove inject_system_prompt node** (if using wrapper approach):
   - Node no longer needed in graph
   - Logic moved to wrapper or LLMProvider

4. **Update call_llm node**:
   - If tools are bound at creation, remove config.tools lookup
   - Simplifies node, removes graph metadata access

5. **Update WebSocket handler**:
   - Remove `getattr(graph, '_tools', None)` logic
   - Simplify RunnableConfig (no tools in configurable)

### Phase 3: Testing
1. **Unit tests**: Update test_onboarding_graph_workflow.py
   - Test system prompt is still injected (approach-dependent)
   - Test tool execution unchanged
   - Test state persistence unchanged

2. **Integration tests**:
   - Full conversation flow (multiple turns)
   - Validation retry logic
   - Export data flow
   - Message history persistence

3. **WebSocket tests**:
   - Token streaming works
   - Tool events generated
   - Multiple connections (different users/conversations)

### Phase 4: Deployment
1. **Backward compatibility**: Ensure checkpoint data readable by new graph
   - Old checkpoints should resume properly
   - If state schema changes, add migration logic

2. **Canary deployment**:
   - Deploy alongside existing implementation
   - Route subset of traffic to new graph
   - Monitor for differences in behavior

3. **Validation**:
   - Manual testing of complete onboarding flow
   - Verify export files created correctly
   - Check message history in checkpoints

---

## Risks & Considerations

### Data Integrity Risks

#### Risk 1: Message History Corruption
- **Scenario**: Migration script fails partway through, leaving incomplete checkpoints
- **Mitigation**: Don't modify existing checkpoints; new graph reads old ones unchanged
- **Backup**: Export onboarding_data JSON files before migration (already created by export_data)

#### Risk 2: Tool Binding Loss
- **Scenario**: create_react_agent expects tools at creation; WebSocket passes different tools
- **Mitigation**: Bind tools at graph creation, remove runtime tool passing
- **Verification**: Test with actual tool calls before full deployment

#### Risk 3: System Prompt Loss
- **Scenario**: Forgot to inject system prompt, LLM doesn't behave as onboarding agent
- **Mitigation**: Verify system prompt injection works in chosen approach; add test
- **Fallback**: If lost, agent will still work but won't be proactive

#### Risk 4: State Field Mismatch
- **Scenario**: create_react_agent requires specific state format, ConversationState incompatible
- **Mitigation**: Verify compatibility in Phase 1; test with actual state
- **Workaround**: Wrap state in compatible structure if needed

### Performance Risks

#### Risk 1: Slower Message Processing
- **Scenario**: create_react_agent has overhead vs manual graph
- **Mitigation**: Benchmark both approaches; may not be measurable
- **Acceptable**: Simplicity gain usually worth small performance cost

#### Risk 2: Checkpoint Overhead
- **Scenario**: Each tool execution persists state; multiple tools = multiple persists
- **Current**: Already happens with manual graph (not a new risk)
- **Mitigation**: MongoDB async I/O handles concurrent checkpoints efficiently

### Operational Risks

#### Risk 1: Production Outage During Migration
- **Scenario**: Deploy breaking change, new graph fails to load
- **Mitigation**: Implement feature flag or A/B routing
- **Rollback**: Keep old factory function callable; route back if needed

#### Risk 2: Data Loss from Export Failures
- **Scenario**: export_data doesn't create file, state lost
- **Current Risk**: Agent should retry if export fails; may loop indefinitely
- **Mitigation**: Add timeout or max-attempt logic in system prompt

#### Risk 3: Incomplete Onboarding Export
- **Scenario**: User leaves before export_data called; no JSON file created
- **Current Risk**: Same as today (user can resume later)
- **Mitigation**: Export data is in checkpoint (resumable); JSON optional

---

## Testing Strategy

### Unit Tests (No Database Needed)

```python
def test_onboarding_tools_with_state():
    """Test tools work with ConversationState"""
    state = ConversationState(
        conversation_id="test",
        user_id="test",
        messages=[],
        employee_name=None
    )

    # Mock LangGraph environment
    result = write_data(state, "employee_name", "John Doe")
    assert result["status"] == "success"
    assert state["employee_name"] == "John Doe"

def test_validation_errors():
    """Test write_data validation"""
    state = ConversationState(conversation_id="test", user_id="test", messages=[])

    result = write_data(state, "starter_kit", "invalid")
    assert result["status"] == "error"
    assert "valid_values" in result
    assert result["valid_values"] == ["mouse", "keyboard", "backpack"]

def test_export_data_requires_all_fields():
    """Test export_data validation"""
    state = ConversationState(
        conversation_id="test",
        user_id="test",
        messages=[],
        employee_name="John",  # Missing employee_id and starter_kit
        employee_id=None,
        starter_kit=None
    )

    # Mock LLM provider
    result = export_data(state)
    assert result["status"] == "error"
    assert set(result["missing_fields"]) == {"employee_id", "starter_kit"}
```

### Integration Tests (With MongoDB)

```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_onboarding_system_prompt_injected():
    """Test system prompt is injected in new graph"""
    checkpointer = AsyncMongoDBSaver.from_conn_string(...)
    graph = create_onboarding_graph_react_agent(checkpointer, tools=[...])

    state = {"messages": [HumanMessage("Hi")], "conversation_id": "test", "user_id": "test"}
    result = await graph.ainvoke(state, config)

    # Verify system prompt was added
    assert isinstance(result["messages"][0], SystemMessage)
    assert "onboarding" in result["messages"][0].content.lower()

@pytest.mark.asyncio
@pytest.mark.integration
async def test_multi_turn_with_persistence():
    """Test message history persists across turns"""
    checkpointer = AsyncMongoDBSaver.from_conn_string(...)
    graph = create_onboarding_graph_react_agent(checkpointer, tools=[...])

    # Turn 1
    state1 = {"messages": [HumanMessage("My name is Alice")], "conversation_id": "test", "user_id": "test"}
    config = RunnableConfig(configurable={"thread_id": "test"})
    result1 = await graph.ainvoke(state1, config)

    # Turn 2
    state2 = {"messages": [HumanMessage("My ID is 123")], "conversation_id": "test", "user_id": "test"}
    result2 = await graph.ainvoke(state2, config)

    # Verify history includes both messages
    assert len(result2["messages"]) > len(result1["messages"])
    assert any("Alice" in msg.content for msg in result2["messages"] if hasattr(msg, "content"))

@pytest.mark.asyncio
@pytest.mark.integration
async def test_export_creates_json_file():
    """Test export_data creates JSON file correctly"""
    # Setup complete state with all fields
    state = ConversationState(
        conversation_id="test-export",
        user_id="test-user",
        messages=[],
        employee_name="John Doe",
        employee_id="EMP-123",
        starter_kit="keyboard",
        dietary_restrictions="vegetarian"
    )

    # Mock LLM for summary generation
    result = await export_data(state)

    assert result["status"] == "success"
    assert Path(result["file_path"]).exists()

    # Verify JSON contents
    with open(result["file_path"]) as f:
        data = json.load(f)
        assert data["employee_name"] == "John Doe"
        assert data["employee_id"] == "EMP-123"
        assert data["starter_kit"] == "keyboard"
        assert "exported_at" in data
```

### End-to-End Tests (WebSocket)

```python
@pytest.mark.asyncio
@pytest.mark.e2e
async def test_websocket_onboarding_flow():
    """Test complete onboarding flow via WebSocket"""
    # Start WebSocket connection
    async with connect("ws://localhost:8000/ws/onboarding?token=test") as websocket:
        # Send first message
        await websocket.send_json({
            "type": "message",
            "conversation_id": "test-e2e",
            "content": "My name is Jane Doe"
        })

        # Receive tokens
        tokens = []
        while True:
            msg = await websocket.recv()
            data = json.loads(msg)
            if data["type"] == "token":
                tokens.append(data["content"])
            elif data["type"] == "complete":
                break

        # Verify response received
        response_text = "".join(tokens)
        assert len(response_text) > 0

        # Send second message with ID
        await websocket.send_json({
            "type": "message",
            "conversation_id": "test-e2e",
            "content": "My ID is EMP-789 and I want a mouse"
        })

        # ... continue flow, verify export happens
```

---

## Summary of Key Data Flow Concerns

### What Stays the Same
1. **ConversationState schema** - No changes needed
2. **Tool implementations** - write_data, read_data, export_data, rag_search unchanged
3. **Tool inputs/outputs** - Same signatures and behavior
4. **Checkpointer integration** - MongoDB persistence unchanged
5. **WebSocket protocol** - Client/server messages unchanged
6. **Message history** - BaseMessage types persist as before

### What Changes
1. **Graph construction** - From manual StateGraph to create_react_agent
2. **System prompt injection** - From dedicated node to (TBD) approach
3. **Tool configuration** - From RunnableConfig to graph creation time
4. **Graph metadata** - `graph._tools` no longer needed

### Critical Dependencies
1. **LangGraph version** - Must support create_react_agent and custom state schemas
2. **System prompt injection approach** - Core decision point for migration
3. **LLMProvider interface** - May need updates depending on approach
4. **MongoDB checkpoint schema** - Must remain compatible

### Migration Success Criteria
- All tests pass (unit, integration, E2E)
- Message history persists correctly
- Tools execute with correct state mutations
- System prompt injected (agent behaves proactively)
- Export data creates JSON files
- WebSocket streaming works
- No data loss from existing conversations
- Performance equivalent to original graph
