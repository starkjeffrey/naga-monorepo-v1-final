/**
 * Modern Router Configuration
 *
 * Complete routing system with beautiful sidebar navigation
 * replacing Django templates with React components
 */

import React from 'react';
import { createBrowserRouter, Outlet } from 'react-router-dom';
import { Sidebar } from '../components/layout/Sidebar';
import { Header } from '../components/layout/Header';
import { StudentDashboard } from '../components/students/StudentDashboard';
import { StudentList } from '../components/students/StudentList';
import { StudentDetail } from '../components/students/StudentDetail';
import { EnrollmentDashboard } from '../components/enrollment/EnrollmentDashboard';

// Main Layout Component with Sidebar
const MainLayout: React.FC = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">
      <div className="flex">
        {/* Beautiful Sidebar Navigation */}
        <Sidebar />

        {/* Main Content Area */}
        <div className="flex-1 lg:ml-80">
          {/* Header */}
          <Header />

          {/* Page Content */}
          <main className="min-h-screen">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
};

// Coming Soon placeholder for future features
const ComingSoonPage: React.FC<{ title: string; icon: string; description?: string }> = ({
  title,
  icon,
  description = "This section is under development and will be available in future updates."
}) => (
  <div className="min-h-screen flex items-center justify-center p-8">
    <div className="text-center max-w-md">
      <div className="text-8xl mb-8 opacity-50">{icon}</div>
      <h1 className="text-4xl font-bold text-gray-900 mb-4">{title}</h1>
      <p className="text-xl text-gray-600 mb-8">{description}</p>
      <div className="bg-white/90 backdrop-blur-sm rounded-3xl p-8 shadow-xl border border-gray-100">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Coming Soon:</h3>
        <ul className="text-left text-gray-600 space-y-3">
          <li className="flex items-center">
            <span className="w-2 h-2 bg-indigo-400 rounded-full mr-3"></span>
            Modern, intuitive interface
          </li>
          <li className="flex items-center">
            <span className="w-2 h-2 bg-indigo-400 rounded-full mr-3"></span>
            Advanced filtering and search
          </li>
          <li className="flex items-center">
            <span className="w-2 h-2 bg-indigo-400 rounded-full mr-3"></span>
            Real-time data updates
          </li>
          <li className="flex items-center">
            <span className="w-2 h-2 bg-indigo-400 rounded-full mr-3"></span>
            Export and reporting tools
          </li>
        </ul>
      </div>
    </div>
  </div>
);

// 404 Page
const NotFoundPage: React.FC = () => (
  <div className="min-h-screen flex items-center justify-center p-8">
    <div className="text-center">
      <div className="text-8xl mb-8 opacity-50">🔍</div>
      <h1 className="text-6xl font-bold text-gray-900 mb-4">404</h1>
      <h2 className="text-2xl font-semibold text-gray-700 mb-4">Page Not Found</h2>
      <p className="text-gray-600 mb-8">
        The page you're looking for doesn't exist or has been moved.
      </p>
      <button
        onClick={() => window.history.back()}
        className="bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white px-8 py-4 rounded-xl font-medium transition-all duration-200 hover:shadow-lg transform hover:scale-105"
      >
        Go Back
      </button>
    </div>
  </div>
);

// Create the router configuration
export const router = createBrowserRouter([
  {
    path: '/',
    element: <MainLayout />,
    children: [
      // Default redirect to student dashboard
      {
        index: true,
        element: <StudentDashboard />,
      },
      {
        path: 'dashboard',
        element: <StudentDashboard />,
      },

      // Student Management Routes
      {
        path: 'students',
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

      // Enrollment Management Routes
      {
        path: 'enrollment',
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

      // Academic Management Routes - Coming Soon
      {
        path: 'academic/*',
        element: (
          <ComingSoonPage
            title="Academic Records"
            icon="📚"
            description="Comprehensive academic record management, transcripts, and grade tracking."
          />
        ),
      },

      // Curriculum Management Routes - Coming Soon
      {
        path: 'curriculum/*',
        element: (
          <ComingSoonPage
            title="Curriculum Management"
            icon="🎓"
            description="Course catalog, program requirements, and curriculum planning tools."
          />
        ),
      },

      // Financial Management Routes - Coming Soon
      {
        path: 'finance/*',
        element: (
          <ComingSoonPage
            title="Financial Management"
            icon="💰"
            description="Billing, payments, scholarships, and financial aid administration."
          />
        ),
      },

      // Scheduling Routes - Coming Soon
      {
        path: 'scheduling/*',
        element: (
          <ComingSoonPage
            title="Scheduling & Calendar"
            icon="📅"
            description="Class schedules, room assignments, and academic calendar management."
          />
        ),
      },

      // Reports Routes - Coming Soon
      {
        path: 'reports/*',
        element: (
          <ComingSoonPage
            title="Reports & Analytics"
            icon="📊"
            description="Advanced reporting, analytics, and data visualization tools."
          />
        ),
      },

      // Settings Routes - Coming Soon
      {
        path: 'settings/*',
        element: (
          <ComingSoonPage
            title="System Settings"
            icon="⚙️"
            description="User management, system configuration, and administrative tools."
          />
        ),
      },

      // 404 Route
      {
        path: '*',
        element: <NotFoundPage />,
      },
    ],
  },
]);