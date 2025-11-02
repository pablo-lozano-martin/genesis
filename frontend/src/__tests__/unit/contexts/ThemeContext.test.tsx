import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { ThemeProvider, useTheme } from '../../../contexts/ThemeContext';
import * as themeUtils from '../../../lib/themeUtils';

function TestComponent() {
  const { theme, effectiveTheme, setTheme } = useTheme();
  return (
    <div>
      <div data-testid="theme">{theme}</div>
      <div data-testid="effective">{effectiveTheme}</div>
      <button onClick={() => setTheme('dark')}>Set Dark</button>
      <button onClick={() => setTheme('light')}>Set Light</button>
      <button onClick={() => setTheme('system')}>Set System</button>
    </div>
  );
}

describe('ThemeContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    document.documentElement.classList.remove('dark');

    vi.spyOn(themeUtils, 'detectSystemPreference').mockReturnValue('light');
    vi.spyOn(themeUtils, 'getStoredTheme').mockReturnValue(null);
    vi.spyOn(themeUtils, 'saveTheme').mockImplementation(() => {});
    vi.spyOn(themeUtils, 'listenToSystemPreference').mockReturnValue(() => {});
  });

  it('initializes with light theme', () => {
    vi.spyOn(themeUtils, 'resolveInitialTheme').mockReturnValue('light');

    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );

    expect(screen.getByTestId('theme').textContent).toBe('light');
    expect(screen.getByTestId('effective').textContent).toBe('light');
  });

  it('initializes with dark theme', () => {
    vi.spyOn(themeUtils, 'resolveInitialTheme').mockReturnValue('dark');

    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );

    expect(screen.getByTestId('theme').textContent).toBe('dark');
    expect(screen.getByTestId('effective').textContent).toBe('dark');
  });

  it('initializes with system theme', () => {
    vi.spyOn(themeUtils, 'resolveInitialTheme').mockReturnValue('system');

    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );

    expect(screen.getByTestId('theme').textContent).toBe('system');
    expect(screen.getByTestId('effective').textContent).toBe('light');
  });

  it('initializes with saved preference from localStorage', () => {
    vi.spyOn(themeUtils, 'resolveInitialTheme').mockReturnValue('dark');

    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );

    expect(screen.getByTestId('theme').textContent).toBe('dark');
  });

  it('setTheme updates state and calls saveTheme', () => {
    vi.spyOn(themeUtils, 'resolveInitialTheme').mockReturnValue('light');

    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );

    act(() => {
      screen.getByText('Set Dark').click();
    });

    expect(screen.getByTestId('theme').textContent).toBe('dark');
    expect(themeUtils.saveTheme).toHaveBeenCalledWith('dark');
  });

  it('effectiveTheme resolves system to actual preference', () => {
    vi.spyOn(themeUtils, 'resolveInitialTheme').mockReturnValue('system');
    vi.spyOn(themeUtils, 'detectSystemPreference').mockReturnValue('dark');

    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );

    expect(screen.getByTestId('theme').textContent).toBe('system');
    expect(screen.getByTestId('effective').textContent).toBe('dark');
  });

  it('useTheme throws error when used outside ThemeProvider', () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => render(<TestComponent />)).toThrow('useTheme must be used within ThemeProvider');

    consoleError.mockRestore();
  });

  it('applies dark class to document element', () => {
    vi.spyOn(themeUtils, 'resolveInitialTheme').mockReturnValue('light');

    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );

    expect(document.documentElement.classList.contains('dark')).toBe(false);

    act(() => {
      screen.getByText('Set Dark').click();
    });

    expect(document.documentElement.classList.contains('dark')).toBe(true);

    act(() => {
      screen.getByText('Set Light').click();
    });

    expect(document.documentElement.classList.contains('dark')).toBe(false);
  });

  it('listens to system preference changes', () => {
    let preferenceCallback: ((pref: 'light' | 'dark') => void) | null = null;
    vi.spyOn(themeUtils, 'listenToSystemPreference').mockImplementation((cb) => {
      preferenceCallback = cb;
      return () => {};
    });
    vi.spyOn(themeUtils, 'resolveInitialTheme').mockReturnValue('system');

    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );

    expect(screen.getByTestId('effective').textContent).toBe('light');

    act(() => {
      preferenceCallback?.('dark');
    });

    expect(screen.getByTestId('effective').textContent).toBe('dark');
  });

  it('handles storage events for cross-tab sync', () => {
    vi.spyOn(themeUtils, 'resolveInitialTheme').mockReturnValue('light');

    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );

    expect(screen.getByTestId('theme').textContent).toBe('light');

    act(() => {
      const event = new StorageEvent('storage', {
        key: 'theme',
        newValue: 'dark',
      });
      window.dispatchEvent(event);
    });

    expect(screen.getByTestId('theme').textContent).toBe('dark');
  });
});
