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
  googleClientId: process.env.EXPO_PUBLIC_GOOGLE_CLIENT_ID,
  googleAndroidClientId: process.env.EXPO_PUBLIC_GOOGLE_ANDROID_CLIENT_ID,
  googleIosClientId: process.env.EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID,
})

// CDN Configuration
export const getCdnConfig = () => ({
  googleApisBaseUrl: 'https://www.googleapis.com/oauth2/v2',
})