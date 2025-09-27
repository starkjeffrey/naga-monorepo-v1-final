<template>
  <div class="min-h-screen bg-gray-50 p-8">
    <div class="max-w-7xl mx-auto">
      <!-- Header -->
      <div class="text-center mb-8">
        <h1 class="text-3xl font-bold text-gray-900 mb-2">
          Student Enrollment Management
        </h1>
        <p class="text-gray-600">
          Transfer students between available and enrolled lists using the arrow controls
        </p>
      </div>

      <!-- Transfer List Component -->
      <TransferList
        :available-items="availableStudents"
        :enrolled-items="enrolledStudents"
        available-title="Available Students"
        enrolled-title="Enrolled Students"
        :searchable="true"
        @transfer="handleTransfer"
      />

      <!-- Debug Info (remove in production) -->
      <div class="mt-8 p-4 bg-white rounded-lg border border-gray-200">
        <h3 class="text-lg font-semibold mb-2">Transfer Log</h3>
        <div class="text-sm text-gray-600">
          <div>Available: {{ availableCount }} students</div>
          <div>Enrolled: {{ enrolledCount }} students</div>
          <div class="mt-2 text-xs text-gray-500">
            Last transfer: {{ lastTransferTime || 'None' }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import TransferList from '../common/TransferList.vue'
import type { TransferItem } from '../common/TransferList.vue'

// Sample data - in real app this would come from API
const availableStudents = ref<TransferItem[]>([
  { id: '1', name: 'Alice Johnson', email: 'alice@example.com', studentId: 'ST001', grade: 'A' },
  { id: '2', name: 'Bob Smith', email: 'bob@example.com', studentId: 'ST002', grade: 'B+' },
  { id: '3', name: 'Charlie Brown', email: 'charlie@example.com', studentId: 'ST003', grade: 'A-' },
  { id: '4', name: 'Diana Prince', email: 'diana@example.com', studentId: 'ST004', grade: 'A+' },
  { id: '5', name: 'Edward Norton', email: 'edward@example.com', studentId: 'ST005', grade: 'B' },
  { id: '6', name: 'Fiona Green', email: 'fiona@example.com', studentId: 'ST006', grade: 'A' },
  { id: '7', name: 'George Wilson', email: 'george@example.com', studentId: 'ST007', grade: 'B-' },
  { id: '8', name: 'Hannah Davis', email: 'hannah@example.com', studentId: 'ST008', grade: 'A-' },
])

const enrolledStudents = ref<TransferItem[]>([
  { id: '9', name: 'Ian Thompson', email: 'ian@example.com', studentId: 'ST009', grade: 'A' },
  { id: '10', name: 'Julia Roberts', email: 'julia@example.com', studentId: 'ST010', grade: 'B+' },
])

// State tracking
const lastTransferTime = ref<string>('')
const availableCount = computed(() => availableStudents.value.length)
const enrolledCount = computed(() => enrolledStudents.value.length)

// Handle transfer events
const handleTransfer = (available: TransferItem[], enrolled: TransferItem[]) => {
  // Update the local data
  availableStudents.value = [...available]
  enrolledStudents.value = [...enrolled]

  // Update timestamp
  lastTransferTime.value = new Date().toLocaleTimeString()

  // In a real app, you would make API calls here to persist the changes
  console.log('Transfer completed:', {
    availableCount: available.length,
    enrolledCount: enrolled.length,
    timestamp: lastTransferTime.value
  })
}
</script>