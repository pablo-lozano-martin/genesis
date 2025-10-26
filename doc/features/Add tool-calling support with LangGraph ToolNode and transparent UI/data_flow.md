# Data Flow Analysis: Tool-Calling Support with LangGraph ToolNode and Transparent UI

## Request Summary

This feature adds tool-calling support to Genesis by:

1. **Integrating LangGraph's ToolNode**: Use LangGraph's prebuilt `ToolNode` and `tools_condition` to automatically handle tool invocation when the LLM decides to call a tool
2. **Implementing ToolMessage Persistence**: Ensure ToolMessage objects (containing tool results) are properly appended to conversation state and persisted via AsyncMongoDBSaver checkpointer
3. **Adding WebSocket Event Streaming for Tools**: Extend graph.astream_events() event handling to intercept tool execution events (on_tool_start, on_tool_end) and stream tool metadata to the frontend
4. **Frontend Tool UI**: Display tool execution transparently to users via new TOOL_START and TOOL_COMPLETE WebSocket message types, allowing users to see which tools were called and their results

The goal is to provide a seamless user experience where tool invocations are streamed in real-time just like LLM token streaming.

## Relevant Files & Modules

### Files to Examine

**Backend - LangGraph Graph & State:**
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/streaming_chat_graph.py` - Main streaming graph with ToolNode integration (already has ToolNode added)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/state.py` - ConversationState extending MessagesState with conversation_id, user_id fields
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/call_llm.py` - LLM invocation node that binds tools with parallel_tool_calls=False
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/process_input.py` - Input validation node
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/state_retrieval.py` - Message retrieval from checkpoints (includes ToolMessage filtering note)

**Backend - Tool Definitions:**
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/multiply.py` - Simple example tool
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/__init__.py` - Tool exports

**Backend - LLM Provider Integration:**
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/llm_provider.py` - ILLMProvider interface with bind_tools() method
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/anthropic_provider.py` - Anthropic provider with bind_tools() implementation
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/openai_provider.py` - OpenAI provider with bind_tools()
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/gemini_provider.py` - Gemini provider with bind_tools()
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/ollama_provider.py` - Ollama provider with bind_tools()

**Backend - WebSocket Handler & Events:**
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py` - Handles WebSocket connections and streams graph.astream_events() events to clients (CRITICAL for tool event streaming)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_schemas.py` - WebSocket message type definitions (needs TOOL_START, TOOL_COMPLETE additions)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_router.py` - WebSocket endpoint routing

**Backend - Checkpointing & State Persistence:**
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/database/langgraph_checkpointer.py` - AsyncMongoDBSaver setup for state persistence

**Frontend - WebSocket Communication:**
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/services/websocketService.ts` - WebSocket service handling message types (needs TOOL_START, TOOL_COMPLETE additions)
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/hooks/useWebSocket.ts` - React hook managing WebSocket state and callbacks (needs tool event handlers)

**Frontend - UI Components (will be created/modified):**
- Component that displays tool execution UI (not yet identified - will need to be created)

### Key Functions & Classes

**Graph & State Management:**
- `create_streaming_chat_graph()` in `streaming_chat_graph.py` - Builds graph with ToolNode and tools_condition
- `ConversationState` in `state.py` - Extends MessagesState with conversation_id, user_id
- `add_messages` reducer in MessagesState - Automatically appends messages (including ToolMessage) to state

**Node Functions:**
- `call_llm()` in `call_llm.py` - Binds tools to LLM provider, returns AIMessage (may contain tool_calls)
- `process_user_input()` in `process_input.py` - Validates input and appends HumanMessage
- ToolNode (LangGraph prebuilt) - Executes tools and appends ToolMessage to state

**WebSocket Event Processing:**
- `handle_websocket_chat()` in `websocket_handler.py` - Main handler that iterates graph.astream_events() and sends events to client
- Event types emitted by astream_events(): `on_chat_model_stream`, `on_tool_start`, `on_tool_end`, etc.

**Tool Support:**
- `bind_tools()` in ILLMProvider implementations - Binds tool callables to LLM (LangChain handles tool calling protocol)
- `tools_condition` from langgraph.prebuilt - Conditional edge function determining: END (no tools) vs tools node
- ToolNode constructor - Takes list of Tool objects and auto-executes them

## Current Data Flow Overview

### High-Level Data Flow for Current Implementation

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Frontend (Browser)                         │
│  useWebSocket Hook → WebSocketService → sends ClientMessage         │
└──────────────────┬──────────────────────────────────────────────────┘
                   │ sends: {"type": "message", "conversation_id": "...", "content": "..."}
                   │
                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    Backend - WebSocket Layer                         │
│  websocket_router.py:websocket_chat_endpoint()                      │
│    ↓ authenticate user                                              │
│  websocket_handler.py:handle_websocket_chat()                       │
│    ↓ validate conversation ownership in App DB                      │
│    ↓ create RunnableConfig with llm_provider and conversation.id   │
│    ↓ create HumanMessage from client content                        │
│    ↓ invoke graph.astream_events(input_data, config, version="v2") │
└──────────────────┬───────────────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│              Backend - LangGraph Execution Layer                     │
│  streaming_chat_graph (compiled with AsyncMongoDBSaver checkpointer)│
│                                                                      │
│  START → process_input → call_llm → tools (if needed) → call_llm → END
│                            ▼                      ▼                 │
│  Nodes emit events:  on_chat_model_stream   on_tool_start/end     │
│                                                                      │
│  State updates:                                                      │
│  - process_input: appends HumanMessage to messages via add_messages │
│  - call_llm: appends AIMessage (may contain tool_calls)            │
│  - ToolNode: executes tools, appends ToolMessage (result)          │
│  - Checkpointer: saves state snapshot after each step              │
└──────────────────┬───────────────────────────────────────────────────┘
                   │ emits: {event: "on_chat_model_stream", data: {chunk: ...}}
                   │         {event: "on_tool_start", data: {...}}
                   │         {event: "on_tool_end", data: {...}}
                   │
                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│                   Backend - Event Processing                         │
