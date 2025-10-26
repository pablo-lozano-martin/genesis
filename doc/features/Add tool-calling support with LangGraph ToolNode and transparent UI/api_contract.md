# API Contract Analysis: Tool Execution via WebSocket

## Request Summary

This feature adds transparent tool-calling support through LangGraph's ToolNode, enabling the AI assistant to invoke tools (like "multiply") and stream tool execution events to frontend clients. The implementation must extend the WebSocket message protocol to communicate tool lifecycle events (tool start, tool complete) while maintaining backward compatibility with clients that don't handle tool messages.

## Relevant Files & Modules

### Files to Examine
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_schemas.py` - WebSocket message type enumeration and server message schemas
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py` - Core WebSocket handler that streams events from LangGraph; primary integration point for tool events
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_router.py` - WebSocket route definition and dependency injection
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/streaming_chat_graph.py` - LangGraph graph definition with ToolNode and tools_condition routing
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/call_llm.py` - LLM invocation node where tools are bound to LLM provider
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/state.py` - Conversation state extending MessagesState
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/multiply.py` - Example tool implementation
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/llm_provider.py` - LLM provider port interface with bind_tools contract

### Key Functions & Endpoints
- `handle_websocket_chat()` in `websocket_handler.py` - Main WebSocket handler; lines 56-186; uses `graph.astream_events()` loop starting at line 145
- `graph.astream_events(input_data, config, version="v2")` - LangGraph event streaming API called at line 145 of websocket_handler.py
- `create_streaming_chat_graph()` in `streaming_chat_graph.py` - Graph builder; includes ToolNode at line 46
- `call_llm()` in `call_llm.py` - Node that binds tools to LLM provider at line 38

## Current API Contract Overview

### Existing WebSocket Message Types

The WebSocket protocol currently defines the following message types in `websocket_schemas.py`:

**Message Type Enum** (lines 9-17):
```python
class MessageType(str, Enum):
    MESSAGE = "message"      # Client → Server (user input)
    TOKEN = "token"          # Server → Client (streaming token)
    COMPLETE = "complete"    # Server → Client (response finished)
    ERROR = "error"          # Server → Client (error occurred)
    PING = "ping"            # Client → Server (health check)
    PONG = "pong"            # Server → Client (health check response)
```

**Server Message Schemas**:

1. **ServerTokenMessage** (lines 32-40):
   - Used during LLM token streaming
   - Fields: `type` (MESSAGE.TOKEN), `content` (str)
   - Emitted on every token from LLM streaming

2. **ServerCompleteMessage** (lines 43-52):
   - Sent when LLM response is completely generated
   - Fields: `type` (MESSAGE.COMPLETE), `message_id` (str), `conversation_id` (str)
   - Currently sent with `message_id="unknown"` (line 157 in websocket_handler.py)

3. **ServerErrorMessage** (lines 55-64):
   - Sent when any error occurs
   - Fields: `type` (MESSAGE.ERROR), `message` (str), `code` (Optional[str])
   - Error codes used: `INVALID_FORMAT`, `ACCESS_DENIED`, `LLM_ERROR`, `INTERNAL_ERROR`

### WebSocket Event Streaming in Handler

The `handle_websocket_chat()` function (websocket_handler.py lines 56-186) implements the streaming loop:

**Key sections**:
- Line 145: `async for event in graph.astream_events(input_data, config, version="v2")`
- Line 147: Event filtering for `"on_chat_model_stream"` event type
- Lines 148-151: Token extraction and emission via `ServerTokenMessage`
- Lines 155-160: Completion message sent after streaming loop ends

**Current event types being handled**:
- `on_chat_model_stream`: LLM token streaming events from the chat model node

**Missing event types for tool execution**:
- `on_tool_start`: Not currently handled
- `on_tool_end`: Not currently handled
- `on_tool_error`: Not currently handled

### LangGraph Graph Structure

The `create_streaming_chat_graph()` (streaming_chat_graph.py) defines:

**Nodes** (lines 42-46):
1. `process_input` - Validates incoming messages
2. `call_llm` - Invokes LLM with tools bound
3. `tools` - LangGraph's prebuilt `ToolNode` that executes tool calls

