# Implementation Plan: Migrate Onboarding Agent to create_react_agent

**Issue**: #18 - Migrate onboarding agent to langgraph.prebuilt.create_react_agent
**Date**: 2025-10-30
**Author**: Analysis based on 5 comprehensive agent reports

---

## Executive Summary

This plan details the migration of the onboarding agent from a hand-built ReAct pattern (using StateGraph with custom nodes) to LangGraph's prebuilt `create_react_agent` function. The migration will:

- **Simplify** the codebase by removing 3 custom nodes (process_input, inject_system_prompt, call_llm)
- **Reduce** maintenance burden by using LangGraph's proven ReAct implementation
- **Preserve** all existing functionality including WebSocket streaming, tool execution, and state persistence
- **Maintain** backward compatibility with the frontend WebSocket API

**Key Challenge**: The current implementation has a dedicated `inject_system_prompt` node that ensures the LLM acts as a proactive onboarding agent. `create_react_agent` may not expose this injection point, requiring careful handling.

---

## Analysis Summary

Based on comprehensive analysis from 5 specialized agents, here are the key findings:

### 1. Backend Hexagonal Architecture (820 lines)
- ✅ Current hexagonal architecture preserved - no domain model changes needed
- ✅ ConversationState compatible with create_react_agent (extends MessagesState)
- ✅ Tool implementations unchanged (read_data, write_data, export_data, rag_search)
- ⚠️ **System prompt injection** is the primary migration challenge
- ⚠️ Tool binding shifts from runtime (RunnableConfig) to creation time

### 2. LLM Integration (1,165 lines)
- ⚠️ **ILLMProvider interface needs `get_model()` method** to expose LangChain model
- ✅ Provider abstraction maintained at app level (config-driven selection)
- ⚠️ Tools bound at graph creation instead of per-request
- ✅ Simplified WebSocket handler (removes llm_provider and tools from config)

### 3. Data Flow (1,201 lines)
- ✅ Complete employee data journey unchanged (collection → validation → export)
- ✅ Checkpointing flow identical (AsyncMongoDBSaver works unchanged)
- ✅ Multi-turn persistence preserved
- ⚠️ **System prompt injection mechanism** must be reimplemented
- ✅ Tool execution flow compatible (sequential tool calls with parallel_tool_calls=False)

### 4. Testing Coverage (642 lines)
- ✅ **30+ unit tests** for tools (write_data, read_data, export_data)
- ✅ **5 integration tests** for graph workflows
- ❌ **WebSocket endpoint /ws/onboarding completely untested** (CRITICAL GAP)
- ❌ **test_onboarding_persistence.py tests wrong graph** (tests streaming_chat_graph)
- ⚠️ Need 15-20 new tests for WebSocket integration and E2E flows

### 5. API Contract (868 lines)
- ✅ **WebSocket message schemas must NOT change** (frontend contract)
- ✅ ConversationState schema compatible
- ✅ Tool interfaces unchanged
- ⚠️ Event streaming (astream_events) must maintain same event types
- ⚠️ Tool binding in call_llm.py may need adjustment

---

## Pre-Migration Checklist

Before starting implementation, verify these prerequisites:

### ☐ Research Phase
1. **Fetch LangGraph documentation** for `create_react_agent`
   - Signature: What parameters does it accept?
   - State schema requirements: Does it work with custom state extending MessagesState?
   - System prompt support: Does it have a `prompt` or `system_prompt` parameter?
   - Tool binding: How are tools passed and bound?
   - Checkpointer: Compatible with AsyncMongoDBSaver?

2. **Review offboarding graph** (if exists)
   - Check if already uses create_react_agent for reference
   - Understand any patterns to reuse

3. **Context7 Documentation**
   - Use `mcp__context7__resolve-library-id` with library name "langgraph"
   - Use `mcp__context7__get-library-docs` to fetch current LangGraph docs

### ☐ Testing Infrastructure
1. **Add missing WebSocket tests** (before migration)
   - Create `/backend/tests/integration/test_onboarding_websocket.py`
   - Test /ws/onboarding endpoint authentication, streaming, tool events
   - Establish baseline behavior

2. **Fix test_onboarding_persistence.py** (tests wrong graph)
   - Change from `create_streaming_chat_graph` to `create_onboarding_graph`
   - Verify onboarding-specific field persistence

