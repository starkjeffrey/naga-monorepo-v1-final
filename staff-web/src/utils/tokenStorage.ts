/**
 * Token storage utilities for secure JWT token management
 */

import { STORAGE_KEYS } from './constants';
import type { User, AuthTokens } from '../types/auth.types';

/**
 * Token storage interface for managing JWT tokens
 */
export class TokenStorage {
  /**
   * Store access token in localStorage
   */
  static setAccessToken(token: string): void {
    try {
      localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, token);
    } catch (error) {
      console.error('Failed to store access token:', error);
    }
  }

  /**
   * Get access token from localStorage
   */
  static getAccessToken(): string | null {
    try {
      return localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
    } catch (error) {
      console.error('Failed to retrieve access token:', error);
      return null;
    }
  }

  /**
   * Store refresh token in localStorage
   */
  static setRefreshToken(token: string): void {
    try {
      localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, token);
    } catch (error) {
      console.error('Failed to store refresh token:', error);
    }
  }

  /**
   * Get refresh token from localStorage
   */
  static getRefreshToken(): string | null {
    try {
      return localStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN);
    } catch (error) {
      console.error('Failed to retrieve refresh token:', error);
      return null;
    }
  }

  /**
   * Store user data in localStorage
   */
  static setUserData(user: User): void {
    try {
      localStorage.setItem(STORAGE_KEYS.USER_DATA, JSON.stringify(user));
    } catch (error) {
      console.error('Failed to store user data:', error);
    }
  }

  /**
   * Get user data from localStorage
   */
  static getUserData(): User | null {
    try {
      const userData = localStorage.getItem(STORAGE_KEYS.USER_DATA);
      return userData ? JSON.parse(userData) : null;
    } catch (error) {
      console.error('Failed to retrieve user data:', error);
      return null;
    }
  }

  /**
   * Store remember me preference
   */
  static setRememberMe(remember: boolean): void {
    try {
      localStorage.setItem(STORAGE_KEYS.REMEMBER_ME, remember.toString());
    } catch (error) {
      console.error('Failed to store remember me preference:', error);
    }
  }

  /**
   * Get remember me preference
   */
  static getRememberMe(): boolean {
    try {
      const rememberMe = localStorage.getItem(STORAGE_KEYS.REMEMBER_ME);
      return rememberMe === 'true';
    } catch (error) {
      console.error('Failed to retrieve remember me preference:', error);
      return false;
    }
  }

  /**
   * Store all authentication data at once
   */
  static setAuthData(tokens: AuthTokens, user: User, rememberMe = false): void {
    this.setAccessToken(tokens.access_token);
    this.setRefreshToken(tokens.refresh_token);
    this.setUserData(user);
    this.setRememberMe(rememberMe);
  }

  /**
   * Get all authentication data at once
   */
  static getAuthData(): {
    accessToken: string | null;
    refreshToken: string | null;
    userData: User | null;
    rememberMe: boolean;
  } {
    return {
      accessToken: this.getAccessToken(),
      refreshToken: this.getRefreshToken(),
      userData: this.getUserData(),
      rememberMe: this.getRememberMe(),
    };
  }

  /**
   * Clear all authentication data
   */
  static clearAuthData(): void {
    try {
      localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
      localStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN);
      localStorage.removeItem(STORAGE_KEYS.USER_DATA);
      localStorage.removeItem(STORAGE_KEYS.REMEMBER_ME);
    } catch (error) {
      console.error('Failed to clear auth data:', error);
    }
  }

  /**
   * Check if user is authenticated based on stored tokens
   */
  static isAuthenticated(): boolean {
    return Boolean(this.getAccessToken() && this.getUserData());
  }

  /**
   * Decode JWT token payload (without verification)
   * Note: This is for client-side use only, server should verify tokens
   */
  static decodeToken(token: string): any {
    try {
      const parts = token.split('.');
      if (parts.length !== 3) {
        throw new Error('Invalid token format');
      }

      const payload = parts[1];
      const decoded = atob(payload.replace(/-/g, '+').replace(/_/g, '/'));
      return JSON.parse(decoded);
    } catch (error) {
      console.error('Failed to decode token:', error);
      return null;
    }
  }

  /**
   * Check if token is expired (with buffer)
   */
  static isTokenExpired(token: string, bufferSeconds = 300): boolean {
    try {
      const decoded = this.decodeToken(token);
      if (!decoded || !decoded.exp) {
        return true;
      }

      const currentTime = Math.floor(Date.now() / 1000);
      return decoded.exp - currentTime <= bufferSeconds;
    } catch (error) {
      console.error('Failed to check token expiry:', error);
      return true;
    }
  }

  /**
   * Get token expiry time
   */
  static getTokenExpiry(token: string): Date | null {
    try {
      const decoded = this.decodeToken(token);
      if (!decoded || !decoded.exp) {
        return null;
      }

      return new Date(decoded.exp * 1000);
    } catch (error) {
      console.error('Failed to get token expiry:', error);
      return null;
    }
  }
}