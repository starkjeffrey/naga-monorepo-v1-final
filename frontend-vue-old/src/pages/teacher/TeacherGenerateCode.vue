<template>
  <q-page class="q-pa-md">
    <div class="q-mb-lg">
      <h4 class="text-h4 q-mb-xs text-weight-medium">
        {{ $t('teacher.generateCode.title') }}
      </h4>
      <p class="text-subtitle1 text-grey-6">
        {{ $t('teacher.generateCode.subtitle') }}
      </p>
    </div>

    <!-- Code Generation Form -->
    <q-card class="q-mb-lg">
      <q-card-section>
        <h6 class="text-h6 q-mb-md">{{ $t('teacher.generateCode.form.title') }}</h6>

        <q-form class="q-gutter-md" @submit="generateCode">
          <!-- Class Selection -->
          <q-select
            v-model="selectedClass"
            :options="classOptions"
            :label="$t('teacher.generateCode.form.classLabel')"
            :rules="[val => !!val || $t('teacher.generateCode.form.classRequired')]"
            outlined
            emit-value
            map-options
            :hint="$t('teacher.generateCode.form.classHint')"
          >
            <template #prepend>
              <q-icon name="class" />
            </template>
          </q-select>

          <!-- Validity Duration -->
          <q-select
            v-model="validityMinutes"
            :options="durationOptions"
            :label="$t('teacher.generateCode.form.durationLabel')"
            :rules="[val => !!val || $t('teacher.generateCode.form.durationRequired')]"
            outlined
            emit-value
            map-options
            :hint="$t('teacher.generateCode.form.durationHint')"
          >
            <template #prepend>
              <q-icon name="timer" />
            </template>
          </q-select>

          <!-- Generate Button -->
          <div class="row q-gutter-sm">
            <q-btn
              :label="$t('teacher.generateCode.form.generate')"
              type="submit"
              color="primary"
              icon="qr_code"
              :loading="generating"
              :disable="generating || !selectedClass || !validityMinutes"
              class="col"
              size="lg"
            />
          </div>
        </q-form>
      </q-card-section>
    </q-card>

    <!-- Active Code Display -->
    <q-card v-if="activeCode" class="code-display-card q-mb-lg">
      <q-card-section class="text-center">
        <div class="row items-center justify-between q-mb-md">
          <h6 class="text-h6 text-weight-medium">{{ $t('teacher.generateCode.display.title') }}</h6>
          <q-btn flat round icon="close" :aria-label="$t('common.close')" @click="clearCode" />
        </div>

        <!-- Large Code Display -->
        <div class="code-display q-mb-lg">
          <div class="code-text">{{ activeCode.code }}</div>
          <div class="code-meta">
            {{ selectedClassName }} • {{ formatDateTime(activeCode.createdAt) }}
          </div>
        </div>

        <!-- QR Code Placeholder -->
        <div class="qr-placeholder q-mb-lg">
          <q-icon name="qr_code" size="120px" color="grey-5" />
          <div class="text-caption text-grey-6 q-mt-sm">
            {{ $t('teacher.generateCode.display.qrPlaceholder') }}
          </div>
        </div>

        <!-- Timer Display -->
        <div class="timer-section">
          <q-circular-progress
            :value="timeProgress"
            size="80px"
            :thickness="0.15"
            color="primary"
            class="q-mb-sm"
          >
            <div class="text-h6 text-weight-bold">{{ formatTimeRemaining }}</div>
          </q-circular-progress>
          <div class="text-body2 text-grey-6">
            {{ $t('teacher.generateCode.display.timeRemaining') }}
          </div>
          <div class="text-caption q-mt-xs">
            {{
              $t('teacher.generateCode.display.expiresAt', {
                time: formatDateTime(activeCode.expiresAt),
              })
            }}
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="row q-gutter-sm q-mt-lg">
          <q-btn
            :label="$t('teacher.generateCode.display.copyCode')"
            color="secondary"
            icon="content_copy"
            outline
            class="col"
            @click="copyCodeToClipboard"
          />
          <q-btn
            :label="$t('teacher.generateCode.display.newCode')"
            color="primary"
            icon="refresh"
            class="col"
            @click="generateNewCode"
          />
        </div>
      </q-card-section>
    </q-card>

    <!-- Instructions -->
    <q-card>
      <q-card-section>
        <h6 class="text-h6 q-mb-md">{{ $t('teacher.generateCode.instructions.title') }}</h6>
        <q-list>
          <q-item>
            <q-item-section avatar>
              <q-icon name="looks_one" color="primary" />
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ $t('teacher.generateCode.instructions.step1') }}</q-item-label>
            </q-item-section>
          </q-item>
          <q-item>
            <q-item-section avatar>
              <q-icon name="looks_two" color="primary" />
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ $t('teacher.generateCode.instructions.step2') }}</q-item-label>
            </q-item-section>
          </q-item>
          <q-item>
            <q-item-section avatar>
              <q-icon name="looks_3" color="primary" />
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ $t('teacher.generateCode.instructions.step3') }}</q-item-label>
            </q-item-section>
          </q-item>
          <q-item>
            <q-item-section avatar>
              <q-icon name="looks_4" color="primary" />
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ $t('teacher.generateCode.instructions.step4') }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useQuasar, date, copyToClipboard } from 'quasar'
import { useI18n } from 'vue-i18n'

const $q = useQuasar()
const { t } = useI18n()

// Form data
const selectedClass = ref(null)
const validityMinutes = ref(15)
const generating = ref(false)
const activeCode = ref(null)
const timer = ref(null)

