<template>
  <q-page>
    <!-- Camera Capture Mode -->
    <error-boundary
      v-if="showCamera"
      :show-report-button="true"
      :can-go-back="true"
      @error="handleCameraError"
      @retry="startCamera"
    >
      <camera-capture
        :passport-size="true"
        @photo-captured="handlePhotoCaptured"
        @cancel="handleCameraCancel"
      />
    </error-boundary>

    <!-- Main Profile Photo Page -->
    <div v-else class="q-pa-md">
      <div class="q-mb-lg">
        <h4 class="text-h4 q-mb-xs text-weight-medium">
          {{ $t('profilePhoto.title') }}
        </h4>
        <p class="text-subtitle1 text-grey-6">
          {{ $t('profilePhoto.subtitle') }}
        </p>
      </div>

      <!-- Current Photo Display -->
      <q-card class="q-mb-md">
        <q-card-section class="text-center q-pa-lg">
          <div class="current-photo-container q-mb-md">
            <q-avatar v-if="currentPhoto" size="200px" class="passport-photo-preview">
              <img :src="currentPhoto.dataUrl" alt="Profile Photo" />
            </q-avatar>
            <div v-else class="no-photo-placeholder">
              <q-icon name="person" size="120px" color="grey-4" />
              <p class="text-caption text-grey-6 q-mt-md">
                {{ $t('profilePhoto.noPhoto') }}
              </p>
            </div>
          </div>

          <div v-if="currentPhoto" class="photo-info q-mb-md">
            <q-chip
              :color="isPhotoRecent ? 'positive' : 'warning'"
              text-color="white"
              :icon="isPhotoRecent ? 'check_circle' : 'schedule'"
              size="sm"
            >
              {{ isPhotoRecent ? $t('profilePhoto.recent') : $t('profilePhoto.outdated') }}
            </q-chip>
            <p class="text-caption text-grey-6 q-mt-sm">
              {{ $t('profilePhoto.takenOn') }}: {{ formatDate(currentPhoto.timestamp) }}
            </p>
          </div>
        </q-card-section>
      </q-card>

      <!-- Action Buttons -->
      <div class="action-buttons q-mb-md">
        <q-btn
          color="primary"
          icon="camera_alt"
          :label="currentPhoto ? $t('profilePhoto.updatePhoto') : $t('profilePhoto.takePhoto')"
          class="full-width q-mb-md"
          size="lg"
          @click="startCamera"
        />

        <q-btn
          v-if="currentPhoto"
          color="negative"
          icon="delete"
          :label="$t('profilePhoto.deletePhoto')"
          outline
          class="full-width q-mb-md"
          @click="confirmDeletePhoto"
        />

        <q-btn
          v-if="hasPendingUpload"
          color="orange"
          icon="cloud_upload"
          :label="$t('profilePhoto.retryUpload')"
          outline
          class="full-width"
          :loading="uploading"
          @click="retryUpload"
        />
      </div>

      <!-- Instructions Card -->
      <q-card>
        <q-card-section>
          <h6 class="text-h6 q-mb-md">{{ $t('profilePhoto.instructions') }}</h6>
          <q-list>
            <q-item>
              <q-item-section avatar>
                <q-icon name="face" color="primary" />
              </q-item-section>
              <q-item-section>
                <q-item-label class="text-body2">
                  {{ $t('profilePhoto.instruction1') }}
                </q-item-label>
              </q-item-section>
            </q-item>

            <q-item>
              <q-item-section avatar>
                <q-icon name="wb_sunny" color="primary" />
              </q-item-section>
              <q-item-section>
                <q-item-label class="text-body2">
                  {{ $t('profilePhoto.instruction2') }}
                </q-item-label>
              </q-item-section>
            </q-item>

            <q-item>
              <q-item-section avatar>
                <q-icon name="crop" color="primary" />
              </q-item-section>
              <q-item-section>
                <q-item-label class="text-body2">
                  {{ $t('profilePhoto.instruction3') }}
                </q-item-label>
              </q-item-section>
            </q-item>

            <q-item>
              <q-item-section avatar>
                <q-icon name="security" color="primary" />
              </q-item-section>
              <q-item-section>
                <q-item-label class="text-body2">
                  {{ $t('profilePhoto.instruction4') }}
                </q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
        </q-card-section>
      </q-card>

      <!-- Upload Progress -->
      <q-dialog v-model="showUploadProgress">
        <q-card style="min-width: 300px">
          <q-card-section>
            <h6 class="text-h6">{{ $t('profilePhoto.uploading') }}</h6>
          </q-card-section>

          <q-card-section>
            <q-linear-progress
              :value="uploadProgress / 100"
              color="primary"
              size="20px"
              class="q-mb-md"
            />
            <p class="text-center">{{ uploadProgress }}%</p>
          </q-card-section>
        </q-card>
      </q-dialog>
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'
import ErrorBoundary from '@/components/ErrorBoundary.vue'
import CameraCapture from '@/components/CameraCapture.vue'
import { useProfilePhoto } from '@/composables/useProfilePhoto'
import { useDatabase } from '@/composables/useDatabase'

const $q = useQuasar()
const { t } = useI18n()
const { currentUser } = useDatabase()
const {
  uploading,
  uploadProgress,
  savePhotoToDatabase,
  uploadPhotoToServer,
  getUserProfilePhoto,
  deleteProfilePhoto,
  validatePhotoQuality,
  isPhotoRecent: checkPhotoRecent,
} = useProfilePhoto()

const showCamera = ref(false)
const currentPhoto = ref(null)
const showUploadProgress = ref(false)

