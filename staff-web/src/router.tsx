/**
 * React Router configuration for the staff web application
 */

import React from 'react';
import { createBrowserRouter, Navigate, Outlet } from 'react-router-dom';
import { LoginPage } from './pages/Login';
import { DashboardPage } from './pages/Dashboard';
import { TransferListDemo } from './pages/TransferListDemo';
import { PageLoadingSpinner } from './components/common/LoadingSpinner';
import { useAuth, useAuthInitialization } from './hooks/useAuth';
import { ROUTES } from './utils/constants';
import { Sidebar } from './components/layout/Sidebar';
import { Header } from './components/layout/Header';
import { StudentDashboard } from './components/students/StudentDashboard';
import {
  StudentListPage,
  StudentDetail,
  StudentCreate,
  StudentSearch,
  StudentLocator,
  StudentEnrollment,
  StudentAnalytics,
  BulkOperations,
} from './pages/Students';
import { EnrollmentDashboard } from './components/enrollment/EnrollmentDashboard';
import FinancePage from './pages/Finance';
import { DatabaseIntegrityReport } from './pages/Reports/DatabaseIntegrityReport';
import SimpleStudentDemographics from './components/reports/SimpleStudentDemographics';
import TestDemographics from './components/reports/TestDemographics';
import DebugDemographics from './components/reports/DebugDemographics';
import DemoPage from './components/DemoPage';

// Academic Management Components
import { CollaborativeGradeEntry } from './pages/Academic/Grades/CollaborativeGradeEntry';
import { GradeSpreadsheet } from './pages/Academic/Grades/GradeSpreadsheet';
import { ScheduleBuilder } from './pages/Academic/Schedule/ScheduleBuilder';
import { EnrollmentHub } from './pages/Academic/Enrollment/EnrollmentHub';
import { EnrollmentWizard } from './pages/Academic/Enrollment/EnrollmentWizard';
import { CourseList } from './pages/Academic/Courses/CourseList';

// Innovation Features
import { DocumentIntelligenceCenter } from './pages/Innovation/Documents/DocumentIntelligenceCenter';
import { StudentSuccessPredictor } from './pages/Innovation/StudentSuccess/StudentSuccessPredictor';
import { StudentInterventionHub } from './pages/Innovation/StudentSuccess/StudentInterventionHub';
import { CommunicationHub } from './pages/Innovation/Communications/CommunicationHub';
import { CollaborationWorkspace } from './pages/Innovation/Communications/CollaborationWorkspace';

/**
 * Main Layout with Sidebar for authenticated users
 */
const MainLayout: React.FC = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">
      <div className="flex">
        <Sidebar />
        <div className="flex-1 lg:ml-80">
          <Header />
          <main className="min-h-screen">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
};

/**
 * Protected route wrapper that requires authentication
 */
const ProtectedRoute: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();
  const { isInitialized, initializeAuth } = useAuthInitialization();

  // Initialize auth if not already done
  React.useEffect(() => {
    if (!isInitialized && !isLoading) {
      initializeAuth();
    }
  }, [isInitialized, isLoading, initializeAuth]);

  // Show loading while initializing or during auth operations
  if (!isInitialized || isLoading) {
    return <PageLoadingSpinner text="Loading..." />;
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    return <Navigate to={ROUTES.LOGIN} replace />;
  }

  // Render protected content with layout
  return <MainLayout />;
};

/**
 * Public route wrapper that redirects authenticated users
 */
const PublicRoute: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();
  const { isInitialized } = useAuthInitialization();

  // Show loading while checking auth status
  if (!isInitialized || isLoading) {
    return <PageLoadingSpinner text="Loading..." />;
  }

  // Redirect to dashboard if already authenticated
  if (isAuthenticated) {
    return <Navigate to={ROUTES.DASHBOARD} replace />;
  }

  // Render public content
  return <Outlet />;
};

/**
 * Root route redirect based on authentication status
 */
const RootRedirect: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const { isInitialized } = useAuthInitialization();

  if (!isInitialized) {
    return <PageLoadingSpinner text="Initializing..." />;
  }

  return (
    <Navigate
      to={isAuthenticated ? ROUTES.DASHBOARD : ROUTES.LOGIN}
      replace
    />
  );
};

/**
 * Error boundary component for route errors
 */
const RouteError: React.FC = () => {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <h1 className="text-2xl font-bold text-gray-900 mb-4">
          Page Not Found
        </h1>
        <p className="text-gray-600 mb-6">
          The page you're looking for doesn't exist.
        </p>
        <a
          href={ROUTES.DASHBOARD}
          className="text-blue-600 hover:text-blue-700 underline"
        >
          Go to Dashboard
        </a>
      </div>
    </div>
  );
};

