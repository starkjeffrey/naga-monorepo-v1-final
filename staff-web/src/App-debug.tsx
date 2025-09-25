/**
 * Debug App component to test basic React functionality
 */

import React from 'react';

function App() {
  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        <header className="bg-white shadow rounded-lg p-6 mb-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 14l9-5-9-5-9 5 9 5z" />
                </svg>
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">NAGA SIS</h1>
                <p className="text-sm text-gray-500">Student Information System</p>
              </div>
            </div>
            <div className="text-right">
              <p className="text-sm font-medium text-gray-900">Academic Dashboard</p>
              <p className="text-xs text-gray-500">{new Date().toLocaleDateString()}</p>
            </div>
          </div>
        </header>

        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Testees This Week</p>
                <p className="text-3xl font-bold text-blue-600 mt-1">142</p>
              </div>
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
            </div>
            <div className="mt-4 flex items-center text-sm">
              <span className="text-green-600 font-medium">↗ +23%</span>
              <span className="text-gray-600 ml-2">vs last week</span>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
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

          <div className="bg-white rounded-lg shadow p-6">
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

          <div className="bg-white rounded-lg shadow p-6">
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

        {/* Students by Term */}
        <div className="bg-white rounded-lg shadow">
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
                  <p className="text-2xl font-bold text-blue-600">1,247</p>
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

        {/* Footer */}
        <footer className="mt-8 text-center text-sm text-gray-500">
          <p>© 2024 NAGA School - System Status: <span className="text-green-600 font-medium">Operational</span></p>
        </footer>
      </div>
    </div>
  );
}

export default App;