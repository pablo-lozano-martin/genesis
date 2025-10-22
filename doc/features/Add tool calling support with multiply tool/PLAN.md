# Implementation Plan: Add Tool Calling Support with Multiply Tool

## Overview

This plan implements LLM tool calling capability following the LangGraph pattern from `/doc/general/agent-memory.ipynb`. We'll keep it simple and avoid over-engineering.

## Architecture Decision

**Keep it simple**: Follow LangGraph's standard tool calling pattern using `ToolNode` and `tools_condition` from `langgraph.prebuilt`.

## Implementation Phases

### Phase 1: Domain Model Extensions (Foundation)

**Goal**: Add minimal domain support for tool messages.

**Files to modify**:

1. `/backend/app/core/domain/message.py`
   - Add `TOOL = "tool"` to `MessageRole` enum
   - No other changes needed (use existing `metadata` field for tool data)

**Changes**:
```python
class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"  # NEW
```

**Testing**:
- Unit test: Verify `MessageRole.TOOL` exists
- Unit test: Create Message with `role=MessageRole.TOOL`

---

### Phase 2: Create the Multiply Tool

**Goal**: Implement a simple multiply tool using LangChain's pattern.

**New file**: `/backend/app/langgraph/tools/math_tools.py`
```python
from langchain_core.tools import tool

@tool
def multiply(a: float, b: float) -> float:
    """Multiply two numbers together.

    Use this when you need to calculate the product of two numbers.

    Args:
        a: First number
        b: Second number

    Returns:
        The product of a and b
    """
    return a * b
```

**New file**: `/backend/app/langgraph/tools/__init__.py`
```python
from .math_tools import multiply

__all__ = ["multiply"]
```

**Testing**:
- Unit test: `multiply(5, 3)` returns `15`
- Unit test: `multiply(0, 100)` returns `0`
- Unit test: `multiply(-2, 5)` returns `-10`

---

### Phase 3: Update LangGraph State

**Goal**: Make state compatible with LangChain's MessagesState pattern.

**File to modify**: `/backend/app/langgraph/state.py`

**Current state**:
```python
class ConversationState(TypedDict):
    messages: Annotated[list[Message], add_messages]
    conversation_id: str
    user_id: str
    current_input: Optional[str]
    llm_response: Optional[str]
    error: Optional[str]
```

**Key issue**: `messages` uses our domain `Message` type, but LangGraph's `ToolNode` expects LangChain message types (HumanMessage, AIMessage, ToolMessage).

**Solution**: Keep both - use LangChain messages for LangGraph flow, convert to domain Messages for persistence.

**Updated state**:
```python
from langchain_core.messages import BaseMessage

class ConversationState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]  # LangChain messages
    conversation_id: str
    user_id: str
    current_input: Optional[str]
    error: Optional[str]
```

**Note**: Remove `llm_response` field - not needed with tool calling flow.

---

### Phase 4: Update LLM Provider for Tool Binding

**Goal**: Enable OpenAI provider to bind tools (start with OpenAI only for MVP).

**File to modify**: `/backend/app/adapters/outbound/llm_providers/openai_provider.py`

**Changes**:
1. Update `__init__` to accept optional tools parameter
2. Bind tools to model if provided
3. Update `_convert_messages()` to handle LangChain messages directly (skip domain Message conversion)

**Updated OpenAIProvider**:
```python
class OpenAIProvider(ILLMProvider):
    def __init__(self, tools: Optional[List] = None):
        # ... existing setup ...
        self.model = ChatOpenAI(...)

        # Bind tools if provided
        if tools:
            self.model = self.model.bind_tools(tools)
```

**Note**: For MVP, only update OpenAIProvider. Other providers can be added later.

---

### Phase 5: Update LangGraph Nodes

**Goal**: Modify nodes to work with LangChain messages and tool flow.

#### 5.1 Update `process_input` node

**File**: `/backend/app/langgraph/nodes/process_input.py`

**Change**: Create HumanMessage instead of domain Message
```python
from langchain_core.messages import HumanMessage

async def process_user_input(state: ConversationState) -> dict:
    current_input = state.get("current_input", "").strip()

    if not current_input:
        return {"error": "Input cannot be empty"}

    user_message = HumanMessage(content=current_input)

    return {
        "messages": [user_message],
        "error": None
    }
```