**Edges** (lines 48-52):
1. START → `process_input`
2. `process_input` → `call_llm`
3. `call_llm` → (conditional) via `tools_condition`
   - If tool calls: `call_llm` → `tools`
   - If no tool calls: `call_llm` → END
4. `tools` → `call_llm` (loop back to LLM after tool execution)

### Tool Binding Contract

The LLM provider interface (`core/ports/llm_provider.py` lines 62-74) defines:
```python
def bind_tools(self, tools: List[Callable], **kwargs: Any) -> 'ILLMProvider':
    """Bind tools to the LLM provider for tool calling."""
```

Implementations in `openai_provider.py` and `anthropic_provider.py`:
- Call `self.model.bind_tools(tools, **kwargs)` (LangChain method)
- Return a new provider instance with bound model
- Support `parallel_tool_calls=False` kwarg (call_llm.py line 38)

## Impact Analysis

### Components Affected by Tool-Calling WebSocket Events

1. **WebSocket Message Schemas** (websocket_schemas.py)
   - Must add new message types: `TOOL_START`, `TOOL_COMPLETE`, `TOOL_ERROR`
   - Must create corresponding Pydantic models: `ServerToolStartMessage`, `ServerToolCompleteMessage`, `ServerToolErrorMessage`
   - Must preserve existing message types for backward compatibility

2. **WebSocket Handler** (websocket_handler.py)
   - Event loop (line 145) must be extended to handle tool events
   - Must filter for `on_tool_start`, `on_tool_end`, `on_tool_error` events
   - Must extract tool metadata (name, arguments, result) from event data
   - Must emit new message types while preserving current token/complete flow

3. **Frontend Protocol** (implied, not in backend)
   - Frontend clients must be able to gracefully ignore unknown message types
   - Clients that implement tool support will display tool execution states
   - Backward compatibility: clients without tool support will receive and ignore tool messages

### Data Flow: Tool Execution via WebSocket

```
User sends message via WebSocket
    ↓
WebSocket handler receives ClientMessage
    ↓
graph.astream_events() begins streaming:
    ↓
    Event: on_llm_start → (no WebSocket message needed)
    ↓
    Event: on_chat_model_stream (LLM reasoning)
    ├→ ServerTokenMessage sent to client
    ├→ Client displays streaming tokens
    ↓
    Event: on_chat_model_end → AIMessage with tool_calls
    ├→ LangGraph conditionally routes to tools node
    ├→ tools_condition evaluates tool_calls
    ↓
    Event: on_tool_start
    ├→ ServerToolStartMessage sent to client
    ├→ Client displays "Tool X starting..."
    ↓
    Tool executes (synchronously in ToolNode)
    ↓
    Event: on_tool_end (or on_tool_error)
    ├→ ServerToolCompleteMessage (or ServerToolErrorMessage) sent
    ├→ Client displays "Tool X completed with result: Y"
    ↓
    Conditional routes back to call_llm
    ↓
    Event: on_chat_model_stream (LLM reasoning with tool result)
    ├→ ServerTokenMessage sent to client
    ↓
    ... (repeat tool loop if needed)
    ↓
    Event: on_chat_model_end → No tool_calls
    ├→ Loop exits, ServerCompleteMessage sent
    ↓
Conversation saved via LangGraph checkpoint
```

### Event Schema for LangGraph Events

Based on LangGraph's event streaming (version="v2"), tool-related events have this structure:

**on_tool_start event**:
```python
{
    "event": "on_tool_start",
    "data": {
        "input": "<tool_input_str>"  # Serialized tool arguments
    },
    "metadata": {
        "langgraph_step": <int>,
        "langgraph_node": "tools",  # The ToolNode name
        "langgraph_trigger": "call_llm"
    }
}
```

**on_tool_end event**:
```python
{
    "event": "on_tool_end",
    "data": {
        "output": "<tool_result>"  # Serialized return value
    },
    "metadata": {
        "langgraph_step": <int>,
        "langgraph_node": "tools",
        "langgraph_run_id": "<run_id>"
    }
}
```

### Tool Information Context

