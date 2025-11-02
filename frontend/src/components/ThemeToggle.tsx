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
      className="p-2 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors text-gray-700 dark:text-gray-300"
    >
      {getIcon()}
    </button>
  );
}
