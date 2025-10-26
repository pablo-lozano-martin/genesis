# Backend Hexagonal Architecture Analysis: Tool-Calling Support

## Request Summary

Add tool-calling capability to Genesis backend using LangGraph's ToolNode and transparent UI integration. This feature enables AI agents to call predefined tools (multiply, API endpoints, database queries, etc.) within conversation flows, with results automatically integrated back into the LLM context. The architecture must maintain clean separation between tool definitions, LLM coordination, and domain boundaries.

## Relevant Files & Modules

### Core Domain Files
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/conversation.py` - Conversation entity, database-agnostic, no tool concerns
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/user.py` - User entity, no tool concerns

### Ports (Interfaces)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/llm_provider.py` - ILLMProvider port defining `bind_tools()` interface
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/conversation_repository.py` - IConversationRepository port (authorization layer)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/user_repository.py` - IUserRepository port
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/auth_service.py` - IAuthService port

### Outbound Adapters (LLM Providers)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/openai_provider.py` - OpenAI adapter, implements `bind_tools()` by delegating to LangChain
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/anthropic_provider.py` - Anthropic adapter, implements `bind_tools()` by delegating to LangChain
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/gemini_provider.py` - Gemini adapter
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/ollama_provider.py` - Ollama adapter
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/provider_factory.py` - Factory for creating provider instances

### LangGraph Layer (Infrastructure for Graph Orchestration)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/state.py` - ConversationState extending MessagesState
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/multiply.py` - Example tool (simple arithmetic)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/tools/__init__.py` - Tool module exports
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/call_llm.py` - LLM invocation node, currently calls `bind_tools()` and hardcodes `[multiply]`
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/nodes/process_input.py` - Input validation node
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/chat_graph.py` - Graph definition with ToolNode, hardcodes `[multiply]`
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/langgraph/graphs/streaming_chat_graph.py` - Streaming graph variant with ToolNode, hardcodes `[multiply]`

### Inbound Adapters (API/WebSocket)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py` - WebSocket handler that invokes graph and streams responses
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_schemas.py` - Message types (ClientMessage, ServerTokenMessage, etc.)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_router.py` - WebSocket route setup
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/conversation_router.py` - REST endpoints for conversations
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/message_router.py` - REST endpoints for messages

## Current Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│         Inbound Adapters (API/WebSocket Layer)              │
│   websocket_handler.py - Receives messages, calls graph     │
│   conversation_router.py - REST endpoints                   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ RunnableConfig(thread_id, llm_provider)
                         │
┌────────────────────────▼────────────────────────────────────┐
│       LangGraph Orchestration Layer (Infrastructure)         │
│                                                              │
│  chat_graph.py / streaming_chat_graph.py                    │
│    ├─ process_input node                                    │
│    ├─ call_llm node (with bind_tools)                       │
│    └─ ToolNode(tools) - Executes tool_calls                │
│                                                              │
│  ConversationState (MessagesState + conversation_id)        │
│  tools/ directory - Tool implementations                    │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
    ┌─────────┐  ┌──────────────┐  ┌─────────┐
    │   ILLMProvider (Port)      │
    │  bind_tools() interface    │
    └─────┬───────────┬──────────┘
          │           │
    ┌─────▼──┐  ┌─────▼──────────┐
    │OpenAI  │  │ Anthropic      │  ... (other providers)
    │Provider│  │ Provider       │
    └────────┘  └────────────────┘
