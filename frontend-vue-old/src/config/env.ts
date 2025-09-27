/**
 * Environment configuration for Vue frontend
 */

// Development check
export const isDevelopment = process.env.NODE_ENV === 'development';

// API Configuration
export const getApiConfig = () => ({
  baseUrl: process.env.VUE_APP_API_BASE_URL || 'http://localhost:8001/api',
});

// Authentication Configuration
export const getAuthConfig = () => ({
  allowedEmailDomain: process.env.VUE_APP_ALLOWED_EMAIL_DOMAIN || 'pucsr.edu.kh',
});

// CDN Configuration
export const getCdnConfig = () => ({
  // CDN URLs can be added here as needed
});