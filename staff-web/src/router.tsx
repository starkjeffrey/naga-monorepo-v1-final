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
import { StudentList } from './components/students/StudentList';
import { StudentDetail } from './components/students/StudentDetail';
import { EnrollmentDashboard } from './components/enrollment/EnrollmentDashboard';

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
 * React Router configuration
 */
export const router = createBrowserRouter([
  {
    path: '/',
    element: <ProtectedRoute />,
    children: [
      {
        index: true,
        element: <StudentDashboard />,
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
  {
    path: '/dashboard',
    element: <ProtectedRoute />,
    children: [
      {
        index: true,
        element: <StudentDashboard />,
      },
    ],
  },
  {
    path: '/students',
    element: <ProtectedRoute />,
    children: [
      {
        index: true,
        element: <StudentDashboard />,
      },
      {
        path: 'dashboard',
        element: <StudentDashboard />,
      },
      {
        path: 'list',
        element: <StudentList />,
      },
      {
        path: 'search',
        element: <StudentList />,
      },
      {
        path: ':studentId',
        element: <StudentDetail />,
      },
    ],
  },
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
  {
    path: '/demo/transfer-list',
    element: <TransferListDemo />,
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
              <h1 className="text-3xl font-bold text-gray-900">PUCSR Staff Portal</h1>
              <p className="text-gray-600">University Management System</p>
            </div>
          </div>
          <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded">
            <strong>Success!</strong> The PUCSR interface is working correctly.
            <ul className="mt-2 list-disc list-inside">
              <li>✅ Main app file fixed (main.tsx)</li>
              <li>✅ PUCSR branding applied</li>
              <li>✅ Dragon logo loaded</li>
              <li>✅ Dependencies installed</li>
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