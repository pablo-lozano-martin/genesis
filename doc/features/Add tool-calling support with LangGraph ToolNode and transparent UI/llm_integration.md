# LLM Integration Analysis

## Request Summary

Add tool-calling support with LangGraph's ToolNode and transparent UI integration. This feature enables LLM providers to call tools (functions) during inference, with seamless integration between the ILLMProvider port abstraction and LangGraph's prebuilt ToolNode. The implementation should maintain provider abstraction while enabling transparent tool execution without requiring changes to application code.

---

## Relevant Files & Modules

### Files to Examine

**LLM Provider Port & Implementations:**
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/llm_provider.py` - ILLMProvider port interface defining tool-calling contract
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/openai_provider.py` - OpenAI provider with bind_tools implementation
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/anthropic_provider.py` - Anthropic provider with bind_tools implementation
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/gemini_provider.py` - Gemini provider with bind_tools implementation
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/ollama_provider.py` - Ollama provider with bind_tools implementation
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/provider_factory.py` - LLM provider factory for creating provider instances

**LangGraph Integration:**
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/state.py` - ConversationState extending MessagesState
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/chat_graph.py` - Main chat graph with ToolNode setup
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/streaming_chat_graph.py` - Streaming graph with tool execution loop
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/call_llm.py` - LLM invocation node with bind_tools call
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/process_input.py` - Input validation node
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/__init__.py` - Tool exports
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/multiply.py` - Example tool (multiply function)

**Configuration & Infrastructure:**
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/config/settings.py` - Settings with LLM provider configuration

**Testing:**
- `/Users/pablolozano/Mac Projects August/genesis/backend/tests/unit/test_llm_providers.py` - Unit tests for LLM provider factory

### Key Functions & Classes

**Port Interface:**
- `ILLMProvider.bind_tools(tools: List[Callable], **kwargs: Any) -> ILLMProvider` - Abstract method for binding tools

**Provider Implementations:**
- `OpenAIProvider.bind_tools()` - Creates new provider instance with bound LangChain model
- `AnthropicProvider.bind_tools()` - Creates new provider instance with bound LangChain model
- `GeminiProvider.bind_tools()` - Creates new provider instance with bound LangChain model
- `OllamaProvider.bind_tools()` - Creates new provider instance with bound LangChain model

**LangGraph Components:**
- `ConversationState` - State schema extending MessagesState
- `create_chat_graph()` - Graph builder with ToolNode
- `create_streaming_chat_graph()` - Streaming graph builder with tool loop
- `call_llm()` - Node that invokes LLM with tools bound
- `ToolNode(tools)` - LangGraph prebuilt node for executing tool calls

---

## Current Integration Overview

### Provider Abstraction Layer

The project implements clean separation between business logic and LLM provider specifics through the hexagonal architecture pattern:

**ILLMProvider Port** (`/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/llm_provider.py`):
- Defines abstract contract for LLM operations
- Methods: `generate()`, `stream()`, `get_model_name()`, `bind_tools()`
- Works exclusively with LangChain `BaseMessage` types (HumanMessage, AIMessage, SystemMessage, ToolMessage)
- All providers implement this interface with zero exposure to application code

**Provider Implementations** (OpenAI, Anthropic, Gemini, Ollama):
- Each wraps a LangChain chat model (ChatOpenAI, ChatAnthropic, ChatGoogleGenerativeAI, ChatOllama)
- Implements `generate()` via `model.ainvoke(messages)`
- Implements `stream()` via `model.astream(messages)` yielding content tokens
- Implements `bind_tools()` by delegating to LangChain's `model.bind_tools()`

### Current bind_tools Implementation Pattern

All four providers use an identical pattern for tool binding:

```python
def bind_tools(self, tools: List[Callable], **kwargs: Any) -> 'ILLMProvider':
    """Bind tools to the provider for tool calling."""
    bound_model = self.model.bind_tools(tools, **kwargs)
    # Create a new instance with the bound model
    new_provider = ProviderClass.__new__(ProviderClass)
    new_provider.model = bound_model
    return new_provider
```

