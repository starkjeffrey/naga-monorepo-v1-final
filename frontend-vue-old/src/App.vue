<template>
  <div class="app-container">
    <error-boundary
      :show-report-button="isDevelopment"
      :reset-on-route-change="true"
      @error="handleGlobalError"
      @report-error="handleErrorReport"
    >
      <router-view />
    </error-boundary>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import ErrorBoundary from '@/components/ErrorBoundary.vue'
import { isDevelopment } from '@/config/env'

import type { ComponentErrorInfo } from '@/types/errors'

// Global error handler for uncaught errors
const handleGlobalError = (error: Error, errorInfo: ComponentErrorInfo) => {
  // Log to console in development
  if (isDevelopment) {
    console.error('Global app error:', error)
    console.error('Error info:', errorInfo)
  }

  // In production, you could send to error monitoring service here
  // e.g., Sentry.captureException(error, { extra: errorInfo })
}

// Handle error reports from error boundary
const handleErrorReport = (error: Error, errorInfo: ComponentErrorInfo) => {
  // In a real app, send error report to backend or monitoring service
  if (isDevelopment) {
    console.info('Error report requested:', { error, errorInfo })
  }
}

// Global unhandled promise rejection handler
onMounted(() => {
  const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
    if (isDevelopment) {
      console.error('Unhandled promise rejection:', event.reason)
    }
    // Prevent default browser handling
    event.preventDefault()
  }

  window.addEventListener('unhandledrejection', handleUnhandledRejection)

  // Cleanup on unmount
  return () => {
    window.removeEventListener('unhandledrejection', handleUnhandledRejection)
  }
})
</script>

<style scoped>
.app-container {
  min-height: 100vh;
  background-color: #f0f0f0;
}

.error-container {
  color: red;
  padding: 20px;
}
</style>