│  websocket_handler.py:handle_websocket_chat()                       │
│    ↓ iterate over astream_events()                                 │
│    ↓ filter and convert events to WebSocket messages               │
│    ↓ send ServerTokenMessage for on_chat_model_stream events       │
│    ↓ send ServerToolMessage for on_tool_start events (FUTURE)      │
│    ↓ send ServerToolCompleteMessage for on_tool_end events (FUTURE)│
└──────────────────┬───────────────────────────────────────────────────┘
                   │ sends: ServerTokenMessage | ServerToolMessage | ...
                   │
                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│                   Frontend - Event Reception                         │
│  WebSocketService.handleMessage()                                    │
│    ↓ parse JSON event                                               │
│    ↓ switch on message.type                                         │
│    ↓ call config.onToken(token) for TOKEN                           │
│    ↓ call config.onToolStart(toolName, args) for TOOL_START (FUTURE)
│    ↓ call config.onToolComplete(toolName, result) for TOOL_COMPLETE │
│    ↓ call config.onComplete() for COMPLETE                          │
│                                                                      │
│  useWebSocket Hook:                                                  │
│    ↓ update streamingMessage state on tokens                        │
│    ↓ update toolExecutions state on tool events (FUTURE)            │
│    ↓ mark complete when COMPLETE received                           │
└──────────────────┬───────────────────────────────────────────────────┘
                   │ renders: message text with tool UI indicators
                   │
                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│              Frontend - UI Display                                   │
│  Displays streamed message tokens in real-time                      │
│  Shows tool execution UI when TOOL_START → TOOL_COMPLETE           │
└──────────────────────────────────────────────────────────────────────┘
```

### Persistence & Checkpointing Flow

```
LangGraph Execution
  ↓
Each node updates state (appends BaseMessage via add_messages reducer)
  ↓
After each step, AsyncMongoDBSaver checkpointer saves state snapshot:
  - Checkpoint Key: thread_id (conversation.id)
  - Checkpoint Value: complete ConversationState
    {
      messages: [HumanMessage, AIMessage, ToolMessage, ...],
      conversation_id: "...",
      user_id: "..."
    }
  ↓
Stored in LangGraph Database (genesis_langgraph):
  langgraph_checkpoints collection
    {
      thread_id: "conv-123",
      checkpoint_id: "...",
      timestamp: ...,
      checkpoint_data: {...}
    }
```

## Impact Analysis: Tool-Calling Feature

### What Changes with Tool Support

**Current (Token-Only) Flow:**
```
User Message → LLM → Token Stream → COMPLETE
```

**New (Tool-Enhanced) Flow:**
```
User Message → LLM Decision:
  ├─ No tools → Token Stream → COMPLETE
  └─ Tools needed → TOOL_START → Tool Execution → ToolMessage → LLM Again → (repeat or no tools) → Token Stream → COMPLETE
```

### Data Flow Components Affected

#### 1. **Graph Execution Flow** (streaming_chat_graph.py)

**Current:**
```
START → process_input → call_llm → END
```

**With Tools:**
```
START → process_input → call_llm → tools_condition (conditional edge)
  ├─ No tool_calls → END
  └─ tool_calls present → tools (ToolNode) → call_llm (loop back)
     → (repeat until no tool_calls) → END
```

**State Updates at Each Step:**
- `process_input`: Appends HumanMessage via add_messages
- `call_llm` (1st call): Appends AIMessage with tool_calls property
- `tools` (ToolNode): Executes each tool, appends ToolMessage with result
- `call_llm` (2nd+ calls): Receives context with ToolMessages, appends AIMessage (without tools if satisfied, or with more tools if needed)

#### 2. **WebSocket Event Streaming** (websocket_handler.py)

**Current Events Handled:**
```python
if event["event"] == "on_chat_model_stream":
    # Extract token from LLM and send to client
```

**New Events to Handle:**
```python
# Tool execution start
if event["event"] == "on_tool_start":
    tool_name = event["data"]["name"]
    tool_input = event["data"]["input"]
    # Send ServerToolStartMessage to client

# Tool execution complete
if event["event"] == "on_tool_end":
    tool_name = event["data"]["name"]
    tool_output = event["data"]["output"]
    # Send ServerToolCompleteMessage to client

# Tool execution error (if applicable)
if event["event"] == "on_tool_error":
    tool_name = event["data"]["name"]
    error_message = event["data"]["error"]
    # Send ServerToolErrorMessage to client
