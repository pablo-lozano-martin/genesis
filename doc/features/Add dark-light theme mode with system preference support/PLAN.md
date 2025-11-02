# Implementation Plan: Dark/Light Theme Mode with System Preference Support

## Executive Summary

Feature adds dark/light theme mode with system preference detection, localStorage persistence, cross-tab sync, and comprehensive test coverage.

**Key Requirements:**
- Theme state management via ThemeContext (light/dark/system modes)
- localStorage persistence with graceful degradation
- System preference detection via window.matchMedia
- Cross-tab synchronization via storage events
- Dark variants for all components (TailwindCSS)
- >80% unit test coverage
- Integration tests for persistence, sync, and system detection
- E2E tests for critical flows

## Prerequisites

### Install Testing Framework (MUST DO FIRST)
```bash
cd /Users/pablolozano/Mac\ Projects\ August/genesis/frontend
npm install -D vitest @vitest/ui @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom
```

## Phase 1: Testing Infrastructure Setup

### 1.1 Create Vitest Configuration
**File:** `frontend/vitest.config.ts`

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

### 1.2 Create Test Setup File
**File:** `frontend/src/__tests__/setup.ts`

```typescript
import '@testing-library/jest-dom'
import { expect, afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'

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

### 1.3 Update package.json Scripts
**File:** `frontend/package.json`

Add to scripts section:
```json
"test": "vitest",
"test:ui": "vitest --ui",
"test:coverage": "vitest --coverage"
```

### 1.4 Verify Setup
```bash
npm test -- --run
```

## Phase 2: Theme Context & Utilities (with Unit Tests)

### 2.1 Create Theme Utilities
**File:** `frontend/src/lib/themeUtils.ts`

```typescript
// ABOUTME: Theme utility functions for system preference detection and localStorage management
// ABOUTME: Handles browser API fallbacks for cross-browser compatibility

export type ThemeMode = 'light' | 'dark' | 'system';

/**
 * Detects system preference for color scheme
 * Returns 'dark' if system prefers dark, 'light' otherwise
 * Falls back to 'light' if matchMedia unavailable (older browsers)
 */
export function detectSystemPreference(): 'light' | 'dark' {
  if (typeof window === 'undefined' || !window.matchMedia) {
    return 'light'; // Fallback for older browsers
  }

  try {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    return mediaQuery.matches ? 'dark' : 'light';
  } catch (error) {
    console.warn('Failed to detect system preference:', error);
    return 'light';
  }
}

/**
 * Gets stored theme preference from localStorage
 * Returns null if no preference saved or if value is corrupted
 */
export function getStoredTheme(): ThemeMode | null {
  try {
    const stored = localStorage.getItem('theme');
    if (stored === 'light' || stored === 'dark' || stored === 'system') {
      return stored;
    }
    return null; // Invalid value
  } catch (error) {
    // localStorage unavailable (private browsing, etc.)
    return null;
  }
}

/**
 * Saves theme preference to localStorage
 * Handles quota exceeded and disabled localStorage gracefully
 */
export function saveTheme(theme: ThemeMode): void {
  try {
    localStorage.setItem('theme', theme);
  } catch (error) {
    // Handle QuotaExceededError or disabled localStorage
    console.warn('Failed to save theme preference:', error);
  }
}

/**
 * Resolves initial theme based on priority:
 * 1. Saved preference (localStorage)
 * 2. System preference (matchMedia)
 * 3. Light theme (default fallback)
 */
export function resolveInitialTheme(): ThemeMode {
  const saved = getStoredTheme();
  if (saved) return saved;

  const systemPreference = detectSystemPreference();
  return systemPreference === 'dark' ? 'system' : 'light';
}

/**
 * Listens to system preference changes
 * Returns cleanup function to remove listener
 */
