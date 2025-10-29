# Orbio Onboarding Chatbot - General Plan

## Assignment Overview

Build an MVP onboarding chatbot for Orbio that demonstrates solid LLM agent concepts and techniques. The goal is to showcase technical capabilities with the Genesis template, focusing on natural conversation flow, ReAct workflow patterns, and RAG integration.

**Timeline**: 1 day
**Approach**: MVP first, then enhancements

---

## Core Concept

A natural, conversational onboarding agent that:
- Collects employee information through free-form dialogue
- Proactively searches company knowledge base (RAG) when relevant
- Uses ReAct workflow to plan and execute multiple steps autonomously
- Feels like talking to a helpful HR person, not filling out a form

**Key Principle**: The user should never need to think about the app structure or logic - just have a natural conversation.

---

## Information to Collect

### Required Fields
- **Name**: Full name of the employee
- **ID**: Employee ID number
- **Starter Kit Choice**: One of: wireless mouse, keyboard, or backpack

### Optional Fields
- **Dietary Restrictions**: For office snacks/meals (optional)

---

## Technical Architecture

### 1. ReAct Agent Workflow
- **Framework**: LangGraph for agent orchestration
- **Pattern**: ReAct (Reasoning + Acting) workflow
  - Agent can make multiple steps in sequence
  - Fully aware of available tools and gathered information
  - Can reason about what info is missing and what tools to use
- **State Management**: Use LangGraph state to track collected information
- **Persistence**: Export final onboarding data to JSON file

### 2. RAG (Retrieval Augmented Generation)
- **Purpose**: Provide company information (policies, guidelines, FAQs)
- **Content**: Made-up company data (focus on demonstrating the workflow)
- **Behavior**: Agent should proactively search RAG when:
  - User asks questions about company policies
  - Information would be helpful in context
  - Clarification is needed about onboarding processes
- **Examples of RAG Content**:
  - Benefits and perks policies
  - Office locations and parking info
  - IT setup guidelines
  - Dress code and culture information
  - Starter kit details and options

### 3. Conversation Design
- **Style**: Natural, free-form conversation
- **No rigid forms**: Agent extracts information from natural dialogue
- **Context-aware**: Agent remembers what's been collected and what's missing
- **Proactive**: Agent guides conversation to ensure all required info is gathered

### 4. Data Validation & Storage Tools
- **Tool-based data management**: Agent uses structured tools to read/write data
- **read_data tool**: Agent can check what fields have been collected from state
- **write_data tool**: Agent writes data to LangGraph state with validation
  - Type validation using Instructor library pattern
  - Returns error if type is wrong, agent can retry
  - Updates state fields directly (employee_name, employee_id, etc.)
- **Structured output**: Ensures data integrity and proper formatting
- **Automatic persistence**: All state changes automatically saved to MongoDB via AsyncMongoDBSaver

### 5. Extended State Schema
- **Leverage existing infrastructure**: Genesis already uses AsyncMongoDBSaver for full checkpoint persistence
- **Extend ConversationState** with onboarding fields:
  - `employee_name: Optional[str]`
  - `employee_id: Optional[str]`
  - `starter_kit: Optional[str]` (mouse/keyboard/backpack)
  - `dietary_restrictions: Optional[str]`
  - `meeting_scheduled: Optional[bool]`
  - `conversation_summary: Optional[str]`
- **Zero extra persistence logic**: Checkpointer automatically saves entire state to MongoDB
- **Bonus**: Full conversation history already persisted with messages

### 6. Session Management
- **Simple approach**: Each new conversation = new onboarding session
- **No resume/edit**: Keep it simple for MVP
- **Persistence**: Automatic via existing MongoDB checkpointer
- **Final export**: JSON file export for assignment deliverable

### 7. Conversation Summary
- **Final step**: After all info is collected and calendar is scheduled
- **LLM-generated summary**: Overview of conversation and key points extracted
- **Saved to state**: Summary stored in `conversation_summary` field
- **Included in JSON export**: Summary included in final output file

---

## Implementation Priorities

### Phase 1: Core Functionality (MUST HAVE)
1. **Extended State Schema**
   - Add onboarding fields to ConversationState
   - Fields: employee_name, employee_id, starter_kit, dietary_restrictions, meeting_scheduled, conversation_summary
   - Automatic MongoDB persistence via existing checkpointer (no extra work needed)

2. **Data Validation Tools** (using Instructor library pattern)
   - `read_data` tool: Query currently collected fields from state
   - `write_data` tool: Write field to state with type validation
     - Parameters: field name, value, optional comments
     - Returns error if type validation fails
     - Agent can retry on validation errors
     - Updates state directly, auto-persisted to MongoDB

3. **ReAct Agent Setup**
   - Create new LangGraph workflow for onboarding (separate from chat)
   - ReAct pattern with reasoning and action steps
   - Tool calling capability (read_data, write_data, rag_search)

4. **Information Collection**
   - Natural conversation flow
   - Extract: name, ID, starter kit choice, dietary restrictions
   - Validation and confirmation of collected data using write_data tool

5. **RAG Integration**
   - Vector store setup (using existing Genesis infrastructure)
   - Sample company documents (benefits, policies, starter kit info, etc.)
   - Tool for querying company knowledge base
   - Agent proactively uses RAG when relevant

6. **Conversation Summary**
   - Final step after all info collected
   - LLM generates summary of conversation and key points
   - Save to state.conversation_summary field

7. **JSON Export**
   - Export final onboarding data from state to JSON file
   - Include all fields + conversation summary
   - Save to disk for assignment deliverable

