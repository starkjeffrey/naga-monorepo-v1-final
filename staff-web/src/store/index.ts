/**
 * Global State Management
 * Zustand-based store with React Query integration
 */

import { create } from 'zustand';
import { subscribeWithSelector, devtools } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';

// App-wide state interface
interface AppState {
  // UI State
  ui: {
    sidebarCollapsed: boolean;
    theme: 'light' | 'dark' | 'auto';
    language: string;
    loading: boolean;
    error: string | null;
  };

  // User State
  user: {
    profile: any | null;
    permissions: string[];
    preferences: Record<string, any>;
  };

  // Navigation State
  navigation: {
    currentPath: string;
    breadcrumbs: Array<{ label: string; path: string }>;
    recentPages: Array<{ label: string; path: string; timestamp: Date }>;
  };

  // Data State
  data: {
    students: any[];
    courses: any[];
    enrollments: any[];
    lastUpdated: Date | null;
  };
}

interface AppActions {
  // UI Actions
  toggleSidebar: () => void;
  setTheme: (theme: AppState['ui']['theme']) => void;
  setLanguage: (language: string) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;

  // User Actions
  setUser: (user: AppState['user']['profile']) => void;
  setPermissions: (permissions: string[]) => void;
  updatePreferences: (preferences: Partial<AppState['user']['preferences']>) => void;

  // Navigation Actions
  setCurrentPath: (path: string) => void;
  setBreadcrumbs: (breadcrumbs: AppState['navigation']['breadcrumbs']) => void;
  addRecentPage: (page: { label: string; path: string }) => void;

  // Data Actions
  setStudents: (students: any[]) => void;
  setCourses: (courses: any[]) => void;
  setEnrollments: (enrollments: any[]) => void;
  updateDataTimestamp: () => void;

  // Global Actions
  reset: () => void;
}

const initialState: AppState = {
  ui: {
    sidebarCollapsed: false,
    theme: 'light',
    language: 'en',
    loading: false,
    error: null,
  },
  user: {
    profile: null,
    permissions: [],
    preferences: {},
  },
  navigation: {
    currentPath: '/',
    breadcrumbs: [],
    recentPages: [],
  },
  data: {
    students: [],
    courses: [],
    enrollments: [],
    lastUpdated: null,
  },
};

export const useAppStore = create<AppState & AppActions>()(
  devtools(
    subscribeWithSelector(
      immer((set, get) => ({
        ...initialState,

        // UI Actions
        toggleSidebar: () =>
          set((state) => {
            state.ui.sidebarCollapsed = !state.ui.sidebarCollapsed;
          }),

        setTheme: (theme) =>
          set((state) => {
            state.ui.theme = theme;
          }),

        setLanguage: (language) =>
          set((state) => {
            state.ui.language = language;
          }),

        setLoading: (loading) =>
          set((state) => {
            state.ui.loading = loading;
          }),

        setError: (error) =>
          set((state) => {
            state.ui.error = error;
          }),

        // User Actions
        setUser: (user) =>
          set((state) => {
            state.user.profile = user;
          }),

        setPermissions: (permissions) =>
          set((state) => {
            state.user.permissions = permissions;
          }),

        updatePreferences: (preferences) =>
          set((state) => {
            state.user.preferences = { ...state.user.preferences, ...preferences };
          }),

        // Navigation Actions
        setCurrentPath: (path) =>
          set((state) => {
            state.navigation.currentPath = path;
          }),

        setBreadcrumbs: (breadcrumbs) =>
          set((state) => {
            state.navigation.breadcrumbs = breadcrumbs;
          }),

        addRecentPage: (page) =>
          set((state) => {
            const recent = state.navigation.recentPages.filter(p => p.path !== page.path);
            state.navigation.recentPages = [
              { ...page, timestamp: new Date() },
              ...recent
            ].slice(0, 10); // Keep only last 10 pages
          }),

        // Data Actions
        setStudents: (students) =>
          set((state) => {
            state.data.students = students;
            state.data.lastUpdated = new Date();
          }),

        setCourses: (courses) =>
          set((state) => {
            state.data.courses = courses;
            state.data.lastUpdated = new Date();
          }),

        setEnrollments: (enrollments) =>
          set((state) => {
            state.data.enrollments = enrollments;
            state.data.lastUpdated = new Date();
          }),

        updateDataTimestamp: () =>
          set((state) => {
            state.data.lastUpdated = new Date();
          }),

        // Global Actions
        reset: () => set(initialState),
      }))
    ),
    {
      name: 'staff-web-store',
    }
  )
);

// Selector hooks for better performance
export const useUI = () => useAppStore((state) => state.ui);
export const useUser = () => useAppStore((state) => state.user);
export const useNavigation = () => useAppStore((state) => state.navigation);
export const useData = () => useAppStore((state) => state.data);

// Action hooks
export const useUIActions = () => useAppStore((state) => ({
  toggleSidebar: state.toggleSidebar,
  setTheme: state.setTheme,
  setLanguage: state.setLanguage,
  setLoading: state.setLoading,
  setError: state.setError,
}));

export const useUserActions = () => useAppStore((state) => ({
  setUser: state.setUser,
  setPermissions: state.setPermissions,
  updatePreferences: state.updatePreferences,
}));

export const useNavigationActions = () => useAppStore((state) => ({
  setCurrentPath: state.setCurrentPath,
  setBreadcrumbs: state.setBreadcrumbs,
  addRecentPage: state.addRecentPage,
}));

export const useDataActions = () => useAppStore((state) => ({
  setStudents: state.setStudents,
  setCourses: state.setCourses,
  setEnrollments: state.setEnrollments,
  updateDataTimestamp: state.updateDataTimestamp,
}));

export default useAppStore;