3. **Add node-level tests** (before migration)
   - Create tests for `process_user_input` node
   - Create tests for `call_llm` node

---

## Implementation Phases

## PHASE 1: Preparation (Research & Test Infrastructure)

**Goal**: Establish clear understanding of create_react_agent API and baseline test coverage

**Duration**: 2-3 hours

### Step 1.1: Research create_react_agent API

```bash
# Use Context7 to fetch LangGraph documentation
# In the implementation phase, call:
# mcp__context7__resolve-library-id with "langgraph"
# mcp__context7__get-library-docs with resolved ID
```

**Document these answers**:
1. Does create_react_agent accept a `prompt` or `system_prompt` parameter?
2. What is the exact function signature?
3. Does it work with custom state schemas (ConversationState)?
4. How are tools passed? As a list parameter?
5. Does it support AsyncMongoDBSaver checkpointer?
6. What events does it emit via astream_events()?

**Deliverable**: Create `/doc/features/Migrate onboarding agent to langgraph.prebuilt.create_react_agent/create_react_agent_api.md` with findings.

### Step 1.2: Fix Existing Test Bugs

**File**: `/backend/tests/integration/test_onboarding_persistence.py`

**Issue**: Tests `create_streaming_chat_graph` instead of `create_onboarding_graph`

**Changes**:
```python
# OLD (line ~15):
graph = create_streaming_chat_graph(checkpointer, tools)

# NEW:
from app.langgraph.tools import read_data, write_data, rag_search, export_data
onboarding_tools = [read_data, write_data, rag_search, export_data]
graph = create_onboarding_graph(checkpointer, onboarding_tools)
```

**Verify**:
- All tests pass with correct graph
- State fields (employee_name, employee_id, starter_kit) persist correctly

### Step 1.3: Add Node-Level Unit Tests

**Create**: `/backend/tests/unit/test_process_input_node.py`

```python
# Test cases:
- test_process_user_input_validates_messages_exist()
- test_process_user_input_with_valid_messages()
- test_process_user_input_logs_validation()
```

**Create**: `/backend/tests/unit/test_call_llm_node.py`

```python
# Test cases:
- test_call_llm_binds_tools_from_config()
- test_call_llm_uses_default_tools_if_no_config()
- test_call_llm_invokes_llm_provider()
- test_call_llm_returns_ai_message()
- test_call_llm_handles_llm_errors()
```

**Verify**: Run `pytest backend/tests/unit/test_*_node.py -v` and confirm all pass.

### Step 1.4: Add WebSocket Integration Tests

**Create**: `/backend/tests/integration/test_onboarding_websocket.py`

```python
# Test cases (minimum 8 tests):
- test_websocket_onboarding_requires_authentication()
- test_websocket_onboarding_initializes_conversation()
- test_websocket_onboarding_streams_llm_tokens()
- test_websocket_onboarding_handles_tool_calls()
- test_websocket_onboarding_handles_validation_errors()
- test_websocket_onboarding_persists_state()
- test_websocket_onboarding_handles_disconnection()
- test_websocket_onboarding_system_prompt_present()
```

**Verify**: All tests pass with current implementation. This establishes baseline behavior.

---

## PHASE 2: Core Migration (Graph Refactoring)

**Goal**: Replace hand-built graph with create_react_agent while preserving all functionality

**Duration**: 3-4 hours

### Step 2.1: Add get_model() to ILLMProvider Interface

**File**: `/backend/app/core/ports/llm_provider.py`

**Add method to interface**:
```python
from langchain_core.language_models import LanguageModel

class ILLMProvider(ABC):
    # ... existing methods ...

    @abstractmethod
    def get_model(self) -> LanguageModel:
        """
        Get the underlying LangChain ChatModel instance.

        Used by LangGraph prebuilt agents that require native LangChain models.

        Returns:
            Underlying ChatModel (ChatOpenAI, ChatAnthropic, etc.)
        """
        pass
```

**Implement in all providers**:

**File**: `/backend/app/adapters/outbound/llm_providers/openai_provider.py`
```python
def get_model(self) -> LanguageModel:
    """Return the underlying ChatOpenAI model."""
    return self.model
```

