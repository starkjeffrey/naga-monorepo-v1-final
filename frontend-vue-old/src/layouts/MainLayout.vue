<template>
  <q-layout view="lHh Lpr lFf">
    <!-- Top Header -->
    <q-header class="bg-dark text-white">
      <q-toolbar>
        <!-- App Icon and Name -->
        <q-avatar size="32px" class="q-mr-sm">
          <img src="/naga-trans.png" alt="NAGA" />
        </q-avatar>
        <q-toolbar-title class="text-weight-medium"> NAGA PUCSR </q-toolbar-title>

        <!-- Role Switcher -->
        <role-switcher class="q-mr-sm" />

        <!-- Language Toggle -->
        <q-btn
          flat
          round
          :icon="currentLanguage === 'en' ? 'language' : 'translate'"
          class="q-mr-sm"
          @click="toggleLanguage"
        >
          <q-tooltip>{{ $t('common.switchLanguage') }}</q-tooltip>
        </q-btn>

        <!-- Theme Toggle -->
        <q-btn
          flat
          round
          :icon="$q.dark.isActive ? 'light_mode' : 'dark_mode'"
          @click="toggleTheme"
        >
          <q-tooltip>{{ $t('common.switchTheme') }}</q-tooltip>
        </q-btn>
      </q-toolbar>
    </q-header>

    <!-- Main Content -->
    <q-page-container>
      <error-boundary :show-report-button="false" :can-go-back="true" @error="handlePageError">
        <router-view />
      </error-boundary>
    </q-page-container>

    <!-- Bottom Navigation -->
    <q-footer class="bg-dark">
      <q-tabs
        v-model="currentTab"
        dense
        active-color="primary"
        indicator-color="primary"
        class="text-white"
      >
        <!-- Student Navigation -->
        <template v-if="isStudent">
          <q-tab name="home" icon="home" :label="$t('nav.home')" @click="$router.push('/')" />
          <q-tab
            name="alerts"
            icon="notifications"
            :label="$t('nav.alerts')"
            @click="$router.push('/alerts')"
          >
            <q-badge v-if="unreadCount > 0" color="red" floating rounded>
              {{ unreadCount }}
            </q-badge>
          </q-tab>
          <q-tab
            name="messages"
            icon="mail"
            :label="$t('nav.messages')"
            @click="$router.push('/messages')"
          />
          <q-tab
            name="profile"
            icon="person"
            :label="$t('nav.profile')"
            @click="$router.push('/profile')"
          />
        </template>

        <!-- Teacher Navigation -->
        <template v-if="isTeacher">
          <q-tab
            name="teacher-home"
            icon="dashboard"
            :label="$t('nav.teacher.dashboard')"
            @click="$router.push('/teacher')"
          />
          <q-tab
            name="teacher-attendance"
            icon="assignment_turned_in"
            :label="$t('nav.teacher.attendance')"
            @click="$router.push('/teacher/attendance')"
          />
          <q-tab
            name="teacher-grades"
            icon="grade"
            :label="$t('nav.teacher.grades')"
            @click="$router.push('/teacher/grades')"
          />
          <q-tab
            name="teacher-courses"
            icon="class"
            :label="$t('nav.teacher.courses')"
            @click="$router.push('/teacher/courses')"
          />
        </template>
      </q-tabs>
    </q-footer>
  </q-layout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { useI18n } from 'vue-i18n'
import { useRouter, useRoute } from 'vue-router'
import { useAnnouncements } from '@/composables/useDatabase'
import { useRole, mockDualRoleUser } from '@/composables/useRole'
import ErrorBoundary from '@/components/ErrorBoundary.vue'
import RoleSwitcher from '@/components/RoleSwitcher.vue'

const $q = useQuasar()
const { locale, t } = useI18n()
const router = useRouter()
const route = useRoute()
const { getUnreadCount } = useAnnouncements()
const { isStudent, isTeacher, validateRole } = useRole()

const currentTab = ref('home')
const unreadCount = ref(0)

const currentLanguage = computed(() => locale.value)

const toggleLanguage = () => {
  locale.value = locale.value === 'en' ? 'km' : 'en'
  localStorage.setItem('language', locale.value)
}

const toggleTheme = () => {
  $q.dark.toggle()
  localStorage.setItem('darkMode', $q.dark.isActive)
}

// Update current tab based on route
const updateCurrentTab = () => {
  const path = route.path
  if (path === '/') currentTab.value = 'home'
  else if (path.startsWith('/alerts')) currentTab.value = 'alerts'
  else if (path.startsWith('/messages')) currentTab.value = 'messages'
  else if (path.startsWith('/profile')) currentTab.value = 'profile'
}

// Load unread notifications count
const loadUnreadCount = async () => {
  try {
    unreadCount.value = await getUnreadCount()
  } catch (error) {
    console.error('Failed to load unread count:', error)
  }
}

onMounted(() => {
  // Initialize dual role for development
  mockDualRoleUser()

  // Restore theme preference
  const savedTheme = localStorage.getItem('darkMode')
  if (savedTheme !== null) {
    $q.dark.set(JSON.parse(savedTheme))
  }

  // Restore language preference
  const savedLanguage = localStorage.getItem('language')
  if (savedLanguage) {
    locale.value = savedLanguage
  }

  updateCurrentTab()
  loadUnreadCount()
  validateRole()

  // Update tab when route changes
  router.afterEach(() => {
    updateCurrentTab()
  })
})

// Handle page-level errors
const handlePageError = (error: Error, errorInfo: any) => {
  console.error('Page error in MainLayout:', error, errorInfo)

  // Show user-friendly error notification
  $q.notify({
    message: t('errorBoundary.defaultMessage'),
    type: 'negative',
    position: 'top',
    timeout: 5000,
    actions: [
      {
        label: t('errorBoundary.retry'),
        color: 'white',
        handler: () => {
          // Reload the current route
          router.go(0)
        },
      },
    ],
  })
}
</script>

<style>
.q-toolbar-title {
  font-size: 1.1rem;
}

/* Remove any padding from page container */
.q-page-container {
  padding-top: 0 !important;
}

.q-footer .q-tabs {
  min-height: 60px;
}

.q-tab {
  min-height: 60px;
}
</style>
