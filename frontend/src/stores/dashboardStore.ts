import { create } from 'zustand';
import type { Notification } from '../types/api';

interface DashboardState {
  sidebarOpen: boolean;
  activePanel: string;
  notifications: Notification[];
  toggleSidebar: () => void;
  setActivePanel: (panel: string) => void;
  addNotification: (n: Notification) => void;
  dismissNotification: (id: string) => void;
  markAllRead: () => void;
  clearNotifications: () => void;
}

export const useDashboardStore = create<DashboardState>((set) => ({
  sidebarOpen: true,
  activePanel: 'overview',
  notifications: [],

  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),

  setActivePanel: (panel) => set({ activePanel: panel }),

  addNotification: (n) =>
    set((s) => ({
      notifications: [n, ...s.notifications].slice(0, 50),
    })),

  dismissNotification: (id) =>
    set((s) => ({
      notifications: s.notifications.filter((n) => n.id !== id),
    })),

  markAllRead: () =>
    set((s) => ({
      notifications: s.notifications.map((n) => ({ ...n, read: true })),
    })),

  clearNotifications: () => set({ notifications: [] }),
}));
