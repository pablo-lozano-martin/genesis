# Testing Coverage Analysis: Dark/Light Theme Mode with System Preference Support

## Request Summary

This feature adds comprehensive dark/light theme mode support to the frontend with the following capabilities:

1. **ThemeContext state management**: Provides theme state and toggle functionality to all components
2. **System preference detection**: Detects user's OS-level dark/light preference via `window.matchMedia`
3. **localStorage persistence**: Saves user's manual theme choice to localStorage
4. **Component-wide theme application**: Applies dark/light variants across all components via CSS classes
5. **Cross-tab synchronization**: Synchronizes theme changes across multiple browser tabs via storage events
6. **Graceful degradation**: Handles missing APIs (older browsers without matchMedia) and corrupted data

The implementation requires comprehensive testing for state management, browser APIs, persistence, and edge cases.

## Relevant Files & Modules

### Files to Examine

#### Frontend Context & Hooks
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/contexts/AuthContext.tsx` - Reference pattern for context implementation (Provider component, custom hook, useContext error handling)
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/contexts/ChatContext.tsx` - Reference pattern for complex context (state management, useCallback patterns, refs)
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/contexts/ThemeContext.tsx` - **[NEW]** Theme context for managing dark/light mode (to be created)

#### Frontend Components
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/App.tsx` - Main app component where ThemeProvider will be integrated
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/pages/Chat.tsx` - Chat page with styled components that need dark variants
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/ConversationSidebar.tsx` - Sidebar with hardcoded colors (bg-gray-50, bg-gray-100) needing dark variants
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/MessageList.tsx` - Message display needing dark styling
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/chat/MarkdownMessage.tsx` - Markdown rendering with github-dark.css requiring dynamic theme support
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/ui/card.tsx` - UI component needing dark variants
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/components/ui/badge.tsx` - Badge component needing dark variants

#### Frontend Utilities
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/lib/utils.ts` - cn() utility for className merging (already available for use)
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/lib/themeUtils.ts` - **[NEW]** Utility functions for theme detection and manipulation

#### Frontend Configuration
- `/Users/pablolozano/Mac Projects August/genesis/frontend/tailwind.config.js` - Tailwind config (currently minimal, needs dark mode configuration)
- `/Users/pablolozano/Mac Projects August/genesis/frontend/src/index.css` - Root CSS file (needs theme variables or dark mode setup)

#### Frontend Package Configuration
- `/Users/pablolozano/Mac Projects August/genesis/frontend/package.json` - Dependency management (needs testing frameworks)

#### Test Infrastructure
- `/Users/pablolozano/Mac Projects August/genesis/frontend/__tests__/` - **[NEW]** Test directory to be created
- `/Users/pablolozano/Mac Projects August/genesis/frontend/vitest.config.ts` - **[NEW]** Vitest configuration to be created
- `/Users/pablolozano/Mac Projects August/genesis/frontend/tsconfig.app.json` - TypeScript config for frontend (may need test setup)

### Key Test Cases & Functions

#### Test Files to Create

**Unit Test Files:**
- `frontend/__tests__/unit/contexts/ThemeContext.test.tsx` - Tests for ThemeContext state management
- `frontend/__tests__/unit/lib/themeUtils.test.ts` - Tests for theme utility functions
- `frontend/__tests__/unit/hooks/useTheme.test.tsx` - Tests for custom theme hook

**Integration Test Files:**
- `frontend/__tests__/integration/theme-persistence.test.tsx` - Tests for localStorage read/write and persistence
- `frontend/__tests__/integration/theme-sync.test.tsx` - Tests for cross-tab synchronization
- `frontend/__tests__/integration/system-preference.test.tsx` - Tests for system preference detection

**E2E Test Files:**
- `frontend/e2e/theme-toggle.spec.ts` - End-to-end tests for theme toggle functionality
- `frontend/e2e/theme-persistence.spec.ts` - E2E tests for persistence across page reloads

#### Key Test Patterns & Functions (to be implemented)

**ThemeContext Tests:**
- `test_theme_context_initializes_with_light_theme()` - Default theme on first mount
- `test_theme_context_initializes_with_system_preference()` - System preference detection on first visit
- `test_theme_context_initializes_with_saved_preference()` - Load saved theme from localStorage
- `test_theme_toggle_updates_state()` - Theme toggle functionality
- `test_theme_context_throws_error_without_provider()` - Hook error handling

**localStorage Tests:**
- `test_localStorage_saves_theme_preference()` - Write to localStorage
- `test_localStorage_reads_saved_theme()` - Read from localStorage
- `test_localStorage_handles_corrupted_value()` - Invalid data recovery
- `test_localStorage_quota_exceeded()` - Storage quota exceeded handling

**System Preference Tests:**
- `test_system_preference_detection_prefers_dark()` - matchMedia returns dark preference
- `test_system_preference_detection_prefers_light()` - matchMedia returns light preference
- `test_system_preference_unavailable()` - window.matchMedia doesn't exist (older browsers)
- `test_system_preference_change_listener()` - OS theme change detection

**Cross-Tab Synchronization Tests:**
- `test_storage_event_listener_updates_theme()` - Update theme when other tab changes it
- `test_storage_event_with_same_tab_ignored()` - Don't update on own storage events
- `test_storage_event_with_corrupted_value()` - Handle invalid data from other tabs

**Component Rendering Tests:**
- `test_child_components_receive_theme_context()` - Context propagation
- `test_dark_variants_applied_when_dark_theme()` - CSS classes applied correctly
- `test_light_variants_applied_when_light_theme()` - CSS classes applied correctly

