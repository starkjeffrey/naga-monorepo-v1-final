/**
 * Environment Configuration
 * Centralized environment variable handling with validation and defaults
 */

// Environment variable validation and parsing
export interface AppConfig {
  // API Configuration
  api: {
    baseUrl: string
    timeout: number
    retries: number
  }

  // Authentication Configuration
  auth: {
    googleClientId: string
    allowedEmailDomain: string
    redirectUri: string
  }

  // CDN Configuration
  cdn: {
    mediaPipeBaseUrl: string
    googleApisBaseUrl: string
    defaultAvatarUrl: string
  }

  // App Configuration
  app: {
    name: string
    shortName: string
    description: string
    version: string
    environment: 'development' | 'staging' | 'production'
  }

  // Feature Flags
  features: {
    devTools: boolean
    bundleAnalysis: boolean
    errorReporting: boolean
  }
}

// Default configuration
const DEFAULT_CONFIG: AppConfig = {
  api: {
    baseUrl: 'http://localhost:8000/api',
    timeout: 10000,
    retries: 3,
  },

  auth: {
    googleClientId: 'your-google-client-id.apps.googleusercontent.com',
    allowedEmailDomain: 'pucsr.edu.kh',
    redirectUri: 'http://localhost:5173/auth/callback',
  },

  cdn: {
    mediaPipeBaseUrl: 'https://cdn.jsdelivr.net/npm/@mediapipe/face_detection',
    googleApisBaseUrl: 'https://www.googleapis.com',
    defaultAvatarUrl: 'https://cdn.quasar.dev/img/boy-avatar.png',
  },

  app: {
    name: 'Naga SIS - PUCSR',
    shortName: 'PUCSR',
    description: 'Student Information System for PUCSR',
    version: '1.0.0',
    environment: 'development',
  },

  features: {
    devTools: true,
    bundleAnalysis: false,
    errorReporting: false,
  },
}

// Environment variable getters with validation
function getEnvString(key: string, defaultValue: string): string {
  const value = import.meta.env[key]
  if (value === undefined || value === '') {
    console.warn(`Environment variable ${key} not set, using default: ${defaultValue}`)
    return defaultValue
  }
  return value
}

function getEnvNumber(key: string, defaultValue: number): number {
  const value = import.meta.env[key]
  if (value === undefined || value === '') {
    return defaultValue
  }

  const parsed = parseInt(value, 10)
  if (isNaN(parsed)) {
    console.warn(
      `Environment variable ${key} is not a valid number, using default: ${defaultValue}`
    )
    return defaultValue
  }

  return parsed
}

function getEnvBoolean(key: string, defaultValue: boolean): boolean {
  const value = import.meta.env[key]
  if (value === undefined || value === '') {
    return defaultValue
  }

  return value.toLowerCase() === 'true' || value === '1'
}

function validateUrl(url: string, name: string): string {
  try {
    const parsedUrl = new URL(url)
    if (!['http:', 'https:'].includes(parsedUrl.protocol)) {
      throw new Error('Invalid protocol')
    }
    return url
  } catch (error) {
    console.error(`Invalid ${name} URL format: ${url}`, error)
    throw new Error(`Invalid ${name} URL configuration`)
  }
}

