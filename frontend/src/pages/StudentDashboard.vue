<template>
  <q-page class="q-px-md q-pb-md custom-page">
    <!-- Welcome Section - Temporarily Hidden -->
    <!-- <div class="q-mb-sm">
      <h4 class="text-h4 q-mb-xs text-weight-medium">
        {{ $t('dashboard.greeting') }}, {{ userName }}!
      </h4>
      <p class="text-subtitle1 text-grey-6">
        {{ $t('dashboard.subtitle') }}
      </p>
    </div> -->

    <!-- Dashboard Cards Grid -->
    <div class="row q-col-gutter-md q-pb-xl">
      <!-- Attendance Card -->
      <div class="col-12 col-sm-6">
        <q-card class="dashboard-card cursor-pointer" @click="$router.push('/attendance')">
          <q-card-section class="text-center">
            <q-avatar size="48px" class="q-mb-sm" color="purple-2">
              <q-icon name="assignment_turned_in" size="24px" color="purple-8" />
            </q-avatar>
            <div class="text-h6 text-weight-medium q-mb-xs text-dark">
              {{ $t('dashboard.attendance.title') }}
            </div>
            <div class="text-caption card-description">
              {{ $t('dashboard.attendance.description') }}
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- Grades Card -->
      <div class="col-12 col-sm-6">
        <q-card class="dashboard-card cursor-pointer" @click="$router.push('/grades')">
          <q-card-section class="text-center">
            <q-avatar size="48px" class="q-mb-sm" color="blue-2">
              <q-icon name="bar_chart" size="24px" color="blue-8" />
            </q-avatar>
            <div class="text-h6 text-weight-medium q-mb-xs text-dark">
              {{ $t('dashboard.grades.title') }}
            </div>
            <div class="text-caption card-description">
              {{ $t('dashboard.grades.description') }}
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- Schedule Card -->
      <div class="col-12 col-sm-6">
        <q-card class="dashboard-card cursor-pointer" @click="$router.push('/schedule')">
          <q-card-section class="text-center">
            <q-avatar size="48px" class="q-mb-sm" color="orange-2">
              <q-icon name="schedule" size="24px" color="orange-8" />
            </q-avatar>
            <div class="text-h6 text-weight-medium q-mb-xs text-dark">
              {{ $t('dashboard.schedule.title') }}
            </div>
            <div class="text-caption card-description">
              {{ $t('dashboard.schedule.description') }}
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- Announcements Card -->
      <div class="col-12 col-sm-6">
        <q-card class="dashboard-card cursor-pointer" @click="$router.push('/announcements')">
          <q-card-section class="text-center">
            <q-avatar size="48px" class="q-mb-sm" color="green-2">
              <q-icon name="campaign" size="24px" color="green-8" />
            </q-avatar>
            <div class="text-h6 text-weight-medium q-mb-xs text-dark">
              {{ $t('dashboard.announcements.title') }}
            </div>
            <div class="text-caption card-description">
              {{ $t('dashboard.announcements.description') }}
            </div>
            <q-badge v-if="unreadAnnouncements > 0" color="red" floating rounded>
              {{ unreadAnnouncements }}
            </q-badge>
          </q-card-section>
        </q-card>
      </div>

      <!-- ID Card -->
      <div class="col-12 col-sm-6">
        <q-card class="dashboard-card cursor-pointer" @click="$router.push('/id-card')">
          <q-card-section class="text-center">
            <q-avatar size="48px" class="q-mb-sm" color="yellow-2">
              <q-icon name="badge" size="24px" color="yellow-8" />
            </q-avatar>
            <div class="text-h6 text-weight-medium q-mb-xs text-dark">
              {{ $t('dashboard.idCard.title') }}
            </div>
            <div class="text-caption card-description">
              {{ $t('dashboard.idCard.description') }}
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- Permission Card -->
      <div class="col-12 col-sm-6">
        <q-card class="dashboard-card cursor-pointer" @click="$router.push('/permission')">
          <q-card-section class="text-center">
            <q-avatar size="48px" class="q-mb-sm" color="pink-2">
              <q-icon name="description" size="24px" color="pink-8" />
            </q-avatar>
            <div class="text-h6 text-weight-medium q-mb-xs text-dark">
              {{ $t('dashboard.permission.title') }}
            </div>
            <div class="text-caption card-description">
              {{ $t('dashboard.permission.description') }}
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- Profile Photo Card -->
      <div class="col-12 col-sm-6">
        <q-card class="dashboard-card cursor-pointer" @click="$router.push('/profile-photo')">
          <q-card-section class="text-center">
            <q-avatar size="48px" class="q-mb-sm" color="indigo-2">
              <q-icon name="photo_camera" size="24px" color="indigo-8" />
            </q-avatar>
            <div class="text-h6 text-weight-medium q-mb-xs text-dark">
              {{ $t('dashboard.profilePhoto.title') }}
            </div>
            <div class="text-caption card-description">
              {{ $t('dashboard.profilePhoto.description') }}
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- Financial Balance Card (Additional) -->
      <div class="col-12 col-sm-6">
        <q-card class="dashboard-card cursor-pointer" @click="$router.push('/finances')">
          <q-card-section class="text-center">
            <q-avatar size="48px" class="q-mb-sm" color="teal-2">
              <q-icon name="account_balance_wallet" size="24px" color="teal-8" />
            </q-avatar>
            <div class="text-h6 text-weight-medium q-mb-xs text-dark">
              {{ $t('dashboard.finances.title') }}
            </div>
            <div class="text-caption card-description">
              {{ $t('dashboard.finances.description') }}
            </div>
          </q-card-section>
        </q-card>
      </div>
    </div>
  </q-page>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useDatabase, useAnnouncements } from '@/composables/useDatabase'

const { currentUser } = useDatabase()
const { getUnreadCount } = useAnnouncements()

const userName = ref('John')
const unreadAnnouncements = ref(0)

const loadUserData = async () => {
  if (currentUser.value) {
    userName.value = currentUser.value.name || 'Student'
  }

  try {
    unreadAnnouncements.value = await getUnreadCount()
  } catch (error) {
    console.error('Failed to load unread announcements:', error)
  }
}

onMounted(() => {
  loadUserData()
})
</script>

<style scoped>
.dashboard-card {
  min-height: 140px;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.dashboard-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.12);
}

.text-h4 {
  line-height: 1.2;
}

.cursor-pointer {
  cursor: pointer;
}

/* Ensure proper text colors in light mode */
.text-dark {
  color: #1d1d1d !important;
}

.body--light .text-dark {
  color: #1d1d1d !important;
}

.body--dark .text-dark {
  color: #ffffff !important;
}

/* Better description text color for readability */
.card-description {
  color: #616161 !important; /* Darker grey for better contrast in light mode */
}

.body--light .card-description {
  color: #424242 !important; /* Even darker for light mode */
}

.body--dark .card-description {
  color: #9e9e9e !important; /* Lighter grey for dark mode */
}

/* Add sufficient top padding to clear the navbar */
.custom-page {
  padding-top: 80px !important;
}

@media (max-width: 599px) {
  .dashboard-card {
    min-height: 120px;
  }
}
</style>
