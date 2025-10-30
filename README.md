# Orbio Onboarding Chatbot

An intelligent conversational AI agent for employee onboarding at Orbio. This production-ready system demonstrates advanced LLM capabilities including ReAct workflow patterns, RAG, speech-to-text input, and natural language data collection.

## 🎯 Project Overview

This project fulfills the AI Engineer assignment requirements by implementing a sophisticated onboarding assistant that:

- **Conducts natural conversations** to collect employee information
- **Extracts and validates data** into structured formats
- **Leverages RAG** to answer questions from a company knowledge base
- **Provides speech-to-text input** for hands-free interaction
- **Generates conversation summaries** with key insights
- **Maintains full conversation context** throughout the interaction

### Assignment Requirements Met

#### Core Requirements ✅
- ✅ Natural conversational flow with context management
- ✅ Structured data extraction and validation (employee_name, employee_id, starter_kit, dietary_restrictions, meeting_scheduled)
- ✅ JSON storage with MongoDB persistence
- ✅ Error handling and graceful degradation
- ✅ LLM-generated conversation summaries

#### Bonus Features ✅
- ✅ RAG implementation with ChromaDB vector store and 6 company documents
- ✅ Multi-turn conversation memory via LangGraph checkpoints
- ✅ Speech-to-text support using OpenAI Whisper API

## 🏗️ System Architecture

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                        │
│  - Chat UI with Shadcn components                              │
│  - WebSocket for real-time streaming                           │
│  - Speech-to-text input via MediaRecorder API                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ WebSocket + REST
┌──────────────────────────▼──────────────────────────────────────┐
│                   Backend (FastAPI + LangGraph)                 │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │          Hexagonal Architecture (Ports & Adapters)      │   │
│  │                                                         │   │
│  │  Core Domain ──► Ports ──► Adapters                    │   │
│  │  (Models, Logic)  (Interfaces)  (LLM, DB, API)         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              LangGraph ReAct Agent                      │   │
│  │                                                         │   │
│  │  System Prompt ──► Agent Reasoning ──► Tool Selection  │   │
│  │       │               │                     │           │   │
│  │       └───► Loop ◄────┴─────────────────────┘           │   │
│  │                                                         │   │
│  │  Tools:                                                 │   │
│  │  - read_data() - Query collected information           │   │
│  │  - write_data() - Validate and store data              │   │
│  │  - rag_search() - Search knowledge base                │   │
│  │  - export_data() - Generate summary & export JSON      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└───┬─────────────────────────┬──────────────────────┬───────────┘
    │                         │                      │
    ▼                         ▼                      ▼
┌────────────┐      ┌──────────────────┐   ┌─────────────────┐
│  MongoDB   │      │   MongoDB        │   │   ChromaDB      │
│  (App DB)  │      │  (LangGraph DB)  │   │ (Vector Store)  │
│            │      │                  │   │                 │
│ - Users    │      │ - Checkpoints    │   │ - 6 Company     │
│ - Convos   │      │ - Message History│   │   Documents     │
└────────────┘      └──────────────────┘   └─────────────────┘
```

### Technology Stack

**Backend:**
- **Framework**: FastAPI (Python 3.13)
- **Agent Orchestration**: LangGraph with `create_react_agent` prebuilt
- **LLM Integration**: Multi-provider support (OpenAI, Anthropic, Google, Ollama)
- **Database**: MongoDB (two-database pattern)
- **Vector Store**: ChromaDB (embedded mode)
- **Architecture**: Hexagonal (Ports & Adapters)

**Frontend:**
- **Framework**: React 19 + TypeScript
- **Build Tool**: Vite
- **Styling**: TailwindCSS + Shadcn UI
- **Real-time**: WebSocket streaming
- **Speech**: Browser MediaRecorder API + OpenAI Whisper

**Infrastructure:**
- **Containerization**: Docker + Docker Compose
- **Authentication**: JWT-based
- **Testing**: Pytest with 24 test files (unit + integration)

## 🔑 Key Design Decisions

### 1. LangGraph with ReAct Pattern
**Decision**: Use LangGraph's `create_react_agent` for agent orchestration

**Rationale**:
- Native support for ReAct (Reasoning + Acting) workflow
- Automatic state persistence via checkpoints
- Built-in streaming and tool calling
- Production-ready error handling
- Less boilerplate than custom implementation

**Trade-offs**:
- Dependency on LangGraph ecosystem
- Learning curve for team members unfamiliar with the framework
- Balanced by significantly faster development time and better maintainability

### 2. Hexagonal Architecture
**Decision**: Implement Ports & Adapters pattern

**Rationale**:
- Testable business logic independent of infrastructure
- Easy to swap LLM providers or databases
- Clear separation of concerns (domain, ports, adapters)
- Improved maintainability and extensibility

**Trade-offs**:
- More initial setup complexity
- Additional abstraction layers
- Justified by long-term maintainability benefits

### 3. Two-Database Pattern
**Decision**: Separate MongoDB instances for application data and LangGraph checkpoints

**Rationale**:
- Security boundary: conversation ownership vs. message content
- Independent scaling strategies
- Leverages LangGraph's native checkpoint persistence
- Cleaner separation of concerns

**Trade-offs**:
- Additional infrastructure complexity
- More connection overhead
- Outweighed by improved security and scalability

### 4. RAG with ChromaDB
**Decision**: Use ChromaDB in embedded mode for knowledge base

**Rationale**:
- No separate service required (simpler deployment)
- File-based persistence (good for MVP)
- Strong performance for 6-document knowledge base
- Simple semantic search API

**Trade-offs**:
- Embedded mode limits multi-process scaling
- Less advanced features than production vector DBs (Pinecone, Weaviate)
- Sufficient for current scale, can migrate later if needed

### 5. Multi-Provider LLM Support
**Decision**: Abstract LLM provider behind `ILLMProvider` interface

**Rationale**:
- Provider flexibility (OpenAI, Anthropic, Google, Ollama)
- Cost optimization by switching models
- Risk mitigation if provider has outages
- Easier testing with local models

**Trade-offs**:
- Additional abstraction overhead
- Need to maintain multiple provider implementations
- Worth it for operational flexibility

### 6. Speech-to-Text Integration
**Decision**: Client-side audio recording with server-side Whisper transcription

**Rationale**:
- Browser MediaRecorder API is widely supported
- OpenAI Whisper provides high-quality transcription
- Auth-protected endpoint ensures security
- Separates UI concern (recording) from AI concern (transcription)

**Trade-offs**:
- Requires OpenAI API key even if using different LLM
- Network overhead for audio upload
- Balanced by superior transcription quality

## 🚀 Setup Instructions

### Prerequisites

- Docker and Docker Compose
- API key for your chosen LLM provider (OpenAI, Anthropic, Google, or Ollama)
- (Optional) OpenAI API key for speech-to-text feature

### Installation

1. **Clone the repository**

```bash
cd genesis
```

2. **Configure environment variables**

```bash
cp .env.example .env
```

Edit `.env` and add your configuration:

```env
# Required: Choose your LLM provider
LLM_PROVIDER=openai

