import { ref, computed } from 'vue'
import { db } from '@/db/database'

// Error types for better error handling
export enum DatabaseErrorType {
  CONNECTION_ERROR = 'CONNECTION_ERROR',
  PERMISSION_DENIED = 'PERMISSION_DENIED',
  QUOTA_EXCEEDED = 'QUOTA_EXCEEDED',
  TRANSACTION_ERROR = 'TRANSACTION_ERROR',
  DATA_CORRUPTION = 'DATA_CORRUPTION',
  UNKNOWN_ERROR = 'UNKNOWN_ERROR',
}

export interface DatabaseError extends Error {
  type: DatabaseErrorType
  originalError: Error
  retryable: boolean
}

// Enhanced error handling utility
export function createDatabaseError(
  message: string,
  originalError: Error,
  type: DatabaseErrorType = DatabaseErrorType.UNKNOWN_ERROR
): DatabaseError {
  const error = new Error(message) as DatabaseError
  error.type = type
  error.originalError = originalError
  error.retryable = [
    DatabaseErrorType.CONNECTION_ERROR,
    DatabaseErrorType.TRANSACTION_ERROR,
  ].includes(type)

  return error
}

// Retry mechanism for database operations
async function withRetry<T>(
  operation: () => Promise<T>,
  maxRetries: number = 3,
  delay: number = 1000
): Promise<T> {
  let lastError: Error

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await operation()
    } catch (error) {
      lastError = error as Error
      console.warn(`Database operation failed (attempt ${attempt}/${maxRetries}):`, error)

      const dbError = error as DatabaseError
      if (!dbError.retryable || attempt === maxRetries) {
        throw error
      }

      // Exponential backoff
      await new Promise(resolve => setTimeout(resolve, delay * Math.pow(2, attempt - 1)))
    }
  }

  throw lastError!
}

// Database health checker
async function checkDatabaseHealth(): Promise<boolean> {
  try {
    await db.appSettings.limit(1).toArray()
    return true
  } catch (error) {
    console.error('Database health check failed:', error)
    return false
  }
}

interface User {
  userId: string
  role: string
  name?: string
  email?: string
  avatar?: string
  lastSync?: Date
}

interface ScheduleData {
  semester?: string
  year?: string
  courseId?: string
  courseName?: string
  userId?: string
}

interface AnnouncementData {
  id: string
  title: string
  content: string
  targetAudience: string
  createdAt: Date
}

interface AttendanceData {
  studentId: string
  courseId: string
  date: Date
  status: 'present' | 'absent' | 'late'
  location?: string
  createdAt?: Date
  syncStatus?: 'pending' | 'synced' | 'failed'
}

interface LeaveRequestData {
  teacherId?: string
  reason: string
  startDate: Date
  endDate: Date
  requestedAt?: Date
  status?: 'pending' | 'approved' | 'rejected'
  syncStatus?: 'pending' | 'synced' | 'failed'
}

interface FinancialData {
  studentId?: string
  year: number
  semester: string
  totalFees: number
  paidAmount: number
  balance: number
  lastSync?: Date
}

