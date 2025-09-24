<template>
  <q-page class="flex flex-center">
    <div class="text-center">
      <q-spinner-cube size="60px" color="primary" class="q-mb-md" />
      <h5 class="text-h5 q-mb-sm">{{ $t('auth.processing') }}</h5>
      <p class="text-body2 text-grey-6">{{ $t('auth.pleaseWait') }}</p>
    </div>
  </q-page>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { useAuth } from '@/composables/useAuth'

const route = useRoute()
const router = useRouter()
const $q = useQuasar()
const { handleAuthCallback } = useAuth()

onMounted(async () => {
  try {
    const code = route.query.code
    const error = route.query.error

    if (error) {
      throw new Error(error)
    }

    if (!code) {
      throw new Error('No authorization code received')
    }

    // Handle the auth callback
    await handleAuthCallback(code)
  } catch (error) {
    console.error('Auth callback error:', error)

    $q.notify({
      message: 'Authentication failed. Please try again.',
      type: 'negative',
      position: 'top',
    })

    // Redirect back to signin
    router.push('/signin')
  }
})
</script>
