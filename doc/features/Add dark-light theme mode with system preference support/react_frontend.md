# React Frontend Analysis: Dark/Light Theme with System Preference Support

## Request Summary

Implement a dark/light theme mode with system preference detection. The feature requires:
- ThemeContext provider managing theme state ('light', 'dark', 'system')
- localStorage persistence for user preference
- System preference detection via `window.matchMedia('(prefers-color-scheme: dark)')`
- Dynamic class toggling on `<html>` element
- Settings toggle component in Chat header
- Theme support across all pages and chat components

## Relevant Files & Modules

### Files to Examine

**Core Context & Provider:**
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/contexts/AuthContext.tsx` - Existing context pattern to follow (state management, hook pattern, error handling)
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/contexts/ChatContext.tsx` - Existing context pattern for complex state and side effects

**Pages (all need theme support):**
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/pages/Chat.tsx` - Main chat page with header; theme toggle should be added to header
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/pages/Login.tsx` - Login page with light-themed form styling
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/pages/Register.tsx` - Registration page with light-themed form styling

**Chat Components (all need theme support):**
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/ConversationSidebar.tsx` - Sidebar with gray backgrounds and hover states
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/MessageList.tsx` - Message containers with blue/gray color scheme
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/MessageInput.tsx` - Input form with border and focus states
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/MarkdownMessage.tsx` - Markdown rendering with custom component styling
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/ToolExecutionCard.tsx` - Card component with colored borders and backgrounds

**App Entry Points:**
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/App.tsx` - Root component where ThemeProvider should wrap entire app
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/main.tsx` - React entry point
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/index.css` - Global Tailwind directives

**Configuration:**
- `/Users/pablolozano/Mac Projects August/genesis/frontend/tailwind.config.js` - Tailwind configuration (needs dark mode setup)
- `/Users/pablolozano/Mac Projects August/genesis/frontend/package.json` - Dependencies (no theme library currently installed)

### Key Components & Hooks

**Pages:**
- `Chat` in Chat.tsx - Main chat page; header at line 30 is where theme toggle UI should be added
- `Login` in Login.tsx - Auth page with centered form layout
- `Register` in Register.tsx - Auth page with centered form layout

**Chat Components:**
- `ConversationSidebar` in ConversationSidebar.tsx - Sidebar with conversation list (gray backgrounds, hover states)
- `MessageList` in MessageList.tsx - Message container (blue user messages, gray assistant messages)
- `MessageInput` in MessageInput.tsx - Text input and buttons
- `MarkdownMessage` in MarkdownMessage.tsx - Custom markdown rendering with hardcoded dark highlight.js styles
- `ToolExecutionCard` in ToolExecutionCard.tsx - Card with purple/blue colored borders and backgrounds

**Existing Contexts:**
- `AuthContext` / `useAuth()` in AuthContext.tsx - Pattern for context creation and hook pattern
- `ChatContext` / `useChat()` in ChatContext.tsx - Pattern for complex state management with multiple state slices
- `AuthProvider` - Wraps routes in App.tsx (provider hierarchy reference)
- `ChatProvider` - Wraps Chat page component (provider hierarchy reference)

## Current Architecture Overview

### App Structure & Provider Hierarchy

Current provider stack in App.tsx:
```
<BrowserRouter>
  <AuthProvider>
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/chat" element={
        <ProtectedRoute>
          <ChatProvider>
            <Chat />
          </ChatProvider>
        </ProtectedRoute>
      } />
    </Routes>
  </AuthProvider>
</BrowserRouter>
```

ThemeProvider should wrap AuthProvider to ensure theme is available on login/register pages before authentication. Placement in App.tsx should be:
```
<BrowserRouter>
  <ThemeProvider>
    <AuthProvider>
      ...
    </AuthProvider>
  </ThemeProvider>