**Repeat for**:
- `/backend/app/adapters/outbound/llm_providers/anthropic_provider.py`
- `/backend/app/adapters/outbound/llm_providers/gemini_provider.py`
- `/backend/app/adapters/outbound/llm_providers/ollama_provider.py`

**Verify**: All providers implement get_model() and return valid LangChain model.

### Step 2.2: Create New Prebuilt Graph Factory

**File**: `/backend/app/langgraph/graphs/onboarding_graph.py`

**Replace entire `create_onboarding_graph()` function**:

```python
# ABOUTME: Onboarding agent graph factory using LangGraph's prebuilt create_react_agent
# ABOUTME: Replaced custom ReAct implementation with prebuilt for cleaner, maintainable code

from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver
from app.langgraph.prompts.onboarding_prompts import ONBOARDING_SYSTEM_PROMPT
from app.langgraph.state import ConversationState
from app.core.ports.llm_provider import ILLMProvider
from app.infrastructure.config.logging_config import get_logger
from typing import List, Callable, Optional

logger = get_logger(__name__)


def create_onboarding_graph(
    checkpointer: AsyncMongoDBSaver,
    tools: Optional[List[Callable]] = None,
    llm_provider: Optional[ILLMProvider] = None
):
    """
    Create onboarding agent graph using LangGraph's prebuilt create_react_agent.

    Advantages over hand-built approach:
    - Simpler implementation: no custom nodes for process_input, inject_system_prompt, call_llm
    - Automatically handles ReAct loop (reason → act → repeat)
    - System prompt injection built-in
    - Streaming support maintained via astream_events()

    Args:
        checkpointer: AsyncMongoDBSaver for state persistence
        tools: Optional list of tools (defaults to onboarding tools)
        llm_provider: ILLMProvider instance (defaults to factory-created provider)

    Returns:
        Compiled LangGraph agent ready for invocation
    """
    # Import default tools if not provided
    if tools is None:
        from app.langgraph.tools import read_data, write_data, rag_search, export_data
        tools = [read_data, write_data, rag_search, export_data]

    # Get LLM provider if not provided
    if llm_provider is None:
        from app.adapters.outbound.llm_providers.provider_factory import get_llm_provider
        llm_provider = get_llm_provider()

    # Get underlying LangChain model from provider abstraction
    model = llm_provider.get_model()

    # Create prebuilt agent with built-in ReAct loop
    # NOTE: Verify system_prompt parameter name in LangGraph docs
    agent = create_react_agent(
        model=model,
        tools=tools,
        state_schema=ConversationState,  # Verify if this parameter exists
        prompt=ONBOARDING_SYSTEM_PROMPT,  # Or system_prompt= depending on API
        checkpointer=checkpointer
    )

    # Store tools as metadata for WebSocket handler access
    # (Handler uses this to determine tool source: local vs MCP)
    agent._tools = tools

    logger.info(
        f"Onboarding graph created with create_react_agent "
        f"(tools: {[t.__name__ for t in tools]})"
    )

    return agent
```

**CRITICAL DECISION POINT**:
Based on Step 1.1 research, adjust the above code for:
1. Correct parameter name for system prompt (`prompt` vs `system_prompt`)
2. Whether `state_schema` parameter exists or if state is inferred
3. Whether `checkpointer` is passed to factory or to compile()

**If system prompt parameter doesn't exist**, use this alternative:

```python
def create_onboarding_graph(checkpointer, tools=None, llm_provider=None):
    # ... same setup as above ...

    # Create agent without system prompt
    agent_base = create_react_agent(
        model=model,
        tools=tools,
        checkpointer=checkpointer
    )

    # Wrap with custom system prompt injection node
    from langgraph.graph import StateGraph

    graph_builder = StateGraph(ConversationState)

    # Add system prompt injection node
    def inject_system_prompt(state: ConversationState) -> dict:
        """Prepend system message if not present."""
        messages = state.get("messages", [])
        if not messages or not isinstance(messages[0], SystemMessage):
            return {"messages": [SystemMessage(content=ONBOARDING_SYSTEM_PROMPT)]}
        return {}

    graph_builder.add_node("inject_system_prompt", inject_system_prompt)
    graph_builder.add_node("agent", agent_base)

    graph_builder.set_entry_point("inject_system_prompt")
    graph_builder.add_edge("inject_system_prompt", "agent")
    graph_builder.add_edge("agent", END)

    compiled = graph_builder.compile(checkpointer=checkpointer)
    compiled._tools = tools

    return compiled
```

