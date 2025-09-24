import {
  createRouter,
  createWebHistory,
  type RouteRecordRaw,
  type NavigationGuardNext,
  type RouteLocationNormalized,
} from 'vue-router'
import { useAuth } from '@/composables/useAuth'
import { useRole, type UserRole } from '@/composables/useRole'

// Lazy load layout components for better performance
const MainLayout = () => import('@/layouts/MainLayout.vue')

// Route factories for better code organization
interface RouteMetaCustom {
  requiresAuth?: boolean
  requiresGuest?: boolean
  role?: UserRole
  roles?: UserRole[]
}

const createStudentRoute = (
  path: string,
  name: string,
  component: string,
  meta: RouteMetaCustom = {}
): RouteRecordRaw => ({
  path,
  name,
  component: () => import(`@/pages/${component}.vue`),
  meta: { requiresAuth: true, ...meta },
})

const createTeacherRoute = (
  path: string,
  name: string,
  component: string,
  meta: RouteMetaCustom = {}
): RouteRecordRaw => ({
  path,
  name,
  component: () => import(`@/pages/teacher/${component}.vue`),
  meta: { requiresAuth: true, role: 'teacher' as UserRole, ...meta },
})

const routes: RouteRecordRaw[] = [
  // Authentication routes (no layout) - Critical path, load first
  {
    path: '/signin',
    name: 'Signin',
    component: () => import('@/pages/SigninPage.vue'),
    meta: { requiresGuest: true },
  },
  {
    path: '/auth/callback',
    name: 'AuthCallback',
    component: () => import('@/pages/AuthCallback.vue'),
  },

  // Main app routes (with lazy-loaded layout)
  {
    path: '/',
    component: MainLayout,
    meta: { requiresAuth: true },
    children: [
      // Student routes - grouped for better code splitting
      createStudentRoute('', 'Dashboard', 'StudentDashboard'),
      createStudentRoute('/attendance', 'Attendance', 'AttendancePage'),
      createStudentRoute('/enter-code', 'EnterCode', 'EnterCodePage'),
      createStudentRoute('/grades', 'Grades', 'GradesPage'),
      createStudentRoute('/schedule', 'Schedule', 'SchedulePage'),
      createStudentRoute('/announcements', 'Announcements', 'AnnouncementsPage'),
      createStudentRoute('/finances', 'Finances', 'FinancesPage'),
      createStudentRoute('/alerts', 'Alerts', 'AlertsPage'),
      createStudentRoute('/messages', 'Messages', 'MessagesPage'),

      // Profile and ID-related routes - separate chunk for photo capture
      createStudentRoute('/id-card', 'IdCard', 'IdCardPage'),
      createStudentRoute('/profile-photo', 'ProfilePhoto', 'ProfilePhotoPage'),
      createStudentRoute('/profile', 'Profile', 'ProfilePage'),

      // Permission route
      createStudentRoute('/permission', 'Permission', 'PermissionPage'),

      // Teacher routes - grouped for optimal loading
      createTeacherRoute('/teacher', 'TeacherDashboard', 'TeacherDashboard'),
      createTeacherRoute('/teacher/attendance', 'TeacherAttendance', 'TeacherAttendance'),
      createTeacherRoute(
        '/teacher/attendance/generate',
        'TeacherGenerateCode',
        'TeacherGenerateCode'
      ),
      createTeacherRoute(
        '/teacher/attendance/manual',
        'TeacherManualAttendance',
        'TeacherManualAttendance'
      ),
      createTeacherRoute('/teacher/grades', 'TeacherGrades', 'TeacherGrades'),
      createTeacherRoute('/teacher/courses', 'TeacherCourses', 'TeacherCourses'),
    ],
  },

  // Error page - lazy loaded for better initial performance
  {
    path: '/:catchAll(.*)*',
    name: 'NotFound',
    component: () => import('@/pages/ErrorNotFound.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Navigation guards
router.beforeEach(
  async (to: RouteLocationNormalized, from: RouteLocationNormalized, next: NavigationGuardNext) => {
    console.log('Router navigation:', { to: to.path, from: from.path })

    try {
      const { isAuthenticated, checkAuthStatus, activeRole: authActiveRole } = useAuth()
      const { hasRole } = useRole()

      // Check auth status on app start
      if (!isAuthenticated.value) {
        await checkAuthStatus()
      }

      // Handle routes that require authentication
      if (to.meta.requiresAuth && !isAuthenticated.value) {
        next('/signin')
        return
      }

      // Handle routes that require guest (not authenticated)
      if (to.meta.requiresGuest && isAuthenticated.value) {
        // If authenticated and trying to access a guest page, redirect based on role
        if (authActiveRole.value === 'teacher') {
          next({ name: 'TeacherDashboard' })
        } else {
          next({ name: 'Dashboard' })
        }
        return
      }

      // If authenticated and navigating to Student Dashboard but role is teacher, redirect to Teacher Dashboard
      if (isAuthenticated.value && authActiveRole.value === 'teacher' && to.name === 'Dashboard') {
        next({ name: 'TeacherDashboard' })
        return
      }

      // Handle role-based access control for specific routes
      if (to.meta.role && authActiveRole.value && !hasRole(to.meta.role)) {
        console.warn(
          `Access denied: User with role '${authActiveRole.value}' does not have required role '${
            to.meta.role
          }' for route ${String(to.name)}`
        )
        // Redirect to appropriate home based on current role
        if (authActiveRole.value === 'teacher') {
          next({ name: 'TeacherDashboard' })
        } else {
          next({ name: 'Dashboard' })
        }
        return
      }

      // If a teacher tries to access a non-teacher route that isn't explicitly allowed for them
      if (
        isAuthenticated.value &&
        authActiveRole.value === 'teacher' &&
        to.name !== 'TeacherDashboard' &&
        !to.path.startsWith('/teacher') &&
        to.name !== 'Profile' &&
        to.name !== 'Settings'
      ) {
        // Allow profile/settings for all
        // Check if the route has a specific role meta that includes teacher
        const routeAllowsTeacher = to.meta.roles && to.meta.roles.includes('teacher')
        if (!routeAllowsTeacher && !to.meta.role) {
          console.warn(
            `Teacher accessing non-teacher route ${String(
              to.name
            )}, redirecting to TeacherDashboard.`
          )
          next({ name: 'TeacherDashboard' })
          return
        }
      }

      next()
    } catch (error) {
      console.error('Router navigation error:', error)
      // Fallback to signin on error
      next('/signin')
    }
  }
)

export default router