// Mock class data - in production this would come from API
const classOptions = computed(() => [
  { label: 'Computer Science 101 - Section A', value: 'cs101a', students: 28 },
  { label: 'Database Systems - Section B', value: 'db202b', students: 32 },
  { label: 'Web Development - Section A', value: 'web301a', students: 25 },
  { label: 'Software Engineering - Section C', value: 'se401c', students: 20 },
])

const durationOptions = computed(() => [
  { label: t('teacher.generateCode.durations.5min'), value: 5 },
  { label: t('teacher.generateCode.durations.10min'), value: 10 },
  { label: t('teacher.generateCode.durations.15min'), value: 15 },
  { label: t('teacher.generateCode.durations.30min'), value: 30 },
  { label: t('teacher.generateCode.durations.60min'), value: 60 },
  { label: t('teacher.generateCode.durations.120min'), value: 120 },
])

// Computed properties
const selectedClassName = computed(() => {
  const classOption = classOptions.value.find(c => c.value === selectedClass.value)
  return classOption ? classOption.label : ''
})

const timeProgress = computed(() => {
  if (!activeCode.value) return 0

  const now = new Date().getTime()
  const created = new Date(activeCode.value.createdAt).getTime()
  const expires = new Date(activeCode.value.expiresAt).getTime()
  const total = expires - created
  const elapsed = now - created

  return Math.max(0, Math.min(100, ((total - elapsed) / total) * 100))
})

const formatTimeRemaining = computed(() => {
  if (!activeCode.value) return '0:00'

  const now = new Date().getTime()
  const expires = new Date(activeCode.value.expiresAt).getTime()
  const remaining = Math.max(0, expires - now)

  const minutes = Math.floor(remaining / 60000)
  const seconds = Math.floor((remaining % 60000) / 1000)

  return `${minutes}:${seconds.toString().padStart(2, '0')}`
})

// Methods
const generateCode = async () => {
  if (!selectedClass.value || !validityMinutes.value) return

  generating.value = true

  try {
    // Generate 6-character alphanumeric code (excluding similar-looking characters)
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    let code = ''
    for (let i = 0; i < 6; i++) {
      code += chars.charAt(Math.floor(Math.random() * chars.length))
    }

    const now = new Date()
    const expiresAt = new Date(now.getTime() + validityMinutes.value * 60000)

    activeCode.value = {
      code,
      classId: selectedClass.value,
      createdAt: now.toISOString(),
      expiresAt: expiresAt.toISOString(),
      validityMinutes: validityMinutes.value,
    }

    // Start countdown timer
    startTimer()

    // In production, this would also send to API:
    // await submitCodeToAPI(activeCode.value)

    $q.notify({
      type: 'positive',
      message: t('teacher.generateCode.success'),
      position: 'top',
    })
  } catch (error) {
    console.error('Error generating code:', error)
    $q.notify({
      type: 'negative',
      message: t('teacher.generateCode.error'),
      position: 'top',
    })
  } finally {
    generating.value = false
  }
}

const generateNewCode = () => {
  clearCode()
  generateCode()
}

const clearCode = () => {
  activeCode.value = null
  if (timer.value) {
    clearInterval(timer.value)
    timer.value = null
  }
}

const startTimer = () => {
  if (timer.value) {
    clearInterval(timer.value)
  }

  timer.value = setInterval(() => {
    if (!activeCode.value) return

    const now = new Date().getTime()
    const expires = new Date(activeCode.value.expiresAt).getTime()

    if (now >= expires) {
      clearCode()
      $q.notify({
        type: 'warning',
        message: t('teacher.generateCode.expired'),
        position: 'top',
      })
    }
  }, 1000)
}

const copyCodeToClipboard = async () => {
  if (!activeCode.value) return

  try {
    await copyToClipboard(activeCode.value.code)
    $q.notify({
      type: 'positive',
      message: t('teacher.generateCode.copied'),
      position: 'top',
    })
  } catch (error) {
    console.error('Failed to copy code:', error)
    $q.notify({
      type: 'negative',
      message: t('teacher.generateCode.copyFailed'),
      position: 'top',
    })
  }
}

const formatDateTime = dateStr => {
  return date.formatDate(new Date(dateStr), 'HH:mm')
}

onMounted(() => {
  // Restore any active code from localStorage for development
  const savedCode = localStorage.getItem('activeAttendanceCode')
  if (savedCode) {
    try {
      const parsed = JSON.parse(savedCode)
      const now = new Date().getTime()
      const expires = new Date(parsed.expiresAt).getTime()

      if (now < expires) {
        activeCode.value = parsed
        selectedClass.value = parsed.classId
        startTimer()
      }
    } catch (error) {
      console.error('Failed to restore active code:', error)
    }
  }
})

onUnmounted(() => {
  if (timer.value) {
    clearInterval(timer.value)
  }

  // Save active code for development
  if (activeCode.value) {
    localStorage.setItem('activeAttendanceCode', JSON.stringify(activeCode.value))
  }
})
</script>

<style scoped>
.code-display-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.code-display {
  padding: 24px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
}

.code-text {
  font-size: 3rem;
  font-weight: bold;
  letter-spacing: 0.5rem;
  margin-bottom: 8px;
  font-family: 'Courier New', monospace;
}

.code-meta {
  font-size: 0.9rem;
  opacity: 0.8;
}

.qr-placeholder {
  padding: 20px;
  border: 2px dashed rgba(255, 255, 255, 0.3);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.05);
}

.timer-section {
  color: white;
}

@media (max-width: 599px) {
  .code-text {
    font-size: 2rem;
    letter-spacing: 0.25rem;
  }
}
</style>