export function useDatabase() {
  const isReady = ref(false)
  const error = ref<DatabaseError | null>(null)
  const currentUser = ref<User | null>(null)
  const isHealthy = ref(true)

  const initializeDatabase = async (): Promise<void> => {
    try {
      await withRetry(async () => {
        await db.open()

        // Verify database health after opening
        const healthy = await checkDatabaseHealth()
        if (!healthy) {
          throw new Error('Database health check failed after initialization')
        }

        isHealthy.value = true
        isReady.value = true
      })

      // Load current user if exists
      try {
        const user = await db.getCurrentUser()
        if (user) {
          currentUser.value = user
        }
      } catch (userError) {
        console.warn('Failed to load current user during initialization:', userError)
        // Continue with initialization even if user loading fails
      }

      console.log('Database initialized successfully')
    } catch (err) {
      const originalError = err as Error
      let dbError: DatabaseError

      if (originalError.name === 'QuotaExceededError') {
        dbError = createDatabaseError(
          'Database storage quota exceeded. Please free up space.',
          originalError,
          DatabaseErrorType.QUOTA_EXCEEDED
        )
      } else if (originalError.name === 'NotFoundError' || originalError.name === 'UnknownError') {
        dbError = createDatabaseError(
          'Database connection failed. Please check your browser settings.',
          originalError,
          DatabaseErrorType.CONNECTION_ERROR
        )
      } else {
        dbError = createDatabaseError(
          'Failed to initialize database',
          originalError,
          DatabaseErrorType.UNKNOWN_ERROR
        )
      }

      console.error('Database initialization failed:', dbError)
      error.value = dbError
      isHealthy.value = false
      isReady.value = false
    }
  }

  const setCurrentUser = async (
    userId: string,
    userData: Partial<User> | null = null
  ): Promise<void> => {
    try {
      // Input validation
      if (!userId || typeof userId !== 'string') {
        throw new Error('Invalid userId provided')
      }

      await withRetry(async () => {
        await db.setCurrentUser(userId)

        if (userData) {
          // Validate userData structure
          if (typeof userData !== 'object') {
            throw new Error('Invalid userData provided')
          }

          await db.userProfiles.put({
            userId,
            ...userData,
            lastSync: new Date(),
          })
        }

        // Verify the user was set correctly
        if (userData) {
          // If userData was provided, try to load the created profile
          const verifyUser = await db.getCurrentUser()
          if (verifyUser && verifyUser.userId === userId) {
            currentUser.value = verifyUser
          } else {
            // Fallback: try to load profile directly
            const profile = await db.userProfiles.where('userId').equals(userId).first()
            currentUser.value = profile || null
            console.warn('User profile verification had issues, but profile exists:', !!profile)
          }
        } else {
          // If no userData, just verify the current user ID was set
          const settings = await db.appSettings.where('key').equals('currentUserId').first()
          if (!settings || settings.value !== userId) {
            throw new Error('Failed to verify current user ID was set correctly')
          }
          // Try to load existing profile if available
          const existingProfile = await db.userProfiles.where('userId').equals(userId).first()
          currentUser.value = existingProfile || null
        }
      })
    } catch (err) {
      const originalError = err as Error
      const dbError = createDatabaseError(
        `Failed to set current user: ${originalError.message}`,
        originalError,
        originalError.name.includes('Transaction')
          ? DatabaseErrorType.TRANSACTION_ERROR
          : DatabaseErrorType.UNKNOWN_ERROR
      )

      console.error('Failed to set current user:', dbError)
      error.value = dbError
      throw dbError
    }
  }

  const clearCurrentUser = async (): Promise<void> => {
    try {
      await withRetry(async () => {
        if (currentUser.value) {
          await db.clearUserData(currentUser.value.userId)
        }
        await db.appSettings.where('key').equals('currentUserId').delete()

        // Verify clearing was successful
        const verifyUser = await db.getCurrentUser()
        if (verifyUser) {
          throw new Error('Failed to verify user was cleared')
        }

        currentUser.value = null
      })
    } catch (err) {
      const originalError = err as Error
      const dbError = createDatabaseError(
        `Failed to clear current user: ${originalError.message}`,
        originalError,
        originalError.name.includes('Transaction')
          ? DatabaseErrorType.TRANSACTION_ERROR
          : DatabaseErrorType.UNKNOWN_ERROR
      )

      console.error('Failed to clear current user:', dbError)
      error.value = dbError
      throw dbError
    }
  }

  const isStudent = computed(() => {
    return currentUser.value?.role === 'student' || currentUser.value?.role === 'both'
  })

  const isTeacher = computed(() => {
    return currentUser.value?.role === 'teacher' || currentUser.value?.role === 'both'
  })

  const hasRole = (role: string): boolean => {
    if (!currentUser.value) return false
    return currentUser.value.role === role || currentUser.value.role === 'both'
  }

  return {
    db,
    isReady,
    isHealthy,
    error,
    currentUser,
    isStudent,
    isTeacher,
    initializeDatabase,
    setCurrentUser,
    clearCurrentUser,
    hasRole,
  }
}

