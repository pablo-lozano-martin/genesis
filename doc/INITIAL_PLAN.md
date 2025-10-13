# Genesis - Initial Implementation Plan

## Project Overview

Genesis is a full-stack application built with a focus on modularity, testability, and rapid development. This document outlines the complete implementation strategy for building this production-ready foundation.

## Core Architecture Principles

1. **Hexagonal Architecture (Backend)**: Core business logic is isolated from external dependencies through ports (interfaces) and adapters (implementations)
2. **Component-Driven UI (Frontend)**: Reusable, composable components using shadcn/ui
3. **Provider Agnostic**: Easy switching between LLM providers without core logic changes
4. **Local-First Development**: One-command Docker setup for the entire stack

---

## Using Context7 MCP During Implementation

Throughout this implementation plan, you'll see **💡 MCP Tip** callouts. These indicate points where you should leverage Context7 MCP to fetch up-to-date documentation.

**What is Context7 MCP?**
Context7 is a Model Context Protocol server that provides access to the latest library documentation and code examples. Instead of relying on potentially outdated information, you can fetch current documentation for any library or framework.

**How to use it:**
When you see an MCP tip, ask your AI assistant to check Context7 for the specified libraries. For example:
- "Check Context7 for latest FastAPI authentication patterns"
- "Get LangGraph streaming documentation from Context7"
- "Fetch shadcn/ui Button component docs via Context7"

This ensures you're always working with the most current API patterns, best practices, and compatibility information.

---

## Project Structure

```
genesis/
├── backend/
│   ├── app/
│   │   ├── core/                    # Hexagonal Architecture - Core Domain
│   │   │   ├── domain/              # Domain models (User, Conversation, Message)
│   │   │   ├── ports/               # Interfaces for repositories and services
│   │   │   └── use_cases/           # Business logic (CreateConversation, SendMessage)
│   │   ├── adapters/                # Hexagonal Architecture - Adapters
│   │   │   ├── inbound/             # API controllers (REST, WebSocket)
│   │   │   └── outbound/            # External service implementations
│   │   │       ├── repositories/    # MongoDB implementations
│   │   │       └── llm_providers/   # OpenAI, Anthropic, Gemini, Ollama adapters
│   │   ├── infrastructure/          # Cross-cutting concerns
│   │   │   ├── config/              # Settings and environment variables
│   │   │   ├── security/            # JWT, OAuth2, password hashing
│   │   │   └── database/            # MongoDB connection and initialization
│   │   ├── langgraph/               # LangGraph conversation flow
│   │   │   ├── graphs/              # Conversation state machines
│   │   │   ├── nodes/               # Processing nodes
│   │   │   └── state.py             # Conversation state definitions
│   │   └── main.py                  # FastAPI application entry point
│   ├── tests/
│   │   ├── unit/                    # Unit tests for core logic
│   │   ├── integration/             # Integration tests
│   │   └── conftest.py              # Pytest fixtures
│   ├── Dockerfile
│   ├── requirements.txt
│   └── pytest.ini
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ui/                  # shadcn/ui components
│   │   │   ├── chat/                # Chat interface components
│   │   │   ├── auth/                # Login/Register components
│   │   │   └── layout/              # Layout components
│   │   ├── hooks/                   # Custom React hooks
│   │   ├── services/                # API and WebSocket clients
│   │   ├── contexts/                # React context providers
│   │   ├── lib/                     # Utility functions
│   │   ├── types/                   # TypeScript types
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── public/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── tsconfig.json
├── docker-compose.yml
├── .env.example
├── doc/
│   └── INITIAL_PLAN.md (this file)
└── README.md
```

---

## Implementation Phases

### Phase 1: Project Foundation & Infrastructure

**Objective**: Set up the basic project structure, Docker environment, and core dependencies.

#### Tasks:
1. **Initialize Backend**
   - Create FastAPI project structure
   - Set up virtual environment and dependencies
   - Configure MongoDB with Beanie ODM
   - Create base configuration system (environment variables)
   - Set up logging
   - 💡 **MCP Tip**: Use Context7 to fetch latest FastAPI documentation for project structure best practices

2. **Initialize Frontend**
   - Create Vite + React + TypeScript project
   - Install TailwindCSS
   - Set up shadcn/ui
   - Configure routing (React Router)
   - Set up base theme and layout
   - 💡 **MCP Tip**: Use Context7 to get up-to-date Vite and React Router documentation

