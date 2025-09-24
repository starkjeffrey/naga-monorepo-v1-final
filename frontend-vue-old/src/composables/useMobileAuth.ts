/**
 * Vue 3 Composable for Mobile Authentication
 *
 * Provides reactive authentication state and methods for Vue 3 applications
 */

import { ref, computed, onMounted, watch } from 'vue'
import {
  mobileAuth,
  type StoredAuthData,
  type GoogleAuthCredentials,
  type AuthResponse,
} from '../services/mobileAuth'

// Global reactive state
const isAuthenticated = ref(false)
const authData = ref<StoredAuthData | null>(null)
const isLoading = ref(true)
const error = ref<string | null>(null)

// Initialization flag
let isInitialized = false

/**
 * Initialize authentication state
 */
async function initializeAuth() {
  if (isInitialized) return

  try {
    isLoading.value = true
    error.value = null

    await mobileAuth.initialize()

    const authenticated = await mobileAuth.isAuthenticated()
    isAuthenticated.value = authenticated

    if (authenticated) {
      const data = await mobileAuth.getAuthData()
      authData.value = data
    }

    isInitialized = true
  } catch (err) {
    console.error('Failed to initialize authentication:', err)
    error.value = 'Failed to initialize authentication'
    isAuthenticated.value = false
    authData.value = null
  } finally {
    isLoading.value = false
  }
}

/**
 * Mobile Authentication Composable
 */