**Choose the appropriate approach based on Step 1.1 research.**

### Step 2.3: Update Application Startup

**File**: `/backend/app/main.py`

**Locate the graph initialization** (around lines 112-117):

**OLD**:
```python
onboarding_tools = [read_data, write_data, rag_search, export_data]
app.state.onboarding_graph = create_onboarding_graph(checkpointer, onboarding_tools)
```

**NEW**:
```python
# Get LLM provider for graph initialization
from app.adapters.outbound.llm_providers.provider_factory import get_llm_provider
llm_provider = get_llm_provider()

# Create onboarding graph with prebuilt agent
onboarding_tools = [read_data, write_data, rag_search, export_data]
app.state.onboarding_graph = create_onboarding_graph(
    checkpointer,
    onboarding_tools,
    llm_provider
)
```

**Verify**: Application starts without errors and graph compiles successfully.

### Step 2.4: Update WebSocket Handler Configuration

**File**: `/backend/app/adapters/inbound/websocket_handler.py`

**Locate RunnableConfig creation** (around lines 125-133):

**OLD**:
```python
config = RunnableConfig(
    configurable={
        "thread_id": conversation.id,
        "llm_provider": llm_provider,
        "user_id": user.id,
        "tools": tools
    }
)
```

**NEW**:
```python
config = RunnableConfig(
    configurable={
        "thread_id": conversation.id,
        "user_id": user.id
        # Removed: llm_provider and tools (now bound at graph creation time)
    }
)
```

**Rationale**: create_react_agent binds model and tools at creation time, not invocation time.

**Verify**: WebSocket handler still retrieves tools via `getattr(graph, '_tools', None)` for tool source detection.

### Step 2.5: Archive or Remove Obsolete Nodes

**Option A (Recommended): Archive for reference**:
```bash
mkdir -p backend/app/langgraph/nodes/deprecated
git mv backend/app/langgraph/nodes/call_llm.py backend/app/langgraph/nodes/deprecated/
# Add comment to file: "Deprecated: Replaced by create_react_agent prebuilt"
```

**Option B: Delete entirely** (only if confident in migration):
```bash
git rm backend/app/langgraph/nodes/call_llm.py
```

**Nodes to archive/remove**:
- `call_llm.py` - Replaced by create_react_agent internal agent node
- `inject_system_prompt` function in `onboarding_graph.py` - Replaced by prompt parameter

**Keep**:
- `process_input.py` - May still be needed (verify in testing)
- Tool files (read_data.py, write_data.py, export_data.py, rag_search.py) - Unchanged

**Commit**:
```bash
git add -A
git commit -m "feat: migrate onboarding graph to create_react_agent prebuilt

- Replace hand-built ReAct graph with create_react_agent
- Add get_model() method to ILLMProvider interface
- Update main.py to initialize graph with llm_provider
- Simplify WebSocket handler RunnableConfig
- Archive obsolete call_llm node

Refs: #18"
```

---

## PHASE 3: Testing & Validation

**Goal**: Verify migration maintains all existing functionality

**Duration**: 2-3 hours

### Step 3.1: Run Existing Unit Tests

```bash
# Test all tool implementations (should pass unchanged)
pytest backend/tests/unit/test_write_data_tool.py -v
pytest backend/tests/unit/test_read_data_tool.py -v
pytest backend/tests/unit/test_export_data_tool.py -v

# Test state schema (should pass unchanged)
pytest backend/tests/unit/test_onboarding_state.py -v

# Expected: ALL TESTS PASS
```

**If tests fail**: Investigate whether tool execution flow changed with create_react_agent.

### Step 3.2: Run Integration Tests

```bash
# Test complete onboarding workflows
pytest backend/tests/integration/test_onboarding_graph_workflow.py -v

# Expected: All 5 tests pass
```

**Critical tests**:
1. `test_onboarding_graph_injects_system_prompt()` - Verify system prompt present
2. `test_onboarding_graph_tool_orchestration()` - Verify tools execute correctly
3. `test_onboarding_graph_state_persistence()` - Verify checkpointing works
4. `test_onboarding_graph_resume_from_checkpoint()` - Verify conversation resumption
5. `test_onboarding_graph_validation_retry()` - Verify validation error handling

