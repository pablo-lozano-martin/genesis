# Feature 2: RAG System

## Overview
Create a knowledge base of company information and implement retrieval capabilities so the agent can proactively answer questions about policies, benefits, and onboarding details.

## Key Components
- **Sample Company Documents**: Create mock documents covering:
  - Company benefits and perks policies
  - Starter kit options (mouse, keyboard, backpack) with descriptions
  - Office locations and parking information
  - IT setup guidelines
  - Dress code and culture information
- **Vector Store Setup**: Use existing Genesis MongoDB infrastructure for document storage and retrieval
- **rag_search Tool**: Implement tool for semantic search over company documents
- **Proactive Usage**: Agent should use RAG when user asks questions or when context is helpful

## Success Criteria
- 5-10 sample documents created with realistic company information
- Documents successfully ingested into vector store
- rag_search tool returns relevant results for test queries
- Tool integrated with agent and callable during conversations
