<template>
  <div class="camera-capture">
    <!-- Camera View -->
    <div v-if="currentStep === 'camera'" class="camera-container">
      <div class="camera-header q-pa-md text-center">
        <h5 class="text-h5 q-mb-sm">{{ $t('camera.title') }}</h5>
        <p class="text-body2 text-grey-6">{{ $t('camera.instructions') }}</p>
      </div>

      <!-- Camera Preview -->
      <div class="camera-preview-container">
        <video ref="videoRef" class="camera-preview" autoplay muted playsinline></video>

        <!-- Face Detection Overlay -->
        <canvas ref="canvasRef" class="face-overlay"></canvas>

        <!-- Passport Photo Guide -->
        <div class="photo-guide">
          <div class="guide-oval"></div>
          <div class="guide-text">
            {{ $t('camera.positionFace') }}
          </div>
        </div>

        <!-- Status Indicators -->
        <div class="status-indicators">
          <q-chip
            :color="faceDetected ? 'positive' : 'negative'"
            text-color="white"
            :icon="faceDetected ? 'face' : 'face_unlock'"
            class="status-chip"
          >
            {{ faceDetected ? $t('camera.faceDetected') : $t('camera.noFace') }}
          </q-chip>

          <q-chip
            v-if="lightingQuality"
            :color="lightingQuality === 'good' ? 'positive' : 'warning'"
            text-color="white"
            :icon="lightingQuality === 'good' ? 'wb_sunny' : 'warning'"
            class="status-chip"
          >
            {{ lightingQuality === 'good' ? $t('camera.goodLighting') : $t('camera.poorLighting') }}
          </q-chip>
        </div>
      </div>

      <!-- Camera Controls -->
      <div class="camera-controls q-pa-md">
        <div class="row justify-center q-gutter-md">
          <q-btn
            color="negative"
            icon="close"
            :label="$t('common.cancel')"
            @click="$emit('cancel')"
          />

          <q-btn
            color="primary"
            icon="camera_alt"
            size="lg"
            :label="$t('camera.takePhoto')"
            :disable="!faceDetected || !isReadyToCapture"
            :loading="capturing"
            @click="capturePhoto"
          />
        </div>
      </div>
    </div>

    <!-- Photo Preview -->
    <div v-else-if="currentStep === 'preview'" class="preview-container">
      <div class="preview-header q-pa-md text-center">
        <h5 class="text-h5 q-mb-sm">{{ $t('camera.reviewPhoto') }}</h5>
        <p class="text-body2 text-grey-6">{{ $t('camera.reviewInstructions') }}</p>
      </div>

      <!-- Cropper Container -->
      <div class="cropper-container">
        <img
          ref="cropperImageRef"
          :src="capturedImageUrl"
          alt="Captured photo"
          class="cropper-image"
        />
      </div>

      <!-- Preview Controls -->
      <div class="preview-controls q-pa-md">
        <div class="row justify-center q-gutter-md">
          <q-btn
            color="negative"
            icon="refresh"
            :label="$t('camera.retake')"
            @click="retakePhoto"
          />

          <q-btn
            color="positive"
            icon="check"
            :label="$t('camera.acceptPhoto')"
            :loading="processing"
            @click="acceptPhoto"
          />
        </div>
      </div>
    </div>

    <!-- Processing -->
    <div v-else-if="currentStep === 'processing'" class="processing-container">
      <div class="text-center q-pa-xl">
        <q-spinner-cube size="60px" color="primary" class="q-mb-md" />
        <h5 class="text-h5 q-mb-sm">{{ $t('camera.processing') }}</h5>
        <p class="text-body2 text-grey-6">{{ $t('camera.processingMessage') }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useQuasar } from 'quasar'
import { FaceDetection } from '@mediapipe/face_detection'
import { Camera } from '@mediapipe/camera_utils'
import Cropper from 'cropperjs'
import { getCdnConfig } from '@/config/env'

defineProps({
  passportSize: {
    type: Boolean,
    default: true,
  },
})

const emit = defineEmits(['photoCaptured', 'cancel'])

const $q = useQuasar()

// Refs
const videoRef = ref(null)
const canvasRef = ref(null)
const cropperImageRef = ref(null)

// State
const currentStep = ref('camera')
const faceDetected = ref(false)
const lightingQuality = ref(null)
const isReadyToCapture = ref(false)
const capturing = ref(false)
const processing = ref(false)
const capturedImageUrl = ref('')

// Camera and detection
let mediaStream = null
let faceDetection = null
let camera = null
let cropper = null

