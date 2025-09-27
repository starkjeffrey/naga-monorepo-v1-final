/**
 * Environment configuration for mobile app
 */

// API Configuration
export const getApiConfig = () => ({
  baseUrl: process.env.EXPO_PUBLIC_API_BASE_URL || 'http://localhost:8001/api',
})

// Authentication Configuration
export const getAuthConfig = () => ({
  allowedEmailDomain: process.env.EXPO_PUBLIC_ALLOWED_EMAIL_DOMAIN || 'pucsr.edu.kh',
  // Google Sign-In configuration removed - not currently implemented
})

// CDN Configuration
export const getCdnConfig = () => ({
  // CDN URLs can be added here as needed
})