#### 5.2 Update `call_llm` node

**File**: `/backend/app/langgraph/nodes/call_llm.py`

**Change**: Return full AIMessage (not just content string)
```python
async def call_llm(state: ConversationState, llm_provider: ILLMProvider) -> dict:
    try:
        messages = state["messages"]

        # Invoke LLM - returns AIMessage (potentially with tool_calls)
        response = await llm_provider.model.ainvoke(messages)

        return {
            "messages": [response],  # Add AIMessage to state
            "error": None
        }
    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        return {"error": f"Failed to generate response: {str(e)}"}
```

#### 5.3 Remove `format_response` node

**Reason**: Not needed - messages are already in correct format for tool flow.

#### 5.4 Update `save_history` node

**File**: `/backend/app/langgraph/nodes/save_history.py`

**Change**: Convert LangChain messages to domain Messages before saving
```python
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

async def save_to_history(
    state: ConversationState,
    message_repository: IMessageRepository,
    conversation_repository: IConversationRepository
) -> dict:
    try:
        conversation_id = state["conversation_id"]
        langchain_messages = state["messages"]

        # Convert LangChain messages to domain Messages
        for lc_msg in langchain_messages:
            domain_msg = _convert_to_domain(lc_msg, conversation_id)
            await message_repository.create(domain_msg)

        # Update conversation metadata
        await conversation_repository.increment_message_count(
            conversation_id,
            len(langchain_messages)
        )

        return {}
    except Exception as e:
        logger.error(f"Failed to save history: {e}")
        return {"error": f"Failed to save conversation: {str(e)}"}

def _convert_to_domain(lc_message, conversation_id: str) -> Message:
    """Convert LangChain message to domain Message."""
    if isinstance(lc_message, HumanMessage):
        return Message(
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content=lc_message.content
        )
    elif isinstance(lc_message, AIMessage):
        # Check if AIMessage has tool calls
        metadata = None
        if hasattr(lc_message, 'tool_calls') and lc_message.tool_calls:
            metadata = {"tool_calls": lc_message.tool_calls}

        return Message(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content=lc_message.content,
            metadata=metadata
        )
    elif isinstance(lc_message, ToolMessage):
        return Message(
            conversation_id=conversation_id,
            role=MessageRole.TOOL,
            content=lc_message.content,
            metadata={
                "tool_call_id": lc_message.tool_call_id,
                "name": getattr(lc_message, 'name', '')
            }
        )
```

---

### Phase 6: Update Chat Graph with Tool Flow

**Goal**: Add ToolNode and conditional routing for tool execution.

**File to modify**: `/backend/app/langgraph/graphs/chat_graph.py`

**Changes**:
1. Import `ToolNode` and `tools_condition` from langgraph.prebuilt
2. Add ToolNode to graph
3. Add conditional edges for tool routing
4. Remove format_response node

**Updated graph**:
```python
from langgraph.prebuilt import ToolNode, tools_condition
from app.langgraph.tools import multiply

def create_chat_graph(
    llm_provider: ILLMProvider,
    message_repository: IMessageRepository,
    conversation_repository: IConversationRepository
):
    logger.info("Creating chat conversation graph")

    # Define tools
    tools = [multiply]

    graph_builder = StateGraph(ConversationState)

    # Add nodes
    graph_builder.add_node("process_input", process_user_input)
    graph_builder.add_node(
        "call_llm",
        lambda state: call_llm(state, llm_provider)
    )
    graph_builder.add_node("tools", ToolNode(tools))  # NEW
    graph_builder.add_node(
        "save_history",
        lambda state: save_to_history(state, message_repository, conversation_repository)
    )

    # Add edges
    graph_builder.add_edge(START, "process_input")

    # Conditional: process_input -> call_llm or END (if error)
    graph_builder.add_conditional_edges(
        "process_input",
        lambda state: "end" if state.get("error") else "call_llm",
        {
            "call_llm": "call_llm",
            "end": END
        }
    )

    # NEW: Conditional routing from call_llm
    # - If AIMessage has tool_calls -> route to "tools"
    # - Otherwise -> route to "save_history"
    graph_builder.add_conditional_edges(
        "call_llm",
        tools_condition,  # Built-in condition from langgraph
    )

    # NEW: After tool execution, loop back to call_llm
    graph_builder.add_edge("tools", "call_llm")

    # Save and end
    graph_builder.add_edge("save_history", END)

    graph = graph_builder.compile()

    logger.info("Chat conversation graph compiled successfully")
    return graph
```