```

### Domain Core (Pure Business Logic)
- **Domain Models**: User, Conversation entities
- **Ports**: ILLMProvider, IConversationRepository, IUserRepository, IAuthService
  - Note: ILLMProvider contains `bind_tools()` method that takes a list of Callable tools
- **Use Cases**: RegisterUser, AuthenticateUser, CreateConversation
  - No use case directly handles tools or tool calling
  - No use case knows about LangGraph graph structure

### LangGraph Layer (Graph Orchestration - Infrastructure, not Domain)
- **ConversationState**: Extends LangGraph MessagesState, adds conversation_id, user_id
- **Nodes**: process_input, call_llm, (implicit ToolNode via prebuilt)
- **Tools**: Stored in `/backend/app/langgraph/tools/` directory
  - Currently: multiply.py (simple example)
  - Future: API adapters, database queries, etc.
- **Graphs**: StateGraph definitions with ToolNode integration
  - Currently hardcodes `[multiply]` in both chat_graph.py and streaming_chat_graph.py
  - ToolNode executes any tool_calls returned by LLM

### Adapters
- **LLM Providers** (Outbound): All implement ILLMProvider
  - All have `bind_tools()` method that wraps LangChain's `.bind_tools()`
  - Returns new provider instance with bound model
- **WebSocket Handler** (Inbound): Receives messages, calls graph, streams responses

## Current State: What Already Works

1. **Tool Binding is Already Abstracted**: The `ILLMProvider.bind_tools()` method already exists as a port interface
2. **Tool Execution via ToolNode**: Both graphs (chat_graph.py and streaming_chat_graph.py) use `ToolNode(tools)` from LangGraph prebuilt
3. **Provider Abstraction**: Tool binding is delegated to LangChain providers via adapter pattern
4. **Conditional Routing**: `tools_condition` from prebuilt routes to ToolNode based on tool_calls in AIMessage

## Current Architectural Issues & Violations

### Issue 1: Hardcoded Tool List in Graph Definitions
**Problem**: Tools are hardcoded in two places:
- `chat_graph.py`: `tools = [multiply]` hardcoded in create_chat_graph()
- `streaming_chat_graph.py`: `tools = [multiply]` hardcoded in create_streaming_chat_graph()
- `call_llm.py`: `tools = [multiply]` hardcoded in call_llm() node function

**Why it's a problem**:
- New tools require modifying graph definitions
- Graphs and tools become tightly coupled
- Can't dynamically register tools
- Violates single responsibility principle
- Makes testing difficult

**Architectural violation**: This creates a dependency from the LangGraph layer (infrastructure) back to tool definitions. While not a complete violation, it prevents flexible tool composition.

### Issue 2: Tools Live in LangGraph Layer, Not Domain
**Current location**: `/backend/app/langgraph/tools/`
**Problem**: This location tightly couples tools to LangGraph's execution model

**Why it's actually OK** (upon deeper analysis):
- Tools are fundamentally infrastructure/execution concerns
- They're not domain logic; they're adapters to external systems
- Domain doesn't need to know about tools
- Having them in langgraph/ makes sense as they're part of the graph orchestration layer

**However, consider this**: As tools grow more complex (API calls, database queries), they should follow adapter pattern with ports.

### Issue 3: Bind Tools in Call_LLM Node
**Current pattern** in `call_llm.py`:
```python
llm_provider_with_tools = llm_provider.bind_tools(tools, parallel_tool_calls=False)
ai_message = await llm_provider_with_tools.generate(messages)
```

**Problem**: Tools are bound per message, not per graph lifecycle. This is inefficient and conceptually unclear.

**Better pattern**: Bind tools once when creating the provider in RunnableConfig, not in the node.

## Impact Analysis

### Components Affected by Adding Tool Support

1. **LangGraph Layer** (Moderate Impact)
   - Graph creation needs to accept tools as parameter
   - Both chat_graph and streaming_chat_graph need updating
   - call_llm node needs refactoring

2. **Tool Directory** (High Impact)
   - New tools added to `/backend/app/langgraph/tools/`
   - Each tool is a Python callable with proper type hints
   - Tools need proper documentation

3. **LLM Providers** (Minimal Impact)
   - bind_tools() already exists
   - Only the invocation pattern in call_llm node needs updating
   - Providers themselves unchanged

4. **WebSocket Handler** (Minor Impact)
   - May need to pass tools via RunnableConfig if we refactor
   - Current astream_events() usage continues to work

5. **Domain & Use Cases** (Zero Impact)
   - Domain models unaware of tools
   - No use case changes needed
   - Pure infrastructure addition

## Hexagonal Architecture Assessment

### Dependency Flow: Good News
```
Domain ← Ports ← LLMProviders (Adapters)
                 ├─ bind_tools() is already in port
                 └─ Tool selection is infrastructure concern

                ← LangGraph Layer (Orchestration)
                 ├─ Graph structure (infrastructure)
                 └─ Tool directory (infrastructure)

                ← WebSocket Handler (Inbound Adapter)
                 ├─ Graph invocation
                 └─ Message streaming
