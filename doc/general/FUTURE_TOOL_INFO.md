# LangGraph Tool Calling Integration - Future Implementation Reference

**Author:** Pablo Lozano Martin
**Date:** 2025-10-26
**Status:** Experimental - Removed from main implementation
**Related Commits:** ef7cdf5, 890bec1

## Overview

This document preserves the approach taken for integrating LangGraph tool calling capabilities into the Genesis chat application. The implementation was removed to maintain architectural purity per the original PLAN.md, but the concepts and patterns here can be reused when tool calling becomes an official feature.

## Core Concept

LangGraph's tool calling allows the LLM to invoke functions during conversation to perform actions (calculations, API calls, database queries, etc.). The flow becomes:

```
User Message → LLM → [Tool Call] → Tool Execution → [Tool Response] → LLM → Final Response
```

## Architecture Changes Made

### 1. ILLMProvider Interface Extension

**File:** `backend/app/core/ports/llm_provider.py`

Added a new method to the port interface:

```python
@abstractmethod
def bind_tools(self, tools: List[Callable], **kwargs: Any) -> 'ILLMProvider':
    """
    Bind tools to the LLM provider for tool calling.

    Args:
        tools: List of callable tools to bind
        **kwargs: Additional keyword arguments for binding (e.g., parallel_tool_calls)

    Returns:
        A new ILLMProvider instance with tools bound
    """
    pass
```

**Key Design Decision:** `bind_tools()` returns a **new instance** rather than mutating the existing provider. This follows LangChain's immutability pattern.

### 2. Provider Implementations

All four providers (OpenAI, Anthropic, Gemini, Ollama) implemented `bind_tools()` using the same pattern:

**Pattern Example (OpenAI):**

```python
def bind_tools(self, tools: List[Callable], **kwargs: Any) -> 'ILLMProvider':
    """Bind tools to the OpenAI provider for tool calling."""
    bound_model = self.model.bind_tools(tools, **kwargs)

    # Create a new instance with the bound model
    new_provider = OpenAIProvider.__new__(OpenAIProvider)
    new_provider.model = bound_model

    return new_provider
```

**Why this pattern works:**
- Delegates to LangChain's native `bind_tools()` on the underlying ChatModel
- Creates a shallow copy with the bound model
- Maintains immutability - original provider unchanged
- Works across all LangChain-supported providers (OpenAI, Anthropic, Google, etc.)

### 3. LangGraph Graph Integration

**File:** `backend/app/langgraph/graphs/chat_graph.py`

The graph was modified to support tool execution with a conditional loop:

```python
from langgraph.prebuilt import ToolNode, tools_condition

def create_chat_graph(checkpointer: AsyncMongoDBSaver):
    graph_builder = StateGraph(ConversationState)

    tools = [multiply]  # List of available tools

    # Add nodes
    graph_builder.add_node("process_input", process_user_input)
    graph_builder.add_node("call_llm", call_llm)
    graph_builder.add_node("tools", ToolNode(tools))  # NEW: Tool execution node

    # Define edges
    graph_builder.add_edge(START, "process_input")
    graph_builder.add_edge("process_input", "call_llm")

    # NEW: Conditional routing based on whether LLM wants to call tools
    graph_builder.add_conditional_edges("call_llm", tools_condition)

    # NEW: Loop back to LLM after tool execution
    graph_builder.add_edge("tools", "call_llm")

    return graph_builder.compile(checkpointer=checkpointer)
```

**How `tools_condition` works:**
- Built-in LangGraph function that examines the AIMessage from `call_llm`
- If AIMessage contains `tool_calls`, routes to `"tools"` node
- If no `tool_calls`, routes to `END`
- Enables multi-step tool calling (LLM → Tool → LLM → Tool → ... → END)

### 4. Tool Binding in call_llm Node

**File:** `backend/app/langgraph/nodes/call_llm.py`

The LLM node binds tools before each invocation:

```python
async def call_llm(state: ConversationState, config: RunnableConfig) -> dict:
    messages = state["messages"]
    tools = [multiply]  # Available tools

    # Get LLM provider from config
    llm_provider = config["configurable"]["llm_provider"]

    # Bind tools to create a tool-enabled version
    llm_provider_with_tools = llm_provider.bind_tools(tools, parallel_tool_calls=False)

    # Generate response (may include tool_calls in AIMessage)
    ai_message = await llm_provider_with_tools.generate(messages)

    return {"messages": [ai_message]}
```