export function listenToSystemPreference(
  callback: (preference: 'light' | 'dark') => void
): () => void {
  if (typeof window === 'undefined' || !window.matchMedia) {
    return () => {}; // No-op cleanup for older browsers
  }

  try {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = (e: MediaQueryListEvent) => {
      callback(e.matches ? 'dark' : 'light');
    };

    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  } catch (error) {
    console.warn('Failed to setup system preference listener:', error);
    return () => {};
  }
}
```

### 2.2 Create ThemeContext
**File:** `frontend/src/contexts/ThemeContext.tsx`

```typescript
// ABOUTME: Theme context for managing dark/light mode state across the application
// ABOUTME: Provides theme state, toggle function, system preference detection, and localStorage persistence

import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import {
  detectSystemPreference,
  getStoredTheme,
  saveTheme,
  resolveInitialTheme,
  listenToSystemPreference,
  type ThemeMode
} from '../lib/themeUtils';

interface ThemeContextType {
  theme: ThemeMode;
  effectiveTheme: 'light' | 'dark';
  setTheme: (theme: ThemeMode) => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<ThemeMode>(resolveInitialTheme);
  const [systemPreference, setSystemPreference] = useState<'light' | 'dark'>(
    detectSystemPreference
  );

  // Calculate effective theme (resolve 'system' to actual light/dark)
  const effectiveTheme = theme === 'system' ? systemPreference : theme;

  // Set theme and persist to localStorage
  const setTheme = useCallback((newTheme: ThemeMode) => {
    setThemeState(newTheme);
    saveTheme(newTheme);
  }, []);

