<template>
  <q-btn
    :loading="loading"
    :disable="disabled"
    color="white"
    text-color="dark"
    class="full-width google-sign-in-btn"
    size="lg"
    @click="handleSignIn"
  >
    <template #loading>
      <q-spinner-dots />
      <span class="q-ml-sm">{{ $t('auth.signingIn') || 'Signing in...' }}</span>
    </template>

    <div v-if="!loading" class="row items-center justify-center no-wrap">
      <q-icon name="img:/icons/google.svg" size="20px" class="q-mr-sm google-icon" />
      <span class="text-weight-medium">
        {{ $t('auth.signInWithGoogle') || 'Sign in with Google Workspace' }}
      </span>
    </div>
  </q-btn>

  <!-- Error display -->
  <div v-if="error" class="q-mt-sm">
    <q-banner class="text-negative bg-negative-light" rounded dense>
      <template #avatar>
        <q-icon name="warning" color="negative" />
      </template>
      {{ error }}
    </q-banner>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useQuasar } from 'quasar'
import { googleAuth } from '@/services/googleAuth'
import type { GoogleAuthResponse } from '@/types/errors'

// Props
interface Props {
  disabled?: boolean
  loadingText?: string
  buttonText?: string
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false,
  loadingText: 'Signing in...',
  buttonText: 'Sign in with Google Workspace',
})

const emit = defineEmits<Emits>()

// Emits
interface Emits {
  success: [authData: GoogleAuthResponse]
  error: [error: string]
}

// Composables
const $q = useQuasar()

// Reactive state
const loading = ref(false)
const error = ref<string | null>(null)

/**
 * Handle sign in button click
 */
const handleSignIn = async (): Promise<void> => {
  if (loading.value || props.disabled) return

  try {
    loading.value = true
    error.value = null

    // Initialize Google Auth service if not already done
    await googleAuth.initialize()

    // Start Google OAuth flow (redirects to Google)
    await googleAuth.signInWithGoogle()

    // Note: The flow continues in the auth callback page
    // This function won't complete as the page redirects
  } catch (err: unknown) {
    const errorMessage =
      err instanceof Error ? err.message : 'Failed to start Google authentication'
    error.value = errorMessage
    emit('error', errorMessage)

    $q.notify({
      message: errorMessage,
      type: 'negative',
      position: 'top',
      timeout: 5000,
      actions: [
        {
          label: 'Dismiss',
          color: 'white',
          handler: () => {
            error.value = null
          },
        },
      ],
    })
  } finally {
    loading.value = false
  }
}

/**
 * Clear error state
 */
const clearError = (): void => {
  error.value = null
}

// Expose methods for parent components
defineExpose({
  clearError,
  handleSignIn,
})
</script>

<style scoped>
.google-sign-in-btn {
  border: 1px solid #dadce0;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
  text-transform: none;
  font-weight: 500;
  transition: box-shadow 0.2s ease;
}

.google-sign-in-btn:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.google-sign-in-btn:focus {
  box-shadow: 0 0 0 2px rgba(66, 133, 244, 0.3);
}

/* Dark mode adjustments */
.body--dark .google-sign-in-btn {
  background: #2d2d2d !important;
  color: white !important;
  border-color: #444;
}

.body--dark .google-sign-in-btn:hover {
  background: #3d3d3d !important;
  box-shadow: 0 2px 8px rgba(255, 255, 255, 0.1);
}

/* Loading state styling */
.google-sign-in-btn .q-btn__content .q-spinner-dots {
  color: currentColor;
}

/* Google icon styling */
.google-icon {
  min-width: 20px;
}

/* Error banner adjustments */
.bg-negative-light {
  background-color: rgba(244, 67, 54, 0.1) !important;
}
</style>
