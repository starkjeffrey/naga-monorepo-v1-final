<template>
  <div class="signin-page">
    <div class="signin-container q-pa-lg">
      <!-- App Title -->
      <div class="text-center q-mb-xl">
        <h3 class="text-h3 text-weight-light q-mb-sm text-primary">
          {{ $t('signin.welcome') }}
        </h3>
        <h4 class="text-h4 text-weight-medium q-mb-md naga-title">NAGA PUCSR</h4>
        <p class="text-subtitle1 text-grey-6">
          {{ $t('signin.subtitle') }}
        </p>
      </div>

      <!-- Role Selector -->
      <div class="q-mb-sm text-center">
        <!-- Reduced bottom margin, centered -->
        <div class="text-caption text-grey-7 q-mb-xs">{{ $t('signin.selectRole') }}</div>
        <q-option-group
          v-model="selectedRole"
          :options="roleOptions"
          color="primary"
          inline
          dense
          size="sm"
        />
      </div>

      <!-- Large Dragon Logo -->
      <div class="text-center q-mb-lg dragon-section">
        <!-- Reduced bottom margin for logo -->
        <img src="/naga-trans.png" alt="NAGA Dragon Logo" class="dragon-logo" />
      </div>

      <!-- Email Input Form -->
      <q-form class="q-mb-md" @submit="handleEmailSubmit">
        <q-input
          v-model="email"
          type="email"
          :label="$t('signin.emailLabel')"
          :placeholder="$t('signin.emailPlaceholder')"
          outlined
          class="q-mb-md"
          :rules="emailRules"
          autocomplete="email"
        >
          <template #prepend>
            <q-icon name="email" />
          </template>
        </q-input>

        <q-btn
          type="submit"
          color="primary"
          :label="$t('signin.continue')"
          class="full-width q-mb-md"
          size="lg"
          :loading="loading"
          :disable="!isValidEmail"
        />
      </q-form>

      <!-- Divider -->
      <div class="text-center q-mb-md">
        <q-separator class="q-mb-md" />
        <span class="text-caption text-grey-6 bg-white q-px-md">
          {{ $t('signin.orSignInWith') }}
        </span>
      </div>

      <!-- Google Workspace Authentication -->
      <div class="google-auth-section q-mb-lg">
        <google-sign-in-button @success="handleAuthSuccess" @error="handleAuthError" />
      </div>

      <!-- Development Authentication (Development Mode Only) -->
      <div v-if="isDevAuthAvailable()" class="dev-auth-section q-mb-lg">
        <q-separator class="q-mb-md" />
        <div class="text-center q-mb-md">
          <span class="text-caption text-orange-8 bg-orange-1 q-px-md q-py-xs rounded-borders">
            🧪 Development Mode
          </span>
        </div>

        <div class="text-caption text-grey-6 q-mb-md text-center">
          Quick sign-in for testing (development only)
        </div>

        <div class="row q-gutter-sm">
          <div class="col-12 col-sm-4">
            <q-btn
              color="blue-6"
              icon="school"
              label="Student"
              class="full-width"
              size="sm"
              outline
              :loading="loading"
              @click="handleDevSignIn('student')"
            >
              <q-tooltip>John Doe - Student Account</q-tooltip>
            </q-btn>
          </div>
          <div class="col-12 col-sm-4">
            <q-btn
              color="green-6"
              icon="person"
              label="Teacher"
              class="full-width"
              size="sm"
              outline
              :loading="loading"
              @click="handleDevSignIn('teacher')"
            >
              <q-tooltip>Prof. Jane Smith - Teacher Account</q-tooltip>
            </q-btn>
          </div>
          <div class="col-12 col-sm-4">
            <q-btn
              color="purple-6"
              icon="people"
              label="Dual Role"
              class="full-width"
              size="sm"
              outline
              :loading="loading"
              @click="handleDevSignIn('dual_role')"
            >
              <q-tooltip>Alex Chen - Student + Teacher</q-tooltip>
            </q-btn>
          </div>
        </div>
      </div>

      <!-- Forgot Password Link -->
      <div class="text-center">
        <q-btn
          flat
          color="grey-6"
          size="sm"
          :label="$t('signin.forgotPassword')"
          class="text-caption"
          @click="handleForgotPassword"
        />
      </div>

      <!-- Language Toggle (Bottom) -->
      <div class="text-center q-mt-xl">
        <q-btn
          flat
          color="primary"
          :icon="currentLanguage === 'en' ? 'language' : 'translate'"
          :label="currentLanguage === 'en' ? 'ខ្មែរ' : 'English'"
          size="sm"
          @click="toggleLanguage"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'
