# Feature 4: Conversation Summary & Export

## Overview
After all onboarding information is collected, generate an LLM-powered summary of the conversation and export the complete onboarding data to a JSON file for the assignment deliverable.

## Key Components
- **Summary Generation**:
  - Triggered after all required fields are collected
  - LLM generates concise summary of conversation and key points
  - Summary saved to state.conversation_summary field
- **JSON Export**:
  - Export complete state to structured JSON file
  - Include all onboarding fields (name, ID, starter kit, dietary restrictions, meeting status)
  - Include conversation summary
  - Include full message history for reference
  - Save to disk with unique filename (conversation_id or timestamp)
- **End-to-End Workflow**: Complete onboarding flow from start to JSON export

## Success Criteria
- Summary accurately reflects conversation highlights
- JSON file contains all required data in structured format
- Export works reliably after conversation completion
- File saved to appropriate location for assignment review
