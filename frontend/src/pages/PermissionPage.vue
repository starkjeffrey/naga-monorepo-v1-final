<template>
  <q-page class="q-pa-md">
    <div class="q-mb-lg">
      <h4 class="text-h4 q-mb-xs text-weight-medium">
        {{ $t('permission.title') }}
      </h4>
      <p class="text-subtitle1 text-grey-6">
        {{ $t('permission.subtitle') }}
      </p>
    </div>

    <q-card>
      <q-card-section>
        <q-form class="q-gutter-md" @submit="onSubmit" @reset="onReset">
          <!-- Class Selection -->
          <q-select
            v-model="form.classId"
            :options="classOptions"
            :label="$t('permission.class.label')"
            :rules="[val => !!val || $t('permission.class.required')]"
            outlined
            emit-value
            map-options
            :hint="$t('permission.class.hint')"
          >
            <template #prepend>
              <q-icon name="class" />
            </template>
          </q-select>

          <!-- Date of Absence -->
          <q-input
            v-model="form.date"
            :label="$t('permission.date.label')"
            :rules="[val => !!val || $t('permission.date.required'), validateDate]"
            outlined
            type="date"
            :min="today"
            :hint="$t('permission.date.hint')"
          >
            <template #prepend>
              <q-icon name="event" />
            </template>
          </q-input>

          <!-- Reason for Absence -->
          <q-select
            v-model="form.reason"
            :options="reasonOptions"
            :label="$t('permission.reason.label')"
            :rules="[val => !!val || $t('permission.reason.required')]"
            outlined
            emit-value
            map-options
            :hint="$t('permission.reason.hint')"
          >
            <template #prepend>
              <q-icon name="help_outline" />
            </template>
          </q-select>

          <!-- Additional Details -->
          <q-input
            v-model="form.details"
            :label="$t('permission.details.label')"
            :rules="[
              val => !!val || $t('permission.details.required'),
              val => val.length >= 10 || $t('permission.details.minLength'),
            ]"
            outlined
            type="textarea"
            rows="4"
            :hint="$t('permission.details.hint', { count: form.details.length })"
            counter
            maxlength="500"
          >
            <template #prepend>
              <q-icon name="notes" />
            </template>
          </q-input>

          <!-- Document Upload -->
          <div class="q-mb-md">
            <q-checkbox
              v-model="form.hasDocument"
              :label="$t('permission.document.checkbox')"
              color="primary"
            />
            <div v-if="form.hasDocument" class="q-mt-sm">
              <q-file
                v-model="form.documentFile"
                :label="$t('permission.document.label')"
                outlined
                accept=".pdf,.jpg,.jpeg,.png"
                max-file-size="5242880"
                :hint="$t('permission.document.hint')"
                @rejected="onDocumentRejected"
              >
                <template #prepend>
                  <q-icon name="attach_file" />
                </template>
              </q-file>
            </div>
          </div>

          <!-- Form Actions -->
          <div class="row q-gutter-sm">
            <q-btn
              :label="$t('permission.submit')"
              type="submit"
              color="primary"
              :loading="submitting"
              :disable="submitting"
              class="col"
            />
            <q-btn
              :label="$t('permission.reset')"
              type="reset"
              color="grey"
              flat
              :disable="submitting"
            />
          </div>
        </q-form>
      </q-card-section>
    </q-card>

    <!-- Recent Requests -->
    <q-card v-if="recentRequests.length > 0" class="q-mt-md">
      <q-card-section>
        <h6 class="text-h6 q-mb-md">{{ $t('permission.recent.title') }}</h6>
        <q-list separator>
          <q-item v-for="request in recentRequests" :key="request.id">
            <q-item-section>
              <q-item-label>{{ request.className || request.classCode }}</q-item-label>
              <q-item-label caption
                >{{ formatDate(request.date) }} •
                {{ $t(`permission.reasons.${request.reason}`) }}</q-item-label
              >
            </q-item-section>
            <q-item-section side>
              <q-badge
                :color="getStatusColor(request.status)"
                :label="$t(`permission.status.${request.status}`)"
              />
            </q-item-section>
          </q-item>
        </q-list>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useQuasar, date } from 'quasar'
import { useI18n } from 'vue-i18n'
import { useDatabase } from '@/composables/useDatabase'

const $q = useQuasar()
const { t } = useI18n()
const { makeApiRequest } = useDatabase()

// Form data
const form = ref({
  classId: '',
  date: '',
  reason: '',
  details: '',
  hasDocument: false,
  documentFile: null,
})

// Form state
const submitting = ref(false)
const recentRequests = ref([])