**Key Design Decisions:**
- Returns a new ILLMProvider instance (immutable approach, no side effects)
- Delegates tool binding to underlying LangChain model via `bind_tools()`
- Forwards all kwargs directly (supports provider-specific options like `parallel_tool_calls=False`)
- Minimal state initialization (only `.model` attribute set)

### LangChain Model Integration

**How LangChain supports tool calling:**
- All LangChain chat models implement `.bind_tools(tools, **kwargs)` method
- This method adds tool schema to the model's prompt/API call
- Model returns AIMessage with `tool_calls` attribute containing structured tool call data
- `tool_calls` is a list of dicts with format: `{"name": "tool_name", "args": {...}, "id": "...", "type": "tool_call"}`

**Provider-Specific bind_tools Behavior:**
- **OpenAI**: Converts tools to OpenAI function schema, uses `function_call` parameter
- **Anthropic**: Converts tools to Anthropic tool schema, uses `tool_choice` parameter
- **Gemini**: Converts tools to Google tool schema, native support
- **Ollama**: Local model; tool calling depends on underlying model capabilities

### LangGraph Integration

**Graph Architecture** (`/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/chat_graph.py`):
```
START -> process_input -> call_llm -> [tools_condition]
                                          |
                                          v
                                        tools (ToolNode) -> call_llm -> END
                                          OR
                                          END (if no tool calls)
```

**How ToolNode Works:**
- `ToolNode(tools)` is a prebuilt LangGraph node that executes tools
- Input: MessagesState with AIMessage containing `tool_calls`
- Processing: Extracts tool_calls from last AIMessage, executes each tool
- Output: Appends ToolMessage objects to messages for each tool execution result
- Supports parallel tool execution by default

**tools_condition Function:**
- LangGraph's prebuilt router for conditional edges
- Checks if last message has `tool_calls`
- Routes to "tools" node if tool calls exist, otherwise to END

**Call LLM Node** (`/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/call_llm.py`):
```python
async def call_llm(state: ConversationState, config: RunnableConfig) -> dict:
    messages = state["messages"]
    tools = [multiply]

    # Get LLM provider from config and bind tools
    llm_provider = config["configurable"]["llm_provider"]
    llm_provider_with_tools = llm_provider.bind_tools(tools, parallel_tool_calls=False)

    # Generate response (returns AIMessage potentially with tool_calls)
    ai_message = await llm_provider_with_tools.generate(messages)

    return {"messages": [ai_message]}
```

### Message Flow Through Tool Calling

**Non-Tool Scenario:**
1. User input -> HumanMessage in state
2. call_llm node invokes LLM with tools bound
3. LLM returns AIMessage with text content (no tool_calls)
4. tools_condition routes to END
5. Graph terminates, message persisted by checkpointer

**Tool Calling Scenario:**
1. User input -> HumanMessage in state
2. call_llm node invokes LLM with tools bound
3. LLM returns AIMessage with `tool_calls` attribute
4. tools_condition routes to tools node
5. ToolNode:
   - Extracts tool_calls from AIMessage
   - Executes each tool function
   - Creates ToolMessage for each result with tool_call_id reference
   - Returns updated state with ToolMessages appended
6. Edge routes back to call_llm
7. call_llm invokes LLM again with full message history including ToolMessages
8. LLM processes tool results and generates final response
9. If no more tool_calls, tools_condition routes to END
10. Graph terminates, full conversation with tool messages persisted

---

## Current State Assessment

### What Works Well

1. **Provider Abstraction**: Excellent separation via ILLMProvider port. Application code never references provider implementations.

2. **Tool Binding Pattern**: Clean, immutable pattern in bind_tools() that avoids stateful mutations. Returns new provider instance.