**If tests fail**: Investigate these specific areas:
- System prompt injection (may need wrapper approach)
- Tool binding (verify tools accessible and callable)
- State persistence (verify checkpointer integration)
- Event streaming (verify astream_events works)

### Step 3.3: Run New WebSocket Tests

```bash
# Test WebSocket integration
pytest backend/tests/integration/test_onboarding_websocket.py -v

# Expected: All 8+ tests pass
```

**If tests fail**: Investigate:
- Event streaming compatibility (on_chat_model_stream, on_tool_start, on_tool_end)
- Tool execution visibility (ServerToolStartMessage, ServerToolCompleteMessage)
- State persistence across WebSocket reconnections

### Step 3.4: Run Fixed Persistence Tests

```bash
# Test state persistence with correct graph
pytest backend/tests/integration/test_onboarding_persistence.py -v

# Expected: Both tests pass with onboarding_graph
```

### Step 3.5: Manual End-to-End Test

**Test via WebSocket client** (use Postman, Thunder Client, or custom script):

1. **Connect**: `ws://localhost:8000/ws/onboarding?token=<valid_jwt>`
2. **Send**: `{"type": "message", "conversation_id": "<uuid>", "content": "Hello"}`
3. **Verify**: Receive ServerTokenMessage chunks
4. **Send**: `{"type": "message", "conversation_id": "<uuid>", "content": "My name is Alice"}`
5. **Verify**: Agent calls write_data tool (ServerToolStartMessage, ServerToolCompleteMessage)
6. **Send**: `{"type": "message", "conversation_id": "<uuid>", "content": "My ID is EMP-123, I want a keyboard"}`
7. **Verify**: Agent calls write_data twice
8. **Send**: `{"type": "message", "conversation_id": "<uuid>", "content": "Yes, finalize my onboarding"}`
9. **Verify**: Agent calls export_data tool
10. **Check**: JSON file created at `/app/onboarding_data/<conversation_id>.json`
11. **Verify**: File contains all collected data and conversation_summary

**Expected behavior**: Identical to current implementation.

### Step 3.6: Test Coverage Check

```bash
# Run with coverage
pytest backend/tests/ --cov=backend/app/langgraph/graphs/onboarding_graph --cov-report=term-missing

# Expected: Coverage >= 90%
```

**If coverage drops**: Add tests for uncovered branches.

---

## PHASE 4: Documentation & Cleanup

**Goal**: Update documentation and remove deprecated code

**Duration**: 1 hour

### Step 4.1: Update ABOUTME Comments

**File**: `/backend/app/langgraph/graphs/onboarding_graph.py`

Ensure first two lines are:
```python
# ABOUTME: Onboarding agent graph factory using LangGraph's prebuilt create_react_agent
# ABOUTME: Replaced custom ReAct implementation with prebuilt for cleaner, maintainable code
```

**File**: `/backend/app/core/ports/llm_provider.py`

Update ABOUTME if file has one, or add:
```python
# ABOUTME: LLM provider port interface with abstraction for OpenAI, Anthropic, Gemini, Ollama
# ABOUTME: Includes get_model() method to expose LangChain model for LangGraph prebuilt agents
```

### Step 4.2: Update Documentation Files

**File**: `/doc/general/ARCHITECTURE.md`

Add section:
```markdown
### Onboarding Graph (create_react_agent)

The onboarding graph uses LangGraph's prebuilt `create_react_agent` instead of hand-built ReAct pattern:

- **System Prompt**: Injected via `prompt` parameter (or wrapper node if API doesn't support)
- **Tools**: Bound at graph creation time: [read_data, write_data, rag_search, export_data]
- **State**: ConversationState extends MessagesState with onboarding-specific fields
- **Checkpointing**: AsyncMongoDBSaver for automatic state persistence

Benefits:
- Simpler implementation (removed 3 custom nodes)
- Less maintenance burden
- Proven ReAct loop implementation
- Same WebSocket API and tool behavior as before
```

### Step 4.3: Clean Up Deprecated Code