export function useMobileAuth() {
  // Initialize on first use
  onMounted(async () => {
    if (!isInitialized) {
      await initializeAuth()
    }
  })

  // Computed properties
  const studentProfile = computed(() => authData.value?.profile || null)
  const studentId = computed(() => authData.value?.studentId || null)
  const userEmail = computed(() => authData.value?.email || null)
  const isTokenExpired = computed(() => {
    if (!authData.value) return true
    return Date.now() >= authData.value.expiresAt * 1000
  })

  /**
   * Login with Google OAuth
   */
  const login = async (
    credentials: GoogleAuthCredentials,
    deviceId: string
  ): Promise<AuthResponse> => {
    try {
      isLoading.value = true
      error.value = null

      const result = await mobileAuth.authenticateWithGoogle(credentials, deviceId)

      if (result.success) {
        isAuthenticated.value = true
        const data = await mobileAuth.getAuthData()
        authData.value = data
      } else {
        error.value = result.error || 'Authentication failed'
      }

      return result
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Login failed'
      error.value = errorMessage
      return {
        success: false,
        error: errorMessage,
        error_code: 'LOGIN_ERROR',
      }
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Logout and clear authentication
   */
  const logout = async (): Promise<void> => {
    try {
      isLoading.value = true
      error.value = null

      await mobileAuth.logout()

      isAuthenticated.value = false
      authData.value = null
    } catch (err) {
      console.error('Logout failed:', err)
      error.value = err instanceof Error ? err.message : 'Logout failed'
    } finally {
      isLoading.value = false
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
      return await mobileAuth.makeAuthenticatedRequest(url, options)
    } catch (err) {
      // If authentication fails, update state
      if (err instanceof Error && err.message.includes('Authentication failed')) {
        isAuthenticated.value = false
        authData.value = null
      }
      throw err
    }
  }

  /**
   * Refresh authentication status
   */
  const refreshAuth = async (): Promise<void> => {
    try {
      isLoading.value = true
      error.value = null

      const authenticated = await mobileAuth.isAuthenticated()
      isAuthenticated.value = authenticated

      if (authenticated) {
        const data = await mobileAuth.getAuthData()
        authData.value = data
      } else {
        authData.value = null
      }
    } catch (err) {
      console.error('Failed to refresh auth:', err)
      error.value = 'Failed to refresh authentication'
      isAuthenticated.value = false
      authData.value = null
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Check if user has specific role
   */
  const hasRole = (role: string): boolean => {
    if (!authData.value) return false

    try {
      const payload = JSON.parse(atob(authData.value.jwt.split('.')[1]))
      return payload.roles?.includes(role) || false
    } catch {
      return false
    }
  }

  /**
   * Check if user has specific permission
   */
  const hasPermission = (permission: string): boolean => {
    if (!authData.value) return false

    try {
      const payload = JSON.parse(atob(authData.value.jwt.split('.')[1]))
      return payload.permissions?.includes(permission) || false
    } catch {
      return false
    }
  }

  /**
   * Get time until token expires (in seconds)
   */
  const getTimeUntilExpiry = (): number => {
    if (!authData.value) return 0

    const expiryTime = authData.value.expiresAt * 1000
    const currentTime = Date.now()

    return Math.max(0, Math.floor((expiryTime - currentTime) / 1000))
  }

  /**
   * Auto-refresh token when it's about to expire
   */
  const startAutoRefresh = () => {
    const checkInterval = setInterval(async () => {
      const timeUntilExpiry = getTimeUntilExpiry()

      // Refresh if token expires in less than 5 minutes
      if (timeUntilExpiry > 0 && timeUntilExpiry < 300) {
        try {
          await refreshAuth()
        } catch (error) {
          console.error('Auto-refresh failed:', error)
          clearInterval(checkInterval)
        }
      }

      // Clear interval if not authenticated
      if (!isAuthenticated.value) {
        clearInterval(checkInterval)
      }
    }, 60000) // Check every minute

    return checkInterval
  }

  // Watch for authentication state changes
  watch(isAuthenticated, newValue => {
    if (newValue) {
      startAutoRefresh()
    }
  })

  return {
    // State
    isAuthenticated: computed(() => isAuthenticated.value),
    authData: computed(() => authData.value),
    isLoading: computed(() => isLoading.value),
    error: computed(() => error.value),

    // Computed properties
    studentProfile,
    studentId,
    userEmail,
    isTokenExpired,

    // Methods
    login,
    logout,
    makeAuthenticatedRequest,
    refreshAuth,
    hasRole,
    hasPermission,
    getTimeUntilExpiry,

    // Utilities
    clearError: () => {
      error.value = null
    },
    initialize: initializeAuth,
  }
}

/**
 * Authentication Guard for Vue Router
 */
export function createAuthGuard() {
  return async (to: any, from: any, next: any) => {
    const { isAuthenticated, isLoading, initialize } = useMobileAuth()

    // Initialize if not already done
    if (!isInitialized) {
      await initialize()
    }

    // Wait for loading to complete
    if (isLoading.value) {
      // Wait for auth state to be determined
      await new Promise(resolve => {
        const unwatch = watch(isLoading, loading => {
          if (!loading) {
            unwatch()
            resolve(void 0)
          }
        })
      })
    }

    // Check if route requires authentication
    if (to.meta?.requiresAuth !== false && !isAuthenticated.value) {
      // Redirect to login page
      next({ name: 'login', query: { redirect: to.fullPath } })
      return
    }

    // Check role requirements
    if (to.meta?.roles && Array.isArray(to.meta.roles)) {
      const { hasRole } = useMobileAuth()
      const hasRequiredRole = to.meta.roles.some((role: string) => hasRole(role))

      if (!hasRequiredRole) {
        next({ name: 'forbidden' })
        return
      }
    }

    // Check permission requirements
    if (to.meta?.permissions && Array.isArray(to.meta.permissions)) {
      const { hasPermission } = useMobileAuth()
      const hasRequiredPermission = to.meta.permissions.some((permission: string) =>
        hasPermission(permission)
      )

      if (!hasRequiredPermission) {
        next({ name: 'forbidden' })
        return
      }
    }

    next()
  }
}

/**
 * Plugin for Vue app
 */
export default {
  install(app: any) {
    // Make auth service available globally
    app.config.globalProperties.$mobileAuth = mobileAuth

    // Provide composable
    app.provide('mobileAuth', useMobileAuth)

    // Initialize auth on app mount
    app.mixin({
      async created() {
        if (!isInitialized) {
          await initializeAuth()
        }
      },
    })
  },
}