3. **LangChain Integration**: Direct delegation to LangChain's bind_tools() leverages battle-tested tool calling implementations.

4. **Tool Execution**: ToolNode and tools_condition already integrated into graphs, enabling automatic tool execution loops.

5. **BaseMessage Types**: Using LangChain's native BaseMessage types (AIMessage with tool_calls) means tool data flows naturally through system.

6. **Streaming Support**: Both chat_graph and streaming_chat_graph have ToolNode integration, supporting tools in streaming mode.

### Current Limitations & Gaps

1. **Configuration Exposure**: Tools are currently hardcoded in nodes (`tools = [multiply]`). Need mechanism to pass tool configuration through the port.

2. **Tool Definition Pattern**: No standard way to register tools that respects the port abstraction. Tools are imported directly in graph nodes.

3. **Tool Result Handling**: While ToolNode creates ToolMessages automatically, there's no custom handling for tool results in the port layer.

4. **Provider-Specific Tool Constraints**:
   - Ollama tool support depends on underlying model (not all models support tools)
   - OpenAI, Anthropic, Gemini have mature tool-calling support
   - No detection or validation of provider capabilities

5. **Streaming Tool Handling**: Tools work in streaming graph, but tool execution doesn't stream (tools run synchronously). Only LLM response tokens stream.

6. **Error Handling**: ToolNode has default error handling (catches exceptions in tools), but no way to customize this per tool or log tool errors through the port.

7. **Tool Introspection**: ILLMProvider doesn't expose what tools are bound or whether provider supports tool calling.

---

## Impact Analysis

### Which Components Are Affected

**High Impact (Core Changes Required):**
1. **ILLMProvider Port** - May need new methods for tool introspection or custom handling
2. **All Provider Implementations** - May need tool capability detection
3. **Call LLM Node** - Currently hardcodes tools; needs parameterization
4. **Graph Creation** - Graphs currently hardcode tool lists in ToolNode

**Medium Impact (Configuration/Behavior Changes):**
1. **Settings** - May need configuration for tool definitions
2. **Provider Factory** - May need to initialize providers with tool metadata
3. **RunnableConfig** - May need to pass tool configuration alongside llm_provider

**Low Impact (No Changes Needed):**
1. **State (ConversationState)** - Already uses MessagesState; ToolMessages fit naturally
2. **ToolNode** - Prebuilt; works as-is with bound tools
3. **tools_condition** - Prebuilt; works as-is with AIMessage.tool_calls

### Data Flow Changes

**Current Flow:**
```
Graph Node -> llm_provider (from config) -> .bind_tools(hardcoded_tools) -> .generate(messages) -> AIMessage with tool_calls
                                                                           -> ToolNode processes automatically
                                                                           -> ToolMessages added to state
```

**Proposed Flow (to enable transparent tool calling):**
```
Graph Node -> llm_provider (from config) + tool_registry (from config)
           -> .bind_tools(dynamic_tools) -> .generate(messages) -> AIMessage with tool_calls
                                                               -> ToolNode processes automatically
                                                               -> ToolMessages added to state
```

---

## LLM Integration Recommendations

### Assumption & Clarification Needed

**Key Question**: How should tools be defined and registered in the application?

Current project structure has two patterns:
1. **LangGraph-native**: Tools defined as functions/callables in `langgraph/tools/` (e.g., multiply.py)
2. **Hardcoded references**: Tools imported directly into graph nodes

**Clarification Needed**: Should tool registration happen at:
- Application startup (configure once, inject into graphs)?
- Graph creation time (pass tool list to graph builder)?
- Graph invocation time (pass tool configuration via RunnableConfig)?
- Node execution time (fetch tools from a tool registry)?

**Recommendation**: Application startup registration with dependency injection into graph creation is cleanest pattern.

---

### Proposed Interfaces

**Option 1: Extend ILLMProvider with Tool Metadata (Minimal)**

