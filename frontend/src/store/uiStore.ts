import { create } from 'zustand';

const applyAccessibilityClasses = (dark: boolean, largeText: boolean) => {
  if (typeof document === 'undefined') return;
  document.documentElement.classList.toggle('dark', dark);
  document.documentElement.classList.toggle('text-lg', largeText);
};

const storedTheme = typeof localStorage !== 'undefined' ? localStorage.getItem('civiclens_theme') : null;
const initialDarkMode = storedTheme
  ? storedTheme === 'dark'
  : typeof window !== 'undefined' && typeof window.matchMedia === 'function' && window.matchMedia('(prefers-color-scheme: dark)').matches;
const initialLargeText = typeof localStorage !== 'undefined' && localStorage.getItem('civiclens_large_text') === 'true';
applyAccessibilityClasses(initialDarkMode, initialLargeText);

interface UIState {
  darkMode: boolean;
  largeText: boolean;
  isOnline: boolean;
  toggleDarkMode: () => void;
  toggleLargeText: () => void;
  setOnlineStatus: (status: boolean) => void;
}

export const useUIStore = create<UIState>((set, get) => ({
  darkMode: initialDarkMode,
  largeText: initialLargeText,
  isOnline: typeof navigator !== 'undefined' ? navigator.onLine : true,

  toggleDarkMode: () => {
    const next = !get().darkMode;
    set({ darkMode: next });
    localStorage.setItem('civiclens_theme', next ? 'dark' : 'light');
    applyAccessibilityClasses(next, get().largeText);
  },

  toggleLargeText: () => {
    const next = !get().largeText;
    set({ largeText: next });
    localStorage.setItem('civiclens_large_text', String(next));
    applyAccessibilityClasses(get().darkMode, next);
  },

  setOnlineStatus: (isOnline) => {
    set({ isOnline });
  },
}));