3. **Docker Configuration**
   - Create backend Dockerfile
   - Create frontend Dockerfile
   - Create docker-compose.yml with:
     - Backend service
     - Frontend service
     - MongoDB service
   - Create .env.example file

**Dependencies (Backend)**:
```txt
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
beanie>=1.23.0
motor>=3.3.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
python-multipart>=0.0.6
langgraph>=0.0.20
langchain>=0.1.0
langchain-openai>=0.0.2
langchain-anthropic>=0.0.1
langchain-google-genai>=0.0.5
websockets>=12.0
pytest>=7.4.3
pytest-asyncio>=0.21.1
httpx>=0.25.2
```

💡 **MCP Tip**: Before installing dependencies, use Context7 to check for latest versions and compatibility of: FastAPI, Beanie, LangGraph, LangChain providers

**Dependencies (Frontend)**:
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "react-markdown": "^9.0.1",
    "remark-gfm": "^4.0.0",
    "react-syntax-highlighter": "^15.5.0",
    "axios": "^1.6.2",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.0.0",
    "tailwind-merge": "^2.1.0",
    "lucide-react": "^0.294.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.43",
    "@types/react-dom": "^18.2.17",
    "@vitejs/plugin-react": "^4.2.1",
    "typescript": "^5.3.3",
    "vite": "^5.0.8",
    "tailwindcss": "^3.3.6",
    "autoprefixer": "^10.4.16",
    "postcss": "^8.4.32"
  }
}
```

💡 **MCP Tip**: Use Context7 to verify latest React, TailwindCSS, and TypeScript setup patterns

---

### Phase 2: Core Domain & Hexagonal Architecture Setup

**Objective**: Implement the domain models and define ports (interfaces) for the hexagonal architecture.

#### Backend Components:

1. **Domain Models** (`app/core/domain/`)
   - `User`: User entity with authentication fields
   - `Conversation`: Conversation entity with metadata
   - `Message`: Message entity (user/assistant, content, timestamps)

2. **Ports (Interfaces)** (`app/core/ports/`)
   - `IUserRepository`: User CRUD operations
   - `IConversationRepository`: Conversation CRUD operations
   - `IMessageRepository`: Message CRUD operations
   - `ILLMProvider`: Abstract LLM interface (generate, stream methods)
   - `IAuthService`: Authentication interface

3. **Use Cases** (`app/core/use_cases/`)
   - `RegisterUser`: Handle user registration
   - `AuthenticateUser`: Handle user login
   - `CreateConversation`: Create new conversation
   - `SendMessage`: Process and respond to user messages
   - `GetConversationHistory`: Retrieve conversation history

---

### Phase 3: Authentication System

**Objective**: Implement secure multi-tenant authentication with OAuth2 and JWT.

#### Tasks:
1. **Backend Security Infrastructure**
   - Password hashing with bcrypt
   - JWT token generation and validation
   - OAuth2 password flow implementation
   - User registration endpoint
   - Login endpoint
   - Token refresh endpoint
   - Protected route middleware

2. **Frontend Authentication**
   - Login form component (shadcn/ui)
   - Register form component
   - Authentication context provider
   - Token storage (localStorage with security considerations)
   - Protected route wrapper
   - Auto-logout on token expiration

**Security Considerations**:
- Password requirements validation
- Rate limiting on auth endpoints
- Secure token storage
- CORS configuration
- HTTPS enforcement in production

💡 **MCP Tip**: Use Context7 to check latest FastAPI security best practices, OAuth2 implementation patterns, and JWT handling

---

### Phase 4: Database Layer (Outbound Adapters)

**Objective**: Implement MongoDB repositories following the hexagonal architecture.

#### Tasks:
1. **MongoDB Setup**
   - Beanie ODM configuration
   - Database connection management
   - Index creation for performance

2. **Repository Implementations** (`app/adapters/outbound/repositories/`)
   - `MongoUserRepository`: Implements `IUserRepository`
   - `MongoConversationRepository`: Implements `IConversationRepository`
   - `MongoMessageRepository`: Implements `IMessageRepository`

3. **Data Models** (Beanie Documents)
   - Map domain models to MongoDB collections
   - Define indexes and constraints

**Key Design Points**:
- Repositories only handle data persistence
- Domain models remain database-agnostic
- Easy to swap MongoDB for another database by creating new adapters

💡 **MCP Tip**: Use Context7 to get latest Beanie ODM documentation for schema definitions, indexing strategies, and async patterns

---

### Phase 5: LLM Provider Abstraction

**Objective**: Create a provider-agnostic LLM service layer supporting multiple providers.

#### Tasks:
1. **LLM Port Interface** (`app/core/ports/llm_provider.py`)
   ```python
   class ILLMProvider(ABC):
       @abstractmethod
       async def generate(self, messages: List[Message]) -> str:
           pass

       @abstractmethod
       async def stream(self, messages: List[Message]) -> AsyncGenerator[str, None]:
           pass
   ```

2. **Provider Adapters** (`app/adapters/outbound/llm_providers/`)
   - `OpenAIProvider`: Implements ILLMProvider using OpenAI API
   - `AnthropicProvider`: Implements ILLMProvider using Anthropic API
   - `GeminiProvider`: Implements ILLMProvider using Google Gemini API
   - `OllamaProvider`: Implements ILLMProvider using local Ollama

3. **Provider Factory**
   - Configuration-based provider selection
   - Environment variable for provider selection
   - Fallback mechanisms

**Configuration Example**:
```env
LLM_PROVIDER=openai  # or anthropic, gemini, ollama
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
OLLAMA_BASE_URL=http://localhost:11434
```

💡 **MCP Tip**: Use Context7 to fetch latest API documentation and code examples for:
   - `langchain-openai` - OpenAI integration patterns and streaming
   - `langchain-anthropic` - Anthropic/Claude API usage
   - `langchain-google-genai` - Google Gemini implementation
   - `langchain` - Core LangChain abstractions and base classes

---

### Phase 6: LangGraph Integration

**Objective**: Implement conversation flow management using LangGraph.

#### Tasks:
1. **State Definition** (`app/langgraph/state.py`)
   - Conversation state schema
   - Message history tracking
   - User context

2. **Graph Nodes** (`app/langgraph/nodes/`)
   - `process_user_input`: Validate and process user messages
   - `call_llm`: Invoke LLM provider
   - `format_response`: Format LLM output
   - `save_to_history`: Persist conversation

3. **Graph Definition** (`app/langgraph/graphs/chat_graph.py`)
   - Define conversation flow
   - Add conditional edges
   - Configure streaming

**Why LangGraph**:
- Provides clear state management
- Enables complex agentic behaviors later (tool calling, multi-step reasoning)
- Built-in streaming support
- Easy to extend with new nodes

💡 **MCP Tip**: Use Context7 to check `langgraph` documentation for:
   - State graph creation and node definitions
   - Conditional edge routing
   - Streaming response patterns
   - State persistence and checkpointing

---

### Phase 7: WebSocket Real-Time Communication

**Objective**: Implement WebSocket endpoints for streaming LLM responses.

#### Tasks:
1. **Backend WebSocket Endpoint** (`app/adapters/inbound/websocket.py`)
   - WebSocket connection handler
   - Authentication middleware for WebSocket
   - Message handler (receive user messages)
   - Stream handler (send LLM responses token-by-token)
   - Error handling and reconnection logic

2. **Frontend WebSocket Client** (`frontend/src/services/websocket.ts`)
   - WebSocket connection management
   - Auto-reconnect logic
   - Message sending
   - Token streaming reception
   - Connection state management

3. **React Integration**
   - Custom `useWebSocket` hook
   - Message state management
   - Streaming message display
   - Loading and error states

**Protocol Design**:
```typescript
// Client -> Server
{
  "type": "message",
  "conversation_id": "uuid",
  "content": "User message"
}