Add two query methods to ILLMProvider to enable introspection:

```python
@abstractmethod
def supports_tool_calling(self) -> bool:
    """
    Check if the current provider supports tool calling.

    Returns:
        True if provider and model support tool calling, False otherwise
    """
    pass

@abstractmethod
def get_bound_tools(self) -> List[Callable]:
    """
    Get the list of tools currently bound to this provider.

    Returns:
        List of callable tools, empty list if no tools bound
    """
    pass
```

**Rationale**:
- Lightweight addition to port
- Enables clients to detect tool-calling capability
- Allows tools to be queried from bound providers
- Maintains abstraction; implementation details hidden

**Implementation**:
- Each provider tracks bound tools in instance variable
- Tool support depends on provider (always True for OpenAI/Anthropic/Gemini, model-dependent for Ollama)
- `bind_tools()` updates the bound tools list

---

**Option 2: Create Tool Registry Port (More Extensible)**

Define a new port for tool management:

```python
class IToolRegistry(ABC):
    """
    Port for registering and retrieving tools for LLM execution.

    Separates tool management from LLM providers, enabling flexible
    tool definition and discovery patterns.
    """

    @abstractmethod
    def register_tool(self, tool: Callable, metadata: Dict[str, Any] = None) -> None:
        """Register a tool for use by LLM providers."""
        pass

    @abstractmethod
    def get_tools(self, category: str = None) -> List[Callable]:
        """Get all registered tools, optionally filtered by category."""
        pass

    @abstractmethod
    def get_tool_by_name(self, name: str) -> Optional[Callable]:
        """Get a specific tool by its name."""
        pass
```

**Rationale**:
- Future-proof; allows complex tool management
- Separates tool concerns from LLM provider concerns
- Enables selective tool binding per graph/conversation
- Allows tool metadata (capabilities, rate limits, cost) to be attached

**Implementation Complexity**: Moderate - requires new adapter, but orthogonal to provider changes

---

### Proposed Implementations

**For bind_tools() - No Changes Needed**

Current implementation is sound. Key points:
- Creates new provider instance (immutable)
- Delegates to LangChain's bind_tools()
- Forwards kwargs for provider-specific options
- All providers follow same pattern

**For Tool Definition - Add Registry Adapter**

Create new adapter to replace hardcoded tool imports:

```python
# backend/app/adapters/outbound/tool_registry.py
class ToolRegistry(IToolRegistry):
    """In-memory tool registry implementation."""

    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._categories: Dict[str, List[str]] = {}

    def register_tool(self, tool: Callable, metadata: Dict[str, Any] = None) -> None:
        """Register a tool with optional metadata."""
        name = tool.__name__
        self._tools[name] = tool

        if metadata and "category" in metadata:
            category = metadata["category"]
            if category not in self._categories:
                self._categories[category] = []
            self._categories[category].append(name)

    def get_tools(self, category: str = None) -> List[Callable]:
        """Get tools, optionally filtered by category."""
        if category is None:
            return list(self._tools.values())

        tool_names = self._categories.get(category, [])
        return [self._tools[name] for name in tool_names if name in self._tools]
```

**For call_llm Node - Parameterize Tool Selection**

Modify call_llm node to accept tools via configuration:

```python
async def call_llm(state: ConversationState, config: RunnableConfig) -> dict:
    """Call the LLM provider to generate a response with optional tools."""
    messages = state["messages"]
    conversation_id = state["conversation_id"]

    logger.info(f"Calling LLM for conversation {conversation_id}")

    # Get LLM provider and tool registry from config
    llm_provider = config["configurable"].get("llm_provider")
    tool_registry = config["configurable"].get("tool_registry")

    # Bind tools if registry is available
    if tool_registry:
        tools = tool_registry.get_tools()
        if tools and llm_provider.supports_tool_calling():
            llm_provider_with_tools = llm_provider.bind_tools(
                tools,
                parallel_tool_calls=False
            )
        else:
            llm_provider_with_tools = llm_provider
    else:
        llm_provider_with_tools = llm_provider

    # Generate response
    ai_message = await llm_provider_with_tools.generate(messages)

    logger.info(f"LLM response generated for conversation {conversation_id}")

    return {"messages": [ai_message]}
```