```

#### 3. **State Persistence** (langgraph_checkpointer.py)

**Current Checkpoint Content:**
```python
{
  "messages": [
    HumanMessage(content="Hello"),
    AIMessage(content="Hello! How can I help?")
  ],
  "conversation_id": "...",
  "user_id": "..."
}
```

**With Tools:**
```python
{
  "messages": [
    HumanMessage(content="What is 5 * 3?"),
    AIMessage(content="", tool_calls=[ToolCall(name="multiply", args={"a": 5, "b": 3})]),
    ToolMessage(tool_call_id="...", content="15"),  # <-- NEW
    AIMessage(content="The answer is 15.")
  ],
  "conversation_id": "...",
  "user_id": "..."
}
```

**Key Point:** ToolMessage objects are BaseMessage subclasses automatically appended by ToolNode and persisted by checkpointer.

#### 4. **Frontend WebSocket Protocol** (websocket_schemas.py, websocketService.ts)

**Current MessageTypes:**
```python
class MessageType(str, Enum):
    MESSAGE = "message"
    TOKEN = "token"
    COMPLETE = "complete"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"
```

**New MessageTypes Needed:**
```python
class MessageType(str, Enum):
    # ... existing types
    TOOL_START = "tool_start"      # NEW: tool execution starting
    TOOL_COMPLETE = "tool_complete"  # NEW: tool execution result
    TOOL_ERROR = "tool_error"       # NEW: tool execution failed
```

**New ServerMessage Types:**
```python
class ServerToolStartMessage(BaseModel):
    type: MessageType = Field(default=MessageType.TOOL_START)
    tool_name: str = Field(..., description="Name of tool being called")
    tool_input: dict = Field(..., description="Arguments passed to tool")

class ServerToolCompleteMessage(BaseModel):
    type: MessageType = Field(default=MessageType.TOOL_COMPLETE)
    tool_name: str = Field(..., description="Name of tool that executed")
    tool_output: str = Field(..., description="Result of tool execution")

class ServerToolErrorMessage(BaseModel):
    type: MessageType = Field(default=MessageType.TOOL_ERROR)
    tool_name: str = Field(..., description="Name of tool that failed")
    error_message: str = Field(..., description="Error details")
```

#### 5. **LLM Provider Integration** (llm_provider.py and implementations)

**No Changes Required to Core Provider Interface:**

The `bind_tools()` method already exists in ILLMProvider:

```python
def bind_tools(self, tools: List[Callable], **kwargs: Any) -> 'ILLMProvider':
    """
    Bind tools to the LLM provider for tool calling.

    Args:
        tools: List of callable tools to bind
        **kwargs: Additional keyword arguments for binding (e.g., parallel_tool_calls)

    Returns:
        A new ILLMProvider instance with tools bound
    """
```

**Current Usage in call_llm.py:**
```python
tools = [multiply]
llm_provider_with_tools = llm_provider.bind_tools(tools, parallel_tool_calls=False)
ai_message = await llm_provider_with_tools.generate(messages)
```

**Provider Implementation Pattern (Anthropic example):**
```python
def bind_tools(self, tools: List[Callable], **kwargs: Any) -> 'ILLMProvider':
    bound_model = self.model.bind_tools(tools, **kwargs)  # LangChain's bind_tools
    new_provider = AnthropicProvider.__new__(AnthropicProvider)
    new_provider.model = bound_model
    return new_provider
```

**Key Point:** LangChain's `bind_tools()` internally handles the tool calling protocol (structuring tools for the API, parsing tool calls from responses). All providers return AIMessage with optional `tool_calls` attribute when tools are called.

## Data Flow Recommendations

### 1. **Proposed WebSocket Message Protocol Updates**

**Backend - websocket_schemas.py changes:**

```python
class MessageType(str, Enum):
    MESSAGE = "message"
    TOKEN = "token"
    COMPLETE = "complete"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"
    TOOL_START = "tool_start"      # NEW
    TOOL_COMPLETE = "tool_complete"  # NEW
    TOOL_ERROR = "tool_error"       # NEW

class ServerToolStartMessage(BaseModel):
    """Tool execution starting notification."""
    type: MessageType = Field(default=MessageType.TOOL_START)
    tool_name: str = Field(..., description="Name of the tool being called")
    tool_input: dict = Field(..., description="Arguments passed to the tool")

class ServerToolCompleteMessage(BaseModel):
    """Tool execution result notification."""
    type: MessageType = Field(default=MessageType.TOOL_COMPLETE)
    tool_name: str = Field(..., description="Name of the tool that executed")
    tool_output: str = Field(..., description="Result/output from tool execution")

class ServerToolErrorMessage(BaseModel):
    """Tool execution error notification."""
    type: MessageType = Field(default=MessageType.TOOL_ERROR)
    tool_name: str = Field(..., description="Name of the tool that failed")
    error_message: str = Field(..., description="Error message from tool execution")
```

**Frontend - websocketService.ts changes:**

```typescript
export const MessageType = {
  MESSAGE: "message",
  TOKEN: "token",
  COMPLETE: "complete",
  ERROR: "error",
  PING: "ping",
  PONG: "pong",
  TOOL_START: "tool_start",      // NEW
  TOOL_COMPLETE: "tool_complete",  // NEW
  TOOL_ERROR: "tool_error",       // NEW
} as const;

export interface ServerToolStartMessage {
  type: typeof MessageType.TOOL_START;
  tool_name: string;
  tool_input: Record<string, unknown>;
}

export interface ServerToolCompleteMessage {
  type: typeof MessageType.TOOL_COMPLETE;
  tool_name: string;
  tool_output: string;
}

export interface ServerToolErrorMessage {
  type: typeof MessageType.TOOL_ERROR;
  tool_name: string;
  error_message: string;
}

export type ServerMessage =
  | ServerTokenMessage
  | ServerCompleteMessage
  | ServerErrorMessage
  | ServerToolStartMessage      // NEW
  | ServerToolCompleteMessage    // NEW
  | ServerToolErrorMessage       // NEW
  | ServerPongMessage;
