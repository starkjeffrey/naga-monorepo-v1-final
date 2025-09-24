<template>
  <q-page class="q-pa-md">
    <div class="q-mb-lg">
      <h4 class="text-h4 q-mb-xs text-weight-medium">
        {{ $t('attendance.title') }}
      </h4>
      <p class="text-subtitle1 text-grey-6">
        {{ $t('attendance.subtitle') }}
      </p>
    </div>

    <q-card>
      <q-list separator>
        <q-item v-ripple clickable @click="$router.push('/enter-code')">
          <q-item-section avatar>
            <q-icon color="primary" name="qr_code_scanner" />
          </q-item-section>
          <q-item-section>
            <q-item-label>{{ $t('attendance.actions.enterCode') }}</q-item-label>
            <q-item-label caption>{{ $t('attendance.actions.enterCodeCaption') }}</q-item-label>
          </q-item-section>
          <q-item-section side>
            <q-icon name="chevron_right" />
          </q-item-section>
        </q-item>

        <q-item v-ripple clickable @click="$router.push('/permission')">
          <q-item-section avatar>
            <q-icon color="amber" name="description" />
          </q-item-section>
          <q-item-section>
            <q-item-label>{{ $t('attendance.actions.requestPermission') }}</q-item-label>
            <q-item-label caption>{{
              $t('attendance.actions.requestPermissionCaption')
            }}</q-item-label>
          </q-item-section>
          <q-item-section side>
            <q-icon name="chevron_right" />
          </q-item-section>
        </q-item>

        <q-item v-ripple clickable @click="$router.push('/attendance-history')">
          <q-item-section avatar>
            <q-icon color="secondary" name="history" />
          </q-item-section>
          <q-item-section>
            <q-item-label>{{ $t('attendance.actions.viewHistory') }}</q-item-label>
            <q-item-label caption>{{ $t('attendance.actions.viewHistoryCaption') }}</q-item-label>
          </q-item-section>
          <q-item-section side>
            <q-icon name="chevron_right" />
          </q-item-section>
        </q-item>
      </q-list>
    </q-card>

    <!-- Offline Queue Info -->
    <q-card v-if="offlineQueue.length > 0" class="q-mt-md">
      <q-card-section>
        <div class="row items-center">
          <div class="col">
            <q-item-label class="text-weight-medium">
              {{ $t('attendance.offline.title') }}
            </q-item-label>
            <q-item-label caption>
              {{ $t('attendance.offline.description', { count: offlineQueue.length }) }}
            </q-item-label>
          </div>
          <div class="col-auto">
            <q-btn
              :label="$t('attendance.offline.retry')"
              color="primary"
              outline
              size="sm"
              :loading="retrying"
              @click="retryOfflineSubmissions"
            />
          </div>
        </div>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup>
import { onMounted, computed } from 'vue'
import { useAttendanceStore } from '@/stores/attendanceStore'
const attendanceStore = useAttendanceStore()

const retrying = computed(() => attendanceStore.retrying)
const offlineQueue = computed(() => attendanceStore.offlineQueue)

const retryOfflineSubmissions = () => {
  attendanceStore.retryOfflineSubmissions()
}

onMounted(() => {
  // We still want to load the offline queue on this page
  attendanceStore.loadOfflineQueue()
})
</script>
