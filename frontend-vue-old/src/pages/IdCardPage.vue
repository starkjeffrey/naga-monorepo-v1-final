<template>
  <q-page class="id-card-page">
    <!-- Header -->
    <div class="q-pa-md">
      <div class="q-mb-lg">
        <h4 class="text-h4 q-mb-xs text-weight-medium">
          {{ $t('idCard.title') }}
        </h4>
        <p class="text-subtitle1 text-grey-6">
          {{ $t('idCard.subtitle') }}
        </p>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="text-center q-pa-xl">
      <q-spinner-cube size="60px" color="primary" class="q-mb-md" />
      <p class="text-body2 text-grey-6">{{ $t('idCard.loading') }}</p>
    </div>

    <!-- Error State -->
    <div v-else-if="validationIssues.length > 0" class="q-pa-md">
      <q-card class="bg-warning text-white">
        <q-card-section>
          <h6 class="text-h6 q-mb-md">{{ $t('idCard.incompleteInfo') }}</h6>
          <q-list>
            <q-item v-for="issue in validationIssues" :key="issue">
              <q-item-section avatar>
                <q-icon name="warning" />
              </q-item-section>
              <q-item-section>
                <q-item-label>{{ issue }}</q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
        </q-card-section>
        <q-card-actions>
          <q-btn
            flat
            icon="person"
            :label="$t('idCard.updateProfile')"
            @click="$router.push('/profile')"
          />
          <q-btn
            flat
            icon="camera_alt"
            :label="$t('idCard.addPhoto')"
            @click="$router.push('/profile-photo')"
          />
        </q-card-actions>
      </q-card>
    </div>

    <!-- ID Card Display -->
    <div v-else class="id-card-container">
      <!-- Digital ID Card -->
      <div class="id-card">
        <!-- Header -->
        <div class="id-card-header">
          <div class="institution-info">
            <img src="/naga-trans.png" alt="PUCSR Logo" class="institution-logo" />
            <div class="institution-text">
              <h3 class="institution-name">PUCSR</h3>
              <p class="institution-subtitle">{{ $t('idCard.institutionName') }}</p>
            </div>
          </div>
        </div>

        <!-- Student Photo -->
        <div class="photo-section">
          <div class="photo-container">
            <img
              v-if="profilePhoto?.dataUrl"
              :src="profilePhoto.dataUrl"
              alt="Student Photo"
              class="student-photo"
            />
            <div v-else class="no-photo">
              <q-icon name="person" size="80px" color="grey-4" />
            </div>
          </div>
        </div>

        <!-- Student Information -->
        <div class="student-info">
          <h2 class="student-name">{{ studentInfo?.fullName || 'Student Name' }}</h2>

          <div class="info-grid">
            <div class="info-item">
              <span class="info-label">{{ $t('idCard.studyLevel') }}</span>
              <span class="info-value study-level">{{
                getStudyLevelDisplay(studentInfo?.studyLevel)
              }}</span>
            </div>

            <div class="info-item">
              <span class="info-label">{{ $t('idCard.department') }}</span>
              <span class="info-value">{{ studentInfo?.department }}</span>
            </div>

            <div class="info-item">
              <span class="info-label">{{ $t('idCard.academicYear') }}</span>
              <span class="info-value">{{ studentInfo?.academicYear }}</span>
            </div>
          </div>
        </div>

        <!-- ID and Email Section -->
        <div class="id-email-section">
          <!-- User ID (Student/Teacher/Both) -->
          <div v-if="getUserIdDisplay().showBoth" class="dual-id-display">
            <div class="id-line-primary">
              <span class="id-label">{{ $t('idCard.studentId') }}</span>
              <span class="id-value">{{ getUserIdDisplay().studentId }}</span>
            </div>
            <div class="id-line-primary">
              <span class="id-label">{{ $t('idCard.teacherId') }}</span>
              <span class="id-value">{{ getUserIdDisplay().teacherId }}</span>
            </div>
          </div>

          <!-- Single ID Display -->
          <div v-else class="single-id-display">
            <div class="id-line-primary">
              <span class="id-label">{{
                getUserIdDisplay().teacherId ? $t('idCard.teacherId') : $t('idCard.studentId')
              }}</span>
              <span class="id-value">{{
                getUserIdDisplay().teacherId || getUserIdDisplay().studentId
              }}</span>
            </div>
          </div>

          <!-- School Email -->
          <div v-if="studentInfo?.schoolEmail" class="email-display">
            <span class="email-label">{{ $t('idCard.schoolEmail') }}</span>
            <span class="email-value">{{ studentInfo.schoolEmail }}</span>
          </div>
        </div>

        <!-- QR Code Section -->
        <div class="qr-section">
          <div class="qr-container">
            <img v-if="qrCodeDataUrl" :src="qrCodeDataUrl" alt="QR Code" class="qr-code" />
            <div v-else class="qr-placeholder">
              <q-icon name="qr_code" size="60px" color="grey-4" />
            </div>
          </div>
          <p class="qr-instructions">{{ $t('idCard.qrInstructions') }}</p>
        </div>

        <!-- Footer -->
        <div class="id-card-footer">
          <p class="validity-info">{{ $t('idCard.validFor') }} {{ studentInfo?.academicYear }}</p>
          <p class="issued-date">{{ $t('idCard.issued') }}: {{ formatDate(new Date()) }}</p>
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="action-buttons q-pa-md">
        <q-btn
          color="primary"
          icon="refresh"
          :label="$t('idCard.refresh')"
          class="full-width q-mb-md"
          :loading="loading"
          @click="refreshCard"
        />

        <q-btn
          color="grey-7"
          icon="brightness_6"
          :label="$t('idCard.adjustBrightness')"
          outline
          class="full-width q-mb-md"
          @click="adjustBrightness"
        />

        <q-btn
          color="indigo"
          icon="fullscreen"
          :label="$t('idCard.fullscreen')"
          outline
          class="full-width"
          @click="toggleFullscreen"
        />
      </div>
    </div>
  </q-page>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useQuasar } from 'quasar'
