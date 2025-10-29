# Feature 5: Frontend & Speech-to-Text

## Overview
Update the chat UI to support the onboarding flow and add speech-to-text capability so users can speak their responses using a microphone button.

## Key Components
- **Chat UI Updates**:
  - Dedicated onboarding chat interface (or adapt existing chat component)
  - Display conversation history clearly
  - Show agent's reasoning/thinking process (for demo purposes)
  - Clear indication when onboarding is complete
- **Speech-to-Text**:
  - Mic icon button next to text input
  - Uses browser Web Speech API for simplicity
  - Record audio, convert to text
  - User can review and edit transcribed text before sending
  - Keep implementation simple (no advanced audio processing)
- **Backend Integration**:
  - Wire UI to onboarding graph endpoint
  - Handle streaming responses if needed
  - Display tool usage and agent reasoning

## Success Criteria
- User can complete onboarding through the UI
- Speech-to-text button works reliably in modern browsers
- Transcribed text appears in input field for review
- Agent messages and reasoning displayed clearly
- End-to-end flow works from frontend to backend