Tool metadata must be inferred from:
1. The ToolNode name in the graph (always "tools")
2. Message metadata in state (from `on_chat_model_end` before tool execution)
3. Tool name can be extracted from LLM's tool_calls in the AIMessage

**Challenge**: LangGraph's `on_tool_start` and `on_tool_end` events don't directly include tool name. Must:
- Track the last AIMessage tool_calls before tool execution
- Extract tool name from `tool_calls` in state
- Map to human-readable tool name for WebSocket messages

## API Contract Recommendations

### 1. Proposed WebSocket Message Types

#### Update MessageType Enum

Add two new constants to `websocket_schemas.py` (line 9-17):

```python
class MessageType(str, Enum):
    """WebSocket message type enumeration."""

    MESSAGE = "message"
    TOKEN = "token"
    COMPLETE = "complete"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"
    TOOL_START = "tool_start"      # NEW: Tool execution started
    TOOL_COMPLETE = "tool_complete"  # NEW: Tool execution finished successfully
```

**Rationale**:
- `TOOL_START` signals to frontend that a tool is being invoked
- `TOOL_COMPLETE` signals that tool execution finished with a result
- Separate from `TOOL_ERROR` (use existing `ERROR` type with tool-specific code)
- Avoid `TOOL_END` in favor of `TOOL_COMPLETE` for clarity

#### Add ServerToolStartMessage Schema

Insert into `websocket_schemas.py` after `ServerCompleteMessage` (around line 53):

```python
class ServerToolStartMessage(BaseModel):
    """
    Tool execution start message sent from server to client.

    Indicates the LLM has invoked a tool and execution is beginning.
    """

    type: MessageType = Field(default=MessageType.TOOL_START, description="Message type")
    tool_name: str = Field(..., description="Name of the tool being executed")
    tool_input: str = Field(..., description="Tool input arguments (JSON string or plain text)")
    timestamp: Optional[datetime] = Field(
        default_factory=lambda: datetime.utcnow(),
        description="Timestamp when tool execution started"
    )
```

**Fields explained**:
- `tool_name`: Human-readable name extracted from LLM's ToolCall (e.g., "multiply")
- `tool_input`: Stringified input arguments (extracted from ToolCall arguments)
- `timestamp`: ISO 8601 timestamp for UI display (optional but recommended)

#### Add ServerToolCompleteMessage Schema

Insert into `websocket_schemas.py` after `ServerToolStartMessage`:

```python
class ServerToolCompleteMessage(BaseModel):
    """
    Tool execution complete message sent from server to client.

    Indicates the tool execution finished successfully with a result.
    """

    type: MessageType = Field(default=MessageType.TOOL_COMPLETE, description="Message type")
    tool_name: str = Field(..., description="Name of the tool that executed")
    tool_result: str = Field(..., description="Tool execution result (JSON string or plain text)")
    timestamp: Optional[datetime] = Field(
        default_factory=lambda: datetime.utcnow(),
        description="Timestamp when tool execution completed"
    )
```

**Fields explained**:
- `tool_name`: Must match the tool_name from corresponding `TOOL_START` message
- `tool_result`: Stringified return value from tool execution
- `timestamp`: ISO 8601 timestamp for UI display

#### Import datetime

Add to imports in `websocket_schemas.py`:

```python
from datetime import datetime
```

**Rationale for separate message types**:
- Allows frontend to distinguish tool lifecycle events from token streaming
- Enables progressive disclosure: clients without tool support simply ignore these messages
- Clean separation of concerns: token streaming vs. tool execution UI
- Aligns with existing error handling (errors use `ServerErrorMessage`)

### 2. Pydantic Validation and Serialization

**Validation strategy** (already implicit in Pydantic models):

1. **ServerToolStartMessage validation**:
   - `tool_name`: Must be non-empty string (enforced by Field(...))
   - `tool_input`: Must be non-empty string (enforced by Field(...))
   - `timestamp`: Automatically set if not provided

2. **ServerToolCompleteMessage validation**:
   - `tool_name`: Must be non-empty string
   - `tool_result`: Must be non-empty string
   - `timestamp`: Automatically set if not provided