</BrowserRouter>
```

### Pages & Routing

- **Login** (`/login`) - Centered card form with `bg-white`, `bg-gray-50` background
- **Register** (`/register`) - Centered card form with `bg-white`, `bg-gray-50` background
- **Chat** (`/chat`) - Full-height layout with header bar, sidebar, and message area
- **Protected Routes** - Chat page requires authentication via ProtectedRoute component

### State Management

**Pattern Analysis:**
Both AuthContext and ChatContext follow this pattern:
1. Create context with `createContext<Type | undefined>`
2. Create Provider component that:
   - Manages multiple state slices with `useState`
   - Uses `useEffect` for side effects (initialization, subscriptions)
   - Provides value object with state + methods
   - Returns `<Context.Provider value={value}>{children}</Context.Provider>`
3. Export custom hook `useContext()` that checks if context exists and throws error if not

**For ThemeContext, follow same pattern:**
- State: `theme` ('light' | 'dark' | 'system'), `systemPreference` (boolean for dark)
- Methods: `setTheme()` to update theme preference
- Side effects:
  - Initialize theme from localStorage
  - Listen to system preference changes with `matchMedia`
  - Update `<html>` element class
  - Persist preference to localStorage

### Data Fetching

Not applicable for theme feature. Theme is client-only state managed locally.

### Custom Hooks

**Existing hook patterns:**
- `useAuth()` - Checks context exists, returns context value
- `useChat()` - Checks context exists, returns context value
- `useSpeechToText()` - Custom hook with initialization and state management
- `useWebSocket()` - Custom hook with side effects and cleanup

**Recommendation:** Consider extracting system preference detection logic into a custom hook `useSystemPreference()` that returns current system dark preference and manages matchMedia listener:
```typescript
useSystemPreference(): boolean // true if system prefers dark
```

This can be used inside ThemeContext to decouple system preference detection logic.

### Component Styling Patterns

**Current styling approach:**
- All components use Tailwind CSS utility classes
- Color scheme is hardcoded: blue (`bg-blue-500`, `text-blue-500`), gray (`bg-gray-50`, `text-gray-600`), red/yellow for alerts
- Hardcoded class selectors like:
  - MessageList: `bg-blue-500 text-white` (user) vs `bg-gray-100 text-gray-900` (assistant)
  - ConversationSidebar: `bg-gray-50`, `hover:bg-gray-100`
  - Login/Register: `bg-gray-50` (page background), `bg-white` (form card)
  - MarkdownMessage: Imports `github-dark.css` for code highlighting

**Dark mode approach:**
Tailwind supports `dark:` prefix for dark mode variants. To implement:

1. **Enable dark mode in tailwind.config.js:**
   ```javascript
   darkMode: 'class',  // Use class strategy (not media query)
   ```

2. **Use Tailwind's dark: prefix for responsive styles:**
   ```jsx
   <div className="bg-white dark:bg-gray-900 text-gray-900 dark:text-white">
   ```

3. **Update MarkdownMessage to use light/dark highlight.js styles:**
   Currently imports only `github-dark.css`. Should conditionally import or provide fallback CSS.

4. **Dynamic class on html element:**
   Set `dark` class on `<html>` when dark mode is active. This enables all `dark:` Tailwind utilities.

### Existing Color Scheme Documentation

**Light mode (current):**
- Page backgrounds: `bg-gray-50` (off-white)
- Card backgrounds: `bg-white` (white)
- Text: `text-gray-900` (dark gray), `text-gray-600` (lighter gray)
- Borders: `border-gray-300`, `border-gray-100`
- Primary buttons: `bg-blue-500`, `hover:bg-blue-600`
- User messages: `bg-blue-500 text-white`
- Assistant messages: `bg-gray-100 text-gray-900`
- Alerts: `bg-red-50 text-red-600`, `bg-yellow-50 text-yellow-600`

**Dark mode recommendations:**
- Page backgrounds: `dark:bg-gray-950` or `dark:bg-gray-900` (very dark)
- Card backgrounds: `dark:bg-gray-800` (dark gray)
- Text: `dark:text-white`, `dark:text-gray-300`
- Borders: `dark:border-gray-700`
- Primary buttons: `dark:bg-blue-600`, `dark:hover:bg-blue-700`
- User messages: `dark:bg-blue-600` (slightly darker blue for contrast)
- Assistant messages: `dark:bg-gray-700` (dark gray)
- Alerts: `dark:bg-red-900 dark:text-red-200`, `dark:bg-yellow-900 dark:text-yellow-200`

## Impact Analysis

### Pages Affected

**All pages need theme support (currently hardcoded colors):**

1. **Chat.tsx** (line 30-40):
   - Header bar: `bg-white` → needs dark mode variant
   - Text colors: `text-gray-600` → needs dark mode variant
   - **Also needs theme toggle UI** in header (recommended placement: next to Logout button)

2. **Login.tsx** (line 32, 33):
   - Page background: `bg-gray-50` → needs dark mode variant
   - Card background: `bg-white` → needs dark mode variant
   - Text: `text-gray-600` → needs dark mode variant

3. **Register.tsx** (line 34, 35):
   - Page background: `bg-gray-50` → needs dark mode variant
   - Card background: `bg-white` → needs dark mode variant
   - Text: `text-gray-600` → needs dark mode variant

### Chat Components Affected

**All components have hardcoded colors:**

1. **ConversationSidebar.tsx** (line 60, 74-75):
   - Background: `bg-gray-50` → `dark:bg-gray-900`
   - Hover: `hover:bg-gray-100` → `dark:hover:bg-gray-800`
   - Borders: `border-gray-100` → `dark:border-gray-700`

2. **MessageList.tsx** (line 25, 38-42):
   - Container background: needs dark mode
   - User message: `bg-blue-500 text-white` → `dark:bg-blue-600` (maintain contrast)
   - Assistant message: `bg-gray-100 text-gray-900` → `dark:bg-gray-700 dark:text-white`
   - Placeholder text: `text-gray-400` → `dark:text-gray-500`

3. **MessageInput.tsx** (line 43, 51):
   - Border: `border-gray-300` → `dark:border-gray-600`
   - Background: `disabled:bg-gray-100` → `dark:disabled:bg-gray-800`
   - Text color in button: needs dark mode

4. **MarkdownMessage.tsx** (line 8, custom styles):
   - Currently imports hardcoded `github-dark.css`
   - Inline code: `bg-gray-200 text-gray-800` → needs dark mode (`dark:bg-gray-700 dark:text-gray-200`)
   - Links: `text-blue-600 hover:text-blue-800` → `dark:text-blue-400 dark:hover:text-blue-300`
   - Tables: `bg-gray-100` → `dark:bg-gray-800`
   - Blockquote: `border-gray-300 bg-gray-50` → `dark:border-gray-600 dark:bg-gray-800`
   - **Critical issue:** Line 8 imports only `github-dark.css`. In dark mode, this is correct. In light mode, should import `github-light.css` instead. Solution: conditionally import based on theme or use CSS that works for both.

5. **ToolExecutionCard.tsx** (line 18):
   - Background: `bg-purple-50/50`, `bg-blue-50/50` → needs dark mode
   - Borders: `border-l-purple-500`, `border-l-blue-500` → may need adjustment for contrast
   - Text colors in badges → needs dark mode

6. **UI Components** (Card, Badge in ToolExecutionCard):
   - Card styling likely uses default Tailwind styling
   - Badge styling uses `variant="outline"`, `variant="secondary"` - implementation needs checking

### State Dependencies

The following components depend on theme state indirectly (through class on html):
- All components using `dark:` Tailwind utilities
- MarkdownMessage which needs conditional CSS import based on theme

Direct consumers of ThemeContext (need `useTheme()` hook):
- Chat.tsx - to display theme toggle button and get current theme
- MarkdownMessage.tsx - to conditionally load highlight.js CSS or provide fallback
- Any component that needs to know theme to conditionally render something (e.g., icons)

### Component Relationships

```
App.tsx
├── BrowserRouter
├── ThemeProvider  [NEW - wraps everything]
│   └── provides useTheme() to all descendants
└── AuthProvider
    ├── Routes
    │   ├── /login → Login.tsx
    │   │   └── uses inherited theme via Tailwind dark: classes
    │   ├── /register → Register.tsx
    │   │   └── uses inherited theme via Tailwind dark: classes
    │   └── /chat → ProtectedRoute → ChatProvider → Chat.tsx
    │       ├── Chat header [NEW - theme toggle button goes here]
    │       ├── ConversationSidebar.tsx
    │       │   └── uses inherited theme
    │       └── MessageList.tsx
    │           ├── MessageInput.tsx
    │           │   └── uses inherited theme
    │           └── MarkdownMessage.tsx
    │               └── needs useTheme() for conditional CSS import
    └── ToolExecutionCard.tsx
        └── uses inherited theme