```

### 2. **Proposed WebSocket Handler Updates** (websocket_handler.py)

**Enhanced Event Processing in handle_websocket_chat():**

```python
async def handle_websocket_chat(
    websocket: WebSocket,
    user: User,
    graph,
    llm_provider: ILLMProvider,
    conversation_repository: IConversationRepository
):
    """
    Enhanced handler that streams both LLM tokens AND tool execution events.
    """
    # ... existing setup code ...

    try:
        async for event in graph.astream_events(input_data, config, version="v2"):

            # Existing: Stream LLM tokens
            if event["event"] == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if hasattr(chunk, 'content') and chunk.content:
                    token_msg = ServerTokenMessage(content=chunk.content)
                    await manager.send_message(websocket, token_msg.model_dump())

            # NEW: Tool execution starting
            elif event["event"] == "on_tool_start":
                tool_name = event["data"].get("name")
                tool_input = event["data"].get("input", {})
                tool_start_msg = ServerToolStartMessage(
                    tool_name=tool_name,
                    tool_input=tool_input
                )
                await manager.send_message(websocket, tool_start_msg.model_dump())

            # NEW: Tool execution complete
            elif event["event"] == "on_tool_end":
                tool_name = event["data"].get("name")
                tool_output = event["data"].get("output")
                # Convert output to string if needed
                tool_output_str = str(tool_output) if tool_output is not None else ""
                tool_complete_msg = ServerToolCompleteMessage(
                    tool_name=tool_name,
                    tool_output=tool_output_str
                )
                await manager.send_message(websocket, tool_complete_msg.model_dump())

            # NEW: Tool execution error (if applicable)
            elif event["event"] == "on_tool_error":
                tool_name = event["data"].get("name")
                error_msg_text = event["data"].get("error", "Unknown error")
                tool_error_msg = ServerToolErrorMessage(
                    tool_name=tool_name,
                    error_message=str(error_msg_text)
                )
                await manager.send_message(websocket, tool_error_msg.model_dump())

    # ... existing error handling ...
```

**Key Implementation Details:**

- Event structure from `graph.astream_events()` is hierarchical: `event["data"]["chunk"]` for chat model, `event["data"]["name"]` and `event["data"]["input"]` for tools
- Tool input arrives as dict/object, tool output may be any type (convert to string for serialization)
- ToolMessage objects are automatically created and persisted by ToolNode (no manual handling needed)
- All events occur within the same `async for event in graph.astream_events()` loop, preserving order

### 3. **Proposed Frontend WebSocket Service Updates** (websocketService.ts)

**Enhanced handleMessage() for tool events:**

```typescript
private handleMessage(data: string): void {
  try {
    const message: ServerMessage = JSON.parse(data);

    switch (message.type) {
      case MessageType.TOKEN:
        this.config.onToken?.(message.content);
        break;

      case MessageType.TOOL_START:
        // NEW: Tool execution starting
        this.config.onToolStart?.(message.tool_name, message.tool_input);
        break;

      case MessageType.TOOL_COMPLETE:
        // NEW: Tool execution complete
        this.config.onToolComplete?.(message.tool_name, message.tool_output);
        break;

      case MessageType.TOOL_ERROR:
        // NEW: Tool execution failed
        this.config.onToolError?.(message.tool_name, message.error_message);
        break;

      case MessageType.COMPLETE:
        this.config.onComplete?.(message.message_id, message.conversation_id);
        break;

      case MessageType.ERROR:
        this.config.onError?.(message.message, message.code);
        break;

      case MessageType.PONG:
        break;

      default:
        console.warn("Unknown message type:", message);
    }
  } catch (error) {
    console.error("Failed to parse WebSocket message:", error);
  }
}
```

**Updated WebSocketConfig interface:**

```typescript
export interface WebSocketConfig {
  url: string;
  token: string;
  onToken?: (token: string) => void;
  onToolStart?: (toolName: string, toolInput: Record<string, unknown>) => void;  // NEW
  onToolComplete?: (toolName: string, toolOutput: string) => void;              // NEW
  onToolError?: (toolName: string, errorMessage: string) => void;               // NEW
  onComplete?: (messageId: string, conversationId: string) => void;
  onError?: (error: string, code?: string) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
}
```

### 4. **Proposed React Hook Updates** (useWebSocket.ts)

**Enhanced hook for tool state management:**

```typescript
export interface ToolExecution {
  toolName: string;
  state: "running" | "completed" | "error";
  input?: Record<string, unknown>;
  output?: string;
  errorMessage?: string;
}

export interface UseWebSocketReturn {
  isConnected: boolean;
  error: string | null;
  sendMessage: (conversationId: string, content: string) => void;
  streamingMessage: StreamingMessage | null;
  toolExecutions: ToolExecution[];  // NEW: Track tool executions
  connect: () => void;
  disconnect: () => void;
}

