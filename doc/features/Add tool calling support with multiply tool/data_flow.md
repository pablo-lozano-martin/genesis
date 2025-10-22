# Data Flow Analysis: Tool Calling Support with Multiply Tool

## Request Summary

Add support for LLM tool calling capabilities to the Genesis chat system, starting with a simple `multiply` tool as a proof of concept. This feature enables the LLM to invoke functions/tools during conversation and receive their results to formulate better responses.

## Relevant Files & Modules

### Files to Examine

#### Domain Models
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/message.py` - Current Message domain model (needs extension for tool calls and tool messages)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/conversation.py` - Conversation domain model (may need tool execution tracking)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/user.py` - User domain model (reference only)

#### LangGraph State & Nodes
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/state.py` - Conversation state schema (needs tool-related fields)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/call_llm.py` - LLM invocation node (needs tool binding support)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/process_input.py` - Input processing node (reference only)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/format_response.py` - Response formatting (needs tool message handling)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/save_history.py` - Message persistence (needs to save tool calls and results)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/chat_graph.py` - Main chat graph (needs tool execution node)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/streaming_chat_graph.py` - Streaming graph (needs tool execution node)

#### LLM Providers
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/llm_provider.py` - LLM provider interface (may need tool binding method)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/openai_provider.py` - OpenAI implementation (needs tool binding)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/anthropic_provider.py` - Anthropic implementation (needs tool binding)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/gemini_provider.py` - Gemini implementation (needs tool binding)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/ollama_provider.py` - Ollama implementation (needs tool binding)

#### Repository Layer
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/message_repository.py` - Message repository interface (reference only)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_models.py` - MongoDB document models (needs tool call fields)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_message_repository.py` - Message persistence (needs tool message transformation)

#### WebSocket Handler
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py` - WebSocket chat handler (needs tool execution streaming)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_schemas.py` - WebSocket message schemas (may need tool execution events)

### Key Functions & Classes

#### Transformation Functions
- `_convert_messages()` in `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/openai_provider.py` - Domain Message to LangChain message conversion (needs tool message support)
- `_to_domain()` in `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_message_repository.py` - MongoDB to domain transformation (needs tool call deserialization)

#### LangGraph Nodes
- `call_llm()` in `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/call_llm.py` - LLM invocation with message history
- `format_response()` in `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/format_response.py` - Response to Message transformation
- `save_to_history()` in `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/save_history.py` - Message persistence

#### Graph Builders
- `create_chat_graph()` in `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/chat_graph.py` - Main graph construction
- `create_streaming_chat_graph()` in `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/streaming_chat_graph.py` - Streaming graph construction

## Current Data Flow Overview

### Data Entry Points

The system has two primary data entry points:

1. **WebSocket Chat Entry** (`/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py`):
   - User sends JSON message via WebSocket: `{ type: "message", conversation_id: "...", content: "..." }`
   - Handler validates conversation ownership
   - Creates domain `Message` object with `MessageRole.USER`
   - Saves user message to database
   - Retrieves conversation history
   - Streams LLM response token-by-token
   - Saves assistant message to database

2. **REST API (future non-streaming use case)** - not currently used for chat but available via LangGraph

### Transformation Layers

The current system has **three transformation boundaries**:

#### 1. API Layer → Domain Layer
- **Location**: `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py` (lines 119-123)
- **Transformation**: WebSocket JSON → Domain `Message` object
- **Data Format**:
  - Input: `{ type: "message", conversation_id: str, content: str }`
  - Output: `Message(conversation_id=str, role=MessageRole.USER, content=str)`

#### 2. Domain Layer → LangChain Layer
- **Location**: `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/openai_provider.py` (lines 46-65)
- **Transformation**: Domain `Message` → LangChain `HumanMessage/AIMessage/SystemMessage`
- **Data Format**:
  - Input: `Message(role=MessageRole, content=str)`
  - Output: `HumanMessage(content=str)` or `AIMessage(content=str)` or `SystemMessage(content=str)`
- **Current limitation**: Only handles simple text messages, no tool calls

