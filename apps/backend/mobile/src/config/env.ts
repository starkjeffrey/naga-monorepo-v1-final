/**
 * Environment configuration for mobile app
 */

export interface ApiConfig {
  baseUrl: string
}

export interface AuthConfig {
  allowedEmailDomain: string
  googleClientId: string
  googleAndroidClientId: string
  googleIosClientId: string
  googleWebClientId: string
}

export const getApiConfig = (): ApiConfig => ({
  baseUrl: process.env.EXPO_PUBLIC_API_BASE_URL || 'http://localhost:8001/api'
})

export const getAuthConfig = (): AuthConfig => ({
  allowedEmailDomain: process.env.EXPO_PUBLIC_ALLOWED_EMAIL_DOMAIN || 'pucsr.edu.kh',
  googleClientId: process.env.EXPO_PUBLIC_GOOGLE_CLIENT_ID || '',
  googleAndroidClientId: process.env.EXPO_PUBLIC_GOOGLE_ANDROID_CLIENT_ID || '',
  googleIosClientId: process.env.EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID || '',
  googleWebClientId: process.env.EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID || ''
})