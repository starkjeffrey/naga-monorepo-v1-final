<template>
  <q-page class="q-pa-md">
    <div class="q-mb-lg">
      <h4 class="text-h4 q-mb-xs text-weight-medium">Manual Attendance</h4>
      <p class="text-subtitle1 text-grey-6">Mark attendance manually for your students</p>
    </div>

    <!-- Class Selection -->
    <q-card class="q-mb-md" v-if="!selectedSession">
      <q-card-section>
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
          label="Load Class Roster"
          color="primary"
          :loading="rosterLoading"
          :disable="!selectedClass || rosterLoading"
          class="full-width"
          @click="loadClassRoster"
        />
      </q-card-section>
    </q-card>

    <!-- Selected Class Info -->
    <q-card class="q-mb-md" v-if="selectedSession">
      <q-card-section>
        <div class="row items-center justify-between">
          <div>
            <h6 class="text-h6 q-mb-xs">{{ selectedSession.class_name }}</h6>
            <p class="text-caption text-grey-6 q-mb-none">
              {{ $t('attendance.teacher.manualEntry') }} • {{ formatDate(new Date()) }}
            </p>
          </div>
          <q-btn
            flat
            round
            icon="close"
            @click="resetSelection"
            class="text-grey-6"
          />
        </div>
      </q-card-section>
    </q-card>

    <!-- Class Roster with Manual Attendance -->
    <q-card v-if="selectedSession && classRoster.length > 0">
      <q-card-section>
        <div class="row items-center justify-between q-mb-md">
          <h6 class="text-h6 q-mb-none">Class Roster ({{ classRoster.length }} students)</h6>
          <div class="text-caption text-grey-6">
            Present: {{ attendanceStats.present }} |
            Absent: {{ attendanceStats.absent }} |
            Late: {{ attendanceStats.late }} |
            Excused: {{ attendanceStats.excused }}
          </div>
        </div>

        <!-- Bulk Actions -->
        <div class="q-mb-md">
          <q-btn-group flat>
            <q-btn
              flat
              dense
              label="Mark All Present"
              @click="markAll('PRESENT')"
              class="text-positive"
            />
            <q-btn
              flat
              dense
              label="Mark All Absent"
              @click="markAll('ABSENT')"
              class="text-negative"
            />
            <q-btn
              flat
              dense
              label="Clear All"
              @click="clearAll()"
              class="text-grey-7"
            />
          </q-btn-group>
        </div>

        <q-list separator>
          <q-item
            v-for="student in classRoster"
            :key="student.student_id"
            class="student-item"
          >
            <q-item-section avatar>
              <q-avatar
                size="48px"
                class="student-avatar"
              >
                <img
                  :src="student.photo_url || 'https://cdn.quasar.dev/img/boy-avatar.png'"
                  :alt="student.student_name"
                />
                <q-tooltip
                  class="bg-white text-dark shadow-2"
                  anchor="center right"
                  self="center left"
                  :offset="[10, 0]"
                  v-if="student.photo_url"
                >
                  <div class="text-center">
                    <q-avatar size="120px" class="q-mb-sm">
                      <img :src="student.photo_url" :alt="student.student_name" />
                    </q-avatar>
                    <div class="text-weight-medium">{{ student.student_name }}</div>
                    <div class="text-caption text-grey-7">ID: {{ student.student_id }}</div>
                  </div>
                </q-tooltip>
              </q-avatar>
            </q-item-section>

            <q-item-section>
              <q-item-label class="text-weight-medium">{{ student.student_name }}</q-item-label>
              <q-item-label caption>
                {{ $t('attendance.teacher.studentId') }}: {{ student.student_id }}
                <span v-if="student.enrollment_status === 'AUDIT'" class="text-orange"> (Audit)</span>
              </q-item-label>
            </q-item-section>

            <q-item-section side>
              <div class="attendance-controls">
                <q-btn-toggle
                  v-model="student.attendance_status"
                  push
                  glossy
                  toggle-color="primary"
                  size="sm"
                  :options="attendanceOptions"
                  @update:model-value="status => onManualMark(student.student_id, status)"
                  class="attendance-toggle"
                />
                <q-btn
                  v-if="student.attendance_status"
                  flat
                  round
                  dense
                  icon="edit_note"
                  size="sm"
                  @click="openNotesDialog(student)"
                  class="q-ml-sm text-grey-6"
                >
                  <q-tooltip>Add notes</q-tooltip>
                </q-btn>
              </div>
            </q-item-section>
          </q-item>
        </q-list>

        <!-- Save Button -->
        <div class="q-mt-lg text-center">
          <q-btn
            label="Save Attendance"
            color="positive"
            size="lg"
            :loading="submissionLoading"
            :disable="!hasAnyAttendance"
            @click="submitAllAttendance"
            class="q-px-xl"
          />
        </div>
      </q-card-section>
    </q-card>

    <!-- Empty State -->
    <q-card v-else-if="selectedSession && classRoster.length === 0 && !rosterLoading">
      <q-card-section class="text-center q-pa-xl">
        <q-icon name="people_outline" size="64px" color="grey-5" class="q-mb-md" />
        <h6 class="text-h6 text-weight-medium q-mb-sm">No Students Found</h6>
        <p class="text-body2 text-grey-6">
          No students are enrolled in this class or the roster hasn't been synced yet.
        </p>
      </q-card-section>
    </q-card>

    <!-- Loading States -->
    <q-inner-loading :showing="rosterLoading">
      <q-spinner-gears size="50px" color="primary" />
    </q-inner-loading>

    <!-- Notes Dialog -->
    <q-dialog v-model="notesDialog.show" persistent>
      <q-card style="min-width: 400px">
        <q-card-section>
          <div class="text-h6">Add Notes</div>
          <div class="text-subtitle2 text-grey-7 q-mt-xs">
            {{ notesDialog.student?.student_name }}
          </div>
        </q-card-section>

        <q-card-section class="q-pt-none">
          <q-input
            v-model="notesDialog.notes"
            type="textarea"
            rows="3"
            outlined
            label="Attendance notes (optional)"
            placeholder="e.g., Late arrival due to traffic, Left early with permission..."
            maxlength="200"
            counter
          />
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Cancel" @click="closeNotesDialog" />
          <q-btn flat label="Save" color="primary" @click="saveNotes" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { useQuasar, date } from 'quasar'