import { useIdCard } from '@/composables/useIdCard'

const $q = useQuasar()
const {
  loading,
  studentInfo,
  profilePhoto,
  qrCodeDataUrl,
  generateIdCard,
  refreshIdCard,
  validateIdCard,
  getStudyLevelDisplay,
  getUserIdDisplay,
} = useIdCard()

const screenBrightness = ref(100)

const validationIssues = computed(() => {
  const validation = validateIdCard()
  return validation.issues
})

const refreshCard = async () => {
  try {
    await refreshIdCard()
    $q.notify({
      message: 'ID Card refreshed successfully',
      type: 'positive',
      position: 'top',
    })
  } catch {
    $q.notify({
      message: 'Failed to refresh ID card',
      type: 'negative',
      position: 'top',
    })
  }
}

const adjustBrightness = () => {
  // Cycle through brightness levels: 100% -> 80% -> 60% -> 100%
  if (screenBrightness.value === 100) {
    screenBrightness.value = 80
  } else if (screenBrightness.value === 80) {
    screenBrightness.value = 60
  } else {
    screenBrightness.value = 100
  }

  // Apply brightness filter to the ID card
  const idCard = document.querySelector('.id-card')
  if (idCard) {
    idCard.style.filter = `brightness(${screenBrightness.value}%)`
  }

  $q.notify({
    message: `Brightness set to ${screenBrightness.value}%`,
    type: 'info',
    position: 'bottom',
  })
}

const toggleFullscreen = () => {
  const idCard = document.querySelector('.id-card-container')
  if (!idCard) return

  if (!document.fullscreenElement) {
    void (
      idCard.requestFullscreen?.() ||
      idCard.webkitRequestFullscreen?.() ||
      idCard.msRequestFullscreen?.()
    )
  } else {
    void (
      document.exitFullscreen?.() ||
      document.webkitExitFullscreen?.() ||
      document.msExitFullscreen?.()
    )
  }
}

const formatDate = date => {
  return date.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

onMounted(async () => {
  try {
    await generateIdCard()
  } catch (error) {
    console.error('Failed to generate ID card:', error)
  }
})
</script>

<style scoped>
.id-card-page {
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  min-height: 100vh;
}

.id-card-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
}

.id-card {
  width: 100%;
  max-width: 400px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 20px;
  padding: 20px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
  color: white;
  position: relative;
  overflow: hidden;
}

.id-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="20" cy="20" r="2" fill="rgba(255,255,255,0.1)"/><circle cx="80" cy="30" r="1" fill="rgba(255,255,255,0.1)"/><circle cx="40" cy="70" r="1.5" fill="rgba(255,255,255,0.1)"/></svg>');
  pointer-events: none;
}

.id-card-header {
  display: flex;
  justify-content: center;
  margin-bottom: 20px;
  position: relative;
  z-index: 1;
}

.institution-info {
  display: flex;
  align-items: center;
  gap: 15px;
}