**Note**: `tools_condition` automatically routes to:
- `"tools"` if last message has tool_calls
- `"__end__"` otherwise

We need to map `"__end__"` to our `"save_history"` node:

```python
graph_builder.add_conditional_edges(
    "call_llm",
    tools_condition,
    {
        "tools": "tools",
        "__end__": "save_history"
    }
)
```

---

### Phase 7: Update WebSocket Handler

**Goal**: Load conversation history and convert to LangChain messages for graph input.

**File to modify**: `/backend/app/adapters/inbound/websocket_handler.py`

**Current flow** (lines 128-162):
```python
messages = await message_repository.get_by_conversation_id(conversation_id)

async for token in llm_provider.stream(messages):
    # Stream tokens...
```

**Updated flow**:
```python
# Load domain messages from DB
domain_messages = await message_repository.get_by_conversation_id(conversation_id)

# Convert to LangChain messages
langchain_messages = _convert_domain_to_langchain(domain_messages)

# Run graph (non-streaming for MVP)
graph = create_chat_graph(llm_provider, message_repository, conversation_repository)
result = await graph.ainvoke({
    "messages": langchain_messages,
    "conversation_id": conversation_id,
    "user_id": user.id,
    "current_input": client_message.content
})

# Extract final AI response and stream it
final_messages = result["messages"]
assistant_message = final_messages[-1]  # Last message is AI response

# Send complete response to client
complete_msg = ServerCompleteMessage(
    message_id=str(assistant_message.id),
    conversation_id=conversation_id
)
await manager.send_message(websocket, complete_msg.model_dump())
```

**Helper function**:
```python
def _convert_domain_to_langchain(domain_messages: List[Message]) -> List[BaseMessage]:
    """Convert domain Messages to LangChain messages."""
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

    langchain_messages = []
    for msg in domain_messages:
        if msg.role == MessageRole.USER:
            langchain_messages.append(HumanMessage(content=msg.content))
        elif msg.role == MessageRole.ASSISTANT:
            ai_msg = AIMessage(content=msg.content)
            # Restore tool_calls from metadata if present
            if msg.metadata and "tool_calls" in msg.metadata:
                ai_msg.tool_calls = msg.metadata["tool_calls"]
            langchain_messages.append(ai_msg)
        elif msg.role == MessageRole.SYSTEM:
            langchain_messages.append(SystemMessage(content=msg.content))
        elif msg.role == MessageRole.TOOL:
            langchain_messages.append(ToolMessage(
                content=msg.content,
                tool_call_id=msg.metadata.get("tool_call_id", ""),
                name=msg.metadata.get("name", "")
            ))
    return langchain_messages
```

**Note**: For MVP, we'll lose streaming during tool execution. This can be improved later.

---

### Phase 8: Update Provider Factory

**Goal**: Pass tools to OpenAI provider at initialization.

**File to modify**: `/backend/app/adapters/outbound/llm_providers/provider_factory.py`

**Change**:
```python
from app.langgraph.tools import multiply

class LLMProviderFactory:
    @staticmethod
    def create_provider(provider_type: str = None, tools: List = None) -> ILLMProvider:
        # ... existing code ...

        if provider_type == "openai":
            return OpenAIProvider(tools=tools)
        # ... other providers ...
```

**Update call sites**: Pass `tools=[multiply]` when creating provider.

---

### Phase 9: Testing

#### Unit Tests

**Test file**: `/backend/tests/unit/test_math_tools.py`
```python
from app.langgraph.tools.math_tools import multiply

def test_multiply_positive():
    result = multiply.invoke({"a": 5, "b": 3})
    assert result == 15

def test_multiply_zero():
    result = multiply.invoke({"a": 0, "b": 100})
    assert result == 0

def test_multiply_negative():
    result = multiply.invoke({"a": -2, "b": 5})
    assert result == -10
```

**Test file**: `/backend/tests/unit/test_message_role.py`
```python
from app.core.domain.message import MessageRole

def test_tool_role_exists():
    assert MessageRole.TOOL == "tool"
```

#### Integration Tests

