import { useAuth } from './useAuth'
import { useMobileAuth } from './useMobileAuth'

// Input validation types
export interface ApiRequestOptions {
  endpoint: string
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'
  body?: Record<string, unknown> | FormData | null
  timeout?: number
  retries?: number
}

export interface ApiError extends Error {
  status?: number
  code?: string
  details?: Record<string, unknown>
}

// Environment configuration with validation
function getApiBaseUrl(): string {
  const url = import.meta.env.VITE_API_BASE_URL

  if (!url) {
    console.warn('VITE_API_BASE_URL not set, using localhost fallback')
    return 'http://localhost:8000/api'
  }

  // Validate URL format
  try {
    const parsedUrl = new URL(url)
    if (!['http:', 'https:'].includes(parsedUrl.protocol)) {
      throw new Error('Invalid protocol')
    }
    return url.endsWith('/api') ? url : `${url}/api`
  } catch {
    console.error('Invalid VITE_API_BASE_URL format, using localhost fallback')
    return 'http://localhost:8000/api'
  }
}

const API_BASE_URL = getApiBaseUrl()

// Input validation utilities
function validateEndpoint(endpoint: string): string {
  if (!endpoint || typeof endpoint !== 'string') {
    throw new Error('Endpoint must be a non-empty string')
  }

  // Remove leading slash and validate format
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint

  // Basic path traversal protection
  if (cleanEndpoint.includes('..') || cleanEndpoint.includes('//')) {
    throw new Error('Invalid endpoint format')
  }

  // Ensure it starts with /
  return `/${cleanEndpoint}`
}

function validateRequestBody(body: unknown): void {
  if (body === null || body === undefined) {
    return
  }

  if (body instanceof FormData) {
    return // FormData is valid
  }

  if (typeof body === 'object') {
    try {
      JSON.stringify(body)
    } catch {
      throw new Error('Request body must be JSON serializable')
    }
  } else {
    throw new Error('Request body must be an object, FormData, or null')
  }
}

function createApiError(message: string, status?: number, originalError?: Error): ApiError {
  const error = new Error(message) as ApiError
  error.status = status
  error.details = { originalError: originalError?.message }
  return error
}

// Helper function to get CSRF token from cookies with validation
function getCookie(name: string): string | null {
  if (!name || typeof name !== 'string') {
    return null
  }

  let cookieValue: string | null = null
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';')
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim()
      if (cookie.substring(0, name.length + 1) === `${name}=`) {
        try {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1))
        } catch {
          console.warn(`Failed to decode cookie: ${name}`)
          return null
        }
        break
      }
    }
  }
  return cookieValue
}

export function useApi() {
  const { refreshToken } = useAuth()
  const { makeAuthenticatedRequest } = useMobileAuth()

  // Enhanced API request with validation and retry logic
  const makeApiRequest = async <T = unknown>(
    options: ApiRequestOptions | string,
    legacyMethod?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH',
    legacyBody?: Record<string, unknown> | null
  ): Promise<T> => {
    // Support both new object-based and legacy parameter-based usage
    const config: ApiRequestOptions =
      typeof options === 'string'
        ? {
            endpoint: options,
            method: legacyMethod || 'GET',
            body: legacyBody,
            timeout: 10000,
            retries: 3,
          }
        : {
            timeout: 10000,
            retries: 3,
            ...options,
          }

    // Input validation
    const validatedEndpoint = validateEndpoint(config.endpoint)
    validateRequestBody(config.body)

    const makeRequestWithRetry = async (attempt: number = 1): Promise<T> => {
      try {
        // Try mobile auth first (secure)
        try {
          const response = await makeAuthenticatedRequest(`${API_BASE_URL}${validatedEndpoint}`, {
            method: config.method || 'GET',
            body:
              config.body instanceof FormData
                ? config.body
                : config.body
                ? JSON.stringify(config.body)
                : undefined,
            headers:
              config.body instanceof FormData
                ? undefined // Let browser set Content-Type for FormData
                : { 'Content-Type': 'application/json' },
          })

          if (!response.ok) {
            const errorData = await response
              .json()
              .catch(() => ({ message: 'An unknown error occurred' }))
            throw createApiError(errorData.message || 'API request failed', response.status)
          }

          return await response.json()
        } catch (mobileAuthError) {
          // Fallback to legacy auth
          console.warn('Mobile auth failed, falling back to legacy auth:', mobileAuthError)
          return await makeLegacyRequest()
        }
      } catch (error) {
        const apiError = error as ApiError

        // Retry logic for retryable errors
        if (attempt < (config.retries || 3) && shouldRetry(apiError)) {
          console.warn(`API request failed (attempt ${attempt}), retrying...`, error)
          await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt) * 1000))
          return makeRequestWithRetry(attempt + 1)
        }

        throw error
      }
    }

    const makeLegacyRequest = async (): Promise<T> => {
      const accessToken = localStorage.getItem('access_token')

      const headers: Record<string, string> = {}

      if (!(config.body instanceof FormData)) {
        headers['Content-Type'] = 'application/json'
      }

      if (accessToken) {
        headers.Authorization = `Bearer ${accessToken}`
      }

      // Add CSRF token for methods that require it
      const method = config.method || 'GET'
      if (!['GET', 'HEAD', 'OPTIONS', 'TRACE'].includes(method.toUpperCase())) {
        const csrfToken = getCookie('csrftoken')
        if (csrfToken) {
          headers['X-CSRFToken'] = csrfToken
        }
      }

      const requestConfig: RequestInit = {
        method,
        headers,
        signal: AbortSignal.timeout(config.timeout || 10000),
      }

      if (config.body) {
        requestConfig.body =
          config.body instanceof FormData ? config.body : JSON.stringify(config.body)
      }

      const response = await fetch(`${API_BASE_URL}${validatedEndpoint}`, requestConfig)

      if (response.status === 401) {
        // Token expired, try to refresh
        try {
          const newAccessToken = await refreshToken()
          headers.Authorization = `Bearer ${newAccessToken}`
          const retryResponse = await fetch(`${API_BASE_URL}${validatedEndpoint}`, {
            ...requestConfig,
            headers,
          })

          if (!retryResponse.ok) {
            const errorData = await retryResponse
              .json()
              .catch(() => ({ message: 'An unknown error occurred' }))
            throw createApiError(errorData.message || 'API request failed', retryResponse.status)
          }

          return await retryResponse.json()
        } catch (refreshError) {
          if (import.meta.env.DEV) {
            console.error('Failed to refresh token:', refreshError)
          }
          throw createApiError('Session expired', 401, refreshError as Error)
        }
      }

      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => ({ message: 'An unknown error occurred' }))
        throw createApiError(errorData.message || 'API request failed', response.status)
      }

      return await response.json()
    }

    return makeRequestWithRetry()
  }

  return { makeApiRequest }
}

// Helper to determine if an error is retryable
function shouldRetry(error: ApiError): boolean {
  if (!error.status) return true // Network errors are retryable

  // Retry on server errors but not client errors
  return error.status >= 500 || error.status === 408 || error.status === 429
}