---

### Configuration Changes

**New Environment Variables** (optional, for advanced setup):
```
# Tool registry configuration
ENABLE_TOOL_REGISTRY=true
TOOL_CATEGORIES=utilities,analysis,search
```

**RunnableConfig Enhancement** (at graph invocation):

Instead of:
```python
config = {"configurable": {"llm_provider": provider}}
```

Use:
```python
tool_registry = ToolRegistry()
tool_registry.register_tool(multiply, metadata={"category": "utilities"})

config = {
    "configurable": {
        "llm_provider": provider,
        "tool_registry": tool_registry
    }
}

graph.invoke(input_data, config=config)
```

**No Changes to Settings** (`settings.py`):
- LLM provider selection stays the same
- Tool configuration happens at runtime, not via environment

---

### Data Flow

**Complete Tool-Calling Flow with Transparency:**

```
┌─────────────────────────────────────────────────────────────────┐
│ WebSocket Handler / API Endpoint                                 │
│ • Receives user message                                          │
│ • Instantiates tool_registry with available tools              │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ Graph Invocation                                                 │
│ • Passes llm_provider and tool_registry via RunnableConfig      │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ process_user_input Node                                          │
│ • Validates messages exist in state                             │
│ • Returns empty dict (no state update)                          │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ call_llm Node                                                    │
│ • Gets llm_provider from config["configurable"]                 │
│ • Gets tool_registry from config["configurable"]                │
│ • Calls llm_provider.bind_tools(tool_registry.get_tools())      │
│   - Provider.bind_tools() delegates to LangChain's bind_tools() │
│   - LangChain converts tools to provider-specific schema        │
│   - Returns new provider with bound model                       │
│ • Calls llm_provider_with_tools.generate(messages)              │
│   - LangChain model makes API call with tool schema included    │
│   - Model returns AIMessage with tool_calls (if needed)         │
│ • Appends AIMessage to state via add_messages reducer           │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ↓
         ┌────────────────────────┐
         │ tools_condition        │
         │ Check: tool_calls in   │
         │ last AIMessage?        │
         └────────────┬───────────┘
                      │
        ┌─────────────┴─────────────┐
        │ YES                       │ NO
        ↓                           ↓
    ┌────────────┐          ┌──────────┐
    │ tools      │          │ END      │
    └────┬───────┘          └──────────┘
         │
         ↓
┌─────────────────────────────────────────────────────────────────┐
│ ToolNode                                                         │
│ • Receives state with AIMessage containing tool_calls           │
│ • For each tool_call:                                           │
│   - Look up tool by name                                        │
│   - Extract args from tool_call["args"]                         │
│   - Execute tool.invoke(args) or tool(**args)                   │
│   - Create ToolMessage with result and tool_call_id             │
│ • Append all ToolMessages to state via add_messages reducer     │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ↓
         ┌────────────────────────┐
         │ Edge: tools -> call_llm │
         └────────────┬───────────┘
                      │
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ call_llm Node (2nd Invocation)                                   │
│ • Full message history now includes:                            │
│   - Original HumanMessage                                       │
│   - AIMessage with tool_calls                                   │
│   - ToolMessage(s) with tool results                            │
│ • Calls llm_provider_with_tools.generate(full_messages)         │
│ • LLM processes tool results and generates final response       │
│ • Returns AIMessage with final text (typically no tool_calls)   │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ↓
         ┌────────────────────────┐
         │ tools_condition        │
         │ Check: tool_calls?     │
         │ (Typically: NO)        │
         └────────────┬───────────┘
                      │
                      ↓
         ┌────────────────────────┐
         │ END                    │
         │ Graph terminates       │
         └────────────┬───────────┘
                      │
                      ↓
┌─────────────────────────────────────────────────────────────────┐
│ Message Persistence (Automatic via Checkpointer)                │
│ • Checkpoint saved with full conversation including:            │
│   - HumanMessage                                                │
│   - AIMessage with tool_calls                                   │
│   - ToolMessage(s) with results                                 │
│   - Final AIMessage with response                               │
│ • Conversation metadata updated in App DB                       │
└─────────────────────────────────────────────────────────────────┘
```