**Test file**: `/backend/tests/integration/test_tool_calling_flow.py`
```python
import pytest
from app.langgraph.graphs.chat_graph import create_chat_graph
from app.langgraph.tools import multiply

@pytest.mark.asyncio
async def test_multiply_tool_execution(
    mock_llm_provider,
    mock_message_repository,
    mock_conversation_repository
):
    """Test complete tool calling flow."""
    graph = create_chat_graph(
        mock_llm_provider,
        mock_message_repository,
        mock_conversation_repository
    )

    result = await graph.ainvoke({
        "messages": [],
        "conversation_id": "test-conv",
        "user_id": "test-user",
        "current_input": "What is 12 times 34?"
    })

    # Verify messages contain tool call and final response
    messages = result["messages"]
    assert any(hasattr(msg, 'tool_calls') for msg in messages)
    assert messages[-1].content  # Final AI response exists
```

#### Manual Testing Checklist

1. Basic tool use:
   - Send "What is 12 * 34?" via API/WebSocket
   - Verify response is "408" or similar
   - Check MongoDB: should have USER, ASSISTANT (with tool_calls), TOOL, ASSISTANT messages

2. No tool needed:
   - Send "Hello, how are you?"
   - Verify normal conversation (no tool calls)

3. Multiple tools in sequence:
   - Send "Calculate 5 * 3, then multiply that by 2"
   - Verify multiple tool calls work

4. Error handling:
   - Send "Multiply abc by xyz"
   - Verify LLM handles gracefully (no crash)

---

## Files Summary

### New Files
1. `/backend/app/langgraph/tools/__init__.py`
2. `/backend/app/langgraph/tools/math_tools.py`
3. `/backend/tests/unit/test_math_tools.py`
4. `/backend/tests/integration/test_tool_calling_flow.py`

### Modified Files
1. `/backend/app/core/domain/message.py` - Add `MessageRole.TOOL`
2. `/backend/app/langgraph/state.py` - Use LangChain BaseMessage type
3. `/backend/app/langgraph/nodes/process_input.py` - Create HumanMessage
4. `/backend/app/langgraph/nodes/call_llm.py` - Return full AIMessage
5. `/backend/app/langgraph/nodes/save_history.py` - Convert LangChain to domain Messages
6. `/backend/app/langgraph/graphs/chat_graph.py` - Add ToolNode and routing
7. `/backend/app/adapters/outbound/llm_providers/openai_provider.py` - Support tool binding
8. `/backend/app/adapters/outbound/llm_providers/provider_factory.py` - Pass tools to provider
9. `/backend/app/adapters/inbound/websocket_handler.py` - Use graph with tool support

### Deleted Files
- `/backend/app/langgraph/nodes/format_response.py` (no longer needed)

---

## Key Design Decisions

1. **Use LangChain messages in state**: Simplifies tool integration, avoids double conversion
2. **Convert to domain Messages only at persistence**: Clean separation of concerns
3. **Use metadata field for tool data**: No MongoDB schema changes needed
4. **Start with OpenAI only**: Prove the pattern, then extend
5. **Non-streaming for MVP**: Simplifies initial implementation
6. **Use LangGraph's built-in ToolNode**: Avoid reinventing the wheel

---

## Migration Strategy

**No migration needed** - all changes are additive:
- New MessageRole value is backward compatible
- Existing messages work unchanged
- Tool calling is opt-in via graph construction

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking change to state | High | Test thoroughly, update all nodes consistently |
| Loss of streaming | Medium | Document limitation, plan streaming in follow-up |
| OpenAI-only support | Low | Document clearly, add other providers incrementally |
| Tool execution errors | Medium | Wrap in try/catch, LLM can explain errors to user |
| Infinite loops | Medium | LangGraph has built-in cycle prevention |

---

## Success Criteria

- User can ask "What is 5 * 3?" and get correct answer "15"
- Tool calls appear in MongoDB conversation history
- Normal conversations (without tools) still work
- All tests pass
- No breaking changes to existing functionality

---

## Future Enhancements (Out of Scope)

1. Restore streaming during tool execution
2. Add more tools (add, subtract, divide)
3. Support tool calling in Anthropic/Gemini/Ollama providers
4. Add tool execution permissions
5. Display tool execution steps to user
6. Add checkpointer for conversation memory persistence