3. **Serialization** via `model_dump()`:
   - Both models use Pydantic's default JSON serialization
   - DatetimeField will serialize as ISO 8601 string
   - Example:
     ```json
     {
       "type": "tool_complete",
       "tool_name": "multiply",
       "tool_result": "20",
       "timestamp": "2025-10-26T15:30:45.123456"
     }
     ```

**No additional validation needed** beyond Pydantic's built-in validators because:
- Tool names come from LLM-generated tool calls (already validated by LLM)
- Input/output are strings (safe to transmit over JSON)
- Timestamps are auto-generated (no client input)

### 3. Event Emission Logic in WebSocket Handler

#### Current Event Loop (websocket_handler.py lines 145-151)

The handler currently only processes `on_chat_model_stream` events:

```python
async for event in graph.astream_events(input_data, config, version="v2"):
    if event["event"] == "on_chat_model_stream":
        chunk = event["data"]["chunk"]
        if hasattr(chunk, 'content') and chunk.content:
            token_msg = ServerTokenMessage(content=chunk.content)
            await manager.send_message(websocket, token_msg.model_dump())
```

#### Extended Event Loop (Proposed Implementation)

Must extend to handle tool events:

**Key events to capture**:

1. **on_chat_model_start** event (optional, for context):
   - Marks when LLM begins processing
   - Used to extract tool information if needed
   - Not necessary to emit to client

2. **on_chat_model_stream** event (existing):
   - Streaming tokens from LLM
   - Already handled: emit `ServerTokenMessage`

3. **on_chat_model_end** event (NEW):
   - Marks when LLM stops (has tool_calls in response)
   - Extract and cache tool_calls for use in tool messages
   - Do NOT emit to client (intermediate event)
   - Structure:
     ```python
     {
         "event": "on_chat_model_end",
         "data": {
             "output": AIMessage(
                 content="...",
                 tool_calls=[
                     ToolCall(
                         id="call_123",
                         name="multiply",
                         args={"a": 5, "b": 4}
                     )
                 ]
             )
         }
     }
     ```

4. **on_tool_start** event (NEW - EMIT):
   - LangGraph signals tool node is beginning execution
   - Must extract tool name from cached tool_calls
   - Emit `ServerToolStartMessage` with tool name and input
   - Structure:
     ```python
     {
         "event": "on_tool_start",
         "data": {
             "input": "{'a': 5, 'b': 4}"  # String representation
         },
         "metadata": {
             "langgraph_node": "tools"
         }
     }
     ```

5. **on_tool_end** event (NEW - EMIT):
   - LangGraph signals tool node completed execution
   - Extract result from event data
   - Emit `ServerToolCompleteMessage` with tool name and result
   - Structure:
     ```python
     {
         "event": "on_tool_end",
         "data": {
             "output": "20"  # Tool return value as string
         }
     }
     ```

6. **on_tool_error** event (NEW - EMIT AS ERROR):
   - If tool execution fails, emit `ServerErrorMessage` with code "TOOL_ERROR"
   - Include tool name in error message for context

#### Algorithm for Tracking Tool Information

Since LangGraph events don't directly contain tool names, implement state tracking:

**Proposed approach** (pseudocode):

```python
current_tool_call = None  # Track the most recent tool call

async for event in graph.astream_events(input_data, config, version="v2"):
    event_type = event["event"]

    # Capture tool calls from LLM response
    if event_type == "on_chat_model_end":
        output = event["data"]["output"]
        if hasattr(output, 'tool_calls') and output.tool_calls:
            current_tool_call = output.tool_calls[0]  # Single tool for now

    # Emit tool start
    elif event_type == "on_tool_start":
        if current_tool_call:
            tool_msg = ServerToolStartMessage(
                tool_name=current_tool_call.name,
                tool_input=json.dumps(current_tool_call.args)
            )
            await manager.send_message(websocket, tool_msg.model_dump())

    # Emit tool complete
    elif event_type == "on_tool_end":
        if current_tool_call:
            result = event["data"]["output"]
            tool_complete_msg = ServerToolCompleteMessage(
                tool_name=current_tool_call.name,
                tool_result=str(result)
            )
            await manager.send_message(websocket, tool_complete_msg.model_dump())

    # Handle streaming tokens (existing)
    elif event_type == "on_chat_model_stream":
        chunk = event["data"]["chunk"]
        if hasattr(chunk, 'content') and chunk.content:
            token_msg = ServerTokenMessage(content=chunk.content)
            await manager.send_message(websocket, token_msg.model_dump())

    # Handle tool errors
    elif event_type == "on_tool_error":
        error = event["data"]["error"]
        error_msg = ServerErrorMessage(
            message=f"Tool error: {str(error)}",
            code="TOOL_ERROR"
        )
        await manager.send_message(websocket, error_msg.model_dump())
```

