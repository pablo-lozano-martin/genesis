# Feature 3: Onboarding Agent Graph

## Overview
Build a new LangGraph workflow specifically for onboarding conversations using the ReAct (Reasoning + Acting) pattern. The agent orchestrates tools to collect information naturally.

## Key Components
- **ReAct Pattern Implementation**: Agent reasons about what information is missing and what actions to take
- **Tool Orchestration**: Integrate read_data, write_data, and rag_search tools
- **Natural Conversation Flow**:
  - Agent initiates friendly onboarding conversation
  - Extracts information from user responses (not form-based)
  - Asks clarifying questions when needed
  - Proactively uses RAG to answer user questions
  - Confirms collected data before finalizing
- **Multi-step Reasoning**: Agent can plan and execute multiple tool calls in sequence
- **Context Awareness**: Agent knows what's been collected and what's still needed

## Success Criteria
- Separate onboarding graph created (not reusing chat graph)
- Agent successfully collects all required fields through natural dialogue
- Agent uses tools appropriately (reads state, writes validated data, searches RAG)
- Conversation feels natural, not like filling out a form
- Agent handles edge cases (invalid data, missing info, user questions)