export function useUserProfile() {
  const { db, currentUser } = useDatabase()

  const updateProfile = async (updates: Partial<User>): Promise<void> => {
    try {
      if (!currentUser.value) {
        throw new Error('No current user')
      }

      // Input validation
      if (!updates || typeof updates !== 'object') {
        throw new Error('Invalid profile updates provided')
      }

      // Sanitize updates to prevent invalid data
      const sanitizedUpdates = { ...updates }
      delete sanitizedUpdates.userId // Prevent userId modification

      await withRetry(async () => {
        const updateCount = await db.userProfiles
          .where('userId')
          .equals(currentUser.value!.userId)
          .modify(sanitizedUpdates)

        if (updateCount === 0) {
          throw new Error('No profile found to update')
        }

        // Verify the update was successful
        const updatedUser = await db.getCurrentUser()
        if (!updatedUser) {
          throw new Error('Failed to verify profile update')
        }

        currentUser.value = updatedUser
      })
    } catch (err) {
      const originalError = err as Error
      const dbError = createDatabaseError(
        `Failed to update profile: ${originalError.message}`,
        originalError,
        originalError.name.includes('Transaction')
          ? DatabaseErrorType.TRANSACTION_ERROR
          : DatabaseErrorType.UNKNOWN_ERROR
      )

      console.error('Failed to update profile:', dbError)
      throw dbError
    }
  }

  const getProfile = async (userId: string | null = null): Promise<User | undefined> => {
    try {
      const targetUserId = userId || currentUser.value?.userId
      if (!targetUserId || typeof targetUserId !== 'string') {
        throw new Error('Invalid user ID provided')
      }

      return await withRetry(async () => {
        const profile = await db.userProfiles.where('userId').equals(targetUserId).first()
        return profile
      })
    } catch (err) {
      const originalError = err as Error
      const dbError = createDatabaseError(
        `Failed to get profile: ${originalError.message}`,
        originalError,
        DatabaseErrorType.UNKNOWN_ERROR
      )

      console.error('Failed to get profile:', dbError)
      throw dbError
    }
  }

  return {
    updateProfile,
    getProfile,
  }
}

export function useSchedule() {
  const { db, currentUser } = useDatabase()

  const getSchedule = async (
    semester: string | null = null,
    year: string | null = null
  ): Promise<ScheduleData[]> => {
    try {
      if (!currentUser.value) return []
      return await db.getUserSchedule(currentUser.value.userId, semester, year)
    } catch (err) {
      console.error('Failed to get schedule:', err)
      return []
    }
  }

  const saveSchedule = async (scheduleData: ScheduleData[]): Promise<void> => {
    try {
      if (!currentUser.value) throw new Error('No current user')

      // Clear existing schedule for the same semester/year
      await db.schedules
        .where('userId')
        .equals(currentUser.value.userId)
        .and(
          item => item.semester === scheduleData[0]?.semester && item.year === scheduleData[0]?.year
        )
        .delete()

      // Add new schedule
      const scheduleWithUser = scheduleData.map(item => ({
        ...item,
        userId: currentUser.value!.userId,
      }))

      await db.schedules.bulkAdd(scheduleWithUser)
    } catch (err) {
      console.error('Failed to save schedule:', err)
      throw err
    }
  }

  return {
    getSchedule,
    saveSchedule,
  }
}

