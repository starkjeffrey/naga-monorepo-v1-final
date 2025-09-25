/**
 * Authentication service for JWT-based authentication
 */

import { api } from './api';
import { TokenStorage } from '../utils/tokenStorage';
import { AUTH_ENDPOINTS, ERROR_MESSAGES } from '../utils/constants';
import type {
  LoginCredentials,
  LoginResponse,
  User,
  RefreshTokenResponse,
  ApiError
} from '../types/auth.types';

/**
 * Authentication service class
 */
export class AuthService {
  /**
   * Log in user with email and password
   */
  static async login(credentials: LoginCredentials): Promise<{ user: User; tokens: any }> {
    try {
      const response = await api.post<LoginResponse>(AUTH_ENDPOINTS.LOGIN, {
        email: credentials.email,
        password: credentials.password,
      });

      const { access_token, refresh_token, token_type, expires_in, user } = response;

      // Store authentication data
      TokenStorage.setAuthData(
        {
          access_token,
          refresh_token,
          token_type,
          expires_in,
        },
        user,
        credentials.rememberMe || false
      );

      return {
        user,
        tokens: {
          access_token,
          refresh_token,
          token_type,
          expires_in,
        },
      };
    } catch (error) {
      console.error('Login failed:', error);
      throw this.handleAuthError(error);
    }
  }

  /**
   * Refresh access token using refresh token
   */
  static async refreshToken(): Promise<{ user: User; tokens: any }> {
    const refreshToken = TokenStorage.getRefreshToken();

    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    try {
      const response = await api.post<RefreshTokenResponse>(AUTH_ENDPOINTS.REFRESH, {
        refresh_token: refreshToken,
      });

      const { access_token, refresh_token: newRefreshToken, token_type, expires_in, user } = response;

      // Update stored tokens
      TokenStorage.setAuthData(
        {
          access_token,
          refresh_token: newRefreshToken,
          token_type,
          expires_in,
        },
        user,
        TokenStorage.getRememberMe()
      );

      return {
        user,
        tokens: {
          access_token,
          refresh_token: newRefreshToken,
          token_type,
          expires_in,
        },
      };
    } catch (error) {
      console.error('Token refresh failed:', error);
      // Clear invalid tokens
      TokenStorage.clearAuthData();
      throw this.handleAuthError(error);
    }
  }

  /**
   * Get current user profile
   */
  static async getProfile(): Promise<User> {
    try {
      const user = await api.get<User>(AUTH_ENDPOINTS.PROFILE);

      // Update stored user data
      TokenStorage.setUserData(user);

      return user;
    } catch (error) {
      console.error('Failed to get user profile:', error);
      throw this.handleAuthError(error);
    }
  }

  /**
   * Log out user and clear all stored data
   */
  static async logout(): Promise<void> {
    try {
      // Attempt to call logout endpoint (optional)
      await api.post(AUTH_ENDPOINTS.LOGOUT);
    } catch (error) {
      console.warn('Logout endpoint failed:', error);
      // Continue with client-side logout even if server call fails
    } finally {
      // Always clear local storage
      TokenStorage.clearAuthData();
    }
  }

  /**
   * Check if user is currently authenticated
   */
  static isAuthenticated(): boolean {
    const accessToken = TokenStorage.getAccessToken();
    const userData = TokenStorage.getUserData();

    if (!accessToken || !userData) {
      return false;
    }

    // Check if token is expired
    if (TokenStorage.isTokenExpired(accessToken)) {
      return false;
    }

    return true;
  }

  /**
   * Get current access token
   */
  static getAccessToken(): string | null {
    return TokenStorage.getAccessToken();
  }

  /**
   * Get current refresh token
   */
  static getRefreshToken(): string | null {
    return TokenStorage.getRefreshToken();
  }

  /**
   * Get current user data
   */
  static getCurrentUser(): User | null {
    return TokenStorage.getUserData();
  }

  /**
   * Clear all authentication data
   */
  static clearAuthData(): void {
    TokenStorage.clearAuthData();
  }

  /**
   * Check if token needs refresh (within buffer time)
   */
  static needsTokenRefresh(): boolean {
    const accessToken = TokenStorage.getAccessToken();
    if (!accessToken) {
      return false;
    }

    return TokenStorage.isTokenExpired(accessToken);
  }

  /**
   * Initialize authentication state on app startup
   */
  static async initializeAuth(): Promise<{ user: User | null; isAuthenticated: boolean }> {
    try {
      // Check if we have stored auth data
      const { accessToken, userData } = TokenStorage.getAuthData();

      if (!accessToken || !userData) {
        return { user: null, isAuthenticated: false };
      }

      // Check if token is expired
      if (TokenStorage.isTokenExpired(accessToken)) {
        // Try to refresh token
        try {
          const { user } = await this.refreshToken();
          return { user, isAuthenticated: true };
        } catch (error) {
          // Refresh failed, clear auth data
          TokenStorage.clearAuthData();
          return { user: null, isAuthenticated: false };
        }
      }

      // Token is still valid, verify with server
      try {
        const user = await this.getProfile();
        return { user, isAuthenticated: true };
      } catch (error) {
        // Profile fetch failed, try refreshing token
        try {
          const { user } = await this.refreshToken();
          return { user, isAuthenticated: true };
        } catch (refreshError) {
          // Both profile and refresh failed, clear auth data
          TokenStorage.clearAuthData();
          return { user: null, isAuthenticated: false };
        }
      }
    } catch (error) {
      console.error('Failed to initialize auth:', error);
      TokenStorage.clearAuthData();
      return { user: null, isAuthenticated: false };
    }
  }

  /**
   * Handle authentication errors and format them consistently
   */
  private static handleAuthError(error: any): ApiError {
    if (error.message && error.status !== undefined) {
      // Already formatted API error
      return error as ApiError;
    }

    // Handle different error types
    if (error.response?.status === 401) {
      return {
        message: ERROR_MESSAGES.INVALID_CREDENTIALS,
        status: 401,
      };
    }

    if (error.response?.status === 403) {
      return {
        message: ERROR_MESSAGES.UNAUTHORIZED,
        status: 403,
      };
    }

    if (!error.response) {
      return {
        message: ERROR_MESSAGES.NETWORK_ERROR,
        status: 0,
      };
    }

    return {
      message: error.message || ERROR_MESSAGES.UNKNOWN_ERROR,
      status: error.response?.status || 500,
    };
  }
}

export default AuthService;