// Server -> Client (streaming)
{
  "type": "token",
  "content": "partial response"
}

// Server -> Client (complete)
{
  "type": "complete",
  "message_id": "uuid"
}

// Server -> Client (error)
{
  "type": "error",
  "message": "Error description"
}
```

💡 **MCP Tip**: Use Context7 to check FastAPI WebSocket documentation for authentication patterns, connection management, and error handling best practices

---

### Phase 8: REST API Endpoints (Inbound Adapters)

**Objective**: Create REST endpoints for non-real-time operations.

#### Endpoints:

**Authentication**:
- `POST /api/auth/register`: Register new user
- `POST /api/auth/token`: Login and get JWT token
- `POST /api/auth/refresh`: Refresh JWT token

**Conversations**:
- `GET /api/conversations`: List user's conversations
- `POST /api/conversations`: Create new conversation
- `GET /api/conversations/{id}`: Get conversation details
- `DELETE /api/conversations/{id}`: Delete conversation
- `GET /api/conversations/{id}/messages`: Get conversation messages

**User**:
- `GET /api/user/me`: Get current user info
- `PATCH /api/user/me`: Update user info

**Health**:
- `GET /api/health`: Health check endpoint

---

### Phase 9: Frontend Chat Interface

**Objective**: Build a modern, responsive chat UI using shadcn/ui components.

#### Components:

1. **Chat Interface** (`src/components/chat/`)
   - `ChatContainer`: Main chat layout
   - `MessageList`: Display conversation messages
   - `MessageItem`: Individual message component
   - `MessageInput`: Text input with send button
   - `TypingIndicator`: Show when bot is responding
   - `CodeBlock`: Syntax-highlighted code display
   - `MarkdownRenderer`: Render markdown in messages

2. **Sidebar**
   - `ConversationList`: List of user conversations
   - `ConversationItem`: Individual conversation card
   - `NewConversationButton`: Create new chat

3. **shadcn/ui Components to Install**:
   - Button
   - Card
   - Input
   - Textarea
   - Avatar
   - Badge
   - ScrollArea
   - Separator
   - Dropdown Menu
   - Dialog
   - Toast

**UI Features**:
- Smooth scrolling to latest message
- Auto-scroll during streaming
- Copy code button for code blocks
- Timestamp display
- Message status indicators
- Responsive design (mobile-friendly)
- Dark/light mode toggle

💡 **MCP Tip**: Use Context7 to get latest shadcn/ui component documentation and installation instructions. Check React hooks documentation for custom hook patterns (useWebSocket, useChat)

---

### Phase 10: Testing Strategy

**Objective**: Ensure reliability through comprehensive testing.

#### Backend Tests:

1. **Unit Tests** (`tests/unit/`)
   - Domain model validation
   - Use case logic
   - Repository mocking
   - LLM provider mocking

2. **Integration Tests** (`tests/integration/`)
   - API endpoint testing
   - Database operations
   - Authentication flow
   - WebSocket communication

**Example Test Structure**:
```python
# tests/unit/use_cases/test_send_message.py
@pytest.mark.asyncio
async def test_send_message_use_case(mock_llm_provider, mock_message_repo):
    # Test use case with mocked dependencies
    pass