**Key implementation points**:
- Cache `current_tool_call` from `on_chat_model_end` event
- Use cached data in `on_tool_start` and `on_tool_end` handlers
- Support multiple sequential tool calls (loop back to `call_llm`)
- Properly serialize tool arguments as JSON

#### Integration Points

**In websocket_handler.py** (lines 142-169):

Replace the simple token-only loop (lines 145-151) with extended event handling that includes:
- `on_chat_model_end` handler to cache tool calls
- `on_tool_start` handler to emit `ServerToolStartMessage`
- `on_tool_end` handler to emit `ServerToolCompleteMessage`
- `on_tool_error` handler to emit `ServerErrorMessage` with TOOL_ERROR code
- Preserve existing `on_chat_model_stream` handler
- Add try-catch around tool handlers (graceful degradation if no cached tool_call)

### 4. Backward Compatibility Strategy

#### Frontend Degradation Path

Clients without tool support will:

1. **Receive tool messages but ignore them**:
   - Unknown message types (e.g., "tool_start", "tool_complete") will be logged but not displayed
   - Frontend filters: `if (messageType in ["token", "complete", "error"]) { process(...) }`

2. **Still receive final response**:
   - After tool execution completes, LLM continues reasoning
   - Client receives streaming tokens from final response
   - Client receives `ServerCompleteMessage` as usual
   - Tool execution is transparent to user (they see final answer)

3. **No breaking changes**:
   - Existing message types unchanged
   - Existing fields unchanged
   - New message types are additions, not modifications

#### Server Validation

The implementation must ensure:
- Tool messages always include required fields (tool_name, etc.)
- Tool message timestamps use consistent format (ISO 8601)
- Tool messages can be safely serialized to JSON without client errors
- Errors during tool event processing don't break the WebSocket connection
- If tool tracking fails, gracefully fall back to error message

#### Testing Backward Compatibility

- Test with clients that only handle "token" and "complete" message types
- Verify tool messages don't crash frontend
- Verify final response is delivered correctly even with tool execution
- Verify multiple sequential tool calls work correctly

### 5. Error Handling for Tool Events

#### New Error Code

Add to WebSocket error codes (documented in API.md):

```
TOOL_ERROR: Tool execution failed (e.g., incorrect arguments, execution error)
```

#### Error Scenarios

1. **Tool input validation fails**:
   - LLM may call tool with incorrect arguments
   - LangGraph's ToolNode handles this and returns error
   - Emit `ServerErrorMessage` with code "TOOL_ERROR"

2. **Tool execution raises exception**:
   - Tool function crashes during execution
   - LangGraph captures exception
   - Emit `ServerErrorMessage` with code "TOOL_ERROR"

3. **Event parsing fails**:
   - If on_chat_model_end doesn't contain tool_calls (unexpected)
   - Catch exception, emit generic error, continue streaming
   - Log detailed error for debugging

## Implementation Guidance

### Step 1: Update Message Schemas
1. Add `TOOL_START` and `TOOL_COMPLETE` to `MessageType` enum
2. Create `ServerToolStartMessage` schema with tool_name, tool_input, timestamp
3. Create `ServerToolCompleteMessage` schema with tool_name, tool_result, timestamp
4. Import `datetime` for timestamp fields
5. Add docstrings following existing pattern