```

**Direction**: Dependencies point inward toward domain (CORRECT)
- Domain doesn't know about LangGraph
- Domain doesn't know about specific tools
- Domain only knows about ILLMProvider port
- Tools are infrastructure, not domain concern

### Port Abstraction: Assessment
The `ILLMProvider.bind_tools()` interface is well-designed:
- Takes list of Callable
- Returns new provider instance with tools bound
- Delegates to LangChain's polymorphic implementation
- Provider implementations follow adapter pattern correctly

### Domain Isolation: Perfect
The domain core (User, Conversation, use cases) is completely isolated from:
- Tool definitions
- Tool execution
- LangGraph graph structure
- Tool calling mechanics

This is exactly what hexagonal architecture demands.

## Architectural Recommendations

### Recommendation 1: Create Tool Registry Port (Optional, for Future Extensibility)

**Current State**: Tools hardcoded in graphs

**Proposed Port**: Create `IToolRegistry` interface
```python
# backend/app/core/ports/tool_registry.py
class IToolRegistry(ABC):
    @abstractmethod
    def get_tools(self) -> List[Callable]:
        """Get all available tools for current conversation"""
        pass

    @abstractmethod
    def get_tool_by_name(self, name: str) -> Optional[Callable]:
        """Get specific tool by name"""
        pass
```

**Proposed Adapter**: Implement in LangGraph layer
```python
# backend/app/langgraph/adapters/langgraph_tool_registry.py
class LangGraphToolRegistry(IToolRegistry):
    def __init__(self, tools_module_path: str):
        """Load tools from directory or module"""
        self.tools = self._load_tools(tools_module_path)
```

**Benefits**:
- Graphs don't need to know about specific tools
- Easy to add/remove tools via configuration
- Testing is simpler (mock registry)
- Could support runtime tool registration

**Trade-off**: Adds indirection. Simple multiply tool doesn't justify this. Wait until tool complexity grows.

**Recommendation**: DEFER - Only implement when you have 3+ complex tools

### Recommendation 2: Refactor Tool Binding Location (IMMEDIATE)

**Current Problem**: Tools bound in call_llm node per message

**Solution**: Move tool binding to provider initialization in RunnableConfig

```python
# In websocket_handler.py
config = RunnableConfig(
    configurable={
        "thread_id": conversation.id,
        "llm_provider": llm_provider,  # Unbounded provider
        "user_id": user.id
    }
)
```

Then pass tools differently:
```python
config = RunnableConfig(
    configurable={
        "thread_id": conversation.id,
        "llm_provider": llm_provider_with_tools,  # BOUND provider
        "user_id": user.id,
        "tools": tools  # Also pass tools to ToolNode
    }
)
```

**Updated call_llm node**:
```python
async def call_llm(state: ConversationState, config: RunnableConfig) -> dict:
    messages = state["messages"]
    llm_provider = config["configurable"]["llm_provider"]  # Already has tools bound
    ai_message = await llm_provider.generate(messages)  # No binding here
    return {"messages": [ai_message]}
```

**Benefits**:
- Tool binding happens once at provider creation
- call_llm node is simpler, focused on LLM invocation
- Clearer data flow: "provider comes with tools"
- Easier to understand execution model

### Recommendation 3: Structure Tool Directory for Extensibility (IMMEDIATE)

**Current State**:
```
/backend/app/langgraph/tools/
├── __init__.py
└── multiply.py
```

**Proposed Structure**:
```
/backend/app/langgraph/tools/
├── __init__.py           # Exports all tools
├── multiply.py           # Simple math tool
├── basic/
│   ├── __init__.py
│   └── calculator.py     # Math operations
├── api/
│   ├── __init__.py
│   └── weather_api.py    # External API calls
└── database/
    ├── __init__.py
    └── query_tool.py     # Database operations
```

**Benefits**:
- Clear categorization as tool complexity grows
- Makes it obvious where to add new tools
- Easier to test tool modules independently
- Follows Django/Flask patterns developers know

### Recommendation 4: Create Tool Base Class or Protocol (FUTURE)

**When**: When you have 2+ complex tools with shared concerns

**Pattern**: Define common tool interface
```python
# backend/app/langgraph/tools/base_tool.py
from typing import Protocol

class ToolInterface(Protocol):
    """Protocol defining tool contract"""

    def __call__(self, *args, **kwargs) -> Any:
        """Execute the tool"""
        ...

    def __doc__(self) -> str:
        """Tool description for LLM"""
        ...