export function useWebSocket(options: UseWebSocketOptions): UseWebSocketReturn {
  // ... existing code ...

  const [toolExecutions, setToolExecutions] = useState<ToolExecution[]>([]);

  const connect = useCallback(() => {
    const config: WebSocketConfig = {
      url,
      token,
      onConnect: () => { /* ... */ },
      onDisconnect: () => { /* ... */ },
      onToken: (tokenContent: string) => { /* ... */ },
      onToolStart: (toolName: string, toolInput: Record<string, unknown>) => {
        // NEW: Add tool execution to list
        setToolExecutions((prev) => [
          ...prev,
          {
            toolName,
            state: "running",
            input: toolInput,
          },
        ]);
      },
      onToolComplete: (toolName: string, toolOutput: string) => {
        // NEW: Mark tool as complete
        setToolExecutions((prev) =>
          prev.map((tool) =>
            tool.toolName === toolName
              ? { ...tool, state: "completed", output: toolOutput }
              : tool
          )
        );
      },
      onToolError: (toolName: string, errorMessage: string) => {
        // NEW: Mark tool as errored
        setToolExecutions((prev) =>
          prev.map((tool) =>
            tool.toolName === toolName
              ? { ...tool, state: "error", errorMessage }
              : tool
          )
        );
      },
      onComplete: (_messageId: string, _conversationId: string) => {
        setStreamingMessage((prev) => {
          if (prev) {
            return { ...prev, isComplete: true };
          }
          return null;
        });
        // Clear tool executions after completion
        setTimeout(() => {
          setStreamingMessage(null);
          setToolExecutions([]);
          currentConversationIdRef.current = null;
        }, 100);
      },
      onError: (errorMessage: string, code?: string) => { /* ... */ },
    };

    const service = new WebSocketService(config);
    wsServiceRef.current = service;
    service.connect();
  }, [url, token]);

  const disconnect = useCallback(() => { /* ... */ }, []);

  return {
    isConnected,
    error,
    sendMessage,
    streamingMessage,
    toolExecutions,  // NEW: Return tool executions
    connect,
    disconnect,
  };
}
```

### 5. **Tool Definition & Registration Pattern**

**Current tool pattern (multiply.py):**

```python
def multiply(a: int, b: int) -> int:
    """
    Simple multiply tool.

    Args:
        a: First number.
        b: Second number.
    """
    return a * b
```

**How tools are integrated:**

In `call_llm.py`:
```python
tools = [multiply]
llm_provider_with_tools = llm_provider.bind_tools(tools, parallel_tool_calls=False)
ai_message = await llm_provider_with_tools.generate(messages)
```

In `streaming_chat_graph.py`:
```python
tools = [multiply]
graph_builder.add_node("tools", ToolNode(tools))
graph_builder.add_conditional_edges("call_llm", tools_condition)
graph_builder.add_edge("tools", "call_llm")
```

**To Add More Tools:**
1. Define tool function with proper docstring (docstring used for tool schema)
2. Add to `tools` list in both `call_llm.py` and `streaming_chat_graph.py`
3. ToolNode and bind_tools handle the rest automatically

### 6. **State Filtering Considerations** (state_retrieval.py)

**Current note in state_retrieval.py:**

```python
"""
...returns complete conversation history. Note: Callers should filter
tool messages and intermediate AI tool-call messages before exposing to frontend.
"""
```

**Recommendation for message retrieval/display:**

When retrieving conversation history for display:
1. Keep ToolMessage objects for audit/transparency (users can see what tools were called)
2. Filter intermediate AIMessages that contain only tool_calls (no user-facing text)
3. Display to user:
   - HumanMessage content
   - Final AIMessage content (after tools executed)
   - Optional: ToolMessage details (showing which tools were called and results)

**Example filtering logic:**

```python
def filter_messages_for_display(messages: List[BaseMessage]) -> List[BaseMessage]:
    """
    Filter messages for user display, keeping meaningful content.

    Rules:
    - Keep HumanMessage (user input)
    - Keep AIMessage with content (LLM response to user)
    - Keep ToolMessage (shows tool calls made, helps user understand reasoning)
    - Skip AIMessage with only tool_calls and no content (intermediate decision)
    """
    display_messages = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            display_messages.append(msg)
        elif isinstance(msg, AIMessage):
            # Include if has content (user-facing response)
            # Skip if only has tool_calls and no content (intermediate)
            if hasattr(msg, 'content') and msg.content:
                display_messages.append(msg)
        elif isinstance(msg, ToolMessage):
            # Include for transparency on tool calls
            display_messages.append(msg)
    return display_messages
```

## Data Flow Diagram: Tool Execution Sequence

```
User Input: "What is 5 * 3?"
    │
    ├─ Creates HumanMessage
    │
    ▼
LLM Call (with bound multiply tool)
    │
    ├─ LLM analyzes request
    ├─ LLM decides: needs multiply tool
    │
    ▼
AIMessage with tool_calls:
    {
      content: "",
      tool_calls: [
        {
          name: "multiply",
          args: {"a": 5, "b": 3},
          id: "call_xyz"
        }
      ]
    }
    │
    ├─ EVENT: on_tool_start emitted
    │       → WebSocket sends: ServerToolStartMessage(tool_name="multiply", tool_input={"a": 5, "b": 3})
    │
    ▼
ToolNode Execution:
    │
    ├─ Reads tool_calls from AIMessage
    ├─ Executes: multiply(a=5, b=3) → 15
    │
    ├─ EVENT: on_tool_end emitted
    │       → WebSocket sends: ServerToolCompleteMessage(tool_name="multiply", tool_output="15")
    │
    ▼
ToolMessage Appended:
    {
      tool_call_id: "call_xyz",
      content: "15"
    }
    │
    ├─ State now has:
    │  - HumanMessage: "What is 5 * 3?"
    │  - AIMessage: (with tool_calls)
    │  - ToolMessage: "15"
    │
    ▼
LLM Call Again (receives full context including ToolMessage):
    │
    ├─ LLM sees: user question + its decision to multiply + tool result
    ├─ LLM decides: I have the answer, no more tools needed
    │
    ▼
