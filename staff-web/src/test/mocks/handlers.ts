/**
 * MSW handlers for mocking authentication API endpoints
 */

import { http, HttpResponse } from 'msw';
import { mockUser, mockAdminUser, mockTokens, mockLoginResponse } from '../utils';

// Base API URL - should match your actual API
const API_BASE = 'http://localhost:8000/api/v1';

export const handlers = [
  // Login endpoint
  http.post(`${API_BASE}/auth/login/`, async ({ request }: { request: Request }) => {
    const { email, password } = await request.json() as any;

    // Simulate authentication validation
    if (email === 'test@example.com' && password === 'password123') {
      return HttpResponse.json(mockLoginResponse, { status: 200 });
    }

    if (email === 'admin@example.com' && password === 'admin123') {
      return HttpResponse.json({
        ...mockTokens,
        user: mockAdminUser,
      }, { status: 200 });
    }

    // Invalid credentials
    return HttpResponse.json(
      {
        message: 'Invalid credentials',
        detail: 'Email or password is incorrect',
      },
      { status: 401 }
    );
  }),

  // Token refresh endpoint
  http.post(`${API_BASE}/auth/refresh/`, async ({ request }: { request: Request }) => {
    const { refresh_token } = await request.json() as any;

    if (refresh_token === 'mock-refresh-token') {
      return HttpResponse.json({
        access_token: 'new-mock-access-token',
        refresh_token: 'new-mock-refresh-token',
        token_type: 'Bearer',
        expires_in: 3600,
        user: mockUser,
      }, { status: 200 });
    }

    if (refresh_token === 'expired-refresh-token') {
      return HttpResponse.json(
        {
          message: 'Token expired',
          detail: 'Refresh token has expired',
        },
        { status: 401 }
      );
    }

    return HttpResponse.json(
      {
        message: 'Invalid token',
        detail: 'Refresh token is invalid',
      },
      { status: 401 }
    );
  }),

  // User profile endpoint
  http.get(`${API_BASE}/auth/profile/`, ({ request }: { request: Request }) => {
    const authHeader = request.headers.get('Authorization');

    if (authHeader === 'Bearer mock-access-token' ||
        authHeader === 'Bearer new-mock-access-token') {
      return HttpResponse.json(mockUser, { status: 200 });
    }

    return HttpResponse.json(
      {
        message: 'Unauthorized',
        detail: 'Invalid or missing token',
      },
      { status: 401 }
    );
  }),

  // Logout endpoint
  http.post(`${API_BASE}/auth/logout/`, () => {
    return HttpResponse.json({ message: 'Logged out successfully' }, { status: 200 });
  }),

  // Network error simulation
  http.post(`${API_BASE}/auth/network-error/`, () => {
    return HttpResponse.error();
  }),

  // Server error simulation
  http.post(`${API_BASE}/auth/server-error/`, () => {
    return HttpResponse.json(
      {
        message: 'Internal server error',
        detail: 'Something went wrong',
      },
      { status: 500 }
    );
  }),
];

// Error handlers for specific test scenarios
export const errorHandlers = [
  // Login network error
  http.post(`${API_BASE}/auth/login/`, () => {
    return HttpResponse.error();
  }),

  // Token refresh network error
  http.post(`${API_BASE}/auth/refresh/`, () => {
    return HttpResponse.error();
  }),

  // Profile fetch error
  http.get(`${API_BASE}/auth/profile/`, () => {
    return HttpResponse.json(
      {
        message: 'Server error',
        detail: 'Failed to fetch profile',
      },
      { status: 500 }
    );
  }),
];

// Slow response handlers for timeout testing
export const slowHandlers = [
  http.post(`${API_BASE}/auth/login/`, async () => {
    // Simulate slow response (5 seconds)
    await new Promise(resolve => setTimeout(resolve, 5000));
    return HttpResponse.json(mockLoginResponse, { status: 200 });
  }),
];