import { useI18n } from 'vue-i18n'
import { useAttendanceStore } from '@/stores/attendanceStore'

const $q = useQuasar()
const { t } = useI18n()
const attendanceStore = useAttendanceStore()

// Data
const selectedClass = ref(null)
const selectedSession = ref(null)
const submissionLoading = ref(false)
const notesDialog = reactive({
  show: false,
  student: null,
  notes: ''
})

// Attendance options with 4 buttons
const attendanceOptions = [
  { label: 'Present', value: 'PRESENT', color: 'positive' },
  { label: 'Absent', value: 'ABSENT', color: 'negative' },
  { label: 'Late', value: 'LATE', color: 'warning' },
  { label: 'Excused', value: 'EXCUSED', color: 'info' }
]

// Mock data for teacher classes
const teacherClasses = ref([])
const classesLoading = ref(false)

const fetchTeacherClasses = async () => {
  classesLoading.value = true
  await new Promise(resolve => setTimeout(resolve, 1000))
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
  classesLoading.value = false
}

// Computed properties
const classRoster = computed(() => attendanceStore.classRoster)
const rosterLoading = computed(() => attendanceStore.rosterLoading)

const attendanceStats = computed(() => {
  const stats = { present: 0, absent: 0, late: 0, excused: 0 }
  classRoster.value.forEach(student => {
    if (student.attendance_status === 'PRESENT') stats.present++
    else if (student.attendance_status === 'ABSENT') stats.absent++
    else if (student.attendance_status === 'LATE') stats.late++
    else if (student.attendance_status === 'EXCUSED') stats.excused++
  })
  return stats
})

const hasAnyAttendance = computed(() => {
  return classRoster.value.some(student => student.attendance_status)
})

// Methods
const loadClassRoster = async () => {
  if (!selectedClass.value) return

  // Create a mock session for manual attendance
  selectedSession.value = {
    class_part_id: selectedClass.value.class_part_id,
    class_name: selectedClass.value.class_name,
    session_type: 'MANUAL'
  }

  try {
    await attendanceStore.fetchClassRoster(selectedClass.value.class_part_id)
  } catch (error) {
    // If API call fails, use mock data for development
    console.log('Using mock student data for development')
  }

  // If no students loaded from API, add mock data
  if (attendanceStore.classRoster.length === 0) {
    attendanceStore.classRoster = [
      {
        student_id: 'STU001',
        student_name: 'Alice Johnson',
        enrollment_status: 'ACTIVE',
        is_audit: false,
        photo_url: 'https://images.unsplash.com/photo-1494790108755-2616b612e31a?w=150&h=150&fit=crop&crop=face',
        attendance_status: null,
        notes: ''
      },
      {
        student_id: 'STU002',
        student_name: 'Bob Smith',
        enrollment_status: 'ACTIVE',
        is_audit: false,
        photo_url: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&h=150&fit=crop&crop=face',
        attendance_status: null,
        notes: ''
      },
      {
        student_id: 'STU003',
        student_name: 'Carol Davis',
        enrollment_status: 'ACTIVE',
        is_audit: false,
        photo_url: 'https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=150&h=150&fit=crop&crop=face',
        attendance_status: null,
        notes: ''
      },
      {
        student_id: 'STU004',
        student_name: 'David Wilson',
        enrollment_status: 'AUDIT',
        is_audit: true,
        photo_url: 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=150&h=150&fit=crop&crop=face',
        attendance_status: null,
        notes: ''
      },
      {
        student_id: 'STU005',
        student_name: 'Emma Brown',
        enrollment_status: 'ACTIVE',
        is_audit: false,
        photo_url: 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=150&h=150&fit=crop&crop=face',
        attendance_status: null,
        notes: ''
      },
      {
        student_id: 'STU006',
        student_name: 'Frank Miller',
        enrollment_status: 'ACTIVE',
        is_audit: false,
        photo_url: null, // Test fallback avatar
        attendance_status: null,
        notes: ''
      }
    ]
  }

  // Initialize attendance status for each student
  classRoster.value.forEach(student => {
    if (!student.attendance_status) {
      student.attendance_status = null
      student.notes = ''
    }
  })
}