// Passport photo dimensions (2x2 inches at 300 DPI = 600x600 pixels)
const PASSPORT_WIDTH = 600
const PASSPORT_HEIGHT = 600

const initializeCamera = async () => {
  try {
    // Request camera permission
    const constraints = {
      video: {
        width: { ideal: 1280 },
        height: { ideal: 720 },
        facingMode: 'user', // Front-facing camera
        frameRate: { ideal: 30 },
      },
      audio: false,
    }

    mediaStream = await navigator.mediaDevices.getUserMedia(constraints)

    if (videoRef.value) {
      videoRef.value.srcObject = mediaStream

      // Wait for video to load
      await new Promise(resolve => {
        videoRef.value.onloadedmetadata = resolve
      })

      // Initialize face detection
      await initializeFaceDetection()
    }
  } catch {
    $q.notify({
      message: 'Camera access denied. Please allow camera permissions.',
      type: 'negative',
      position: 'top',
    })
  }
}

const initializeFaceDetection = async () => {
  try {
    const cdnConfig = getCdnConfig()
    faceDetection = new FaceDetection({
      locateFile: file => {
        return `${cdnConfig.mediaPipeBaseUrl}/${file}`
      },
    })

    faceDetection.setOptions({
      model: 'short',
      minDetectionConfidence: 0.5,
    })

    faceDetection.onResults(onFaceDetectionResults)

    // Initialize camera for MediaPipe
    if (videoRef.value) {
      camera = new Camera(videoRef.value, {
        onFrame: async () => {
          if (faceDetection && videoRef.value) {
            await faceDetection.send({ image: videoRef.value })
          }
        },
        width: 1280,
        height: 720,
      })

      camera.start()
    }
  } catch {
    // Face detection initialization failed - continue without face detection
  }
}

const onFaceDetectionResults = results => {
  const canvas = canvasRef.value
  const video = videoRef.value

  if (!canvas || !video) return

  const ctx = canvas.getContext('2d')
  canvas.width = video.videoWidth
  canvas.height = video.videoHeight

  // Clear previous drawings
  ctx.clearRect(0, 0, canvas.width, canvas.height)

  if (results.detections && results.detections.length > 0) {
    faceDetected.value = true

    // Check if face is properly positioned
    const detection = results.detections[0]
    const bbox = detection.boundingBox

    // Validate face position and size
    const faceArea = bbox.width * bbox.height
    const totalArea = canvas.width * canvas.height
    const faceRatio = faceArea / totalArea

    // Face should be 15-35% of the frame for passport photos
    const isProperSize = faceRatio > 0.15 && faceRatio < 0.35
    const isCentered = Math.abs(bbox.xCenter - 0.5) < 0.1 && Math.abs(bbox.yCenter - 0.4) < 0.1

    isReadyToCapture.value = isProperSize && isCentered

    // Draw face detection box
    ctx.strokeStyle = isReadyToCapture.value ? '#4CAF50' : '#FF9800'
    ctx.lineWidth = 3
    ctx.strokeRect(
      bbox.xCenter * canvas.width - (bbox.width * canvas.width) / 2,
      bbox.yCenter * canvas.height - (bbox.height * canvas.height) / 2,
      bbox.width * canvas.width,
      bbox.height * canvas.height
    )

    // Check lighting quality
    checkLightingQuality(results)
  } else {
    faceDetected.value = false
    isReadyToCapture.value = false
    lightingQuality.value = null
  }
}

const checkLightingQuality = results => {
  // Simple lighting assessment based on detection confidence
  if (results.detections && results.detections.length > 0) {
    const confidence = results.detections[0].score[0]
    lightingQuality.value = confidence > 0.8 ? 'good' : 'poor'
  }
}

const capturePhoto = async () => {
  if (!videoRef.value || !faceDetected.value) return

  capturing.value = true

  try {
    // Create canvas for capture
    const canvas = document.createElement('canvas')
    const ctx = canvas.getContext('2d')

    // Set canvas size to match video
    canvas.width = videoRef.value.videoWidth
    canvas.height = videoRef.value.videoHeight

    // Draw video frame to canvas
    ctx.drawImage(videoRef.value, 0, 0, canvas.width, canvas.height)

    // Convert to blob
    const blob = await new Promise(resolve => {
      canvas.toBlob(resolve, 'image/jpeg', 0.9)
    })

    // Create object URL for preview
    capturedImageUrl.value = URL.createObjectURL(blob)

    // Move to preview step
    currentStep.value = 'preview'

    // Initialize cropper in next tick
    await nextTick()
    initializeCropper()
  } catch {
    $q.notify({
      message: 'Failed to capture photo. Please try again.',
      type: 'negative',
      position: 'top',
    })
  } finally {
    capturing.value = false
  }
}

