<template>
  <q-btn-dropdown
    v-if="hasMultipleRoles"
    :color="roleColor"
    :icon="roleIcon"
    :label="roleDisplayName"
    flat
    no-caps
    dropdown-icon="expand_more"
  >
    <q-list>
      <q-item
        v-for="role in availableRoles"
        :key="role"
        v-close-popup
        clickable
        :class="{ 'bg-grey-2': activeRole === role }"
        @click="switchRole(role)"
      >
        <q-item-section avatar>
          <q-icon :name="getRoleIcon(role)" :color="getRoleColor(role)" />
        </q-item-section>
        <q-item-section>
          <q-item-label>{{ getRoleDisplayName(role) }}</q-item-label>
          <q-item-label caption>{{ getRoleDescription(role) }}</q-item-label>
        </q-item-section>
        <q-item-section v-if="activeRole === role" side>
          <q-icon name="check" color="positive" />
        </q-item-section>
      </q-item>
    </q-list>
  </q-btn-dropdown>

  <!-- Single role indicator -->
  <q-chip
    v-else-if="activeRole"
    :color="roleColor"
    text-color="white"
    :icon="roleIcon"
    :label="roleDisplayName"
    dense
  />
</template>

<script setup>
import { useRole } from '@/composables/useRole'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const {
  availableRoles,
  activeRole,
  hasMultipleRoles,
  roleDisplayName,
  roleIcon,
  roleColor,
  switchRole,
} = useRole()

// Helper functions for role display
const getRoleIcon = role => {
  switch (role) {
    case 'student':
      return 'person'
    case 'teacher':
      return 'school'
    case 'admin':
      return 'admin_panel_settings'
    default:
      return 'person'
  }
}

const getRoleColor = role => {
  switch (role) {
    case 'student':
      return 'primary'
    case 'teacher':
      return 'secondary'
    case 'admin':
      return 'warning'
    default:
      return 'grey'
  }
}

const getRoleDisplayName = role => {
  return t(`roles.${role}.name`)
}

const getRoleDescription = role => {
  return t(`roles.${role}.description`)
}
</script>

<style scoped>
.q-btn-dropdown {
  min-width: 120px;
}

.q-chip {
  font-weight: 500;
}
</style>
