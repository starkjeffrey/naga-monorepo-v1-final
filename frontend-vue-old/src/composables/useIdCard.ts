import { ref, computed, ComputedRef } from 'vue'
import QRCode from 'qrcode'
import { useDatabase } from './useDatabase'
import { useProfilePhoto, PhotoRecord } from './useProfilePhoto'

// Types
export interface StudentInfo {
  studentId: string
  fullName: string
  studyLevel: string
  department: string
  academicYear: string
  email: string
  schoolEmail: string
  phone: string
  teacherId: string | null
  role: string
}

export interface QRCodeInfo {
  name: string
  email: string
  student_id?: string
  teacher_id?: string | null
  role: string
  level: string
  dept: string
  year: string
  issued: string
  institution: string
  version: string
}

export interface IdCardData {
  student: StudentInfo
  qrCode: string
  photo: PhotoRecord | null
  generatedAt: string
}

export interface ValidationResult {
  isValid: boolean
  issues: string[]
}

export interface UserIdDisplay {
  studentId?: string
  teacherId?: string
  showBoth: boolean
}

export function useIdCard() {
  const { currentUser } = useDatabase()
  const { getUserProfilePhoto } = useProfilePhoto()

  const idCardData = ref<IdCardData | null>(null)
  const qrCodeDataUrl = ref<string>('')
  const profilePhoto = ref<PhotoRecord | null>(null)
  const loading = ref<boolean>(false)

  const studentInfo: ComputedRef<StudentInfo | null> = computed(() => {
    if (!currentUser.value) return null

    return {
      studentId: currentUser.value.studentId || 'ST000000',
      fullName: currentUser.value.name || 'Student Name',
      studyLevel: currentUser.value.studyLevel || 'BA',
      department: currentUser.value.department || 'General Studies',
      academicYear: currentUser.value.academicYear || '2024-2025',
      email: currentUser.value.email || '',
      schoolEmail: currentUser.value.schoolEmail || currentUser.value.school_email || '',
      phone: currentUser.value.phone || '',
      teacherId: currentUser.value.teacherId || currentUser.value.teacher_id || null,
      role: currentUser.value.role || 'student',
    }
  })

  const qrCodeData: ComputedRef<string> = computed(() => {
    if (!studentInfo.value) return ''

    // Create QR code data with essential information including ID and email
    const qrData: QRCodeInfo = {
      name: studentInfo.value.fullName,
      email: studentInfo.value.schoolEmail || studentInfo.value.email,
      role: studentInfo.value.role,
      level: studentInfo.value.studyLevel,
      dept: studentInfo.value.department,
      year: studentInfo.value.academicYear,
      issued: new Date().toISOString().split('T')[0], // Current date
      institution: 'PUCSR',
      version: '1.0', // Version for QR code format
    }

    // Add student_id if available
    if (studentInfo.value.studentId) {
      qrData.student_id = studentInfo.value.studentId
    }

    // Add teacher_id if available
    if (studentInfo.value.teacherId) {
      qrData.teacher_id = studentInfo.value.teacherId
    }

    // Remove null, undefined, or empty values to keep QR code clean
    Object.keys(qrData).forEach(key => {
      const value = qrData[key as keyof QRCodeInfo]
      if (value === null || value === undefined || value === '') {
        delete qrData[key as keyof QRCodeInfo]
      }
    })

    return JSON.stringify(qrData)
  })

  const generateQRCode = async (): Promise<void> => {
    try {
      if (!qrCodeData.value) return

      const options = {
        width: 300,
        margin: 2,
        color: {
          dark: '#000000',
          light: '#FFFFFF',
        },
        errorCorrectionLevel: 'M' as const,
      }

      qrCodeDataUrl.value = await QRCode.toDataURL(qrCodeData.value, options)
    } catch (error) {
      console.error('Failed to generate QR code:', error)
      throw error
    }
  }

  const loadProfilePhoto = async (): Promise<void> => {
    try {
      if (!currentUser.value) return

      profilePhoto.value = await getUserProfilePhoto()
    } catch (error) {
      console.error('Failed to load profile photo:', error)
    }
  }

  const generateIdCard = async (): Promise<IdCardData> => {
    loading.value = true
    try {
      await Promise.all([generateQRCode(), loadProfilePhoto()])

      if (!studentInfo.value) {
        throw new Error('No student information available')
      }

      idCardData.value = {
        student: studentInfo.value,
        qrCode: qrCodeDataUrl.value,
        photo: profilePhoto.value,
        generatedAt: new Date().toISOString(),
      }

      return idCardData.value
    } catch (error) {
      console.error('Failed to generate ID card:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  const validateIdCard = (): ValidationResult => {
    const issues: string[] = []

    if (!studentInfo.value?.studentId) {
      issues.push('Missing student ID')
    }

    if (!studentInfo.value?.fullName) {
      issues.push('Missing student name')
    }

    if (!studentInfo.value?.studyLevel) {
      issues.push('Missing study level')
    }

    if (!profilePhoto.value) {
      issues.push('Missing profile photo')
    } else if (!profilePhoto.value.dataUrl) {
      issues.push('Invalid profile photo')
    }

    return {
      isValid: issues.length === 0,
      issues,
    }
  }

  const refreshIdCard = async (): Promise<IdCardData> => {
    return await generateIdCard()
  }

  const getStudyLevelDisplay = (level: string): string => {
    const levels: Record<string, string> = {
      LANG: 'Language Program',
      BA: "Bachelor's Degree",
      MA: "Master's Degree",
    }
    return levels[level] || level
  }

  const formatStudentId = (id: string): string => {
    // Format student ID for display (e.g., ST-2024-001)
    if (!id) return ''

    if (id.length >= 8) {
      return `${id.slice(0, 2)}-${id.slice(2, 6)}-${id.slice(6)}`
    }

    return id
  }

  const formatTeacherId = (id: string | null): string => {
    // Format teacher ID for display (e.g., TC-2024-001 or similar)
    if (!id) return ''

    const idStr = id.toString()
    if (idStr.length >= 5) {
      // Assuming 5-6 digit teacher IDs, format as TC-XXXX or TC-XXXXX
      return `TC-${idStr}`
    }

    return idStr
  }

  const getUserIdDisplay = (): UserIdDisplay => {
    const info = studentInfo.value
    if (!info) return { showBoth: false }

    // For dual-role users, show both IDs
    if (info.role === 'both' && info.teacherId && info.studentId) {
      return {
        studentId: formatStudentId(info.studentId),
        teacherId: formatTeacherId(info.teacherId),
        showBoth: true,
      }
    }

    // Teacher only
    if ((info.role === 'teacher' || info.role === 'both') && info.teacherId) {
      return {
        teacherId: formatTeacherId(info.teacherId),
        showBoth: false,
      }
    }

    // Student only (default)
    return {
      studentId: formatStudentId(info.studentId),
      showBoth: false,
    }
  }

  return {
    // State
    loading,
    idCardData,
    studentInfo,
    profilePhoto,
    qrCodeDataUrl,

    // Methods
    generateIdCard,
    refreshIdCard,
    validateIdCard,
    getStudyLevelDisplay,
    formatStudentId,
    formatTeacherId,
    getUserIdDisplay,

    // Computed
    qrCodeData,
  }
}
