import { create } from 'zustand';

interface UiState {
  sidebarOpen: boolean;
  language: string;
  toggleSidebar: () => void;
  setLanguage: (lang: string) => void;
}

export const useUiStore = create<UiState>()((set) => ({
  sidebarOpen: true,
  language: 'hu',
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setLanguage: (lang: string) => set({ language: lang }),
}));
