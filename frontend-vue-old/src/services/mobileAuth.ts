/**
 * Mobile Authentication Service
 *
 * Provides secure authentication services for mobile applications including:
 * - Google OAuth authentication
 * - JWT token management
 * - Secure storage of authentication data
 * - API request authentication
 */

import * as SecureStore from 'expo-secure-store'

// Types
export interface GoogleAuthCredentials {
  idToken: string
  accessToken: string
  user: {
    email: string
    name: string
    picture?: string
    id: string
  }
}

export interface StoredAuthData {
  email: string
  studentId: number
  jwt: string
  tokenId: string
  expiresAt: number
  personUuid: string
  profile: StudentProfile
}

export interface StudentProfile {
  student_id: number
  person_uuid: string
  full_name: string
  family_name: string
  personal_name: string
  school_email: string
  phone?: string
  current_status: string
  enrollment_date?: string
  graduation_date?: string
}

export interface AuthResponse {
  success: boolean
  jwt_token?: string
  student_id?: number
  email?: string
  person_uuid?: string
  expires_at?: number
  expires_in?: number
  profile?: StudentProfile
  error?: string
  error_code?: string
}

export interface TokenValidationResponse {
  valid: boolean
  claims?: Record<string, any>
  error?: string
}

import { getApiConfig, getAuthConfig } from '../config/env'

// Constants
const STORAGE_KEY = 'naga_auth_data'
const API_BASE_URL = getApiConfig().baseUrl.replace('/api', '') // Remove /api since we'll add it back
const ALLOWED_EMAIL_DOMAIN = `@${getAuthConfig().allowedEmailDomain}`

export class MobileAuthService {
  private static instance: MobileAuthService
  private authData: StoredAuthData | null = null
  private isInitialized = false

  private constructor() {}

  static getInstance(): MobileAuthService {
    if (!MobileAuthService.instance) {
      MobileAuthService.instance = new MobileAuthService()
    }
    return MobileAuthService.instance
  }

  /**
   * Initialize the authentication service
   */
  async initialize(): Promise<void> {
    if (this.isInitialized) return

    try {
      this.authData = await this.getStoredAuthData()

      // Validate stored token if exists
      if (this.authData) {
        const isValid = await this.validateStoredToken()
        if (!isValid) {
          await this.clearAuthData()
          this.authData = null
        }
      }

      this.isInitialized = true
    } catch (error) {
      console.error('Failed to initialize MobileAuthService:', error)
      this.isInitialized = true // Continue even if initialization fails
    }
  }

