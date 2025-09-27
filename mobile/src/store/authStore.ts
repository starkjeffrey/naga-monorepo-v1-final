import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import AsyncStorage from '@react-native-async-storage/async-storage';

interface User {
  id: string;
  name: string;
  email: string;
  role: 'student' | 'teacher' | 'admin' | 'ma_teacher'; // MA students who teach
  studentId?: string;
  teacherId?: string;
  profilePhoto?: string;
  department?: string;
  currentAcademicYear?: string;
  enrollmentStatus?: 'active' | 'inactive' | 'graduated';
  permissions?: string[];
}

interface AuthStore {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  selectedRole?: 'student' | 'teacher'; // For MA students who can switch roles

  // Actions
  login: (user: User, token: string) => void;
  logout: () => void;
  setLoading: (loading: boolean) => void;
  updateUser: (user: Partial<User>) => void;
  switchRole: (role: 'student' | 'teacher') => void;
  hasPermission: (permission: string) => boolean;
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,
      selectedRole: undefined,

      login: (user: User, token: string) => {
        // Set default role for MA teachers
        let defaultRole: 'student' | 'teacher' | undefined;
        if (user.role === 'ma_teacher') {
          defaultRole = 'student'; // Default to student view for MA teachers
        }

        set({
          user,
          token,
          isAuthenticated: true,
          isLoading: false,
          selectedRole: defaultRole,
        });
      },

      logout: () => {
        set({
          user: null,
          token: null,
          isAuthenticated: false,
          isLoading: false,
          selectedRole: undefined,
        });
      },

      setLoading: (loading: boolean) => {
        set({ isLoading: loading });
      },

      updateUser: (userData: Partial<User>) => {
        const currentUser = get().user;
        if (currentUser) {
          set({
            user: { ...currentUser, ...userData },
          });
        }
      },

      switchRole: (role: 'student' | 'teacher') => {
        const currentUser = get().user;
        // Only MA teachers can switch roles
        if (currentUser?.role === 'ma_teacher') {
          set({ selectedRole: role });
        }
      },

      hasPermission: (permission: string) => {
        const currentUser = get().user;
        return currentUser?.permissions?.includes(permission) || false;
      },
    }),
    {
      name: 'auth-store',
      storage: {
        getItem: async (name: string) => {
          const value = await AsyncStorage.getItem(name);
          return value ? JSON.parse(value) : null;
        },
        setItem: async (name: string, value: any) => {
          await AsyncStorage.setItem(name, JSON.stringify(value));
        },
        removeItem: async (name: string) => {
          await AsyncStorage.removeItem(name);
        },
      },
    }
  )
);