#### 3. Domain Layer → MongoDB Layer
- **Location**: `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_message_repository.py`
- **Transformation**: Domain `Message` ↔ MongoDB `MessageDocument`
- **Data Format**:
  - To DB (lines 40-45): `Message` → `MessageDocument(conversation_id, role, content, metadata)`
  - From DB (lines 19-28): `MessageDocument` → `Message(id, conversation_id, role, content, created_at, metadata)`

### Persistence Layer

**Message Storage** (`/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_models.py`):
- Collection: `messages`
- Schema: `{ conversation_id, role, content, created_at, metadata }`
- Indexes: `conversation_id`, composite `(conversation_id, created_at)`
- **Current limitation**: `metadata` field is generic dict, not structured for tool calls

**Conversation Metadata**:
- Collection: `conversations`
- Schema: `{ user_id, title, created_at, updated_at, message_count }`
- Updated when messages are saved (increment `message_count`)

### Data Exit Points

1. **WebSocket Streaming**:
   - LLM generates response via `llm_provider.stream(messages)`
   - Each token wrapped in `ServerTokenMessage` and sent to client
   - Final message wrapped in `ServerCompleteMessage` with message ID

2. **REST API Responses**:
   - Message objects transformed to `MessageResponse` schema
   - Serialized to JSON via Pydantic

## Impact Analysis

### Message Flow Changes Required

The introduction of tool calling fundamentally changes the message flow from a **simple request-response pattern** to a **potentially multi-turn agentic loop**:

**Current Flow**:
```
User Input → LLM → Assistant Response → Save → Done
```

**Tool-Enhanced Flow**:
```
User Input → LLM → [Decision Point]
                   ├─ Text Response → Save → Done
                   └─ Tool Call(s) → Execute Tool(s) → ToolMessage(s) → LLM → [Loop back to Decision Point]
```

### Affected Components

#### HIGH IMPACT (Core Changes Required)

1. **Domain Message Model** (`/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/message.py`):
   - **Impact**: Must support multiple message types beyond user/assistant/system
   - **Changes needed**:
     - Add `MessageRole.TOOL` enum value
     - Add optional `tool_calls` field to Message for AIMessages with tool invocations
     - Add optional `tool_call_id` field to Message for ToolMessages
     - Add optional `name` field for tool names
   - **Risk**: Breaking change to existing message handling if not handled carefully

2. **MongoDB Schema** (`/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_models.py`):
   - **Impact**: Must persist tool call data structures
   - **Changes needed**:
     - Add `tool_calls` field (List of dicts with id, name, args)
     - Add `tool_call_id` field (str, for tool result messages)
     - Add `name` field (str, for tool/function name)
   - **Risk**: Migration may be needed for existing messages (nullable fields recommended)

3. **LangChain Message Conversion** (`/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/*.py`):
   - **Impact**: Must convert between domain Messages and LangChain's ToolMessage format
   - **Changes needed**:
     - Handle `AIMessage.tool_calls` when converting from LangChain to domain
     - Create `ToolMessage` objects when converting domain tool messages to LangChain
     - Preserve tool call IDs for proper linking
   - **Risk**: Each provider (OpenAI, Anthropic, Gemini, Ollama) needs consistent handling

4. **LangGraph State** (`/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/state.py`):
   - **Impact**: State must track tool execution status
   - **Changes needed**:
     - Consider adding `pending_tool_calls` field to track what tools need execution
     - Consider adding `tool_results` field for executed tool outputs
   - **Risk**: State bloat if not carefully designed