**Key points:**
- `parallel_tool_calls=False` forces sequential tool execution
- Original `llm_provider` remains unchanged (immutability)
- AIMessage may contain both `content` and `tool_calls`

### 5. Example Tool Implementation

**File:** `backend/app/langgraph/tools/multiply.py`

Simple example showing tool structure:

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

**Tool requirements:**
- Must be a callable (function or class with `__call__`)
- Must have type hints for parameters
- Docstring is used by LLM to understand tool purpose
- Return value is passed back to LLM as ToolMessage

**Tool registration:**

```python
# backend/app/langgraph/tools/__init__.py
from .multiply import multiply

# Makes tools importable as: from app.langgraph.tools import multiply
```

## Message Flow with Tools

### Without Tools (Original):
```
1. HumanMessage("What is 5 * 3?")
2. AIMessage(content="5 * 3 equals 15")
```

### With Tools (New):
```
1. HumanMessage("What is 5 * 3?")
2. AIMessage(content="", tool_calls=[{"name": "multiply", "args": {"a": 5, "b": 3}}])
3. ToolMessage(content="15", tool_call_id="call_xyz")
4. AIMessage(content="The result is 15")
```

**Message types:**
- `HumanMessage` - User input
- `AIMessage` with `tool_calls` - LLM requesting tool execution
- `ToolMessage` - Tool execution result
- `AIMessage` with `content` - Final LLM response

## Why Tool Messages Were Filtered

**Problem:** Internal execution details (tool calls/responses) were being exposed to the frontend.

**Solution:** Filter in `message_router.py`:

```python
# Only return user-facing messages
user_facing_messages = []
for msg in base_messages:
    # Skip tool messages (internal execution details)
    if msg.type == "tool":
        continue

    # Skip AI messages that only contain tool_calls (no content)
    if msg.type == "ai":
        if hasattr(msg, 'tool_calls') and msg.tool_calls and not msg.content:
            continue

    user_facing_messages.append(msg)
```

**Why this matters:**
- Tool calls are like `thread_id` - internal LangGraph execution details
- Users should only see the final answer, not intermediate tool invocations
- Similar to how SQL queries aren't shown to users, just the results

## Frontend Impact

### Message Role Extension

**File:** `frontend/src/services/conversationService.ts`

```typescript
export interface Message {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | "system" | "tool";  // Added "tool"
  content: string;
  created_at: string;
}
```

**Note:** If tool messages are filtered in backend, the `"tool"` role becomes unnecessary and should be removed.

## Implementation Checklist for Future

When implementing tool calling as an official feature:

### Backend Tasks

