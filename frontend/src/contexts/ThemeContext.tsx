// ABOUTME: Theme context for managing dark/light mode state across the application
// ABOUTME: Provides theme state, toggle function, system preference detection, and localStorage persistence

import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import {
  detectSystemPreference,
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