5. **LangGraph Chat Graph** (`/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/chat_graph.py`):
   - **Impact**: Graph flow must include tool execution node and routing logic
   - **Changes needed**:
     - Add new node for tool execution (likely using LangGraph's `ToolNode`)
     - Add conditional edge from `call_llm` to route between:
       - Tool execution (if `AIMessage.tool_calls` present)
       - Format response (if no tool calls)
     - Add edge from tool execution back to `call_llm` for continuation
   - **Risk**: Complex cyclic graph may introduce infinite loops if not bounded

#### MEDIUM IMPACT (Extension Required)

6. **LLM Provider Interface** (`/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/llm_provider.py`):
   - **Impact**: Providers need tool binding capability
   - **Changes needed**:
     - Consider adding `bind_tools(tools: List[Tool])` method to interface
     - Or handle tool binding internally in provider implementations
   - **Risk**: Different providers have different tool calling capabilities

7. **WebSocket Handler** (`/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py`):
   - **Impact**: Must stream tool execution events to client
   - **Changes needed**:
     - Send tool call notifications to client (optional, for UX)
     - Send tool execution results to client (optional, for transparency)
     - Handle the graph's multi-turn execution within single user message
   - **Risk**: Streaming becomes more complex with intermediate tool steps

8. **Message Persistence** (`/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/save_history.py`):
   - **Impact**: Must save tool call messages in addition to user/assistant
   - **Changes needed**:
     - Save AIMessages with tool_calls metadata
     - Save ToolMessages with tool results
     - Properly handle the multiple messages generated in a single turn
   - **Risk**: Message count inflation (one user input → potentially many messages)

#### LOW IMPACT (Minimal Changes)

9. **Message Repository** (`/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/message_repository.py`):
   - **Impact**: Interface remains the same, implementation handles new fields
   - **Changes**: None required to interface
   - **Note**: Actual implementation in `MongoMessageRepository` needs updates

10. **Conversation Metadata** (`/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/conversation.py`):
    - **Impact**: Minimal, may want to track tool usage statistics
    - **Changes**: Optional - add fields like `tool_calls_count` for analytics
    - **Risk**: Low

## Data Flow Recommendations

### Proposed Message Structure Extensions

The domain `Message` model should be extended to support tool calling while maintaining backward compatibility:

```python
# Additions to /Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/message.py

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"  # NEW

class ToolCall(BaseModel):
    """Represents a tool invocation request from the LLM."""
    id: str = Field(..., description="Unique identifier for this tool call")
    name: str = Field(..., description="Name of the tool to invoke")
    args: dict = Field(..., description="Arguments to pass to the tool")

class Message(BaseModel):
    id: Optional[str] = Field(default=None)
    conversation_id: str = Field(...)
    role: MessageRole = Field(...)
    content: str = Field(...)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[dict] = Field(default=None)

    # NEW FIELDS FOR TOOL CALLING
    tool_calls: Optional[List[ToolCall]] = Field(
        default=None,
        description="Tool calls requested by assistant (only for ASSISTANT role)"
    )
    tool_call_id: Optional[str] = Field(
        default=None,
        description="ID of the tool call this message responds to (only for TOOL role)"
    )
    name: Optional[str] = Field(
        default=None,
        description="Name of the tool that produced this result (only for TOOL role)"
    )
```

**Rationale**:
- `tool_calls` on ASSISTANT messages preserves the LLM's decision to invoke tools
- `tool_call_id` on TOOL messages links results back to requests
- `name` identifies which tool produced a result
- All fields are optional for backward compatibility
- Structure mirrors LangChain's message format for easy transformation

### Proposed MongoDB Schema Extensions

The `MessageDocument` should be extended with matching fields:

```python
# Updates to /Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_models.py

class MessageDocument(Document):
    conversation_id: Indexed(str)
    role: MessageRole
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[dict] = None

    # NEW FIELDS (all nullable for backward compatibility)
    tool_calls: Optional[List[dict]] = None  # Serialized ToolCall objects
    tool_call_id: Optional[str] = None
    name: Optional[str] = None

    class Settings:
        name = "messages"
        indexes = [
            "conversation_id",
            [("conversation_id", 1), ("created_at", 1)],
            "tool_call_id",  # NEW: For finding tool results by call ID
        ]
```

**Rationale**:
- All new fields are optional (existing messages remain valid)
- `tool_calls` stored as list of dicts (Beanie handles serialization)
- Index on `tool_call_id` enables efficient lookup of tool results
- No data migration required for existing messages

### Proposed LangChain Transformation Updates

The message conversion functions in LLM providers need bidirectional tool support:

```python
# Pattern for /Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/openai_provider.py

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

def _convert_to_langchain(self, messages: List[Message]) -> List:
    """Convert domain Messages to LangChain messages."""
    langchain_messages = []
    for msg in messages:
        if msg.role == MessageRole.USER:
            langchain_messages.append(HumanMessage(content=msg.content))
        elif msg.role == MessageRole.ASSISTANT:
            ai_msg = AIMessage(content=msg.content)
            # NEW: Preserve tool calls if present
            if msg.tool_calls:
                ai_msg.tool_calls = [
                    {
                        "id": tc.id,
                        "name": tc.name,
                        "args": tc.args
                    }
                    for tc in msg.tool_calls
                ]
            langchain_messages.append(ai_msg)
        elif msg.role == MessageRole.SYSTEM:
            langchain_messages.append(SystemMessage(content=msg.content))
        elif msg.role == MessageRole.TOOL:
            # NEW: Handle tool result messages
            langchain_messages.append(
                ToolMessage(
                    content=msg.content,
                    tool_call_id=msg.tool_call_id,
                    name=msg.name
                )
            )
    return langchain_messages

def _convert_from_langchain(self, lc_message, conversation_id: str) -> Message:
    """Convert LangChain message to domain Message."""
    base_data = {
        "conversation_id": conversation_id,
        "content": lc_message.content
    }

    if isinstance(lc_message, HumanMessage):
        return Message(role=MessageRole.USER, **base_data)
    elif isinstance(lc_message, AIMessage):
        # NEW: Extract tool calls if present
        tool_calls = None
        if hasattr(lc_message, 'tool_calls') and lc_message.tool_calls:
            tool_calls = [
                ToolCall(
                    id=tc["id"],
                    name=tc["name"],
                    args=tc["args"]
                )
                for tc in lc_message.tool_calls
            ]
        return Message(
            role=MessageRole.ASSISTANT,
            tool_calls=tool_calls,
            **base_data
        )
    elif isinstance(lc_message, ToolMessage):
        # NEW: Handle tool messages
        return Message(
            role=MessageRole.TOOL,
            tool_call_id=lc_message.tool_call_id,
            name=lc_message.name if hasattr(lc_message, 'name') else None,
            **base_data
        )
    # ... handle SystemMessage
```

**Rationale**:
- Bidirectional conversion maintains data fidelity
- LangChain's `AIMessage.tool_calls` attribute is the source of truth for tool invocations
- Domain model preserves tool call data for persistence
- Each provider (OpenAI, Anthropic, etc.) applies same pattern

### Proposed LangGraph Flow Updates

The conversation graph needs a tool execution node and routing logic:

```python
# Updates to /Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/chat_graph.py

from langgraph.prebuilt import ToolNode
from typing import Literal

def should_call_tools(state: ConversationState) -> Literal["tools", "format_response", "end"]:
    """
    Route based on whether the LLM requested tool calls.

    Checks the last message in the conversation state:
    - If it's an AIMessage with tool_calls → route to "tools"
    - If it's a regular response → route to "format_response"
    - If there's an error → route to "end"
    """
    if state.get("error"):
        return "end"

    messages = state.get("messages", [])
    if not messages:
        return "end"

    last_message = messages[-1]

    # Check if last message has tool calls
    if last_message.role == MessageRole.ASSISTANT and last_message.tool_calls:
        return "tools"

    return "format_response"

def create_chat_graph(
    llm_provider: ILLMProvider,
    message_repository: IMessageRepository,
    conversation_repository: IConversationRepository,
    tools: List  # NEW: Pass in available tools
):
    """Create chat graph with tool calling support."""

    graph_builder = StateGraph(ConversationState)

    # Existing nodes
    graph_builder.add_node("process_input", process_user_input)
    graph_builder.add_node(
        "call_llm",
        lambda state: call_llm(state, llm_provider)
    )
    graph_builder.add_node("format_response", format_response)
    graph_builder.add_node(
        "save_history",
        lambda state: save_to_history(state, message_repository, conversation_repository)
    )

    # NEW: Add tool execution node
    tool_node = ToolNode(tools)
    graph_builder.add_node("tools", tool_node)

    # Existing edges
    graph_builder.add_edge(START, "process_input")
    graph_builder.add_conditional_edges(
        "process_input",
        should_continue,  # Existing error check
        {
            "call_llm": "call_llm",
            "end": END
        }
    )

    # NEW: Route from LLM to either tools or response formatting
    graph_builder.add_conditional_edges(
        "call_llm",
        should_call_tools,
        {
            "tools": "tools",           # Execute tools
            "format_response": "format_response",  # No tools, format response
            "end": END
        }
    )

    # NEW: After tool execution, go back to LLM for continuation
    graph_builder.add_edge("tools", "call_llm")

    # Existing edges
    graph_builder.add_edge("format_response", "save_history")
    graph_builder.add_edge("save_history", END)

    return graph_builder.compile()
```

**Rationale**:
- `should_call_tools()` routing function checks for tool calls in last message
- `ToolNode` from LangGraph handles tool execution automatically
- Cyclic edge from "tools" back to "call_llm" enables multi-turn reasoning
- Graph automatically loops until LLM produces a final text response
- Existing error handling remains intact

### Tool Definition and Binding

Tools should be defined using LangChain's `@tool` decorator pattern:

```python
# NEW FILE: /Users/pablolozano/Mac Projects August/genesis/backend/app/core/tools/multiply.py

from langchain_core.tools import tool

@tool
def multiply(a: float, b: float) -> float:
    """Multiply two numbers together.

    Args:
        a: First number
        b: Second number

    Returns:
        The product of a and b
    """
    return a * b
```

**Tool Binding Strategy**:

Option 1 - Bind in LLM Provider (Recommended for flexibility):
```python
# In OpenAIProvider.__init__()
def __init__(self, tools: Optional[List] = None):
    self.model = ChatOpenAI(...)
    if tools:
        self.model = self.model.bind_tools(tools)
```

Option 2 - Bind in Graph Construction (Simpler):
```python
# In create_chat_graph()
llm_with_tools = llm_provider.model.bind_tools(tools)
```

**Recommendation**: Use Option 1 with tools passed to provider factory, allowing different tool sets per conversation if needed in future.

### Data Flow Diagram

Here's the complete data flow for a tool-calling interaction:

```
1. USER INPUT
   WebSocket → Domain Message (USER role)
   ↓
2. SAVE USER MESSAGE
   Domain Message → MongoDB MessageDocument
   ↓
3. LOAD HISTORY
   MongoDB MessageDocuments → Domain Messages
   ↓
4. TRANSFORM TO LANGCHAIN
   Domain Messages → LangChain Messages (HumanMessage, AIMessage, ToolMessage)
   ↓
5. LLM INVOCATION (with tools bound)
   LangChain Messages → LLM → AIMessage
   ↓
   [DECISION POINT: Does AIMessage have tool_calls?]
   ↓
6a. IF TOOL CALLS PRESENT:
    ↓
    Extract tool_calls from AIMessage
    ↓
    TOOL EXECUTION (ToolNode)
    Execute tool(s) → ToolMessage(s)
    ↓
    Transform to Domain Message(s) (TOOL role)
    ↓
    Add to message history
    ↓
    LOOP BACK TO STEP 4 (LLM sees tool results)
    ↓
6b. IF NO TOOL CALLS:
    ↓
    Transform AIMessage → Domain Message (ASSISTANT role)
    ↓
7. SAVE ASSISTANT MESSAGE
   Domain Message → MongoDB MessageDocument
   ↓
8. STREAM TO CLIENT
   Domain Message → WebSocket JSON
```

**Key Transformation Points**:

| Boundary | Input Format | Output Format | Location |
|----------|-------------|---------------|----------|
| WebSocket → Domain | JSON `{content: str}` | `Message(role=USER)` | websocket_handler.py |
| Domain → MongoDB | `Message` + tool fields | `MessageDocument` | mongo_message_repository.py |
| MongoDB → Domain | `MessageDocument` | `Message` + tool fields | mongo_message_repository.py |
| Domain → LangChain | `Message` + tool fields | `HumanMessage/AIMessage/ToolMessage` | openai_provider.py (and others) |
| LangChain → Domain | `AIMessage.tool_calls` | `Message.tool_calls` | openai_provider.py (and others) |
| Tool Execution | `AIMessage.tool_calls` | `ToolMessage` | LangGraph ToolNode |

## Implementation Guidance

### Phase 1: Foundation (Message Model Extensions)

**Goal**: Extend domain models to support tool calling without breaking existing functionality.

**Steps**:
1. Add `MessageRole.TOOL` to enum in `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/message.py`
2. Add `ToolCall` model class (id, name, args) to message.py
3. Add optional fields to `Message`: `tool_calls`, `tool_call_id`, `name`
4. Update `MessageDocument` in `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_models.py` with same optional fields
5. Test: Verify existing messages still load and save correctly

**Data Integrity Considerations**:
- All new fields must be Optional to maintain backward compatibility
- Existing messages without tool fields should load without errors
- Validation: `tool_calls` should only be present when `role=ASSISTANT`
- Validation: `tool_call_id` should only be present when `role=TOOL`

### Phase 2: Transformation Layer Updates

**Goal**: Enable conversion between domain Messages and LangChain's tool message types.

**Steps**:
1. Update `_convert_messages()` in each LLM provider to handle `MessageRole.TOOL`
2. Add logic to preserve `AIMessage.tool_calls` when converting from LangChain
3. Add logic to create `ToolMessage` objects when converting domain TOOL messages
4. Update `_to_domain()` in `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_message_repository.py` to deserialize tool fields
5. Update repository `create()` to serialize tool fields
6. Test: Round-trip transformation (domain → LangChain → domain) preserves all data

**Providers to Update**:
- OpenAIProvider (primary)
- AnthropicProvider
- GeminiProvider (if supports tools)
- OllamaProvider (if supports tools)

**Data Integrity Considerations**:
- Tool call IDs must be preserved exactly (used for linking)
- Tool arguments should be validated as valid JSON dicts
- Content field may be empty for some tool messages (check LangChain docs)

### Phase 3: Tool Definition and Registration

**Goal**: Create the multiply tool and make it available to the LLM.

**Steps**:
1. Create new directory `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/tools/`
2. Create `multiply.py` with `@tool` decorated function
3. Create `__init__.py` that exports available tools as a list
4. Update LLM providers to accept tools parameter and call `bind_tools()`
5. Test: Verify LLM providers successfully bind tools without errors

**Tool Definition Pattern**:
```python
from langchain_core.tools import tool

@tool
def multiply(a: float, b: float) -> float:
    """Multiply two numbers.

    Use this when you need to calculate the product of two numbers.

    Args:
        a: The first number
        b: The second number

    Returns:
        The product of a and b
    """
    return float(a * b)
```

**Data Integrity Considerations**:
- Tool function must have type hints (required by LangChain)
- Docstring must describe when to use the tool (LLM uses this)
- Return type should be serializable (primitives, dicts, lists)
- Input validation should happen within tool function

### Phase 4: LangGraph Flow Updates

**Goal**: Integrate tool execution into the conversation graph.

**Steps**:
1. Add `should_call_tools()` routing function to `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/chat_graph.py`
2. Import `ToolNode` from `langgraph.prebuilt`
3. Add tools node to graph
4. Add conditional edge from `call_llm` that routes to tools or format_response
5. Add edge from tools back to `call_llm`
6. Update `create_chat_graph()` to accept tools parameter
7. Repeat for streaming_chat_graph.py
8. Test: Graph compiles successfully, visualize with Mermaid if possible

**Cycle Prevention**:
- Consider adding max iteration limit (10-20 turns)
- Track number of tool calls in state
- Add timeout for total graph execution time

**Data Integrity Considerations**:
- Ensure ToolNode receives messages in correct format
- Verify tool results are properly wrapped in ToolMessage
- Validate that tool_call_id links are maintained through the cycle

### Phase 5: Persistence Updates

**Goal**: Save tool call messages and results to database.

**Steps**:
1. Update `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/save_history.py` to handle all message roles
2. Ensure tool call messages are saved with complete metadata
3. Ensure tool result messages are saved with tool_call_id links
4. Update message count logic (should all tool messages count?)
5. Test: Verify tool calling conversation persists correctly and can be loaded

**Message Count Considerations**:
- One user input may generate: 1 user msg + 1 AI msg with tool_calls + N tool messages + 1 final AI msg
- Should all be saved? Yes (for conversation history completeness)
- Should all increment counter? Consider only user/final assistant messages for UX

**Data Integrity Considerations**:
- Tool call IDs must be preserved for linking
- Tool execution errors should be saved (content = error message)
- Timestamps should accurately reflect when each message was created
- Conversation history reload must preserve exact order

### Phase 6: WebSocket Streaming Integration

**Goal**: Stream tool execution through WebSocket while maintaining UX.

**Steps**:
1. Update `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py` to use updated graph
2. Consider sending tool execution events to client (optional)
3. Update streaming to handle multi-turn LLM execution
4. Test: User sends message → tool called → result streamed → done

**Streaming Strategy Options**:

Option A - Silent Tool Execution:
- Don't stream tool calls/results to client
- Only stream final assistant response
- Simpler UX, less noise

Option B - Transparent Tool Execution:
- Stream new message types: `{ type: "tool_call", name: "multiply", args: {...} }`
- Stream: `{ type: "tool_result", name: "multiply", result: "..." }`
- More complex but better transparency

**Recommendation**: Start with Option A for simplicity, add Option B later for advanced UX.

**Data Integrity Considerations**:
- Ensure WebSocket stays connected during entire multi-turn execution
- Handle tool execution errors gracefully (send error message to client)
- Timeout handling for long-running tools

### Phase 7: Testing Strategy

**Goal**: Comprehensive test coverage for tool calling data flow.

**Test Categories**:

1. **Unit Tests - Domain Models**:
   - Message with tool_calls serializes/deserializes correctly
   - ToolCall model validates required fields
   - MessageRole.TOOL is valid

2. **Unit Tests - Transformations**:
   - Domain Message with tool_calls → LangChain AIMessage preserves data
   - LangChain ToolMessage → Domain Message preserves tool_call_id
   - MongoDB MessageDocument with tool fields round-trips correctly

3. **Unit Tests - Tools**:
   - multiply() function returns correct results
   - multiply() handles edge cases (zero, negative, large numbers)
   - Tool schema generation works correctly

4. **Integration Tests - Repository**:
   - Save and load message with tool_calls
   - Save and load tool result message
   - Query messages by tool_call_id

5. **Integration Tests - LangGraph**:
   - Graph routes to tool execution when LLM requests tool
   - Graph routes to response formatting when no tool requested
   - Graph handles tool execution errors
   - Graph prevents infinite loops

6. **End-to-End Tests**:
   - User message → LLM calls multiply → result returned → conversation saved
   - Load conversation with tool calls from database → resume correctly
   - WebSocket streams complete tool-calling interaction

**Test Data Examples**:
```python
# Message with tool call
tool_call_message = Message(
    conversation_id="123",
    role=MessageRole.ASSISTANT,
    content="",  # May be empty when tools called
    tool_calls=[
        ToolCall(id="call_abc", name="multiply", args={"a": 5, "b": 3})
    ]
)

# Tool result message
tool_result_message = Message(
    conversation_id="123",
    role=MessageRole.TOOL,
    content="15",  # Result as string
    tool_call_id="call_abc",
    name="multiply"
)
```

## Risks and Considerations

### Data Integrity Risks

1. **Tool Call ID Mismatches**:
   - **Risk**: Tool result message references non-existent tool_call_id
   - **Impact**: LLM may get confused or error
   - **Mitigation**: Validate tool_call_id links before saving, add database constraint

2. **Incomplete Tool Execution**:
   - **Risk**: Tool execution fails but state is not properly updated
   - **Impact**: Graph may hang or produce incorrect response
   - **Mitigation**: Use ToolNode's error handling, wrap tool execution in try/catch

3. **Message Ordering**:
   - **Risk**: Messages saved out of order in multi-turn execution
   - **Impact**: Conversation history becomes inconsistent
   - **Mitigation**: Use timestamps, ensure sequential saves, test load order

4. **Schema Migration**:
   - **Risk**: Existing messages break when new fields added
   - **Impact**: Production data becomes unreadable
   - **Mitigation**: All new fields are Optional, test backward compatibility

### Performance Risks

1. **Increased Message Volume**:
   - **Risk**: One user input generates 5+ messages (user + AI tool call + N tools + final AI)
   - **Impact**: Database storage grows faster, queries slower
   - **Mitigation**: Implement message pagination, consider TTL for old tool messages

2. **Tool Execution Latency**:
   - **Risk**: Slow tools block entire conversation flow
   - **Impact**: Poor user experience, WebSocket timeouts
   - **Mitigation**: Set timeout on tool execution (30s default), async tool execution

3. **Graph Cycles**:
   - **Risk**: LLM gets stuck in tool-calling loop
   - **Impact**: Infinite execution, resource exhaustion
   - **Mitigation**: Set max iterations (e.g., 10), add circuit breaker

4. **Parallel Tool Calls**:
   - **Risk**: LLM requests 10 tools simultaneously
   - **Impact**: Resource spike, potential rate limiting
   - **Mitigation**: ToolNode handles this automatically with asyncio, monitor concurrency

### Security Risks

1. **Tool Argument Injection**:
   - **Risk**: Malicious user crafts input that causes LLM to call tool with dangerous args
   - **Impact**: Depends on tool (for multiply: minimal; for file operations: critical)
   - **Mitigation**: Validate tool arguments, use type hints, sanitize inputs

2. **Tool Access Control**:
   - **Risk**: All users get access to all tools
   - **Impact**: Users could call tools they shouldn't have access to
   - **Mitigation**: Implement tool permission system (future), start with safe read-only tools

3. **Information Disclosure**:
   - **Risk**: Tool results expose sensitive data in conversation history
   - **Impact**: Data leaks via conversation export/sharing
   - **Mitigation**: Audit tool return values, implement data masking for sensitive results

### LLM Provider Compatibility Risks

1. **Provider-Specific Tool Formats**:
   - **Risk**: Different providers have different tool calling formats
   - **Impact**: Code works for OpenAI but breaks for Anthropic
   - **Mitigation**: LangChain abstracts this, but test each provider independently

2. **Tool Support Availability**:
   - **Risk**: Ollama or older models may not support tool calling
   - **Impact**: Feature doesn't work for all users
   - **Mitigation**: Feature detection, graceful fallback to non-tool mode

3. **Tool Call Reliability**:
   - **Risk**: LLM hallucinates tool calls with invalid schemas
   - **Impact**: ToolNode execution fails
   - **Mitigation**: ToolNode handles errors by default, validate tool calls before execution

### Data Flow Complexity Risks

1. **Transformation Data Loss**:
   - **Risk**: Data lost in domain ↔ LangChain ↔ MongoDB transformations
   - **Impact**: Incomplete conversation history, broken tool chains
   - **Mitigation**: Round-trip tests, schema validation, comprehensive logging

2. **State Bloat**:
   - **Risk**: LangGraph state grows unbounded with tool calls
   - **Impact**: Memory issues, slow graph execution
   - **Mitigation**: Clear temporary fields, use message history from DB not state

3. **Race Conditions**:
   - **Risk**: Parallel tool execution causes race in state updates
   - **Impact**: Inconsistent state, lost messages
   - **Mitigation**: ToolNode handles parallelism, ensure state updates are atomic

## Summary of Key Considerations

### Critical Dependencies

1. **Message Model Must Support Tool Fields**: Without this, cannot persist tool calls
2. **LangChain Message Conversion Must Be Bidirectional**: Round-trip fidelity is essential
3. **Graph Must Handle Cycles**: Tool execution loops back to LLM
4. **MongoDB Schema Must Be Backward Compatible**: Existing messages must still work

### Performance Bottlenecks to Monitor

1. **Tool Execution Time**: Can block entire conversation flow
2. **Message Volume Growth**: Each conversation generates more messages
3. **Graph Iteration Count**: Unbounded loops can exhaust resources
4. **Database Query Performance**: Need efficient tool_call_id lookups

### Data Integrity Boundaries

1. **WebSocket → Domain**: JSON validation, conversation ownership check
2. **Domain → MongoDB**: Schema validation, null handling
3. **Domain → LangChain**: Message type mapping, tool call preservation
4. **LangChain → Tool**: Argument validation, type checking
5. **Tool → LangChain**: Result serialization, error handling

### Recommended Implementation Order

1. **Message Model Extensions** (lowest risk, foundation for everything)
2. **Transformation Layer Updates** (enables data flow)
3. **Tool Definition** (simple, isolated)
4. **LangGraph Flow Updates** (orchestration logic)
5. **Persistence Updates** (data durability)
6. **WebSocket Integration** (user-facing)
7. **Testing & Refinement** (validation)

This order minimizes risk by building from the bottom up, with each phase testable independently before integration.

---

**Document Version**: 1.0
**Last Updated**: 2025-10-23
**Author**: data-flow-analyzer agent
