# React Frontend Analysis

## Request Summary
Add speech-to-text input capability for chat messages. Users should be able to click a microphone button to record audio, which will be transcribed and inserted into the message input field.

## Relevant Files & Modules

### Files to Examine

#### Core Chat Components
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/MessageInput.tsx` - Simple textarea component with send button - PRIMARY TARGET for adding microphone button
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/MessageList.tsx` - Displays messages with auto-scroll, uses ToolExecutionCard for tool executions
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/ConversationSidebar.tsx` - Manages conversation list with create/delete/rename actions
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/MarkdownMessage.tsx` - Renders assistant messages with markdown support
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/ToolExecutionCard.tsx` - Shows tool execution status using lucide-react icons (Check, Loader2)

#### Pages
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/pages/Chat.tsx` - Main chat page that orchestrates all chat components, provides layout structure

#### State Management & Hooks
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/contexts/ChatContext.tsx` - Chat context managing conversation/message state and WebSocket integration
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/contexts/AuthContext.tsx` - Authentication state management
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/hooks/useWebSocket.ts` - Custom hook for WebSocket connection, message sending, and streaming

#### Services
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/services/conversationService.ts` - REST API service for CRUD operations on conversations and messages
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/services/websocketService.ts` - WebSocket service for real-time chat
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/services/authService.ts` - Authentication service
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/services/axiosConfig.ts` - Axios configuration for HTTP requests

#### UI Components
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/ui/badge.tsx` - Badge component using class-variance-authority for variants
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/ui/card.tsx` - Card components (Card, CardHeader, CardContent, etc.)

#### Utilities
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/lib/utils.ts` - Utility functions including `cn()` for className merging (clsx + tailwind-merge)
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/lib/titleUtils.ts` - Title generation utilities

#### Types
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/types/auth.ts` - Authentication type definitions

#### Configuration
- `/Users/pablolozano/Mac Projects August/genesis/frontend/package.json` - Dependencies include lucide-react for icons, axios for HTTP, react-markdown for rendering

### Key Components & Hooks

#### MessageInput Component
- **Location:** `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/MessageInput.tsx`
- **Lines 1-50:** Complete component
- **Props:**
  - `onSend: (content: string) => void` - Callback to send message
  - `disabled?: boolean` - Disables input when not connected or streaming
- **State:**
  - `input` - Local state for textarea value
- **Key Methods:**
  - `handleSend()` (lines 15-19) - Validates, calls onSend, clears input
  - `handleKeyDown()` (lines 21-26) - Sends on Enter, allows Shift+Enter for newlines
- **UI Structure:**
  - Flex container with gap-2
  - Textarea (flex-1) with border, rounded-lg styling
  - Send button with blue background, disabled states

#### Chat Page
- **Location:** `/Users/pablolozano/Mac Projects August/genesis/frontend/src/pages/Chat.tsx`
- **Lines 73-76:** MessageInput usage - passes `sendMessage` from ChatContext and `disabled` based on connection/streaming state
- **Layout:** Full-screen flex column with header, sidebar, and main chat area

#### ChatContext
- **Location:** `/Users/pablolozano/Mac Projects August/genesis/frontend/src/contexts/ChatContext.tsx`
- **Lines 178-204:** `sendMessage()` function - adds user message to state, triggers WebSocket send, auto-names conversation
- **State Management:**
  - `messages` - Array of Message objects
  - `streamingMessage` - Current streaming content from assistant
  - `isStreaming` - Boolean flag for streaming state
  - `isConnected` - WebSocket connection status
  - `toolExecutions` - Array of tool execution states
- **WebSocket Integration:** Uses `useWebSocket` hook with callbacks for tool execution

## Current Architecture Overview

### Pages & Routing
The application uses React Router with three main routes:
- `/login` - Login page
- `/register` - Register page
- `/chat` - Protected chat interface (requires authentication)

The `Chat` page is wrapped in `ProtectedRoute` and `ChatProvider`, providing authentication and chat state to all child components.

### State Management

#### Context API Pattern
The application uses React Context API for state management with two primary contexts:

1. **AuthContext** (`/Users/pablolozano/Mac Projects August/genesis/frontend/src/contexts/AuthContext.tsx`)
   - Manages user authentication state (user, token, isAuthenticated, isLoading)
   - Provides login, register, and logout methods
   - Initialized in App.tsx, wraps entire application

