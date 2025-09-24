import { defineStore } from 'pinia'
import { useAttendance } from '@/composables/useDatabase'
import { useApi } from '@/composables/useApi'
import { notificationService } from '@/services/notificationService'

// Define interfaces for store state and data
interface AttendanceSubmission {
  code: string
  timestamp: string
  status: 'pending' | 'synced' | 'error'
}

interface TeacherSession {
  id: string
  class_part_id: string
  attendance_code: string
  [key: string]: unknown
}

interface ClassRosterStudent {
  id: string
  name: string
  student_id: string
  [key: string]: unknown
}

interface ClassRosterResponse {
  students: ClassRosterStudent[]
}

interface ManualAttendanceData {
  session_id: string
  student_id: string
  status: string
  notes?: string
}

interface LocationData {
  latitude?: number
  longitude?: number
  [key: string]: unknown
}

// Define store state interface
interface AttendanceStoreState {
  // Student-specific state
  submitting: boolean
  retrying: boolean
  recentCheckIns: AttendanceSubmission[]
  offlineQueue: AttendanceSubmission[]

  // Teacher-specific state
  activeTeacherSession: TeacherSession | null
  classRoster: ClassRosterStudent[]
  teacherSessionLoading: boolean
  rosterLoading: boolean
  manualSubmissionLoading: boolean
}

export const useAttendanceStore = defineStore('attendance', {
  state: (): AttendanceStoreState => ({
    // Student-specific state
    submitting: false,
    retrying: false,
    recentCheckIns: [],
    offlineQueue: [],

    // Teacher-specific state
    activeTeacherSession: null,
    classRoster: [],
    teacherSessionLoading: false,
    rosterLoading: false,
    manualSubmissionLoading: false,
  }),

  actions: {
    // STUDENT ACTIONS //
    async submitAttendanceCode(code: string): Promise<void> {
      this.submitting = true

      try {
        const payload: AttendanceSubmission = {
          code,
          timestamp: new Date().toISOString(),
          status: 'pending',
        }

        await this.queueAttendanceSubmission(payload)
        await this._submitToServer(payload)

        notificationService.success('Attendance submitted successfully!')

        await this.loadRecentCheckIns()
        await this.loadOfflineQueue()
      } catch (error) {
        console.error('Attendance submission error:', error)
        notificationService.error('Failed to submit attendance. Please try again.')
      } finally {
        this.submitting = false
      }
    },

    async queueAttendanceSubmission(payload: AttendanceSubmission): Promise<void> {
      const { recordAttendance } = useAttendance()
      try {
        await recordAttendance(payload)
      } catch (error) {
        console.error('Error queuing attendance:', error)
      }
    },

    async _submitToServer(payload: AttendanceSubmission): Promise<void> {
      const { makeApiRequest } = useApi()
      try {
        await makeApiRequest('/student/checkin/', 'POST', payload)
        console.log('Attendance code submitted:', payload)

        // After successful submission, you might want to update the local record's sync status
        // This part is left for a dedicated sync process for now.
      } catch (error) {
        console.error('Failed to submit attendance code:', error)
        throw error // Re-throw to be caught by the caller
      }
    },

    async retryOfflineSubmissions(): Promise<void> {
      this.retrying = true

      try {
        const { getPendingSync } = useAttendance()
        const { attendance } = await getPendingSync()

        for (const submission of attendance) {
          try {
            await this._submitToServer(submission)
          } catch (error) {
            console.error('Failed to retry submission:', error)
          }
        }

        notificationService.success('Offline submissions synced successfully!')

        await this.loadOfflineQueue()
        await this.loadRecentCheckIns()
      } catch (error) {
        notificationService.error('Failed to sync offline submissions')
      } finally {
        this.retrying = false
      }
    },

    async loadRecentCheckIns(): Promise<void> {
      const { getAttendanceRecords } = useAttendance()
      try {
        this.recentCheckIns = await getAttendanceRecords()
      } catch (error) {
        console.error('Error loading recent check-ins:', error)
      }
    },

    async loadOfflineQueue(): Promise<void> {
      const { getPendingSync } = useAttendance()
      try {
        const { attendance } = await getPendingSync()
        this.offlineQueue = attendance
      } catch (error) {
        console.error('Error loading offline queue:', error)
      }
    },

    // TEACHER ACTIONS //

    async startTeacherSession(classPartId: string, locationData: LocationData): Promise<void> {
      const { makeApiRequest } = useApi()
      this.teacherSessionLoading = true

      try {
        const payload = {
          class_part_id: classPartId,
          ...locationData, // e.g., latitude, longitude
          // attendance_code is generated by backend as per our discussion
        }

        // API endpoint from docs: POST /api/attendance/teacher/start-session
        const sessionData = await makeApiRequest<TeacherSession>(
          '/attendance/teacher/start-session',
          'POST',
          payload
        )

        this.activeTeacherSession = sessionData

        // Optionally, fetch roster immediately
        if (sessionData && sessionData.class_part_id) {
          await this.fetchClassRoster(sessionData.class_part_id)
        } else if (classPartId) {
          // if response doesn't include class_part_id but we have it from input
          await this.fetchClassRoster(classPartId)
        }

        notificationService.success('Attendance session started successfully!')
      } catch (error) {
        console.error('Error starting teacher session:', error)
        notificationService.error('Failed to start attendance session')
        this.activeTeacherSession = null
      } finally {
        this.teacherSessionLoading = false
      }
    },

    async fetchClassRoster(classPartId: string): Promise<void> {
      const { makeApiRequest } = useApi()
      this.rosterLoading = true

      try {
        // API endpoint from docs: GET /api/attendance/teacher/class-roster/{class_part_id}
        const rosterData = await makeApiRequest<ClassRosterResponse>(
          `/attendance/teacher/class-roster/${classPartId}`,
          'GET'
        )
        this.classRoster = rosterData.students || []
      } catch (error) {
        console.error('Error fetching class roster:', error)
        notificationService.error('Failed to fetch class roster')
        this.classRoster = []
      } finally {
        this.rosterLoading = false
      }
    },

    async submitManualAttendance(manualEntryData: ManualAttendanceData): Promise<void> {
      const { makeApiRequest } = useApi()
      this.manualSubmissionLoading = true

      try {
        // API endpoint from docs: POST /api/attendance/teacher/manual-attendance
        await makeApiRequest('/attendance/teacher/manual-attendance', 'POST', manualEntryData)

        notificationService.success('Manual attendance recorded successfully!')
        // Optionally, refresh part of the roster or session data if needed
      } catch (error) {
        console.error('Error submitting manual attendance:', error)
        notificationService.error('Failed to record manual attendance')
      } finally {
        this.manualSubmissionLoading = false
      }
    },

    async endTeacherSession(): Promise<void> {
      const { makeApiRequest } = useApi()

      if (!this.activeTeacherSession || !this.activeTeacherSession.id) {
        console.warn('No active teacher session to end.')
        return
      }

      this.teacherSessionLoading = true

      try {
        // API endpoint from docs: POST /api/attendance/teacher/end-session/{session_id}
        await makeApiRequest(
          `/attendance/teacher/end-session/${this.activeTeacherSession.id}`,
          'POST'
        )

        notificationService.success('Attendance session ended successfully!')

        this.activeTeacherSession = null
        this.classRoster = []
      } catch (error) {
        console.error('Error ending teacher session:', error)
        notificationService.error('Failed to end attendance session')
      } finally {
        this.teacherSessionLoading = false
      }
    },
  },
})
