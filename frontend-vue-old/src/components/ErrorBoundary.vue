<template>
  <div class="error-boundary">
    <slot v-if="!hasError" />

    <!-- Error State -->
    <div v-else class="error-state">
      <q-card class="error-card">
        <q-card-section class="text-center q-pa-xl">
          <q-icon name="error_outline" size="4rem" color="negative" class="q-mb-md" />

          <h5 class="text-h5 q-mb-sm text-negative">
            {{ errorTitle }}
          </h5>

          <p class="text-body1 text-grey-7 q-mb-lg">
            {{ errorMessage }}
          </p>

          <!-- Error Details (Development Only) -->
          <q-expansion-item
            v-if="isDevelopment && errorDetails"
            icon="bug_report"
            label="Error Details"
            class="error-details q-mb-md"
          >
            <q-card flat bordered class="q-pa-md">
              <pre class="error-stack">{{ errorDetails }}</pre>
            </q-card>
          </q-expansion-item>

          <!-- Action Buttons -->
          <div class="row justify-center q-gutter-sm">
            <q-btn
              color="primary"
              outline
              icon="refresh"
              :label="$t('errorBoundary.retry')"
              @click="retry"
            />

            <q-btn
              v-if="canGoBack"
              color="negative"
              flat
              icon="arrow_back"
              :label="$t('errorBoundary.goBack')"
              @click="goBack"
            />

            <q-btn
              v-if="showReportButton"
              color="warning"
              flat
              icon="bug_report"
              :label="$t('errorBoundary.reportBug')"
              @click="reportError"
            />
          </div>
        </q-card-section>
      </q-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onErrorCaptured, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { isDevelopment } from '@/config/env'
import type { ComponentErrorInfo, ErrorDetails, VueComponentInstance } from '@/types/errors'

// Props
interface Props {
  fallbackTitle?: string
  fallbackMessage?: string
  showReportButton?: boolean
  canGoBack?: boolean
  resetOnRouteChange?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  fallbackTitle: 'Something went wrong',
  fallbackMessage: 'An unexpected error occurred. Please try refreshing the page.',
  showReportButton: false,
  canGoBack: true,
  resetOnRouteChange: true,
})

// Emits
const emit = defineEmits<{
  error: [error: Error, errorInfo: ComponentErrorInfo]
  retry: []
  reportError: [error: Error, errorInfo: ComponentErrorInfo]
}>()

// Composables
const router = useRouter()
const $q = useQuasar()

// State
const hasError = ref(false)
const error = ref<Error | null>(null)
const errorInfo = ref<ComponentErrorInfo | null>(null)
const retryCount = ref(0)
const maxRetries = 3

// Computed
const errorTitle = computed(() => {
  if (error.value && isDevelopment) {
    return error.value.name || 'Error'
  }
  return props.fallbackTitle
})

const errorMessage = computed(() => {
  if (error.value) {
    // In development, show actual error message
    if (isDevelopment) {
      return error.value.message || props.fallbackMessage
    }

    // In production, show user-friendly messages based on error type
    if (error.value.name === 'NetworkError' || error.value.message.includes('fetch')) {
      return 'Network connection problem. Please check your internet connection.'
    }

    if (error.value.name === 'ChunkLoadError') {
      return 'Failed to load application resources. Please refresh the page.'
    }

    if (error.value.message.includes('permission') || error.value.message.includes('denied')) {
      return 'Permission denied. Please check your browser settings.'
    }

    // Generic message for production
    return props.fallbackMessage
  }

  return props.fallbackMessage
})

const errorDetails = computed((): ErrorDetails | null => {
  if (!error.value || !isDevelopment) return null

  return {
    name: error.value.name,
    message: error.value.message,
    stack: error.value.stack,
    component: errorInfo.value?.componentName || 'Unknown',
    props: errorInfo.value?.propsData || {},
    retryCount: retryCount.value,
  }
})

// Error Boundary Implementation
onErrorCaptured((err: Error, instance: VueComponentInstance | null, info: string) => {
  console.error('Error Boundary caught error:', err)
  console.error('Component instance:', instance)
  console.error('Error info:', info)

  // Set error state
  hasError.value = true
  error.value = err
  errorInfo.value = {
    componentName: instance?.$options.name || instance?.$options.__name || 'Unknown',
    propsData: instance?.$props || {},
    errorInfo: info,
  }

  // Emit error event
  emit('error', err, errorInfo.value)

  // Report error to monitoring service if enabled
  reportToMonitoring(err, errorInfo.value)

  // Prevent error from propagating
  return false
})

// Watch route changes to reset error state
if (props.resetOnRouteChange) {
  watch(
    () => router.currentRoute.value.path,
    () => {
      if (hasError.value) {
        resetError()
      }
    }
  )
}

// Methods
const retry = () => {
  if (retryCount.value >= maxRetries) {
    $q.notify({
      message: `Maximum retry attempts (${maxRetries}) reached. Please refresh the page.`,
      type: 'warning',
      timeout: 5000,
    })
    return
  }

  retryCount.value++
  resetError()
  emit('retry')

  $q.notify({
    message: 'Retrying...',
    type: 'info',
    timeout: 1000,
  })
}

const resetError = () => {
  hasError.value = false
  error.value = null
  errorInfo.value = null
}

const goBack = () => {
  if (window.history.length > 1) {
    router.go(-1)
  } else {
    router.push('/')
  }
}

const reportError = () => {
  if (error.value) {
    emit('reportError', error.value, errorInfo.value)

    // Show confirmation
    $q.notify({
      message: 'Error report sent. Thank you for helping us improve!',
      type: 'positive',
      timeout: 3000,
    })
  }
}

const reportToMonitoring = (error: Error, errorInfo: ComponentErrorInfo) => {
  // In a real app, you would send this to your monitoring service
  // e.g., Sentry, Bugsnag, LogRocket, etc.
  if (isDevelopment) {
    console.warn('Error boundary would report to monitoring:', { error, errorInfo })
  }
}

// Global error handler for uncaught promises
onMounted(() => {
  const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
    console.error('Unhandled promise rejection:', event.reason)

    // Convert to Error if not already
    const error = event.reason instanceof Error ? event.reason : new Error(String(event.reason))

    // Trigger error boundary
    hasError.value = true
    error.value = error
    errorInfo.value = {
      componentName: 'Global',
      propsData: {},
      errorInfo: `unhandled-promise-rejection: ${String(event.reason)}`,
    }

    emit('error', error, errorInfo.value)
    reportToMonitoring(error, errorInfo.value)
  }

  window.addEventListener('unhandledrejection', handleUnhandledRejection)

  // Cleanup on unmount
  return () => {
    window.removeEventListener('unhandledrejection', handleUnhandledRejection)
  }
})
</script>

<script lang="ts">
export default {
  name: 'ErrorBoundary',
}
</script>

<style scoped>
.error-boundary {
  width: 100%;
  height: 100%;
}

.error-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 50vh;
  padding: 1rem;
}

.error-card {
  max-width: 600px;
  width: 100%;
}

.error-details {
  text-align: left;
}

.error-stack {
  font-family: 'Courier New', monospace;
  font-size: 0.8rem;
  white-space: pre-wrap;
  word-break: break-word;
  background-color: #f5f5f5;
  padding: 1rem;
  border-radius: 4px;
  max-height: 300px;
  overflow-y: auto;
}

@media (max-width: 600px) {
  .error-state {
    min-height: 40vh;
    padding: 0.5rem;
  }

  .error-card {
    margin: 0;
  }
}
</style>
