import Dexie, { type Table, type Transaction } from 'dexie'

// Define interfaces for database entities
export interface UserProfile {
  id?: number
  userId: string
  name: string
  email: string
  phone: string
  role: string
  avatar?: string
  preferredLanguage: string
  theme: string
  profilePhoto?: string
  studentId?: string
  studyLevel?: string
  department?: string
  academicYear?: string
  lastSync?: Date
  createdAt?: Date
  updatedAt?: Date
}

export interface Schedule {
  id?: number
  userId: string
  courseId: string
  courseName: string
  instructor: string
  classroom: string
  dayOfWeek: string
  startTime: string
  endTime: string
  semester: string
  year: string
}

export interface Announcement {
  id?: number
  announcementId: string
  title: string
  content: string
  author: string
  priority: string
  targetAudience: string | string[]
  createdAt: Date
  readAt?: Date
  isRead: boolean
}

export interface AttendanceRecord {
  id?: number
  studentId: string
  courseId: string
  date: Date
  status: string
  takenBy: string
  location?: string
  syncStatus: 'pending' | 'synced' | 'error'
  createdAt: Date
  syncedAt?: Date
}

export interface FinancialRecord {
  id?: number
  studentId: string
  balance: number
  lastPayment?: Date
  dueDate?: Date
  semester: string
  year: string
  lastSync: Date
}

export interface LeaveRequest {
  id?: number
  teacherId: string
  startDate: Date
  endDate: Date
  reason: string
  status: string
  requestedAt: Date
  approvedAt?: Date
  syncStatus: 'pending' | 'synced' | 'error'
  createdAt?: Date
  syncedAt?: Date
}

export interface AppSetting {
  id?: number
  key: string
  value: string
  userId?: string
}

export interface SyncLogEntry {
  id?: number
  tableName: string
  operation: string
  recordId: string | number
  timestamp: Date
  status: 'success' | 'error'
  error?: string
}

export interface PendingSyncData {
  attendance: AttendanceRecord[]
  leaveRequests: LeaveRequest[]
}

export class NagaDatabase extends Dexie {
  // Define tables with proper typing
  userProfiles!: Table<UserProfile>
  schedules!: Table<Schedule>
  announcements!: Table<Announcement>
  attendanceRecords!: Table<AttendanceRecord>
  financialRecords!: Table<FinancialRecord>
  leaveRequests!: Table<LeaveRequest>
  appSettings!: Table<AppSetting>
  syncLog!: Table<SyncLogEntry>

  constructor() {
    super('NagaDatabase')

    this.version(1).stores({
      // User profile and settings
      userProfiles:
        '++id, userId, name, email, phone, role, avatar, preferredLanguage, theme, profilePhoto, studentId, studyLevel, department, academicYear, lastSync',

      // Course schedules (cached for offline access)
      schedules:
        '++id, userId, courseId, courseName, instructor, classroom, dayOfWeek, startTime, endTime, semester, year',

      // Announcements (cached for offline reading)
      announcements:
        '++id, announcementId, title, content, author, priority, targetAudience, createdAt, readAt, isRead',

      // Attendance records (for offline viewing and sync)
      attendanceRecords:
        '++id, studentId, courseId, date, status, takenBy, location, syncStatus, createdAt',

      // Financial balance snapshots (for students)
      financialRecords: '++id, studentId, balance, lastPayment, dueDate, semester, year, lastSync',

      // Leave requests (for teachers)
      leaveRequests:
        '++id, teacherId, startDate, endDate, reason, status, requestedAt, approvedAt, syncStatus',

      // App settings and preferences
      appSettings: '++id, key, value, userId',

      // Sync metadata
      syncLog: '++id, tableName, operation, recordId, timestamp, status, error',
    })

    // Define hooks for automatic timestamping
    this.userProfiles.hook('creating', (_primKey, obj: UserProfile, _trans: Transaction) => {
      obj.createdAt = new Date()
      obj.updatedAt = new Date()
    })

    this.userProfiles.hook(
      'updating',
      (modifications: Partial<UserProfile>, _primKey, _obj, _trans) => {
        modifications.updatedAt = new Date()
      }
    )

    // Add similar hooks for other tables
    this.attendanceRecords.hook(
      'creating',
      (_primKey, obj: AttendanceRecord, _trans: Transaction) => {
        obj.createdAt = new Date()
        obj.syncStatus = obj.syncStatus || 'pending'
      }
    )

    this.leaveRequests.hook('creating', (_primKey, obj: LeaveRequest, _trans: Transaction) => {
      obj.createdAt = new Date()
      obj.syncStatus = obj.syncStatus || 'pending'
    })
  }

