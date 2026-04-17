import { create } from 'zustand';
import { authApi } from '../services/api/auth';

interface PermissionState {
  permissions: Set<string>;
  isLoaded: boolean;
  loadPermissions: () => Promise<void>;
  hasPermission: (resource: string, action: string) => boolean;
  hasAnyPermission: (resource: string) => boolean;
  clear: () => void;
}

export const usePermissionStore = create<PermissionState>()((set, get) => ({
  permissions: new Set<string>(),
  isLoaded: false,

  loadPermissions: async () => {
    try {
      const data = await authApi.getMyPermissions();
      const perms = new Set<string>(data.permissions);
      sessionStorage.setItem('permissions', JSON.stringify(data.permissions));
      set({ permissions: perms, isLoaded: true });
    } catch {
      // Fallback: try restoring from sessionStorage
      const saved = sessionStorage.getItem('permissions');
      if (saved) {
        try {
          set({ permissions: new Set(JSON.parse(saved)), isLoaded: true });
        } catch {
          set({ isLoaded: true });
        }
      } else {
        set({ isLoaded: true });
      }
    }
  },

  hasPermission: (resource: string, action: string) => {
    return get().permissions.has(`${resource}:${action}`);
  },

  hasAnyPermission: (resource: string) => {
    const prefix = `${resource}:`;
    for (const p of get().permissions) {
      if (p.startsWith(prefix)) return true;
    }
    return false;
  },

  clear: () => {
    sessionStorage.removeItem('permissions');
    set({ permissions: new Set(), isLoaded: false });
  },
}));
