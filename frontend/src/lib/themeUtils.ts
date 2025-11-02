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
 * 2. Light theme (default fallback)
 */
export function resolveInitialTheme(): ThemeMode {
  const saved = getStoredTheme();
  if (saved) return saved;

  // Default to light on first visit
  return 'light';
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
