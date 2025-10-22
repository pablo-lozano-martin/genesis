# Database MongoDB Analysis

## Request Summary

Add support for tool calling to enable LLM agents to invoke external tools (starting with a multiply tool) during conversations. This requires extending the Message model in MongoDB to store tool call requests and tool results, supporting the MessageRole.TOOL role, and maintaining backward compatibility with existing messages.

## Relevant Files & Modules

### Files to Examine

- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/message.py` - Message domain model with MessageRole enum and Message schema
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_models.py` - Beanie ODM document models including MessageDocument
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_message_repository.py` - MongoDB repository implementation for message operations
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/message_repository.py` - Message repository port interface
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/database/mongodb.py` - MongoDB connection manager and Beanie initialization
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/main.py` - Application startup with document model registration
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/anthropic_provider.py` - Example LLM provider showing message conversion from domain to LangChain format
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/use_cases/send_message.py` - Use case showing message creation and conversation history retrieval
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_handler.py` - WebSocket handler showing message flow during streaming chat

### Key Functions & Classes

- `MessageRole` enum in `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/message.py` - Currently has USER, ASSISTANT, SYSTEM (needs TOOL)
- `Message` class in `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/message.py` - Domain model with id, conversation_id, role, content, created_at, metadata fields
- `MessageDocument` class in `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_models.py` - MongoDB document model with Beanie ODM
- `MongoMessageRepository._to_domain()` in `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_message_repository.py` - Converts MessageDocument to domain Message
- `MongoMessageRepository.create()` in `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_message_repository.py` - Creates new messages in database
- `MongoMessageRepository.get_by_conversation_id()` in `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/repositories/mongo_message_repository.py` - Retrieves conversation history
- `AnthropicProvider._convert_messages()` in `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/anthropic_provider.py` - Converts domain messages to LangChain format

## Current Database Overview

### Collections & Schemas

The application uses three MongoDB collections managed by Beanie ODM:

**messages collection**
```python
class MessageDocument(Document):
    conversation_id: Indexed(str)       # Links message to conversation
    role: MessageRole                   # Enum: USER, ASSISTANT, SYSTEM
    content: str                        # Message text content
    created_at: datetime               # Message timestamp
    metadata: Optional[dict] = None    # Flexible metadata storage
```

**Current MessageRole enum:**
```python
class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
```

**conversations collection**
```python
class ConversationDocument(Document):
    user_id: Indexed(str)
    title: str = "New Conversation"
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
```

**users collection**
```python
class UserDocument(Document):
    email: Indexed(EmailStr, unique=True)
    username: Indexed(str, unique=True)
    hashed_password: str
    full_name: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
```

### Indexes

**MessageDocument indexes:**
- `conversation_id` - Single field index for filtering messages by conversation
- `[("conversation_id", 1), ("created_at", 1)]` - Compound index for ordered message retrieval

These indexes efficiently support the primary query pattern: fetching all messages for a conversation in chronological order.

### Repository Layer

The `MongoMessageRepository` implements `IMessageRepository` port interface and handles:
- Message creation with automatic ID generation
- Conversion between MongoDB documents and domain models
- Query operations filtered by conversation_id
- Deletion operations (single message or all messages in conversation)

The repository is instantiated per-request in websocket handlers and uses Beanie's async API for all database operations.

### Query Patterns

**Primary query pattern:**
```python
# Fetch conversation history ordered by creation time
docs = await MessageDocument.find(
    MessageDocument.conversation_id == conversation_id
).sort(MessageDocument.created_at).skip(skip).limit(limit).to_list()
```

This query is covered by the compound index `(conversation_id, created_at)`.

**Message flow:**
1. User sends message via WebSocket
2. Message saved to MongoDB as MessageRole.USER
3. All messages for conversation retrieved (indexed query)
4. Messages passed to LLM provider for generation
5. Assistant response saved as MessageRole.ASSISTANT
6. Conversation message_count incremented by 2

## Impact Analysis

### Collections Affected

**messages collection** - Primary impact
- Schema needs to support tool call data structure
- MessageRole enum needs TOOL value
- Document structure must accommodate tool_name, tool_args, tool_result

### Components Affected

1. **Domain Model** (`message.py`)
   - Add `MessageRole.TOOL` to enum
   - Consider adding optional tool-specific fields to Message model
   - Update MessageCreate and MessageResponse schemas

2. **MongoDB Document Model** (`mongo_models.py`)
   - MessageDocument may need additional optional fields for tool data
   - Existing metadata field might be sufficient for storing tool information

3. **Repository Layer** (`mongo_message_repository.py`)
   - `_to_domain()` conversion must handle tool messages
   - No changes needed if tool data stored in metadata

4. **LLM Provider Integration** (`anthropic_provider.py`, etc.)
   - `_convert_messages()` must handle MessageRole.TOOL conversion to LangChain ToolMessage
   - All LLM providers (OpenAI, Anthropic, Gemini, Ollama) need updating

5. **Use Cases** (`send_message.py`)
   - May need new use case for handling tool execution flow
   - Existing use case handles standard user/assistant exchange

6. **Query Patterns**
   - Existing indexes remain sufficient
   - No new query patterns anticipated for tool messages

## Database Recommendations

### Proposed Schema Changes

**Approach 1: Store tool data in metadata field (RECOMMENDED)**

The existing `metadata: Optional[dict]` field can store tool-specific information without breaking changes:

```python
# For tool call request messages
Message(
    conversation_id="...",
    role=MessageRole.TOOL,
    content="",  # Empty or descriptive text
    metadata={
        "tool_call": {
            "id": "call_123",
            "name": "multiply",
            "arguments": {"a": 5, "b": 10}
        }
    }
)