- [ ] **Create issue/plan document** - Tool calling deserves its own implementation plan
- [ ] **Add `bind_tools()` to ILLMProvider interface** (pattern documented above)
- [ ] **Implement `bind_tools()` in all 4 providers** (OpenAI, Anthropic, Gemini, Ollama)
- [ ] **Create tools directory** with proper structure
- [ ] **Implement ToolNode and tools_condition in graph**
- [ ] **Add tool binding in call_llm node**
- [ ] **Filter tool messages from API responses** (don't expose to frontend)
- [ ] **Add tool configuration** (which tools are available per conversation?)
- [ ] **Add tool discovery mechanism** (dynamic tool loading?)
- [ ] **Add tool security** (authorization, rate limiting, sandboxing)

### Testing Tasks

- [ ] **Unit tests for each tool** (input validation, error handling)
- [ ] **Unit tests for bind_tools()** (each provider)
- [ ] **Integration tests for tool execution flow** (LLM → Tool → LLM)
- [ ] **Integration tests for multi-tool scenarios** (sequential tool calls)
- [ ] **E2E tests for user-facing tool workflows** (e.g., "calculate 5 * 3")
- [ ] **Test tool error handling** (tool exceptions, timeouts, invalid args)
- [ ] **Test message filtering** (ensure tool messages don't leak to frontend)

### Documentation Tasks

- [ ] **Update ARCHITECTURE.md** with tool calling architecture
- [ ] **Create TOOLS.md** guide for implementing new tools
- [ ] **Update API.md** with any tool-related endpoints (if any)
- [ ] **Add tool calling examples** to documentation

## Security Considerations

### Tool Authorization

**Question:** Who can use which tools?

**Options:**
1. **Global tools** - All users can use all tools
2. **Per-conversation tools** - Tools enabled per conversation
3. **Per-user tools** - Tools based on user role/permissions
4. **Context-aware tools** - Tools available based on conversation context

### Tool Sandboxing

**Dangerous tools need isolation:**
- File system operations
- Network requests
- Database queries
- Code execution

**Mitigation strategies:**
- Whitelist allowed operations
- Resource limits (time, memory, network)
- Separate execution context
- Audit logging

### Tool Rate Limiting

**Prevent abuse:**
- Max tool calls per conversation
- Max tool calls per user per time period
- Cost tracking for expensive tools (API calls)

## Example Tools to Implement

### Low-hanging fruit:
1. **Calculator** - Basic math operations (add, subtract, multiply, divide)
2. **Web search** - Search the web for information
3. **Date/time** - Get current date, format dates, calculate date differences
4. **Unit conversion** - Convert between units (temperature, distance, weight)

### Medium complexity:
5. **Code interpreter** - Execute Python/JavaScript in sandbox
6. **Image generation** - Generate images from text (DALL-E, Stable Diffusion)
7. **Database query** - Query application database (with restrictions)
8. **API calls** - Call external APIs (weather, news, etc.)

### Advanced:
9. **File operations** - Create, read, update files (with security)
10. **Email/notifications** - Send emails or push notifications
11. **Workflow automation** - Chain multiple tools together
12. **Memory/RAG** - Retrieve from long-term conversation memory

## Alternative Architectures Considered

### Option 1: Tool-per-Node (Rejected)

```python
graph_builder.add_node("multiply_tool", multiply_node)
graph_builder.add_node("search_tool", search_node)
# ... one node per tool
```

**Pros:** Fine-grained control over each tool
**Cons:** Graph becomes huge with many tools, hard to maintain

### Option 2: Single Tool Executor Node (Chosen)

```python
graph_builder.add_node("tools", ToolNode(all_tools))
```

**Pros:** Scales to many tools, clean graph structure
**Cons:** Less control over individual tool execution

### Option 3: LangChain Agent (Considered)

```python
from langgraph.prebuilt import create_react_agent
agent = create_react_agent(llm, tools, checkpointer=checkpointer)
```

**Pros:** Fully-featured agent with built-in reasoning
**Cons:** Less control, harder to customize, different architecture

**Decision:** Option 2 (ToolNode) chosen for balance of simplicity and control.

## Performance Considerations

### Tool Execution Latency

Each tool call adds latency:
- LLM inference time: ~1-3 seconds
- Tool execution time: varies (0.1s for math, 5s+ for API calls)
- Additional LLM call after tool: ~1-3 seconds

**Total:** Can add 5-10+ seconds per tool-using conversation turn

### Checkpoint Size Growth

Tool messages increase checkpoint size:
- 1 HumanMessage: ~100 bytes
- 1 AIMessage with tool_calls: ~200-500 bytes
- 1 ToolMessage: ~100-1000 bytes (depending on result)

**Impact:** More MongoDB storage, slower state retrieval

### Streaming Considerations

With tools, streaming becomes complex:
1. LLM streams thinking → detects need for tool
2. Streaming pauses while tool executes
3. LLM streams final response

**User experience:** Intermittent streaming, need loading states

## Related LangGraph Documentation

- [LangGraph Tools](https://langchain-ai.github.io/langgraph/concepts/low_level/#tools)
- [ToolNode](https://langchain-ai.github.io/langgraph/reference/prebuilt/#toolnode)
- [tools_condition](https://langchain-ai.github.io/langgraph/reference/prebuilt/#tools_condition)
- [Tool Calling Guide](https://python.langchain.com/docs/modules/model_io/chat/function_calling/)

## Conclusion

The tool calling integration followed LangGraph best practices and maintained architectural boundaries:
- ✅ Used native LangChain/LangGraph patterns (ToolNode, tools_condition)
- ✅ Maintained immutability (bind_tools returns new instance)
- ✅ Preserved hexagonal architecture (tools are adapters)
- ✅ Kept frontend clean (filtered internal messages)

**When to implement officially:**
- After core chat functionality is stable
- When specific use cases for tools are identified
- After security model is designed
- With proper testing and monitoring

This document provides a solid foundation for implementing tool calling when the time is right.

---

**Preserved code examples:** See commits ef7cdf5 and 890bec1 for full implementation details.