**Key Observations:**
- Tool binding happens transparently in call_llm node
- ToolNode execution is automatic via conditional edges
- Message flow is standard LangChain/LangGraph pattern
- Full conversation history (including tool interactions) persists
- Application code doesn't directly call tools; LLM decides when to call them

---

## Implementation Guidance

### Step-by-Step Approach

**Phase 1: Add Tool Introspection to ILLMProvider (Low Risk)**

1. Add `supports_tool_calling()` method to ILLMProvider port
2. Implement in all four providers:
   - OpenAI: Always True
   - Anthropic: Always True
   - Gemini: Always True
   - Ollama: Return check for model capabilities (or always True for now)
3. Add `get_bound_tools()` method to track bound tools
4. Update `bind_tools()` implementations to store tools list
5. Write unit tests for tool introspection

**Phase 2: Create Tool Registry Adapter (Medium Risk)**

1. Create IToolRegistry port in `core/ports/`
2. Implement in `adapters/outbound/tool_registry.py`
3. Add tool registration at application startup
4. Write unit tests for tool registration and retrieval

**Phase 3: Parameterize Graph Tool Binding (Medium Risk)**

1. Update `call_llm` node to accept tool_registry from config
2. Update graph creators to handle optional tool_registry
3. Update WebSocket handler to pass tool_registry in RunnableConfig
4. Update API endpoints similarly if applicable
5. Write integration tests verifying tool execution flow

**Phase 4: Add Tool Execution Transparency (Low Risk)**

1. Update WebSocket handler to emit tool execution events
2. Add tool call and tool result events to streaming output
3. Frontend displays tool calls transparently to user
4. No backend code changes required; ToolNode already executes

**Phase 5: Testing & Documentation (Medium Risk)**

1. Write comprehensive unit tests for tool binding across all providers
2. Write integration tests for tool execution loop
3. Write tests for streaming with tool calls
4. Document tool registration patterns
5. Document tool-calling limitations per provider

### Minimal Viable Implementation

**If time is limited, implement only:**
1. Tool introspection methods on ILLMProvider (Phase 1)
2. Update call_llm to parameterize tools via RunnableConfig (Phase 3, simplified)
3. Comprehensive tests for tool-calling scenarios

This enables tool calling without creating new abstractions.

---

## Risks and Considerations

### Provider-Specific Constraints

**OpenAI (Mature Support):**
- Full support for tool calling in all recent models
- Supports parallel tool calls and explicit tool choice
- Risk: None identified

**Anthropic (Mature Support):**
- Full support for tool/function calling in Claude 3+
- Supports tool_choice parameter
- Risk: Tool definitions must follow Anthropic schema

**Gemini (Good Support):**
- Full support for function calling in recent models
- May have slight differences in schema conversion
- Risk: Older Gemini models may not support tools

**Ollama (Limited Support):**
- Tool support depends on underlying model
- Many local models have limited or no tool support
- Risk: Tool calling may fail silently on unsupported models
- Mitigation: Detect model capabilities at provider initialization

### Rate Limiting & Cost

**Tool Execution Impact:**
- Tool calling requires additional API call with full message history + tool schemas
- Tool schemas increase prompt token count
- Multiple tool calls in a loop increases cost
- Mitigation: Implement token counting and cost estimation