// Create validated configuration
function createAppConfig(): AppConfig {
  const isDevelopment = import.meta.env.DEV
  const isProduction = import.meta.env.PROD
  const mode = import.meta.env.MODE as 'development' | 'staging' | 'production'

  // Get base API URL with validation
  let apiBaseUrl = getEnvString('VITE_API_BASE_URL', DEFAULT_CONFIG.api.baseUrl)
  if (apiBaseUrl !== DEFAULT_CONFIG.api.baseUrl) {
    apiBaseUrl = validateUrl(apiBaseUrl, 'API base')
    // Ensure it ends with /api
    if (!apiBaseUrl.endsWith('/api')) {
      apiBaseUrl = `${apiBaseUrl.replace(/\/$/, '')}/api`
    }
  }

  // Get Google OAuth configuration
  const googleClientId = getEnvString('VITE_GOOGLE_CLIENT_ID', DEFAULT_CONFIG.auth.googleClientId)
  const redirectUri = getEnvString('VITE_GOOGLE_REDIRECT_URI', DEFAULT_CONFIG.auth.redirectUri)

  return {
    api: {
      baseUrl: apiBaseUrl,
      timeout: getEnvNumber('VITE_API_TIMEOUT', DEFAULT_CONFIG.api.timeout),
      retries: getEnvNumber('VITE_API_RETRIES', DEFAULT_CONFIG.api.retries),
    },

    auth: {
      googleClientId,
      allowedEmailDomain: getEnvString(
        'VITE_ALLOWED_EMAIL_DOMAIN',
        DEFAULT_CONFIG.auth.allowedEmailDomain
      ),
      redirectUri,
    },

    cdn: {
      mediaPipeBaseUrl: getEnvString('VITE_MEDIAPIPE_CDN_URL', DEFAULT_CONFIG.cdn.mediaPipeBaseUrl),
      googleApisBaseUrl: getEnvString('VITE_GOOGLE_APIS_URL', DEFAULT_CONFIG.cdn.googleApisBaseUrl),
      defaultAvatarUrl: getEnvString(
        'VITE_DEFAULT_AVATAR_URL',
        DEFAULT_CONFIG.cdn.defaultAvatarUrl
      ),
    },

    app: {
      name: getEnvString('VITE_APP_NAME', DEFAULT_CONFIG.app.name),
      shortName: getEnvString('VITE_APP_SHORT_NAME', DEFAULT_CONFIG.app.shortName),
      description: getEnvString('VITE_APP_DESCRIPTION', DEFAULT_CONFIG.app.description),
      version: getEnvString('VITE_APP_VERSION', DEFAULT_CONFIG.app.version),
      environment: mode,
    },

    features: {
      devTools: getEnvBoolean('VITE_ENABLE_DEV_TOOLS', isDevelopment),
      bundleAnalysis: getEnvBoolean('VITE_ENABLE_BUNDLE_ANALYSIS', false),
      errorReporting: getEnvBoolean('VITE_ENABLE_ERROR_REPORTING', isProduction),
    },
  }
}

// Export the singleton configuration
export const config: AppConfig = createAppConfig()

// Configuration validation on app start
export function validateConfiguration(): boolean {
  const errors: string[] = []

  // Validate required URLs
  try {
    validateUrl(config.api.baseUrl, 'API base')
  } catch (error) {
    errors.push(`API base URL validation failed: ${(error as Error).message}`)
  }

  // Validate Google Client ID format
  if (
    !config.auth.googleClientId ||
    !config.auth.googleClientId.includes('.apps.googleusercontent.com')
  ) {
    errors.push('Google Client ID must be a valid Google OAuth client ID')
  }

  // Validate numeric ranges
  if (config.api.timeout < 1000 || config.api.timeout > 60000) {
    errors.push('API timeout must be between 1000ms and 60000ms')
  }

  if (config.api.retries < 1 || config.api.retries > 10) {
    errors.push('API retries must be between 1 and 10')
  }

  // Validate email domain
  if (!config.auth.allowedEmailDomain || config.auth.allowedEmailDomain.length < 3) {
    errors.push('Allowed email domain must be a valid domain')
  }

  if (errors.length > 0) {
    console.error('Configuration validation failed:')
    errors.forEach(error => console.error(`  - ${error}`))
    return false
  }

  console.log('Configuration validation passed')
  return true
}

// Helper functions for common configuration access
export const getApiConfig = () => config.api
export const getAuthConfig = () => config.auth
export const getCdnConfig = () => config.cdn
export const getAppConfig = () => config.app
export const getFeatureFlags = () => config.features

// Environment helpers
export const isDevelopment = () => config.app.environment === 'development'
export const isStaging = () => config.app.environment === 'staging'
export const isProduction = () => config.app.environment === 'production'

// Default export for convenience
export default config