```

## React Architecture Recommendations

### 1. Create ThemeContext and ThemeProvider

**File to create:** `/Users/pablolozano/Mac Projects August/genesis/frontend/src/contexts/ThemeContext.tsx`

**Type Definition:**
```typescript
type ThemeMode = 'light' | 'dark' | 'system';

interface ThemeContextType {
  theme: ThemeMode;              // User's selected theme
  effectiveTheme: 'light' | 'dark';  // Actual theme being used (resolves 'system')
  setTheme: (theme: ThemeMode) => void;
}
```

**Provider Implementation:**
- Manage `theme` state (persisted to localStorage)
- Calculate `effectiveTheme` based on `theme` + system preference
- Set `dark` class on `<html>` element when `effectiveTheme` is 'dark'
- Listen to system preference changes with `matchMedia` listener
- Cleanup listener on unmount
- Initialize from localStorage on mount

**Hook:**
```typescript
export const useTheme = (): ThemeContextType => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
};
```

### 2. Create useSystemPreference Hook (optional)

**File to create:** `/Users/pablolozano/Mac Projects August/genesis/frontend/src/hooks/useSystemPreference.ts`

Encapsulate system preference detection logic:
```typescript
export const useSystemPreference = (): boolean => {
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

    // Set initial value
    setIsDark(mediaQuery.matches);

    // Listen for changes
    const handler = (e: MediaQueryListEvent) => setIsDark(e.matches);
    mediaQuery.addEventListener('change', handler);

    return () => mediaQuery.removeEventListener('change', handler);
  }, []);

  return isDark;
};
```

This keeps ThemeContext focused on theme state management while logic is separate.

### 3. Update Tailwind Configuration

**File to modify:** `/Users/pablolozano/Mac Projects August/genesis/frontend/tailwind.config.js`

Add dark mode configuration:
```javascript
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',  // Enable class-based dark mode
  theme: {
    extend: {},
  },
  plugins: [],
}
```

Setting `darkMode: 'class'` enables Tailwind's `dark:` prefix utilities. When `dark` class is on `<html>`, all `dark:` variants activate.

### 4. Wrap App with ThemeProvider

**File to modify:** `/Users/pablolozano/Mac Projects August/genesis/frontend/src/App.tsx`

Update provider hierarchy:
```typescript
import { ThemeProvider } from "./contexts/ThemeContext";

