<template>
  <q-page class="q-pa-md">
    <div class="q-mb-lg">
      <h4 class="text-h4 q-mb-xs text-weight-medium">
        {{ $t('teacher.dashboard.title') }}
      </h4>
      <p class="text-subtitle1 text-grey-6">
        {{ $t('teacher.dashboard.subtitle') }}
      </p>
    </div>

    <!-- Quick Stats -->
    <div class="row q-col-gutter-md q-mb-lg">
      <div class="col-12 col-sm-6 col-md-3">
        <q-card class="stats-card">
          <q-card-section class="text-center">
            <q-icon name="school" size="32px" color="primary" class="q-mb-sm" />
            <div class="text-h6 text-weight-bold">{{ totalCourses }}</div>
            <div class="text-caption text-grey-6">{{ $t('teacher.dashboard.stats.courses') }}</div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-12 col-sm-6 col-md-3">
        <q-card class="stats-card">
          <q-card-section class="text-center">
            <q-icon name="people" size="32px" color="secondary" class="q-mb-sm" />
            <div class="text-h6 text-weight-bold">{{ totalStudents }}</div>
            <div class="text-caption text-grey-6">{{ $t('teacher.dashboard.stats.students') }}</div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-12 col-sm-6 col-md-3">
        <q-card class="stats-card">
          <q-card-section class="text-center">
            <q-icon name="assignment_turned_in" size="32px" color="positive" class="q-mb-sm" />
            <div class="text-h6 text-weight-bold">{{ attendanceRate }}%</div>
            <div class="text-caption text-grey-6">
              {{ $t('teacher.dashboard.stats.attendance') }}
            </div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-12 col-sm-6 col-md-3">
        <q-card class="stats-card">
          <q-card-section class="text-center">
            <q-icon name="grade" size="32px" color="warning" class="q-mb-sm" />
            <div class="text-h6 text-weight-bold">{{ pendingGrades }}</div>
            <div class="text-caption text-grey-6">
              {{ $t('teacher.dashboard.stats.pendingGrades') }}
            </div>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <!-- Quick Actions -->
    <q-card class="q-mb-lg">
      <q-card-section>
        <h6 class="text-h6 q-mb-md">{{ $t('teacher.dashboard.quickActions.title') }}</h6>
        <div class="row q-col-gutter-md">
          <div class="col-12 col-sm-6 col-md-4">
            <q-btn
              :label="$t('teacher.dashboard.quickActions.generateCode')"
              color="primary"
              icon="qr_code"
              no-caps
              class="full-width"
              @click="$router.push('/teacher/attendance/generate')"
            />
          </div>
          <div class="col-12 col-sm-6 col-md-4">
            <q-btn
              :label="$t('teacher.dashboard.quickActions.manualAttendance')"
              color="secondary"
              icon="assignment_turned_in"
              no-caps
              class="full-width"
              @click="$router.push('/teacher/attendance/manual')"
            />
          </div>
          <div class="col-12 col-sm-6 col-md-4">
            <q-btn
              :label="$t('teacher.dashboard.quickActions.enterGrades')"
              color="orange"
              icon="grade"
              no-caps
              class="full-width"
              @click="$router.push('/teacher/grades')"
            />
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Today's Classes -->
    <q-card class="q-mb-lg">
      <q-card-section>
        <h6 class="text-h6 q-mb-md">{{ $t('teacher.dashboard.todaysClasses.title') }}</h6>
        <q-list v-if="todaysClasses.length > 0" separator>
          <q-item v-for="classItem in todaysClasses" :key="classItem.id">
            <q-item-section avatar>
              <q-avatar :color="getClassStatusColor(classItem.status)" text-color="white">
                <q-icon :name="getClassStatusIcon(classItem.status)" />
              </q-avatar>
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ classItem.name }}</q-item-label>
              <q-item-label caption>
                {{ classItem.time }} • {{ classItem.room }} • {{ classItem.students }}
                {{ $t('teacher.dashboard.students') }}
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-badge
                :color="getClassStatusColor(classItem.status)"
                :label="$t(`teacher.dashboard.classStatus.${classItem.status}`)"
              />
            </q-item-section>
          </q-item>
        </q-list>
        <div v-else class="text-center q-pa-lg">
          <q-icon name="event_busy" size="48px" color="grey-5" class="q-mb-sm" />
          <div class="text-grey-6">{{ $t('teacher.dashboard.todaysClasses.noClasses') }}</div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Recent Activity -->
    <q-card>
      <q-card-section>
        <h6 class="text-h6 q-mb-md">{{ $t('teacher.dashboard.recentActivity.title') }}</h6>
        <q-list v-if="recentActivity.length > 0" separator>
          <q-item v-for="activity in recentActivity" :key="activity.id">
            <q-item-section avatar>
              <q-icon :name="activity.icon" :color="activity.color" />
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ activity.description }}</q-item-label>
              <q-item-label caption>{{ formatDateTime(activity.timestamp) }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
        <div v-else class="text-center q-pa-lg">
          <q-icon name="history" size="48px" color="grey-5" class="q-mb-sm" />
          <div class="text-grey-6">{{ $t('teacher.dashboard.recentActivity.noActivity') }}</div>
        </div>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { date } from 'quasar'

// Mock data - in production this would come from API
const totalCourses = ref(3)
const totalStudents = ref(85)
const attendanceRate = ref(87)
const pendingGrades = ref(12)

const todaysClasses = ref([
  {
    id: 1,
    name: 'Computer Science 101',
    time: '08:00 - 09:30',
    room: 'Room A-101',
    students: 28,
    status: 'upcoming',
  },
  {
    id: 2,
    name: 'Database Systems',
    time: '10:00 - 11:30',
    room: 'Lab B-205',
    students: 32,
    status: 'in-progress',
  },
  {
    id: 3,
    name: 'Web Development',
    time: '14:00 - 15:30',
    room: 'Lab C-301',
    students: 25,
    status: 'completed',
  },
])

const recentActivity = ref([
  {
    id: 1,
    description: 'Generated attendance code for Computer Science 101',
    timestamp: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
    icon: 'qr_code',
    color: 'primary',
  },
  {
    id: 2,
    description: 'Updated grades for Database Systems midterm',
    timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    icon: 'grade',
    color: 'orange',
  },
  {
    id: 3,
    description: 'Marked manual attendance for Web Development',
    timestamp: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
    icon: 'assignment_turned_in',
    color: 'positive',
  },
])

// Helper functions
const getClassStatusColor = status => {
  switch (status) {
    case 'upcoming':
      return 'info'
    case 'in-progress':
      return 'positive'
    case 'completed':
      return 'grey'
    default:
      return 'grey'
  }
}

const getClassStatusIcon = status => {
  switch (status) {
    case 'upcoming':
      return 'schedule'
    case 'in-progress':
      return 'play_circle'
    case 'completed':
      return 'check_circle'
    default:
      return 'help'
  }
}

const formatDateTime = dateStr => {
  return date.formatDate(new Date(dateStr), 'MMM DD, HH:mm')
}

onMounted(() => {
  // Load dashboard data
  console.log('Teacher dashboard loaded')
})
</script>

<style scoped>
.stats-card {
  transition: transform 0.2s ease;
}

.stats-card:hover {
  transform: translateY(-2px);
}

.text-h6 {
  margin-bottom: 8px;
}
</style>