# tests/integration/test_chat_api.py
@pytest.mark.asyncio
async def test_websocket_message_streaming(test_client, auth_token):
    # Test real WebSocket streaming
    pass
```

#### Frontend Tests:
- Component rendering tests (React Testing Library)
- Integration tests for authentication flow
- WebSocket mock testing

💡 **MCP Tip**: Use Context7 to check latest pytest patterns, pytest-asyncio best practices, and FastAPI testing utilities (TestClient, WebSocketTestSession)

---

### Phase 11: Docker & Deployment Configuration

**Objective**: Create a production-ready containerized deployment.

#### docker-compose.yml Structure:
```yaml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - MONGODB_URL=mongodb://mongodb:27017
      - LLM_PROVIDER=${LLM_PROVIDER}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - mongodb
    volumes:
      - ./backend:/app
    command: uvicorn app.main:app --host 0.0.0 --port 8000 --reload

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - VITE_API_URL=http://localhost:8000
    volumes:
      - ./frontend:/app
      - /app/node_modules
    command: npm run dev

  mongodb:
    image: mongo:7.0
    ports:
      - "27017:27017"
    volumes:
      - mongodb_data:/data/db
    environment:
      - MONGO_INITDB_DATABASE=genesis

volumes:
  mongodb_data:
```

#### Dockerfile Optimization:
- Multi-stage builds for production
- Layer caching for faster builds
- Security: non-root user
- Health checks

💡 **MCP Tip**: Use Context7 to verify latest Docker best practices for Python (FastAPI) and Node.js (Vite) applications, including multi-stage builds and security hardening

---

### Phase 12: Documentation & Developer Experience

**Objective**: Provide clear documentation and tooling for future development.

#### Documentation Files:
1. **README.md**: Quick start guide, features, architecture overview
2. **CLAUDE.md**: AI assistant guidance for working with the codebase
3. **API.md**: API endpoint documentation
4. **ARCHITECTURE.md**: Detailed architecture explanation
5. **DEPLOYMENT.md**: Production deployment guide

#### Developer Tools:
- Pre-commit hooks for code formatting
- Linting configuration (Ruff for Python, ESLint for TypeScript)
- API documentation (FastAPI auto-docs at `/docs`)
- Environment variable validation
- Database migration scripts

---

## Key Technical Decisions

### 1. Why Hexagonal Architecture?

**Benefits**:
- **Testability**: Core logic can be tested without database or external APIs
- **Flexibility**: Easy to swap databases or LLM providers
- **Clarity**: Clear separation between business logic and infrastructure
- **Future-proof**: Easy to add new features without refactoring

**Trade-offs**:
- More initial setup (interfaces, adapters)
- May feel over-engineered for simple use cases

**Verdict**: Worth it for a template meant to be extended and maintained long-term.

### 2. Why LangGraph?

**Benefits**:
- Built for agentic AI workflows
- Clear state management
- Native streaming support
- Easy to extend with tools and multi-step reasoning

**Trade-offs**:
- Additional dependency
- Learning curve

**Verdict**: Essential for building extensible chatbot logic beyond simple request-response.

### 3. Why MongoDB?

**Benefits**:
- Flexible schema for evolving conversation structures
- Good performance for document-based data
- Easy to store nested conversation history

**Trade-offs**:
- Not as ACID-compliant as PostgreSQL
- May be overkill for simple relational data

**Verdict**: Good fit for conversational data with potential for complex nested structures.

### 4. Why shadcn/ui?

**Benefits**:
- Copy-paste components (no npm bloat)
- Full customization (you own the code)
- Built on Radix UI (accessible)
- Beautiful, modern design

**Trade-offs**:
- Manual component installation
- Need to maintain component code

**Verdict**: Perfect for a template where developers should own and customize the UI.

---

## Development Workflow

### Initial Setup:
```bash
# Clone and setup
git clone <repo-url>
cd genesis
cp .env.example .env
# Edit .env with your API keys