import { useAuth } from '@/composables/useAuth'
import GoogleSignInButton from '@/components/GoogleSignInButton.vue'

const router = useRouter()
const $q = useQuasar()
const { locale } = useI18n()
const {
  signInWithGoogle,
  isAuthenticated,
  activeRole,
  signInWithDevUser,
  getDevTestUsers,
  isDevAuthAvailable,
} = useAuth()

const email = ref('')
const loading = ref(false)
const selectedRole = ref('student') // Default role

const roleOptions = [
  { label: 'Student', value: 'student' },
  { label: 'Teacher', value: 'teacher' },
]

const currentLanguage = computed(() => locale.value)

const isValidEmail = computed(() => {
  const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailPattern.test(email.value)
})

const emailRules = [
  (val: string) => !!val || 'Email is required',
  (_val: string) => isValidEmail.value || 'Please enter a valid email address',
]

const handleEmailSubmit = async () => {
  if (!isValidEmail.value) return

  // For now, redirect email submissions to Google OAuth
  // This maintains the UI but channels all auth through Google
  $q.notify({
    message: 'Please use Google Workspace authentication for @pucsr.edu.kh accounts.',
    type: 'info',
    position: 'top',
    timeout: 3000,
  })
}

/**
 * Handle successful Google authentication
 */
const handleAuthSuccess = (authData: any) => {
  $q.notify({
    message: 'Successfully signed in!',
    type: 'positive',
    position: 'top',
    timeout: 2000,
  })

  // The useAuth composable will handle the redirect to appropriate dashboard
}

/**
 * Handle Google authentication error
 */
const handleAuthError = (error: string) => {
  $q.notify({
    message: error || 'Google authentication failed. Please try again.',
    type: 'negative',
    position: 'top',
    timeout: 5000,
    actions: [
      {
        label: 'Dismiss',
        color: 'white',
        handler: () => {},
      },
    ],
  })
}

const handleForgotPassword = () => {
  $q.notify({
    message: 'Please contact IT support for password assistance.',
    type: 'info',
    position: 'top',
    timeout: 5000,
  })
}

const toggleLanguage = () => {
  locale.value = locale.value === 'en' ? 'km' : 'en'
  localStorage.setItem('language', locale.value)
}

/**
 * Handle development authentication
 */
const handleDevSignIn = async (userType: 'student' | 'teacher' | 'dual_role') => {
  try {
    loading.value = true
    await signInWithDevUser(userType)

    $q.notify({
      message: `Successfully signed in as ${userType}!`,
      type: 'positive',
      position: 'top',
      timeout: 2000,
    })
  } catch (error: unknown) {
    const errorMessage = error instanceof Error ? error.message : 'Development sign in failed'
    $q.notify({
      message: errorMessage,
      type: 'negative',
      position: 'top',
      timeout: 5000,
    })
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  // Check if already authenticated
  if (isAuthenticated.value) {
    // Redirect to appropriate dashboard based on role
    if (activeRole.value === 'teacher') {
      router.push({ name: 'TeacherDashboard' })
    } else {
      router.push({ name: 'Dashboard' })
    }
    return
  }

  // Restore language preference
  const savedLanguage = localStorage.getItem('language')
  if (savedLanguage) {
    locale.value = savedLanguage
  }

  // Auto-focus email input on desktop
  if (!$q.platform.is.mobile) {
    // Focus will be handled by Quasar automatically
  }
})
</script>

<style scoped>
.signin-page {
  min-height: 100vh;
  height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.signin-container {
  width: 100%;
  max-width: 400px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
}

.dragon-logo {
  height: 8cm; /* ~300px - much larger to fill the space */
  width: auto;
  object-fit: contain;
}

.dragon-section {
  margin-bottom: 1.5rem !important; /* Reduced space below dragon */
}

.naga-title {
  color: #be0001 !important;
}

.google-auth-section {
  /* Additional styling for Google auth section if needed */
}

.dev-auth-section {
  border: 1px dashed #ffa726;
  border-radius: 8px;
  padding: 16px;
  background: rgba(255, 167, 38, 0.05);
}

.dev-auth-section .q-btn {
  font-size: 0.75rem;
}

@media (max-width: 599px) {
  .signin-container {
    margin: 16px;
    max-width: none;
  }

  .dragon-logo {
    height: 6cm; /* Proportionally larger for mobile */
  }
}

/* Dark mode adjustments */
.body--dark .signin-container {
  background: #1e1e1e;
  color: white;
}
</style>