# Add your API key for the chosen provider
OPENAI_API_KEY=your-openai-key-here
# OR
ANTHROPIC_API_KEY=your-anthropic-key-here
# OR
GOOGLE_API_KEY=your-google-key-here

# Required: JWT secret for authentication
SECRET_KEY=your-random-secret-key-here

# Optional: Customize model (defaults to gpt-4o-mini)
LLM_MODEL=gpt-4o-mini
```

3. **Start the application**

```bash
docker-compose up
```

This will start:
- Backend API at `http://localhost:8000`
- Frontend at `http://localhost:5173`
- MongoDB at `localhost:27017`

4. **Access the application**

- **Frontend**: http://localhost:5173
- **API Documentation**: http://localhost:8000/docs

5. **Create an account**

- Navigate to the frontend
- Click "Register" and create a new account
- Login and start a conversation with the onboarding bot

## 💬 Sample Conversations

### Example 1: Complete Onboarding Flow

```
User: Hi, I'm starting at Orbio next week.

Bot: Welcome to Orbio! I'm excited to help you get started. To make sure
     everything is ready for your first day, I'll need to collect some
     information from you. Could you tell me your full name?

User: John Smith

Bot: Great to meet you, John! What's your employee ID?

User: EMP12345

Bot: Perfect. Now, we have a few starter kit options available. Would you
     like to hear about them?

User: Yes, what are my options?

Bot: [Agent searches knowledge base using rag_search tool]

     We offer three starter kit options:

     1. **Standard Kit**: Laptop, monitor, keyboard, mouse
     2. **Developer Kit**: Standard kit + mechanical keyboard + dual monitors
     3. **Designer Kit**: Standard kit + graphics tablet + color-calibrated monitor

     Which one would you prefer?

User: I'll take the Developer Kit.

Bot: Excellent choice! Do you have any dietary restrictions we should know
     about for team lunches and office snacks?

User: I'm vegetarian.

Bot: Noted! Lastly, would you like me to schedule a welcome meeting with
     your manager for your first day?

User: Yes, please schedule it.

Bot: Perfect! I have all the information I need. Let me generate a summary
     of your onboarding details.

     [Agent calls export_data tool]

     Your onboarding is complete! Here's a summary:

     - Employee Name: John Smith
     - Employee ID: EMP12345
     - Starter Kit: Developer Kit
     - Dietary Restrictions: Vegetarian
     - Welcome Meeting: Scheduled

     All details have been saved. Looking forward to seeing you on your first day!
```

### Example 2: RAG-Powered Question Answering

```
User: What benefits does Orbio offer?

Bot: [Agent searches knowledge base using rag_search tool]

     Orbio offers a comprehensive benefits package including:

     - Health insurance (medical, dental, vision)
     - 401(k) with company match
     - Unlimited PTO
     - Remote work flexibility
     - Professional development budget
     - Stock options

     Is there a specific benefit you'd like to know more about?

User: Tell me about the professional development budget.

Bot: Each employee receives an annual professional development budget of
     $2,000 that can be used for courses, conferences, certifications, or
     books related to your role. You can submit reimbursement requests
     through our HR portal.
```

### Example 3: Error Handling