# For tool result messages
Message(
    conversation_id="...",
    role=MessageRole.TOOL,
    content="50",  # Result as string, or empty
    metadata={
        "tool_result": {
            "tool_call_id": "call_123",
            "name": "multiply",
            "result": 50
        }
    }
)
```

**Pros:**
- No schema migration required
- Backward compatible with existing messages
- Flexible structure for different tool types
- Metadata field already indexed as part of document

**Cons:**
- Less type safety than dedicated fields
- Querying specific tool calls requires metadata field queries

**Approach 2: Add dedicated optional fields to MessageDocument**

```python
class MessageDocument(Document):
    conversation_id: Indexed(str)
    role: MessageRole
    content: str
    created_at: datetime
    metadata: Optional[dict] = None

    # New optional fields for tool support
    tool_call_id: Optional[str] = None
    tool_name: Optional[str] = None
    tool_arguments: Optional[dict] = None
    tool_result: Optional[Any] = None
```

**Pros:**
- More explicit schema
- Easier to query tool-specific messages
- Better type validation

**Cons:**
- Requires careful handling of optional fields
- More fields to maintain
- Still need migration strategy

**RECOMMENDATION:** Use Approach 1 (metadata field) because:
1. Zero migration effort - existing messages unaffected
2. Maximum flexibility for future tool types
3. Aligns with MongoDB's document-oriented philosophy
4. Metadata field already exists and is working

### Proposed Indexes

**No new indexes required.** The current compound index `(conversation_id, created_at)` efficiently supports:
- Retrieving all messages (including tool messages) for a conversation in order
- Tool messages will be interspersed chronologically with user/assistant messages

**Optional future index** (only if filtering by tool calls becomes common):
```python
# Sparse index on metadata.tool_call.name for querying tool usage
[("metadata.tool_call.name", 1)]  # Sparse index, only for tool messages
```

This would enable queries like "find all multiply tool calls" but is likely premature optimization.

### Repository Changes

**Minimal changes required:**

1. **Domain Model Update** (`message.py`):
```python
class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"  # Add this
```

2. **Repository Layer** (`mongo_message_repository.py`):
- `_to_domain()` already handles metadata passthrough - no changes needed
- `create()` already handles metadata - no changes needed
- Existing methods work unchanged

3. **LLM Provider Updates** (all providers):
```python
def _convert_messages(self, messages: List[Message]) -> List:
    langchain_messages = []
    for msg in messages:
        if msg.role == MessageRole.USER:
            langchain_messages.append(HumanMessage(content=msg.content))
        elif msg.role == MessageRole.ASSISTANT:
            langchain_messages.append(AIMessage(content=msg.content))
        elif msg.role == MessageRole.SYSTEM:
            langchain_messages.append(SystemMessage(content=msg.content))
        elif msg.role == MessageRole.TOOL:
            # Convert to LangChain ToolMessage
            tool_call_id = msg.metadata.get("tool_result", {}).get("tool_call_id", "")
            langchain_messages.append(ToolMessage(content=msg.content, tool_call_id=tool_call_id))
    return langchain_messages
```

### Query Optimization

**Current query performance is optimal:**
- Compound index `(conversation_id, created_at)` covers the primary access pattern
- MongoDB efficiently retrieves messages in chronological order
- Tool messages integrate seamlessly into existing query patterns

**No optimization needed** because:
1. Tool messages don't introduce new query patterns
2. Existing index structure supports ordered retrieval
3. Metadata queries (if needed) are secondary and infrequent

## Implementation Guidance

### Step 1: Update Domain Model (Zero Migration)

1. Add `TOOL = "tool"` to MessageRole enum in `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/message.py`
2. No changes to Message class - metadata field handles tool data
3. Document metadata structure for tool messages in code comments

### Step 2: Update LLM Providers

1. Update `_convert_messages()` in all four providers:
   - `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/anthropic_provider.py`
   - `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/openai_provider.py`
   - `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/gemini_provider.py`
   - `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/llm_providers/ollama_provider.py`
2. Import LangChain's ToolMessage class
3. Handle MessageRole.TOOL conversion to ToolMessage

### Step 3: Implement Tool Calling Flow

1. Create tool execution logic (multiply function)
2. Intercept LLM responses that request tool calls
3. Create MessageRole.TOOL messages with tool_call metadata
4. Execute tools and create MessageRole.TOOL messages with tool_result metadata
5. Pass updated conversation history back to LLM

### Step 4: Testing Strategy

1. **Unit tests** - Test MessageRole.TOOL enum value exists
2. **Unit tests** - Test message creation with tool metadata structure
3. **Repository tests** - Verify tool messages can be created and retrieved
4. **Integration tests** - Test full conversation flow with tool calls
5. **Provider tests** - Verify each LLM provider converts tool messages correctly

### Metadata Structure Convention

Document the standard metadata structure for tool messages:

```python
# Tool call request (from LLM to application)
{
    "tool_call": {
        "id": "call_abc123",           # Unique call ID for correlation
        "name": "multiply",             # Tool function name
        "arguments": {"a": 5, "b": 10} # Tool arguments as dict
    }
}

