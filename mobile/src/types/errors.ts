/**
 * Type definitions for authentication and error handling
 */

export interface GoogleUserProfile {
  id: string
  email: string
  verified_email: boolean
  name: string
  given_name: string
  family_name: string
  picture: string
  locale: string
}

export interface GoogleAuthResponse {
  success: boolean
  jwt_token?: string
  student_id?: number
  email?: string
  person_uuid?: string
  expires_at?: number
  expires_in?: number
  profile?: StudentProfile
  error?: string
  error_code?: string
}

export interface StudentProfile {
  student_id: number
  person_uuid: string
  full_name: string
  family_name: string
  personal_name: string
  school_email: string
  phone?: string
  current_status: string
  enrollment_date?: string
  graduation_date?: string
}