## Current Testing Overview

### Frontend Testing Status

**Current State:**
- No testing framework installed in frontend
- No test files exist in the codebase (checked `/Users/pablolozano/Mac Projects August/genesis/frontend` - no `.test.ts` or `.test.tsx` files)
- No vitest, jest, or testing library configuration found
- Backend uses pytest with comprehensive test patterns (unit, integration, fixtures)

**Frontend Testing Infrastructure Gaps:**
1. **No test framework**: Need to install Vitest (modern, TypeScript-first, Vite-integrated)
2. **No test utilities**: Need React Testing Library for component testing
3. **No mock infrastructure**: Need to mock browser APIs (localStorage, window.matchMedia)
4. **No configuration**: Need vitest.config.ts setup
5. **No E2E framework**: No Playwright or Cypress detected

### Backend Testing Patterns (Reference)

The backend uses pytest with these patterns:

**Test Structure:**
- Location: `/Users/pablolozano/Mac Projects August/genesis/backend/tests/`
- Organization: `unit/` and `integration/` subdirectories
- Fixtures: Centralized in `conftest.py`
- Markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.asyncio`

**Fixtures Available (for reference):**
- `app()` - Application instance
- `client()` - Async HTTP client
- Mock repositories for testing in isolation
- Sample domain models with realistic test data

**Patterns to Emulate:**
- Descriptive test names: `test_action_describes_scenario()`
- AAA pattern: Arrange, Act, Assert
- One responsibility per test
- Comprehensive edge case coverage
- Error handling and validation testing

## Coverage Analysis

### Well-Tested Components
- None yet (frontend testing framework not yet installed)

### Undertested Components
- React Contexts (AuthContext and ChatContext exist but have no test coverage)
- Component styling and theming (Tailwind classes applied but no theme testing)

### Untested Components
- **ThemeContext** - Will be created, needs comprehensive unit tests
- **Theme utilities** - Will be created, needs unit tests for edge cases
- **localStorage interaction** - No existing patterns; needs mocking
- **window.matchMedia** - No existing patterns; needs mocking
- **Storage events** - No existing patterns; needs mocking
- **All themed components** - No dark variant testing
- **System preference detection** - No tests exist
- **Theme persistence flow** - Integration tests needed
- **Cross-tab synchronization** - Integration tests needed
- **Browser API fallbacks** - Edge case testing needed

## Testing Recommendations

### Required Test Infrastructure Setup

#### Phase 0: Install Testing Dependencies

**Install Vitest and React Testing Library:**
```bash
cd /Users/pablolozano/Mac\ Projects\ August/genesis/frontend
npm install -D vitest @vitest/ui @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom
```

**Create `frontend/vitest.config.ts`:**
```typescript
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/__tests__/setup.ts',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/**/*.d.ts', 'src/**/*.test.{ts,tsx}']
    }
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  }
})
```

**Create `frontend/src/__tests__/setup.ts`:**
```typescript
import '@testing-library/jest-dom'
import { expect, afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'

// Cleanup after each test
afterEach(() => {
  cleanup()
})

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
}
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
})
```

**Update `frontend/package.json` scripts:**
```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "lint": "eslint .",
    "preview": "vite preview",
    "test": "vitest",
    "test:ui": "vitest --ui",
    "test:coverage": "vitest --coverage"
  }
}
```

### Proposed Unit Tests

#### 1. ThemeContext Tests
**New File**: `/Users/pablolozano/Mac Projects August/genesis/frontend/src/__tests__/unit/contexts/ThemeContext.test.tsx`

**Test Cases:**

```
test_theme_context_initializes_with_light_theme
  Given: First visit, no localStorage, system preference is light
  When: ThemeProvider mounts
  Then: Context provides theme='light'

test_theme_context_initializes_with_dark_system_preference
  Given: First visit, no localStorage, system preference is dark
  When: ThemeProvider mounts with system preference 'dark'
  Then: Context provides theme='dark'

test_theme_context_initializes_with_saved_preference
  Given: localStorage has 'dark' saved
  When: ThemeProvider mounts
  Then: Context provides theme='dark' (saved preference takes priority)

test_theme_toggle_switches_from_light_to_dark
  Given: Theme is 'light'
  When: toggleTheme() called
  Then: Theme becomes 'dark'

test_theme_toggle_switches_from_dark_to_light
  Given: Theme is 'dark'
  When: toggleTheme() called
  Then: Theme becomes 'light'

test_theme_toggle_saves_to_localStorage
  Given: Theme context with working localStorage
  When: toggleTheme() called
  Then: localStorage.setItem called with ('theme', 'dark')

test_use_theme_hook_throws_without_provider
  Given: Component using useTheme without ThemeProvider
  When: Hook invoked
  Then: Error thrown with clear message

test_theme_context_applies_to_document_element
  Given: Theme provider with theme='dark'
  When: Component renders
  Then: document.documentElement has class 'dark'

test_theme_context_removes_class_when_toggled
  Given: document.documentElement has class 'dark'
  When: Theme toggled to 'light'
  Then: document.documentElement class 'dark' removed

test_theme_persists_across_provider_remount
  Given: localStorage has 'dark' saved
  When: Provider unmounts and remounts
  Then: Theme restored as 'dark'
```

#### 2. Theme Utilities Tests
**New File**: `/Users/pablolozano/Mac Projects August/genesis/frontend/src/__tests__/unit/lib/themeUtils.test.ts`

**Test Cases:**

```
test_detect_system_preference_dark
  Given: window.matchMedia('(prefers-color-scheme: dark)').matches = true
  When: detectSystemPreference() called
  Then: Returns 'dark'

