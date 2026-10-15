import React, { useState, useMemo, useEffect } from 'react';
import { ThemeContext } from './themeContextObject';

export function ThemeProvider({ children }) {
  const [darkMode, setDarkMode] = useState(false);

  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkMode);
  }, [darkMode]);

  const toggleDarkMode = () => setDarkMode(prev => !prev);

  const value = useMemo(() => {
    return {
      darkMode,
      setDarkMode,
      toggleDarkMode,
      glassClass: darkMode ? 'glass-dark' : 'glass-light',
      textPrimary: darkMode ? 'text-white' : 'text-slate-800',
      textSecondary: darkMode ? 'text-slate-300' : 'text-slate-600',
      textMuted: darkMode ? 'text-slate-400' : 'text-slate-500',
      borderClass: darkMode ? 'border-white/10' : 'border-slate-200',
      inputClass: darkMode
        ? 'bg-black/30 border-white/10 text-white placeholder-slate-400 focus:ring-emerald-400'
        : 'bg-white/60 border-slate-200 text-slate-800 placeholder-slate-400 focus:ring-emerald-600',
    };
  }, [darkMode]);

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
}
