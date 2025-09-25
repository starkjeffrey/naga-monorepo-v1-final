/**
 * Custom hook for authentication functionality
 */

import { useCallback } from 'react';
import {
  useUser,
  useIsAuthenticated,
  useAuthLoading,
  useAuthError,
  useIsAuthInitialized,
  useAuthActions,
} from '../store/authStore';
import type { LoginCredentials, UseAuthReturn } from '../types/auth.types';

/**
 * Main authentication hook that provides all auth functionality
 */
export const useAuth = (): UseAuthReturn => {
  const user = useUser();
  const isAuthenticated = useIsAuthenticated();
  const isLoading = useAuthLoading();
  const error = useAuthError();
  const { login, logout, refreshAuth, clearError } = useAuthActions();

  // Wrap actions to ensure they're stable references
  const handleLogin = useCallback(
    async (credentials: LoginCredentials) => {
      await login(credentials);
    },
    [login]
  );

  const handleLogout = useCallback(() => {
    logout();
  }, [logout]);

  const handleRefreshAuth = useCallback(async () => {
    await refreshAuth();
  }, [refreshAuth]);

  const handleClearError = useCallback(() => {
    clearError();
  }, [clearError]);

  return {
    user,
    isAuthenticated,
    isLoading,
    error,
    login: handleLogin,
    logout: handleLogout,
    refreshAuth: handleRefreshAuth,
    clearError: handleClearError,
  };
};

/**
 * Hook to check if auth is initialized
 */
export const useAuthInitialization = () => {
  const isInitialized = useIsAuthInitialized();
  const { initializeAuth } = useAuthActions();

  return {
    isInitialized,
    initializeAuth,
  };
};

/**
 * Hook for checking user permissions
 */
export const usePermissions = () => {
  const user = useUser();

  const hasRole = useCallback(
    (role: string): boolean => {
      return Boolean(user?.roles?.includes(role));
    },
    [user]
  );

  const hasAnyRole = useCallback(
    (roles: string[]): boolean => {
      return Boolean(user?.roles?.some((role) => roles.includes(role)));
    },
    [user]
  );

  const hasAllRoles = useCallback(
    (roles: string[]): boolean => {
      return Boolean(roles.every((role) => user?.roles?.includes(role)));
    },
    [user]
  );

  return {
    isStaff: Boolean(user?.is_staff),
    isSuperuser: Boolean(user?.is_superuser),
    roles: user?.roles || [],
    hasRole,
    hasAnyRole,
    hasAllRoles,
  };
};

/**
 * Hook for authentication status checks
 */
export const useAuthStatus = () => {
  const isAuthenticated = useIsAuthenticated();
  const isLoading = useAuthLoading();
  const isInitialized = useIsAuthInitialized();

  return {
    isAuthenticated,
    isLoading,
    isInitialized,
    isReady: isInitialized && !isLoading,
  };
};

export default useAuth;