# Tool result (from application to LLM)
{
    "tool_result": {
        "tool_call_id": "call_abc123",  # Correlates with tool_call.id
        "name": "multiply",              # Tool function name
        "result": 50,                    # Tool execution result
        "status": "success"              # Optional: success/error
    }
}
```

## Risks and Considerations

### Backward Compatibility

**LOW RISK** - The proposed approach maintains full backward compatibility:
- Existing messages without metadata continue to work
- MessageRole.TOOL is additive, doesn't affect existing roles
- No database migration required
- Existing queries and indexes unchanged

### Data Consistency

**MEDIUM RISK** - Tool call/result correlation:
- Tool calls and results are stored as separate messages
- `tool_call_id` in metadata must match between call and result
- Consider validation logic to ensure proper correlation
- Missing tool results could cause incomplete conversation history

**Mitigation:**
- Implement validation when creating tool result messages
- Add logging for tool call lifecycle tracking
- Consider adding tool_call_status field to track pending/completed calls

### Query Performance

**LOW RISK** - No performance degradation expected:
- Existing compound index supports chronological retrieval
- Tool messages will be sparse in most conversations
- Metadata field queries are infrequent and not performance-critical

### Schema Evolution

**LOW RISK** - Flexible metadata approach supports future changes:
- New tool types can be added without schema changes
- Tool-specific fields can be added to metadata structure
- If needed later, can migrate to dedicated fields

### LLM Provider Compatibility

**MEDIUM RISK** - Different providers handle tools differently:
- OpenAI uses function calling format
- Anthropic uses tool use format
- Gemini has its own tool schema
- Ollama may have limited tool support

**Mitigation:**
- Abstract tool calling interface per provider
- Document provider-specific tool capabilities
- Test tool calling with each supported LLM provider

### Transaction Boundaries

**LOW RISK** - Current implementation doesn't use MongoDB transactions:
- Messages are created individually (no multi-document transactions)
- Tool call + result could theoretically be inconsistent
- However, conversation flow is sequential and single-threaded per user

**Recommendation:**
- Continue without transactions for simplicity
- If transactional guarantees needed later, Beanie supports MongoDB transactions

## Testing Strategy

### Database Layer Tests

1. **Unit tests for domain model**
   - Test MessageRole.TOOL enum value
   - Test Message creation with tool metadata
   - Test validation rejects invalid metadata structures

2. **Repository integration tests**
   - Create tool call message with metadata
   - Create tool result message with metadata
   - Retrieve conversation with mixed message types
   - Verify tool messages maintain chronological order
   - Test metadata field preserves tool data structure

3. **Index performance tests** (optional)
   - Verify compound index covers tool message queries
   - Measure query performance with tool messages in history

### Application Layer Tests

1. **LLM provider tests**
   - Test _convert_messages() handles MessageRole.TOOL
   - Verify ToolMessage created with correct tool_call_id
   - Test each provider (OpenAI, Anthropic, Gemini, Ollama)

2. **End-to-end tool calling tests**
   - User sends message requiring tool use
   - LLM responds with tool call request
   - Tool executes and result stored
   - LLM receives tool result and generates final response
   - All messages persisted correctly in database

3. **Backward compatibility tests**
   - Conversations without tool messages continue to work
   - Existing message queries return correct results
   - Old messages without metadata field work correctly

### Migration Validation Tests

**Not applicable** - No migration needed with metadata approach. However, if migrating from an existing implementation:
- Verify all existing messages remain accessible
- Test that tool messages can coexist with regular messages
- Validate index coverage unchanged

## Summary

The recommended approach for adding tool calling support to the MongoDB message storage is:

1. **Add MessageRole.TOOL** to the enum (one-line change)
2. **Use existing metadata field** to store tool call and result data
3. **No database migration required** - fully backward compatible
4. **No new indexes required** - existing compound index is sufficient
5. **Update LLM provider message converters** to handle ToolMessage
6. **Document metadata structure convention** for tool calls and results

This approach minimizes risk, maintains backward compatibility, leverages MongoDB's document flexibility, and requires minimal code changes to the database layer. The primary implementation work will be in the tool execution logic and LLM provider integration, not in the database schema.