# Start everything with Docker
docker-compose up

# Backend will be available at http://localhost:8000
# Frontend will be available at http://localhost:3000
# API docs at http://localhost:8000/docs
```

### Development Commands:

**Backend**:
```bash
# Run tests
docker-compose exec backend pytest

# Run specific test
docker-compose exec backend pytest tests/unit/test_use_cases.py

# Access backend shell
docker-compose exec backend bash

# View logs
docker-compose logs -f backend
```

**Frontend**:
```bash
# Install new dependency
docker-compose exec frontend npm install <package>

# Access frontend shell
docker-compose exec frontend sh

# View logs
docker-compose logs -f frontend
```

---

## Success Criteria

The implementation will be considered complete when:

1. ✅ A user can register and log in
2. ✅ A user can create a new conversation
3. ✅ A user can send a message and receive a streamed response
4. ✅ Responses stream token-by-token in real-time
5. ✅ Conversation history is persisted and retrievable
6. ✅ Multiple LLM providers can be swapped via configuration
7. ✅ The entire stack starts with `docker-compose up`
8. ✅ Core use cases have unit tests
9. ✅ API endpoints have integration tests
10. ✅ Code is formatted and linted
11. ✅ README provides clear setup instructions
12. ✅ UI is responsive and accessible

---

## Estimated Timeline

- **Phase 1-2**: Project setup and domain modeling (1-2 days)
- **Phase 3-4**: Authentication and database layer (2-3 days)
- **Phase 5-6**: LLM integration and LangGraph (2-3 days)
- **Phase 7-8**: WebSocket and REST API (2-3 days)
- **Phase 9**: Frontend chat interface (3-4 days)
- **Phase 10**: Testing (2-3 days)
- **Phase 11-12**: Docker, documentation, polish (1-2 days)

**Total**: ~15-20 days of focused development

---

## Future Extension Points

This template is designed to be easily extended with:

1. **RAG (Retrieval-Augmented Generation)**:
   - Add vector database adapter (Pinecone, Weaviate, ChromaDB)
   - Create document upload endpoints
   - Add retrieval node in LangGraph

2. **Agentic Tools**:
   - Add tool interfaces in ports
   - Implement tool nodes in LangGraph
   - Create tool registry system

3. **Multi-modal Support**:
   - Extend message model for images/audio
   - Add file upload handling
   - Integrate vision models

4. **Advanced Features**:
   - Conversation sharing
   - Export conversations
   - Usage analytics
   - Rate limiting per user
   - Admin dashboard

---

## Next Steps

1. **Review this plan** and provide feedback
2. **Approve to start implementation** or request changes
3. **Begin with Phase 1**: Project foundation and infrastructure

Once approved, we'll proceed phase-by-phase, ensuring each component is working before moving to the next. Each phase will include testing and validation.
