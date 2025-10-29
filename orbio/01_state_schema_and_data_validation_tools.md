# Feature 1: State Schema & Data Validation Tools

## Overview
Extend the existing ConversationState to include onboarding-specific fields and implement structured tools for reading and writing data with validation.

## Key Components
- **Extended State Schema**: Add fields for employee_name, employee_id, starter_kit, dietary_restrictions, meeting_scheduled, and conversation_summary to ConversationState
- **read_data Tool**: Allow agent to query what fields have been collected from the current state
- **write_data Tool**: Allow agent to write validated data to state fields
  - Uses Instructor library pattern for type validation
  - Returns errors on invalid types, agent can retry
  - Updates state directly, automatically persisted via AsyncMongoDBSaver

## Success Criteria
- State schema extended with all required fields
- Tools implemented and integrated with LangGraph state
- Type validation working correctly (accepts valid data, rejects invalid)
- State changes persist to MongoDB automatically
- Agent can successfully read and write onboarding data during conversation