Final AIMessage:
    {
      content: "5 × 3 = 15",
      tool_calls: []  # or None (no more tools)
    }
    │
    ├─ EVENT: on_chat_model_stream emitted
    │       → WebSocket sends: ServerTokenMessage("5"), ServerTokenMessage(" × "), ...
    │
    ▼
tools_condition Edge:
    │
    ├─ Checks if AIMessage has tool_calls: No
    ├─ Routes to END (not to tools node)
    │
    ▼
Graph Execution Complete
    │
    ├─ Final state checkpointed:
    │  - messages: [HumanMessage, AIMessage (with tool_calls), ToolMessage, Final AIMessage]
    │  - conversation_id, user_id preserved
    │
    ├─ EVENT: graph execution finished
    │       → WebSocket sends: ServerCompleteMessage
    │
    ▼
Frontend Receives Events in Order:
    1. TOOL_START: multiply called with {a: 5, b: 3}
    2. TOOL_COMPLETE: multiply result = 15
    3. TOKEN: "5"
    4. TOKEN: " × "
    5. TOKEN: "3"
    6. TOKEN: " = "
    7. TOKEN: "15"
    8. COMPLETE: message finished

Frontend UI Flow:
    1. Show tool execution in progress
    2. Show tool completed with result
    3. Stream and display final response
    4. Mark message as complete
```

## Implementation Guidance

### Phase 1: WebSocket Schema Updates (Backend & Frontend)

1. **Backend - Add message types to websocket_schemas.py:**
   - Add TOOL_START, TOOL_COMPLETE, TOOL_ERROR to MessageType enum
   - Create ServerToolStartMessage, ServerToolCompleteMessage, ServerToolErrorMessage Pydantic models
   - Add to type union for ServerMessage

2. **Frontend - Add message types to websocketService.ts:**
   - Add TOOL_START, TOOL_COMPLETE, TOOL_ERROR to MessageType object
   - Create TypeScript interfaces for tool messages
   - Update ServerMessage union type
   - Update WebSocketConfig with onToolStart, onToolComplete, onToolError callbacks

3. **Validation:**
   - Write unit tests for new Pydantic models
   - Test TypeScript type checking for new message types

### Phase 2: WebSocket Handler Enhancement (Backend)

1. **Update websocket_handler.py:handle_websocket_chat():**
   - Add event handlers for "on_tool_start", "on_tool_end", "on_tool_error"
   - Extract tool name, input, output from event data
   - Create and send appropriate ServerToolMessage variants
   - Ensure event order is preserved (all events in single async for loop)

2. **Testing:**
   - Mock graph.astream_events() to emit tool events
   - Verify correct ServerToolMessage types sent
   - Test error path (tool execution failure)

### Phase 3: React Hook & Frontend Service (Frontend)

1. **Update websocketService.ts:**
   - Implement tool message handling in handleMessage()
   - Call onToolStart, onToolComplete, onToolError callbacks
   - Test with all three tool message types

2. **Update useWebSocket.ts:**
   - Add toolExecutions state (array of ToolExecution objects)
   - Implement onToolStart callback (add to array with state="running")
   - Implement onToolComplete callback (update array entry, set state="completed", add output)
   - Implement onToolError callback (update array entry, set state="error", add error message)
   - Clear toolExecutions on complete/disconnect

3. **Testing:**
   - Unit test tool state updates
   - Test rendering with tool executions

### Phase 4: Tool UI Component (Frontend)

1. **Create tool execution display component:**
   - Display tool name and current status (running/completed/error)
   - Show tool input parameters
   - Show tool output (when available)
   - Handle error states gracefully

2. **Integration:**
   - Integrate into chat message display
   - Show tools before final response text (for transparency)
   - Maintain order of execution

3. **Testing:**
   - Component renders correctly
   - Displays tool execution flow properly

### Phase 5: Verification & Testing

1. **End-to-end test:**
   - Send message requiring tool call
   - Verify TOOL_START event received
   - Verify TOOL_COMPLETE event received with result
   - Verify final response received
   - Verify checkpointer stored ToolMessage in state

2. **Error handling test:**
   - Mock tool that throws error
   - Verify TOOL_ERROR event sent
   - Verify graph handles error gracefully

3. **Multiple tool test:**
   - Create scenario where multiple tools called
   - Verify events received in correct order

### Phase 6: Message History Display (Optional Refinement)

1. **Update state_retrieval.py usage:**
   - Where conversation history displayed, decide on filtering strategy
   - Keep ToolMessages visible (transparency) or filter (cleaner UI)
   - Document decision in comments

2. **Testing:**
   - Retrieve conversation with tools
   - Verify correct messages returned/filtered

## Risks and Considerations

### Risk 1: Event Stream Ordering

**Risk:** WebSocket events may arrive out of order or be dropped if server handling is not careful.

**Mitigation:**
- Keep all event processing in single `async for event in graph.astream_events()` loop (maintains order)
- Do not spawn background tasks for event processing
- Use sequential awaits: `await manager.send_message()` after each event
- No buffering/batching that could reorder events

### Risk 2: Tool Output Serialization

**Risk:** Tool outputs may be non-JSON-serializable (objects, custom types, etc.).

**Mitigation:**
- Convert tool output to string: `str(tool_output)`
- In state_retrieval.py when retrieving for display, handle both:
  - ToolMessage.content (string form)
  - Raw tool output in checkpoint (if needed)
- Test with various tool return types (int, dict, custom objects)

### Risk 3: Checkpointer State Size with Tools

**Risk:** ToolMessages accumulate in state, potentially making checkpoints large with many tool calls.

**Mitigation:**
- Monitor checkpoint size
- Consider archiving old conversations
- If needed, implement state filtering in checkpointer (though LangGraph handles this efficiently)

### Risk 4: Tool Name Collisions

**Risk:** Multiple tools with same name could cause routing issues.

**Mitigation:**
- Enforce unique tool names in tools registry
- Add validation in streaming_chat_graph.py: `assert len(tools) == len({t.__name__ for t in tools})`
- Document naming convention

### Risk 5: Long-Running Tools

**Risk:** Tool execution taking long time could timeout WebSocket or cause UI to appear frozen.

**Mitigation:**
- Set reasonable timeout on tool execution in LangGraph
- Inform user (TOOL_START event) that tool is running
- Show progress indicator while tool_start emitted but tool_end not yet received
- Handle timeout by sending TOOL_ERROR event

### Risk 6: Tool Error Handling

**Risk:** Tool raising exception could crash graph or leave state inconsistent.

**Mitigation:**
- ToolNode wraps execution in try/catch
- LangGraph emits on_tool_error event (or on exception event)
- Send TOOL_ERROR message to frontend
- State remains consistent (tool error doesn't halt graph, just returns error message)
- Verify with test: throw exception from tool, check graph continues

### Risk 7: Frontend Tool UI Complexity

**Risk:** Complex tool results (large objects, deeply nested) hard to display.

**Mitigation:**
- Keep tool output as string (truncate if needed)
- Provide expandable/collapsible tool details
- Limit output length: `tool_output[:500] + "..." if len(tool_output) > 500 else tool_output`
- Test with various output sizes

## Testing Strategy

### Unit Tests: WebSocket Schema (Backend)

**File:** `backend/tests/unit/test_websocket_tool_schemas.py`

```python
@pytest.mark.asyncio
def test_tool_start_message_validation():
    """Test ServerToolStartMessage validation"""
    msg = ServerToolStartMessage(
        tool_name="multiply",
        tool_input={"a": 5, "b": 3}
    )
    assert msg.type == MessageType.TOOL_START
    assert msg.tool_name == "multiply"
    assert msg.model_dump()["type"] == "tool_start"

