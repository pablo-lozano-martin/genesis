# Issue #6: LangGraph-First Architecture with Two-Database Pattern

## Analysis Documents

This folder contains comprehensive analysis for implementing a LangGraph-first architecture with separate databases for application metadata and LangGraph checkpoints.

### Documents

1. **data_flow.md** (57KB, 1633 lines)
   - Complete data flow analysis
   - Current architecture problems identified
   - New architecture design with two-database pattern
   - All affected files with absolute paths
   - Data transformations and boundaries
   - Consistency patterns and failure scenarios
   - Comprehensive testing strategy
   - 10-phase implementation plan
   - 8 major risks with mitigation strategies

### Quick Navigation

#### For Implementation Planning
- **Files to Review**: See "Relevant Files & Modules" section in data_flow.md
- **Implementation Phases**: See "Implementation Guidance: Phase-by-Phase" section
- **Timeline Estimates**: Each phase includes 2-day estimates
- **Dependency Order**: Phases sequenced to resolve dependencies first

#### For Architecture Understanding
- **Current Problems**: "Request Summary" and "Current Data Flow Overview" sections
- **New Architecture**: "Core Architecture Principle" and "Two-Database Setup" sections
- **Mapping Concept**: "Conversation.id ↔ thread_id Mapping" section
- **Design Rationale**: "Database Pattern: App DB vs LangGraph DB" section

#### For Testing & Quality
- **Test Strategy**: "Testing Strategy for Data Flows" section (10+ unit tests, 6+ integration tests, 3+ E2E tests)
- **Test Code Examples**: Complete Python test examples provided
- **Coverage Targets**: >80% overall coverage requirement
- **Failure Scenarios**: "Failure Scenarios & Recovery" section

#### For Risk Management
- **Risk Analysis**: "Risks and Considerations" section (8 major risks)
- **Mitigation Strategies**: Each risk includes concrete mitigation approach
- **Monitoring**: Specific alerts and metrics to track per risk
- **Data Migration**: Complete migration strategy for existing conversations

#### For Reference
- **File Changes Summary**: "Summary of Key Changes" section
  - 7 files to delete
  - 9 files to update (major)
  - 2 files to create
  - 5 files unchanged
- **Data Flow Comparison**: "Data Flow Comparison Table" section (14 aspects)

### Key Findings

**Problem Statement**
- LangGraph currently bypassed by WebSocket handler
- Manual message persistence ignores LangGraph checkpointer
- Missing advanced features: checkpointing, time-travel, human-in-the-loop

**Solution Architecture**
- Two databases: App DB (metadata) + LangGraph DB (AI state)
- Conversation.id maps to thread_id
- LangGraph owns conversation state
- Hexagonal architecture owns infrastructure

**Core Changes**
1. Remove message repository abstraction (manual persistence deleted)
2. Replace custom Message domain model with native HumanMessage/AIMessage
3. Use LangGraph's MessagesState instead of custom ConversationState
4. Call graph.astream() instead of llm_provider.stream() in WebSocket handler
5. Retrieve messages from graph.get_state() instead of repository query

**Timeline**: ~12 days (10 phases of 2 days each)
**Test Coverage**: >80% across unit, integration, and E2E tests
**Risk Level**: Medium (significant refactoring, but safe migration path provided)

### Starting Implementation

Before starting:
1. Read the complete data_flow.md document
2. Review the "Implementation Guidance" section
3. Check file paths (all absolute) against your system
4. Start with Phase 1: Infrastructure setup
5. Follow the phase sequence (dependencies are sequential)
6. Run tests after each phase to verify no regressions

### Document Structure

Each major section in data_flow.md includes:
- Clear problem/concept explanation
- Code examples (before/after where applicable)
- Specific file paths and line numbers
- Testing guidance
- Considerations and edge cases

### Questions to Answer During Implementation

**Before Phase 1**
- Do you have two MongoDB instances available (local dev)?
- Can you update docker-compose.yml with dual MongoDB URIs?
- Is the team comfortable with eventual consistency windows?

**During Implementation**
- What existing conversation data needs migration?
- Should checkpoints be archived after 90 days (TTL)?
- How many checkpoints per thread to keep in production?

**After Implementation**
- Is checkpoint size tracking in place?
- Are alerts configured for database independence failures?
- Is data migration script tested with real conversation data?

---

**Analysis Date**: October 25, 2025
**Issue**: #6 - Implement LangGraph-First Architecture with Two-Database Pattern
**Status**: Ready for Implementation
