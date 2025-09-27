<template>
  <div class="flex flex-col lg:flex-row gap-4 w-full max-w-6xl mx-auto">
    <!-- Available Items List -->
    <div class="flex-1">
      <ListPanel
        :title="availableTitle"
        :items="availableItems"
        :selectedItems="selectedAvailable"
        :searchable="searchable"
        @update:selectedItems="selectedAvailable = $event"
      />
    </div>

    <!-- Transfer Controls -->
    <div class="flex lg:flex-col items-center justify-center gap-2 lg:gap-4 py-4">
      <div class="flex lg:flex-col gap-2">
        <!-- Move all to enrolled -->
        <button
          @click="handleEnrollAll"
          :disabled="availableItems.length === 0"
          class="lg:w-12 lg:h-12 w-auto px-3 py-2 bg-gray-100 hover:bg-gray-200 disabled:bg-gray-50 disabled:cursor-not-allowed border border-gray-300 rounded-md transition-colors"
          title="Move all to enrolled"
        >
          <!-- Double Right Arrow SVG -->
          <svg class="h-4 w-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 5l7 7-7 7M5 5l7 7-7 7" />
          </svg>
        </button>

        <!-- Move selected to enrolled -->
        <button
          @click="handleEnroll"
          :disabled="selectedAvailable.length === 0"
          class="lg:w-12 lg:h-12 w-auto px-3 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-200 disabled:cursor-not-allowed text-white rounded-md transition-colors"
          title="Move selected to enrolled"
        >
          <!-- Right Arrow SVG -->
          <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
          </svg>
        </button>

        <!-- Move selected to available -->
        <button
          @click="handleUnenroll"
          :disabled="selectedEnrolled.length === 0"
          class="lg:w-12 lg:h-12 w-auto px-3 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-200 disabled:cursor-not-allowed text-white rounded-md transition-colors"
          title="Move selected to available"
        >
          <!-- Left Arrow SVG -->
          <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
          </svg>
        </button>

        <!-- Move all to available -->
        <button
          @click="handleUnenrollAll"
          :disabled="enrolledItems.length === 0"
          class="lg:w-12 lg:h-12 w-auto px-3 py-2 bg-gray-100 hover:bg-gray-200 disabled:bg-gray-50 disabled:cursor-not-allowed border border-gray-300 rounded-md transition-colors"
          title="Move all to available"
        >
          <!-- Double Left Arrow SVG -->
          <svg class="h-4 w-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 19l-7-7 7-7M19 19l-7-7 7-7" />
          </svg>
        </button>
      </div>
    </div>

    <!-- Enrolled Items List -->
    <div class="flex-1">
      <ListPanel
        :title="enrolledTitle"
        :items="enrolledItems"
        :selectedItems="selectedEnrolled"
        :searchable="searchable"
        @update:selectedItems="selectedEnrolled = $event"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, defineEmits, defineProps, withDefaults } from 'vue'
// Using inline SVG icons instead of external dependencies
import ListPanel from './ListPanel.vue'

export interface TransferItem {
  id: string
  name: string
  email?: string
  [key: string]: any
}

interface Props {
  availableItems: TransferItem[]
  enrolledItems: TransferItem[]
  availableTitle?: string
  enrolledTitle?: string
  searchable?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  availableTitle: 'Available',
  enrolledTitle: 'Selected',
  searchable: true
})

const emit = defineEmits<{
  transfer: [available: TransferItem[], enrolled: TransferItem[]]
}>()

// Local reactive copies of the props
const availableItems = ref<TransferItem[]>([...props.availableItems])
const enrolledItems = ref<TransferItem[]>([...props.enrolledItems])

// Selected items tracking
const selectedAvailable = ref<string[]>([])
const selectedEnrolled = ref<string[]>([])

// Transfer functions
const handleEnroll = () => {
  const itemsToEnroll = availableItems.value.filter(item =>
    selectedAvailable.value.includes(item.id)
  )

  availableItems.value = availableItems.value.filter(item =>
    !selectedAvailable.value.includes(item.id)
  )

  enrolledItems.value = [...enrolledItems.value, ...itemsToEnroll]
  selectedAvailable.value = []

  emit('transfer', availableItems.value, enrolledItems.value)
}

const handleUnenroll = () => {
  const itemsToUnenroll = enrolledItems.value.filter(item =>
    selectedEnrolled.value.includes(item.id)
  )

  enrolledItems.value = enrolledItems.value.filter(item =>
    !selectedEnrolled.value.includes(item.id)
  )

  availableItems.value = [...availableItems.value, ...itemsToUnenroll]
  selectedEnrolled.value = []

  emit('transfer', availableItems.value, enrolledItems.value)
}

const handleEnrollAll = () => {
  enrolledItems.value = [...enrolledItems.value, ...availableItems.value]
  availableItems.value = []
  selectedAvailable.value = []

  emit('transfer', availableItems.value, enrolledItems.value)
}

const handleUnenrollAll = () => {
  availableItems.value = [...availableItems.value, ...enrolledItems.value]
  enrolledItems.value = []
  selectedEnrolled.value = []

  emit('transfer', availableItems.value, enrolledItems.value)
}
</script>