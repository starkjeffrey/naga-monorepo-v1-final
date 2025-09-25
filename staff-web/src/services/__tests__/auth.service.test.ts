/**
 * Unit tests for AuthService
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { AuthService } from '../auth.service';
import { TokenStorage } from '../../utils/tokenStorage';
import { api } from '../api';
import { mockUser, mockCredentials, mockTokens, mockLoginResponse } from '../../test/utils';
import type { LoginCredentials } from '../../types/auth.types';

// Mock dependencies
vi.mock('../api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

vi.mock('../../utils/tokenStorage', () => ({
  TokenStorage: {
    setAuthData: vi.fn(),
    getAccessToken: vi.fn(),
    getRefreshToken: vi.fn(),
    getUserData: vi.fn(),
    getAuthData: vi.fn(),
    setUserData: vi.fn(),
    clearAuthData: vi.fn(),
    isTokenExpired: vi.fn(),
    getRememberMe: vi.fn(),
    setAccessToken: vi.fn(),
    setRefreshToken: vi.fn(),
  },
}));

describe('AuthService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  describe('login', () => {
    it('should successfully log in with valid credentials', async () => {
      const mockApiResponse = mockLoginResponse;
      (api.post as any).mockResolvedValue(mockApiResponse);

      const result = await AuthService.login(mockCredentials);

      expect(api.post).toHaveBeenCalledWith('/auth/login/', {
        email: mockCredentials.email,
        password: mockCredentials.password,
      });

      expect(TokenStorage.setAuthData).toHaveBeenCalledWith(
        {
          access_token: mockTokens.access_token,
          refresh_token: mockTokens.refresh_token,
          token_type: mockTokens.token_type,
          expires_in: mockTokens.expires_in,
        },
        mockUser,
        false
      );

      expect(result).toEqual({
        user: mockUser,
        tokens: {
          access_token: mockTokens.access_token,
          refresh_token: mockTokens.refresh_token,
          token_type: mockTokens.token_type,
          expires_in: mockTokens.expires_in,
        },
      });
    });

    it('should store remember me preference', async () => {
      const credentialsWithRememberMe: LoginCredentials = {
        ...mockCredentials,
        rememberMe: true,
      };

      (api.post as any).mockResolvedValue(mockLoginResponse);

      await AuthService.login(credentialsWithRememberMe);

      expect(TokenStorage.setAuthData).toHaveBeenCalledWith(
        expect.any(Object),
        expect.any(Object),
        true
      );
    });

    it('should handle login failure with 401 error', async () => {
      const mockError = {
        response: {
          status: 401,
          data: { message: 'Invalid credentials' },
        },
      };

      (api.post as any).mockRejectedValue(mockError);

      await expect(AuthService.login(mockCredentials)).rejects.toEqual({
        message: 'Invalid email or password.',
        status: 401,
      });
    });

    it('should handle network errors', async () => {
      const mockError = {
        message: 'Network Error',
      };

      (api.post as any).mockRejectedValue(mockError);

      await expect(AuthService.login(mockCredentials)).rejects.toEqual({
        message: 'Network error. Please check your connection.',
        status: 0,
      });
    });

    it('should handle 403 forbidden error', async () => {
      const mockError = {
        response: {
          status: 403,
          data: { message: 'Forbidden' },
        },
      };

      (api.post as any).mockRejectedValue(mockError);

      await expect(AuthService.login(mockCredentials)).rejects.toEqual({
        message: 'You are not authorized to perform this action.',
        status: 403,
      });
    });
  });

  describe('refreshToken', () => {
    it('should successfully refresh token', async () => {
      const mockRefreshToken = 'mock-refresh-token';
      const mockRefreshResponse = {
        access_token: 'new-access-token',
        refresh_token: 'new-refresh-token',
        token_type: 'Bearer',
        expires_in: 3600,
        user: mockUser,
      };

      (TokenStorage.getRefreshToken as any).mockReturnValue(mockRefreshToken);
      (TokenStorage.getRememberMe as any).mockReturnValue(false);
      (api.post as any).mockResolvedValue(mockRefreshResponse);

      const result = await AuthService.refreshToken();

      expect(api.post).toHaveBeenCalledWith('/auth/refresh/', {
        refresh_token: mockRefreshToken,
      });

      expect(TokenStorage.setAuthData).toHaveBeenCalledWith(
        {
          access_token: 'new-access-token',
          refresh_token: 'new-refresh-token',
          token_type: 'Bearer',
          expires_in: 3600,
        },
        mockUser,
        false
      );

      expect(result).toEqual({
        user: mockUser,
        tokens: {
          access_token: 'new-access-token',
          refresh_token: 'new-refresh-token',
          token_type: 'Bearer',
          expires_in: 3600,
        },
      });
    });

    it('should throw error when no refresh token is available', async () => {
      (TokenStorage.getRefreshToken as any).mockReturnValue(null);

      await expect(AuthService.refreshToken()).rejects.toThrow('No refresh token available');
    });

    it('should clear auth data on refresh failure', async () => {
      const mockRefreshToken = 'expired-refresh-token';
      const mockError = {
        response: {
          status: 401,
          data: { message: 'Token expired' },
        },
      };

      (TokenStorage.getRefreshToken as any).mockReturnValue(mockRefreshToken);
      (api.post as any).mockRejectedValue(mockError);

      await expect(AuthService.refreshToken()).rejects.toEqual({
        message: 'Invalid email or password.',
        status: 401,
      });

      expect(TokenStorage.clearAuthData).toHaveBeenCalled();
    });
  });

  describe('getProfile', () => {
    it('should successfully get user profile', async () => {
      (api.get as any).mockResolvedValue(mockUser);

      const result = await AuthService.getProfile();

      expect(api.get).toHaveBeenCalledWith('/auth/profile/');
      expect(TokenStorage.setUserData).toHaveBeenCalledWith(mockUser);
      expect(result).toEqual(mockUser);
    });

    it('should handle profile fetch error', async () => {
      const mockError = {
        response: {
          status: 401,
          data: { message: 'Unauthorized' },
        },
      };

      (api.get as any).mockRejectedValue(mockError);

      await expect(AuthService.getProfile()).rejects.toEqual({
        message: 'Invalid email or password.',
        status: 401,
      });
    });
  });

  describe('logout', () => {
    it('should successfully logout', async () => {
      (api.post as any).mockResolvedValue({ message: 'Logged out' });

      await AuthService.logout();

      expect(api.post).toHaveBeenCalledWith('/auth/logout/');
      expect(TokenStorage.clearAuthData).toHaveBeenCalled();
    });

    it('should clear auth data even if logout endpoint fails', async () => {
      const mockError = new Error('Network error');
      (api.post as any).mockRejectedValue(mockError);

      // Should not throw error
      await AuthService.logout();

      expect(TokenStorage.clearAuthData).toHaveBeenCalled();
    });
  });

  describe('isAuthenticated', () => {
    it('should return true when user has valid token and data', () => {
      (TokenStorage.getAccessToken as any).mockReturnValue('valid-token');
      (TokenStorage.getUserData as any).mockReturnValue(mockUser);
      (TokenStorage.isTokenExpired as any).mockReturnValue(false);

      const result = AuthService.isAuthenticated();

      expect(result).toBe(true);
    });

    it('should return false when no access token', () => {
      (TokenStorage.getAccessToken as any).mockReturnValue(null);
      (TokenStorage.getUserData as any).mockReturnValue(mockUser);

      const result = AuthService.isAuthenticated();

      expect(result).toBe(false);
    });

    it('should return false when no user data', () => {
      (TokenStorage.getAccessToken as any).mockReturnValue('valid-token');
      (TokenStorage.getUserData as any).mockReturnValue(null);

      const result = AuthService.isAuthenticated();

      expect(result).toBe(false);
    });

    it('should return false when token is expired', () => {
      (TokenStorage.getAccessToken as any).mockReturnValue('expired-token');
      (TokenStorage.getUserData as any).mockReturnValue(mockUser);
      (TokenStorage.isTokenExpired as any).mockReturnValue(true);

      const result = AuthService.isAuthenticated();

      expect(result).toBe(false);
    });
  });

  describe('getAccessToken', () => {
    it('should return access token from storage', () => {
      const mockToken = 'mock-access-token';
      (TokenStorage.getAccessToken as any).mockReturnValue(mockToken);

      const result = AuthService.getAccessToken();

      expect(result).toBe(mockToken);
      expect(TokenStorage.getAccessToken).toHaveBeenCalled();
    });
  });

  describe('getRefreshToken', () => {
    it('should return refresh token from storage', () => {
      const mockToken = 'mock-refresh-token';
      (TokenStorage.getRefreshToken as any).mockReturnValue(mockToken);

      const result = AuthService.getRefreshToken();

      expect(result).toBe(mockToken);
      expect(TokenStorage.getRefreshToken).toHaveBeenCalled();
    });
  });

  describe('getCurrentUser', () => {
    it('should return user data from storage', () => {
      (TokenStorage.getUserData as any).mockReturnValue(mockUser);

      const result = AuthService.getCurrentUser();

      expect(result).toBe(mockUser);
      expect(TokenStorage.getUserData).toHaveBeenCalled();
    });
  });

  describe('clearAuthData', () => {
    it('should clear auth data from storage', () => {
      AuthService.clearAuthData();

      expect(TokenStorage.clearAuthData).toHaveBeenCalled();
    });
  });

  describe('needsTokenRefresh', () => {
    it('should return true when token is expired', () => {
      (TokenStorage.getAccessToken as any).mockReturnValue('expired-token');
      (TokenStorage.isTokenExpired as any).mockReturnValue(true);

      const result = AuthService.needsTokenRefresh();

      expect(result).toBe(true);
    });

    it('should return false when token is valid', () => {
      (TokenStorage.getAccessToken as any).mockReturnValue('valid-token');
      (TokenStorage.isTokenExpired as any).mockReturnValue(false);

      const result = AuthService.needsTokenRefresh();

      expect(result).toBe(false);
    });

    it('should return false when no token available', () => {
      (TokenStorage.getAccessToken as any).mockReturnValue(null);

      const result = AuthService.needsTokenRefresh();

      expect(result).toBe(false);
    });
  });

  describe('initializeAuth', () => {
    it('should return authenticated user when token is valid', async () => {
      (TokenStorage.getAuthData as any).mockReturnValue({
        accessToken: 'valid-token',
        userData: mockUser,
      });
      (TokenStorage.isTokenExpired as any).mockReturnValue(false);
      (api.get as any).mockResolvedValue(mockUser);

      const result = await AuthService.initializeAuth();

      expect(result).toEqual({
        user: mockUser,
        isAuthenticated: true,
      });
    });

    it('should return unauthenticated when no auth data', async () => {
      (TokenStorage.getAuthData as any).mockReturnValue({
        accessToken: null,
        userData: null,
      });

      const result = await AuthService.initializeAuth();

      expect(result).toEqual({
        user: null,
        isAuthenticated: false,
      });
    });

    it('should refresh token when expired and return authenticated user', async () => {
      const mockRefreshResponse = {
        access_token: 'new-token',
        refresh_token: 'new-refresh-token',
        token_type: 'Bearer',
        expires_in: 3600,
        user: mockUser,
      };

      (TokenStorage.getAuthData as any).mockReturnValue({
        accessToken: 'expired-token',
        userData: mockUser,
      });
      (TokenStorage.isTokenExpired as any).mockReturnValue(true);
      (TokenStorage.getRefreshToken as any).mockReturnValue('refresh-token');
      (TokenStorage.getRememberMe as any).mockReturnValue(false);
      (api.post as any).mockResolvedValue(mockRefreshResponse);

      const result = await AuthService.initializeAuth();

      expect(result).toEqual({
        user: mockUser,
        isAuthenticated: true,
      });
    });

    it('should clear auth data and return unauthenticated when refresh fails', async () => {
      (TokenStorage.getAuthData as any).mockReturnValue({
        accessToken: 'expired-token',
        userData: mockUser,
      });
      (TokenStorage.isTokenExpired as any).mockReturnValue(true);
      (TokenStorage.getRefreshToken as any).mockReturnValue('expired-refresh-token');
      (api.post as any).mockRejectedValue(new Error('Refresh failed'));

      const result = await AuthService.initializeAuth();

      expect(TokenStorage.clearAuthData).toHaveBeenCalled();
      expect(result).toEqual({
        user: null,
        isAuthenticated: false,
      });
    });

    it('should handle profile fetch failure by trying refresh', async () => {
      const mockRefreshResponse = {
        access_token: 'new-token',
        refresh_token: 'new-refresh-token',
        token_type: 'Bearer',
        expires_in: 3600,
        user: mockUser,
      };

      (TokenStorage.getAuthData as any).mockReturnValue({
        accessToken: 'valid-token',
        userData: mockUser,
      });
      (TokenStorage.isTokenExpired as any).mockReturnValue(false);
      (api.get as any).mockRejectedValue(new Error('Profile fetch failed'));
      (TokenStorage.getRefreshToken as any).mockReturnValue('refresh-token');
      (TokenStorage.getRememberMe as any).mockReturnValue(false);
      (api.post as any).mockResolvedValue(mockRefreshResponse);

      const result = await AuthService.initializeAuth();

      expect(result).toEqual({
        user: mockUser,
        isAuthenticated: true,
      });
    });

    it('should clear auth data when both profile and refresh fail', async () => {
      (TokenStorage.getAuthData as any).mockReturnValue({
        accessToken: 'valid-token',
        userData: mockUser,
      });
      (TokenStorage.isTokenExpired as any).mockReturnValue(false);
      (api.get as any).mockRejectedValue(new Error('Profile fetch failed'));
      (TokenStorage.getRefreshToken as any).mockReturnValue('refresh-token');
      (api.post as any).mockRejectedValue(new Error('Refresh failed'));

      const result = await AuthService.initializeAuth();

      expect(TokenStorage.clearAuthData).toHaveBeenCalled();
      expect(result).toEqual({
        user: null,
        isAuthenticated: false,
      });
    });

    it('should handle initialization error gracefully', async () => {
      (TokenStorage.getAuthData as any).mockImplementation(() => {
        throw new Error('Storage error');
      });

      const result = await AuthService.initializeAuth();

      expect(TokenStorage.clearAuthData).toHaveBeenCalled();
      expect(result).toEqual({
        user: null,
        isAuthenticated: false,
      });
    });
  });
});