**If archive approach was used**:
```bash
# Verify deprecated nodes are not imported anywhere
grep -r "from app.langgraph.nodes.deprecated" backend/app/
# (Should return empty)

# If safe, remove deprecated folder entirely
git rm -r backend/app/langgraph/nodes/deprecated/
git commit -m "chore: remove deprecated nodes after successful migration

All tests pass with create_react_agent prebuilt approach.

Refs: #18"
```

**If nodes were already deleted**: Skip this step.

---

## PHASE 5: Deployment & Monitoring

**Goal**: Deploy safely with rollback capability

**Duration**: 1-2 hours

### Step 5.1: Create Feature Branch

```bash
git checkout -b feat/migrate-onboarding-to-create-react-agent
git push -u origin feat/migrate-onboarding-to-create-react-agent
```

### Step 5.2: Create Pull Request

**Title**: `feat: Migrate onboarding agent to create_react_agent prebuilt`

**Description**:
```markdown
## Summary
Migrates the onboarding agent from a hand-built ReAct pattern to LangGraph's prebuilt `create_react_agent` function.

## Changes
- Replaced custom graph construction with `create_react_agent`
- Added `get_model()` method to `ILLMProvider` interface
- Updated application startup to pass `llm_provider` to graph factory
- Simplified WebSocket handler configuration (removed runtime tool passing)
- Archived deprecated `call_llm` node
- Added 15+ new tests for WebSocket integration

## Testing
- ✅ All existing unit tests pass (30+ tests)
- ✅ All existing integration tests pass (5+ tests)
- ✅ New WebSocket integration tests pass (8+ tests)
- ✅ Manual E2E test successful (full onboarding flow)
- ✅ Coverage maintained at >= 90%

## Breaking Changes
None. WebSocket API contract preserved for frontend compatibility.

## Definition of Done
- [x] Refactor `create_onboarding_graph` to use `create_react_agent`
- [x] Make `ConversationState` extend `AgentState` (or verify compatibility)
- [x] System prompt passed via `prompt` parameter (or wrapper node)
- [x] Migrate tools to use `InjectedState` where beneficial (optional, not done)
- [x] Remove obsolete nodes: `call_llm`
- [x] Update existing integration tests
- [x] Update unit tests
- [x] All tests pass (>80% coverage achieved)
- [x] Update ABOUTME comments
- [x] No breaking changes to WebSocket API

Closes #18
```

### Step 5.3: Code Review Checklist

**For Reviewer (Pablo)**:

- [ ] System prompt injection works (verify first message is SystemMessage)
- [ ] All 4 onboarding tools execute correctly (read_data, write_data, rag_search, export_data)
- [ ] State persistence works (fields persist across turns)
- [ ] WebSocket streaming works (tokens, tool events)
- [ ] JSON export creates file with correct structure
- [ ] No changes to WebSocket message schemas
- [ ] Test coverage >= 90%
- [ ] ABOUTME comments present and accurate
- [ ] No hardcoded values or temporal naming (no "new", "improved", etc.)
- [ ] Git commit messages follow convention

### Step 5.4: Merge & Deploy

```bash
# After approval
git checkout main
git merge feat/migrate-onboarding-to-create-react-agent
git push origin main
```

### Step 5.5: Monitor Production (If Applicable)

**Watch for**:
- Increase in WebSocket errors
- Tool execution failures
- State persistence issues
- Changes in LLM token usage (should be similar)
- Export file creation failures

**Rollback Plan** (if issues detected):
```bash
git revert <commit_hash>
git push origin main
# Redeploy previous version
```

---

## Risk Mitigation

### Risk 1: System Prompt Not Injected (HIGH)

**Symptom**: Agent doesn't proactively guide onboarding, doesn't call export_data

**Diagnosis**:
```bash
# Check first message in state after first invocation
# Should be SystemMessage with ONBOARDING_SYSTEM_PROMPT content
```

**Solution Options**:
1. Use prompt parameter if create_react_agent supports it
2. Use wrapper node approach (inject_system_prompt → agent)
3. Modify ILLMProvider to include system message in every call

### Risk 2: Tool Binding Fails (MEDIUM)

**Symptom**: Tools not called, or LLM doesn't know about tools

**Diagnosis**:
```python
# Verify tools bound to model
model = llm_provider.get_model()
print(model.bind_tools)  # Should exist
```

