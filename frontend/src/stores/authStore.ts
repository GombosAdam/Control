import { create } from 'zustand';
import type { User } from '../types/user';
import { authApi } from '../services/api/auth';

interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  restoreSession: () => void;
}

export const useAuthStore = create<AuthState>()((set) => ({
  user: null,
  token: null,
  isLoading: true,
  isAuthenticated: false,

  login: async (email: string, password: string) => {
    const response = await authApi.login(email, password);
    sessionStorage.setItem('token', response.token);
    sessionStorage.setItem('currentUser', JSON.stringify(response.user));
    set({ user: response.user, token: response.token, isAuthenticated: true, isLoading: false });
  },

  logout: () => {
    sessionStorage.removeItem('token');
    sessionStorage.removeItem('currentUser');
    set({ user: null, token: null, isAuthenticated: false });
  },

  restoreSession: () => {
    const token = sessionStorage.getItem('token');
    const saved = sessionStorage.getItem('currentUser');
    if (token && saved) {
      try {
        const user = JSON.parse(saved);
        set({ user, token, isAuthenticated: true, isLoading: false });
      } catch {
        sessionStorage.removeItem('token');
        sessionStorage.removeItem('currentUser');
        set({ isLoading: false });
      }
    } else {
      set({ isLoading: false });
    }
  },
}));
