<template>
  <q-page class="q-pa-md">
    <div class="q-mb-lg">
      <h4 class="text-h4 q-mb-xs text-weight-medium">
        {{ $t('attendance.teacher.title') }}
      </h4>
      <p class="text-subtitle1 text-grey-6">
        {{ $t('attendance.teacher.subtitle') }}
      </p>
    </div>

    <!-- Class Selection and Session Control -->
    <q-card class="q-mb-md">
      <q-card-section>
        <div v-if="!activeSession">
          <h6 class="text-h6 q-mb-md">{{ $t('attendance.teacher.selectClass') }}</h6>
          <q-select
            v-model="selectedClass"
            :options="teacherClasses"
            option-value="class_part_id"
            option-label="class_name"
            :label="$t('attendance.teacher.classLabel')"
            outlined
            class="q-mb-md"
            :loading="classesLoading"
            :disable="classesLoading"
          />
          <q-btn
            :label="$t('attendance.teacher.startSession')"
            color="primary"
            :loading="sessionLoading"
            :disable="!selectedClass || sessionLoading"
            class="full-width"
            @click="startSession"
          />
        </div>

        <!-- Active Session Info -->
        <div v-else>
          <h6 class="text-h6 q-mb-md">{{ $t('attendance.teacher.activeSession') }}</h6>
          <div class="text-center q-pa-lg bg-grey-2 rounded-borders">
            <div class="text-h1 text-weight-bolder text-primary">
              {{ activeSession.attendance_code }}
            </div>
            <div class="text-subtitle1 text-grey-7 q-mt-sm">
              {{ $t('attendance.teacher.codeInstructions') }}
            </div>
            <div class="text-caption text-grey-6 q-mt-xs">
              {{ $t('attendance.teacher.expiresAt') }}:
              {{ formatExpiry(activeSession.code_expires_at) }}
            </div>
          </div>
          <q-btn
            :label="$t('attendance.teacher.endSession')"
            color="negative"
            :loading="sessionLoading"
            class="full-width q-mt-md"
            @click="endSession"
          />
        </div>
      </q-card-section>
    </q-card>

    <!-- Class Roster and Manual Attendance -->
    <q-card v-if="activeSession && classRoster.length > 0">
      <q-card-section>
        <h6 class="text-h6 q-mb-md">{{ $t('attendance.teacher.classRoster') }}</h6>
        <q-list separator>
          <q-item v-for="student in classRoster" :key="student.student_id">
            <q-item-section avatar>
              <q-avatar>
                <img :src="student.photo_url || 'https://cdn.quasar.dev/img/boy-avatar.png'" />
              </q-avatar>
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ student.student_name }}</q-item-label>
              <q-item-label caption
                >{{ $t('attendance.teacher.studentId') }}: {{ student.student_id }}</q-item-label
              >
            </q-item-section>
            <q-item-section side>
              <q-btn-toggle
                v-model="student.attendance_status"
                push
                glossy
                toggle-color="primary"
                :options="[
                  { label: $t('attendance.status.present'), value: 'PRESENT' },
                  { label: $t('attendance.status.absent'), value: 'ABSENT' },
                  { label: $t('attendance.status.late'), value: 'LATE' },
                ]"
                @update:model-value="status => onManualMark(student.student_id, status)"
              />
            </q-item-section>
          </q-item>
        </q-list>
      </q-card-section>
    </q-card>

    <q-inner-loading :showing="rosterLoading">
      <q-spinner-gears size="50px" color="primary" />
    </q-inner-loading>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useQuasar, date } from 'quasar'
import { useI18n } from 'vue-i18n'
import { useAttendanceStore } from '@/stores/attendanceStore'

const $q = useQuasar()
const { t } = useI18n()
const attendanceStore = useAttendanceStore()

const selectedClass = ref(null)

// --- MOCK DATA (to be replaced by store action) ---
const teacherClasses = ref([])
const classesLoading = ref(false)

const fetchTeacherClasses = async () => {
  classesLoading.value = true
  // This will be replaced by: await attendanceStore.fetchTeacherClasses();
  await new Promise(resolve => setTimeout(resolve, 1000)) // Simulate API call
  teacherClasses.value = [
    {
      class_part_id: 101,
      class_name: 'English Intermediate A (Mon 09:00)',
      schedule: { day_of_week: 1, start_time: '09:00' },
    },
    {
      class_part_id: 102,
      class_name: 'Advanced Writing Workshop (Wed 14:00)',
      schedule: { day_of_week: 3, start_time: '14:00' },
    },
    {
      class_part_id: 103,
      class_name: 'Intro to Linguistics (Fri 11:00)',
      schedule: { day_of_week: 5, start_time: '11:00' },
    },
  ]
  // Smart selection logic
  const now = new Date()
  const currentDay = now.getDay() === 0 ? 7 : now.getDay() // Sunday: 0 -> 7
  const currentTime = date.formatDate(now, 'HH:mm')
  const currentClass = teacherClasses.value.find(
    c => c.schedule.day_of_week === currentDay && currentTime >= c.schedule.start_time
  )
  if (currentClass) {
    selectedClass.value = currentClass
  }
  classesLoading.value = false
}
// --- END MOCK DATA ---

// Computed properties from the store
const activeSession = computed(() => attendanceStore.activeTeacherSession)
const classRoster = computed(() => attendanceStore.classRoster)
const sessionLoading = computed(() => attendanceStore.teacherSessionLoading)
const rosterLoading = computed(() => attendanceStore.rosterLoading)

const startSession = async () => {
  if (!selectedClass.value) return
  // In a real scenario, you'd get location data
  const locationData = { latitude: 11.5564, longitude: 104.9282 }
  await attendanceStore.startTeacherSession(selectedClass.value.class_part_id, locationData)
}

const endSession = async () => {
  await attendanceStore.endTeacherSession()
  selectedClass.value = null // Reset class selection
}

const onManualMark = async (studentId, status) => {
  if (!activeSession.value) return
  const payload = {
    session_id: activeSession.value.id,
    student_id: studentId,
    status,
  }
  await attendanceStore.submitManualAttendance(payload)
}

const formatExpiry = expiryDate => {
  return date.formatDate(expiryDate, 'HH:mm:ss')
}

onMounted(() => {
  fetchTeacherClasses()
})
</script>