test_detect_system_preference_light
  Given: window.matchMedia('(prefers-color-scheme: dark)').matches = false
  When: detectSystemPreference() called
  Then: Returns 'light'

test_detect_system_preference_unavailable
  Given: window.matchMedia is undefined (older browser)
  When: detectSystemPreference() called
  Then: Returns 'light' (fallback)

test_listen_to_system_preference_changes
  Given: System preference listener setup
  When: OS theme changes (matchMedia fires change event)
  Then: Callback invoked with new preference

test_get_theme_from_localStorage
  Given: localStorage has 'dark' saved
  When: getStoredTheme() called
  Then: Returns 'dark'

test_get_theme_from_localStorage_empty
  Given: localStorage has no theme
  When: getStoredTheme() called
  Then: Returns null

test_get_theme_from_localStorage_corrupted
  Given: localStorage has invalid value 'invalid'
  When: getStoredTheme() called
  Then: Returns null (ignores corrupted data)

test_save_theme_to_localStorage
  Given: localStorage.setItem available
  When: saveTheme('dark') called
  Then: localStorage.setItem('theme', 'dark')

test_save_theme_handles_quota_exceeded
  Given: localStorage.setItem throws QuotaExceededError
  When: saveTheme('dark') called
  Then: Error caught and logged (doesn't crash)

test_safe_localStorage_access_when_disabled
  Given: localStorage access throws (disabled in private mode)
  When: saveTheme() called
  Then: Function handles gracefully, no crash

test_resolve_initial_theme_priority
  Given: saved='dark', system='light', no default
  When: resolveInitialTheme() called
  Then: Returns 'dark' (saved takes priority)

test_resolve_initial_theme_system_fallback
  Given: saved=null, system='dark'
  When: resolveInitialTheme() called
  Then: Returns 'dark' (system is fallback)

test_resolve_initial_theme_light_default
  Given: saved=null, system=null
  When: resolveInitialTheme() called
  Then: Returns 'light' (final fallback)
```

#### 3. Theme Hook Tests
**New File**: `/Users/pablolozano/Mac Projects August/genesis/frontend/src/__tests__/unit/hooks/useTheme.test.tsx`

**Test Cases:**

```
test_use_theme_returns_current_theme
  Given: Theme context with theme='dark'
  When: useTheme() called in component
  Then: Returns object with theme='dark'

test_use_theme_returns_toggle_function
  Given: useTheme() called
  When: Called in component
  Then: Returns object with toggleTheme function

test_use_theme_toggle_updates_context
  Given: Component using useTheme with theme='light'
  When: toggleTheme() invoked
  Then: Hook returns updated theme='dark'

test_use_theme_hook_stable_across_renders
  Given: Component using useTheme
  When: Component re-renders
  Then: toggleTheme reference remains stable (useCallback)

test_use_theme_multiple_consumers_synchronized
  Given: Two components using useTheme
  When: One calls toggleTheme()
  Then: Both components receive updated theme
```

### Proposed Integration Tests

#### 1. Theme Persistence Integration Tests
**New File**: `/Users/pablolozano/Mac Projects August/genesis/frontend/src/__tests__/integration/theme-persistence.test.tsx`

**Test Cases:**

```
test_theme_preference_persists_on_page_reload
  Given: User selects dark theme
  When: Page reloads
  Then: Dark theme is still active
  Implementation: Mock localStorage, toggle theme, remount provider, verify theme

test_first_visit_uses_system_preference
  Given: First visit with no saved theme, system preference is dark
  When: Page loads
  Then: Dark theme applied without user action
  Implementation: Mock localStorage.getItem returns null, matchMedia dark=true, verify

test_manual_preference_overrides_system_preference
  Given: System preference is light, user selected dark
  When: Page reloads
  Then: Dark theme applied (saved overrides system)
  Implementation: Mock both, verify saved takes precedence

test_invalid_localStorage_value_falls_back_to_system
  Given: localStorage has corrupted value 'garbage'
  When: Page loads
  Then: System preference used
  Implementation: Mock localStorage with invalid data, verify fallback

test_localStorage_quota_exceeded_graceful_fallback
  Given: localStorage.setItem throws QuotaExceededError
  When: User toggles theme
  Then: Theme changes in memory, localStorage error logged but no crash
  Implementation: Mock setItem to throw, verify theme still toggles

test_private_browsing_localStorage_unavailable
  Given: localStorage access throws (private mode)
  When: Theme context initializes
  Then: Theme works with system preference, no crash
  Implementation: Mock localStorage throws, verify context initializes
```

#### 2. Theme Synchronization (Cross-Tab) Tests
**New File**: `/Users/pablolozano/Mac Projects August/genesis/frontend/src/__tests__/integration/theme-sync.test.tsx`

**Test Cases:**

```
test_storage_event_updates_theme_in_other_tab
  Given: Two tabs open, one changes theme to dark
  When: Other tab receives storage event from changed tab
  Then: Other tab's theme updates to dark
  Implementation: Mock storage event, verify listener updates context

test_storage_event_ignored_if_from_same_tab
  Given: Storage event from same tab/window
  When: Storage event received
  Then: Theme not updated (no duplicate change)
  Implementation: Verify listener checks event.storageArea, doesn't update self

test_storage_event_invalid_data_ignored
  Given: Storage event with corrupted theme value 'invalid'
  When: Storage event received
  Then: Old theme retained, no crash
  Implementation: Mock event with invalid value, verify theme unchanged

test_multiple_tabs_in_sync
  Given: Three tabs with same app instance
  When: Tab 1 changes to dark, Tab 2 changes to light
  Then: All tabs show correct theme after changes
  Implementation: Mock multiple storage events, verify all respond correctly

test_storage_listener_cleanup_on_unmount
  Given: Component with storage event listener
  When: Component unmounts
  Then: Storage listener removed (no memory leak)
  Implementation: Spy on removeEventListener, verify called on cleanup

test_storage_event_listener_added_on_mount
  Given: Theme provider mounting
  When: Provider mounts
  Then: Storage event listener registered
  Implementation: Spy on addEventListener, verify called

test_rapid_theme_changes_across_tabs
  Given: Rapid toggles in multiple tabs
  When: Storage events arrive out of order
  Then: Final theme state is consistent (last write wins)
  Implementation: Simulate rapid events, verify final state
```

#### 3. System Preference Detection Tests
**New File**: `/Users/pablolozano/Mac Projects August/genesis/frontend/src/__tests__/integration/system-preference.test.tsx`

**Test Cases:**

```
test_system_preference_dark_detected
  Given: matchMedia('(prefers-color-scheme: dark)').matches = true
  When: detectSystemPreference() called
  Then: Returns 'dark'
  Implementation: Mock matchMedia with dark preference

test_system_preference_light_detected
  Given: matchMedia('(prefers-color-scheme: dark)').matches = false
  When: detectSystemPreference() called
  Then: Returns 'light'
  Implementation: Mock matchMedia without dark preference

test_matchMedia_unavailable_fallback
  Given: window.matchMedia is undefined (older browser)
  When: detectSystemPreference() called
  Then: Returns 'light' (safe fallback)
  Implementation: Delete window.matchMedia, call function

test_system_preference_listener_detects_os_theme_change
  Given: OS theme listener registered
  When: OS theme changes (matchMedia fires change event)
  Then: Callback receives new preference
  Implementation: Mock matchMedia with addEventListener, trigger change event

test_system_preference_listener_cleanup
  Given: System preference listener setup
  When: Listener cleanup called
  Then: Event listener removed
  Implementation: Spy on removeEventListener, verify called

test_system_preference_change_during_page_lifetime
  Given: User changes OS theme while app is open
  When: matchMedia change event fires
  Then: App switches theme (if no saved preference)
  Implementation: Trigger change event, verify theme updates

test_system_preference_ignored_with_saved_preference
  Given: User has saved dark preference, system is light
  When: System theme changes to dark
  Then: App stays dark (saved preference locked in)
  Implementation: Verify saved theme doesn't change when system changes
```

#### 4. Component Styling Integration Tests
**New File**: `/Users/pablolozano/Mac Projects August/genesis/frontend/src/__tests__/integration/theme-rendering.test.tsx`

**Test Cases:**

```
test_document_element_dark_class_applied
  Given: Theme is 'dark'
  When: Component renders
  Then: document.documentElement has 'dark' class
  Implementation: Render provider, check document.documentElement.classList

test_document_element_dark_class_removed
  Given: Theme is 'dark', user toggles to 'light'
  When: toggleTheme() called
  Then: document.documentElement 'dark' class removed
  Implementation: Toggle theme, verify class list

test_dark_tailwind_variants_applied
  Given: Component with dark:bg-slate-900 class
  When: Theme is 'dark'
  Then: Dark variant applied (requires document dark class)
  Implementation: Render with Tailwind, verify computed styles

test_light_tailwind_variants_applied
  Given: Component with bg-white (light) and dark:bg-slate-900
  When: Theme is 'light'
  Then: Light variant applied
  Implementation: Toggle theme, verify computed styles change

test_child_components_inherit_theme
  Given: Nested components under ThemeProvider
  When: Theme is 'dark'
  Then: All children can access dark theme via context
  Implementation: Use multiple consumers, verify all get dark theme

test_sidebar_dark_variant_colors
  Given: ConversationSidebar with theme='dark'
  When: Component renders
  Then: Dark background colors applied (not light gray)
  Implementation: Render sidebar with dark theme, check styles

test_message_list_dark_variant_colors
  Given: MessageList with theme='dark'
  When: Component renders
  Then: Dark text/background colors used
  Implementation: Similar to sidebar test

test_markdown_message_dark_variant
  Given: MarkdownMessage with theme='dark'
  When: Component renders
  Then: github-dark.css styles applied
  Implementation: Verify correct highlight.js CSS loaded
```

### Proposed End-to-End Tests

#### 1. Theme Toggle E2E Test
**New File**: `/Users/pablolozano/Mac Projects August/genesis/frontend/e2e/theme-toggle.spec.ts`

**Test Cases:**

```
test_theme_toggle_button_switches_appearance
  1. Load app
  2. Click theme toggle button (when implemented)
  3. Observe UI changes to dark theme
  4. Click again
  5. Observe UI returns to light theme

test_theme_persists_after_page_reload
  1. Load app
  2. Switch to dark theme
  3. Verify dark theme active
  4. Reload page
  5. Verify dark theme still active

test_system_preference_respected_on_first_visit
  1. Clear localStorage and cookies
  2. Set system theme to dark (OS settings or browser simulation)
  3. Load app
  4. Verify dark theme applied automatically

test_manual_theme_overrides_system_preference
  1. System theme is light, app shows light
  2. User clicks to switch to dark
  3. Verify dark theme applied
  4. Reload page
  5. Verify dark theme persists (saved overrides system)

test_theme_toggle_affects_all_components
  1. Load app
  2. Switch to dark theme
  3. Verify sidebar dark colors
  4. Verify messages dark colors
  5. Verify all UI components updated
```

#### 2. Theme Persistence E2E Test
**New File**: `/Users/pablolozano/Mac Projects August/genesis/frontend/e2e/theme-persistence.spec.ts`

**Test Cases:**

```
test_theme_preference_survives_multiple_reloads
  1. Switch to dark theme
  2. Reload page - verify dark
  3. Close and reopen tab - verify dark
  4. Navigate away and back - verify dark

test_cross_tab_theme_synchronization
  1. Open app in two tabs
  2. Switch to dark in tab 1
  3. Verify tab 2 updates to dark in real-time
  4. Switch to light in tab 2
  5. Verify tab 1 updates to light

test_corrupted_localStorage_recovery
  1. Manually set localStorage.theme to invalid value
  2. Reload page
  3. Verify app still works, uses system preference
  4. User can toggle theme
  5. Valid value saved to localStorage
```

### Test Data & Fixtures

#### Frontend Test Utilities
**New File**: `/Users/pablolozano/Mac Projects August/genesis/frontend/src/__tests__/utils/test-utils.tsx`

```typescript
// Test utilities for rendering components with theme context

import { render } from '@testing-library/react'
import { ThemeProvider } from '../../contexts/ThemeContext'

export function renderWithTheme(ui: React.ReactElement, options = {}) {
  return render(
    <ThemeProvider initialTheme="light">
      {ui}
    </ThemeProvider>,
    options
  )
}

export function createMatchMediaMock(prefersColorScheme: 'dark' | 'light') {
  return {
    matches: prefersColorScheme === 'dark',
    media: '(prefers-color-scheme: dark)',
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }
}

export function createStorageEventMock(theme: string) {
  return new StorageEvent('storage', {
    key: 'theme',
    newValue: theme,
    oldValue: null,
  })
}
```

#### Mock Factories
**New File**: `/Users/pablolozano/Mac Projects August/genesis/frontend/src/__tests__/mocks/browser-mocks.ts`

```typescript
// Mock implementations for browser APIs

export const mockLocalStorage = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
  key: vi.fn(),
  length: 0,
}

