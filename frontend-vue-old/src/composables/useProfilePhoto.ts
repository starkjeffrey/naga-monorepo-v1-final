import { ref } from 'vue'
import { useDatabase } from './useDatabase'
import { useMobileAuth } from './useMobileAuth'

// Types
export interface PhotoData {
  blob: Blob
  dataUrl: string
  width: number
  height: number
  timestamp: string
  metadata?: PhotoMetadata
}

export interface PhotoMetadata {
  quality?: number
  faceDetected?: boolean
  deviceInfo?: string
  captureMethod?: string
  [key: string]: any
}

export interface PhotoRecord {
  id: string
  userId: string
  imageData: string
  dataUrl: string
  width: number
  height: number
  timestamp: string
  metadata?: PhotoMetadata
  isActive: boolean
  syncStatus: 'pending' | 'synced' | 'failed'
  serverId?: string
  serverUrl?: string
  error?: string
  createdAt: Date
}

export interface ValidationResult {
  isValid: boolean
  issues: string[]
}

export interface AttendancePhoto {
  id: string
  dataUrl: string
  timestamp: string
  isRecent: boolean
}

export function useProfilePhoto() {
  const { db, currentUser } = useDatabase()
  const { makeAuthenticatedRequest } = useMobileAuth()
  const uploading = ref<boolean>(false)
  const uploadProgress = ref<number>(0)

  const savePhotoToDatabase = async (photoData: PhotoData): Promise<PhotoRecord> => {
    try {
      if (!currentUser.value) {
        throw new Error('No current user')
      }

      // Input validation
      if (!photoData || !photoData.blob || !photoData.dataUrl) {
        throw new Error('Invalid photo data provided')
      }

      // Convert blob to base64 for storage
      const base64Data = await blobToBase64(photoData.blob)

      const photoRecord: PhotoRecord = {
        id: `photo_${currentUser.value.userId}_${Date.now()}`,
        userId: currentUser.value.userId,
        imageData: base64Data,
        dataUrl: photoData.dataUrl,
        width: photoData.width,
        height: photoData.height,
        timestamp: photoData.timestamp,
        metadata: photoData.metadata,
        isActive: true,
        syncStatus: 'pending',
        createdAt: new Date(),
      }

      // Store in profile photos table
      await db.transaction('rw', [db.userProfiles], async () => {
        // Deactivate previous photos
        await db.userProfiles
          .where('userId')
          .equals(currentUser.value!.userId)
          .modify({ profilePhoto: null })

        // Save new photo and update user profile
        await db.userProfiles.where('userId').equals(currentUser.value!.userId).modify({
          profilePhoto: photoRecord,
          avatar: photoData.dataUrl,
          updatedAt: new Date(),
        })
      })

      return photoRecord
    } catch (error) {
      console.error('Failed to save photo to database:', error)
      throw error
    }
  }

  const uploadPhotoToServer = async (photoData: PhotoData): Promise<any> => {
    uploading.value = true
    uploadProgress.value = 0

    try {
      if (!currentUser.value) {
        throw new Error('No current user')
      }

      // Create FormData for upload
      const formData = new FormData()
      formData.append('photo', photoData.blob, 'profile_photo.jpg')
      formData.append('userId', currentUser.value.userId)
      formData.append('timestamp', photoData.timestamp)
      if (photoData.metadata) {
        formData.append('metadata', JSON.stringify(photoData.metadata))
      }

      // Upload to Django server using authenticated request
      const response = await makeAuthenticatedRequest('/api/profile/photo', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`)
      }

      const result = await response.json()
      uploadProgress.value = 100

      // Update sync status in database
      await db.userProfiles.where('userId').equals(currentUser.value.userId).modify({
        'profilePhoto.syncStatus': 'synced',
        'profilePhoto.serverId': result.photoId,
        'profilePhoto.serverUrl': result.photoUrl,
      })

      return result
    } catch (error) {
      console.error('Failed to upload photo to server:', error)

      // Update sync status to failed
      if (currentUser.value) {
        await db.userProfiles
          .where('userId')
          .equals(currentUser.value.userId)
          .modify({
            'profilePhoto.syncStatus': 'failed',
            'profilePhoto.error': (error as Error).message,
          })
      }

      throw error
    } finally {
      uploading.value = false
      uploadProgress.value = 0
    }
  }

  const getUserProfilePhoto = async (userId?: string): Promise<PhotoRecord | null> => {
    try {
      const targetUserId = userId || currentUser.value?.userId
      if (!targetUserId) return null

      const user = await db.userProfiles.where('userId').equals(targetUserId).first()

      return user?.profilePhoto || null
    } catch (error) {
      console.error('Failed to get profile photo:', error)
      return null
    }
  }

  const deleteProfilePhoto = async (): Promise<boolean> => {
    try {
      if (!currentUser.value) {
        throw new Error('No current user')
      }

      // Mark photo as deleted in database
      await db.userProfiles.where('userId').equals(currentUser.value.userId).modify({
        profilePhoto: null,
        avatar: null,
        updatedAt: new Date(),
      })

      // Try to delete from server
      try {
        await makeAuthenticatedRequest('/api/profile/photo', {
          method: 'DELETE',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ userId: currentUser.value.userId }),
        })
      } catch (serverError) {
        console.warn('Failed to delete photo from server:', serverError)
        // Continue with local deletion even if server fails
      }

      return true
    } catch (error) {
      console.error('Failed to delete profile photo:', error)
      throw error
    }
  }

  const syncPendingPhotos = async (): Promise<void> => {
    try {
      // Find users with pending photo uploads
      const usersWithPendingPhotos = await db.userProfiles
        .where('profilePhoto.syncStatus')
        .equals('pending')
        .toArray()

      for (const user of usersWithPendingPhotos) {
        if (user.profilePhoto) {
          try {
            // Convert base64 back to blob
            const blob = base64ToBlob(user.profilePhoto.imageData, 'image/jpeg')
            const photoData: PhotoData = {
              blob,
              dataUrl: user.profilePhoto.dataUrl,
              width: user.profilePhoto.width,
              height: user.profilePhoto.height,
              timestamp: user.profilePhoto.timestamp,
              metadata: user.profilePhoto.metadata,
            }

            await uploadPhotoToServer(photoData)
          } catch (error) {
            console.error(`Failed to sync photo for user ${user.userId}:`, error)
          }
        }
      }
    } catch (error) {
      console.error('Failed to sync pending photos:', error)
    }
  }

  const validatePhotoQuality = (photoData: PhotoData): ValidationResult => {
    const issues: string[] = []

    // Input validation
    if (!photoData) {
      issues.push('No photo data provided')
      return { isValid: false, issues }
    }

    if (!photoData.blob) {
      issues.push('No photo blob provided')
      return { isValid: false, issues }
    }

    if (!photoData.width || !photoData.height) {
      issues.push('Photo dimensions not provided')
      return { isValid: false, issues }
    }

    // Check dimensions
    if (photoData.width < 400 || photoData.height < 400) {
      issues.push('Photo resolution too low (minimum 400x400)')
    }

    // Check aspect ratio
    const aspectRatio = photoData.width / photoData.height
    if (aspectRatio < 0.75 || aspectRatio > 1.33) {
      issues.push('Photo aspect ratio should be close to 1:1')
    }

    // Check file size
    if (photoData.blob.size > 5 * 1024 * 1024) {
      // 5MB limit
      issues.push('Photo file size too large (maximum 5MB)')
    }

    if (photoData.blob.size < 50 * 1024) {
      // 50KB minimum
      issues.push('Photo file size too small (minimum 50KB)')
    }

    // Check file type
    if (!photoData.blob.type.startsWith('image/')) {
      issues.push('File must be an image')
    }

    return {
      isValid: issues.length === 0,
      issues,
    }
  }

  const blobToBase64 = (blob: Blob): Promise<string> => {
    return new Promise((resolve, reject) => {
      if (!blob) {
        reject(new Error('No blob provided'))
        return
      }

      if (!(blob instanceof Blob)) {
        reject(new Error('Invalid blob type'))
        return
      }

      const reader = new FileReader()
      reader.onload = () => resolve(reader.result as string)
      reader.onerror = () => reject(new Error('Failed to read blob'))
      reader.readAsDataURL(blob)
    })
  }

  const base64ToBlob = (base64Data: string, contentType: string): Blob => {
    const base64 = base64Data.split(',')[1]
    const byteCharacters = atob(base64)
    const byteNumbers = new Array(byteCharacters.length)

    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i)
    }

    const byteArray = new Uint8Array(byteNumbers)
    return new Blob([byteArray], { type: contentType })
  }

  const getPhotoForAttendance = async (userId: string): Promise<AttendancePhoto | null> => {
    try {
      const photo = await getUserProfilePhoto(userId)

      if (!photo) return null

      return {
        id: photo.id,
        dataUrl: photo.dataUrl,
        timestamp: photo.timestamp,
        isRecent: isPhotoRecent(photo.timestamp),
      }
    } catch (error) {
      console.error('Failed to get photo for attendance:', error)
      return null
    }
  }

  const isPhotoRecent = (timestamp: string): boolean => {
    const photoDate = new Date(timestamp)
    const now = new Date()
    const daysDiff = (now.getTime() - photoDate.getTime()) / (1000 * 60 * 60 * 24)

    // Consider photo recent if taken within last 30 days
    return daysDiff <= 30
  }

  return {
    // State
    uploading,
    uploadProgress,

    // Methods
    savePhotoToDatabase,
    uploadPhotoToServer,
    getUserProfilePhoto,
    deleteProfilePhoto,
    syncPendingPhotos,
    validatePhotoQuality,
    getPhotoForAttendance,
    isPhotoRecent,
  }
}
