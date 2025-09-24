/**
 * Security tests for mobile authentication service
 *
 * Comprehensive test suite covering:
 * - Authentication flow security
 * - Token validation and storage
 * - Error handling and edge cases
 * - Security vulnerabilities
 */

import { jest, describe, it, expect, beforeEach, afterEach } from '@jest/globals'
import { mobileAuth, MobileAuthService } from '../mobileAuth'
import type { GoogleAuthCredentials, StoredAuthData } from '../mobileAuth'

// Mock SecureStore
jest.mock('expo-secure-store', () => ({
  setItemAsync: jest.fn(),
  getItemAsync: jest.fn(),
  deleteItemAsync: jest.fn(),
}))

// Mock fetch
const mockFetch = jest.fn() as jest.MockedFunction<typeof fetch>
global.fetch = mockFetch

describe('MobileAuthService Security Tests', () => {
  let authService: MobileAuthService

  beforeEach(() => {
    authService = MobileAuthService.getInstance()
    jest.clearAllMocks()

    // Mock environment variables
    process.env.EXPO_PUBLIC_API_URL = 'https://test-api.pucsr.edu.kh'
  })

  afterEach(() => {
    jest.restoreAllMocks()
  })

  describe('Authentication Flow Security', () => {
    it('should reject authentication with invalid email domain', async () => {
      const invalidCredentials: GoogleAuthCredentials = {
        idToken: 'valid-id-token',
        accessToken: 'valid-access-token',
        user: {
          email: 'test@gmail.com', // Invalid domain
          name: 'Test User',
          id: 'google-user-id',
        },
      }

      const result = await authService.authenticateWithGoogle(invalidCredentials, 'test-device')

      expect(result.success).toBe(false)
      expect(result.error).toContain('Invalid email domain')
      expect(result.error_code).toBe('INVALID_EMAIL_DOMAIN')
    })

    it('should accept authentication with valid PUCSR email domain', async () => {
      const validCredentials: GoogleAuthCredentials = {
        idToken: 'valid-id-token',
        accessToken: 'valid-access-token',
        user: {
          email: 'test.student@pucsr.edu.kh', // Valid domain
          name: 'Test Student',
          id: 'google-user-id',
        },
      }

      const mockResponse = {
        success: true,
        jwt_token: 'valid-jwt-token',
        student_id: 12345,
        email: 'test.student@pucsr.edu.kh',
        person_uuid: 'test-uuid',
        expires_at: Math.floor(Date.now() / 1000) + 3600,
        expires_in: 3600,
        profile: {
          student_id: 12345,
          person_uuid: 'test-uuid',
          full_name: 'Test Student',
          family_name: 'Student',
          personal_name: 'Test',
          school_email: 'test.student@pucsr.edu.kh',
          current_status: 'ACTIVE',
        },
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response)

      const result = await authService.authenticateWithGoogle(validCredentials, 'test-device')

      expect(result.success).toBe(true)
      expect(result.jwt_token).toBe('valid-jwt-token')
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/mobile/auth/google'),
        expect.objectContaining({
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            google_token: 'valid-id-token',
            email: 'test.student@pucsr.edu.kh',
            device_id: 'test-device',
          }),
        })
      )
    })

    it('should handle network errors gracefully', async () => {
      const validCredentials: GoogleAuthCredentials = {
        idToken: 'valid-id-token',
        accessToken: 'valid-access-token',
        user: {
          email: 'test.student@pucsr.edu.kh',
          name: 'Test Student',
          id: 'google-user-id',
        },
      }

      mockFetch.mockRejectedValueOnce(new Error('Network error'))

      const result = await authService.authenticateWithGoogle(validCredentials, 'test-device')

      expect(result.success).toBe(false)
      expect(result.error).toContain('Network error')
      expect(result.error_code).toBe('NETWORK_ERROR')
    })

    it('should handle server errors properly', async () => {
      const validCredentials: GoogleAuthCredentials = {
        idToken: 'invalid-token',
        accessToken: 'invalid-access-token',
        user: {
          email: 'test.student@pucsr.edu.kh',
          name: 'Test Student',
          id: 'google-user-id',
        },
      }

      const mockErrorResponse = {
        success: false,
        error: 'Invalid Google token',
        error_code: 'INVALID_GOOGLE_TOKEN',
      }

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => mockErrorResponse,
      } as Response)

      const result = await authService.authenticateWithGoogle(validCredentials, 'test-device')

      expect(result.success).toBe(false)
      expect(result.error).toBe('Invalid Google token')
      expect(result.error_code).toBe('INVALID_GOOGLE_TOKEN')
    })
  })

  describe('Token Security', () => {
    it('should detect expired tokens', async () => {
      const expiredAuthData: StoredAuthData = {
        email: 'test@pucsr.edu.kh',
        studentId: 12345,
        jwt: 'expired-jwt-token',
        tokenId: 'token-id',
        expiresAt: Math.floor(Date.now() / 1000) - 3600, // Expired 1 hour ago
        personUuid: 'test-uuid',
        profile: {
          student_id: 12345,
          person_uuid: 'test-uuid',
          full_name: 'Test Student',
          family_name: 'Student',
          personal_name: 'Test',
          school_email: 'test@pucsr.edu.kh',
          current_status: 'ACTIVE',
        },
      }

      const SecureStore = await import('expo-secure-store')
      SecureStore.getItemAsync.mockResolvedValueOnce(JSON.stringify(expiredAuthData))

      await authService.initialize()
      const isAuthenticated = await authService.isAuthenticated()

      expect(isAuthenticated).toBe(false)
    })

    it('should validate tokens with server', async () => {
      const validAuthData: StoredAuthData = {
        email: 'test@pucsr.edu.kh',
        studentId: 12345,
        jwt: 'valid-jwt-token',
        tokenId: 'token-id',
        expiresAt: Math.floor(Date.now() / 1000) + 3600, // Valid for 1 hour
        personUuid: 'test-uuid',
        profile: {
          student_id: 12345,
          person_uuid: 'test-uuid',
          full_name: 'Test Student',
          family_name: 'Student',
          personal_name: 'Test',
          school_email: 'test@pucsr.edu.kh',
          current_status: 'ACTIVE',
        },
      }

      const SecureStore = await import('expo-secure-store')
      SecureStore.getItemAsync.mockResolvedValueOnce(JSON.stringify(validAuthData))

      // Mock token validation response
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ valid: true }),
      } as Response)

      await authService.initialize()
      const isAuthenticated = await authService.isAuthenticated()

      expect(isAuthenticated).toBe(true)
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/mobile/auth/validate'),
        expect.objectContaining({
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ token: 'valid-jwt-token' }),
        })
      )
    })

    it('should handle invalid tokens from server validation', async () => {
      const invalidAuthData: StoredAuthData = {
        email: 'test@pucsr.edu.kh',
        studentId: 12345,
        jwt: 'invalid-jwt-token',
        tokenId: 'token-id',
        expiresAt: Math.floor(Date.now() / 1000) + 3600,
        personUuid: 'test-uuid',
        profile: {
          student_id: 12345,
          person_uuid: 'test-uuid',
          full_name: 'Test Student',
          family_name: 'Student',
          personal_name: 'Test',
          school_email: 'test@pucsr.edu.kh',
          current_status: 'ACTIVE',
        },
      }

      const SecureStore = await import('expo-secure-store')
      SecureStore.getItemAsync.mockResolvedValueOnce(JSON.stringify(invalidAuthData))

      // Mock token validation response - invalid token
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ valid: false, error: 'Invalid token' }),
      } as Response)

      await authService.initialize()
      const isAuthenticated = await authService.isAuthenticated()

      expect(isAuthenticated).toBe(false)
      expect(SecureStore.deleteItemAsync).toHaveBeenCalled()
    })

    it('should extract token ID correctly', async () => {
      // Create a mock JWT token with jti claim
      const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
      const payload = btoa(
        JSON.stringify({
          sub: 'student_12345',
          jti: 'unique-token-id',
          exp: Math.floor(Date.now() / 1000) + 3600,
        })
      )
      const mockJWT = `${header}.${payload}.mock-signature`

      const validCredentials: GoogleAuthCredentials = {
        idToken: 'valid-id-token',
        accessToken: 'valid-access-token',
        user: {
          email: 'test.student@pucsr.edu.kh',
          name: 'Test Student',
          id: 'google-user-id',
        },
      }

      const mockResponse = {
        success: true,
        jwt_token: mockJWT,
        student_id: 12345,
        email: 'test.student@pucsr.edu.kh',
        person_uuid: 'test-uuid',
        expires_at: Math.floor(Date.now() / 1000) + 3600,
        expires_in: 3600,
        profile: {
          student_id: 12345,
          person_uuid: 'test-uuid',
          full_name: 'Test Student',
          family_name: 'Student',
          personal_name: 'Test',
          school_email: 'test.student@pucsr.edu.kh',
          current_status: 'ACTIVE',
        },
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response)

      const SecureStore = await import('expo-secure-store')
      SecureStore.setItemAsync.mockResolvedValueOnce(undefined)

      const result = await authService.authenticateWithGoogle(validCredentials, 'test-device')

      expect(result.success).toBe(true)
      expect(SecureStore.setItemAsync).toHaveBeenCalledWith(
        'naga_auth_data',
        expect.stringContaining('unique-token-id')
      )
    })
  })

  describe('Secure Storage', () => {
    it('should store authentication data securely', async () => {
      const validCredentials: GoogleAuthCredentials = {
        idToken: 'valid-id-token',
        accessToken: 'valid-access-token',
        user: {
          email: 'test.student@pucsr.edu.kh',
          name: 'Test Student',
          id: 'google-user-id',
        },
      }

      const mockResponse = {
        success: true,
        jwt_token: 'valid-jwt-token',
        student_id: 12345,
        email: 'test.student@pucsr.edu.kh',
        person_uuid: 'test-uuid',
        expires_at: Math.floor(Date.now() / 1000) + 3600,
        expires_in: 3600,
        profile: {
          student_id: 12345,
          person_uuid: 'test-uuid',
          full_name: 'Test Student',
          family_name: 'Student',
          personal_name: 'Test',
          school_email: 'test.student@pucsr.edu.kh',
          current_status: 'ACTIVE',
        },
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response)

      const SecureStore = await import('expo-secure-store')
      SecureStore.setItemAsync.mockResolvedValueOnce(undefined)

      await authService.authenticateWithGoogle(validCredentials, 'test-device')

      expect(SecureStore.setItemAsync).toHaveBeenCalledWith(
        'naga_auth_data',
        expect.stringContaining('valid-jwt-token')
      )
    })

    it('should handle storage errors gracefully', async () => {
      const validCredentials: GoogleAuthCredentials = {
        idToken: 'valid-id-token',
        accessToken: 'valid-access-token',
        user: {
          email: 'test.student@pucsr.edu.kh',
          name: 'Test Student',
          id: 'google-user-id',
        },
      }

      const mockResponse = {
        success: true,
        jwt_token: 'valid-jwt-token',
        student_id: 12345,
        email: 'test.student@pucsr.edu.kh',
        person_uuid: 'test-uuid',
        expires_at: Math.floor(Date.now() / 1000) + 3600,
        expires_in: 3600,
        profile: {
          student_id: 12345,
          person_uuid: 'test-uuid',
          full_name: 'Test Student',
          family_name: 'Student',
          personal_name: 'Test',
          school_email: 'test.student@pucsr.edu.kh',
          current_status: 'ACTIVE',
        },
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response)

      const SecureStore = await import('expo-secure-store')
      SecureStore.setItemAsync.mockRejectedValueOnce(new Error('Storage error'))

      await expect(
        authService.authenticateWithGoogle(validCredentials, 'test-device')
      ).rejects.toThrow('Failed to store authentication data securely')
    })

    it('should clear sensitive data on logout', async () => {
      const SecureStore = await import('expo-secure-store')
      SecureStore.deleteItemAsync.mockResolvedValueOnce(undefined)

      // Mock successful logout request
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true }),
      } as Response)

      await authService.logout()

      expect(SecureStore.deleteItemAsync).toHaveBeenCalledWith('naga_auth_data')
    })
  })

  describe('API Request Security', () => {
    it('should add proper authentication headers', async () => {
      const authData: StoredAuthData = {
        email: 'test@pucsr.edu.kh',
        studentId: 12345,
        jwt: 'valid-jwt-token',
        tokenId: 'token-id',
        expiresAt: Math.floor(Date.now() / 1000) + 3600,
        personUuid: 'test-uuid',
        profile: {
          student_id: 12345,
          person_uuid: 'test-uuid',
          full_name: 'Test Student',
          family_name: 'Student',
          personal_name: 'Test',
          school_email: 'test@pucsr.edu.kh',
          current_status: 'ACTIVE',
        },
      }

      const SecureStore = await import('expo-secure-store')
      SecureStore.getItemAsync.mockResolvedValueOnce(JSON.stringify(authData))

      // Mock token validation
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ valid: true }),
      } as Response)

      // Mock API request
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ data: 'success' }),
      } as Response)

      await authService.initialize()
      await authService.makeAuthenticatedRequest('https://api.example.com/data')

      expect(mockFetch).toHaveBeenCalledWith(
        'https://api.example.com/data',
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer valid-jwt-token',
            'Content-Type': 'application/json',
            'X-Student-ID': '12345',
          }),
        })
      )
    })

    it('should handle 401 responses by clearing auth data', async () => {
      const authData: StoredAuthData = {
        email: 'test@pucsr.edu.kh',
        studentId: 12345,
        jwt: 'expired-jwt-token',
        tokenId: 'token-id',
        expiresAt: Math.floor(Date.now() / 1000) + 3600,
        personUuid: 'test-uuid',
        profile: {
          student_id: 12345,
          person_uuid: 'test-uuid',
          full_name: 'Test Student',
          family_name: 'Student',
          personal_name: 'Test',
          school_email: 'test@pucsr.edu.kh',
          current_status: 'ACTIVE',
        },
      }

      const SecureStore = await import('expo-secure-store')
      SecureStore.getItemAsync.mockResolvedValueOnce(JSON.stringify(authData))
      SecureStore.deleteItemAsync.mockResolvedValueOnce(undefined)

      // Mock token validation
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ valid: true }),
      } as Response)

      // Mock 401 response
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ error: 'Unauthorized' }),
      } as Response)

      await authService.initialize()

      await expect(
        authService.makeAuthenticatedRequest('https://api.example.com/data')
      ).rejects.toThrow('Authentication failed')

      expect(SecureStore.deleteItemAsync).toHaveBeenCalledWith('naga_auth_data')
    })
  })

  describe('Error Handling', () => {
    it('should not expose sensitive information in errors', async () => {
      const validCredentials: GoogleAuthCredentials = {
        idToken: 'valid-id-token',
        accessToken: 'valid-access-token',
        user: {
          email: 'test.student@pucsr.edu.kh',
          name: 'Test Student',
          id: 'google-user-id',
        },
      }

      const mockErrorResponse = {
        success: false,
        error: 'Internal server error: Database connection failed on server db-prod-123',
        error_code: 'INTERNAL_ERROR',
      }

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => mockErrorResponse,
      } as Response)

      const result = await authService.authenticateWithGoogle(validCredentials, 'test-device')

      expect(result.success).toBe(false)
      // Should not expose internal server details
      expect(result.error).not.toContain('db-prod-123')
      expect(result.error).not.toContain('Database connection failed')
    })

    it('should handle malformed server responses', async () => {
      const validCredentials: GoogleAuthCredentials = {
        idToken: 'valid-id-token',
        accessToken: 'valid-access-token',
        user: {
          email: 'test.student@pucsr.edu.kh',
          name: 'Test Student',
          id: 'google-user-id',
        },
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => {
          throw new Error('Invalid JSON')
        },
      } as Response)

      const result = await authService.authenticateWithGoogle(validCredentials, 'test-device')

      expect(result.success).toBe(false)
      expect(result.error).toContain('Network error')
    })
  })
})