  // Helper methods for common operations
  async getCurrentUser(): Promise<UserProfile | null> {
    const settings = await this.appSettings.where('key').equals('currentUserId').first()
    if (settings) {
      return (await this.userProfiles.where('userId').equals(settings.value).first()) || null
    }
    return null
  }

  async setCurrentUser(userId: string): Promise<void> {
    await this.appSettings.put({ key: 'currentUserId', value: userId })
  }

  async getUserSchedule(userId: string, semester?: string, year?: string): Promise<Schedule[]> {
    let query = this.schedules.where('userId').equals(userId)
    if (semester) query = query.and(item => item.semester === semester)
    if (year) query = query.and(item => item.year === year)
    return await query.toArray()
  }

  async getUnreadAnnouncements(userId: string): Promise<Announcement[]> {
    const user = await this.userProfiles.where('userId').equals(userId).first()
    if (!user) return []

    return await this.announcements
      .where('isRead')
      .equals(false)
      .and(item => {
        if (typeof item.targetAudience === 'string') {
          return item.targetAudience === 'all' || item.targetAudience === user.role
        }
        return item.targetAudience.includes('all') || item.targetAudience.includes(user.role)
      })
      .reverse()
      .sortBy('createdAt')
  }

  async markAnnouncementAsRead(announcementId: string): Promise<void> {
    await this.announcements
      .where('announcementId')
      .equals(announcementId)
      .modify({ isRead: true, readAt: new Date() })
  }

  async getAttendanceForStudent(studentId: string, courseId?: string): Promise<AttendanceRecord[]> {
    let query = this.attendanceRecords.where('studentId').equals(studentId)
    if (courseId) query = query.and(item => item.courseId === courseId)
    return await query.reverse().sortBy('date')
  }

  async getPendingSyncRecords(): Promise<PendingSyncData> {
    const attendance = await this.attendanceRecords.where('syncStatus').equals('pending').toArray()
    const leaves = await this.leaveRequests.where('syncStatus').equals('pending').toArray()

    return {
      attendance,
      leaveRequests: leaves,
    }
  }

  async markRecordAsSynced(tableName: keyof NagaDatabase, recordId: number): Promise<void> {
    const table = this[tableName] as Table<any>
    await table.update(recordId, { syncStatus: 'synced', syncedAt: new Date() })
  }

  async logSyncOperation(
    tableName: string,
    operation: string,
    recordId: string | number,
    status: 'success' | 'error',
    error?: string
  ): Promise<void> {
    await this.syncLog.add({
      tableName,
      operation,
      recordId,
      timestamp: new Date(),
      status,
      error,
    })
  }

  async clearUserData(userId: string): Promise<void> {
    await this.transaction(
      'rw',
      [
        this.userProfiles,
        this.schedules,
        this.announcements,
        this.attendanceRecords,
        this.financialRecords,
        this.leaveRequests,
        this.appSettings,
      ],
      async () => {
        await this.userProfiles.where('userId').equals(userId).delete()
        await this.schedules.where('userId').equals(userId).delete()
        await this.attendanceRecords.where('studentId').equals(userId).delete()
        await this.financialRecords.where('studentId').equals(userId).delete()
        await this.leaveRequests.where('teacherId').equals(userId).delete()
        await this.appSettings.where('userId').equals(userId).delete()
      }
    )
  }
}

// Create and export a singleton instance
export const db = new NagaDatabase()
