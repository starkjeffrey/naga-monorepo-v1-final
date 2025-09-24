<template>
  <q-page class="q-pa-md">
    <q-btn flat icon="arrow_back" :label="$t('general.back')" @click="$router.back()" />
    <div class="q-mb-lg q-mt-md">
      <h4 class="text-h4 q-mb-xs text-weight-medium">
        {{ $t('attendance.checkIn.title') }}
      </h4>
      <p class="text-subtitle1 text-grey-6">
        {{ $t('attendance.checkIn.instructions') }}
      </p>
    </div>

    <q-card class="q-mb-md">
      <q-card-section>
        <q-form class="q-gutter-md" @submit="onSubmitCode">
          <q-input
            v-model="attendanceCode"
            :label="$t('attendance.checkIn.codeLabel')"
            :placeholder="$t('attendance.checkIn.codePlaceholder')"
            outlined
            maxlength="6"
            :rules="[
              val => !!val || $t('attendance.checkIn.codeRequired'),
              val => val.length === 6 || $t('attendance.checkIn.codeLength'),
            ]"
            autofocus
            @input="onCodeInput"
          >
            <template #prepend>
              <q-icon name="qr_code" />
            </template>
            <template #append>
              <q-btn
                v-if="attendanceCode"
                round
                dense
                flat
                icon="clear"
                @click="attendanceCode = ''"
              />
            </template>
          </q-input>

          <div class="row q-gutter-sm">
            <q-btn
              :label="$t('attendance.checkIn.submit')"
              type="submit"
              color="primary"
              :loading="submitting"
              :disable="submitting || attendanceCode.length !== 6"
              class="full-width"
            />
          </div>
        </q-form>
      </q-card-section>
    </q-card>

    <!-- Recent Check-ins can be shown here for context -->
    <q-card v-if="recentCheckIns.length > 0" class="q-mb-md">
      <q-card-section>
        <h6 class="text-h6 q-mb-md">{{ $t('attendance.recent.title') }}</h6>
        <q-list separator>
          <q-item v-for="checkin in recentCheckIns" :key="checkin.id">
            <q-item-section>
              <q-item-label>{{
                checkin.className || $t('attendance.recent.unknownClass')
              }}</q-item-label>
              <q-item-label caption>{{ formatDateTime(checkin.timestamp) }}</q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-badge
                :color="getCheckinStatusColor(checkin.status)"
                :label="$t(`attendance.status.${checkin.status}`)"
              />
            </q-item-section>
          </q-item>
        </q-list>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useQuasar, date } from 'quasar'
import { useI18n } from 'vue-i18n'
import { useAttendanceStore } from '@/stores/attendanceStore'
import { useRouter } from 'vue-router'

const $q = useQuasar()
const { t } = useI18n()
const router = useRouter()
const attendanceStore = useAttendanceStore()

// Form data
const attendanceCode = ref('')

const submitting = computed(() => attendanceStore.submitting)
const recentCheckIns = computed(() => attendanceStore.recentCheckIns)

// Methods
const onCodeInput = val => {
  // Convert to uppercase and remove non-alphanumeric characters
  attendanceCode.value = val.toUpperCase().replace(/[^A-Z0-9]/g, '')
}

const onSubmitCode = async () => {
  if (!attendanceCode.value || attendanceCode.value.length !== 6) {
    return
  }
  const success = await attendanceStore.submitAttendanceCode(attendanceCode.value)
  if (success) {
    attendanceCode.value = ''
    // Optionally, navigate back or show a success message
    $q.notify({
      type: 'positive',
      message: t('attendance.checkIn.success'),
      icon: 'check_circle',
    })
    router.push('/attendance')
  }
}

const formatDateTime = dateStr => {
  return date.formatDate(new Date(dateStr), 'MMM DD, YYYY HH:mm')
}

const getCheckinStatusColor = status => {
  switch (status) {
    case 'confirmed':
      return 'positive'
    case 'pending':
      return 'warning'
    case 'failed':
      return 'negative'
    default:
      return 'grey'
  }
}

onMounted(() => {
  attendanceStore.loadRecentCheckIns()
})
</script>
