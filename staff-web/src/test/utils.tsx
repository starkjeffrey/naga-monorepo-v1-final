/**
 * Testing utilities for React components and authentication
 */

import React from 'react';
import { render } from '@testing-library/react';
import type { ReactElement } from 'react';
import type { RenderOptions } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { ConfigProvider, App as AntdApp } from 'antd';
import { vi } from 'vitest';
import type { User, LoginCredentials } from '../types/auth.types';

// Mock user data for testing
export const mockUser: User = {
  id: 1,
  email: 'test@example.com',
  first_name: 'Test',
  last_name: 'User',
  full_name: 'Test User',
  is_staff: true,
  is_superuser: false,
  roles: ['staff', 'teacher'],
};

export const mockAdminUser: User = {
  id: 2,
  email: 'admin@example.com',
  first_name: 'Admin',
  last_name: 'User',
  full_name: 'Admin User',
  is_staff: true,
  is_superuser: true,
  roles: ['staff', 'admin'],
};

// Mock login credentials
export const mockCredentials: LoginCredentials = {
  email: 'test@example.com',
  password: 'password123',
  rememberMe: false,
};

// Mock tokens
export const mockTokens = {
  access_token: 'mock-access-token',
  refresh_token: 'mock-refresh-token',
  token_type: 'Bearer',
  expires_in: 3600,
};

// Mock login response
export const mockLoginResponse = {
  ...mockTokens,
  user: mockUser,
};

// Custom render function with providers
interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  initialEntries?: string[];
  withRouter?: boolean;
}

function AllTheProviders({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <BrowserRouter>
      <ConfigProvider>
        <AntdApp>
          {children}
        </AntdApp>
      </ConfigProvider>
    </BrowserRouter>
  );
}

export function renderWithProviders(
  ui: ReactElement,
  options: CustomRenderOptions = {}
) {
  const { withRouter = true, ...renderOptions } = options;

  if (withRouter) {
    return render(ui, {
      wrapper: ({ children }) => (
        <AllTheProviders>
          {children}
        </AllTheProviders>
      ),
      ...renderOptions,
    });
  }

  return render(ui, {
    wrapper: ({ children }) => (
      <ConfigProvider>
        <AntdApp>{children}</AntdApp>
      </ConfigProvider>
    ),
    ...renderOptions,
  });
}

// Storage mock utilities
export const mockLocalStorage = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};

export const mockSessionStorage = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};

// Setup storage mocks
export function setupStorageMocks() {
  Object.defineProperty(window, 'localStorage', {
    writable: true,
    value: mockLocalStorage,
  });

  Object.defineProperty(window, 'sessionStorage', {
    writable: true,
    value: mockSessionStorage,
  });
}

// Wait for async operations
export const waitFor = (ms: number) =>
  new Promise(resolve => setTimeout(resolve, ms));

// Utility to wait for next React update
export const waitForNextUpdate = () => new Promise(resolve => {
  setTimeout(resolve, 0);
});

// Mock error objects
export const mockApiError = {
  message: 'API Error',
  status: 400,
  detail: 'Bad request',
};

export const mockNetworkError = {
  message: 'Network Error',
  status: 0,
  detail: 'Failed to fetch',
};

export const mockAuthError = {
  message: 'Invalid credentials',
  status: 401,
  detail: 'Authentication failed',
};

// JWT token utilities for testing
export const createMockJWT = (payload: Record<string, any> = {}) => {
  const header = btoa(JSON.stringify({ typ: 'JWT', alg: 'HS256' }));
  const body = btoa(JSON.stringify({
    sub: '1',
    email: 'test@example.com',
    exp: Math.floor(Date.now() / 1000) + 3600, // 1 hour from now
    iat: Math.floor(Date.now() / 1000),
    ...payload,
  }));
  const signature = 'mock-signature';

  return `${header}.${body}.${signature}`;
};

export const createExpiredMockJWT = () => {
  return createMockJWT({
    exp: Math.floor(Date.now() / 1000) - 3600, // 1 hour ago
  });
};

// Form validation test utilities
export const validateEmailField = (email: string) => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};

export const validatePasswordField = (password: string) => {
  return password.length >= 1; // Basic non-empty validation as per the form
};

// Re-export testing library utilities
export * from '@testing-library/react';
export { default as userEvent } from '@testing-library/user-event';