// Computed
const today = computed(() => date.formatDate(new Date(), 'YYYY-MM-DD'))

// Mock student's enrolled classes - in production this would come from API
const classOptions = computed(() => [
  { label: 'CS101 - Computer Science 101', value: 'cs101', code: 'CS101' },
  { label: 'DB202 - Database Systems', value: 'db202', code: 'DB202' },
  { label: 'WEB301 - Web Development', value: 'web301', code: 'WEB301' },
  { label: 'SE401 - Software Engineering', value: 'se401', code: 'SE401' },
])

const reasonOptions = computed(() => [
  { label: t('permission.reasons.sick'), value: 'sick' },
  { label: t('permission.reasons.family'), value: 'family' },
  { label: t('permission.reasons.religious'), value: 'religious' },
  { label: t('permission.reasons.transport'), value: 'transport' },
  { label: t('permission.reasons.work'), value: 'work' },
  { label: t('permission.reasons.other'), value: 'other' },
])

const selectedClassName = computed(() => {
  const classOption = classOptions.value.find(c => c.value === form.value.classId)
  return classOption ? classOption.label : ''
})

// Validation
const validateDate = val => {
  if (!val) return true
  const selectedDate = new Date(val)
  const currentDate = new Date()
  currentDate.setHours(0, 0, 0, 0)

  if (selectedDate < currentDate) {
    return t('permission.date.pastDate')
  }
  return true
}

// Methods
const onSubmit = async () => {
  submitting.value = true

  try {
    const classOption = classOptions.value.find(c => c.value === form.value.classId)
    const payload = {
      classId: form.value.classId,
      className: classOption ? classOption.label : '',
      classCode: classOption ? classOption.code : '',
      date: form.value.date,
      reason: form.value.reason,
      details: form.value.details,
      hasDocument: form.value.hasDocument,
      timestamp: new Date().toISOString(),
    }

    // Handle file upload if document is provided
    if (form.value.hasDocument && form.value.documentFile) {
      // In a real implementation, you would upload the file here
      payload.documentName = form.value.documentFile.name
      payload.documentSize = form.value.documentFile.size
    }

    // Queue for offline sync if needed
    await queuePermissionRequest(payload)

    // Try to submit immediately
    await submitPermissionRequest(payload)

    $q.notify({
      type: 'positive',
      message: t('permission.success'),
      position: 'top',
    })

    onReset()
    loadRecentRequests()
  } catch (error) {
    console.error('Permission request error:', error)
    $q.notify({
      type: 'negative',
      message: t('permission.error'),
      position: 'top',
    })
  } finally {
    submitting.value = false
  }
}

const onReset = () => {
  form.value = {
    classId: '',
    date: '',
    reason: '',
    details: '',
    hasDocument: false,
    documentFile: null,
  }
}

const onDocumentRejected = rejectedEntries => {
  const reasons = rejectedEntries.map(entry => entry.failedPropValidation).join(', ')
  $q.notify({
    type: 'negative',
    message: t('permission.document.rejected', { reasons }),
    position: 'top',
  })
}

const queuePermissionRequest = async payload => {
  try {
    const queue = JSON.parse(localStorage.getItem('permissionQueue') || '[]')
    queue.push({
      ...payload,
      id: Date.now().toString(),
      status: 'pending',
    })
    localStorage.setItem('permissionQueue', JSON.stringify(queue))
  } catch (error) {
    console.error('Error queuing permission request:', error)
  }
}

const submitPermissionRequest = async payload => {
  try {
    // Simulate API call for development
    await new Promise(resolve => setTimeout(resolve, 1000))

    // In production, this would be:
    // await makeApiRequest('/api/student/permission-request/', 'POST', payload)

    console.log('Permission request submitted:', payload)
  } catch (error) {
    throw new Error('Failed to submit permission request')
  }
}

const loadRecentRequests = () => {
  // Load from localStorage for now
  try {
    const queue = JSON.parse(localStorage.getItem('permissionQueue') || '[]')
    recentRequests.value = queue.slice(-5).reverse() // Show last 5 requests
  } catch (error) {
    console.error('Error loading recent requests:', error)
  }
}

const formatDate = dateStr => {
  return date.formatDate(new Date(dateStr), 'MMM DD, YYYY')
}

const getStatusColor = status => {
  switch (status) {
    case 'approved':
      return 'positive'
    case 'denied':
      return 'negative'
    case 'pending':
      return 'warning'
    default:
      return 'grey'
  }
}

onMounted(() => {
  loadRecentRequests()
})
</script>