def test_tool_complete_message_validation():
    """Test ServerToolCompleteMessage validation"""
    msg = ServerToolCompleteMessage(
        tool_name="multiply",
        tool_output="15"
    )
    assert msg.type == MessageType.TOOL_COMPLETE
    assert msg.tool_output == "15"

def test_tool_error_message_validation():
    """Test ServerToolErrorMessage validation"""
    msg = ServerToolErrorMessage(
        tool_name="divide",
        error_message="Division by zero"
    )
    assert msg.type == MessageType.TOOL_ERROR
    assert "zero" in msg.error_message
```

### Integration Tests: WebSocket Handler (Backend)

**File:** `backend/tests/integration/test_websocket_tool_streaming.py`

```python
@pytest.mark.asyncio
async def test_websocket_streams_tool_events():
    """Test WebSocket handler emits tool events from graph.astream_events()"""
    # Mock WebSocket
    mock_ws = AsyncMock(spec=WebSocket)

    # Mock graph that emits tool events
    mock_graph = AsyncMock()
    async def mock_astream_events(input_data, config, version=None):
        yield {"event": "on_tool_start", "data": {"name": "multiply", "input": {"a": 5, "b": 3}}}
        yield {"event": "on_tool_end", "data": {"name": "multiply", "output": 15}}
        yield {"event": "on_chat_model_stream", "data": {"chunk": ...}}

    mock_graph.astream_events = mock_astream_events

    # Invoke handler
    await handle_websocket_chat(
        websocket=mock_ws,
        user=test_user,
        graph=mock_graph,
        llm_provider=mock_provider,
        conversation_repository=mock_conv_repo
    )

    # Verify messages sent
    calls = [call[0][0] for call in mock_ws.send_text.call_args_list]
    messages = [json.loads(call) for call in calls]

    # Find tool messages in order
    tool_start = next(m for m in messages if m["type"] == "tool_start")
    assert tool_start["tool_name"] == "multiply"
    assert tool_start["tool_input"] == {"a": 5, "b": 3}

    tool_complete = next(m for m in messages if m["type"] == "tool_complete")
    assert tool_complete["tool_name"] == "multiply"
    assert tool_complete["tool_output"] == "15"

@pytest.mark.asyncio
async def test_websocket_tool_error_event():
    """Test WebSocket handles tool error events"""
    # Mock graph emitting error event
    async def mock_astream_events(input_data, config, version=None):
        yield {"event": "on_tool_error", "data": {"name": "divide", "error": "Division by zero"}}

    # ... assertion code to verify ServerToolErrorMessage sent ...
