/**
 * Unit tests for AuthStore (Zustand store)
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import { useAuthStore, useUser, useIsAuthenticated, useAuthActions } from '../authStore';
import AuthService from '../../services/auth.service';
import { mockUser, mockCredentials } from '../../test/utils';
import type { ApiError } from '../../types/auth.types';

// Mock AuthService
vi.mock('../../services/auth.service', () => ({
  default: {
    login: vi.fn(),
    logout: vi.fn(),
    refreshToken: vi.fn(),
    initializeAuth: vi.fn(),
  },
}));

// Mock console methods
const mockConsole = {
  log: vi.fn(),
  error: vi.fn(),
};

vi.stubGlobal('console', mockConsole);

describe('AuthStore', () => {
  beforeEach(() => {
    // Reset store state
    useAuthStore.setState({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
      isInitialized: false,
    });

    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  describe('initial state', () => {
    it('should have correct initial state', () => {
      const { result } = renderHook(() => useAuthStore());

      expect(result.current.user).toBeNull();
      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
      expect(result.current.isInitialized).toBe(false);
    });
  });

  describe('login action', () => {
    it('should successfully login user', async () => {
      const mockLoginResponse = { user: mockUser };
      (AuthService.login as any).mockResolvedValue(mockLoginResponse);

      const { result } = renderHook(() => useAuthStore());

      await act(async () => {
        await result.current.login(mockCredentials);
      });

      expect(AuthService.login).toHaveBeenCalledWith(mockCredentials);
      expect(result.current.user).toEqual(mockUser);
      expect(result.current.isAuthenticated).toBe(true);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
      expect(mockConsole.log).toHaveBeenCalledWith('Successfully logged in!');
    });

    it('should handle login failure', async () => {
      const mockError: ApiError = {
        message: 'Invalid credentials',
        status: 401,
      };

      (AuthService.login as any).mockRejectedValue(mockError);

      const { result } = renderHook(() => useAuthStore());

      await act(async () => {
        try {
          await result.current.login(mockCredentials);
        } catch (error) {
          // Expected to throw
        }
      });

      expect(result.current.user).toBeNull();
      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBe('Invalid credentials');
      expect(mockConsole.error).toHaveBeenCalledWith('Login error:', mockError);
    });

    it('should set loading state during login', async () => {
      let resolveLogin: (value: any) => void;
      const loginPromise = new Promise((resolve) => {
        resolveLogin = resolve;
      });

      (AuthService.login as any).mockReturnValue(loginPromise);

      const { result } = renderHook(() => useAuthStore());

      // Start login
      act(() => {
        result.current.login(mockCredentials);
      });

      // Check loading state
      expect(result.current.isLoading).toBe(true);
      expect(result.current.error).toBeNull();

      // Complete login
      await act(async () => {
        resolveLogin({ user: mockUser });
        await loginPromise;
      });

      expect(result.current.isLoading).toBe(false);
    });

    it('should use fallback error message when none provided', async () => {
      const mockError = {}; // Error without message
      (AuthService.login as any).mockRejectedValue(mockError);

      const { result } = renderHook(() => useAuthStore());

      await act(async () => {
        try {
          await result.current.login(mockCredentials);
        } catch (error) {
          // Expected to throw
        }
      });

      expect(result.current.error).toBe('Invalid email or password.');
    });
  });

  describe('logout action', () => {
    beforeEach(() => {
      // Set authenticated state
      useAuthStore.setState({
        user: mockUser,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });
    });

    it('should successfully logout user', async () => {
      (AuthService.logout as any).mockResolvedValue(undefined);

      const { result } = renderHook(() => useAuthStore());

      await act(async () => {
        result.current.logout();
        // Wait for async operation to complete
        await new Promise(resolve => setTimeout(resolve, 0));
      });

      expect(AuthService.logout).toHaveBeenCalled();
      expect(result.current.user).toBeNull();
      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
      expect(mockConsole.log).toHaveBeenCalledWith('Successfully logged out!');
    });

    it('should clear state even if logout service fails', async () => {
      const mockError = new Error('Network error');
      (AuthService.logout as any).mockRejectedValue(mockError);

      const { result } = renderHook(() => useAuthStore());

      await act(async () => {
        result.current.logout();
        // Wait for async operation to complete
        await new Promise(resolve => setTimeout(resolve, 0));
      });

      expect(result.current.user).toBeNull();
      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
      expect(mockConsole.error).toHaveBeenCalledWith('Logout error:', mockError);
    });

    it('should set loading state during logout', async () => {
      let resolveLogout: () => void;
      const logoutPromise = new Promise<void>((resolve) => {
        resolveLogout = resolve;
      });

      (AuthService.logout as any).mockReturnValue(logoutPromise);

      const { result } = renderHook(() => useAuthStore());

      // Start logout
      act(() => {
        result.current.logout();
      });

      // Check loading state
      expect(result.current.isLoading).toBe(true);

      // Complete logout
      await act(async () => {
        resolveLogout();
        await logoutPromise;
      });

      expect(result.current.isLoading).toBe(false);
    });
  });

  describe('refreshAuth action', () => {
    it('should successfully refresh authentication', async () => {
      const mockRefreshResponse = { user: mockUser };
      (AuthService.refreshToken as any).mockResolvedValue(mockRefreshResponse);

      const { result } = renderHook(() => useAuthStore());

      await act(async () => {
        await result.current.refreshAuth();
      });

      expect(AuthService.refreshToken).toHaveBeenCalled();
      expect(result.current.user).toEqual(mockUser);
      expect(result.current.isAuthenticated).toBe(true);
      expect(result.current.error).toBeNull();
    });

    it('should handle refresh failure', async () => {
      const mockError: ApiError = {
        message: 'Token expired',
        status: 401,
      };

      (AuthService.refreshToken as any).mockRejectedValue(mockError);

      const { result } = renderHook(() => useAuthStore());

      await act(async () => {
        try {
          await result.current.refreshAuth();
        } catch (error) {
          // Expected to throw
        }
      });

      expect(result.current.user).toBeNull();
      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.error).toBe('Token expired');
      expect(mockConsole.error).toHaveBeenCalledWith('Token refresh error:', mockError);
    });

    it('should use fallback error message for refresh failure', async () => {
      const mockError = {}; // Error without message
      (AuthService.refreshToken as any).mockRejectedValue(mockError);

      const { result } = renderHook(() => useAuthStore());

      await act(async () => {
        try {
          await result.current.refreshAuth();
        } catch (error) {
          // Expected to throw
        }
      });

      expect(result.current.error).toBe('Your session has expired. Please log in again.');
    });
  });

  describe('clearError action', () => {
    it('should clear error state', () => {
      // Set error state
      useAuthStore.setState({ error: 'Some error' });

      const { result } = renderHook(() => useAuthStore());

      act(() => {
        result.current.clearError();
      });

      expect(result.current.error).toBeNull();
    });
  });

  describe('initializeAuth action', () => {
    it('should successfully initialize auth', async () => {
      const mockInitResponse = {
        user: mockUser,
        isAuthenticated: true,
      };

      (AuthService.initializeAuth as any).mockResolvedValue(mockInitResponse);

      const { result } = renderHook(() => useAuthStore());

      await act(async () => {
        await result.current.initializeAuth();
      });

      expect(AuthService.initializeAuth).toHaveBeenCalled();
      expect(result.current.user).toEqual(mockUser);
      expect(result.current.isAuthenticated).toBe(true);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
      expect(result.current.isInitialized).toBe(true);
    });

    it('should handle initialization failure gracefully', async () => {
      const mockError = new Error('Initialization failed');
      (AuthService.initializeAuth as any).mockRejectedValue(mockError);

      const { result } = renderHook(() => useAuthStore());

      await act(async () => {
        await result.current.initializeAuth();
      });

      expect(result.current.user).toBeNull();
      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull(); // Should not show error on init failure
      expect(result.current.isInitialized).toBe(true);
      expect(mockConsole.error).toHaveBeenCalledWith('Auth initialization error:', mockError);
    });

    it('should not initialize if already initialized', async () => {
      // Set initialized state
      useAuthStore.setState({ isInitialized: true });

      const { result } = renderHook(() => useAuthStore());

      await act(async () => {
        await result.current.initializeAuth();
      });

      expect(AuthService.initializeAuth).not.toHaveBeenCalled();
    });
  });

  describe('utility actions', () => {
    it('should set loading state', () => {
      const { result } = renderHook(() => useAuthStore());

      act(() => {
        result.current.setLoading(true);
      });

      expect(result.current.isLoading).toBe(true);

      act(() => {
        result.current.setLoading(false);
      });

      expect(result.current.isLoading).toBe(false);
    });

    it('should set error state', () => {
      const { result } = renderHook(() => useAuthStore());

      act(() => {
        result.current.setError('Test error');
      });

      expect(result.current.error).toBe('Test error');

      act(() => {
        result.current.setError(null);
      });

      expect(result.current.error).toBeNull();
    });

    it('should set user state', () => {
      const { result } = renderHook(() => useAuthStore());

      act(() => {
        result.current.setUser(mockUser);
      });

      expect(result.current.user).toEqual(mockUser);
      expect(result.current.isAuthenticated).toBe(true);

      act(() => {
        result.current.setUser(null);
      });

      expect(result.current.user).toBeNull();
      expect(result.current.isAuthenticated).toBe(false);
    });
  });

  describe('selector hooks', () => {
    beforeEach(() => {
      useAuthStore.setState({
        user: mockUser,
        isAuthenticated: true,
        isLoading: false,
        error: 'Test error',
        isInitialized: true,
      });
    });

    it('should provide user selector', () => {
      const { result } = renderHook(() => useUser());
      expect(result.current).toEqual(mockUser);
    });

    it('should provide isAuthenticated selector', () => {
      const { result } = renderHook(() => useIsAuthenticated());
      expect(result.current).toBe(true);
    });

    it('should provide actions selector', () => {
      const { result } = renderHook(() => useAuthActions());

      expect(typeof result.current.login).toBe('function');
      expect(typeof result.current.logout).toBe('function');
      expect(typeof result.current.refreshAuth).toBe('function');
      expect(typeof result.current.clearError).toBe('function');
      expect(typeof result.current.initializeAuth).toBe('function');
    });
  });

  describe('role-based selectors', () => {
    it('should detect staff role', () => {
      const staffUser = { ...mockUser, is_staff: true };
      useAuthStore.setState({ user: staffUser });

      const { result } = renderHook(() => useAuthStore(state => Boolean(state.user?.is_staff)));
      expect(result.current).toBe(true);
    });

    it('should detect superuser role', () => {
      const superUser = { ...mockUser, is_superuser: true };
      useAuthStore.setState({ user: superUser });

      const { result } = renderHook(() => useAuthStore(state => Boolean(state.user?.is_superuser)));
      expect(result.current).toBe(true);
    });

    it('should check specific roles', () => {
      const userWithRoles = { ...mockUser, roles: ['teacher', 'admin'] };
      useAuthStore.setState({ user: userWithRoles });

      const { result } = renderHook(() =>
        useAuthStore(state => Boolean(state.user?.roles?.includes('teacher')))
      );
      expect(result.current).toBe(true);

      const { result: result2 } = renderHook(() =>
        useAuthStore(state => Boolean(state.user?.roles?.includes('student')))
      );
      expect(result2.current).toBe(false);
    });
  });
});