export function useAnnouncements() {
  const { db, currentUser } = useDatabase()

  const getAnnouncements = async (limit: number = 50): Promise<AnnouncementData[]> => {
    try {
      if (!currentUser.value) return []

      const user = currentUser.value
      return await db.announcements
        .where('targetAudience')
        .anyOf(['all', user.role])
        .or('targetAudience')
        .startsWith(user.role)
        .reverse()
        .limit(limit)
        .toArray()
    } catch (err) {
      console.error('Failed to get announcements:', err)
      return []
    }
  }

  const getUnreadCount = async (): Promise<number> => {
    try {
      if (!currentUser.value) return 0
      const unread = await db.getUnreadAnnouncements(currentUser.value.userId)
      return unread.length
    } catch (err) {
      console.error('Failed to get unread count:', err)
      return 0
    }
  }

  const markAsRead = async (announcementId: string): Promise<void> => {
    try {
      await db.markAnnouncementAsRead(announcementId)
    } catch (err) {
      console.error('Failed to mark announcement as read:', err)
      throw err
    }
  }

  const saveAnnouncements = async (announcements: AnnouncementData[]): Promise<void> => {
    try {
      await db.announcements.bulkPut(announcements)
    } catch (err) {
      console.error('Failed to save announcements:', err)
      throw err
    }
  }

  return {
    getAnnouncements,
    getUnreadCount,
    markAsRead,
    saveAnnouncements,
  }
}

export function useAttendance() {
  const { db, currentUser } = useDatabase()

  const getAttendanceRecords = async (
    courseId: string | null = null
  ): Promise<AttendanceData[]> => {
    try {
      if (!currentUser.value) return []
      return await db.getAttendanceForStudent(currentUser.value.userId, courseId)
    } catch (err) {
      console.error('Failed to get attendance records:', err)
      return []
    }
  }

  const recordAttendance = async (attendanceData: AttendanceData): Promise<AttendanceData> => {
    try {
      const record = {
        ...attendanceData,
        createdAt: new Date(),
        syncStatus: 'pending' as const,
      }

      await db.attendanceRecords.add(record)
      return record
    } catch (err) {
      console.error('Failed to record attendance:', err)
      throw err
    }
  }

  const getPendingSync = async (): Promise<{
    attendance: AttendanceData[]
    leaveRequests: LeaveRequestData[]
  }> => {
    try {
      return await db.getPendingSyncRecords()
    } catch (err) {
      console.error('Failed to get pending sync records:', err)
      return { attendance: [], leaveRequests: [] }
    }
  }

  return {
    getAttendanceRecords,
    recordAttendance,
    getPendingSync,
  }
}

export function useLeaveRequests() {
  const { db, currentUser } = useDatabase()

  const getLeaveRequests = async (): Promise<LeaveRequestData[]> => {
    try {
      if (!currentUser.value) return []
      return await db.leaveRequests
        .where('teacherId')
        .equals(currentUser.value.userId)
        .reverse()
        .sortBy('requestedAt')
    } catch (err) {
      console.error('Failed to get leave requests:', err)
      return []
    }
  }

  const submitLeaveRequest = async (leaveData: LeaveRequestData): Promise<LeaveRequestData> => {
    try {
      if (!currentUser.value) throw new Error('No current user')

      const request = {
        ...leaveData,
        teacherId: currentUser.value.userId,
        requestedAt: new Date(),
        status: 'pending' as const,
        syncStatus: 'pending' as const,
      }

      await db.leaveRequests.add(request)
      return request
    } catch (err) {
      console.error('Failed to submit leave request:', err)
      throw err
    }
  }

  return {
    getLeaveRequests,
    submitLeaveRequest,
  }
}

export function useFinancials() {
  const { db, currentUser } = useDatabase()

  const getFinancialRecords = async (): Promise<FinancialData[]> => {
    try {
      if (!currentUser.value) return []
      return await db.financialRecords
        .where('studentId')
        .equals(currentUser.value.userId)
        .reverse()
        .sortBy('year')
    } catch (err) {
      console.error('Failed to get financial records:', err)
      return []
    }
  }

  const saveFinancialData = async (financialData: FinancialData): Promise<void> => {
    try {
      if (!currentUser.value) throw new Error('No current user')

      const record = {
        ...financialData,
        studentId: currentUser.value.userId,
        lastSync: new Date(),
      }

      await db.financialRecords.put(record)
    } catch (err) {
      console.error('Failed to save financial data:', err)
      throw err
    }
  }

  return {
    getFinancialRecords,
    saveFinancialData,
  }
}
