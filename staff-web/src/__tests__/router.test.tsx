/**
 * Tests for protected routes and authentication guards
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { RouterProvider, createMemoryRouter } from 'react-router-dom';
import { ConfigProvider, App as AntdApp } from 'antd';
import { useAuth, useAuthInitialization } from '../hooks/useAuth';
import { mockUser } from '../test/utils';
import { ROUTES } from '../utils/constants';

// Mock the hooks
vi.mock('../hooks/useAuth', () => ({
  useAuth: vi.fn(),
  useAuthInitialization: vi.fn(),
}));

// Mock the page components to avoid complex dependencies
vi.mock('../pages/Login', () => ({
  LoginPage: () => <div data-testid="login-page">Login Page</div>,
}));

vi.mock('../pages/Dashboard', () => ({
  DashboardPage: () => <div data-testid="dashboard-page">Dashboard Page</div>,
}));

vi.mock('../components/common/LoadingSpinner', () => ({
  PageLoadingSpinner: ({ text }: { text: string }) => (
    <div data-testid="loading-spinner">{text}</div>
  ),
}));

// Import router components after mocking
import router from '../router';

// Create a wrapper component for testing with router
const RouterWrapper = ({ children, initialEntries = ['/'] }: {
  children: React.ReactNode;
  initialEntries?: string[];
}) => {
  const testRouter = createMemoryRouter(router.routes, {
    initialEntries,
    initialIndex: 0,
  });

  return (
    <ConfigProvider>
      <AntdApp>
        <RouterProvider router={testRouter} />
        {children}
      </AntdApp>
    </ConfigProvider>
  );
};

describe('Router and Protected Routes', () => {
  const mockUseAuth = {
    isAuthenticated: false,
    isLoading: false,
    user: null,
    error: null,
  };

  const mockUseAuthInitialization = {
    isInitialized: true,
    initializeAuth: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    (useAuth as any).mockReturnValue(mockUseAuth);
    (useAuthInitialization as any).mockReturnValue(mockUseAuthInitialization);
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  describe('Root route (/)', () => {
    it('should redirect to login when not authenticated', async () => {
      (useAuth as any).mockReturnValue({
        ...mockUseAuth,
        isAuthenticated: false,
      });

      render(<RouterWrapper initialEntries={['/']} />);

      await waitFor(() => {
        expect(screen.getByTestId('login-page')).toBeInTheDocument();
      });
    });

    it('should redirect to dashboard when authenticated', async () => {
      (useAuth as any).mockReturnValue({
        ...mockUseAuth,
        isAuthenticated: true,
        user: mockUser,
      });

      render(<RouterWrapper initialEntries={['/']} />);

      await waitFor(() => {
        expect(screen.getByTestId('dashboard-page')).toBeInTheDocument();
      });
    });

    it('should show loading when not initialized', () => {
      (useAuthInitialization as any).mockReturnValue({
        ...mockUseAuthInitialization,
        isInitialized: false,
      });

      render(<RouterWrapper initialEntries={['/']} />);

      expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
      expect(screen.getByText('Initializing...')).toBeInTheDocument();
    });
  });

  describe('Login route (/login)', () => {
    it('should render login page when not authenticated', () => {
      (useAuth as any).mockReturnValue({
        ...mockUseAuth,
        isAuthenticated: false,
      });

      render(<RouterWrapper initialEntries={['/login']} />);

      expect(screen.getByTestId('login-page')).toBeInTheDocument();
    });

    it('should redirect to dashboard when already authenticated', async () => {
      (useAuth as any).mockReturnValue({
        ...mockUseAuth,
        isAuthenticated: true,
        user: mockUser,
      });

      render(<RouterWrapper initialEntries={['/login']} />);

      await waitFor(() => {
        expect(screen.getByTestId('dashboard-page')).toBeInTheDocument();
      });
    });

    it('should show loading while checking auth status', () => {
      (useAuth as any).mockReturnValue({
        ...mockUseAuth,
        isLoading: true,
      });

      render(<RouterWrapper initialEntries={['/login']} />);

      expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
      expect(screen.getByText('Loading...')).toBeInTheDocument();
    });

    it('should show loading when not initialized', () => {
      (useAuthInitialization as any).mockReturnValue({
        ...mockUseAuthInitialization,
        isInitialized: false,
      });

      render(<RouterWrapper initialEntries={['/login']} />);

      expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
      expect(screen.getByText('Loading...')).toBeInTheDocument();
    });
  });

  describe('Protected routes (/dashboard, /profile)', () => {
    it('should render dashboard when authenticated', () => {
      (useAuth as any).mockReturnValue({
        ...mockUseAuth,
        isAuthenticated: true,
        user: mockUser,
      });

      render(<RouterWrapper initialEntries={['/dashboard']} />);

      expect(screen.getByTestId('dashboard-page')).toBeInTheDocument();
    });

    it('should redirect to login when not authenticated', async () => {
      (useAuth as any).mockReturnValue({
        ...mockUseAuth,
        isAuthenticated: false,
      });

      render(<RouterWrapper initialEntries={['/dashboard']} />);

      await waitFor(() => {
        expect(screen.getByTestId('login-page')).toBeInTheDocument();
      });
    });

    it('should render profile page when authenticated', () => {
      (useAuth as any).mockReturnValue({
        ...mockUseAuth,
        isAuthenticated: true,
        user: mockUser,
      });

      render(<RouterWrapper initialEntries={['/profile']} />);

      expect(screen.getByText('Profile')).toBeInTheDocument();
      expect(screen.getByText('Profile page coming soon...')).toBeInTheDocument();
    });

    it('should show loading while initializing auth', () => {
      (useAuth as any).mockReturnValue({
        ...mockUseAuth,
        isAuthenticated: false,
        isLoading: true,
      });

      (useAuthInitialization as any).mockReturnValue({
        ...mockUseAuthInitialization,
        isInitialized: false,
      });

      render(<RouterWrapper initialEntries={['/dashboard']} />);

      expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
      expect(screen.getByText('Loading...')).toBeInTheDocument();
    });

    it('should initialize auth when not initialized and not loading', () => {
      const initializeAuth = vi.fn();

      (useAuth as any).mockReturnValue({
        ...mockUseAuth,
        isAuthenticated: false,
        isLoading: false,
      });

      (useAuthInitialization as any).mockReturnValue({
        isInitialized: false,
        initializeAuth,
      });

      render(<RouterWrapper initialEntries={['/dashboard']} />);

      expect(initializeAuth).toHaveBeenCalled();
    });

    it('should not initialize auth when already loading', () => {
      const initializeAuth = vi.fn();

      (useAuth as any).mockReturnValue({
        ...mockUseAuth,
        isAuthenticated: false,
        isLoading: true,
      });

      (useAuthInitialization as any).mockReturnValue({
        isInitialized: false,
        initializeAuth,
      });

      render(<RouterWrapper initialEntries={['/dashboard']} />);

      expect(initializeAuth).not.toHaveBeenCalled();
    });
  });

  describe('Error routes', () => {
    it('should show 404 error for unknown routes', () => {
      (useAuth as any).mockReturnValue({
        ...mockUseAuth,
        isAuthenticated: true,
        user: mockUser,
      });

      render(<RouterWrapper initialEntries={['/unknown-route']} />);

      expect(screen.getByText('Page Not Found')).toBeInTheDocument();
      expect(screen.getByText("The page you're looking for doesn't exist.")).toBeInTheDocument();
      expect(screen.getByText('Go to Dashboard')).toBeInTheDocument();
    });

    it('should have correct link to dashboard in error page', () => {
      (useAuth as any).mockReturnValue({
        ...mockUseAuth,
        isAuthenticated: true,
        user: mockUser,
      });

      render(<RouterWrapper initialEntries={['/unknown-route']} />);

      const dashboardLink = screen.getByText('Go to Dashboard');
      expect(dashboardLink).toHaveAttribute('href', '/dashboard');
    });
  });

  describe('Authentication state transitions', () => {
    it('should handle transition from loading to authenticated', async () => {
      const { rerender } = render(<div />);

      // Start with loading state
      (useAuth as any).mockReturnValue({
        ...mockUseAuth,
        isLoading: true,
        isAuthenticated: false,
      });

      rerender(<RouterWrapper initialEntries={['/dashboard']} />);

      expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();

      // Transition to authenticated
      (useAuth as any).mockReturnValue({
        ...mockUseAuth,
        isLoading: false,
        isAuthenticated: true,
        user: mockUser,
      });

      rerender(<RouterWrapper initialEntries={['/dashboard']} />);

      await waitFor(() => {
        expect(screen.getByTestId('dashboard-page')).toBeInTheDocument();
      });
    });

    it('should handle transition from loading to unauthenticated', async () => {
      const { rerender } = render(<div />);

      // Start with loading state on protected route
      (useAuth as any).mockReturnValue({
        ...mockUseAuth,
        isLoading: true,
        isAuthenticated: false,
      });

      rerender(<RouterWrapper initialEntries={['/dashboard']} />);

      expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();

      // Transition to unauthenticated
      (useAuth as any).mockReturnValue({
        ...mockUseAuth,
        isLoading: false,
        isAuthenticated: false,
      });

      rerender(<RouterWrapper initialEntries={['/dashboard']} />);

      await waitFor(() => {
        expect(screen.getByTestId('login-page')).toBeInTheDocument();
      });
    });

    it('should handle authentication during protected route access', async () => {
      const { rerender } = render(<div />);

      // Start unauthenticated on protected route
      (useAuth as any).mockReturnValue({
        ...mockUseAuth,
        isAuthenticated: false,
      });

      rerender(<RouterWrapper initialEntries={['/profile']} />);

      await waitFor(() => {
        expect(screen.getByTestId('login-page')).toBeInTheDocument();
      });

      // Become authenticated
      (useAuth as any).mockReturnValue({
        ...mockUseAuth,
        isAuthenticated: true,
        user: mockUser,
      });

      rerender(<RouterWrapper initialEntries={['/profile']} />);

      await waitFor(() => {
        expect(screen.getByText('Profile')).toBeInTheDocument();
      });
    });
  });
});