2. **ChatContext** (`/Users/pablolozano/Mac Projects August/genesis/frontend/src/contexts/ChatContext.tsx`)
   - Manages conversation and message state
   - Integrates WebSocket for real-time streaming
   - Handles tool execution tracking
   - Provides methods: loadConversations, createConversation, selectConversation, deleteConversation, sendMessage, updateConversationTitle

#### Component-Level State
Individual components use local `useState` for UI-specific state:
- `MessageInput`: `input` state for textarea value
- `ConversationSidebar`: `editingId` and `editValue` for inline title editing
- `MessageList`: No local state, purely presentational with auto-scroll via `useRef`

### Data Fetching

#### REST API Pattern
- **Service Layer:** Dedicated service classes for API calls (conversationService, authService)
- **Axios Integration:** HTTP client configured in axiosConfig.ts
- **Authentication:** Bearer token passed in headers via `getAuthHeaders()` method
- **Endpoints:**
  - `GET /api/conversations` - List conversations
  - `POST /api/conversations` - Create conversation
  - `GET /api/conversations/:id` - Get single conversation
  - `PATCH /api/conversations/:id` - Update conversation
  - `DELETE /api/conversations/:id` - Delete conversation
  - `GET /api/conversations/:id/messages` - Get messages for conversation

#### WebSocket Pattern
- **Service:** WebSocketService class handles connection lifecycle
- **Hook:** `useWebSocket` custom hook provides React integration
- **Real-time Streaming:** Token-by-token streaming of assistant responses
- **Event Handlers:**
  - `onConnect` - Connection established
  - `onDisconnect` - Connection lost
  - `onToken` - Streaming token received
  - `onComplete` - Message complete
  - `onError` - Error occurred
  - `onToolStart` - Tool execution started
  - `onToolComplete` - Tool execution finished
- **URL:** WebSocket URL constructed from VITE_API_URL environment variable, replacing http with ws

### Custom Hooks

#### useWebSocket
- **Location:** `/Users/pablolozano/Mac Projects August/genesis/frontend/src/hooks/useWebSocket.ts`
- **Purpose:** Manages WebSocket connection state, message sending, and streaming reception
- **Returns:**
  - `isConnected` - Connection status
  - `error` - Error message if any
  - `sendMessage(conversationId, content)` - Send message function
  - `streamingMessage` - Current streaming message with conversationId, content, isComplete
  - `connect()` - Manual connect
  - `disconnect()` - Manual disconnect
- **Features:**
  - Auto-reconnect on disconnect
  - Ref-based service management for cleanup
  - Streaming state accumulation

#### useChat
- **Location:** `/Users/pablolozano/Mac Projects August/genesis/frontend/src/contexts/ChatContext.tsx` (lines 235-241)
- **Purpose:** Hook to access ChatContext
- **Returns:** All ChatContext values (conversations, messages, streaming state, methods)

#### useAuth
- **Location:** `/Users/pablolozano/Mac Projects August/genesis/frontend/src/contexts/AuthContext.tsx` (lines 100-106)
- **Purpose:** Hook to access AuthContext
- **Returns:** All AuthContext values (user, token, isAuthenticated, login, register, logout)

## Impact Analysis

### Components Affected

#### Primary Impact
**MessageInput.tsx** will require the most significant changes:
- Add microphone button next to Send button
- Add state for recording status (idle, recording, processing)
- Add state for audio blob storage
- Add handlers for start/stop recording
- Add transcription logic (either browser Web Speech API or backend API call)
- Insert transcribed text into textarea input state
- Handle loading/error states during transcription

#### Secondary Impact
**ChatContext.tsx** may need updates if:
- Transcription is handled via backend API (would need new service method)
- Audio files need to be uploaded for transcription (would affect message sending flow)
- Tool execution pattern should be used for transcription status (similar to current tool tracking)

#### Minimal/No Impact
- **MessageList.tsx** - No changes needed, displays messages as usual
- **ConversationSidebar.tsx** - No changes needed
- **Chat.tsx** - No changes needed unless we add global transcription settings
- **MarkdownMessage.tsx** - No changes needed

### Data Flow Changes