export const mockMatchMedia = (prefersDark: boolean) => {
  return {
    matches: prefersDark,
    media: '(prefers-color-scheme: dark)',
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }
}

export function setupLocalStorageMock() {
  const store: Record<string, string> = {}

  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value.toString()
    },
    removeItem: (key: string) => {
      delete store[key]
    },
    clear: () => {
      Object.keys(store).forEach(key => delete store[key])
    },
  }
}
```

## Implementation Guidance

### Step-by-Step Testing Approach

#### Phase 1: Test Infrastructure Setup (Prerequisite)

1. **Install testing dependencies:**
   ```bash
   cd /Users/pablolozano/Mac\ Projects\ August/genesis/frontend
   npm install -D vitest @vitest/ui @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom
   ```

2. **Create vitest configuration:**
   - Add `frontend/vitest.config.ts` (see infrastructure section above)

3. **Create test setup file:**
   - Add `frontend/src/__tests__/setup.ts` with mocks for window.matchMedia and localStorage

4. **Update package.json scripts:**
   - Add `test`, `test:ui`, `test:coverage` scripts

5. **Verify setup works:**
   ```bash
   npm test -- --run
   ```

#### Phase 2: ThemeContext Implementation & Unit Tests

1. **Create ThemeContext:**
   - File: `/Users/pablolozano/Mac Projects August/genesis/frontend/src/contexts/ThemeContext.tsx`
   - Pattern: Follow AuthContext structure (Provider component, custom hook, error handling)
   - Features: State management, localStorage persistence, system preference detection

2. **Create unit tests for ThemeContext:**
   - File: `/Users/pablolozano/Mac Projects August/genesis/frontend/src/__tests__/unit/contexts/ThemeContext.test.tsx`
   - Coverage: All state transitions, initialization paths, hook usage
   - Run: `npm test -- ThemeContext.test.tsx`

3. **Create theme utilities:**
   - File: `/Users/pablolozano/Mac Projects August/genesis/frontend/src/lib/themeUtils.ts`
   - Functions: `detectSystemPreference()`, `getStoredTheme()`, `saveTheme()`, `resolveInitialTheme()`

4. **Create unit tests for utilities:**
   - File: `/Users/pablolozano/Mac Projects August/genesis/frontend/src/__tests__/unit/lib/themeUtils.test.ts`
   - Coverage: All utility functions, edge cases, error handling
   - Run: `npm test -- themeUtils.test.ts`

5. **Create useTheme hook:**
   - File: `/Users/pablolozano/Mac Projects August/genesis/frontend/src/hooks/useTheme.ts`
   - Pattern: Follow existing useAuth pattern

6. **Create unit tests for hook:**
   - File: `/Users/pablolozano/Mac Projects August/genesis/frontend/src/__tests__/unit/hooks/useTheme.test.tsx`
   - Run: `npm test -- useTheme.test.tsx`

#### Phase 3: Integration Tests (Persistence & Sync)

1. **Create localStorage integration tests:**
   - File: `/Users/pablolozano/Mac Projects August/genesis/frontend/src/__tests__/integration/theme-persistence.test.tsx`
   - Scenarios: Save/load, corrupted data, quota exceeded, private browsing
   - Run: `npm test -- theme-persistence.test.tsx`

2. **Create cross-tab sync tests:**
   - File: `/Users/pablolozano/Mac Projects August/genesis/frontend/src/__tests__/integration/theme-sync.test.tsx`
   - Scenarios: Storage events, multiple tabs, event cleanup
   - Run: `npm test -- theme-sync.test.tsx`

3. **Create system preference tests:**
   - File: `/Users/pablolozano/Mac Projects August/genesis/frontend/src/__tests__/integration/system-preference.test.tsx`
   - Scenarios: Detection, listener, OS changes, fallbacks
   - Run: `npm test -- system-preference.test.tsx`

4. **Create component rendering tests:**
   - File: `/Users/pablolozano/Mac Projects August/genesis/frontend/src/__tests__/integration/theme-rendering.test.tsx`
   - Scenarios: CSS classes, Tailwind variants, nested components
   - Run: `npm test -- theme-rendering.test.tsx`

#### Phase 4: Component Updates (Applying Theme)

1. **Update Tailwind configuration:**
   - File: `/Users/pablolozano/Mac Projects August/genesis/frontend/tailwind.config.js`
   - Add: `darkMode: 'class'` to enable `dark:` prefix classes

2. **Update all components with dark variants:**
   - ConversationSidebar: Add dark:bg-slate-950, dark:text-white, etc.
   - MessageList: Dark styling for messages
   - All cards and buttons: Add dark variants
   - Pattern: Use cn() utility to merge classNames

3. **Update App.tsx:**
   - Wrap with `<ThemeProvider>`
   - Place before `<BrowserRouter>` (or after if contexts need routing)

4. **Create integration tests for styled components:**
   - Verify dark classes applied when theme='dark'
   - Verify light classes applied when theme='light'

#### Phase 5: End-to-End Tests (Optional but Recommended)

1. **Install Playwright:**
   ```bash
   npm install -D @playwright/test
   ```

2. **Create playwright config:**
   - File: `/Users/pablolozano/Mac Projects August/genesis/frontend/playwright.config.ts`

3. **Create E2E tests:**
   - File: `/Users/pablolozano/Mac Projects August/genesis/frontend/e2e/theme-toggle.spec.ts`
   - File: `/Users/pablolozano/Mac Projects August/genesis/frontend/e2e/theme-persistence.spec.ts`

4. **Run E2E tests:**
   ```bash
   npx playwright test
   ```

### Running Tests

**All Tests:**
```bash
cd /Users/pablolozano/Mac\ Projects\ August/genesis/frontend
npm test
```

**Unit Tests Only:**
```bash
npm test -- src/__tests__/unit
```

**Integration Tests Only:**
```bash
npm test -- src/__tests__/integration
```

**Specific Test File:**
```bash
npm test -- ThemeContext.test.tsx
```

**With UI Dashboard:**
```bash
npm run test:ui
```

**With Coverage Report:**
```bash
npm run test:coverage
```

**E2E Tests:**
```bash
npx playwright test
```

**E2E Tests with UI:**
```bash
npx playwright test --ui
```

## Risks and Considerations

### Technical Risks

#### 1. localStorage Availability
**Risk**: localStorage unavailable in private browsing, disabled browsers, or when quota exceeded
**Impact**: Theme preference not persisted, user loses manual choice after reload
**Mitigation**:
- Wrap all localStorage calls in try/catch
- Gracefully fall back to system preference if storage fails
- Log errors but don't crash application
**Testing**: Test private browsing scenario, quota exceeded errors, disabled localStorage

#### 2. window.matchMedia Unavailable
**Risk**: Older browsers (IE 8 and below) don't have matchMedia API
**Impact**: System preference detection fails
**Mitigation**:
- Check if window.matchMedia exists before using
- Default to 'light' theme if API unavailable
- Ensure app works without system preference detection
**Testing**: Mock matchMedia as undefined, verify fallback to light theme

#### 3. Race Conditions in Storage Events
**Risk**: Multiple storage events from different tabs arrive out of order
**Impact**: Theme state inconsistency across tabs
**Mitigation**:
- Use last-write-wins strategy
- Add timestamps to stored theme values
- Handle events gracefully even if corrupted
**Testing**: Simulate rapid storage events, verify final state consistency

#### 4. Document Element Mutations
**Risk**: Third-party libraries or other code modify document.documentElement.className
**Impact**: Dark theme class removed by external code
**Mitigation**:
- Use classList API (add/remove) instead of string manipulation
- Monitor for mutations and reapply if needed
- Avoid assuming class string is static
**Testing**: Verify classList methods used, not string assignment

#### 5. CSS Variant Compatibility
**Risk**: Missing dark variants on new components during development
**Impact**: Components look broken in dark mode
**Mitigation**:
- Define dark variants for all color-dependent classes
- Use Tailwind's dark: prefix consistently
- Create component dark variant checklist
- Add tests verifying dark classes exist
**Testing**: Verify dark: variants exist for all color classes in components

#### 6. System Theme Change During Session
**Risk**: User changes OS theme while app is open
**Impact**: Theme in app doesn't match OS if no listener active
**Mitigation**:
- Keep system preference listener active throughout app lifetime
- Only update theme if no manual preference saved
- Provide user option to re-sync with system
**Testing**: Trigger matchMedia change event during session, verify update

### Edge Cases Requiring Special Attention

#### 1. No System Preference (Older Browsers)
**Scenario**: Browser doesn't support matchMedia for color-scheme
**Test**: Mock window.matchMedia as undefined
**Expected**: App initializes with 'light' theme, works normally
**Implementation**: Check if function exists before calling

#### 2. Rapid Theme Toggling
**Scenario**: User rapidly clicks theme button multiple times
**Test**: Simulate rapid toggleTheme() calls
**Expected**: Final theme state correct, no memory leaks, no duplicate listeners
**Implementation**: Debounce or batch updates if needed

#### 3. localStorage Quota Exceeded
**Scenario**: Browser storage quota full
**Test**: Mock localStorage.setItem to throw QuotaExceededError
**Expected**: Theme toggles in memory, error logged, app continues working
**Implementation**: Try/catch with fallback

#### 4. Corrupted localStorage Value
**Scenario**: localStorage.theme contains invalid value 'invalid' (not 'light' or 'dark')
**Test**: Set localStorage.theme='invalid', reload app
**Expected**: Ignored, system preference used instead
**Implementation**: Validate stored value against whitelist ['light', 'dark']

#### 5. Private Browsing Mode
**Scenario**: Browser in private/incognito mode, localStorage disabled
**Test**: Mock localStorage to throw on access
**Expected**: App uses system preference, works normally, no crash
**Implementation**: Try/catch all localStorage calls

#### 6. Storage Events from Same Tab
**Scenario**: Storage event fired from same window (shouldn't happen in modern browsers)
**Test**: Dispatch storage event with same window source
**Expected**: Theme not updated (prevent duplicate changes)
**Implementation**: Check event.storageArea or similar identifier

#### 7. Missing Dark Variants on Components
**Scenario**: New component added without dark:bg, dark:text variants
**Test**: Component test checks for dark variant classes
**Expected**: Test fails if dark variants missing
**Implementation**: Explicit dark variant checklist in component tests

#### 8. Markdown Component Theme Switching
**Scenario**: MarkdownMessage with highlight.js needs github-dark.css in dark mode
**Test**: Switch theme, verify correct CSS stylesheet loaded
**Expected**: Syntax highlighting adjusts to dark/light
**Implementation**: Dynamic import or CSS switching

#### 9. Multiple Tabs with Rapid Updates
**Scenario**: Three tabs rapidly toggling theme
**Test**: Simulate rapid storage events from different sources
**Expected**: Final theme state consistent, no crashes
**Implementation**: Last-write-wins with proper validation

#### 10. System Preference Change During First Visit
**Scenario**: User changes OS theme while first page load in progress
**Test**: Trigger matchMedia change during initialization
**Expected**: System preference listener detects change
**Implementation**: Register listener early in mount

### Testing Technical Debt

#### 1. No Frontend Test Framework
**Status**: No vitest, jest, or testing library installed
**Impact**: Cannot write frontend tests without setup
**Recommendation**: Install Vitest as part of Phase 0 (highest priority)

#### 2. No Browser API Mocking Library
**Status**: No dedicated mocking utilities for localStorage, matchMedia
**Impact**: Each test must manually mock these APIs
**Recommendation**: Create mock utilities file (test-utils.tsx, mocks/browser-mocks.ts)

#### 3. No E2E Test Framework
**Status**: No Playwright or Cypress
**Impact**: Cannot test full user flows across tabs, persistence
**Recommendation**: Optional but recommended for critical flows (Phase 5)

#### 4. No Component Styling Tests
**Status**: No tests verify Tailwind classes applied correctly
**Impact**: Dark variants could be missing without detection
**Recommendation**: Add component rendering tests to verify CSS classes (Phase 4)

### Testing Requirements from CLAUDE.md

Per project guidelines, this feature MUST have:

1. **Unit Tests** (>80% coverage of ThemeContext and utilities)
   - All state transitions
   - All utility functions
   - All error paths
   - Edge cases

2. **Integration Tests**
   - localStorage read/write
   - System preference detection
   - Cross-tab synchronization
   - Component rendering with theme

3. **End-to-End Tests** (critical user flows)
   - Theme toggle works
   - Theme persists across reload
   - System preference respected on first visit

4. **Pristine Test Output**
   - No warnings or errors
   - All tests pass
   - Clear test names describing scenarios
   - Proper cleanup and isolation

5. **No Test Code in Production**
   - All tests in `__tests__` directory or `.test.tsx` files
   - No mock modes or fake implementations
   - All test infrastructure separate from main code

## Testing Strategy

### Test Pyramid Balance

**Recommended Distribution**:
- **70% Unit Tests**: Fast, isolated, comprehensive coverage
  - ThemeContext state management (5 test cases)
  - Theme utilities (13 test cases)
  - useTheme hook (5 test cases)
  - Total: ~23 unit tests, 1-2 minutes execution time

- **25% Integration Tests**: Real dependencies, browser APIs
  - localStorage persistence (6 test cases)
  - Cross-tab synchronization (6 test cases)
  - System preference detection (6 test cases)
  - Component rendering (8 test cases)
  - Total: ~26 integration tests, 2-3 minutes execution time

- **5% End-to-End Tests**: Critical user flows only
  - Theme toggle flow (1 test)
  - Theme persistence across reload (1 test)
  - System preference on first visit (1 test)
  - Cross-tab sync (1 test)
  - Total: ~4 E2E tests, 10-15 seconds per test

**Rationale**:
- Unit tests are fastest and catch most bugs at component level
- Integration tests verify browser API interactions and data persistence
- E2E tests cover critical user journeys but are slower and more brittle

### CI Integration (Recommended Future Addition)

**Frontend Test Script** (add to `.github/workflows/frontend-tests.yml`):
```yaml
name: Frontend Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: cd frontend && npm install
      - run: cd frontend && npm test -- --run
      - run: cd frontend && npm run test:coverage
      - uses: codecov/codecov-action@v3
        with:
          files: ./frontend/coverage/coverage-final.json
          flags: frontend