### Step 2: Extend WebSocket Handler Event Loop
1. Declare `current_tool_call = None` before the event loop (line ~144)
2. Add handler for `on_chat_model_end` to cache tool calls from AIMessage
3. Add handler for `on_tool_start` to emit `ServerToolStartMessage`
4. Add handler for `on_tool_end` to emit `ServerToolCompleteMessage`
5. Add handler for `on_tool_error` to emit `ServerErrorMessage`
6. Wrap tool event handlers in try-except for robustness
7. Preserve existing `on_chat_model_stream` handler

### Step 3: Add Type Imports
1. Import new message types in websocket_handler.py
2. Import json for serializing tool inputs
3. Import datetime if not already imported

### Step 4: Test Event Emission
1. Create test conversation that triggers tool call
2. Verify tool messages appear in correct order: TOOL_START, TOOL_COMPLETE, then final tokens
3. Verify backward compatibility: client ignores unknown message types
4. Verify tool information (name, input, result) is accurate

## Risks and Considerations

### 1. Tool Information Tracking

**Risk**: `current_tool_call` may be None when tool events fire if graph structure changes.

**Mitigation**:
- Wrap tool event handlers in try-except
- Log warnings if tool_call cannot be found
- Emit error message rather than crashing
- Test with various tool call scenarios

### 2. Multiple Tool Calls

**Risk**: LangGraph may support parallel tool calls in future versions.

**Considerations**:
- Current implementation: `parallel_tool_calls=False` in call_llm.py line 38
- Sequential execution: one tool at a time
- Current tracking: single `current_tool_call` variable
- Future enhancement: track list of tool calls if parallel execution enabled

### 3. Tool Input/Output Serialization

**Risk**: Tool arguments or results may not serialize cleanly to strings.

**Mitigation**:
- Use `json.dumps()` for structured arguments
- Use `str()` for tool results (generic fallback)
- Store as string fields in message schemas (not objects)
- Frontend can parse JSON if needed for advanced displays

### 4. Event Ordering and Race Conditions

**Risk**: Events may arrive out of order or tool execution may be very fast (no streaming).

**Considerations**:
- LangGraph guarantees event ordering within `astream_events()`
- Tool execution is synchronous in ToolNode (no actual async)
- Events will always fire: start → end/error (no skips)
- No race conditions in single-threaded async loop

### 5. Message Size and Performance

**Risk**: Tool inputs/results may be large (e.g., large JSON or binary data).

**Considerations**:
- Tool inputs are usually small (function arguments)
- Tool results may be large (database queries, file contents)
- Keep as strings in schema (client can decide how to display)
- Monitor WebSocket message rates if tools are frequently called

### 6. Timestamp Precision and Timezone

**Risk**: Timestamps may have timezone issues or precision inconsistencies.

**Recommendations**:
- Use UTC for all timestamps
- Format as ISO 8601 (Pydantic default)
- Optional field: allow client to ignore timestamps
- Consistent with ServerTokenMessage approach (no timestamps there)

## Testing Strategy

### Unit Tests

**Test file**: `backend/tests/unit/test_websocket_schemas.py`

1. Test `ServerToolStartMessage` schema validation:
   - Valid message with all fields
   - Valid message with auto-generated timestamp
   - Invalid message without tool_name (should raise ValidationError)
   - Invalid message without tool_input (should raise ValidationError)

2. Test `ServerToolCompleteMessage` schema validation:
   - Valid message with all fields
   - Valid message with auto-generated timestamp
   - Invalid message without tool_name
   - Invalid message without tool_result

3. Test JSON serialization of tool messages:
   - model_dump() produces valid JSON
   - Timestamps serialize as ISO 8601 strings
   - All fields present in serialized output

### Integration Tests

**Test file**: `backend/tests/integration/test_websocket_tool_streaming.py`

1. Test tool message emission during graph execution:
   - Create conversation and send message that triggers tool call
   - Capture all WebSocket messages
   - Verify TOOL_START emitted before TOOL_COMPLETE
   - Verify tool_name matches the called tool
   - Verify tool_input contains correct arguments
   - Verify tool_result contains correct result

2. Test multiple sequential tool calls:
   - LLM calls multiply twice (if graph allows)
   - Verify TOOL_START/TOOL_COMPLETE pairs received for each
   - Verify no tool messages lost