```

**Benefits**:
- Consistent tool signature
- Type safety
- Self-documenting
- LangChain can extract docstring for tool definition

### Recommendation 5: Tool Configuration via Environment (LATER)

**Pattern**: Make tool list configurable
```python
# backend/app/infrastructure/config/settings.py
class Settings:
    enabled_tools: List[str] = Field(
        default=["multiply"],
        description="List of enabled tool names"
    )
    tool_max_iterations: int = 10
    tool_timeout_seconds: int = 30
```

**Benefits**:
- Different tools in dev/prod
- Feature flags for tool availability
- Rate limiting configuration
- Timeout configuration

## Implementation Guidance

### Phase 1: Quick Win (This Sprint)

1. **Move tool binding to provider creation**
   - In websocket_handler.py, bind tools before passing to graph
   - Remove bind_tools call from call_llm node
   - Remove duplicate tools list from call_llm.py
   - Keep tools list in graph definitions for now

2. **Document current architecture**
   - Add comments explaining why tools are in langgraph/
   - Document how ToolNode works with MessagesState
   - Explain tool_calls in AIMessage structure

3. **Test tool execution flow**
   - Verify multiply tool works end-to-end
   - Test tool_calls are properly generated
   - Test ToolNode execution integration

### Phase 2: Organize Tools (Next Sprint)

1. **Create tool subdirectories**
   - Move multiply to `tools/basic/`
   - Create placeholder for `tools/api/` and `tools/database/`
   - Update __init__.py exports

2. **Add tool registry configuration**
   - Not as a port yet, just config-driven
   - Read tool list from environment or config
   - Dynamically load tools in graph creation

3. **Add tool documentation**
   - Each tool needs comprehensive docstring
   - Document parameters and return types
   - Document side effects and limitations

### Phase 3: Advanced Extensibility (Later)

1. **Implement IToolRegistry port**
   - Only if you have 3+ complex tools
   - Create adapter for dynamic loading
   - Update graphs to use registry

2. **Add tool permissions/access control**
   - Some tools might be user-specific
   - Authorization checks in ToolNode
   - Audit logging for tool execution

3. **Add tool composition patterns**
   - Sequential tool execution
   - Conditional tool availability
   - Tool dependency management

## Risks and Considerations

### Risk 1: Tool Execution Errors Crash Graph

**Concern**: If a tool raises exception, does entire graph fail?

**Current Reality**: LangGraph's ToolNode handles exceptions, returns as ToolMessage

**Mitigation**:
- Wrap tools in try/catch during ToolNode execution
- Return structured error messages to LLM
- LLM can then clarify with user
- Log tool errors separately for debugging

**Acceptance**: LangGraph handles this well out of the box

### Risk 2: Security: Users Executing Arbitrary Tools

**Concern**: Can users abuse tool calling to access unauthorized data?

**Mitigation** (MUST implement):
- Authorization check in WebSocket handler before graph invocation
- Pass authorization context to graph via RunnableConfig
- In tool execution, check user permissions for each tool call
- Database query tools must respect conversation ownership

**Implementation**:
```python
# In websocket_handler.py
config = RunnableConfig(
    configurable={
        "user_id": user.id,  # Already done
        "authorized_tools": await get_user_authorized_tools(user.id)
    }
)
```

**Timeframe**: REQUIRED for production

### Risk 3: Tool Latency Impacts Streaming

**Concern**: If tool execution is slow, does streaming stop?

**Current Reality**: astream_events includes ToolNode execution in event stream

**Mitigation**:
- Measure tool execution time in production
- Consider async tool execution where possible
- Add timeout configuration
- Consider tool queue/worker pattern for slow tools

**Acceptance**: Acceptable for Phase 1. Monitor in production.

### Risk 4: Tool Side Effects (Database Modifications)

**Concern**: Tools might modify database. How do we handle rollback?

**Current Model**: LangGraph checkpoints don't rollback tool side effects

**Mitigation**:
- Design tools as read-only where possible
- For write operations, implement explicit confirmation flow
- Tool descriptions should be clear about side effects
- Consider separating "analysis" tools from "action" tools

**Guidance**: Start with read-only tools. Document clearly.

### Risk 5: Hardcoded Tools Become Maintenance Burden

**Concern**: As tools grow, hardcoding them causes scalability issues

**Current State**: Multiply is simple. Will grow.

**Mitigation**:
- Follow Phase 2 recommendation for tool organization
- Don't wait for perfect design before adding second tool
- Use environment configuration early
- Plan for Phase 3 registry when 3+ tools exist

### Architectural Debt: Tool Knowledge in Graphs

**Issue**: Graph creation functions "know" about tools

**Why it matters**: Every graph modification requires code change, not config change

**Resolution**: Phase 2 addresses this with config-driven tool loading

## Testing Strategy

### Unit Tests: Tool Functions

```python
# tests/unit/langgraph/tools/test_multiply.py
def test_multiply_basic():
    assert multiply(3, 4) == 12