```

### Coverage Goals

**Targets**:
- **ThemeContext**: 100% coverage (critical logic)
- **Theme utilities**: 100% coverage (pure functions, all paths testable)
- **useTheme hook**: 100% coverage (context wrapper)
- **System preference detection**: 100% coverage (cross-browser compatibility critical)
- **localStorage integration**: 100% coverage (persistence critical)
- **Cross-tab sync**: 100% coverage (multi-tab scenarios complex)
- **Components**: 80%+ coverage of styled components

**Measurement**:
```bash
npm run test:coverage
# Generates HTML report in coverage/
```

### Test Quality Checklist

Before merging theme feature implementation, verify:

- [ ] All unit tests pass (23+ tests)
- [ ] All integration tests pass (26+ tests)
- [ ] Test coverage >95% for ThemeContext, utilities, hooks
- [ ] Theme toggle works in all components
- [ ] Dark variants applied correctly to all color-dependent elements
- [ ] localStorage persistence tested (save, load, corruption, quota exceeded)
- [ ] System preference detected correctly (dark, light, unavailable)
- [ ] Cross-tab sync tested (storage events, cleanup)
- [ ] Private browsing handled gracefully
- [ ] Rapid toggling doesn't cause issues
- [ ] No console errors or warnings in test output
- [ ] Tests are isolated (can run in any order)
- [ ] Proper cleanup after each test
- [ ] Test names clearly describe scenario being tested
- [ ] All async operations properly awaited
- [ ] All mocks properly reset between tests
- [ ] No flaky tests (run 10x to verify consistency)

### Test Maintenance

**Best Practices**:

1. **Descriptive Test Names**:
   - `test_theme_context_initializes_with_system_preference()` ✓
   - `test_init()` ✗

2. **One Assertion per Test**:
   - Each test verifies one behavior
   - Easier to understand failures

3. **AAA Pattern**:
   - **Arrange**: Setup test data and mocks
   - **Act**: Call function or render component
   - **Assert**: Verify outcome

4. **DRY Fixtures**:
   - Extract common setup to test utilities
   - Reuse mocks across tests

5. **Mock External Dependencies**:
   - Always mock localStorage, matchMedia, storage events
   - Never use real browser APIs in tests

6. **Cleanup After Tests**:
   - Use Vitest afterEach hooks
   - Reset mocks between tests
   - Remove DOM elements

7. **Avoid Test Interdependence**:
   - Each test should pass independently
   - No shared state between tests
   - Can run tests in any order

8. **Test Behavior, Not Implementation**:
   - Test that theme persists (behavior)
   - Don't test internal implementation details
   - Focus on user-facing outcomes

**Anti-Patterns to Avoid**:
- ❌ Testing implementation details (how localStorage called)
- ❌ Complex test setup obscuring what's being tested
- ❌ Using sleep() for timing (use proper mocks)
- ❌ Sharing mutable state between tests
- ❌ Testing multiple scenarios in one test
- ❌ Ignoring test failures or flaky tests

## Summary

Pablo, this feature requires comprehensive testing across unit, integration, and E2E layers for a robust theme system:

### Key Testing Considerations

1. **Browser APIs**: localStorage and window.matchMedia are external dependencies that must be mocked in tests
2. **State Management**: ThemeContext manages theme state, system preference detection, and localStorage persistence
3. **Cross-Tab Sync**: Storage events require careful mocking to test multi-tab scenarios
4. **Fallback Handling**: System must work gracefully when APIs unavailable (private browsing, older browsers)
5. **Component Styling**: All components need Tailwind dark: variants and tests verifying they're applied

### Priority 1 Tasks
1. **Install testing framework**: Vitest + React Testing Library
2. **Create ThemeContext**: With localStorage persistence and system preference detection
3. **Write unit tests**: >80% coverage of ThemeContext, utilities, hooks (23+ tests)

### Priority 2 Tasks
1. **Write integration tests**: localStorage, system preference, cross-tab sync (26+ tests)
2. **Update components**: Add dark: variants to all color-dependent elements
3. **Create component rendering tests**: Verify dark classes applied correctly

### Priority 3 Tasks
1. **Write E2E tests**: Theme toggle, persistence, system preference flows
2. **Setup CI**: Add frontend test scripts to GitHub Actions
3. **Coverage reporting**: Generate and track coverage metrics

### Test Infrastructure Gaps
- No frontend testing framework (need Vitest)
- No React Testing Library (need @testing-library/react)
- No E2E framework (optional but recommended: Playwright)
- No mock utilities for browser APIs (create test utilities)

### Critical Edge Cases to Test
1. localStorage unavailable (private browsing, quota exceeded)
2. window.matchMedia unavailable (older browsers)
3. Corrupted localStorage values (invalid data recovery)
4. Rapid theme toggling (no memory leaks, consistent state)
5. System theme changes during session (listener updates theme)
6. Multiple tabs with rapid updates (eventual consistency)
7. Missing dark variants on components (CSS classes verification)

The testing strategy prioritizes unit tests for fast feedback, integration tests for API interactions, and selective E2E tests for critical user flows. All tests must produce pristine output with no warnings or errors, following strict testing requirements from CLAUDE.md.