#### Current Message Flow
1. User types in MessageInput textarea
2. User presses Enter or clicks Send
3. MessageInput calls `onSend(content)` prop
4. Chat page passes this to `sendMessage` from ChatContext
5. ChatContext adds user message to local state immediately
6. ChatContext sends message via WebSocket
7. WebSocket streams back assistant response token by token
8. ChatContext updates `streamingMessage` state
9. MessageList displays streaming message with loading indicator
10. On completion, ChatContext loads full messages from backend

#### Proposed Speech-to-Text Flow
**Option A: Browser Web Speech API (simpler, no backend changes)**
1. User clicks microphone button
2. MessageInput starts browser recording via MediaRecorder API
3. Browser streams audio to Web Speech API (SpeechRecognition)
4. Interim results update textarea in real-time
5. User clicks stop or API auto-stops
6. Final transcript is set in textarea
7. User reviews and can edit before sending
8. Existing send flow continues from step 2 above

**Option B: Backend Transcription API (more robust, requires backend)**
1. User clicks microphone button
2. MessageInput starts browser recording via MediaRecorder API
3. User clicks stop
4. Audio blob is uploaded to backend transcription endpoint
5. Backend calls Whisper or similar STT service
6. Transcript is returned to frontend
7. MessageInput inserts transcript into textarea
8. User reviews and can edit before sending
9. Existing send flow continues from step 2 above

## React Architecture Recommendations

### Proposed Components

#### 1. Enhance MessageInput Component
**File:** `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/MessageInput.tsx`

**New State:**
```typescript
const [isRecording, setIsRecording] = useState(false);
const [isTranscribing, setIsTranscribing] = useState(false);
const [transcriptionError, setTranscriptionError] = useState<string | null>(null);
```

**New Refs:**
```typescript
const mediaRecorderRef = useRef<MediaRecorder | null>(null);
const recognitionRef = useRef<SpeechRecognition | null>(null);
```

**New Handlers:**
- `handleStartRecording()` - Initialize and start MediaRecorder/SpeechRecognition
- `handleStopRecording()` - Stop recording, finalize transcript
- `handleTranscriptionResult()` - Update input with transcript
- `handleTranscriptionError()` - Display error message

**UI Changes:**
- Add microphone button between textarea and send button
- Use `lucide-react` `Mic` icon (not recording) and `MicOff` or `Loader2` (recording/processing)
- Show visual recording indicator (pulsing red dot or border color change)
- Show error message below input if transcription fails
- Disable microphone button when `disabled` prop is true

#### 2. Optional: Create useSpeechToText Hook
**File:** `/Users/pablolozano/Mac Projects August/genesis/frontend/src/hooks/useSpeechToText.ts` (NEW)

**Purpose:** Extract speech-to-text logic into reusable hook for cleaner component code

**Interface:**
```typescript
interface UseSpeechToTextReturn {
  transcript: string;
  isRecording: boolean;
  isTranscribing: boolean;
  error: string | null;
  startRecording: () => void;
  stopRecording: () => void;
  resetTranscript: () => void;
}

function useSpeechToText(options?: {
  onTranscriptComplete?: (transcript: string) => void;
  continuous?: boolean;
  language?: string;
}): UseSpeechToTextReturn
```

**Benefits:**
- Separates concerns (UI vs. recording logic)
- Makes MessageInput easier to test
- Allows reuse if speech input is needed elsewhere
- Encapsulates browser API complexity

#### 3. Optional: Create SpeechToTextService
**File:** `/Users/pablolozano/Mac Projects August/genesis/frontend/src/services/speechToTextService.ts` (NEW)

**Purpose:** If using backend API for transcription, create service class following existing pattern

**Interface:**
```typescript
class SpeechToTextService {
  async transcribe(audioBlob: Blob): Promise<string>;
}
```

**Pattern:** Follows same structure as conversationService and authService with auth headers

### Proposed Hooks

#### useSpeechToText (Optional but Recommended)
See component section above for full details.

**Why Recommended:**
- Keeps MessageInput focused on UI concerns
- Easier to test recording logic in isolation
- Can mock hook in component tests
- Follows existing pattern of extracting complex logic (see useWebSocket)

**Implementation Approach:**
- Use browser's `SpeechRecognition` API (if Option A)
- Handle browser compatibility (check for webkit prefix)
- Manage MediaRecorder for audio capture
- Handle permissions requests
- Provide error handling for unsupported browsers
- Clean up listeners on unmount

### State Management Changes

