<template>
  <q-page class="q-pa-md">
    <div class="q-mb-lg">
      <h4 class="text-h4 q-mb-xs text-weight-medium">
        {{ $t('profile.title') }}
      </h4>
      <p class="text-subtitle1 text-grey-6">
        {{ $t('profile.subtitle') }}
      </p>
    </div>

    <!-- Profile Header -->
    <q-card class="q-mb-md">
      <q-card-section class="text-center q-pa-lg">
        <q-avatar size="100px" class="q-mb-md">
          <img v-if="userProfile.avatar" :src="userProfile.avatar" alt="Profile" />
          <q-icon v-else name="person" size="60px" />
        </q-avatar>
        <h5 class="text-h5 text-weight-medium q-mb-xs">{{ userProfile.name }}</h5>
        <p class="text-subtitle2 text-primary">{{ userProfile.role }}</p>
        <p class="text-caption text-grey-6">
          {{ $t('profile.studentId') }}: {{ userProfile.studentId }}
        </p>
      </q-card-section>
    </q-card>

    <!-- Profile Information -->
    <q-card class="q-mb-md">
      <q-card-section>
        <h6 class="text-h6 q-mb-md">{{ $t('profile.personalInfo') }}</h6>

        <q-list separator>
          <q-item>
            <q-item-section avatar>
              <q-icon name="email" color="primary" />
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ $t('profile.email') }}</q-item-label>
              <q-item-label caption>{{ userProfile.email }}</q-item-label>
            </q-item-section>
          </q-item>

          <q-item>
            <q-item-section avatar>
              <q-icon name="phone" color="primary" />
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ $t('profile.phone') }}</q-item-label>
              <q-item-label caption>{{ userProfile.phone }}</q-item-label>
            </q-item-section>
          </q-item>

          <q-item>
            <q-item-section avatar>
              <q-icon name="school" color="primary" />
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ $t('profile.department') }}</q-item-label>
              <q-item-label caption>{{ userProfile.department }}</q-item-label>
            </q-item-section>
          </q-item>

          <q-item>
            <q-item-section avatar>
              <q-icon name="calendar_today" color="primary" />
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ $t('profile.academicYear') }}</q-item-label>
              <q-item-label caption>{{ userProfile.academicYear }}</q-item-label>
            </q-item-section>
          </q-item>

          <q-item>
            <q-item-section avatar>
              <q-icon name="location_on" color="primary" />
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ $t('profile.address') }}</q-item-label>
              <q-item-label caption>{{ userProfile.address }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
      </q-card-section>
    </q-card>

    <!-- Academic Information -->
    <q-card class="q-mb-md">
      <q-card-section>
        <h6 class="text-h6 q-mb-md">{{ $t('profile.academicInfo') }}</h6>

        <q-list separator>
          <q-item>
            <q-item-section avatar>
              <q-icon name="menu_book" color="primary" />
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ $t('profile.program') }}</q-item-label>
              <q-item-label caption>{{ userProfile.program }}</q-item-label>
            </q-item-section>
          </q-item>

          <q-item>
            <q-item-section avatar>
              <q-icon name="trending_up" color="primary" />
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ $t('profile.gpa') }}</q-item-label>
              <q-item-label caption>{{ userProfile.gpa }}</q-item-label>
            </q-item-section>
          </q-item>

          <q-item>
            <q-item-section avatar>
              <q-icon name="class" color="primary" />
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ $t('profile.semester') }}</q-item-label>
              <q-item-label caption>{{ userProfile.currentSemester }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
      </q-card-section>
    </q-card>

    <!-- Action Buttons -->
    <div class="row q-gutter-md">
      <div class="col">
        <q-btn
          color="primary"
          icon="edit"
          :label="$t('profile.editProfile')"
          class="full-width"
          @click="editProfile"
        />
      </div>
      <div class="col">
        <q-btn
          color="negative"
          icon="logout"
          :label="$t('profile.logout')"
          class="full-width"
          @click="logout"
        />
      </div>
    </div>
  </q-page>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { useDatabase } from '@/composables/useDatabase'
import { useAuth } from '@/composables/useAuth'

const router = useRouter()
const $q = useQuasar()
const { currentUser, clearCurrentUser } = useDatabase()
const { signOut } = useAuth()

const userProfile = ref({
  name: 'John Doe',
  role: 'Student',
  studentId: 'ST2024001',
  email: 'john.doe@student.pucsr.edu.kh',
  phone: '+855 12 345 678',
  department: 'Computer Science',
  academicYear: '2024-2025',
  address: 'Siem Reap, Cambodia',
  program: 'Bachelor of Computer Science',
  gpa: '3.75',
  currentSemester: 'Semester 2',
  studyLevel: 'BA', // BA, MA, or LANG
  avatar: null,
})

const editProfile = () => {
  $q.notify({
    message: 'Edit profile functionality coming soon',
    type: 'info',
    position: 'top',
  })
}

const logout = () => {
  $q.dialog({
    title: 'Confirm Logout',
    message: 'Are you sure you want to logout?',
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    try {
      await signOut()
      $q.notify({
        message: 'Logged out successfully',
        type: 'positive',
        position: 'top',
      })
    } catch (error) {
      $q.notify({
        message: 'Error during logout',
        type: 'negative',
        position: 'top',
      })
    }
  })
}

onMounted(() => {
  if (currentUser.value) {
    // Load actual user data from database
    userProfile.value = {
      ...userProfile.value,
      ...currentUser.value,
    }
  }
})
</script>