const isPhotoRecent = computed(() => {
  return currentPhoto.value ? checkPhotoRecent(currentPhoto.value.timestamp) : false
})

const hasPendingUpload = computed(() => {
  return currentPhoto.value?.syncStatus === 'pending' || currentPhoto.value?.syncStatus === 'failed'
})

const startCamera = () => {
  // Check camera permissions first
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    $q.notify({
      message: t('profilePhoto.cameraNotSupported'),
      type: 'negative',
      position: 'top',
    })
    return
  }

  showCamera.value = true
}

const handleCameraCancel = () => {
  showCamera.value = false
}

const handlePhotoCaptured = async photoData => {
  showCamera.value = false

  try {
    // Validate photo quality
    const validation = validatePhotoQuality(photoData)
    if (!validation.isValid) {
      $q.notify({
        message: `Photo quality issues: ${validation.issues.join(', ')}`,
        type: 'warning',
        position: 'top',
      })
    }

    // Save to local database
    const savedPhoto = await savePhotoToDatabase(photoData)
    currentPhoto.value = savedPhoto

    $q.notify({
      message: t('profilePhoto.photoSaved'),
      type: 'positive',
      position: 'top',
    })

    // Upload to server
    showUploadProgress.value = true
    try {
      await uploadPhotoToServer(photoData)
      $q.notify({
        message: t('profilePhoto.uploadSuccess'),
        type: 'positive',
        position: 'top',
      })
    } catch (uploadError) {
      console.error('Upload failed:', uploadError)
      $q.notify({
        message: t('profilePhoto.uploadFailed'),
        type: 'warning',
        position: 'top',
      })
    } finally {
      showUploadProgress.value = false
    }
  } catch (error) {
    console.error('Failed to save photo:', error)
    $q.notify({
      message: t('profilePhoto.saveFailed'),
      type: 'negative',
      position: 'top',
    })
  }
}

const confirmDeletePhoto = () => {
  $q.dialog({
    title: t('profilePhoto.confirmDelete'),
    message: t('profilePhoto.deleteWarning'),
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    try {
      await deleteProfilePhoto()
      currentPhoto.value = null
      $q.notify({
        message: t('profilePhoto.deleteSuccess'),
        type: 'positive',
        position: 'top',
      })
    } catch (error) {
      console.error('Failed to delete photo:', error)
      $q.notify({
        message: t('profilePhoto.deleteFailed'),
        type: 'negative',
        position: 'top',
      })
    }
  })
}

const retryUpload = async () => {
  if (!currentPhoto.value) return

  try {
    // Convert stored data back to proper format
    const photoData = {
      blob: base64ToBlob(currentPhoto.value.imageData, 'image/jpeg'),
      dataUrl: currentPhoto.value.dataUrl,
      width: currentPhoto.value.width,
      height: currentPhoto.value.height,
      timestamp: currentPhoto.value.timestamp,
      metadata: currentPhoto.value.metadata,
    }

    showUploadProgress.value = true
    await uploadPhotoToServer(photoData)

    // Refresh current photo data
    currentPhoto.value = await getUserProfilePhoto()

    $q.notify({
      message: t('profilePhoto.uploadSuccess'),
      type: 'positive',
      position: 'top',
    })
  } catch (error) {
    console.error('Retry upload failed:', error)
    $q.notify({
      message: t('profilePhoto.uploadFailed'),
      type: 'negative',
      position: 'top',
    })
  } finally {
    showUploadProgress.value = false
  }
}

const base64ToBlob = (base64Data, contentType) => {
  const base64 = base64Data.split(',')[1]
  const byteCharacters = atob(base64)
  const byteNumbers = new Array(byteCharacters.length)

  for (let i = 0; i < byteCharacters.length; i++) {
    byteNumbers[i] = byteCharacters.charCodeAt(i)
  }

  const byteArray = new Uint8Array(byteNumbers)
  return new Blob([byteArray], { type: contentType })
}

const formatDate = timestamp => {
  return new Date(timestamp).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

const loadCurrentPhoto = async () => {
  try {
    if (currentUser.value) {
      currentPhoto.value = await getUserProfilePhoto()
    }
  } catch (error) {
    console.error('Failed to load current photo:', error)
  }
}

const handleCameraError = (error: Error, errorInfo: any) => {
  console.error('Camera error:', error, errorInfo)
  showCamera.value = false

  // Show user-friendly error message based on error type
  let message = t('camera.error', { defaultValue: 'Camera error occurred. Please try again.' })

  if (error.message.includes('permission') || error.message.includes('denied')) {
    message = 'Camera permission was denied. Please check your browser settings and try again.'
  } else if (error.message.includes('MediaPipe') || error.message.includes('face_detection')) {
    message = 'Face detection failed. You can still take photos without face detection.'
  } else if (error.message.includes('getUserMedia')) {
    message =
      'Camera access failed. Please ensure your camera is connected and not in use by another application.'
  }

  $q.notify({
    message,
    type: 'negative',
    position: 'top',
    timeout: 5000,
  })
}

onMounted(() => {
  loadCurrentPhoto()
})
</script>

<style scoped>
.current-photo-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 220px;
}

.passport-photo-preview {
  border: 3px solid #e0e0e0;
  border-radius: 8px;
}

.passport-photo-preview img {
  object-fit: cover;
  width: 100%;
  height: 100%;
}

.no-photo-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  border: 2px dashed #e0e0e0;
  border-radius: 8px;
  min-height: 200px;
}

.photo-info {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.action-buttons {
  max-width: 400px;
  margin: 0 auto;
}

@media (max-width: 599px) {
  .passport-photo-preview {
    width: 150px !important;
    height: 150px !important;
  }
}
</style>
