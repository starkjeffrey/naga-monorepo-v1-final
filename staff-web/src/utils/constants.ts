/**
 * Constants for the Naga SIS Staff Portal
 */

// API Configuration
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001/api';
export const APP_NAME = import.meta.env.VITE_APP_NAME || 'Naga SIS Staff Portal';

// Authentication endpoints
export const AUTH_ENDPOINTS = {
  LOGIN: '/auth/login/',
  REFRESH: '/auth/refresh/',
  PROFILE: '/auth/profile/',
  LOGOUT: '/auth/logout/',
} as const;

// Token storage keys
export const STORAGE_KEYS = {
  ACCESS_TOKEN: 'access_token',
  REFRESH_TOKEN: 'refresh_token',
  USER_DATA: 'user_data',
  REMEMBER_ME: 'remember_me',
} as const;

// Token expiry buffer (in seconds) - refresh token when it expires in 5 minutes
export const TOKEN_REFRESH_BUFFER = 300;

// API timeout (in milliseconds)
export const API_TIMEOUT = 30000;

// Default headers
export const DEFAULT_HEADERS = {
  'Content-Type': 'application/json',
  'Accept': 'application/json',
} as const;

// Form validation
export const VALIDATION_RULES = {
  EMAIL: {
    REQUIRED: 'Email is required',
    INVALID: 'Please enter a valid email address',
  },
  PASSWORD: {
    REQUIRED: 'Password is required',
    MIN_LENGTH: 'Password must be at least 8 characters long',
  },
} as const;

// UI Constants
export const UI = {
  BREAKPOINTS: {
    MOBILE: 768,
    TABLET: 1024,
    DESKTOP: 1200,
  },
  TRANSITIONS: {
    FAST: '150ms',
    NORMAL: '200ms',
    SLOW: '300ms',
  },
} as const;

// Routes
export const ROUTES = {
  LOGIN: '/login',
  DASHBOARD: '/',
  PROFILE: '/profile',
  CALLBACK: '/callback',
} as const;

// Error messages
export const ERROR_MESSAGES = {
  NETWORK_ERROR: 'Network error. Please check your connection.',
  INVALID_CREDENTIALS: 'Invalid email or password.',
  SESSION_EXPIRED: 'Your session has expired. Please log in again.',
  UNAUTHORIZED: 'You are not authorized to perform this action.',
  SERVER_ERROR: 'Server error. Please try again later.',
  UNKNOWN_ERROR: 'An unexpected error occurred.',
} as const;

// Success messages
export const SUCCESS_MESSAGES = {
  LOGIN_SUCCESS: 'Successfully logged in!',
  LOGOUT_SUCCESS: 'Successfully logged out!',
  PROFILE_UPDATED: 'Profile updated successfully!',
} as const;