#### No Context Changes Required (Option A)
If using browser Web Speech API, no changes to ChatContext are needed. All state is local to MessageInput or useSpeechToText hook.

#### Optional Context Changes (Option B)
If using backend transcription API, consider:

**Option 1: Add to ChatContext (NOT RECOMMENDED)**
- Would pollute chat concerns with transcription state
- Transcription is input-specific, not chat-wide state

**Option 2: Keep Local to MessageInput (RECOMMENDED)**
- Transcription state only matters while input is active
- No need to share across components
- Follows separation of concerns

**Option 3: Create TranscriptionContext (OVERKILL)**
- Only justified if multiple components need transcription
- Not the case for this feature

### Data Flow Diagram

#### Option A: Browser Web Speech API Flow
```
User Click Mic Button
        ↓
MessageInput: setIsRecording(true)
        ↓
Initialize SpeechRecognition API
        ↓
Request Microphone Permission
        ↓
User Grants Permission
        ↓
Start Recording & Recognition
        ↓
[Real-time] Recognition Results
        ↓
Update textarea with interim transcript
        ↓
User Clicks Stop OR Auto-Stop After Silence
        ↓
MessageInput: setIsRecording(false)
        ↓
Final transcript in textarea
        ↓
User Reviews/Edits
        ↓
User Clicks Send
        ↓
[Existing Flow] onSend(content) → ChatContext.sendMessage() → WebSocket
```

#### Option B: Backend API Transcription Flow
```
User Click Mic Button
        ↓
MessageInput: setIsRecording(true)
        ↓
Initialize MediaRecorder
        ↓
Request Microphone Permission
        ↓
User Grants Permission
        ↓
Start Recording (capture to Blob)
        ↓
User Clicks Stop
        ↓
MessageInput: setIsRecording(false), setIsTranscribing(true)
        ↓
Upload audioBlob to /api/transcribe
        ↓
Backend calls Whisper API
        ↓
Backend returns transcript
        ↓
MessageInput: setIsTranscribing(false)
        ↓
Insert transcript into textarea
        ↓
User Reviews/Edits
        ↓
User Clicks Send
        ↓
[Existing Flow] onSend(content) → ChatContext.sendMessage() → WebSocket
```

## Implementation Guidance

### Step-by-Step Approach

#### Phase 1: Assess Browser API Feasibility (Option A)
1. Research Web Speech API browser support (Chrome, Edge support well; Firefox/Safari limited)
2. Test SpeechRecognition API in target browsers
3. Evaluate accuracy and language support requirements
4. **Decision Point:** If browser support is acceptable, proceed with Option A. Otherwise, proceed with Option B.

#### Phase 2: Create useSpeechToText Hook (RECOMMENDED)
**File:** `/Users/pablolozano/Mac Projects August/genesis/frontend/src/hooks/useSpeechToText.ts`

1. Create hook file with ABOUTME comments
2. Define interface and return type
3. Implement state management (isRecording, transcript, error)
4. Implement SpeechRecognition initialization with browser compatibility checks
5. Add start/stop recording handlers
6. Add event listeners for results, errors, end events
7. Add cleanup in useEffect return
8. Handle microphone permissions
9. Add error handling for unsupported browsers

**Key Considerations:**
- Check for `window.SpeechRecognition || window.webkitSpeechRecognition`
- Set `recognition.continuous = true` for ongoing recognition
- Set `recognition.interimResults = true` for real-time updates
- Set `recognition.lang` based on user locale or setting
- Handle `onerror` events (no-speech, audio-capture, not-allowed)
- Clean up recognition instance on unmount

#### Phase 3: Update MessageInput Component
**File:** `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/MessageInput.tsx`

1. Import `useSpeechToText` hook and `Mic` icon from lucide-react
2. Use hook: `const { transcript, isRecording, error, startRecording, stopRecording } = useSpeechToText()`
3. Add useEffect to update input state when transcript changes
4. Add microphone button to UI between textarea and send button
5. Add button click handler (toggle recording on/off)
6. Add visual recording indicator (border color, icon change, pulsing animation)
7. Add error message display below input
8. Disable microphone button when component is disabled
9. Style button to match existing Send button pattern