3. Test backward compatibility:
   - Frontend client that ignores TOOL_START/TOOL_COMPLETE messages
   - Verify CLIENT still receives final response via streaming tokens
   - Verify COMPLETE message sent after tools finish
   - Verify no errors or broken connection

4. Test error handling:
   - Manually craft graph to trigger on_tool_error (if possible)
   - Verify ServerErrorMessage sent with code "TOOL_ERROR"
   - Verify connection remains open
   - Verify final response completes

### End-to-End Tests

**Test file**: `backend/tests/e2e/test_tool_execution_flow.py`

1. Test complete tool execution flow:
   - User connects via WebSocket
   - User sends message asking for multiplication (e.g., "multiply 5 and 4")
   - System receives message, processes through graph
   - System emits TOOL_START with tool_name and arguments
   - System executes multiply tool
   - System emits TOOL_COMPLETE with result
   - System resumes LLM for final response
   - System emits TOKEN messages with final response
   - System emits COMPLETE message
   - Verify all messages received in correct order
   - Verify conversation saved correctly in LangGraph

2. Test tool execution without tool call:
   - User sends message that doesn't need tools
   - Verify no TOOL_START or TOOL_COMPLETE messages
   - Verify normal token streaming and completion
   - Verify no errors

### Frontend Compatibility Tests

1. Create minimal JavaScript WebSocket client that:
   - Receives WebSocket messages
   - Only handles "token" and "complete" types
   - Logs unknown message types (including "tool_start", "tool_complete")
   - Verifies no JavaScript errors
   - Verifies final response displayed correctly

## Future Enhancements

### Planned Extensions

1. **Tool Result Streaming**: If tool results are large, stream them token-by-token
   - New message types: TOOL_RESULT_CHUNK, TOOL_RESULT_END
   - Extend event handler for on_tool_end to chunk large results

2. **Tool UI Components**: Frontend displays tool execution in dedicated UI sections
   - Tool execution card showing name, input, result
   - Tool timeline showing start → complete
   - Parallel execution support (if parallel_tool_calls enabled)

3. **Tool Cancellation**: Allow user to cancel running tools (long-running operations)
   - New message type: TOOL_CANCEL request from client
   - Interrupt ToolNode execution (if architecture supports)

4. **Tool Retry**: Automatic or manual retry of failed tools
   - New message type: TOOL_RETRY from client
   - Send message back to LLM to retry with corrected arguments

5. **Tool Metadata**: Expose tool descriptions and schemas to frontend
   - Send tool availability and schemas on connection
   - Allow frontend to display tool help or parameter requirements

## Summary of Key Points

### What Changes

**API Contract**:
- Add `TOOL_START` and `TOOL_COMPLETE` message types
- Add `ServerToolStartMessage` with tool_name, tool_input, timestamp
- Add `ServerToolCompleteMessage` with tool_name, tool_result, timestamp

**WebSocket Handler**:
- Extend event loop to handle on_chat_model_end, on_tool_start, on_tool_end, on_tool_error
- Track current tool call from on_chat_model_end
- Emit new message types during tool execution

### What Stays the Same

- Existing message types (MESSAGE, TOKEN, COMPLETE, ERROR, PING, PONG) unchanged
- Existing message schemas (ServerTokenMessage, ServerCompleteMessage, etc.) unchanged
- WebSocket connection behavior unchanged
- LangGraph graph structure unchanged
- Tool binding mechanism unchanged

### Why This Design

- **Simple**: Only extends existing protocol, doesn't replace it
- **Backward compatible**: Unknown message types safely ignored by old clients
- **Clear**: Tool lifecycle (start → complete) obvious from message sequence
- **Decoupled**: Frontend can evolve tool UI independently of backend events
- **Extensible**: Easy to add tool streaming, cancellation, etc. later

## Questions for Clarification

1. **Tool Result Size**: Should large tool results be truncated in WebSocket messages, or fully transmitted?
2. **Tool Metadata**: Should tool descriptions and parameter schemas be sent to client on startup?
3. **Multiple Tools**: How should frontend display multiple sequential tool calls?
4. **Error Recovery**: If tool execution fails, should LLM auto-retry or fail the request?
5. **User Interruption**: Should frontend allow users to cancel running tools?
