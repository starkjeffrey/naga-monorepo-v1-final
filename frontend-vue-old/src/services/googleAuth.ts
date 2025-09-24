/**
 * Google OAuth Authentication Service for Web
 *
 * Provides Google OAuth 2.0 authentication for web applications with:
 * - Domain restriction to @pucsr.edu.kh
 * - JWT token management
 * - Role-based authentication
 * - Backend integration for school authentication
 */

import { getApiConfig, getAuthConfig } from '../config/env'

// Types for Google OAuth
export interface GoogleUser {
  sub: string
  email: string
  email_verified: boolean
  name: string
  picture?: string
  given_name: string
  family_name: string
  hd?: string // Google Workspace domain
}

export interface GoogleAuthCredentials {
  access_token: string
  id_token: string
  expires_in: number
  token_type: string
  scope: string
}

export interface AuthResponse {
  success: boolean
  jwt_token?: string
  student_id?: number
  teacher_id?: number
  email?: string
  user_uuid?: string
  expires_at?: number
  expires_in?: number
  role?: 'student' | 'teacher'
  profile?: UserProfile
  error?: string
  error_code?: string
}

export interface UserProfile {
  user_uuid: string
  email: string
  full_name: string
  given_name: string
  family_name: string
  role: 'student' | 'teacher'
  status: string
  profile_picture?: string
  // Student-specific fields (when role is student)
  student_id?: number
  enrollment_date?: string
  graduation_date?: string
  // Teacher-specific fields (when role is teacher)
  teacher_id?: number
  department?: string
  hire_date?: string
}

export interface StoredAuthData {
  jwt: string
  user_uuid: string
  email: string
  role: 'student' | 'teacher'
  expires_at: number
  profile: UserProfile
}

// Google OAuth Configuration
const GOOGLE_OAUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
const GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
const GOOGLE_USERINFO_URL = 'https://www.googleapis.com/oauth2/v2/userinfo'

// Storage keys
const AUTH_STORAGE_KEY = 'naga_auth_data'
const TOKEN_STORAGE_KEY = 'naga_access_token'

export class GoogleAuthService {
  private static instance: GoogleAuthService
  private authData: StoredAuthData | null = null
  private isInitialized = false

  private constructor() {}

  static getInstance(): GoogleAuthService {
    if (!GoogleAuthService.instance) {
      GoogleAuthService.instance = new GoogleAuthService()
    }
    return GoogleAuthService.instance
  }

  /**
   * Initialize the authentication service
   */
  async initialize(): Promise<void> {
    if (this.isInitialized) return

    try {
      // Load stored authentication data
      this.authData = this.getStoredAuthData()

      // Validate stored token if exists
      if (this.authData) {
        const isValid = await this.isTokenValid()
        if (!isValid) {
          await this.clearAuthData()
          this.authData = null
        }
      }

      this.isInitialized = true
    } catch (error) {
      console.error('Failed to initialize GoogleAuthService:', error)
      this.isInitialized = true // Continue even if initialization fails
    }
  }

  /**
   * Start Google OAuth authentication flow
   */
  async signInWithGoogle(): Promise<void> {
    const authConfig = getAuthConfig()

    // Build Google OAuth URL
    const params = new URLSearchParams({
      client_id: authConfig.googleClientId,
      redirect_uri: authConfig.redirectUri,
      response_type: 'code',
      scope: 'openid email profile',
      access_type: 'offline',
      prompt: 'select_account',
      hd: authConfig.allowedEmailDomain, // Restrict to domain
    })

    const authUrl = `${GOOGLE_OAUTH_URL}?${params.toString()}`

    // Redirect to Google OAuth
    window.location.href = authUrl
  }

  /**
   * Handle OAuth callback with authorization code
   */
  async handleAuthCallback(code: string): Promise<AuthResponse> {
    try {
      // Exchange code for tokens
      const tokenResponse = await this.exchangeCodeForTokens(code)

      // Get user info from Google
      const userInfo = await this.getUserInfo(tokenResponse.access_token)

      // Validate email domain
      if (!this.isValidDomain(userInfo.email)) {
        return {
          success: false,
          error: `Please use your @${getAuthConfig().allowedEmailDomain} email address.`,
          error_code: 'INVALID_EMAIL_DOMAIN',
        }
      }

      // Authenticate with backend
      const authResult = await this.authenticateWithBackend(tokenResponse, userInfo)

      if (authResult.success && authResult.jwt_token) {
        // Store authentication data
        const authData: StoredAuthData = {
          jwt: authResult.jwt_token,
          user_uuid: authResult.user_uuid!,
          email: authResult.email!,
          role: authResult.role!,
          expires_at: authResult.expires_at!,
          profile: authResult.profile!,
        }

        this.storeAuthData(authData)
        this.authData = authData
      }

      return authResult
    } catch (error) {
      console.error('Auth callback error:', error)
      return {
        success: false,
        error: 'Authentication failed. Please try again.',
        error_code: 'AUTHENTICATION_ERROR',
      }
    }
  }