**UI Structure:**
```tsx
<div className="border-t p-4">
  <div className="flex gap-2">
    <textarea {...existing props} />
    <button
      onClick={isRecording ? stopRecording : startRecording}
      disabled={disabled}
      className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 disabled:bg-gray-300 disabled:cursor-not-allowed"
    >
      {isRecording ? <Loader2 className="animate-spin" /> : <Mic />}
    </button>
    <button {...existing send button} />
  </div>
  {error && <div className="text-red-500 text-sm mt-2">{error}</div>}
</div>
```

#### Phase 4: Test & Refine
1. Test microphone permission flow
2. Test recording start/stop
3. Test transcript insertion and editing
4. Test error handling (permission denied, unsupported browser)
5. Test disabled state behavior
6. Test accessibility (keyboard navigation, screen readers)
7. Test on multiple browsers
8. Add loading states and user feedback
9. Consider adding tooltip or help text for first-time users

#### Phase 5: Optional Backend Integration (Option B)
**If browser API is insufficient:**

1. Create backend endpoint: `POST /api/transcribe`
2. Create SpeechToTextService class in `/Users/pablolozano/Mac Projects August/genesis/frontend/src/services/speechToTextService.ts`
3. Implement `transcribe(audioBlob)` method with auth headers
4. Update useSpeechToText hook to use service instead of browser API
5. Add upload progress indicator
6. Handle backend errors (timeout, service unavailable, quota exceeded)

### Following Existing Patterns

#### Icon Usage Pattern
- Import from `lucide-react` (see ToolExecutionCard.tsx line 7)
- Use `Mic` icon for idle state
- Use `Loader2` with `animate-spin` for processing state
- Consider `MicOff` for disabled/error state

#### Button Styling Pattern
- Match existing Send button style (blue background, rounded-lg, hover states)
- Use secondary style for microphone button (gray background to differentiate)
- Include disabled states with `disabled:bg-gray-300 disabled:cursor-not-allowed`
- Use Tailwind utility classes consistently

#### Error Handling Pattern
- Display errors below input (see Chat.tsx lines 60-64 for error display pattern)
- Use red color scheme (`text-red-500`, `bg-red-50`)
- Provide clear, user-friendly error messages
- Clear error on successful action

#### State Management Pattern
- Use local useState for component-specific state
- Use useRef for DOM references and service instances (see useWebSocket.ts)
- Don't add to Context unless state needs to be shared across components
- Clean up effects and listeners on unmount

#### Loading States Pattern
- Show loading indicator during async operations (see MessageList.tsx lines 70-74)
- Disable buttons during processing
- Provide visual feedback (spinning icon, pulsing animation)
- Maintain button size during state changes (use fixed dimensions if needed)

#### Service Layer Pattern
- Create service class with methods for API calls (see conversationService.ts)
- Use `getAuthHeaders()` method for authentication
- Use axios for HTTP requests
- Handle errors with try/catch and throw to caller
- Export singleton instance: `export const speechToTextService = new SpeechToTextService()`

## Risks and Considerations

### Browser Compatibility Risks
**Web Speech API Support:**
- **Chrome/Edge:** Full support for SpeechRecognition
- **Firefox:** Limited support, may require flags
- **Safari:** No support for SpeechRecognition API
- **Mobile:** Varying support across iOS/Android browsers

**Mitigation:**
- Feature detection: Check for API availability before showing microphone button
- Progressive enhancement: Show microphone only in supported browsers
- Fallback message: "Speech-to-text not supported in your browser"
- Consider backend Option B for universal support

### Microphone Permissions
**Permission Request UX:**
- Browser shows permission prompt on first recording attempt
- User may deny permission
- Permission state persists across sessions
- Different browsers have different permission UI

**Mitigation:**
- Show helpful message before first permission request
- Handle permission denial gracefully with clear error message
- Provide instructions to re-enable if previously denied
- Test permission request flow thoroughly

### Privacy and Security
**Audio Data Handling:**
- Browser Web Speech API sends audio to Google/Microsoft servers
- Users may have privacy concerns about audio transmission
- Audio is not stored locally by default
- Transcription accuracy may vary by accent/language

**Mitigation:**
- Add privacy notice or disclaimer about audio processing
- Don't store audio unless explicitly needed
- Use backend Option B if data sovereignty is required
- Consider adding user preference to enable/disable feature

### State Management Complexity
**Multiple Recording States:**
- Idle, requesting permission, recording, processing, error states
- Need to handle race conditions (rapid start/stop clicks)
- Need to clean up resources on unmount during recording