**Solution**:
- Verify create_react_agent accepts tools parameter
- Verify tools list passed correctly
- Check LangChain model supports bind_tools()

### Risk 3: WebSocket Events Different (MEDIUM)

**Symptom**: Frontend doesn't receive token messages or tool events

**Diagnosis**:
```python
# In websocket_handler.py, add logging:
async for event in graph.astream_events(...):
    logger.info(f"Event: {event['event']}")
```

**Solution**:
- Map new event names to expected names in handler
- Update handler logic if event structure differs
- Verify event types: on_chat_model_stream, on_tool_start, on_tool_end

### Risk 4: State Persistence Breaks (HIGH)

**Symptom**: Conversations don't resume, fields lost between turns

**Diagnosis**:
```python
# Check checkpoint after invocation
state = await graph.aget_state(config)
print(state["values"])  # Should include all onboarding fields
```

**Solution**:
- Verify checkpointer passed to create_react_agent or compile()
- Verify ConversationState structure unchanged
- Check AsyncMongoDBSaver compatibility

### Risk 5: Export Data Fails (MEDIUM)

**Symptom**: export_data doesn't create JSON file or doesn't update state

**Diagnosis**:
```bash
# Check if file created
ls /app/onboarding_data/
# Should see <conversation_id>.json files
```

**Solution**:
- Verify export_data tool still has write permissions
- Check state["conversation_summary"] is set
- Verify LLM summary generation works

---

## Success Criteria

### Functional Requirements
- ✅ All onboarding workflows complete successfully
- ✅ System prompt guides agent behavior
- ✅ All 4 tools execute correctly (read_data, write_data, rag_search, export_data)
- ✅ State persists across conversation turns
- ✅ Validation errors handled and retried
- ✅ Export data creates JSON file with summary
- ✅ WebSocket streaming works (tokens and tool events)

### Technical Requirements
- ✅ Test coverage >= 90% (currently 80%+, improved with new tests)
- ✅ All existing tests pass without modification (except test_onboarding_persistence.py)
- ✅ WebSocket API contract unchanged (no breaking changes to frontend)
- ✅ CI/CD pipeline passes (linting, type checking, tests)
- ✅ Code review approved

### Performance Requirements
- ✅ No increase in response latency (< 10% variance)
- ✅ Token usage similar to current implementation (< 5% variance)
- ✅ No memory leaks or resource issues

---

## Rollback Plan

### Scenario 1: Tests Fail in PR
- Do not merge
- Investigate failures in feature branch
- Fix issues before attempting merge again

### Scenario 2: Production Issues After Merge
```bash
# Immediate rollback
git revert <migration_commit_hash>
git push origin main

# Alternative: Revert to previous commit
git reset --hard <previous_commit_hash>
git push origin main --force  # Use with caution
```

### Scenario 3: Partial Functionality Lost
- Keep new implementation but restore specific functionality
- Example: If system prompt fails, add wrapper node
- Example: If tool binding fails, adjust tool passing mechanism

---

## Alternative Approaches Considered

### Alternative 1: Keep Hand-Built Graph
**Pros**: No migration risk, known behavior
**Cons**: More maintenance burden, more code to test
**Decision**: Not chosen - prebuilt simplifies codebase

### Alternative 2: Hybrid Approach (Wrapper Node)
**Pros**: Preserves system prompt injection explicitly
**Cons**: Still some custom code
**Decision**: Use if create_react_agent doesn't support prompt parameter

### Alternative 3: Migrate All Graphs at Once
**Pros**: Consistent approach across all graphs
**Cons**: Higher risk, more complex PR
**Decision**: Not chosen - migrate onboarding first, learn, then migrate others

---

## Post-Migration Tasks

### Immediate (Week 1)
- [ ] Monitor production metrics (if deployed)
- [ ] Watch for error logs related to onboarding
- [ ] Gather feedback from users (if applicable)

### Short-term (Month 1)
- [ ] Consider migrating streaming_chat_graph to create_react_agent
- [ ] Document lessons learned for future migrations
- [ ] Share approach with team

### Long-term (Quarter 1)
- [ ] Evaluate InjectedState and Command patterns for tools
- [ ] Consider using pre_model_hook if beneficial
- [ ] Explore other LangGraph prebuilt patterns

---

## Key Files Reference

