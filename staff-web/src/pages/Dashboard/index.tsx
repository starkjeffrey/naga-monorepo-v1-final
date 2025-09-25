/**
 * Dashboard page component - Professional SIS Dashboard
 */

import React from 'react';
import { Button } from 'antd';
import { LogoutOutlined } from '@ant-design/icons';
import { useAuth } from '../../hooks/useAuth';

/**
 * Main SIS dashboard page showing key academic metrics
 */
export const DashboardPage: React.FC = () => {
  const { logout } = useAuth();
  const currentDate = new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });

  const lastUpdated = new Date().toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit'
  });

  const handleLogout = () => {
    logout();
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-blue-700 rounded-lg flex items-center justify-center">
                  <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 14l9-5-9-5-9 5 9 5z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 14l6.16-3.422a12.083 12.083 0 01.665 6.479A11.952 11.952 0 0012 20.055a11.952 11.952 0 00-6.824-2.998 12.078 12.078 0 01.665-6.479L12 14z" />
                  </svg>
                </div>
                <div>
                  <h1 className="text-xl font-bold text-gray-900">NAGA SIS</h1>
                  <p className="text-sm text-gray-500">Student Information System</p>
                </div>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className="text-right">
                <p className="text-sm font-medium text-gray-900">Academic Dashboard</p>
                <p className="text-xs text-gray-500">{currentDate}</p>
              </div>
              <Button
                type="primary"
                danger
                icon={<LogoutOutlined />}
                onClick={handleLogout}
              >
                Sign Out
              </Button>
            </div>
          </div>
        </div>
      </header>

      <div className="flex h-screen">
        {/* Sidebar */}
        <aside className="w-64 bg-white shadow-sm border-r border-gray-200">
          <nav className="mt-6 px-4">
            <div className="space-y-2">
              <a href="#" className="bg-blue-700 text-white px-3 py-2 rounded-lg flex items-center space-x-3 text-sm font-medium">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                <span>Dashboard</span>
              </a>
              <a href="#" className="text-gray-700 hover:bg-gray-100 px-3 py-2 rounded-lg flex items-center space-x-3 text-sm">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z" />
                </svg>
                <span>Students</span>
              </a>
              <a href="#" className="text-gray-700 hover:bg-gray-100 px-3 py-2 rounded-lg flex items-center space-x-3 text-sm">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3a2 2 0 012-2h4a2 2 0 012 2v4m-6 0V3a2 2 0 012-2h4a2 2 0 012 2v4m-6 0h8m-9 0H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5z" />
                </svg>
                <span>Schedule</span>
              </a>
              <a href="#" className="text-gray-700 hover:bg-gray-100 px-3 py-2 rounded-lg flex items-center space-x-3 text-sm">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>Testing</span>
              </a>
              <a href="#" className="text-gray-700 hover:bg-gray-100 px-3 py-2 rounded-lg flex items-center space-x-3 text-sm">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                </svg>
                <span>Curriculum</span>
              </a>
              <a href="#" className="text-gray-700 hover:bg-gray-100 px-3 py-2 rounded-lg flex items-center space-x-3 text-sm">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                <span>Reports</span>
              </a>
              <a href="#" className="text-gray-700 hover:bg-gray-100 px-3 py-2 rounded-lg flex items-center space-x-3 text-sm">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                <span>Settings</span>
              </a>
            </div>
          </nav>
        </aside>

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto">
          <div className="p-8">
            {/* Page Title */}
            <div className="mb-8">
              <h2 className="text-2xl font-bold text-gray-900">Academic Dashboard</h2>
              <p className="text-gray-600 mt-1">Overview of current academic activities and enrollment</p>
            </div>

            {/* Key Metrics Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
              {/* Weekly Testing */}
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Testees This Week</p>
                    <p className="text-3xl font-bold text-blue-700 mt-1">142</p>
                  </div>
                  <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                    <svg className="w-6 h-6 text-blue-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                </div>
                <div className="mt-4 flex items-center text-sm">
                  <span className="text-green-600 font-medium">↗ +23%</span>
                  <span className="text-gray-600 ml-2">vs last week</span>
                </div>
              </div>

              {/* Total Active Students */}
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Active Students</p>
                    <p className="text-3xl font-bold text-green-600 mt-1">1,847</p>
                  </div>
                  <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                    <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z" />
                    </svg>
                  </div>
                </div>
                <div className="mt-4 flex items-center text-sm">
                  <span className="text-green-600 font-medium">↗ +5.2%</span>
                  <span className="text-gray-600 ml-2">this term</span>
                </div>
              </div>

              {/* Current Term Classes */}
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Active Classes</p>
                    <p className="text-3xl font-bold text-yellow-600 mt-1">89</p>
                  </div>
                  <div className="w-12 h-12 bg-yellow-100 rounded-lg flex items-center justify-center">
                    <svg className="w-6 h-6 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2-2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                    </svg>
                  </div>
                </div>
                <div className="mt-4 flex items-center text-sm">
                  <span className="text-gray-600">across all levels</span>
                </div>
              </div>

              {/* Pending Enrollments */}
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Pending Enrollments</p>
                    <p className="text-3xl font-bold text-purple-600 mt-1">37</p>
                  </div>
                  <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                    <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                </div>
                <div className="mt-4 flex items-center text-sm">
                  <span className="text-purple-600 font-medium">requires review</span>
                </div>
              </div>
            </div>

            {/* Two-Column Layout */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* Students by Term */}
              <div className="bg-white rounded-lg shadow-sm border border-gray-200">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900">Students by Term</h3>
                  <p className="text-sm text-gray-600">Current enrollment breakdown</p>
                </div>
                <div className="p-6">
                  <div className="space-y-4">
                    <div className="flex items-center justify-between p-4 bg-blue-50 rounded-lg">
                      <div>
                        <p className="font-semibold text-gray-900">Fall 2024 (Current)</p>
                        <p className="text-sm text-gray-600">Sep 1 - Dec 15, 2024</p>
                      </div>
                      <div className="text-right">
                        <p className="text-2xl font-bold text-blue-700">1,247</p>
                        <p className="text-sm text-gray-600">students</p>
                      </div>
                    </div>

                    <div className="flex items-center justify-between p-4 bg-green-50 rounded-lg">
                      <div>
                        <p className="font-semibold text-gray-900">Winter 2025 (Next)</p>
                        <p className="text-sm text-gray-600">Jan 6 - Apr 20, 2025</p>
                      </div>
                      <div className="text-right">
                        <p className="text-2xl font-bold text-green-600">389</p>
                        <p className="text-sm text-gray-600">enrolled</p>
                      </div>
                    </div>

                    <div className="flex items-center justify-between p-4 bg-yellow-50 rounded-lg">
                      <div>
                        <p className="font-semibold text-gray-900">Spring 2025</p>
                        <p className="text-sm text-gray-600">May 1 - Aug 15, 2025</p>
                      </div>
                      <div className="text-right">
                        <p className="text-2xl font-bold text-yellow-600">211</p>
                        <p className="text-sm text-gray-600">pre-enrolled</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Key Dates */}
              <div className="bg-white rounded-lg shadow-sm border border-gray-200">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900">Upcoming Key Dates</h3>
                  <p className="text-sm text-gray-600">Important academic deadlines</p>
                </div>
                <div className="p-6">
                  <div className="space-y-4">
                    <div className="flex items-start space-x-4 p-4 bg-red-50 border-l-4 border-red-400 rounded-r-lg">
                      <div className="flex-shrink-0">
                        <svg className="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3a2 2 0 012-2h4a2 2 0 012 2v4m-6 0V3a2 2 0 012-2h4a2 2 0 012 2v4m-6 0h8m-9 0H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5z" />
                        </svg>
                      </div>
                      <div className="flex-1">
                        <p className="font-semibold text-gray-900">Fall Term End</p>
                        <p className="text-sm text-gray-600">December 15, 2024</p>
                        <p className="text-xs text-red-600 mt-1">3 weeks remaining</p>
                      </div>
                    </div>

                    <div className="flex items-start space-x-4 p-4 bg-blue-50 border-l-4 border-blue-400 rounded-r-lg">
                      <div className="flex-shrink-0">
                        <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3a2 2 0 012-2h4a2 2 0 012 2v4m-6 0V3a2 2 0 012-2h4a2 2 0 012 2v4m-6 0h8m-9 0H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5z" />
                        </svg>
                      </div>
                      <div className="flex-1">
                        <p className="font-semibold text-gray-900">Winter Registration Opens</p>
                        <p className="text-sm text-gray-600">December 1, 2024</p>
                        <p className="text-xs text-blue-600 mt-1">Opens in 1 week</p>
                      </div>
                    </div>

                    <div className="flex items-start space-x-4 p-4 bg-green-50 border-l-4 border-green-400 rounded-r-lg">
                      <div className="flex-shrink-0">
                        <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3a2 2 0 012-2h4a2 2 0 012 2v4m-6 0V3a2 2 0 012-2h4a2 2 0 012 2v4m-6 0h8m-9 0H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5z" />
                        </svg>
                      </div>
                      <div className="flex-1">
                        <p className="font-semibold text-gray-900">Winter Term Begins</p>
                        <p className="text-sm text-gray-600">January 6, 2025</p>
                        <p className="text-xs text-green-600 mt-1">6 weeks away</p>
                      </div>
                    </div>

                    <div className="flex items-start space-x-4 p-4 bg-purple-50 border-l-4 border-purple-400 rounded-r-lg">
                      <div className="flex-shrink-0">
                        <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5h2a2 2 0 012 2v6a2 2 0 01-2 2h-2a2 2 0 01-2-2V7a2 2 0 012-2z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17h6" />
                        </svg>
                      </div>
                      <div className="flex-1">
                        <p className="font-semibold text-gray-900">Level Testing Period</p>
                        <p className="text-sm text-gray-600">Dec 2-13, 2024</p>
                        <p className="text-xs text-purple-600 mt-1">Ongoing</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Recent Activity */}
            <div className="mt-8 bg-white rounded-lg shadow-sm border border-gray-200">
              <div className="px-6 py-4 border-b border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900">Recent System Activity</h3>
                <p className="text-sm text-gray-600">Latest updates and notifications</p>
              </div>
              <div className="p-6">
                <div className="space-y-3">
                  <div className="flex items-center space-x-3 p-3 bg-blue-50 rounded-lg">
                    <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
                    </svg>
                    <div className="flex-1">
                      <p className="text-sm font-medium">12 new student enrollments processed</p>
                      <p className="text-xs text-gray-600">2 hours ago</p>
                    </div>
                  </div>

                  <div className="flex items-center space-x-3 p-3 bg-green-50 rounded-lg">
                    <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <div className="flex-1">
                      <p className="text-sm font-medium">Level testing completed for 47 students</p>
                      <p className="text-xs text-gray-600">4 hours ago</p>
                    </div>
                  </div>

                  <div className="flex items-center space-x-3 p-3 bg-yellow-50 rounded-lg">
                    <svg className="w-5 h-5 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3a2 2 0 012-2h4a2 2 0 012 2v4m-6 0V3a2 2 0 012-2h4a2 2 0 012 2v4m-6 0h8m-9 0H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5z" />
                    </svg>
                    <div className="flex-1">
                      <p className="text-sm font-medium">Winter 2025 schedule published</p>
                      <p className="text-xs text-gray-600">Yesterday</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Footer */}
          <footer className="bg-white border-t border-gray-200 py-4 mt-8">
            <div className="px-8">
              <div className="flex items-center justify-between">
                <p className="text-sm text-gray-600">© 2024 NAGA School. All rights reserved.</p>
                <div className="flex items-center space-x-6 text-sm text-gray-600">
                  <span>System Status: <span className="text-green-600 font-medium">Operational</span></span>
                  <span>Last Updated: <span>{lastUpdated}</span></span>
                </div>
              </div>
            </div>
          </footer>
        </main>
      </div>
    </div>
  );
};

export default DashboardPage;