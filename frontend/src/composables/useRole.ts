import { ref, computed, watch, readonly, type Ref, type ComputedRef } from 'vue'
import { useRouter, type Router } from 'vue-router'

// Define role types
export type UserRole = 'student' | 'teacher' | 'admin'

// Interface for role change event
interface RoleChangeEvent extends CustomEvent {
  detail: {
    newRole: UserRole | null
    oldRole: UserRole | null
  }
}

// Interface for the useRole composable return type
interface UseRoleReturn {
  // State
  availableRoles: Ref<readonly UserRole[]>
  activeRole: Ref<readonly (UserRole | null)>
  isInitialized: Ref<readonly boolean>

  // Computed
  hasMultipleRoles: ComputedRef<boolean>
  isStudent: ComputedRef<boolean>
  isTeacher: ComputedRef<boolean>
  isAdmin: ComputedRef<boolean>
  roleDisplayName: ComputedRef<string>
  roleIcon: ComputedRef<string>
  roleColor: ComputedRef<string>

  // Methods
  initializeRoles: (userRoles?: UserRole[]) => void
  switchRole: (newRole: UserRole) => boolean
  hasRole: (role: UserRole) => boolean
  getRoutePrefix: () => string
  getHomeRoute: () => string
  resetRoles: () => void
  validateRole: () => void
}

// Global role state
const availableRoles = ref<UserRole[]>([])
const activeRole = ref<UserRole | null>(null)
const isInitialized = ref(false)

export function useRole(): UseRoleReturn {
  const router: Router = useRouter()

  // Computed properties
  const hasMultipleRoles = computed(() => availableRoles.value.length > 1)
  const isStudent = computed(() => activeRole.value === 'student')
  const isTeacher = computed(() => activeRole.value === 'teacher')
  const isAdmin = computed(() => activeRole.value === 'admin')

  const roleDisplayName = computed(() => {
    switch (activeRole.value) {
      case 'student':
        return 'Student'
      case 'teacher':
        return 'Teacher'
      case 'admin':
        return 'Admin'
      default:
        return ''
    }
  })

  const roleIcon = computed(() => {
    switch (activeRole.value) {
      case 'student':
        return 'person'
      case 'teacher':
        return 'school'
      case 'admin':
        return 'admin_panel_settings'
      default:
        return 'person'
    }
  })

  const roleColor = computed(() => {
    switch (activeRole.value) {
      case 'student':
        return 'primary'
      case 'teacher':
        return 'secondary'
      case 'admin':
        return 'warning'
      default:
        return 'grey'
    }
  })

  // Initialize roles from localStorage or user data
  const initializeRoles = (userRoles: UserRole[] = []) => {
    if (isInitialized.value) return

    // Set available roles from user data
    availableRoles.value = userRoles.length > 0 ? userRoles : ['student']

    // Try to restore saved role preference
    const savedRole = localStorage.getItem('activeRole') as UserRole | null

    if (savedRole && availableRoles.value.includes(savedRole)) {
      activeRole.value = savedRole
    } else {
      // Default role priority: student > teacher > admin
      if (availableRoles.value.includes('student')) {
        activeRole.value = 'student'
      } else {
        activeRole.value = availableRoles.value[0]
      }
    }

    isInitialized.value = true
    console.log('Roles initialized:', {
      availableRoles: availableRoles.value,
      activeRole: activeRole.value,
    })
  }

  // Switch to a different role
  const switchRole = (newRole: UserRole): boolean => {
    if (!availableRoles.value.includes(newRole)) {
      console.error(`Role '${newRole}' not available for user`)
      return false
    }

    const previousRole = activeRole.value
    activeRole.value = newRole

    // Save preference
    localStorage.setItem('activeRole', newRole)

    // Navigate to role-specific home page
    const roleRoutes: Record<UserRole, string> = {
      student: '/',
      teacher: '/teacher',
      admin: '/admin',
    }

    if (roleRoutes[newRole]) {
      router.push(roleRoutes[newRole])
    }

    console.log(`Role switched from '${previousRole}' to '${newRole}'`)
    return true
  }

  // Check if user has a specific role
  const hasRole = (role: UserRole): boolean => {
    return availableRoles.value.includes(role)
  }

  // Get role-specific route prefix
  const getRoutePrefix = (): string => {
    switch (activeRole.value) {
      case 'teacher':
        return '/teacher'
      case 'admin':
        return '/admin'
      default:
        return ''
    }
  }

  // Get home route for current role
  const getHomeRoute = (): string => {
    switch (activeRole.value) {
      case 'teacher':
        return '/teacher'
      case 'admin':
        return '/admin'
      default:
        return '/'
    }
  }

  // Reset roles (for logout)
  const resetRoles = (): void => {
    availableRoles.value = []
    activeRole.value = null
    isInitialized.value = false
    localStorage.removeItem('activeRole')
  }

  // Validate current role
  const validateRole = (): void => {
    if (!activeRole.value || !availableRoles.value.includes(activeRole.value)) {
      console.warn('Invalid active role, resetting to default')
      if (availableRoles.value.length > 0) {
        switchRole(availableRoles.value.includes('student') ? 'student' : availableRoles.value[0])
      }
    }
  }

  // Watch for role changes to perform side effects
  watch(activeRole, (newRole, oldRole) => {
    if (newRole !== oldRole && isInitialized.value) {
      // Emit role change event for other components to react
      const event: RoleChangeEvent = new CustomEvent('roleChanged', {
        detail: { newRole, oldRole },
      }) as RoleChangeEvent
      document.dispatchEvent(event)
    }
  })

  return {
    // State
    availableRoles: readonly(availableRoles),
    activeRole: readonly(activeRole),
    isInitialized: readonly(isInitialized),

    // Computed
    hasMultipleRoles,
    isStudent,
    isTeacher,
    isAdmin,
    roleDisplayName,
    roleIcon,
    roleColor,

    // Methods
    initializeRoles,
    switchRole,
    hasRole,
    getRoutePrefix,
    getHomeRoute,
    resetRoles,
    validateRole,
  }
}

// For development/testing - mock user with multiple roles
export function mockDualRoleUser(): void {
  const { initializeRoles } = useRole()
  initializeRoles(['student', 'teacher'])
}

// For development/testing - mock single role user
export function mockSingleRoleUser(role: UserRole = 'student'): void {
  const { initializeRoles } = useRole()
  initializeRoles([role])
}