  /**
   * Authenticate with Google OAuth
   */
  async authenticateWithGoogle(
    credentials: GoogleAuthCredentials,
    deviceId: string
  ): Promise<AuthResponse> {
    try {
      // Validate email domain
      if (!credentials.user.email.endsWith(ALLOWED_EMAIL_DOMAIN)) {
        return {
          success: false,
          error: `Invalid email domain. Please use your ${ALLOWED_EMAIL_DOMAIN} email address.`,
          error_code: 'INVALID_EMAIL_DOMAIN',
        }
      }

      // Send authentication request to backend
      const response = await fetch(`${API_BASE_URL}/api/mobile/auth/google`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          google_token: credentials.idToken,
          email: credentials.user.email,
          device_id: deviceId,
        }),
      })

      const data: AuthResponse = await response.json()

      if (!response.ok) {
        return {
          success: false,
          error: data.error || 'Authentication failed',
          error_code: data.error_code || 'AUTHENTICATION_FAILED',
        }
      }

      if (data.success && data.jwt_token) {
        // Store authentication data securely
        const authData: StoredAuthData = {
          email: data.email!,
          studentId: data.student_id!,
          jwt: data.jwt_token,
          tokenId: this.extractTokenId(data.jwt_token),
          expiresAt: data.expires_at!,
          personUuid: data.person_uuid!,
          profile: data.profile!,
        }

        await this.storeAuthData(authData)
        this.authData = authData

        return {
          success: true,
          ...data,
        }
      }

      return {
        success: false,
        error: 'Invalid response from server',
        error_code: 'INVALID_RESPONSE',
      }
    } catch (error) {
      console.error('Google authentication error:', error)
      return {
        success: false,
        error: 'Network error. Please check your connection and try again.',
        error_code: 'NETWORK_ERROR',
      }
    }
  }

  /**
   * Validate current authentication status
   */
  async isAuthenticated(): Promise<boolean> {
    if (!this.isInitialized) {
      await this.initialize()
    }

    if (!this.authData) {
      return false
    }

    // Check if token is expired
    if (Date.now() >= this.authData.expiresAt * 1000) {
      await this.clearAuthData()
      return false
    }

    // Optionally validate token with server
    const validation = await this.validateToken(this.authData.jwt)
    if (!validation.valid) {
      await this.clearAuthData()
      return false
    }

    return true
  }

  /**
   * Get current authentication data
   */
  async getAuthData(): Promise<StoredAuthData | null> {
    if (!this.isInitialized) {
      await this.initialize()
    }

    return this.authData
  }

  /**
   * Get current student profile
   */
  async getStudentProfile(): Promise<StudentProfile | null> {
    const authData = await this.getAuthData()
    return authData?.profile || null
  }

  /**
   * Make authenticated API request
   */
  async makeAuthenticatedRequest(url: string, options: RequestInit = {}): Promise<Response> {
    if (!this.isInitialized) {
      await this.initialize()
    }

    if (!this.authData) {
      throw new Error('No authentication data available')
    }

    // Check if token is expired
    if (Date.now() >= this.authData.expiresAt * 1000) {
      throw new Error('Authentication token has expired')
    }

    // Add authentication headers
    const headers = {
      Authorization: `Bearer ${this.authData.jwt}`,
      'Content-Type': 'application/json',
      'X-Student-ID': this.authData.studentId.toString(),
      ...options.headers,
    }

    const response = await fetch(url, {
      ...options,
      headers,
    })

    // Handle authentication errors
    if (response.status === 401) {
      await this.clearAuthData()
      throw new Error('Authentication failed. Please login again.')
    }

    return response
  }

  /**
   * Logout and clear authentication data
   */
  async logout(): Promise<void> {
    if (this.authData) {
      try {
        // Attempt to revoke token on server
        await this.makeAuthenticatedRequest(`${API_BASE_URL}/api/mobile/auth/logout`, {
          method: 'POST',
        })
      } catch (error) {
        console.warn('Failed to revoke token on server:', error)
      }
    }

    await this.clearAuthData()
  }

  /**
   * Validate token with server
   */
  private async validateToken(token: string): Promise<TokenValidationResponse> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/mobile/auth/validate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ token }),
      })

      if (!response.ok) {
        return { valid: false, error: 'Validation request failed' }
      }

      return await response.json()
    } catch (error) {
      console.error('Token validation error:', error)
      return { valid: false, error: 'Network error during validation' }
    }
  }

  /**
   * Validate stored token
   */
  private async validateStoredToken(): Promise<boolean> {
    if (!this.authData) return false

    // Check local expiration
    if (Date.now() >= this.authData.expiresAt * 1000) {
      return false
    }

    // Validate with server
    const validation = await this.validateToken(this.authData.jwt)
    return validation.valid
  }

  /**
   * Store authentication data securely
   */
  private async storeAuthData(authData: StoredAuthData): Promise<void> {
    try {
      await SecureStore.setItemAsync(STORAGE_KEY, JSON.stringify(authData))
    } catch (error) {
      console.error('Failed to store authentication data:', error)
      throw new Error('Failed to store authentication data securely')
    }
  }

  /**
   * Retrieve stored authentication data
   */
  private async getStoredAuthData(): Promise<StoredAuthData | null> {
    try {
      const data = await SecureStore.getItemAsync(STORAGE_KEY)
      return data ? JSON.parse(data) : null
    } catch (error) {
      console.error('Failed to retrieve authentication data:', error)
      return null
    }
  }

  /**
   * Clear authentication data
   */
  private async clearAuthData(): Promise<void> {
    try {
      await SecureStore.deleteItemAsync(STORAGE_KEY)
      this.authData = null
    } catch (error) {
      console.error('Failed to clear authentication data:', error)
    }
  }

  /**
   * Extract token ID from JWT token
   */
  private extractTokenId(token: string): string {
    try {
      const payload = JSON.parse(atob(token.split('.')[1]))
      return payload.jti || ''
    } catch (error) {
      console.error('Failed to extract token ID:', error)
      return ''
    }
  }
}

// Export singleton instance
export const mobileAuth = MobileAuthService.getInstance()

// Hook for React components
export const useMobileAuth = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [authData, setAuthData] = useState<StoredAuthData | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const checkAuth = async () => {
      setIsLoading(true)
      try {
        const authenticated = await mobileAuth.isAuthenticated()
        setIsAuthenticated(authenticated)

        if (authenticated) {
          const data = await mobileAuth.getAuthData()
          setAuthData(data)
        }
      } catch (error) {
        console.error('Auth check failed:', error)
        setIsAuthenticated(false)
        setAuthData(null)
      } finally {
        setIsLoading(false)
      }
    }

    checkAuth()
  }, [])

  const login = async (credentials: GoogleAuthCredentials, deviceId: string) => {
    setIsLoading(true)
    try {
      const result = await mobileAuth.authenticateWithGoogle(credentials, deviceId)

      if (result.success) {
        setIsAuthenticated(true)
        const data = await mobileAuth.getAuthData()
        setAuthData(data)
      }

      return result
    } finally {
      setIsLoading(false)
    }
  }

  const logout = async () => {
    setIsLoading(true)
    try {
      await mobileAuth.logout()
      setIsAuthenticated(false)
      setAuthData(null)
    } finally {
      setIsLoading(false)
    }
  }

  const makeAuthenticatedRequest = async (url: string, options?: RequestInit) => {
    return mobileAuth.makeAuthenticatedRequest(url, options)
  }

  return {
    isAuthenticated,
    authData,
    isLoading,
    login,
    logout,
    makeAuthenticatedRequest,
  }
}

// This is a Vue project, not React
