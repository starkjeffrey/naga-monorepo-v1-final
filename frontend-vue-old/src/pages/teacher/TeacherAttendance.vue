<template>
  <q-page class="q-pa-md">
    <div class="q-mb-lg">
      <h4 class="text-h4 q-mb-xs text-weight-medium">
        {{ $t('teacher.attendance.title') }}
      </h4>
      <p class="text-subtitle1 text-grey-6">
        {{ $t('teacher.attendance.subtitle') }}
      </p>
    </div>

    <!-- Attendance Methods -->
    <div class="row q-col-gutter-md q-mb-lg">
      <div class="col-12 col-sm-6">
        <q-card
          class="attendance-method-card cursor-pointer"
          @click="$router.push('/teacher/attendance/generate')"
        >
          <q-card-section class="text-center q-pa-lg">
            <q-icon name="qr_code" size="64px" color="primary" class="q-mb-md" />
            <h6 class="text-h6 text-weight-medium q-mb-sm">
              {{ $t('teacher.attendance.methods.generateCode.title') }}
            </h6>
            <p class="text-body2 text-grey-6">
              {{ $t('teacher.attendance.methods.generateCode.description') }}
            </p>
            <q-btn
              :label="$t('teacher.attendance.methods.generateCode.action')"
              color="primary"
              outline
              no-caps
              class="q-mt-md"
            />
          </q-card-section>
        </q-card>
      </div>

      <div class="col-12 col-sm-6">
        <q-card
          class="attendance-method-card cursor-pointer"
          @click="$router.push('/teacher/attendance/manual')"
        >
          <q-card-section class="text-center q-pa-lg">
            <q-icon name="assignment_turned_in" size="64px" color="secondary" class="q-mb-md" />
            <h6 class="text-h6 text-weight-medium q-mb-sm">
              {{ $t('teacher.attendance.methods.manual.title') }}
            </h6>
            <p class="text-body2 text-grey-6">
              {{ $t('teacher.attendance.methods.manual.description') }}
            </p>
            <q-btn
              :label="$t('teacher.attendance.methods.manual.action')"
              color="secondary"
              outline
              no-caps
              class="q-mt-md"
            />
          </q-card-section>
        </q-card>
      </div>
    </div>

    <!-- Today's Attendance Summary -->
    <q-card class="q-mb-lg">
      <q-card-section>
        <h6 class="text-h6 q-mb-md">{{ $t('teacher.attendance.todaysSummary.title') }}</h6>
        <div class="row q-col-gutter-md">
          <div class="col-6 col-sm-3">
            <div class="stat-box text-center">
              <div class="stat-number text-h5 text-weight-bold text-positive">
                {{ todaysStats.present }}
              </div>
              <div class="stat-label text-caption text-grey-6">
                {{ $t('teacher.attendance.stats.present') }}
              </div>
            </div>
          </div>
          <div class="col-6 col-sm-3">
            <div class="stat-box text-center">
              <div class="stat-number text-h5 text-weight-bold text-negative">
                {{ todaysStats.absent }}
              </div>
              <div class="stat-label text-caption text-grey-6">
                {{ $t('teacher.attendance.stats.absent') }}
              </div>
            </div>
          </div>
          <div class="col-6 col-sm-3">
            <div class="stat-box text-center">
              <div class="stat-number text-h5 text-weight-bold text-warning">
                {{ todaysStats.late }}
              </div>
              <div class="stat-label text-caption text-grey-6">
                {{ $t('teacher.attendance.stats.late') }}
              </div>
            </div>
          </div>
          <div class="col-6 col-sm-3">
            <div class="stat-box text-center">
              <div class="stat-number text-h5 text-weight-bold text-info">
                {{ todaysStats.excused }}
              </div>
              <div class="stat-label text-caption text-grey-6">
                {{ $t('teacher.attendance.stats.excused') }}
              </div>
            </div>
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Recent Activity -->
    <q-card>
      <q-card-section>
        <h6 class="text-h6 q-mb-md">{{ $t('teacher.attendance.recentActivity.title') }}</h6>
        <q-list v-if="recentActivity.length > 0" separator>
          <q-item v-for="activity in recentActivity" :key="activity.id">
            <q-item-section avatar>
              <q-icon :name="activity.icon" :color="activity.color" />
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ activity.description }}</q-item-label>
              <q-item-label caption>{{ formatDateTime(activity.timestamp) }}</q-item-label>
            </q-item-section>
            <q-item-section v-if="activity.count" side>
              <q-badge :color="activity.color" :label="activity.count" />
            </q-item-section>
          </q-item>
        </q-list>
        <div v-else class="text-center q-pa-lg">
          <q-icon name="history" size="48px" color="grey-5" class="q-mb-sm" />
          <div class="text-grey-6">{{ $t('teacher.attendance.recentActivity.noActivity') }}</div>
        </div>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { date } from 'quasar'

// Mock data - in production this would come from API
const todaysStats = ref({
  present: 45,
  absent: 8,
  late: 3,
  excused: 2,
})

const recentActivity = ref([
  {
    id: 1,
    description: 'Generated attendance code for Computer Science 101',
    timestamp: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
    icon: 'qr_code',
    color: 'primary',
    count: '28',
  },
  {
    id: 2,
    description: 'Manual attendance taken for Database Systems',
    timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    icon: 'assignment_turned_in',
    color: 'secondary',
    count: '32',
  },
  {
    id: 3,
    description: 'Generated attendance code for Web Development',
    timestamp: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
    icon: 'qr_code',
    color: 'primary',
    count: '25',
  },
])

const formatDateTime = dateStr => {
  return date.formatDate(new Date(dateStr), 'MMM DD, HH:mm')
}

onMounted(() => {
  // Load attendance data
  console.log('Teacher attendance hub loaded')
})
</script>

<style scoped>
.attendance-method-card {
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  border: 2px solid transparent;
}

.attendance-method-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.12);
  border-color: var(--q-primary);
}

.stat-box {
  padding: 16px;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.02);
}

.stat-number {
  line-height: 1;
}

.cursor-pointer {
  cursor: pointer;
}
</style>