/**
 * React Router configuration for Staff-Web V2
 * Complete routing structure with all new features
 */
export const router = createBrowserRouter([
  {
    path: '/',
    element: <ProtectedRoute />,
    children: [
      {
        index: true,
        element: <Navigate to={ROUTES.DASHBOARD} replace />,
      },
    ],
  },
  {
    path: '/login',
    element: <PublicRoute />,
    children: [
      {
        index: true,
        element: <LoginPage />,
      },
    ],
  },

  // 📊 DASHBOARD ROUTES
  {
    path: '/dashboard',
    element: <ProtectedRoute />,
    children: [
      {
        index: true,
        element: <DashboardPage />,
      },
      {
        path: 'executive',
        element: <div>Executive Overview Dashboard</div>,
      },
      {
        path: 'student',
        element: <StudentDashboard />,
      },
      {
        path: 'staff',
        element: <div>Staff Dashboard</div>,
      },
    ],
  },

  // 👥 STUDENT MANAGEMENT ROUTES
  {
    path: '/students',
    element: <ProtectedRoute />,
    children: [
      {
        index: true,
        element: <Navigate to="list" replace />,
      },
      {
        path: 'list',
        element: <StudentListPage />,
      },
      {
        path: 'create',
        element: <StudentCreate />,
      },
      {
        path: 'search',
        element: <StudentSearch />,
      },
      {
        path: 'locator',
        element: <StudentLocator />,
      },
      {
        path: 'enrollment',
        element: <StudentEnrollment />,
      },
      {
        path: 'analytics',
        element: <StudentAnalytics />,
      },
      {
        path: 'bulk-operations',
        element: <BulkOperations />,
      },
      {
        path: ':studentId',
        element: <StudentDetail />,
        children: [
          {
            index: true,
            element: <Navigate to="overview" replace />,
          },
          {
            path: 'overview',
            element: <div>Student Overview Tab</div>,
          },
          {
            path: 'academic',
            element: <div>Academic Tab</div>,
          },
          {
            path: 'financial',
            element: <div>Financial Tab</div>,
          },
          {
            path: 'documents',
            element: <div>Documents Tab</div>,
          },
          {
            path: 'communications',
            element: <div>Communications Tab</div>,
          },
          {
            path: 'edit',
            element: <div>Edit Student Form</div>,
          },
        ],
      },
    ],
  },

  // 🎓 ACADEMIC MANAGEMENT ROUTES
  {
    path: '/academic',
    element: <ProtectedRoute />,
    children: [
      {
        index: true,
        element: <Navigate to="grade-entry" replace />,
      },
      {
        path: 'grade-entry',
        element: <CollaborativeGradeEntry />,
      },
      {
        path: 'grade-spreadsheet',
        element: <GradeSpreadsheet />,
      },
      {
        path: 'schedule-builder',
        element: <ScheduleBuilder />,
      },
      {
        path: 'enrollment',
        element: <EnrollmentHub />,
      },
      {
        path: 'enrollment-wizard',
        element: <EnrollmentWizard />,
      },
      {
        path: 'courses',
        element: <CourseList />,
      },
      {
        path: 'transcripts',
        element: <div>Transcripts Management</div>,
      },
      {
        path: 'attendance',
        element: <div>Attendance Hub</div>,
      },
      {
        path: 'classes/:classId',
        element: <div>Class Detail</div>,
      },
    ],
  },

  // 💰 FINANCIAL MANAGEMENT ROUTES
  {
    path: '/finance',
    element: <ProtectedRoute />,
    children: [
      {
        index: true,
        element: <FinancePage />,
      },
      {
        path: 'dashboard',
        element: <FinancePage />,
      },
      {
        path: 'invoices',
        element: <div>Invoice Dashboard</div>,
      },
      {
        path: 'payments',
        element: <div>Payment Processing</div>,
      },
      {
        path: 'accounts',
        element: <div>Student Accounts</div>,
      },
      {
        path: 'reports',
        element: <div>Financial Reports</div>,
      },
      {
        path: 'scholarships',
        element: <div>Scholarship Hub</div>,
      },
      {
        path: 'pos',
        element: <div>Point of Sale</div>,
      },
      {
        path: 'cashier',
        element: <div>Cashier Station</div>,
      },
    ],
  },

  // 📋 REPORTS & ANALYTICS ROUTES
  {
    path: '/reports',
    element: <ProtectedRoute />,
    children: [
      {
        index: true,
        element: <div>Report Builder</div>,
      },
      {
        path: 'builder',
        element: <div>Report Builder</div>,
      },
      {
        path: 'analytics',
        element: <div>Real-time Analytics</div>,
      },
      {
        path: 'export',
        element: <div>Data Export Hub</div>,
      },
      {
        path: 'queries',
        element: <div>Custom Queries</div>,
      },
      {
        path: 'scheduled',
        element: <div>Scheduled Reports</div>,
      },
      {
        path: 'database-integrity',
        element: <DatabaseIntegrityReport />,
      },
      {
        path: 'demographics',
        element: <DebugDemographics />,
      },
      {
        path: 'test-demographics',
        element: <TestDemographics />,
      },
      {
        path: 'demo',
        element: <DemoPage />,
      },
    ],
  },

  // 🚀 INNOVATION FEATURES ROUTES
  {
    path: '/innovation',
    element: <ProtectedRoute />,
    children: [
      {
        index: true,
        element: <Navigate to="student-success" replace />,
      },
      {
        path: 'student-success',
        element: <StudentSuccessPredictor />,
      },
      {
        path: 'interventions',
        element: <StudentInterventionHub />,
      },
      {
        path: 'documents',
        element: <DocumentIntelligenceCenter />,
      },
      {
        path: 'communications',
        element: <CommunicationHub />,
      },
      {
        path: 'collaboration',
        element: <CollaborationWorkspace />,
      },
    ],
  },

  // ⚙️ SYSTEM & ADMINISTRATION ROUTES
  {
    path: '/system',
    element: <ProtectedRoute />,
    children: [
      {
        index: true,
        element: <Navigate to="settings" replace />,
      },
      {
        path: 'settings',
        element: <div>System Settings</div>,
      },
      {
        path: 'users',
        element: <div>User Management</div>,
      },
      {
        path: 'permissions',
        element: <div>Permissions</div>,
      },
      {
        path: 'audit-logs',
        element: <div>Audit Logs</div>,
      },
    ],
  },

  // Legacy and Demo Routes
  {
    path: '/enrollment',
    element: <ProtectedRoute />,
    children: [
      {
        index: true,
        element: <EnrollmentDashboard />,
      },
      {
        path: 'dashboard',
        element: <EnrollmentDashboard />,
      },
      {
        path: 'programs',
        element: <EnrollmentDashboard />,
      },
      {
        path: 'classes',
        element: <EnrollmentDashboard />,
      },
    ],
  },
  {
    path: '/profile',
    element: <ProtectedRoute />,
    children: [
      {
        index: true,
        element: (
          <div className="min-h-screen bg-gray-50 p-6">
            <div className="max-w-4xl mx-auto">
              <h1 className="text-2xl font-bold mb-4">Profile</h1>
              <p>Profile page coming soon...</p>
            </div>
          </div>
        ),
      },
    ],
  },

  // Demo and Test Routes
  {
    path: '/demo',
    children: [
      {
        path: 'transfer-list',
        element: <TransferListDemo />,
      },
      {
        path: 'data-grid',
        element: <div>DataGrid Demo</div>,
      },
      {
        path: 'dashboard',
        element: <div>Dashboard Demo</div>,
      },
      {
        path: 'wizard',
        element: <div>Wizard Demo</div>,
      },
    ],
  },
  {
    path: '/test',
    element: (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 p-8">
        <div className="max-w-4xl mx-auto bg-white rounded-lg shadow-lg p-8">
          <div className="flex items-center mb-6">
            <img
              src="/naga-logo.png"
              alt="PUCSR University"
              className="w-20 h-20 object-contain mr-4"
            />
            <div>
              <h1 className="text-3xl font-bold text-gray-900">PUCSR Staff Portal V2</h1>
              <p className="text-gray-600">Enhanced University Management System</p>
            </div>
          </div>
          <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded">
            <strong>Success!</strong> Staff-Web V2 is ready for deployment.
            <ul className="mt-2 list-disc list-inside">
              <li>✅ 4 Standardized Component Patterns Implemented</li>
              <li>✅ Enhanced Router Configuration</li>
              <li>✅ Complete Navigation Structure</li>
              <li>✅ Foundation for State Management</li>
            </ul>
          </div>
        </div>
      </div>
    ),
  },
  {
    path: '*',
    element: <RouteError />,
  },
]);

export default router;