**Mitigation:**
- Use useRef for mutable values that don't trigger re-renders
- Implement proper cleanup in useEffect
- Add debouncing or button disabling during transitions
- Test edge cases (component unmount during recording)

### User Experience Considerations
**Transcript Accuracy:**
- Speech recognition may have errors
- Users need to review before sending
- Unclear words may result in gibberish
- Background noise affects accuracy

**Mitigation:**
- Always insert into textarea (not auto-send) so user can review/edit
- Show confidence indicators if available from API
- Provide clear visual feedback during recording
- Consider adding "retry" option for poor transcriptions

### Component Size and Responsibility
**MessageInput Complexity:**
- Adding recording logic significantly increases component responsibility
- Mixing UI and recording logic violates separation of concerns
- Makes testing more difficult

**Mitigation:**
- Extract logic into useSpeechToText hook (STRONGLY RECOMMENDED)
- Keep MessageInput focused on UI rendering
- Write separate tests for hook and component
- Document component responsibilities in ABOUTME comments

### Accessibility Concerns
**Keyboard Navigation:**
- Microphone button must be keyboard accessible
- Need keyboard shortcut to start/stop recording (optional enhancement)
- Screen readers need appropriate ARIA labels

**Mitigation:**
- Use semantic button element (not div with onClick)
- Add aria-label="Start recording" / "Stop recording"
- Add aria-live region for recording status announcements
- Test with screen readers (NVDA, JAWS, VoiceOver)
- Ensure focus management during state changes

## Testing Strategy

### Unit Tests

#### useSpeechToText Hook Tests
**File:** `/Users/pablolozano/Mac Projects August/genesis/frontend/src/hooks/useSpeechToText.test.ts` (NEW)

**Test Cases:**
1. Hook initialization returns correct default values
2. startRecording() creates SpeechRecognition instance
3. startRecording() requests microphone permission
4. stopRecording() stops recognition and finalizes transcript
5. Recognition results update transcript state
6. Recognition errors update error state
7. Cleanup function stops recognition on unmount
8. Unsupported browser returns appropriate error
9. Permission denied updates error state

**Mocking Strategy:**
- Mock window.SpeechRecognition with jest mock
- Mock navigator.mediaDevices.getUserMedia
- Mock permission API responses
- Use @testing-library/react-hooks for hook testing

#### MessageInput Component Tests
**File:** `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/MessageInput.test.tsx` (UPDATE EXISTING)

**New Test Cases:**
1. Microphone button renders when speech API is supported
2. Microphone button is hidden when speech API is not supported
3. Clicking microphone button starts recording
4. Clicking microphone button again stops recording
5. Transcript updates textarea value
6. Error message displays when transcription fails
7. Microphone button is disabled when component is disabled
8. Recording indicator shows during recording
9. User can edit transcribed text before sending
10. Send button works normally with transcribed text

**Mocking Strategy:**
- Mock useSpeechToText hook return values
- Test different hook states (recording, error, success)
- Verify button click handlers are called
- Verify UI updates based on hook state

### Integration Tests

#### Full Speech-to-Text Flow
**File:** `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/MessageInput.integration.test.tsx` (NEW)

**Test Cases:**
1. User clicks microphone, grants permission, records, stops, reviews, sends
2. User clicks microphone, denies permission, sees error
3. User records, transcript has errors, user edits, sends
4. User records, clicks send while recording (should stop first)
5. Connection lost during recording (should handle gracefully)

**Mocking Strategy:**
- Use real hook with mocked SpeechRecognition API
- Simulate permission flows
- Simulate recognition events
- Verify end-to-end state transitions

### End-to-End Tests

#### E2E Chat with Speech Input
**File:** `/Users/pablolozano/Mac Projects August/genesis/e2e/chat-speech-input.spec.ts` (NEW)

**Test Cases:**
1. User logs in, opens chat, uses speech-to-text, sends message
2. Speech-to-text works across conversation switches
3. Speech-to-text disabled during streaming response
4. Multiple speech inputs in single conversation

**Tools:**
- Playwright or Cypress for E2E testing
- Mock browser permissions
- Simulate audio input (if possible) or mock SpeechRecognition

### Manual Testing Checklist

