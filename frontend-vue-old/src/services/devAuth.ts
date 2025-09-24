/**
 * Development Authentication Service
 *
 * DEVELOPMENT ONLY - provides fake authentication for testing
 * Should never be available in production builds
 */

import type { AuthResponse, UserProfile } from './googleAuth'

// Test user profiles for development
export const DEV_TEST_USERS = {
  student: {
    email: 'john.doe@pucsr.edu.kh',
    full_name: 'John Doe',
    given_name: 'John',
    family_name: 'Doe',
    role: 'student' as const,
    user_uuid: 'dev-student-001',
    student_id: 12345,
    enrollment_date: '2023-09-01',
    status: 'active',
    profile_picture: 'https://cdn.quasar.dev/img/boy-avatar.png',
  },
  teacher: {
    email: 'jane.smith@pucsr.edu.kh',
    full_name: 'Prof. Jane Smith',
    given_name: 'Jane',
    family_name: 'Smith',
    role: 'teacher' as const,
    user_uuid: 'dev-teacher-001',
    teacher_id: 54321,
    department: 'Computer Science',
    hire_date: '2020-08-15',
    status: 'active',
    profile_picture: 'https://cdn.quasar.dev/img/avatar.png',
  },
  dual_role: {
    email: 'alex.chen@pucsr.edu.kh',
    full_name: 'Alex Chen',
    given_name: 'Alex',
    family_name: 'Chen',
    role: 'teacher' as const, // Default role
    user_uuid: 'dev-dual-001',
    student_id: 67890,
    teacher_id: 98765,
    enrollment_date: '2022-01-15',
    department: 'Mathematics',
    hire_date: '2023-02-01',
    status: 'active',
    profile_picture: 'https://cdn.quasar.dev/img/avatar2.png',
  },
} as const

export type DevUserType = keyof typeof DEV_TEST_USERS

/**
 * Development Authentication Service
 * Only available in development mode
 */
export class DevAuthService {
  private static instance: DevAuthService

  private constructor() {}

  static getInstance(): DevAuthService {
    if (!DevAuthService.instance) {
      DevAuthService.instance = new DevAuthService()
    }
    return DevAuthService.instance
  }

  /**
   * Check if development authentication is available
   */
  isAvailable(): boolean {
    return import.meta.env.DEV === true
  }

  /**
   * Authenticate with a test user
   */
  async authenticateWithTestUser(userType: DevUserType): Promise<AuthResponse> {
    if (!this.isAvailable()) {
      return {
        success: false,
        error: 'Development authentication not available in production',
        error_code: 'DEV_AUTH_DISABLED',
      }
    }

    const testUser = DEV_TEST_USERS[userType]

    // Simulate network delay
    await new Promise(resolve => setTimeout(resolve, 500))

    const profile: UserProfile = {
      user_uuid: testUser.user_uuid,
      email: testUser.email,
      full_name: testUser.full_name,
      given_name: testUser.given_name,
      family_name: testUser.family_name,
      role: testUser.role,
      status: testUser.status,
      profile_picture: testUser.profile_picture,
      ...(testUser.student_id && {
        student_id: testUser.student_id,
        enrollment_date: testUser.enrollment_date,
      }),
      ...(testUser.teacher_id && {
        teacher_id: testUser.teacher_id,
        department: testUser.department,
        hire_date: testUser.hire_date,
      }),
    }

    // Create fake JWT token (base64 encoded JSON for dev visibility)
    const tokenPayload = {
      sub: testUser.user_uuid,
      email: testUser.email,
      role: testUser.role,
      exp: Math.floor(Date.now() / 1000) + 24 * 60 * 60, // 24 hours
      iat: Math.floor(Date.now() / 1000),
      iss: 'dev-auth-service',
    }

    const fakeJwt = `dev.${btoa(JSON.stringify(tokenPayload))}.signature`

    return {
      success: true,
      jwt_token: fakeJwt,
      user_uuid: testUser.user_uuid,
      email: testUser.email,
      role: testUser.role,
      expires_at: tokenPayload.exp,
      expires_in: 24 * 60 * 60,
      profile,
      ...(testUser.student_id && { student_id: testUser.student_id }),
      ...(testUser.teacher_id && { teacher_id: testUser.teacher_id }),
    }
  }

  /**
   * Get list of available test users
   */
  getAvailableTestUsers(): Array<{
    type: DevUserType
    name: string
    email: string
    role: string
    description: string
  }> {
    if (!this.isAvailable()) {
      return []
    }

    return [
      {
        type: 'student',
        name: DEV_TEST_USERS.student.full_name,
        email: DEV_TEST_USERS.student.email,
        role: DEV_TEST_USERS.student.role,
        description: 'Regular student account',
      },
      {
        type: 'teacher',
        name: DEV_TEST_USERS.teacher.full_name,
        email: DEV_TEST_USERS.teacher.email,
        role: DEV_TEST_USERS.teacher.role,
        description: 'Teacher account',
      },
      {
        type: 'dual_role',
        name: DEV_TEST_USERS.dual_role.full_name,
        email: DEV_TEST_USERS.dual_role.email,
        role: 'student + teacher',
        description: 'Dual role account (student + teacher)',
      },
    ]
  }

  /**
   * Validate development JWT token
   */
  validateDevToken(token: string): boolean {
    if (!this.isAvailable() || !token.startsWith('dev.')) {
      return false
    }

    try {
      const parts = token.split('.')
      if (parts.length !== 3) return false

      const payload = JSON.parse(atob(parts[1]))
      const now = Math.floor(Date.now() / 1000)

      return payload.exp > now && payload.iss === 'dev-auth-service'
    } catch {
      return false
    }
  }

  /**
   * Get user data from development JWT token
   */
  getDevTokenData(token: string): { user_uuid: string; email: string; role: string } | null {
    if (!this.validateDevToken(token)) {
      return null
    }

    try {
      const payload = JSON.parse(atob(token.split('.')[1]))
      return {
        user_uuid: payload.sub,
        email: payload.email,
        role: payload.role,
      }
    } catch {
      return null
    }
  }
}

// Export singleton instance
export const devAuth = DevAuthService.getInstance()