function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <AuthProvider>
          {/* existing routes */}
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}
```

Placement is important: ThemeProvider should wrap AuthProvider so theme is available on login/register pages.

### 5. Create Theme Toggle Component (optional)

**File to create:** `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/ThemeToggle.tsx`

Small component for the Chat header:
```typescript
import { useTheme } from "../contexts/ThemeContext";
import { Moon, Sun } from "lucide-react";

export const ThemeToggle: React.FC = () => {
  const { theme, effectiveTheme, setTheme } = useTheme();

  // Cycle through: light → dark → system → light
  const handleToggle = () => {
    const themes: ThemeMode[] = ['light', 'dark', 'system'];
    const currentIndex = themes.indexOf(theme);
    const nextIndex = (currentIndex + 1) % themes.length;
    setTheme(themes[nextIndex]);
  };

  return (
    <button
      onClick={handleToggle}
      aria-label={`Theme: ${theme}`}
      className="p-2 rounded hover:bg-gray-100 dark:hover:bg-gray-700"
    >
      {effectiveTheme === 'dark' ? (
        <Moon className="h-5 w-5" />
      ) : (
        <Sun className="h-5 w-5" />
      )}
    </button>
  );
};
```

**Usage in Chat.tsx** (line 32, in header gap-4):
```typescript
<div className="flex items-center gap-4">
  <ThemeToggle />
  <div className="text-sm text-gray-600 dark:text-gray-400">{user?.username}</div>
  <button /* logout */ />