```
User: My employee ID is ABC.

Bot: I need a valid employee ID format (e.g., EMP12345). Could you provide
     your complete employee ID?

User: Oh sorry, it's EMP67890.

Bot: Thank you! I've recorded your employee ID.
```

## 📊 Project Structure

```
genesis/
├── backend/
│   ├── app/
│   │   ├── core/                    # Domain models, ports, use cases
│   │   ├── adapters/                # API routers, LLM providers, repositories
│   │   ├── infrastructure/          # Database, security, config
│   │   ├── langgraph/              # Graphs, tools, state, prompts
│   │   │   ├── graphs/             # onboarding_graph.py
│   │   │   ├── tools/              # read_data, write_data, export_data, rag_search
│   │   │   ├── state.py            # ConversationState schema
│   │   │   └── prompts/            # System prompts
│   │   └── main.py                 # FastAPI application
│   ├── tests/                      # 24 test files (unit + integration)
│   ├── knowledge_base/             # 6 Orbio company documents
│   │   ├── benefits_and_perks.md
│   │   ├── starter_kit_options.md
│   │   ├── office_locations.md
│   │   └── ...
│   ├── scripts/                    # Document ingestion for RAG
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/             # React UI components (Shadcn)
│       ├── hooks/                  # useSpeechToText, useWebSocket
│       ├── services/               # API clients
│       └── pages/                  # Login, Register, Chat
├── orbio/                          # Assignment documentation
│   ├── ORBIO_GENERAL_PLAN.md
│   └── 01-05 feature planning docs
├── doc/                            # Technical documentation
│   ├── general/                    # API.md, ARCHITECTURE.md, DEVELOPMENT.md
│   └── features/                   # Feature analysis docs
└── docker-compose.yml
```

## 🚧 Potential Improvements

### Short-term (Next Sprint)

1. **Enhanced Validation**
   - Add more sophisticated validation rules for employee IDs
   - Implement regex patterns for common field formats
   - Provide clearer error messages with examples

2. **Sentiment Analysis**
   - Detect user frustration or confusion
   - Automatically escalate to human support if needed
   - Track sentiment metrics across conversations

3. **Multi-language Support**
   - Add i18n for UI and bot responses
   - Support Spanish, French, German for global teams
   - Auto-detect language preference

4. **Google Calendar Integration**
   - Implement MCP tool for calendar scheduling
   - Automatically create welcome meeting events
   - Send calendar invites to manager and new hire

### Medium-term (Next Quarter)

5. **Enhanced RAG**
   - Increase knowledge base to 50+ documents
   - Add document versioning and updates
   - Implement hybrid search (keyword + semantic)
   - Add citation tracking for source attribution

6. **Analytics Dashboard**
   - Track onboarding completion rates
   - Monitor average conversation length
   - Identify common questions and pain points
   - A/B test different prompts

7. **Voice Output (TTS)**
   - Add text-to-speech for bot responses
   - Fully voice-driven onboarding experience
   - Support multiple voice options

8. **Workflow Automation**
   - Trigger IT provisioning based on starter kit choice
   - Send automated emails to relevant departments
   - Create tasks in project management tools

### Long-term (Roadmap)

9. **Advanced Agent Capabilities**
   - Multi-agent system (separate agents for IT, HR, scheduling)
   - Tool calling for external APIs (Slack, Jira, etc.)
   - Proactive follow-ups (check-in messages on day 1, week 1, month 1)

10. **Scalability Enhancements**
    - Migrate to production vector DB (Pinecone, Weaviate)
    - Implement caching layer for common RAG queries
    - Add Redis for session management
    - Horizontal scaling with Kubernetes

11. **Compliance & Security**
    - Add audit logging for all data access
    - Implement data retention policies
    - GDPR compliance features (data export, deletion)
    - Role-based access control (RBAC)

12. **Personalization**
    - Learn from past conversations to improve responses
    - Customize onboarding flow based on role/department
    - Adaptive prompts based on user expertise level

## 🧪 Testing

The project includes comprehensive test coverage:

- **Unit Tests** (14 files): Domain models, use cases, tools, LLM providers
- **Integration Tests** (6 files): API endpoints, graph workflows, RAG pipeline
- **End-to-End**: Manual UI testing

Run tests locally:

```bash
cd backend
pytest tests/ -v
```

## 📚 Documentation

Additional documentation is available in the `doc/` directory:

- **API Reference**: `doc/general/API.md`
- **Architecture Guide**: `doc/general/ARCHITECTURE.md`
- **Development Guide**: `doc/general/DEVELOPMENT.md`
- **Deployment Guide**: `doc/general/DEPLOYMENT.md`

Assignment-specific documentation:

- **Planning Documents**: `orbio/` directory
- **Feature Analysis**: `doc/features/` directory

## 🤖 Development Workflow

This project follows a structured AI-assisted development workflow.

The `.claude` directory contains specialized analyzer agents that explore the codebase from different perspectives (backend architecture, frontend, security, testing, etc.) before implementation begins. This ensures thorough understanding and planning before code changes.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Built with** ❤️ **using LangGraph, FastAPI, React, and Claude Code**