8. **Frontend**
   - Chat interface using existing Genesis UI components
   - Display conversation history
   - **Speech-to-text**: Mic icon to record audio, convert to text, user can then send
     - Keep implementation simple (use browser Web Speech API)
   - Show agent's reasoning/thinking process (for demo purposes)

### Phase 2: Enhancements (NICE TO HAVE)
1. **Google Calendar Integration (via MCP)**
   - Tool for calendar access
   - Simple flow: ask user for preferred time tomorrow
   - Create onboarding interview meeting
   - Confirm meeting details with user

2. **Additional Polish** (if time permits)
   - Admin view to see all onboarding submissions
   - Better error messages and edge case handling

---

## Technical Stack (Leveraging Genesis Template)

- **Backend**: FastAPI (Python)
- **Agent Framework**: LangGraph with ReAct pattern
- **LLM Provider**: OpenAI/Anthropic (existing Genesis setup)
- **Persistence**: AsyncMongoDBSaver (full checkpoint persistence to MongoDB)
- **Vector Store**: MongoDB (existing Genesis setup for RAG)
- **Data Validation**: Instructor library for structured tool outputs
- **Speech-to-Text**: Browser Web Speech API
- **Frontend**: React + Shadcn UI (existing Genesis setup)
- **State Management**: Extended ConversationState (auto-persisted) + JSON export

---

## Success Criteria

### Core Requirements (Assignment Must-Haves)
- ✅ Natural conversational flow with context management
- ✅ Information extraction into structured format (JSON)
- ✅ Data validation with error handling (Instructor-based tools)
- ✅ Conversation summary with key points
- ✅ RAG integration with company knowledge base
- ✅ Speech-to-text capability (mic icon)

### Technical Demonstration
- ✅ ReAct workflow with multi-step reasoning
- ✅ LangGraph state management
- ✅ Structured tool usage (read_data/write_data)
- ✅ Clean, maintainable code following Genesis patterns
- ✅ Comprehensive tests

### User Experience
- ✅ Feels like natural conversation, not a form
- ✅ Agent proactively helps and guides
- ✅ Handles questions about company policies (RAG)
- ✅ Graceful error handling for invalid inputs
- ✅ Clear confirmation of collected data

### Bonus/Stretch Goals
- ✅ Google Calendar integration working
- ✅ Show agent reasoning for technical demonstration

---

## Documentation & Deliverables

### README Requirements (Assignment Deliverable)
Must include the following sections:

1. **Setup Instructions**
   - Environment setup (Python, dependencies)
   - Configuration (API keys, environment variables)
   - How to run the application (backend + frontend)
   - How to run tests

2. **System Architecture Overview**
   - High-level architecture diagram or description
   - Component breakdown (Agent, RAG, Tools, Frontend, Backend)
   - Data flow explanation
   - Technology stack used

3. **Key Design Decisions**
   - Why LangGraph for agent orchestration
   - Why ReAct pattern for workflow
   - Tool design rationale (read_data/write_data validation)
   - RAG implementation approach
   - State management choices

4. **Potential Improvements**
   - Scalability considerations
   - Production-ready enhancements
   - Additional features that could be added
   - Performance optimizations

### Sample Conversations (Assignment Deliverable)
- Create 2-3 sample conversation demos showing:
  - Basic happy path (user provides all info smoothly)
  - User asking questions about policies (RAG usage)
  - User providing invalid data (validation/error handling)
- Can be saved as text files or included in README

---

## Development Approach

1. **Extend state schema**: Add onboarding fields to ConversationState (persists automatically)
2. **Data validation tools**: Implement read_data and write_data tools with Instructor
3. **ReAct agent graph**: Create onboarding graph with tool calling
4. **Information collection**: Natural conversation flow with data validation
5. **RAG integration**: Knowledge base setup and proactive search
6. **Conversation summary**: Generate summary after data collection
7. **JSON export**: Export state to JSON file for deliverable
8. **Frontend & speech-to-text**: Chat UI with mic icon for audio input
9. **Calendar integration**: Add after core is solid (Phase 2)
10. **Documentation**: Write comprehensive README with sample conversations
11. **Testing**: Ensure all functionality works end-to-end

---

## Notes

- Focus on demonstrating **concepts and techniques** over polish
- The existing Genesis architecture + Claude Code workflow already demonstrates technical sophistication
- Keep it simple where possible - this is an MVP to showcase capabilities
- Each conversation is independent (no multi-session persistence for MVP)

### Key Infrastructure Advantages

**Persistence Made Easy**: Genesis already has full LangGraph checkpoint persistence to MongoDB via `AsyncMongoDBSaver`. This means:
- ✅ Zero extra persistence logic needed - just extend the state schema
- ✅ All state changes automatically saved to MongoDB
- ✅ Full conversation history persisted with messages
- ✅ Can easily export state to JSON for assignment deliverable
- ✅ Shows production-ready architecture (not just in-memory persistence)

## Assignment Alignment

This plan addresses all core assignment requirements:
- ✅ Conversational flow with natural dialogue
- ✅ Information collection and extraction to structured JSON format
- ✅ Data validation with error handling (Instructor-based tools)
- ✅ Context management throughout interaction (LangGraph state)
- ✅ Conversation summary generation
- ✅ **Bonus**: RAG implementation with company knowledge base
- ✅ **Bonus**: Multi-turn conversation memory (LangGraph state)
- ✅ **Bonus (Stretch)**: Google Calendar integration via MCP

All deliverables covered:
- ✅ Source code in Git repository (already tracked)
- ✅ Comprehensive README (setup, architecture, design decisions, improvements)
- ✅ Sample conversations demonstrating capabilities