</div>
```

### 6. Update MarkdownMessage Component

**File to modify:** `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/MarkdownMessage.tsx`

**Current issue:** Line 8 imports only `github-dark.css`. This is incorrect for light mode.

**Solution options:**

**Option A: Conditional import (recommended)**
```typescript
import { useTheme } from "../../contexts/ThemeContext";

export function MarkdownMessage({ content }: MarkdownMessageProps) {
  const { effectiveTheme } = useTheme();

  useEffect(() => {
    // Conditionally load CSS
    if (effectiveTheme === 'dark') {
      import('highlight.js/styles/github-dark.css');
    } else {
      import('highlight.js/styles/github-light.css');
    }
  }, [effectiveTheme]);

  // rest of component
}
```

**Option B: Load both and let CSS specificity handle it** (simpler)
Keep both CSS imports at top level and let dark mode CSS override:
```typescript
import 'highlight.js/styles/github-light.css';
// Then in a separate dark.css file, import dark version with !important or higher specificity
```

**Option C: Provide custom CSS that supports both themes**
Create custom styling for code blocks that uses CSS variables tied to theme.

Recommend Option A for cleanest approach that loads only what's needed.

### 7. Update All Components with Dark Mode Variants

**Files to modify:**

1. **Chat.tsx** - Add dark variants to header colors
2. **Login.tsx** - Add dark variants to background and card
3. **Register.tsx** - Add dark variants to background and card
4. **ConversationSidebar.tsx** - Add dark variants to sidebar colors
5. **MessageList.tsx** - Add dark variants to message containers
6. **MessageInput.tsx** - Add dark variants to input styling
7. **ToolExecutionCard.tsx** - Add dark variants to badge/card colors
8. **index.css** (optional) - Can add any custom dark mode CSS if needed

**Pattern for all components:**
Replace hardcoded color classes with Tailwind dark: variants:
```typescript
// Before
<div className="bg-gray-100 text-gray-900">

// After
<div className="bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white">
```

### Proposed Components

**New Components:**
1. `ThemeToggle` (in `/components/ThemeToggle.tsx`) - Button to cycle theme
2. Optional: `ThemeProvider` could render hidden theme toggle on all pages if needed (but Chat header is better place)

**Modified Components:**
1. All existing pages and chat components (add dark: variants)

### Proposed Hooks

**New Hooks:**
1. `useTheme()` (in `ThemeContext.tsx`) - Access theme state and setTheme
2. `useSystemPreference()` (in `/hooks/useSystemPreference.ts`) - Optional, for system preference detection

**No modifications to existing hooks needed.**

### State Management Changes

**New context:**
- `ThemeContext` - Manages theme preference, effective theme, system preference listening

**Provider hierarchy:**
```
ThemeProvider (NEW)
└── AuthProvider (existing)
    └── Routes
        └── ChatProvider (existing)
```

**State flow:**
1. ThemeProvider initializes from localStorage
2. Listens to system preference changes
3. Provides `useTheme()` hook to all descendants
4. Updates `<html>` element class when theme changes
5. Components use Tailwind `dark:` classes (no explicit theme prop passing needed)
6. MarkdownMessage can optionally use `useTheme()` to conditionally load CSS

### Data Flow Diagram

```
ThemeContext stores:
  ├── theme: 'light' | 'dark' | 'system' (from localStorage)
  ├── systemPreference: boolean (from matchMedia)
  └── effectiveTheme: 'light' | 'dark' (computed from theme + systemPreference)

Side effects:
  ├── Mount: Load from localStorage, setup matchMedia listener
  ├── Theme change: Save to localStorage, update <html class>
  ├── System preference change: Update effectiveTheme, update <html class>
  └── Unmount: Cleanup matchMedia listener