  // Apply theme class to document element
  useEffect(() => {
    const root = document.documentElement;
    if (effectiveTheme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
  }, [effectiveTheme]);

  // Listen to system preference changes
  useEffect(() => {
    const cleanup = listenToSystemPreference(setSystemPreference);
    return cleanup;
  }, []);

  // Listen to storage events (cross-tab sync)
  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'theme' && e.newValue) {
        const newTheme = e.newValue as ThemeMode;
        if (newTheme === 'light' || newTheme === 'dark' || newTheme === 'system') {
          setThemeState(newTheme);
        }
      }
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);

  return (
    <ThemeContext.Provider value={{ theme, effectiveTheme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme(): ThemeContextType {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
}
```

### 2.3 Unit Tests for Theme Utilities
**File:** `frontend/src/__tests__/unit/lib/themeUtils.test.ts`

Create 13 test cases covering:
- detectSystemPreference (dark/light/unavailable)
- getStoredTheme (saved/empty/corrupted)
- saveTheme (success/quota exceeded)
- resolveInitialTheme (priority logic)
- listenToSystemPreference (listener setup/changes)

### 2.4 Unit Tests for ThemeContext
**File:** `frontend/src/__tests__/unit/contexts/ThemeContext.test.tsx`

Create 10 test cases covering:
- Initialization (light/dark/system/saved preference)
- setTheme updates state and localStorage
- effectiveTheme resolves system correctly
- useTheme hook error handling
- Document element class application

### 2.5 Run Unit Tests
```bash
npm test -- src/__tests__/unit
```

## Phase 3: Tailwind Configuration & Component Infrastructure

### 3.1 Update Tailwind Config
**File:** `frontend/tailwind.config.js`

```javascript
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class', // CRITICAL: Enable class-based dark mode
  theme: {
    extend: {},
  },
  plugins: [],
}
```

### 3.2 Integrate ThemeProvider in App
**File:** `frontend/src/App.tsx`

**Change:**
```typescript
// Before:
<BrowserRouter>
  <AuthProvider>
    ...
  </AuthProvider>
</BrowserRouter>

// After:
import { ThemeProvider } from "./contexts/ThemeContext";

<BrowserRouter>
  <ThemeProvider>
    <AuthProvider>
      ...
    </AuthProvider>
  </ThemeProvider>
</BrowserRouter>
```

**Location:** After line 7 (import section), wrap at line 10 (return statement)

### 3.3 Create Theme Toggle Component
**File:** `frontend/src/components/ThemeToggle.tsx`

```typescript
// ABOUTME: Theme toggle button component for cycling through light/dark/system modes
// ABOUTME: Displays icon based on current theme and updates on click

import { useTheme } from "../contexts/ThemeContext";
import { Moon, Sun, Monitor } from "lucide-react";

export function ThemeToggle() {
  const { theme, effectiveTheme, setTheme } = useTheme();

  const handleToggle = () => {
    const themes = ['light', 'dark', 'system'] as const;
    const currentIndex = themes.indexOf(theme);
    const nextIndex = (currentIndex + 1) % themes.length;
    setTheme(themes[nextIndex]);
  };

  const getIcon = () => {
    if (theme === 'system') {
      return <Monitor className="h-5 w-5" />;
    }
    return effectiveTheme === 'dark' ?
      <Moon className="h-5 w-5" /> :
      <Sun className="h-5 w-5" />;
  };

  return (
    <button
      onClick={handleToggle}
      aria-label={`Current theme: ${theme}`}
      className="p-2 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
    >
      {getIcon()}
    </button>
  );
}
```

### 3.4 Add Theme Toggle to Chat Header
**File:** `frontend/src/pages/Chat.tsx`

**Location:** Line 32 (in header, before username)

**Change:**
```typescript
// Add import
import { ThemeToggle } from "../components/ThemeToggle";

// Update header div (line 32):
<div className="flex items-center gap-4">
  <ThemeToggle />  {/* ADD THIS LINE */}
  <div className="text-sm text-gray-600 dark:text-gray-400">{user?.username}</div>
  <button /* existing logout button */ />
</div>
```

## Phase 4: Component Dark Mode Updates

### 4.1 Chat.tsx
**File:** `frontend/src/pages/Chat.tsx`

**Changes:**
- Line 30: `bg-white` → `bg-white dark:bg-gray-800`
- Line 33: `text-gray-600` → `text-gray-600 dark:text-gray-400`
- Line 36: `text-gray-500 hover:text-gray-700` → `text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300`
- Line 53: `bg-white` → `bg-white dark:bg-gray-900`
- Line 55: `text-gray-400` → `text-gray-400 dark:text-gray-500`
- Line 61: `bg-red-50 text-red-600` → `bg-red-50 text-red-600 dark:bg-red-950/30 dark:text-red-400`
- Line 67: `bg-yellow-50 text-yellow-600` → `bg-yellow-50 text-yellow-600 dark:bg-yellow-950/30 dark:text-yellow-400`

### 4.2 ConversationSidebar.tsx
**File:** `frontend/src/components/chat/ConversationSidebar.tsx`

**Changes:**
- Line 60: `bg-gray-50` → `bg-gray-50 dark:bg-gray-900`
- Line 61: `border-b` → `border-b dark:border-gray-700`
- Line 74-75: `hover:bg-gray-100` → `hover:bg-gray-100 dark:hover:bg-gray-800`
- Line 75: `bg-gray-100` → `bg-gray-100 dark:bg-gray-800` (selected state)
- Line 89: Add `dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200`
- Line 104: `text-gray-500` → `text-gray-500 dark:text-gray-400`
- Line 114: `text-gray-400 hover:text-red-500` → `text-gray-400 hover:text-red-500 dark:text-gray-500 dark:hover:text-red-400`
- Line 123: `text-gray-400` → `text-gray-400 dark:text-gray-500`

### 4.3 MessageList.tsx
**File:** `frontend/src/components/chat/MessageList.tsx`

**Changes:**
- Line 27: `text-gray-400` → `text-gray-400 dark:text-gray-500`
- Line 39-41:
  - User: `bg-blue-500 text-white` → `bg-blue-500 text-white dark:bg-blue-600`
  - Assistant: `bg-gray-100 text-gray-900` → `bg-gray-100 text-gray-900 dark:bg-gray-800 dark:text-white`
- Line 63: `bg-gray-100 text-gray-900` → `bg-gray-100 text-gray-900 dark:bg-gray-800 dark:text-white`
- Line 67: `text-gray-400` → `text-gray-400 dark:text-gray-500`
- Lines 71-73: `bg-gray-400` → `bg-gray-400 dark:bg-gray-500` (animation dots)

### 4.4 MessageInput.tsx
**File:** `frontend/src/components/chat/MessageInput.tsx`

**Changes:**
- Line 43: `border-t` → `border-t dark:border-gray-700`
- Line 51: `border-gray-300` → `border-gray-300 dark:border-gray-600`
- Line 51: `disabled:bg-gray-100` → `disabled:bg-gray-100 dark:disabled:bg-gray-800`
- Line 51: Add `dark:bg-gray-800 dark:text-white`
- Line 60-62 (mic button):
  - Recording: `bg-red-50 border-red-500 text-red-600 hover:bg-red-100` → add `dark:bg-red-950/30 dark:border-red-800 dark:text-red-400 dark:hover:bg-red-950/50`
  - Not recording: `bg-white border-gray-300 text-gray-700 hover:bg-gray-50` → add `dark:bg-gray-800 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700`
- Line 74: `disabled:bg-gray-300` → `disabled:bg-gray-300 dark:disabled:bg-gray-700`
- Line 80: `text-red-500` → `text-red-500 dark:text-red-400`

### 4.5 MarkdownMessage.tsx
**File:** `frontend/src/components/chat/MarkdownMessage.tsx`

**CRITICAL: Fix hardcoded CSS import**

**Changes:**
- Line 8: Replace static import with dynamic import based on theme:

```typescript
import { useTheme } from "../../contexts/ThemeContext";

export function MarkdownMessage({ content }: MarkdownMessageProps) {
  const { effectiveTheme } = useTheme();

  useEffect(() => {
    // Dynamically load highlight.js CSS based on theme
    if (effectiveTheme === 'dark') {
      import('highlight.js/styles/github-dark.css');
    } else {
      import('highlight.js/styles/github-light.css');
    }
  }, [effectiveTheme]);

  // Rest of component...
}
```

- Line 21: `bg-gray-200 text-gray-800` → `bg-gray-200 text-gray-800 dark:bg-gray-700 dark:text-gray-200`
- Line 45: `text-blue-600 hover:text-blue-800` → `text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300`
- Line 77: `border-gray-300 bg-gray-50` → `border-gray-300 bg-gray-50 dark:border-gray-600 dark:bg-gray-800`
- Line 86: `border-gray-300` → `border-gray-300 dark:border-gray-600`
- Line 93: `bg-gray-100` → `bg-gray-100 dark:bg-gray-800`
- Line 99: `border-gray-300` → `border-gray-300 dark:border-gray-600`
- Line 103: `border-gray-300` → `border-gray-300 dark:border-gray-600`
- Line 109: `border-gray-300` → `border-gray-300 dark:border-gray-600`
- Line 113: `border-gray-300` → `border-gray-300 dark:border-gray-600`

### 4.6 ToolExecutionCard.tsx
**File:** `frontend/src/components/chat/ToolExecutionCard.tsx`

**Changes:**
- Line 18: Update conditional className:
  ```typescript
  isMcpTool
    ? "border-l-purple-500 bg-purple-50/50 dark:border-l-purple-900 dark:bg-purple-950/20"
    : "border-l-blue-500 bg-blue-50/50 dark:border-l-blue-900 dark:bg-blue-950/20"
  ```
- Line 22: `text-blue-600` → `text-blue-600 dark:text-blue-400`
- Line 25: `text-green-600` → `text-green-600 dark:text-green-400`
- Line 31: `bg-purple-100 text-purple-700` → `bg-purple-100 text-purple-700 dark:bg-purple-950/40 dark:text-purple-300`
- Line 36: `text-gray-600` → `text-gray-600 dark:text-gray-400`

### 4.7 Login.tsx
**File:** `frontend/src/pages/Login.tsx`

**Changes:**
- Line 32: `bg-gray-50` → `bg-gray-50 dark:bg-gray-950`
- Line 33: `bg-white` → `bg-white dark:bg-gray-800`
- Line 37: `bg-red-50 text-red-600` → `bg-red-50 text-red-600 dark:bg-red-950/30 dark:text-red-400`
- Line 50: `border` → `border border-gray-300 dark:border-gray-600`
- Line 50: Add `dark:bg-gray-900 dark:text-white`
- Line 68: `bg-blue-500 hover:bg-blue-600` → `bg-blue-500 hover:bg-blue-600 dark:bg-blue-600 dark:hover:bg-blue-700`
- Line 68: `disabled:bg-gray-300` → `disabled:bg-gray-300 dark:disabled:bg-gray-700`
- Line 74: `text-gray-600` → `text-gray-600 dark:text-gray-400`
- Line 76: `text-blue-500` → `text-blue-500 dark:text-blue-400`

### 4.8 Register.tsx
**File:** `frontend/src/pages/Register.tsx`

**Changes:** (Same pattern as Login.tsx)
- Line 34: `bg-gray-50` → `bg-gray-50 dark:bg-gray-950`
- Line 35: `bg-white` → `bg-white dark:bg-gray-800`
- Line 36: `text-gray-900` → `text-gray-900 dark:text-white`
- Line 39: `bg-red-50 text-red-600` → `bg-red-50 text-red-600 dark:bg-red-950/30 dark:text-red-400`
- Lines 52-79 (all inputs): Add `border-gray-300 dark:border-gray-600 dark:bg-gray-900 dark:text-white`
- Line 92: Button same as Login.tsx
- Text links: `text-gray-600` → `text-gray-600 dark:text-gray-400`, `text-blue-500` → `text-blue-500 dark:text-blue-400`

## Phase 5: Integration Tests

### 5.1 Theme Persistence Tests
**File:** `frontend/src/__tests__/integration/theme-persistence.test.tsx`

Create 6 test cases:
- Theme persists on page reload
- First visit uses system preference
- Manual preference overrides system
- Invalid localStorage falls back to system
- localStorage quota exceeded graceful handling
- Private browsing localStorage unavailable

### 5.2 Cross-Tab Synchronization Tests
**File:** `frontend/src/__tests__/integration/theme-sync.test.tsx`

Create 7 test cases:
- Storage event updates theme in other tab
- Storage event ignored if from same tab
- Storage event with invalid data ignored
- Multiple tabs stay in sync
- Storage listener cleanup on unmount
- Storage listener added on mount
- Rapid theme changes across tabs

### 5.3 System Preference Detection Tests
**File:** `frontend/src/__tests__/integration/system-preference.test.tsx`

Create 6 test cases:
- System preference dark detected
- System preference light detected
- matchMedia unavailable fallback
- System preference listener detects OS theme change
- System preference listener cleanup
- System preference ignored with saved preference

### 5.4 Component Rendering Tests
**File:** `frontend/src/__tests__/integration/theme-rendering.test.tsx`

Create 8 test cases:
- Document element dark class applied
- Document element dark class removed
- Dark Tailwind variants applied
- Light Tailwind variants applied
- Child components inherit theme
- Sidebar dark variant colors
- MessageList dark variant colors
- MarkdownMessage dark variant

### 5.5 Run Integration Tests
```bash
npm test -- src/__tests__/integration
```

## Phase 6: Manual Testing & Validation

### 6.1 Basic Flow Testing
1. Fresh browser (clear localStorage) → verify system preference detected
2. Toggle theme to light → reload → verify persists
3. Toggle to dark → reload → verify persists
4. Toggle to system → change OS theme → verify updates
5. Navigate Login → Register → Chat → verify consistent theme

### 6.2 Edge Case Testing
1. No system preference (mock older browser) → verify defaults to light
2. Rapid toggling (10 clicks fast) → verify no UI glitches
3. localStorage quota exceeded → verify graceful degradation
4. Mid-session OS theme change (system mode) → verify app updates
5. Multiple tabs → change theme tab 1 → verify tab 2 updates

### 6.3 Component Visual Validation
For each component (Chat, Sidebar, MessageList, etc.):
- Verify light mode: all backgrounds, text, borders correct
- Verify dark mode: all dark variants applied
- Verify hover states work in both modes
- Verify focus indicators visible in both modes

### 6.4 Accessibility Testing
- Check contrast ratios meet WCAG AA (use Chrome DevTools)
- Verify keyboard navigation works (Tab, Enter, Escape)
- Verify theme toggle button has proper aria-label
- Verify focus indicators visible in both modes

## Phase 7: End-to-End Tests (Optional)

### 7.1 Install Playwright
```bash
npm install -D @playwright/test
npx playwright install
```

### 7.2 Create E2E Tests
**File:** `frontend/e2e/theme-toggle.spec.ts`

Create 4 test cases:
- Theme toggle button switches appearance
- Theme persists after page reload
- System preference respected on first visit
- Manual theme overrides system preference

**File:** `frontend/e2e/theme-persistence.spec.ts`

Create 3 test cases:
- Theme survives multiple reloads
- Cross-tab synchronization
- Corrupted localStorage recovery

### 7.3 Run E2E Tests
```bash
npx playwright test
```

## Phase 8: Documentation & Cleanup

### 8.1 Update Frontend README
**File:** `frontend/README.md`

Add section:
```markdown
## Theme Support

The application supports light, dark, and system-based themes.

### Using Theme Context
Components can access theme via `useTheme()` hook:

import { useTheme } from './contexts/ThemeContext';

const { theme, effectiveTheme, setTheme } = useTheme();

### Adding Dark Mode to Components
Use Tailwind's `dark:` prefix for dark mode variants:

<div className="bg-white dark:bg-gray-900 text-gray-900 dark:text-white">
  Content
</div>

### Theme Values
- `light`: Light mode
- `dark`: Dark mode
- `system`: Follows OS preference

### Testing
Run theme tests: `npm test -- theme`
```

### 8.2 Add JSDoc to ThemeContext
**File:** `frontend/src/contexts/ThemeContext.tsx`

Add JSDoc comments to:
- ThemeProvider component
- useTheme hook
- ThemeContextType interface

## Critical Path Summary

**MUST DO IN ORDER:**

1. **Install testing dependencies** (Phase 1.0)
2. **Setup test infrastructure** (Phase 1.1-1.4)
3. **Create themeUtils.ts + unit tests** (Phase 2.1, 2.3)
4. **Create ThemeContext.tsx + unit tests** (Phase 2.2, 2.4)
5. **Run and verify unit tests pass** (Phase 2.5)
6. **Update tailwind.config.js** (Phase 3.1) - CRITICAL
7. **Integrate ThemeProvider in App.tsx** (Phase 3.2)
8. **Create ThemeToggle component** (Phase 3.3)
9. **Add ThemeToggle to Chat header** (Phase 3.4)
10. **Update all component dark variants** (Phase 4.1-4.8)
11. **Write integration tests** (Phase 5.1-5.4)
12. **Run and verify all tests pass** (Phase 5.5)
13. **Manual testing** (Phase 6.1-6.4)
14. **Documentation** (Phase 8.1-8.2)

**Optional but recommended:**
- E2E tests (Phase 7)

## Files to Create

**New Files:**
1. `frontend/vitest.config.ts` - Vitest configuration
2. `frontend/src/__tests__/setup.ts` - Test setup with mocks
3. `frontend/src/lib/themeUtils.ts` - Theme utility functions
4. `frontend/src/contexts/ThemeContext.tsx` - Theme context provider
5. `frontend/src/components/ThemeToggle.tsx` - Theme toggle UI
6. `frontend/src/__tests__/unit/lib/themeUtils.test.ts` - Utility tests
7. `frontend/src/__tests__/unit/contexts/ThemeContext.test.tsx` - Context tests
8. `frontend/src/__tests__/integration/theme-persistence.test.tsx` - Persistence tests
9. `frontend/src/__tests__/integration/theme-sync.test.tsx` - Sync tests
10. `frontend/src/__tests__/integration/system-preference.test.tsx` - System detection tests
11. `frontend/src/__tests__/integration/theme-rendering.test.tsx` - Component rendering tests

**Optional E2E:**
12. `frontend/playwright.config.ts` - Playwright config
13. `frontend/e2e/theme-toggle.spec.ts` - E2E toggle tests
14. `frontend/e2e/theme-persistence.spec.ts` - E2E persistence tests

## Files to Modify

**Configuration:**
1. `frontend/package.json` - Add test scripts
2. `frontend/tailwind.config.js` - Enable dark mode

**Core App:**
3. `frontend/src/App.tsx` - Add ThemeProvider wrapper

**Pages:**
4. `frontend/src/pages/Chat.tsx` - Dark variants + ThemeToggle
5. `frontend/src/pages/Login.tsx` - Dark variants
6. `frontend/src/pages/Register.tsx` - Dark variants

**Chat Components:**
7. `frontend/src/components/chat/ConversationSidebar.tsx` - Dark variants
8. `frontend/src/components/chat/MessageList.tsx` - Dark variants
9. `frontend/src/components/chat/MessageInput.tsx` - Dark variants
10. `frontend/src/components/chat/MarkdownMessage.tsx` - Dynamic CSS + dark variants
11. `frontend/src/components/chat/ToolExecutionCard.tsx` - Dark variants

**Documentation:**
12. `frontend/README.md` - Add theme usage docs

## Definition of Done Checklist

- [ ] Testing infrastructure installed and configured
- [ ] All utility functions created with >80% test coverage
- [ ] ThemeContext created with >80% test coverage
- [ ] Tailwind dark mode enabled (`darkMode: 'class'`)
- [ ] ThemeProvider integrated in App.tsx
- [ ] ThemeToggle component created and added to Chat header
- [ ] All components updated with dark: variants (11 files)
- [ ] MarkdownMessage dynamic CSS import working
- [ ] All unit tests pass (23+ tests)
- [ ] All integration tests pass (26+ tests)
- [ ] Manual testing complete (basic flow, edge cases, visual validation)
- [ ] Accessibility testing complete (contrast ratios, keyboard navigation)
- [ ] No console errors or warnings
- [ ] Theme persists across page reloads
- [ ] System preference detection works
- [ ] Cross-tab synchronization works
- [ ] Code reviewed and approved
- [ ] Documentation updated (README.md, JSDoc comments)
- [ ] CI/CD passes (if applicable)

## Risk Mitigation

**localStorage unavailable:**
- All localStorage calls wrapped in try/catch
- Falls back to system preference if storage fails
- Tests verify graceful degradation

**window.matchMedia unavailable:**
- Check existence before using
- Default to 'light' if API unavailable
- Tests verify fallback behavior

**Corrupted localStorage data:**
- Validate stored values against whitelist
- Ignore invalid data, use fallback
- Tests verify recovery

**Missing dark variants:**
- Systematic component update checklist
- Component rendering tests verify dark classes exist
- Manual visual validation per component

**CSS class conflicts:**
- Use classList.add/remove (not string manipulation)
- ThemeContext is sole owner of document dark class
- No third-party libraries modify root element

## Estimated Complexity

**Overall:** Medium-High

**Per Phase:**
- Phase 1 (Setup): 30 min - 1 hour
- Phase 2 (Context + Tests): 3-4 hours
- Phase 3 (Config + Toggle): 1 hour
- Phase 4 (Component Updates): 4-6 hours (11 files)
- Phase 5 (Integration Tests): 3-4 hours
- Phase 6 (Manual Testing): 2-3 hours
- Phase 7 (E2E, optional): 2-3 hours
- Phase 8 (Docs): 1 hour

**Total Estimated Time:** 16-23 hours (excluding E2E)

## Questions for Pablo

1. Should theme toggle cycle through all 3 modes (light/dark/system) or just 2 (light/dark)?
   - **Recommendation:** All 3 modes for flexibility

2. Should theme preference sync across tabs in real-time?
   - **Recommendation:** Yes, use storage events (already in plan)

3. Default theme on first visit: system preference or always light?
   - **Recommendation:** System preference (better UX)

4. Should we add transition animation for theme switch?
   - **Recommendation:** Subtle transition-colors (add to component classes)

5. Should E2E tests be included or skipped for MVP?
   - **Recommendation:** Include for critical flows (theme toggle, persistence)
