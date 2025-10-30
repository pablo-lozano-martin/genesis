# create_react_agent API Research

**Date**: 2025-10-30
**Source**: Context7 LangGraph Documentation

## Function Signature

```python
from langgraph.prebuilt import create_react_agent

agent = create_react_agent(
    model,  # LangChain chat model (ChatOpenAI, ChatAnthropic, etc.)
    tools,  # List of callable tools
    prompt=None,  # Optional: System prompt or callable that returns messages
    pre_model_hook=None,  # Optional: Callable run before model invocation
    post_model_hook=None,  # Optional: Callable run after model invocation
    response_format=None,  # Optional: Pydantic model for structured output
    checkpointer=None,  # Optional: Checkpointer for state persistence
    state_schema=None,  # Optional: Custom state schema (NOT CONFIRMED)
)
```

## Key Findings

### 1. System Prompt Support: YES ✅

The `prompt` parameter supports system prompts in two ways:

**Option A - Direct string/template**:
```python
agent = create_react_agent(
    model="anthropic:claude-3-7-sonnet-latest",
    tools=[get_weather],
    prompt="You are a helpful assistant"
)
```

**Option B - Callable function (for dynamic prompts)**:
```python
def prepare_messages(state, *, store: BaseStore):
    memories = "\n".join(item.value["text"] for item in items)
    return [
        {"role": "system", "content": f"You are a helpful assistant.\n{memories}"}
    ] + state["messages"]

agent = create_react_agent(
    model,
    tools=[upsert_memory],
    prompt=prepare_messages,  # Callable
    store=store,
)
```

### 2. Model Parameter

- **Accepts**: LangChain chat model instances (ChatOpenAI, ChatAnthropic, etc.)
- **Requires**: Model must support tool calling via `bind_tools()`
- **Example**:
```python
from langchain_anthropic import ChatAnthropic
model = ChatAnthropic(model="claude-3-7-sonnet-latest")
agent = create_react_agent(model, tools)
```

### 3. Tools Parameter

- **Type**: List of callables (functions decorated with `@tool` or plain functions)
- **Binding**: Tools are bound at graph creation time (not invocation time)
- **Example**:
```python
@tool
def multiply(a: int, b: int) -> int:
    """Multiply two numbers."""
    return a * b

agent = create_react_agent(model, tools=[multiply])
```

### 4. State Schema

**UNCERTAIN**: Documentation does not explicitly show `state_schema` parameter.

**Evidence**:
- Examples show agents invoked with `{"messages": [...]}` state
- ConversationState extending MessagesState should work
- May need to use `pre_model_hook` for custom state fields

**Recommendation**: Test with ConversationState first. If fails, use MessagesState base.

### 5. Checkpointer Support: YES ✅

```python
from langgraph.checkpoint.memory import InMemorySaver

agent = create_react_agent(
    model,
    tools,
    checkpointer=InMemorySaver()  # or AsyncMongoDBSaver
)
```

### 6. Event Streaming

- Uses `astream_events()` for streaming
- Event types: `on_chat_model_stream`, `on_tool_start`, `on_tool_end`
- Same as hand-built graphs

### 7. Tool Execution

- Uses `ToolNode` internally for tool execution
- Supports error handling (default, custom messages)
- Supports parallel tool calls (can be disabled via `model.bind_tools(tools, parallel_tool_calls=False)`)

### 8. Hooks Support

**pre_model_hook**: Run before LLM invocation
```python
def pre_model_hook(state):
    # Initialize state or modify messages
    return state

agent = create_react_agent(model, tools, pre_model_hook=pre_model_hook)
```

**post_model_hook**: Run after LLM invocation
```python
def post_model_hook(state):
    # Post-process LLM response
    return state

agent = create_react_agent(model, tools, post_model_hook=post_model_hook)
```

### 9. Configuration Access

Tools can access `RunnableConfig` for runtime data:
```python
from langchain_core.runnables import RunnableConfig

def get_user_info(config: RunnableConfig) -> str:
    user_id = config["configurable"].get("user_id")
    return f"User is {user_id}"

agent = create_react_agent(model, tools=[get_user_info])
agent.invoke(
    {"messages": [...]},
    config={"configurable": {"user_id": "user_123"}}
)
```

## Migration Strategy

### Approach 1: Direct Migration (Recommended)

Use `prompt` parameter for system prompt:

```python
from langgraph.prebuilt import create_react_agent
from app.langgraph.prompts.onboarding_prompts import ONBOARDING_SYSTEM_PROMPT

agent = create_react_agent(
    model=llm_provider.get_model(),  # Underlying LangChain model
    tools=[read_data, write_data, rag_search, export_data],
    prompt=ONBOARDING_SYSTEM_PROMPT,  # System prompt string
    checkpointer=checkpointer
)
```

### Approach 2: Callable Prompt (If state initialization needed)

```python
def prepare_onboarding_messages(state):
    """Inject system prompt and initialize state."""
    return [
        {"role": "system", "content": ONBOARDING_SYSTEM_PROMPT}
    ] + state.get("messages", [])

agent = create_react_agent(
    model=llm_provider.get_model(),
    tools=[read_data, write_data, rag_search, export_data],
    prompt=prepare_onboarding_messages,  # Callable
    checkpointer=checkpointer
)
```

### Approach 3: pre_model_hook (If state schema incompatible)

```python
def initialize_state_hook(state):
    """Initialize onboarding-specific fields."""
    if not state.get("messages"):
        state["messages"] = []
    # Ensure system prompt is first message
    if not state["messages"] or state["messages"][0].type != "system":
        state["messages"].insert(0, SystemMessage(content=ONBOARDING_SYSTEM_PROMPT))
    return state

agent = create_react_agent(
    model=llm_provider.get_model(),
    tools=[read_data, write_data, rag_search, export_data],
    pre_model_hook=initialize_state_hook,
    checkpointer=checkpointer
)
```

## Answers to Planning Questions

1. **Does create_react_agent accept a `prompt` or `system_prompt` parameter?**
   - **YES**: Uses `prompt` parameter (not `system_prompt`)

2. **What is the exact function signature?**
   - `create_react_agent(model, tools, prompt=None, pre_model_hook=None, post_model_hook=None, response_format=None, checkpointer=None)`

3. **Does it work with custom state schemas (ConversationState)?**
   - **UNCERTAIN**: No explicit `state_schema` parameter in docs
   - **Recommendation**: Test with ConversationState, fallback to MessagesState if needed

4. **How are tools passed?**
   - As a list parameter: `tools=[read_data, write_data, ...]`

5. **Does it support AsyncMongoDBSaver checkpointer?**
   - **YES**: Checkpointer passed as parameter

6. **What events does it emit via astream_events()?**
   - Same as hand-built: `on_chat_model_stream`, `on_tool_start`, `on_tool_end`

## Migration Risks

### Risk 1: State Schema Compatibility (MEDIUM)
- **Issue**: ConversationState may not be compatible
- **Mitigation**: Test with ConversationState first, use pre_model_hook if needed

### Risk 2: Tool Binding (LOW)
- **Issue**: Tools bound at creation time, not invocation time
- **Mitigation**: Already resolved in plan - pass tools to factory

### Risk 3: System Prompt Injection (LOW)
- **Issue**: Prompt parameter might not work as expected
- **Mitigation**: Documented 3 alternative approaches above

## Next Steps

1. Implement get_model() method in ILLMProvider interface
2. Test create_react_agent with ConversationState
3. Use `prompt` parameter for system prompt (Approach 1)
4. Fallback to callable prompt or pre_model_hook if needed