.institution-logo {
  width: 50px;
  height: 50px;
  object-fit: contain;
}

.institution-name {
  font-size: 1.8rem;
  font-weight: bold;
  margin: 0;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
}

.institution-subtitle {
  font-size: 0.9rem;
  margin: 0;
  opacity: 0.9;
}

.photo-section {
  display: flex;
  justify-content: center;
  margin-bottom: 20px;
  position: relative;
  z-index: 1;
}

.photo-container {
  width: 120px;
  height: 120px;
  border-radius: 15px;
  overflow: hidden;
  border: 4px solid rgba(255, 255, 255, 0.3);
  background: rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
}

.student-photo {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.no-photo {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
}

.student-info {
  text-align: center;
  margin-bottom: 20px;
  position: relative;
  z-index: 1;
}

.student-name {
  font-size: 1.4rem;
  font-weight: bold;
  margin: 0 0 15px 0;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
  line-height: 1.2;
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 15px;
}

.info-item {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 8px;
  backdrop-filter: blur(10px);
}

.info-item-full-width {
  grid-column: 1 / -1;
}

.dual-ids {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.id-line {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.id-type {
  font-size: 0.75rem;
  opacity: 0.9;
  margin-right: 8px;
}

.info-email {
  font-size: 0.7rem;
  word-break: break-all;
}

/* ID and Email Section */
.id-email-section {
  background: rgba(255, 255, 255, 0.15);
  border-radius: 15px;
  padding: 15px;
  margin: 15px 0;
  backdrop-filter: blur(15px);
  border: 2px solid rgba(255, 255, 255, 0.2);
  position: relative;
  z-index: 1;
}

.dual-id-display,
.single-id-display {
  margin-bottom: 10px;
}

.id-line-primary {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 8px;
}

.id-line-primary:last-child {
  margin-bottom: 0;
}

.id-label {
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #ffd700;
}

.id-value {
  font-size: 1rem;
  font-weight: bold;
  font-family: monospace;
  letter-spacing: 1px;
}

.email-display {
  text-align: center;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.2);
}

.email-label {
  display: block;
  font-size: 0.7rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 4px;
  opacity: 0.9;
}

.email-value {
  font-size: 0.9rem;
  font-weight: 600;
  word-break: break-all;
  color: #e8f4fd;
}

.info-label {
  display: block;
  font-size: 0.7rem;
  opacity: 0.8;
  margin-bottom: 2px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.info-value {
  display: block;
  font-size: 0.9rem;
  font-weight: bold;
  word-break: break-word;
}

.study-level {
  color: #ffd700;
  font-size: 1rem;
}

.qr-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 15px;
  position: relative;
  z-index: 1;
}

.qr-container {
  background: white;
  border-radius: 10px;
  padding: 10px;
  margin-bottom: 10px;
}

.qr-code {
  width: 100px;
  height: 100px;
  display: block;
}

.qr-placeholder {
  width: 100px;
  height: 100px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.qr-instructions {
  font-size: 0.7rem;
  text-align: center;
  opacity: 0.8;
  margin: 0;
}

.id-card-footer {
  text-align: center;
  font-size: 0.7rem;
  opacity: 0.8;
  position: relative;
  z-index: 1;
}

.validity-info {
  margin: 0 0 5px 0;
  font-weight: bold;
}

.issued-date {
  margin: 0;
}

.action-buttons {
  width: 100%;
  max-width: 400px;
}

/* Fullscreen styles */
.id-card-container:-webkit-full-screen .id-card {
  max-width: 600px;
  transform: scale(1.2);
}

.id-card-container:-moz-full-screen .id-card {
  max-width: 600px;
  transform: scale(1.2);
}

.id-card-container:fullscreen .id-card {
  max-width: 600px;
  transform: scale(1.2);
}

/* Mobile optimizations */
@media (max-width: 599px) {
  .id-card {
    max-width: 350px;
    padding: 15px;
  }

  .student-name {
    font-size: 1.2rem;
  }

  .institution-name {
    font-size: 1.5rem;
  }

  .photo-container {
    width: 100px;
    height: 100px;
  }

  .qr-code {
    width: 80px;
    height: 80px;
  }

  .info-grid {
    grid-template-columns: 1fr;
    gap: 8px;
  }

  .id-email-section {
    padding: 12px;
    margin: 12px 0;
  }

  .id-value {
    font-size: 0.9rem;
  }

  .email-value {
    font-size: 0.8rem;
  }
}

/* Dark mode support */
.body--dark .id-card-page {
  background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
}
</style>