```

### Frontend Unit Tests: WebSocket Service (TypeScript)

**File:** `frontend/src/services/__tests__/websocketService.test.ts`

```typescript
describe("WebSocketService - Tool Events", () => {
  it("should call onToolStart when receiving TOOL_START message", () => {
    const onToolStart = jest.fn();
    const service = new WebSocketService({
      url: "ws://test",
      token: "test",
      onToolStart,
    });

    const message = {
      type: "tool_start",
      tool_name: "multiply",
      tool_input: { a: 5, b: 3 },
    };

    service["handleMessage"](JSON.stringify(message));

    expect(onToolStart).toHaveBeenCalledWith("multiply", { a: 5, b: 3 });
  });

  it("should call onToolComplete when receiving TOOL_COMPLETE message", () => {
    const onToolComplete = jest.fn();
    const service = new WebSocketService({
      url: "ws://test",
      token: "test",
      onToolComplete,
    });

    const message = {
      type: "tool_complete",
      tool_name: "multiply",
      tool_output: "15",
    };

    service["handleMessage"](JSON.stringify(message));

    expect(onToolComplete).toHaveBeenCalledWith("multiply", "15");
  });
});
```

### Frontend Hook Tests: useWebSocket (TypeScript)

**File:** `frontend/src/hooks/__tests__/useWebSocket.test.ts`

```typescript
describe("useWebSocket - Tool Execution State", () => {
  it("should add tool execution when onToolStart called", () => {
    const { result } = renderHook(() =>
      useWebSocket({ url: "ws://test", token: "test" })
    );

    act(() => {
      const config = /* get config from service setup */;
      config.onToolStart?.("multiply", { a: 5, b: 3 });
    });

    expect(result.current.toolExecutions).toHaveLength(1);
    expect(result.current.toolExecutions[0]).toEqual({
      toolName: "multiply",
      state: "running",
      input: { a: 5, b: 3 },
    });
  });

  it("should update tool execution when onToolComplete called", () => {
    const { result } = renderHook(() =>
      useWebSocket({ url: "ws://test", token: "test" })
    );

    act(() => {
      config.onToolStart?.("multiply", { a: 5, b: 3 });
      config.onToolComplete?.("multiply", "15");
    });

    expect(result.current.toolExecutions[0]).toEqual({
      toolName: "multiply",
      state: "completed",
      input: { a: 5, b: 3 },
      output: "15",
    });
  });
});
```

### End-to-End Test: Full Tool Execution Flow

**File:** `backend/tests/e2e/test_tool_execution_flow.py`

```python
@pytest.mark.asyncio
async def test_full_tool_execution_with_checkpointing():
    """
    End-to-end test: user message → LLM calls tool → ToolMessage persisted →
    final response → checkpointer contains ToolMessage
    """
    # Setup: real graph, real checkpointer, mock LLM
    checkpointer = mock_checkpointer  # AsyncMongoDBSaver
    graph = create_streaming_chat_graph(checkpointer)

    mock_llm = AsyncMock(spec=ILLMProvider)
    # First call: LLM decides to call multiply
    mock_llm.generate.side_effect = [
        AIMessage(
            content="",
            tool_calls=[
                ToolCall(name="multiply", args={"a": 5, "b": 3}, id="call_1")
            ]
        ),
        # Second call: LLM provides final answer
        AIMessage(content="5 × 3 = 15")
    ]

    # Invoke graph
    config = RunnableConfig(
        configurable={
            "llm_provider": mock_llm,
            "thread_id": "conv-test"
        }
    )

    result = await graph.ainvoke(
        {
            "messages": [HumanMessage(content="What is 5 * 3?")],
            "conversation_id": "conv-test",
            "user_id": "user-test"
        },
        config
    )

    # Verify state contains all message types
    assert len(result["messages"]) == 4
    assert isinstance(result["messages"][0], HumanMessage)
    assert isinstance(result["messages"][1], AIMessage)
    assert hasattr(result["messages"][1], "tool_calls")
    assert isinstance(result["messages"][2], ToolMessage)  # From multiply
    assert result["messages"][2].content == "15"
    assert isinstance(result["messages"][3], AIMessage)
    assert "15" in result["messages"][3].content

    # Verify checkpointer persisted everything
    checkpoint = await checkpointer.get("conv-test")
    assert checkpoint is not None
    assert len(checkpoint.values["messages"]) == 4
    assert isinstance(checkpoint.values["messages"][2], ToolMessage)
```

## Summary of Key Data Flow Insights

### 1. **Graph Execution with Tools**

- ToolNode is prebuilt LangGraph component that automatically executes tool callables
- tools_condition routes: no tool_calls → END, tool_calls present → ToolNode
- ToolNode creates ToolMessage with tool result and appends to state
- Multiple tool calls loop back to call_llm until no more tools needed

### 2. **Event Streaming Order**

Events from `graph.astream_events()` arrive in execution order:
1. on_chat_model_stream (LLM generating token)
2. on_tool_start (tool about to execute)
3. on_tool_end (tool finished, result available)
4. on_chat_model_stream (LLM generating response after tool)

All in single async loop - maintains strict ordering.

### 3. **State Persistence**

AsyncMongoDBSaver checkpointer:
- Saves complete ConversationState after each step
- ToolMessage objects automatically appended by add_messages reducer
- Accessible later via thread_id (conversation.id)
- Full conversation history recoverable via checkpoints

### 4. **Provider Changes**

No breaking changes required:
- bind_tools() already exists on all providers
- LangChain's bind_tools() handles tool calling protocol
- AIMessage.tool_calls attribute auto-populated by LLM API
- ToolMessage creation/appending handled by ToolNode

### 5. **WebSocket Protocol**

New message types bridge LangGraph events to frontend:
- TOOL_START → displays tool execution in progress
- TOOL_COMPLETE → displays tool result
- TOOL_ERROR → displays error information
- All streamed in order matching execution

### 6. **Frontend State Management**

Tool executions tracked separately from streaming message:
- toolExecutions: array of {toolName, state, input, output, errorMessage}
- State transitions: running → completed/error
- Cleared when response complete

This design provides full transparency of tool execution while maintaining clean separation between LLM token streaming and tool invocation events.
