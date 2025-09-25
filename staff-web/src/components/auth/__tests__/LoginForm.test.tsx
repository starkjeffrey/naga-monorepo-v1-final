/**
 * Unit tests for LoginForm component
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LoginForm, ModalLoginForm } from '../LoginForm';
import { renderWithProviders, mockUser } from '../../../test/utils';
import { useAuth } from '../../../hooks/useAuth';

// Mock the useAuth hook
vi.mock('../../../hooks/useAuth', () => ({
  useAuth: vi.fn(),
}));

// Mock console methods to avoid noise
vi.stubGlobal('console', {
  log: vi.fn(),
  error: vi.fn(),
  warn: vi.fn(),
});

describe('LoginForm', () => {
  const mockUseAuth = {
    login: vi.fn(),
    isLoading: false,
    error: null,
    clearError: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    (useAuth as any).mockReturnValue(mockUseAuth);
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  describe('rendering', () => {
    it('should render login form with all fields', () => {
      renderWithProviders(<LoginForm />);

      expect(screen.getByText('Welcome Back')).toBeInTheDocument();
      expect(screen.getByText('Sign in to Naga SIS Staff Portal')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Email address')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Password')).toBeInTheDocument();
      expect(screen.getByText('Remember me for 30 days')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
    });

    it('should hide remember me checkbox when showRememberMe is false', () => {
      renderWithProviders(<LoginForm showRememberMe={false} />);

      expect(screen.queryByText('Remember me for 30 days')).not.toBeInTheDocument();
    });

    it('should apply custom className', () => {
      const { container } = renderWithProviders(<LoginForm className="custom-class" />);

      expect(container.querySelector('.custom-class')).toBeInTheDocument();
    });

    it('should display error message when error prop is provided', () => {
      (useAuth as any).mockReturnValue({
        ...mockUseAuth,
        error: 'Invalid credentials',
      });

      renderWithProviders(<LoginForm />);

      expect(screen.getByText('Invalid credentials')).toBeInTheDocument();
    });
  });

  describe('form validation', () => {
    it('should show email required validation', async () => {
      const user = userEvent.setup();
      renderWithProviders(<LoginForm />);

      const submitButton = screen.getByRole('button', { name: /sign in/i });
      await user.click(submitButton);

      expect(await screen.findByText('Email is required')).toBeInTheDocument();
    });

    it('should show invalid email validation', async () => {
      const user = userEvent.setup();
      renderWithProviders(<LoginForm />);

      const emailInput = screen.getByPlaceholderText('Email address');
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      await user.type(emailInput, 'invalid-email');
      await user.click(submitButton);

      expect(await screen.findByText('Please enter a valid email address')).toBeInTheDocument();
    });

    it('should show password required validation', async () => {
      const user = userEvent.setup();
      renderWithProviders(<LoginForm />);

      const emailInput = screen.getByPlaceholderText('Email address');
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      await user.type(emailInput, 'test@example.com');
      await user.click(submitButton);

      expect(await screen.findByText('Password is required')).toBeInTheDocument();
    });

    it('should not show validation errors for valid input', async () => {
      const user = userEvent.setup();
      renderWithProviders(<LoginForm />);

      const emailInput = screen.getByPlaceholderText('Email address');
      const passwordInput = screen.getByPlaceholderText('Password');
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'password123');
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.queryByText('Email is required')).not.toBeInTheDocument();
        expect(screen.queryByText('Password is required')).not.toBeInTheDocument();
        expect(screen.queryByText('Please enter a valid email address')).not.toBeInTheDocument();
      });
    });
  });

  describe('form submission', () => {
    it('should call login with correct credentials on form submission', async () => {
      const user = userEvent.setup();
      renderWithProviders(<LoginForm />);

      const emailInput = screen.getByPlaceholderText('Email address');
      const passwordInput = screen.getByPlaceholderText('Password');
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'password123');
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockUseAuth.login).toHaveBeenCalledWith({
          email: 'test@example.com',
          password: 'password123',
          rememberMe: false,
        });
      });
    });

    it('should include remember me preference when checked', async () => {
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

      await waitFor(() => {
        expect(mockUseAuth.login).toHaveBeenCalledWith({
          email: 'test@example.com',
          password: 'password123',
          rememberMe: true,
        });
      });
    });

    it('should trim email input', async () => {
      const user = userEvent.setup();
      renderWithProviders(<LoginForm />);

      const emailInput = screen.getByPlaceholderText('Email address');
      const passwordInput = screen.getByPlaceholderText('Password');
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      await user.type(emailInput, '  test@example.com  ');
      await user.type(passwordInput, 'password123');
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockUseAuth.login).toHaveBeenCalledWith({
          email: 'test@example.com',
          password: 'password123',
          rememberMe: false,
        });
      });
    });

    it('should call onSuccess callback when login succeeds', async () => {
      const onSuccess = vi.fn();
      const user = userEvent.setup();

      mockUseAuth.login.mockResolvedValue(undefined);

      renderWithProviders(<LoginForm onSuccess={onSuccess} />);

      const emailInput = screen.getByPlaceholderText('Email address');
      const passwordInput = screen.getByPlaceholderText('Password');
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'password123');
      await user.click(submitButton);

      await waitFor(() => {
        expect(onSuccess).toHaveBeenCalled();
      });
    });

    it('should call onError callback when login fails', async () => {
      const onError = vi.fn();
      const user = userEvent.setup();
      const mockError = new Error('Login failed');

      mockUseAuth.login.mockRejectedValue(mockError);

      renderWithProviders(<LoginForm onError={onError} />);

      const emailInput = screen.getByPlaceholderText('Email address');
      const passwordInput = screen.getByPlaceholderText('Password');
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'password123');
      await user.click(submitButton);

      await waitFor(() => {
        expect(onError).toHaveBeenCalledWith('Login failed');
      });
    });

    it('should use fallback error message when error has no message', async () => {
      const onError = vi.fn();
      const user = userEvent.setup();

      mockUseAuth.login.mockRejectedValue({});

      renderWithProviders(<LoginForm onError={onError} />);

      const emailInput = screen.getByPlaceholderText('Email address');
      const passwordInput = screen.getByPlaceholderText('Password');
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'password123');
      await user.click(submitButton);

      await waitFor(() => {
        expect(onError).toHaveBeenCalledWith('Login failed. Please try again.');
      });
    });
  });

  describe('loading states', () => {
    it('should disable form inputs during loading', () => {
      (useAuth as any).mockReturnValue({
        ...mockUseAuth,
        isLoading: true,
      });

      renderWithProviders(<LoginForm />);

      const emailInput = screen.getByPlaceholderText('Email address');
      const passwordInput = screen.getByPlaceholderText('Password');
      const rememberMeCheckbox = screen.getByRole('checkbox');
      const submitButton = screen.getByRole('button', { name: /signing in/i });

      expect(emailInput).toBeDisabled();
      expect(passwordInput).toBeDisabled();
      expect(rememberMeCheckbox).toBeDisabled();
      expect(submitButton).toBeDisabled();
    });

    it('should show loading state on submit button', () => {
      (useAuth as any).mockReturnValue({
        ...mockUseAuth,
        isLoading: true,
      });

      renderWithProviders(<LoginForm />);

      expect(screen.getByText('Signing in...')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /signing in/i })).toHaveAttribute('disabled');
    });
  });

  describe('keyboard interactions', () => {
    it('should submit form when Enter is pressed', async () => {
      const user = userEvent.setup();
      renderWithProviders(<LoginForm />);

      const emailInput = screen.getByPlaceholderText('Email address');
      const passwordInput = screen.getByPlaceholderText('Password');

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'password123');
      await user.keyboard('{Enter}');

      await waitFor(() => {
        expect(mockUseAuth.login).toHaveBeenCalledWith({
          email: 'test@example.com',
          password: 'password123',
          rememberMe: false,
        });
      });
    });
  });

  describe('error handling', () => {
    it('should clear errors when form values change', async () => {
      const user = userEvent.setup();

      (useAuth as any).mockReturnValue({
        ...mockUseAuth,
        error: 'Invalid credentials',
      });

      renderWithProviders(<LoginForm />);

      const emailInput = screen.getByPlaceholderText('Email address');

      // Error should be displayed initially
      expect(screen.getByText('Invalid credentials')).toBeInTheDocument();

      // Type in email field
      await user.type(emailInput, 'test@example.com');

      // clearError should be called
      expect(mockUseAuth.clearError).toHaveBeenCalled();
    });

    it('should show error with close button', async () => {
      (useAuth as any).mockReturnValue({
        ...mockUseAuth,
        error: 'Invalid credentials',
      });

      renderWithProviders(<LoginForm />);

      const errorMessage = screen.getByText('Invalid credentials');
      expect(errorMessage).toBeInTheDocument();

      // Error should have close functionality (through ErrorMessage component)
      const closeButton = screen.getByRole('button', { name: /close/i });
      expect(closeButton).toBeInTheDocument();
    });
  });

  describe('accessibility', () => {
    it('should have proper form labels and structure', () => {
      renderWithProviders(<LoginForm />);

      // Check for form structure
      expect(screen.getByRole('form')).toBeInTheDocument();

      // Check for input accessibility
      const emailInput = screen.getByPlaceholderText('Email address');
      const passwordInput = screen.getByPlaceholderText('Password');

      expect(emailInput).toHaveAttribute('autoComplete', 'email');
      expect(passwordInput).toHaveAttribute('autoComplete', 'current-password');

      // Check for submit button
      const submitButton = screen.getByRole('button', { name: /sign in/i });
      expect(submitButton).toHaveAttribute('type', 'submit');
    });

    it('should focus email input on mount', () => {
      renderWithProviders(<LoginForm />);

      // Since we mocked document.getElementById in setup.ts
      // The focus call should have been made
      expect(document.getElementById).toHaveBeenCalledWith('email');
    });
  });
});

describe('ModalLoginForm', () => {
  const mockOnSuccess = vi.fn();
  const mockOnCancel = vi.fn();

  const mockUseAuth = {
    login: vi.fn(),
    isLoading: false,
    error: null,
    clearError: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    (useAuth as any).mockReturnValue(mockUseAuth);
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  it('should render modal login form with cancel button', () => {
    renderWithProviders(
      <ModalLoginForm onSuccess={mockOnSuccess} onCancel={mockOnCancel} />
    );

    expect(screen.getByText('Welcome Back')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
    expect(screen.queryByText('Remember me for 30 days')).not.toBeInTheDocument();
  });

  it('should call onCancel when cancel button is clicked', async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <ModalLoginForm onSuccess={mockOnSuccess} onCancel={mockOnCancel} />
    );

    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    await user.click(cancelButton);

    expect(mockOnCancel).toHaveBeenCalled();
  });

  it('should call onSuccess when login succeeds', async () => {
    const user = userEvent.setup();
    mockUseAuth.login.mockResolvedValue(undefined);

    renderWithProviders(
      <ModalLoginForm onSuccess={mockOnSuccess} onCancel={mockOnCancel} />
    );

    const emailInput = screen.getByPlaceholderText('Email address');
    const passwordInput = screen.getByPlaceholderText('Password');
    const submitButton = screen.getByRole('button', { name: /sign in/i });

    await user.type(emailInput, 'test@example.com');
    await user.type(passwordInput, 'password123');
    await user.click(submitButton);

    await waitFor(() => {
      expect(mockOnSuccess).toHaveBeenCalled();
    });
  });
});