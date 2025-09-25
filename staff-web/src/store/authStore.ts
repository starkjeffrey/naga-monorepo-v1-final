/**
 * Zustand store for authentication state management
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import AuthService from '../services/auth.service';
import { SUCCESS_MESSAGES, ERROR_MESSAGES } from '../utils/constants';
import type { User, LoginCredentials, ApiError } from '../types/auth.types';

/**
 * Authentication store state interface
 */
interface AuthState {
  // State
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  isInitialized: boolean;

  // Actions
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => void;
  refreshAuth: () => Promise<void>;
  clearError: () => void;
  initializeAuth: () => Promise<void>;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setUser: (user: User | null) => void;
}

/**
 * Create the authentication store
 */
export const useAuthStore = create<AuthState>()(
  devtools(
    persist(
      (set, get) => ({
        // Initial state
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,
        isInitialized: false,

        // Actions
        login: async (credentials: LoginCredentials) => {
          set({ isLoading: true, error: null });

          try {
            const { user } = await AuthService.login(credentials);

            set({
              user,
              isAuthenticated: true,
              isLoading: false,
              error: null,
            });

            // Optional: Show success message
            console.log(SUCCESS_MESSAGES.LOGIN_SUCCESS);
          } catch (error) {
            const apiError = error as ApiError;
            console.error('Login error:', apiError);

            set({
              user: null,
              isAuthenticated: false,
              isLoading: false,
              error: apiError.message || ERROR_MESSAGES.INVALID_CREDENTIALS,
            });

            throw error; // Re-throw for component handling
          }
        },

        logout: () => {
          set({ isLoading: true });

          AuthService.logout()
            .then(() => {
              set({
                user: null,
                isAuthenticated: false,
                isLoading: false,
                error: null,
              });

              console.log(SUCCESS_MESSAGES.LOGOUT_SUCCESS);
            })
            .catch((error) => {
              console.error('Logout error:', error);
              // Still clear the state even if server logout fails
              set({
                user: null,
                isAuthenticated: false,
                isLoading: false,
                error: null,
              });
            });
        },

        refreshAuth: async () => {
          try {
            const { user } = await AuthService.refreshToken();

            set({
              user,
              isAuthenticated: true,
              error: null,
            });
          } catch (error) {
            const apiError = error as ApiError;
            console.error('Token refresh error:', apiError);

            set({
              user: null,
              isAuthenticated: false,
              error: apiError.message || ERROR_MESSAGES.SESSION_EXPIRED,
            });

            throw error; // Re-throw for component handling
          }
        },

        clearError: () => {
          set({ error: null });
        },

        initializeAuth: async () => {
          if (get().isInitialized) {
            return; // Already initialized
          }

          set({ isLoading: true });

          try {
            const { user, isAuthenticated } = await AuthService.initializeAuth();

            set({
              user,
              isAuthenticated,
              isLoading: false,
              error: null,
              isInitialized: true,
            });
          } catch (error) {
            const apiError = error as ApiError;
            console.error('Auth initialization error:', apiError);

            set({
              user: null,
              isAuthenticated: false,
              isLoading: false,
              error: null, // Don't show error on initialization failure
              isInitialized: true,
            });
          }
        },

        setLoading: (loading: boolean) => {
          set({ isLoading: loading });
        },

        setError: (error: string | null) => {
          set({ error });
        },

        setUser: (user: User | null) => {
          set({
            user,
            isAuthenticated: Boolean(user),
          });
        },
      }),
      {
        name: 'auth-storage',
        partialize: (state) => ({
          // Only persist essential data, not loading/error states
          user: state.user,
          isAuthenticated: state.isAuthenticated,
        }),
        version: 1,
        migrate: (persistedState: any, version: number) => {
          // Handle migration if store structure changes
          if (version === 0) {
            // Migration from version 0 to 1
            return {
              ...persistedState,
              isInitialized: false, // Force re-initialization
            };
          }
          return persistedState;
        },
      }
    ),
    {
      name: 'auth-store', // DevTools name
    }
  )
);

/**
 * Selector hooks for common state access patterns
 */

// Get user data
export const useUser = () => useAuthStore((state) => state.user);

// Get authentication status
export const useIsAuthenticated = () => useAuthStore((state) => state.isAuthenticated);

// Get loading state
export const useAuthLoading = () => useAuthStore((state) => state.isLoading);

// Get error state
export const useAuthError = () => useAuthStore((state) => state.error);

// Get initialization status
export const useIsAuthInitialized = () => useAuthStore((state) => state.isInitialized);

// Get authentication actions
export const useAuthActions = () => useAuthStore((state) => ({
  login: state.login,
  logout: state.logout,
  refreshAuth: state.refreshAuth,
  clearError: state.clearError,
  initializeAuth: state.initializeAuth,
}));

/**
 * Utility selector for checking specific user permissions
 */
export const useHasRole = (role: string) => {
  return useAuthStore((state) =>
    Boolean(state.user?.roles?.includes(role))
  );
};

/**
 * Utility selector for checking if user is staff
 */
export const useIsStaff = () => {
  return useAuthStore((state) => Boolean(state.user?.is_staff));
};

/**
 * Utility selector for checking if user is superuser
 */
export const useIsSuperuser = () => {
  return useAuthStore((state) => Boolean(state.user?.is_superuser));
};

export default useAuthStore;