const initializeCropper = () => {
  if (cropperImageRef.value && !cropper) {
    cropper = new Cropper(cropperImageRef.value, {
      aspectRatio: 1, // Square for passport photos
      viewMode: 1,
      guides: true,
      center: true,
      highlight: false,
      cropBoxMovable: true,
      cropBoxResizable: true,
      toggleDragModeOnDblclick: false,
      ready() {
        // Auto-crop to face area if possible
        const imageData = cropper.getImageData()
        const cropSize = Math.min(imageData.naturalWidth, imageData.naturalHeight) * 0.8
        const x = (imageData.naturalWidth - cropSize) / 2
        const y = (imageData.naturalHeight - cropSize) / 2

        cropper.setCropBoxData({
          left: x,
          top: y,
          width: cropSize,
          height: cropSize,
        })
      },
    })
  }
}

const retakePhoto = () => {
  // Clean up cropper
  if (cropper) {
    cropper.destroy()
    cropper = null
  }

  // Clean up image URL
  if (capturedImageUrl.value) {
    URL.revokeObjectURL(capturedImageUrl.value)
    capturedImageUrl.value = ''
  }

  // Go back to camera
  currentStep.value = 'camera'
}

const acceptPhoto = async () => {
  if (!cropper) return

  processing.value = true
  currentStep.value = 'processing'

  try {
    // Get cropped canvas
    const croppedCanvas = cropper.getCroppedCanvas({
      width: PASSPORT_WIDTH,
      height: PASSPORT_HEIGHT,
      imageSmoothingEnabled: true,
      imageSmoothingQuality: 'high',
    })

    // Convert to blob
    const blob = await new Promise(resolve => {
      croppedCanvas.toBlob(resolve, 'image/jpeg', 0.9)
    })

    // Create final image data
    const photoData = {
      blob,
      dataUrl: croppedCanvas.toDataURL('image/jpeg', 0.9),
      width: PASSPORT_WIDTH,
      height: PASSPORT_HEIGHT,
      timestamp: new Date().toISOString(),
      metadata: {
        deviceType: 'camera',
        userAgent: navigator.userAgent,
        captureDate: new Date().toISOString(),
      },
    }

    // Emit the captured photo
    emit('photoCaptured', photoData)
  } catch {
    $q.notify({
      message: 'Failed to process photo. Please try again.',
      type: 'negative',
      position: 'top',
    })
    retakePhoto()
  } finally {
    processing.value = false
  }
}

const cleanup = () => {
  // Stop camera
  if (camera) {
    camera.stop()
  }

  // Stop media stream
  if (mediaStream) {
    mediaStream.getTracks().forEach(track => track.stop())
  }

  // Clean up face detection
  if (faceDetection) {
    faceDetection.close()
  }

  // Clean up cropper
  if (cropper) {
    cropper.destroy()
  }

  // Clean up image URL
  if (capturedImageUrl.value) {
    URL.revokeObjectURL(capturedImageUrl.value)
  }
}

onMounted(() => {
  initializeCamera()
})

onUnmounted(() => {
  cleanup()
})
</script>

<style scoped>
.camera-capture {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.camera-container {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.camera-preview-container {
  position: relative;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #000;
  overflow: hidden;
}

.camera-preview {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.face-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.photo-guide {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  pointer-events: none;
}

.guide-oval {
  width: 200px;
  height: 240px;
  border: 2px dashed rgba(255, 255, 255, 0.8);
  border-radius: 50%;
  margin: 0 auto;
}

.guide-text {
  color: white;
  text-align: center;
  margin-top: 10px;
  font-size: 14px;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.8);
}

.status-indicators {
  position: absolute;
  top: 20px;
  left: 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.status-chip {
  font-size: 12px;
}

.camera-controls {
  background: rgba(0, 0, 0, 0.8);
  color: white;
}

.preview-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.cropper-container {
  flex: 1;
  min-height: 0;
}

.cropper-image {
  max-width: 100%;
  max-height: 100%;
}

.preview-controls {
  background: rgba(0, 0, 0, 0.8);
  color: white;
}

.processing-container {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
}

@media (max-width: 599px) {
  .guide-oval {
    width: 150px;
    height: 180px;
  }

  .status-indicators {
    top: 10px;
    left: 10px;
  }
}
</style>
