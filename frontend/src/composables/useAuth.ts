/**
 * Vue 3 Authentication Composable
 *
 * Provides reactive authentication state and methods using Google OAuth
 * Replaces previous Keycloak-based authentication
 */

import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useDatabase } from './useDatabase'
import { googleAuth, type AuthResponse, type UserProfile } from '@/services/googleAuth'
import { devAuth, type DevUserType } from '@/services/devAuth'
import { useRole } from './useRole'

// Global reactive state
const isAuthenticated = ref(false)
const currentUser = ref<UserProfile | null>(null)
const activeRole = ref<'student' | 'teacher' | null>(null)
const authLoading = ref(false)
const authError = ref<string | null>(null)

// Initialization flag
let isInitialized = false

export function useAuth() {
  const router = useRouter()
  const { setCurrentUser, clearCurrentUser } = useDatabase()
  const { initializeRoles } = useRole()

  /**
   * Initialize authentication state
   */
  const initializeAuth = async (): Promise<void> => {
    if (isInitialized) return

    try {
      authLoading.value = true
      authError.value = null

      // Initialize Google Auth service
      await googleAuth.initialize()

      // Check authentication status
      const authenticated = await googleAuth.isAuthenticated()
      isAuthenticated.value = authenticated

      if (authenticated) {
        const authData = googleAuth.getAuthData()
        if (authData) {
          currentUser.value = authData.profile
          activeRole.value = authData.role

          // Update local database
          await setCurrentUser(authData.user_uuid, {
            name: authData.profile.full_name,
            email: authData.email,
            role: authData.role,
            avatar: authData.profile.profile_picture,
          })
        }
      }

      isInitialized = true
    } catch (error) {
      console.error('Failed to initialize authentication:', error)
      authError.value = 'Failed to initialize authentication'
      isAuthenticated.value = false
      currentUser.value = null
      activeRole.value = null
    } finally {
      authLoading.value = false
    }
  }

  /**
   * Sign in with Google OAuth
   */
  const signInWithGoogle = async (): Promise<void> => {
    try {
      authLoading.value = true
      authError.value = null

      await googleAuth.signInWithGoogle()
      // Note: This will redirect to Google, so the function won't return normally
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Google sign in failed'
      authError.value = errorMessage
      throw error
    } finally {
      authLoading.value = false
    }
  }

  /**
   * Handle OAuth callback with authorization code
   */
  const handleAuthCallback = async (code: string): Promise<void> => {
    try {
      authLoading.value = true
      authError.value = null

      const result: AuthResponse = await googleAuth.handleAuthCallback(code)

      if (result.success && result.profile) {
        // Update reactive state
        isAuthenticated.value = true
        currentUser.value = result.profile
        activeRole.value = result.role!

        // Update local database
        await setCurrentUser(result.user_uuid!, {
          name: result.profile.full_name,
          email: result.email!,
          role: result.role!,
          avatar: result.profile.profile_picture,
          phone: '', // Default empty for dev users
          preferredLanguage: 'en', // Default to English
          theme: 'light', // Default theme
        })

        // Redirect to appropriate dashboard
        if (result.role === 'teacher') {
          router.push({ name: 'TeacherDashboard' })
        } else {
          router.push({ name: 'Dashboard' })
        }
      } else {
        throw new Error(result.error || 'Authentication failed')
      }
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Authentication callback failed'
      authError.value = errorMessage
      isAuthenticated.value = false
      currentUser.value = null
      activeRole.value = null
      throw error
    } finally {
      authLoading.value = false
    }
  }

  /**
   * Sign out user
   */
  const signOut = async (): Promise<void> => {
    try {
      authLoading.value = true
      authError.value = null

      // Sign out from Google Auth service
      await googleAuth.signOut()

      // Clear local state
      await clearCurrentUser()
      isAuthenticated.value = false
      currentUser.value = null
      activeRole.value = null

      // Redirect to signin page
      router.push('/signin')
    } catch (error: unknown) {
      console.error('Sign out error:', error)
      const errorMessage = error instanceof Error ? error.message : 'Sign out failed'
      authError.value = errorMessage
    } finally {
      authLoading.value = false
    }
  }

  /**
   * Check current authentication status
   */
  const checkAuthStatus = async (): Promise<boolean> => {
    if (!isInitialized) {
      await initializeAuth()
      return isAuthenticated.value
    }

    try {
      const authenticated = await googleAuth.isAuthenticated()

      if (authenticated) {
        const authData = googleAuth.getAuthData()
        if (authData) {
          isAuthenticated.value = true
          currentUser.value = authData.profile
          activeRole.value = authData.role
          return true
        }
      }

      // Not authenticated or auth data invalid
      isAuthenticated.value = false
      currentUser.value = null
      activeRole.value = null
      return false
    } catch (error) {
      console.error('Auth status check failed:', error)
      isAuthenticated.value = false
      currentUser.value = null
      activeRole.value = null
      return false
    }
  }

  /**
   * Make authenticated API request
   */
  const makeAuthenticatedRequest = async (
    url: string,
    options?: RequestInit
  ): Promise<Response> => {
    try {
      return await googleAuth.makeAuthenticatedRequest(url, options)
    } catch (error: unknown) {
      // If authentication fails, update state
      const errorMessage = error instanceof Error ? error.message : String(error)
      if (errorMessage.includes('Authentication failed')) {
        isAuthenticated.value = false
        currentUser.value = null
        activeRole.value = null
        await clearCurrentUser()
      }
      throw error
    }
  }

  /**
   * Require authentication for route access
   */
  const requireAuth = (): boolean => {
    if (!isAuthenticated.value) {
      router.push('/signin')
      return false
    }
    return true
  }

  /**
   * Check if user has specific role
   */
  const hasRole = (role: 'student' | 'teacher'): boolean => {
    return activeRole.value === role
  }

  /**
   * Switch user role (for users who are both student and teacher)
   */
  const switchRole = async (newRole: 'student' | 'teacher'): Promise<boolean> => {
    if (!currentUser.value) return false

    // For now, we'll check if the user profile supports multiple roles
    // This might need backend support to determine if user can switch roles
    const authData = googleAuth.getAuthData()
    if (!authData) return false

    // TODO: Implement backend call to check/switch roles if user has multiple roles
    // For now, just check if the current profile supports the requested role
    if (authData.role === newRole || newRole === activeRole.value) {
      activeRole.value = newRole
      return true
    }

    return false
  }

  /**
   * Get current user's authentication token
   */
  const getAuthToken = (): string | null => {
    const authData = googleAuth.getAuthData()
    return authData?.jwt || null
  }

  /**
   * Sign in with development test user (development mode only)
   */
  const signInWithDevUser = async (userType: DevUserType): Promise<void> => {
    if (!devAuth.isAvailable()) {
      throw new Error('Development authentication not available')
    }

    try {
      authLoading.value = true
      authError.value = null

      const result = await devAuth.authenticateWithTestUser(userType)

      if (result.success && result.profile) {
        // Update reactive state
        isAuthenticated.value = true
        currentUser.value = result.profile
        activeRole.value = result.role!

        // Update local database
        await setCurrentUser(result.user_uuid!, {
          name: result.profile.full_name,
          email: result.email!,
          role: result.role!,
          avatar: result.profile.profile_picture,
          phone: '', // Default empty for dev users
          preferredLanguage: 'en', // Default to English
          theme: 'light', // Default theme
        })

        // Initialize role system with user's available roles
        const userRoles = []
        if (userType === 'dual_role') {
          userRoles.push('student', 'teacher')
        } else {
          userRoles.push(result.role!)
        }
        initializeRoles(userRoles)

        // Redirect to appropriate dashboard
        if (result.role === 'teacher') {
          router.push({ name: 'TeacherDashboard' })
        } else {
          router.push({ name: 'Dashboard' })
        }
      } else {
        throw new Error(result.error || 'Development authentication failed')
      }
    } catch (error: unknown) {
      const errorMessage =
        error instanceof Error ? error.message : 'Development authentication failed'
      authError.value = errorMessage
      isAuthenticated.value = false
      currentUser.value = null
      activeRole.value = null
      throw error
    } finally {
      authLoading.value = false
    }
  }

  /**
   * Get available development test users
   */
  const getDevTestUsers = () => {
    return devAuth.getAvailableTestUsers()
  }

  /**
   * Check if development authentication is available
   */
  const isDevAuthAvailable = (): boolean => {
    return devAuth.isAvailable()
  }

  /**
   * Clear any authentication errors
   */
  const clearError = (): void => {
    authError.value = null
  }

  // Initialize on first use
  if (!isInitialized) {
    initializeAuth().catch(console.error)
  }

  return {
    // State (computed for reactivity)
    isAuthenticated: computed(() => isAuthenticated.value),
    currentUser: computed(() => currentUser.value),
    activeRole: computed(() => activeRole.value),
    authLoading: computed(() => authLoading.value),
    authError: computed(() => authError.value),

    // Methods
    signInWithGoogle,
    handleAuthCallback,
    signOut,
    checkAuthStatus,
    requireAuth,
    hasRole,
    switchRole,
    makeAuthenticatedRequest,
    getAuthToken,
    clearError,
    initializeAuth,

    // Development authentication methods
    signInWithDevUser,
    getDevTestUsers,
    isDevAuthAvailable,

    // Legacy methods for compatibility (deprecated)
    signInWithKeycloak: signInWithGoogle, // Alias for backward compatibility
    signInWithFacebookAuth: signInWithGoogle, // Alias for backward compatibility
    refreshToken: checkAuthStatus, // Alias for backward compatibility
  }
}