Components:
  ├── Consume theme via Tailwind dark: classes (automatic, no hook needed)
  ├── Chat.tsx: Use <ThemeToggle /> from ThemeContext
  └── MarkdownMessage.tsx: Use useTheme() for conditional CSS import

HTML element:
  └── <html class="dark"> or <html class=""> (set by ThemeProvider)
      ↓
      Activates/deactivates all Tailwind dark: utilities
```

## Implementation Guidance

### Step 1: Create ThemeContext

1. Create `/Users/pablolozano/Mac Projects August/genesis/frontend/src/contexts/ThemeContext.tsx`
2. Define types: `ThemeMode`, `ThemeContextType`
3. Implement ThemeProvider:
   - Use `useState` for theme and systemPreference
   - Use `useEffect` to initialize from localStorage
   - Use `useEffect` to setup matchMedia listener
   - Compute `effectiveTheme` from theme + systemPreference
   - Update `<html>` element class when effectiveTheme changes
4. Export `useTheme()` hook
5. Follow AuthContext pattern for consistency

### Step 2: Update Tailwind Configuration

1. Open `/Users/pablolozano/Mac Projects August/genesis/frontend/tailwind.config.js`
2. Add `darkMode: 'class'` to config
3. Test with dev server to ensure Tailwind compiles with dark: variants

### Step 3: Wrap App with ThemeProvider

1. Open `/Users/pablolozano/Mac Projects August/genesis/frontend/src/App.tsx`
2. Import ThemeProvider
3. Add `<ThemeProvider>` wrapper around `<AuthProvider>`
4. Ensure placement is correct (before AuthProvider)

### Step 4: Add Theme Toggle Button (optional but recommended)

1. Create `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/ThemeToggle.tsx`
2. Import useTheme hook
3. Create button that cycles through themes
4. Add to Chat.tsx header (line 32, in gap-4 div before username)

### Step 5: Update All Components (systematic)

For each component file, add dark: variants to all color classes:

**ConversationSidebar.tsx:**
- Line 60: `bg-gray-50` → `bg-gray-50 dark:bg-gray-900`
- Line 74: `hover:bg-gray-100` → `hover:bg-gray-100 dark:hover:bg-gray-800`
- Line 89: Update input styling for dark mode

**MessageList.tsx:**
- Line 40: `bg-blue-500 text-white` → add `dark:bg-blue-600` (darker for contrast)
- Line 41: `bg-gray-100 text-gray-900` → add `dark:bg-gray-700 dark:text-white`
- Line 63: Similar updates for streaming message styling

**MessageInput.tsx:**
- Line 51: `border-gray-300` → `border-gray-300 dark:border-gray-600`
- Line 52: `disabled:bg-gray-100` → add `dark:disabled:bg-gray-800`
- Update button colors for dark mode

**Chat.tsx:**
- Line 30: Header `bg-white` → `bg-white dark:bg-gray-800`
- Line 33: Text colors add dark: variants
- Line 32: Add `<ThemeToggle />` component

**Login.tsx & Register.tsx:**
- Line 32, 34: Background `bg-gray-50` → `bg-gray-50 dark:bg-gray-950`
- Line 33, 35: Card `bg-white` → `bg-white dark:bg-gray-800`
- Update all text colors with dark: variants
- Update form input styling

**MarkdownMessage.tsx:**
- Line 8: Change CSS import strategy (see options in recommendations)
- Line 21, 45, 77, etc.: Update all hardcoded colors with dark: variants
- If using Option A: Add useTheme() hook and conditional CSS loading

**ToolExecutionCard.tsx:**
- Line 18: Update bg-purple-50/50, bg-blue-50/50 with dark variants

### Step 6: Test Theme Switching

1. Start dev server
2. Test theme toggle button cycles through: light → dark → system
3. Verify localStorage persistence (open DevTools, check localStorage)
4. Verify system preference detection (DevTools → Rendering → emulate prefers-color-scheme)
5. Verify all component colors update correctly in both modes
6. Verify code blocks display correctly in both modes (MarkdownMessage)
7. Test on login and register pages (before authentication)

### Step 7: Consider Additional Enhancements (optional)

- Add transition effect for theme switch: `transition-colors duration-200` on root elements
- Add keyboard shortcut to toggle theme (e.g., Cmd/Ctrl + Shift + T)
- Add theme indicator in UI (e.g., show current theme in settings)
- Ensure accessible contrast ratios in both modes

## Risks and Considerations

### 1. Prop Drilling Risk - **LOW**

**Situation:** Components might receive theme as prop instead of using context.
**Mitigation:** Use Tailwind dark: classes for styling (no prop needed). Only use `useTheme()` when you need the actual theme value (e.g., conditional rendering, CSS import). Most components don't need this.

### 2. CSS Import Loading - **MEDIUM**

**Situation:** MarkdownMessage currently imports only `github-dark.css`. In light mode, code syntax highlighting will be wrong.
**Mitigation:** Use Option A (conditional import based on theme) or load both CSS files and rely on CSS specificity.
**Impact:** Code blocks won't display correctly in light mode without fix.

### 3. Color Scheme Consistency - **MEDIUM**

**Situation:** Need to ensure dark mode colors provide sufficient contrast and maintain visual hierarchy.
**Mitigation:**
- Use standard dark mode color palette (dark gray for backgrounds, light gray for text)
- Test contrast ratios with accessibility checker
- Ensure primary brand colors (blue) are visible in dark mode

### 4. localStorage Access Timing - **LOW**

**Situation:** localStorage might not be available during server-side rendering (if any).
**Mitigation:** Only Genesis frontend is client-side React, no SSR concerns. Safe to use localStorage directly.

### 5. System Preference Listener Cleanup - **LOW**

**Situation:** matchMedia listener must be cleaned up on unmount to prevent memory leaks.
**Mitigation:** ThemeContext useEffect cleanup function removes listener. Follow existing pattern in ChatContext.

### 6. HTML Element Class Mutation - **LOW**

**Situation:** Directly mutating `<html class>` could conflict with other code.
**Mitigation:** ThemeProvider is only component that sets this class. Keep centralized to avoid conflicts.

### 7. Tailwind Dark Mode Not Configured - **HIGH (blocking)**

**Situation:** If Tailwind darkMode is not set to 'class', dark: utilities won't work.
**Mitigation:** Must update tailwind.config.js in Step 2 before testing.

### 8. MarkdownMessage Hardcoded CSS Imports - **MEDIUM (blocking for code blocks)**

**Situation:** Currently imports only github-dark.css by default. If theme is light, code will look wrong.
**Mitigation:** Implement Option A conditional import before testing theme toggle.

### 9. Component Interdependencies - **LOW**

**Situation:** If components are tightly coupled to color scheme, dark mode updates might require extensive refactoring.
**Mitigation:** Current components use simple Tailwind utilities (not custom CSS or CSS-in-JS), so adding dark: variants is straightforward.

### 10. Theme Preference Sync Across Tabs - **LOW**

**Situation:** If user opens app in two tabs and changes theme in one, other tab won't update.
**Mitigation:** Could add `storage` event listener, but not required for MVP. Nice-to-have enhancement.

## Testing Strategy

### Unit Tests (for ThemeContext)

**File:** `/Users/pablolozano/Mac Projects August/genesis/frontend/src/contexts/__tests__/ThemeContext.test.ts`

Test cases:
1. ThemeProvider initializes with 'light' if no localStorage
2. ThemeProvider loads theme from localStorage if present
3. `useTheme()` throws error if called outside provider
4. Setting theme updates localStorage
5. System preference changes update effectiveTheme
6. Setting theme to 'system' uses system preference
7. HTML element class is set to 'dark' when effectiveTheme is 'dark'
8. HTML element class is removed when effectiveTheme is 'light'

### Integration Tests (for ThemeProvider in App)

**File:** `/Users/pablolozano/Mac Projects August/genesis/frontend/src/__tests__/App.theme.test.tsx`

Test cases:
1. Theme toggle in Chat header cycles through themes
2. Theme persists after page reload
3. Login page displays correctly in both light and dark modes
4. Chat page displays correctly in both light and dark modes
5. System preference is detected on first load
6. Changing system preference updates theme when set to 'system'

### Component Visual Tests (manual)

**Login.tsx:**
- Visual check: Form is readable in both light and dark modes
- Visual check: Proper contrast ratios
- Visual check: Input focus states visible

**Chat.tsx:**
- Visual check: Header bar themed correctly
- Visual check: Theme toggle button is accessible and works
- Visual check: Sidebar background and hover states correct

**ConversationSidebar.tsx:**
- Visual check: Sidebar background correct
- Visual check: Conversation items readable
- Visual check: Hover states visible

**MessageList.tsx:**
- Visual check: User messages (blue) visible in both modes
- Visual check: Assistant messages (gray) visible and readable
- Visual check: Streaming indicator visible

**MarkdownMessage.tsx:**
- Visual check: Code blocks display correctly in both modes
- Visual check: Code syntax highlighting is appropriate for theme
- Visual check: Links are visible and understandable
- Visual check: Tables are readable

**ToolExecutionCard.tsx:**
- Visual check: Card background and border visible
- Visual check: Text and badges readable

### Accessibility Testing

- Check contrast ratios meet WCAG AA standard in both modes
- Verify keyboard navigation still works with theme changes
- Test theme toggle button is keyboard accessible
- Verify focus indicators are visible in both modes

### Browser Testing

Test in:
- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers (iOS Safari, Chrome Mobile)

Test matchMedia listener works correctly in all browsers.

## Summary

**Key Implementation Steps:**

1. Create ThemeContext with localStorage persistence and system preference listening
2. Update Tailwind config to enable `darkMode: 'class'`
3. Wrap App with ThemeProvider
4. Create ThemeToggle component for Chat header
5. Systematically add dark: variants to all color classes in components
6. Fix MarkdownMessage CSS import strategy for code blocks
7. Test thoroughly in both light and dark modes

**Critical Files to Create:**
- `/contexts/ThemeContext.tsx`
- `/components/ThemeToggle.tsx` (optional but recommended)

**Critical Files to Modify:**
- `tailwind.config.js` - Enable dark mode
- `App.tsx` - Add ThemeProvider
- `Chat.tsx` - Add dark: variants and ThemeToggle
- `Login.tsx` - Add dark: variants
- `Register.tsx` - Add dark: variants
- `ConversationSidebar.tsx` - Add dark: variants
- `MessageList.tsx` - Add dark: variants
- `MessageInput.tsx` - Add dark: variants
- `MarkdownMessage.tsx` - Fix CSS import, add dark: variants
- `ToolExecutionCard.tsx` - Add dark: variants

**Estimated Complexity:** Medium
- ThemeContext creation: straightforward (follows AuthContext pattern)
- Tailwind dark mode setup: simple (one config line)
- Component updates: repetitive but straightforward (add dark: variants)
- MarkdownMessage CSS fix: requires careful testing

**No backend changes needed.** This is purely frontend state management and styling.

## Assumptions

1. Project uses Tailwind CSS for styling (verified - index.css imports @tailwind directives)
2. Components are class-based with hooks (verified - all components use React hooks)
3. localStorage is available (verified - Genesis is client-only app)
4. matchMedia API is available (standard in modern browsers)
5. No existing theme library or custom theme system (verified - no theme-related code found)
6. Auth and Chat contexts follow standard React context patterns (verified)

## Open Questions for Pablo

1. Should theme toggle be in Chat header or in a settings menu? (Recommend: header for easy access)
2. Should app show transition animation when theme changes? (Recommend: subtle transition-colors)
3. Should system preference be the default if user hasn't set preference? (Recommend: yes, 'system' is default)
4. Any specific dark mode colors you prefer, or should we use standard Tailwind dark palette? (Recommend: standard palette)
5. Should theme preference sync across browser tabs? (Recommend: not required for MVP, nice-to-have)