def test_multiply_zero():
    assert multiply(0, 5) == 0

def test_multiply_negative():
    assert multiply(-2, 3) == -6
```

### Unit Tests: Graph Nodes

```python
# tests/unit/langgraph/nodes/test_call_llm.py
@pytest.mark.asyncio
async def test_call_llm_with_tools():
    state = ConversationState(
        messages=[HumanMessage(content="What is 3 times 4?")],
        conversation_id="test-conv",
        user_id="test-user"
    )
    config = RunnableConfig(
        configurable={
            "llm_provider": MockLLMProvider(),  # Mock that returns tool_calls
        }
    )
    result = await call_llm(state, config)
    assert "messages" in result
```

### Integration Tests: Graph Execution with ToolNode

```python
# tests/integration/langgraph/test_graph_with_tools.py
@pytest.mark.asyncio
async def test_chat_graph_executes_tools():
    graph = create_chat_graph(mock_checkpointer)
    config = RunnableConfig(
        configurable={
            "thread_id": "test-thread",
            "llm_provider": OpenAIProvider(),  # Real provider
        }
    )

    input_data = {
        "messages": [HumanMessage(content="What is 3 times 4?")],
        "conversation_id": "test-conv",
        "user_id": "test-user"
    }

    result = await graph.ainvoke(input_data, config)

    # Verify tool was executed and result returned
    assert any(isinstance(msg, ToolMessage) for msg in result["messages"])
```

### End-to-End Tests: WebSocket with Tool Calling

```python
# tests/e2e/test_tool_calling_e2e.py
@pytest.mark.asyncio
async def test_websocket_tool_calling():
    # Connect WebSocket
    # Send message requesting tool usage
    # Verify ToolMessage appears in conversation
    # Verify final response includes tool result
```

### Test Coverage Checklist

- [ ] Individual tool functions return correct values
- [ ] Tool type hints are respected
- [ ] Call_llm node properly invokes tools
- [ ] ToolNode executes tools correctly
- [ ] Tool errors are handled gracefully
- [ ] Tool results are converted to ToolMessage properly
- [ ] Graph conditional edges route to ToolNode when needed
- [ ] Graph completes successfully after tool execution
- [ ] WebSocket streaming includes tool execution events
- [ ] Tool binding in provider works correctly
- [ ] Multiple tools can be executed in sequence
- [ ] User authorization checked for tool access

## Summary: Key Architectural Considerations

### What's Right About Current Architecture

1. Domain is completely isolated from tools
2. Tool binding is abstracted via ILLMProvider port
3. LangGraph layer is separate infrastructure layer
4. ToolNode handles execution details
5. Provider adapters correctly implement interface

### What Needs Improvement

1. Tools are hardcoded in graph definitions (Phase 2)
2. Tool binding happens in node instead of provider creation (Phase 1)
3. Tool directory structure will need organization as it grows (Phase 2)
4. Missing authorization checks for tool access (Phase 1)
5. No tool registry abstraction (Phase 3 - defer)

### Critical Architectural Constraints

- **Don't violate domain isolation**: Tools must stay in infrastructure layer
- **Don't couple graphs to specific tools**: Make tool list configurable
- **Don't expose tool details to domain**: Domain only knows about ILLMProvider
- **Don't skip authorization**: Tool execution must check user permissions
- **Don't treat tools as domain logic**: They're adapters to external systems

### Recommended Action Plan

1. **Immediate** (Phase 1): Move tool binding to provider initialization, add authorization checks
2. **Near-term** (Phase 2): Organize tool directory, add configuration-driven tool loading
3. **Future** (Phase 3): Implement IToolRegistry only when justifiable by tool complexity

This approach maintains hexagonal architecture principles while allowing tool functionality to grow naturally without architectural refactoring.