#### Browser Compatibility
- [ ] Test on Chrome/Chromium (full support expected)
- [ ] Test on Edge (full support expected)
- [ ] Test on Firefox (limited support expected)
- [ ] Test on Safari (no support expected, verify graceful degradation)
- [ ] Test on mobile Chrome (Android)
- [ ] Test on mobile Safari (iOS)

#### Permission Scenarios
- [ ] First-time permission request shows browser prompt
- [ ] Permission granted allows recording
- [ ] Permission denied shows helpful error
- [ ] Previously denied permission can be re-enabled
- [ ] Permission state persists across page refreshes

#### Recording Scenarios
- [ ] Click to start recording shows visual indicator
- [ ] Click to stop recording stops indicator
- [ ] Audio is captured and transcribed
- [ ] Transcript appears in textarea
- [ ] User can edit transcript before sending
- [ ] Multiple recordings in sequence work correctly
- [ ] Recording during streaming is blocked

#### Error Scenarios
- [ ] Unsupported browser shows appropriate message
- [ ] No microphone available shows error
- [ ] Network error during transcription (if backend) shows error
- [ ] Background noise doesn't crash application
- [ ] Component unmount during recording cleans up properly

#### Accessibility
- [ ] Keyboard tab navigation reaches microphone button
- [ ] Enter key activates microphone button
- [ ] Screen reader announces recording state
- [ ] Focus management works during state changes
- [ ] Color contrast meets WCAG standards
- [ ] Visible focus indicators on all interactive elements

## Summary & Key Recommendations

### Primary Recommendation: Use Browser Web Speech API (Option A)

**Why:**
- Simpler implementation (no backend changes)
- Real-time transcription provides better UX
- Faster to implement and test
- Adequate browser support for primary use case (Chrome/Edge)

**Trade-offs:**
- Limited browser support (no Safari)
- Privacy concerns (audio sent to third-party servers)
- Less control over transcription quality

### Architecture Decisions

1. **Extract logic into useSpeechToText hook** (STRONGLY RECOMMENDED)
   - Keeps MessageInput component clean and focused
   - Easier to test and maintain
   - Follows existing pattern (see useWebSocket)

2. **Keep state local to MessageInput** (DO NOT use Context)
   - Transcription state is input-specific, not global
   - No need to share across components
   - Follows separation of concerns

3. **Use lucide-react icons** (FOLLOW EXISTING PATTERN)
   - Mic icon for idle state
   - Loader2 with spin for recording/processing
   - Matches existing ToolExecutionCard pattern

4. **Insert transcript into textarea, not auto-send** (CRITICAL UX)
   - Allows user to review and edit
   - Prevents sending errors from poor transcription
   - Follows principle of user control

### Implementation Priority

**Phase 1 (Essential):**
1. Create useSpeechToText hook with browser API
2. Update MessageInput with microphone button
3. Add basic error handling and loading states

**Phase 2 (Important):**
1. Add visual recording indicators
2. Improve error messages and user feedback
3. Add accessibility features (ARIA labels, keyboard support)

**Phase 3 (Nice-to-Have):**
1. Add backend transcription option for unsupported browsers
2. Add user preferences for language/dialect
3. Add keyboard shortcuts for recording
4. Add recording duration display

### Files to Create
1. `/Users/pablolozano/Mac Projects August/genesis/frontend/src/hooks/useSpeechToText.ts` - Speech recognition hook
2. `/Users/pablolozano/Mac Projects August/genesis/frontend/src/hooks/useSpeechToText.test.ts` - Hook unit tests
3. `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/MessageInput.integration.test.tsx` - Integration tests

### Files to Modify
1. `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/MessageInput.tsx` - Add microphone button and recording UI
2. `/Users/pablolozano/Mac Projects August/genesis/frontend/package.json` - No new dependencies needed (lucide-react already included)

### Files to Review (Optional Backend Path)
1. `/Users/pablolozano/Mac Projects August/genesis/frontend/src/services/speechToTextService.ts` - NEW if using backend API
2. Backend transcription endpoint (out of scope for this frontend analysis)

### Next Steps for Main Agent

1. **Decide on Option A vs Option B** based on browser support requirements and privacy constraints
2. **Review this analysis** and confirm architectural approach
3. **Implement useSpeechToText hook** following existing hook patterns
4. **Update MessageInput component** with microphone button and UI
5. **Write tests** for hook and component
6. **Test manually** across browsers and scenarios
7. **Document** any assumptions or limitations for users