  /**
   * Check if user is authenticated
   */
  async isAuthenticated(): Promise<boolean> {
    if (!this.isInitialized) {
      await this.initialize()
    }

    if (!this.authData) {
      return false
    }

    // Check if token is expired
    if (Date.now() >= this.authData.expires_at * 1000) {
      await this.clearAuthData()
      return false
    }

    // Validate with server
    const isValid = await this.isTokenValid()
    if (!isValid) {
      await this.clearAuthData()
      return false
    }

    return true
  }

  /**
   * Get current authentication data
   */
  getAuthData(): StoredAuthData | null {
    return this.authData
  }

  /**
   * Make authenticated API request
   */
  async makeAuthenticatedRequest(url: string, options: RequestInit = {}): Promise<Response> {
    if (!this.authData) {
      throw new Error('Not authenticated')
    }

    // Check if token is expired
    if (Date.now() >= this.authData.expires_at * 1000) {
      throw new Error('Authentication token has expired')
    }

    // Add authentication headers
    const headers = {
      Authorization: `Bearer ${this.authData.jwt}`,
      'Content-Type': 'application/json',
      'X-User-UUID': this.authData.user_uuid,
      'X-User-Role': this.authData.role,
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
   * Sign out and clear authentication data
   */
  async signOut(): Promise<void> {
    if (this.authData) {
      try {
        // Attempt to revoke token on server
        const apiConfig = getApiConfig()
        await this.makeAuthenticatedRequest(`${apiConfig.baseUrl}/auth/logout`, {
          method: 'POST',
        })
      } catch (error) {
        console.warn('Failed to revoke token on server:', error)
      }
    }

    await this.clearAuthData()
  }

  /**
   * Get current user profile
   */
  getUserProfile(): UserProfile | null {
    return this.authData?.profile || null
  }

  /**
   * Check if user has specific role
   */
  hasRole(role: 'student' | 'teacher'): boolean {
    return this.authData?.role === role
  }

  // Private methods

  private async exchangeCodeForTokens(code: string): Promise<GoogleAuthCredentials> {
    const authConfig = getAuthConfig()

    const response = await fetch(GOOGLE_TOKEN_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        client_id: authConfig.googleClientId,
        client_secret: '', // For web apps, this might be empty or handled server-side
        code,
        grant_type: 'authorization_code',
        redirect_uri: authConfig.redirectUri,
      }),
    })

    if (!response.ok) {
      throw new Error('Token exchange failed')
    }

    return await response.json()
  }

  private async getUserInfo(accessToken: string): Promise<GoogleUser> {
    const response = await fetch(`${GOOGLE_USERINFO_URL}?access_token=${accessToken}`)

    if (!response.ok) {
      throw new Error('Failed to get user info from Google')
    }

    return await response.json()
  }

  private isValidDomain(email: string): boolean {
    const allowedDomain = `@${getAuthConfig().allowedEmailDomain}`
    return email.endsWith(allowedDomain)
  }

  private async authenticateWithBackend(
    tokens: GoogleAuthCredentials,
    userInfo: GoogleUser
  ): Promise<AuthResponse> {
    const apiConfig = getApiConfig()

    const response = await fetch(`${apiConfig.baseUrl}/auth/google`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        google_token: tokens.id_token,
        access_token: tokens.access_token,
        email: userInfo.email,
        name: userInfo.name,
        picture: userInfo.picture,
        given_name: userInfo.given_name,
        family_name: userInfo.family_name,
        domain: userInfo.hd,
      }),
    })

    const data: AuthResponse = await response.json()

    if (!response.ok) {
      return {
        success: false,
        error: data.error || 'Authentication failed',
        error_code: data.error_code || 'BACKEND_AUTH_FAILED',
      }
    }

    return data
  }

  private async isTokenValid(): Promise<boolean> {
    if (!this.authData) return false

    try {
      const apiConfig = getApiConfig()
      const response = await fetch(`${apiConfig.baseUrl}/auth/validate`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${this.authData.jwt}`,
          'Content-Type': 'application/json',
        },
      })

      return response.ok
    } catch (error) {
      console.error('Token validation error:', error)
      return false
    }
  }

  private storeAuthData(authData: StoredAuthData): void {
    try {
      localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(authData))
      localStorage.setItem(TOKEN_STORAGE_KEY, authData.jwt)
    } catch (error) {
      console.error('Failed to store authentication data:', error)
    }
  }

  private getStoredAuthData(): StoredAuthData | null {
    try {
      const stored = localStorage.getItem(AUTH_STORAGE_KEY)
      return stored ? JSON.parse(stored) : null
    } catch (error) {
      console.error('Failed to retrieve authentication data:', error)
      return null
    }
  }

  private async clearAuthData(): Promise<void> {
    try {
      localStorage.removeItem(AUTH_STORAGE_KEY)
      localStorage.removeItem(TOKEN_STORAGE_KEY)
      this.authData = null
    } catch (error) {
      console.error('Failed to clear authentication data:', error)
    }
  }
}

// Export singleton instance
export const googleAuth = GoogleAuthService.getInstance()
