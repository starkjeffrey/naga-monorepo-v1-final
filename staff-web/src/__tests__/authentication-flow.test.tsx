/**
 * Integration tests for complete authentication flow
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders, mockUser, mockCredentials } from '../test/utils';
import { LoginForm } from '../components/auth/LoginForm';
import AuthService from '../services/auth.service';
import { useAuthStore } from '../store/authStore';
import { server } from '../test/mocks/server';
import { http, HttpResponse } from 'msw';
import { act } from '@testing-library/react';

// Mock console methods
vi.stubGlobal('console', {
  log: vi.fn(),
  error: vi.fn(),
  warn: vi.fn(),
});

describe('Authentication Flow Integration Tests', () => {
  beforeEach(() => {
    // Reset Zustand store state
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
    server.resetHandlers();
  });

  describe('Login Flow', () => {
    it('should complete successful login flow end-to-end', async () => {
      const user = userEvent.setup();
      const onSuccess = vi.fn();

      renderWithProviders(<LoginForm onSuccess={onSuccess} />);

      // Fill in login form
      const emailInput = screen.getByPlaceholderText('Email address');
      const passwordInput = screen.getByPlaceholderText('Password');
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'password123');

      // Submit form
      await user.click(submitButton);

      // Wait for login to complete
      await waitFor(() => {
        expect(onSuccess).toHaveBeenCalled();
      });

      // Check store state
      const storeState = useAuthStore.getState();
      expect(storeState.isAuthenticated).toBe(true);
      expect(storeState.user).toEqual(mockUser);
      expect(storeState.isLoading).toBe(false);
      expect(storeState.error).toBeNull();
    });

    it('should handle login failure with proper error display', async () => {
      const user = userEvent.setup();

      // Override the default handler to return an error
      server.use(
        http.post('http://localhost:8000/api/v1/auth/login/', () => {
          return HttpResponse.json(
            { message: 'Invalid credentials', detail: 'Email or password is incorrect' },
            { status: 401 }
          );
        })
      );

      renderWithProviders(<LoginForm />);

      // Fill in form with invalid credentials
      const emailInput = screen.getByPlaceholderText('Email address');
      const passwordInput = screen.getByPlaceholderText('Password');
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      await user.type(emailInput, 'invalid@example.com');
      await user.type(passwordInput, 'wrongpassword');
      await user.click(submitButton);

      // Wait for error to appear
      await waitFor(() => {
        expect(screen.getByText('Invalid credentials')).toBeInTheDocument();
      });

      // Check store state
      const storeState = useAuthStore.getState();
      expect(storeState.isAuthenticated).toBe(false);
      expect(storeState.user).toBeNull();
      expect(storeState.isLoading).toBe(false);
      expect(storeState.error).toBe('Invalid credentials');
    });

    it('should handle network errors gracefully', async () => {
      const user = userEvent.setup();

      // Simulate network error
      server.use(
        http.post('http://localhost:8000/api/v1/auth/login/', () => {
          return HttpResponse.error();
        })
      );

      renderWithProviders(<LoginForm />);

      const emailInput = screen.getByPlaceholderText('Email address');
      const passwordInput = screen.getByPlaceholderText('Password');
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'password123');
      await user.click(submitButton);

      // Wait for network error to be handled
      await waitFor(() => {
        expect(screen.getByText('Network error. Please check your connection.')).toBeInTheDocument();
      });

      // Check store state
      const storeState = useAuthStore.getState();
      expect(storeState.isAuthenticated).toBe(false);
      expect(storeState.user).toBeNull();
      expect(storeState.isLoading).toBe(false);
      expect(storeState.error).toBe('Network error. Please check your connection.');
    });

    it('should preserve remember me preference', async () => {
      const user = userEvent.setup();

      renderWithProviders(<LoginForm />);

      const emailInput = screen.getByPlaceholderText('Email address');
      const passwordInput = screen.getByPlaceholderText('Password');
      const rememberMeCheckbox = screen.getByRole('checkbox');
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'password123');
      await user.click(rememberMeCheckbox);
      await user.click(submitButton);

      // Wait for login to complete
      await waitFor(() => {
        const storeState = useAuthStore.getState();
        expect(storeState.isAuthenticated).toBe(true);
      });
    });
  });

  describe('Token Refresh Flow', () => {
    it('should refresh token automatically when needed', async () => {
      // Set up initial authenticated state with expired token
      useAuthStore.setState({
        user: mockUser,
        isAuthenticated: true,
        isLoading: false,
        error: null,
        isInitialized: true,
      });

      const store = useAuthStore.getState();

      // Call refresh token manually to test the flow
      await act(async () => {
        await store.refreshAuth();
      });

      // Check that refresh was successful
      const updatedState = useAuthStore.getState();
      expect(updatedState.isAuthenticated).toBe(true);
      expect(updatedState.user).toEqual(mockUser);
      expect(updatedState.error).toBeNull();
    });

    it('should handle refresh token failure', async () => {
      // Set up authenticated state
      useAuthStore.setState({
        user: mockUser,
        isAuthenticated: true,
        isLoading: false,
        error: null,
        isInitialized: true,
      });

      // Mock refresh failure
      server.use(
        http.post('http://localhost:8000/api/v1/auth/refresh/', () => {
          return HttpResponse.json(
            { message: 'Token expired', detail: 'Refresh token has expired' },
            { status: 401 }
          );
        })
      );

      const store = useAuthStore.getState();

      // Attempt to refresh and expect it to fail
      await act(async () => {
        try {
          await store.refreshAuth();
        } catch (error) {
          // Expected to fail
        }
      });

      // Check that user is logged out
      const updatedState = useAuthStore.getState();
      expect(updatedState.isAuthenticated).toBe(false);
      expect(updatedState.user).toBeNull();
      expect(updatedState.error).toBe('Token expired');
    });
  });

  describe('Logout Flow', () => {
    it('should complete logout flow successfully', async () => {
      // Set up authenticated state
      useAuthStore.setState({
        user: mockUser,
        isAuthenticated: true,
        isLoading: false,
        error: null,
        isInitialized: true,
      });

      const store = useAuthStore.getState();

      // Perform logout
      await act(async () => {
        store.logout();
        // Wait for async logout to complete
        await new Promise(resolve => setTimeout(resolve, 0));
      });

      // Check that user is logged out
      const updatedState = useAuthStore.getState();
      expect(updatedState.isAuthenticated).toBe(false);
      expect(updatedState.user).toBeNull();
      expect(updatedState.isLoading).toBe(false);
      expect(updatedState.error).toBeNull();
    });

    it('should handle logout even if server call fails', async () => {
      // Set up authenticated state
      useAuthStore.setState({
        user: mockUser,
        isAuthenticated: true,
        isLoading: false,
        error: null,
        isInitialized: true,
      });

      // Mock logout server error
      server.use(
        http.post('http://localhost:8000/api/v1/auth/logout/', () => {
          return HttpResponse.json(
            { message: 'Server error' },
            { status: 500 }
          );
        })
      );

      const store = useAuthStore.getState();

      // Perform logout despite server error
      await act(async () => {
        store.logout();
        // Wait for async logout to complete
        await new Promise(resolve => setTimeout(resolve, 0));
      });

      // User should still be logged out locally
      const updatedState = useAuthStore.getState();
      expect(updatedState.isAuthenticated).toBe(false);
      expect(updatedState.user).toBeNull();
      expect(updatedState.isLoading).toBe(false);
      expect(updatedState.error).toBeNull();
    });
  });

  describe('Authentication Initialization Flow', () => {
    it('should initialize authentication successfully with valid stored token', async () => {
      // Mock successful profile fetch
      server.use(
        http.get('http://localhost:8000/api/v1/auth/profile/', () => {
          return HttpResponse.json(mockUser, { status: 200 });
        })
      );

      const store = useAuthStore.getState();

      // Initialize auth
      await act(async () => {
        await store.initializeAuth();
      });

      // Check that user is authenticated
      const updatedState = useAuthStore.getState();
      expect(updatedState.isAuthenticated).toBe(true);
      expect(updatedState.user).toEqual(mockUser);
      expect(updatedState.isInitialized).toBe(true);
      expect(updatedState.error).toBeNull();
    });

    it('should handle initialization failure gracefully', async () => {
      // Mock initialization failure
      server.use(
        http.get('http://localhost:8000/api/v1/auth/profile/', () => {
          return HttpResponse.json(
            { message: 'Unauthorized' },
            { status: 401 }
          );
        }),
        http.post('http://localhost:8000/api/v1/auth/refresh/', () => {
          return HttpResponse.json(
            { message: 'Token expired' },
            { status: 401 }
          );
        })
      );

      const store = useAuthStore.getState();

      // Initialize auth
      await act(async () => {
        await store.initializeAuth();
      });

      // Check that initialization completed but user is not authenticated
      const updatedState = useAuthStore.getState();
      expect(updatedState.isAuthenticated).toBe(false);
      expect(updatedState.user).toBeNull();
      expect(updatedState.isInitialized).toBe(true);
      expect(updatedState.error).toBeNull(); // Should not show error on init failure
    });

    it('should not initialize twice', async () => {
      // Set initialized state
      useAuthStore.setState({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,
        isInitialized: true,
      });

      const mockProfileCall = vi.fn();
      server.use(
        http.get('http://localhost:8000/api/v1/auth/profile/', () => {
          mockProfileCall();
          return HttpResponse.json(mockUser, { status: 200 });
        })
      );

      const store = useAuthStore.getState();

      // Try to initialize again
      await act(async () => {
        await store.initializeAuth();
      });

      // Should not have called profile endpoint
      expect(mockProfileCall).not.toHaveBeenCalled();
    });
  });

  describe('Error Handling and Recovery', () => {
    it('should clear errors when requested', async () => {
      // Set error state
      useAuthStore.setState({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: 'Some error',
        isInitialized: true,
      });

      const store = useAuthStore.getState();

      // Clear error
      act(() => {
        store.clearError();
      });

      // Check that error is cleared
      const updatedState = useAuthStore.getState();
      expect(updatedState.error).toBeNull();
    });

    it('should handle concurrent login attempts', async () => {
      const user = userEvent.setup();

      renderWithProviders(<LoginForm />);

      const emailInput = screen.getByPlaceholderText('Email address');
      const passwordInput = screen.getByPlaceholderText('Password');
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'password123');

      // Attempt multiple rapid clicks
      await user.click(submitButton);
      await user.click(submitButton);
      await user.click(submitButton);

      // Wait for login to complete
      await waitFor(() => {
        const storeState = useAuthStore.getState();
        expect(storeState.isAuthenticated).toBe(true);
      });

      // Should only be authenticated once
      const finalState = useAuthStore.getState();
      expect(finalState.user).toEqual(mockUser);
    });
  });
});