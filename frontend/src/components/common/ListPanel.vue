<template>
  <div class="bg-white rounded-lg border border-gray-200 shadow-sm flex flex-col h-96">
    <!-- Header -->
    <div class="p-4 border-b border-gray-200">
      <div class="flex items-center justify-between mb-3">
        <h3 class="text-lg font-semibold text-gray-900">{{ title }}</h3>
        <span class="text-sm text-gray-500">
          {{ selectedItems.length }}/{{ filteredItems.length }} selected
        </span>
      </div>

      <!-- Search Input -->
      <div v-if="searchable" class="mb-3">
        <input
          v-model="searchTerm"
          type="text"
          placeholder="Search..."
          class="w-full px-3 py-2 text-sm border border-gray-300 rounded-md bg-white text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>

      <!-- Select All Button -->
      <button
        @click="handleSelectAll"
        class="w-full px-3 py-2 text-sm border border-gray-300 rounded-md bg-white text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        {{ allSelected ? 'Deselect All' : 'Select All' }}
      </button>
    </div>

    <!-- Items List -->
    <div class="flex-1 overflow-y-auto p-2">
      <div v-if="filteredItems.length === 0" class="flex items-center justify-center h-full text-gray-500">
        {{ searchTerm ? 'No items found' : 'No items available' }}
      </div>

      <div v-else class="space-y-1">
        <div
          v-for="item in filteredItems"
          :key="item.id"
          @click="handleItemClick(item.id)"
          :class="[
            'p-3 rounded-md cursor-pointer transition-colors border',
            selectedItems.includes(item.id)
              ? 'bg-blue-50 border-blue-200 text-blue-900'
              : 'bg-white border-gray-200 hover:bg-gray-50'
          ]"
        >
          <div class="font-medium text-sm">{{ item.name }}</div>
          <div v-if="item.email" class="text-xs text-gray-500 mt-1">
            {{ item.email }}
          </div>
          <div v-if="item.studentId" class="text-xs text-gray-500">
            ID: {{ item.studentId }}
          </div>
          <div v-if="item.grade" class="text-xs text-gray-500">
            Grade: {{ item.grade }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, defineProps, defineEmits } from 'vue'
import type { TransferItem } from './TransferList.vue'

interface Props {
  title: string
  items: TransferItem[]
  selectedItems: string[]
  searchable?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  searchable: true
})

const emit = defineEmits<{
  'update:selectedItems': [selectedItems: string[]]
}>()

const searchTerm = ref('')

// Computed properties
const filteredItems = computed(() => {
  if (!searchTerm.value) return props.items

  const search = searchTerm.value.toLowerCase()
  return props.items.filter(item =>
    item.name.toLowerCase().includes(search) ||
    (item.email && item.email.toLowerCase().includes(search)) ||
    (item.studentId && item.studentId.toLowerCase().includes(search))
  )
})

const allSelected = computed(() =>
  filteredItems.value.length > 0 &&
  props.selectedItems.length === filteredItems.value.length
)

// Event handlers
const handleItemClick = (itemId: string) => {
  const newSelection = props.selectedItems.includes(itemId)
    ? props.selectedItems.filter(id => id !== itemId)
    : [...props.selectedItems, itemId]

  emit('update:selectedItems', newSelection)
}

const handleSelectAll = () => {
  if (allSelected.value) {
    emit('update:selectedItems', [])
  } else {
    emit('update:selectedItems', filteredItems.value.map(item => item.id))
  }
}
</script>