### Files to Modify
1. `/backend/app/core/ports/llm_provider.py` - Add get_model() method
2. `/backend/app/adapters/outbound/llm_providers/openai_provider.py` - Implement get_model()
3. `/backend/app/adapters/outbound/llm_providers/anthropic_provider.py` - Implement get_model()
4. `/backend/app/adapters/outbound/llm_providers/gemini_provider.py` - Implement get_model()
5. `/backend/app/adapters/outbound/llm_providers/ollama_provider.py` - Implement get_model()
6. `/backend/app/langgraph/graphs/onboarding_graph.py` - Replace create_onboarding_graph()
7. `/backend/app/main.py` - Update graph initialization
8. `/backend/app/adapters/inbound/websocket_handler.py` - Simplify RunnableConfig

### Files to Create
1. `/backend/tests/integration/test_onboarding_websocket.py` - WebSocket integration tests
2. `/backend/tests/unit/test_process_input_node.py` - Node unit tests
3. `/backend/tests/unit/test_call_llm_node.py` - Node unit tests (may be obsolete after migration)

### Files to Update (Tests)
1. `/backend/tests/integration/test_onboarding_persistence.py` - Fix graph import
2. `/backend/tests/integration/test_onboarding_graph_workflow.py` - Verify still passes
3. `/backend/tests/unit/test_onboarding_graph_nodes.py` - May need updates for wrapper node

### Files to Archive/Remove
1. `/backend/app/langgraph/nodes/call_llm.py` - Archive to deprecated/ or delete

### Documentation Files to Update
1. `/doc/general/ARCHITECTURE.md` - Add section on create_react_agent usage
2. `/doc/features/Migrate onboarding agent to langgraph.prebuilt.create_react_agent/PLAN.md` - This file

---

## Time Estimates

| Phase | Duration | Tasks |
|-------|----------|-------|
| Phase 1: Preparation | 2-3 hours | Research API, add tests, fix bugs |
| Phase 2: Core Migration | 3-4 hours | Refactor graph, update interfaces |
| Phase 3: Testing | 2-3 hours | Run tests, manual E2E, verify |
| Phase 4: Documentation | 1 hour | Update docs, ABOUTME comments |
| Phase 5: Deployment | 1-2 hours | PR, review, merge, monitor |
| **Total** | **9-13 hours** | Complete migration with testing |

---

## Questions for Pablo Before Implementation

1. **System Prompt**: If create_react_agent doesn't support prompt parameter, do you prefer:
   - [ ] Wrapper node approach (explicit control)
   - [ ] LLMProvider-level injection (cleaner abstraction)
   - [ ] Pre-state injection (simplest but logic outside graph)

2. **Tool Migration**: Should tools be migrated to use InjectedState and Command patterns?
   - [ ] Yes, migrate tools for cleaner code
   - [ ] No, keep current tool interface (simpler migration)
   - [ ] Evaluate after migration completes

3. **Test Coverage**: Is 90%+ coverage acceptable, or should we aim higher?
   - [ ] 90%+ is acceptable
   - [ ] Aim for 95%+
   - [ ] 100% coverage required

4. **Deployment**: Should this be deployed behind a feature flag for gradual rollout?
   - [ ] Yes, use feature flag for safety
   - [ ] No, deploy directly after tests pass
   - [ ] Not applicable (development environment only)

5. **Offboarding**: Should offboarding graph be migrated in same PR or separate?
   - [ ] Same PR (consistent approach)
   - [ ] Separate PR (lower risk)
   - [ ] Offboarding doesn't exist yet

---

## Conclusion

This migration plan provides a comprehensive, step-by-step approach to migrating the onboarding agent to `create_react_agent`. The plan prioritizes:

1. **Safety**: Extensive testing before, during, and after migration
2. **Simplicity**: Removing 3 custom nodes for cleaner codebase
3. **Compatibility**: Preserving WebSocket API contract for frontend
4. **Reversibility**: Clear rollback plan if issues arise

The migration is well-researched (5 comprehensive agent analyses) and focuses on the primary challenge: **system prompt injection**. With proper testing and validation, this migration should take 9-13 hours and result in a simpler, more maintainable onboarding system.

**Next Step**: Review this plan, answer the questions above, and proceed with Phase 1 (Preparation).