**Streaming Considerations:**
- Tool execution doesn't stream (tools run synchronously)
- Implies gap between LLM finishing tool call and tool executing
- User doesn't see real-time tool execution
- Mitigation: Document limitation; emit tool execution events async

### Backward Compatibility

**Breaking Changes:** None anticipated
- Existing code without tool registry continues to work
- bind_tools() behavior unchanged
- graph structure unchanged
- ToolNode already in place

**Deprecations:** None needed

**Migration Path:**
- Old: Hardcoded tools in graph nodes
- New: Tool registry injected via config
- Both patterns can coexist during transition

### Error Handling

**Current ToolNode Behavior:**
- Catches exceptions in tool execution
- Returns error message as ToolMessage content
- Continues graph execution
- Configurable via `handle_tool_errors` parameter

**Gaps:**
- No custom error handling per provider
- No error logging through LLMProvider port
- No way for tool to retry after failure

**Recommendation:**
- Wrap ToolNode to add logging/metrics collection
- Document error handling behavior
- Provide hooks for custom error handling if needed

### Testing Strategy

**Unit Test Requirements:**
1. Test bind_tools() on each provider
   - Verifies return type is ILLMProvider
   - Verifies tools are correctly bound
   - Verifies kwargs forwarded to LangChain
2. Test supports_tool_calling() for each provider
3. Test get_bound_tools() returns correct list
4. Test tool registry registration and retrieval

**Integration Test Requirements:**
1. Test full tool-calling workflow for each provider
   - User message -> Tool call decision -> Tool execution -> Response
2. Test multiple tool calls in sequence
3. Test tool with parameters and return values
4. Test tool error handling
5. Test streaming with tool calls
6. Test message persistence (tools included in checkpoint)

**End-to-End Test Requirements:**
1. Test via WebSocket: full conversation with tools
2. Test via REST API if applicable
3. Test UI display of tool calls and results
4. Test tool execution in real conversation context

**Mock/Fixture Strategy:**
- No mocks of actual tools (use real tool functions)
- Mock LLM responses with predetermined tool calls
- Mock external APIs called by tools (if applicable)
- Use test models (gpt-4-turbo-preview for OpenAI, etc.)

---

## Completion Criteria

### Functional Requirements
- [ ] All four LLM providers support tool calling via bind_tools()
- [ ] Tool calling works in both regular and streaming graphs
- [ ] Tools are executed automatically via ToolNode
- [ ] Tool results flow back to LLM correctly
- [ ] Tool calling is transparent to application code
- [ ] Tool capabilities detected per provider

### Testing Requirements
- [ ] Unit tests: 100% coverage for tool-calling code paths
- [ ] Integration tests: Full tool-calling workflow for each provider
- [ ] End-to-end tests: Tool calling in real WebSocket conversation
- [ ] Error handling: Tool execution errors handled gracefully
- [ ] Streaming: Tool calls don't break streaming

### Documentation Requirements
- [ ] Implementation guide for developers
- [ ] Tool registration patterns documented
- [ ] Provider-specific quirks documented
- [ ] Limitations (Ollama, rate limiting) documented
- [ ] Example tools provided
- [ ] Migration guide from hardcoded to registry pattern

---

## Summary of Key Files to Modify

1. **Core Port** (`llm_provider.py`): Add tool introspection methods
2. **All Providers** (4 files): Implement tool introspection, update bind_tools to track tools
3. **Tool Registry** (new): Create IToolRegistry port and adapter
4. **call_llm Node** (`nodes/call_llm.py`): Parameterize tool binding
5. **Graph Creators** (2 files): Update to handle optional tool registry
6. **WebSocket Handler**: Pass tool_registry in RunnableConfig
7. **Tests** (multiple): Add comprehensive tool-calling tests

**Estimated Complexity**: Medium (5-6 days for experienced developer)

**Risk Level**: Low (builds on existing abstraction, no core changes)

