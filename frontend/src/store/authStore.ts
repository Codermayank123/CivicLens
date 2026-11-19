import { create } from 'zustand';
import { UserProfile } from '../types';
import { authService } from '../services/auth.service';

interface AuthState {
  user: UserProfile | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  setUser: (user: UserProfile | null) => void;
  initAuth: () => Promise<void>;
  logout: () => Promise<void>;
  hasRole: (role: string) => boolean;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: authService.getStoredUser(),
  isAuthenticated: !!localStorage.getItem('civiclens_access_token'),
  isLoading: !!localStorage.getItem('civiclens_access_token'),

  setUser: (user) => {
    set({ user, isAuthenticated: !!user });
  },

  initAuth: async () => {
    const token = localStorage.getItem('civiclens_access_token');
    if (!token) {
      set({ user: null, isAuthenticated: false, isLoading: false });
      return;
    }

    try {
      set({ isLoading: true });
      const user = await authService.getMe();
      set({ user, isAuthenticated: true, isLoading: false });
    } catch {
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
  },

  logout: async () => {
    await authService.logout();
    set({ user: null, isAuthenticated: false });
  },

  hasRole: (role: string) => {
    const user = get().user;
    if (!user || !user.roles) return false;
    return user.roles.includes(role) || user.roles.includes('admin');
  },
}));