const resetSelection = () => {
  selectedClass.value = null
  selectedSession.value = null
  attendanceStore.classRoster.length = 0
}

const onManualMark = async (studentId, status) => {
  const student = classRoster.value.find(s => s.student_id === studentId)
  if (student) {
    student.attendance_status = status

    // Show success feedback
    $q.notify({
      type: 'positive',
      message: `${student.student_name} marked as ${status.toLowerCase()}`,
      position: 'top',
      timeout: 1500
    })
  }
}

const markAll = (status) => {
  classRoster.value.forEach(student => {
    student.attendance_status = status
  })
  $q.notify({
    type: 'info',
    message: `All students marked as ${status.toLowerCase()}`,
    position: 'top'
  })
}

const clearAll = () => {
  classRoster.value.forEach(student => {
    student.attendance_status = null
    student.notes = ''
  })
  $q.notify({
    type: 'info',
    message: 'All attendance cleared',
    position: 'top'
  })
}

const openNotesDialog = (student) => {
  notesDialog.student = student
  notesDialog.notes = student.notes || ''
  notesDialog.show = true
}

const closeNotesDialog = () => {
  notesDialog.show = false
  notesDialog.student = null
  notesDialog.notes = ''
}

const saveNotes = () => {
  if (notesDialog.student) {
    notesDialog.student.notes = notesDialog.notes
  }
  closeNotesDialog()
  $q.notify({
    type: 'positive',
    message: 'Notes saved',
    position: 'top'
  })
}

const submitAllAttendance = async () => {
  if (!selectedSession.value) return

  submissionLoading.value = true

  try {
    // Submit attendance for each student with a status
    const attendancePromises = classRoster.value
      .filter(student => student.attendance_status)
      .map(student => {
        const payload = {
          session_id: selectedSession.value.class_part_id, // Using class_part_id as session_id for manual
          student_id: student.student_id,
          status: student.attendance_status,
          notes: student.notes || undefined
        }
        return attendanceStore.submitManualAttendance(payload)
      })

    await Promise.all(attendancePromises)

    $q.notify({
      type: 'positive',
      message: `Attendance saved for ${attendancePromises.length} students`,
      position: 'top'
    })

    // Reset after successful submission
    setTimeout(() => {
      resetSelection()
    }, 1500)

  } catch (error) {
    console.error('Failed to submit attendance:', error)
    $q.notify({
      type: 'negative',
      message: 'Failed to save attendance. Please try again.',
      position: 'top'
    })
  } finally {
    submissionLoading.value = false
  }
}

const formatDate = (date) => {
  return new Intl.DateTimeFormat('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  }).format(date)
}

// Lifecycle
onMounted(() => {
  fetchTeacherClasses()
})
</script>

<style scoped>
.student-item {
  transition: background-color 0.2s ease;
}

.student-item:hover {
  background-color: rgba(0, 0, 0, 0.02);
}

.student-avatar {
  cursor: pointer;
  transition: transform 0.2s ease;
}

.student-avatar:hover {
  transform: scale(1.1);
}

.attendance-controls {
  display: flex;
  align-items: center;
}

.attendance-toggle {
  border-radius: 8px;
}

.attendance-toggle .q-btn {
  min-width: 60px;
  font-size: 11px;
}

/* Custom colors for attendance status */
.attendance-toggle .q-btn--push.q-btn--active {
  transform: translateY(0);
}

.attendance-toggle .q-btn[data-value="PRESENT"].q-btn--active {
  background-color: #4caf50 !important;
  color: white !important;
}

.attendance-toggle .q-btn[data-value="ABSENT"].q-btn--active {
  background-color: #f44336 !important;
  color: white !important;
}

.attendance-toggle .q-btn[data-value="LATE"].q-btn--active {
  background-color: #ff9800 !important;
  color: white !important;
}

.attendance-toggle .q-btn[data-value="EXCUSED"].q-btn--active {
  background-color: #2196f3 !important;
  color: white !important;
}

/* Photo tooltip styling */
.q-tooltip {
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}
</style>