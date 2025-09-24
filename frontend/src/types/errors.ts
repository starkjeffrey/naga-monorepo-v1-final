// Error handling types for the application

export interface ComponentErrorInfo {
  componentName: string
  propsData: Record<string, unknown>
  errorInfo: string
}

export interface ErrorDetails {
  name: string
  message: string
  stack?: string
  component: string
  props: Record<string, unknown>
  retryCount: number
}

export interface VueComponentInstance {
  $options: {
    name?: string
    __name?: string
  }
  $props?: Record<string, unknown>
}

export interface GoogleUserProfile {
  email: string
  name: string
  picture?: string
  given_name?: string
  family_name?: string
  locale?: string
}

export interface GoogleAuthResponse {
  access_token: string
  id_token: string
  scope: string
  token_type: string
  expires_in: number
}

export interface GoogleCredentialResponse {
  credential: string
  select_by: string
}

export interface AuthCallbackData {
  token?: string
  error?: string
  state?: string
}

// Update existing GoogleUserProfile to include id field
export interface GoogleUserProfileComplete extends GoogleUserProfile {
  id: string
}

export interface MediaPipeResults {
  detections: Array<{
    boundingBox: {
      xCenter: number
      yCenter: number
      width: number
      height: number
    }
    landmarks: Array<{
      x: number
      y: number
      z?: number
    }>
    score: number
  }>
}
