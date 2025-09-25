/**
 * Header Component for Staff Web Application
 *
 * Clean, modern header with:
 * - Breadcrumb navigation
 * - Search functionality
 * - User profile and notifications
 * - Responsive design
 */

import React, { useState } from 'react';
import { useLocation } from 'react-router-dom';
import {
  Search,
  Bell,
  User,
  ChevronRight,
  Home,
  Settings,
  LogOut,
  Menu
} from 'lucide-react';

const routeNameMap: Record<string, string> = {
  '': 'Dashboard',
  'students': 'Students',
  'enrollment': 'Enrollment',
  'academic': 'Academic',
  'curriculum': 'Curriculum',
  'finance': 'Finance',
  'scheduling': 'Scheduling',
  'reports': 'Reports',
  'settings': 'Settings',
  'dashboard': 'Dashboard',
  'list': 'Student List',
  'detail': 'Student Details'
};

export const Header: React.FC = () => {
  const location = useLocation();
  const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const pathSegments = location.pathname.split('/').filter(Boolean);

  const breadcrumbs = pathSegments.map((segment, index) => ({
    name: routeNameMap[segment] || segment.charAt(0).toUpperCase() + segment.slice(1),
    path: '/' + pathSegments.slice(0, index + 1).join('/')
  }));

  return (
    <header className="bg-white/90 backdrop-blur-xl border-b border-gray-200/50 shadow-sm">
      <div className="px-6 py-4">
        <div className="flex items-center justify-between">
          {/* Left Section - Breadcrumbs */}
          <div className="flex items-center space-x-4">
            <nav className="flex items-center space-x-2 text-sm">
              <div className="flex items-center space-x-3 text-gray-500">
                <img
                  src="/naga-logo.png"
                  alt="PUCSR"
                  className="w-6 h-6 object-contain"
                />
                <span className="font-semibold">PUCSR Staff Portal</span>
              </div>
              {breadcrumbs.map((breadcrumb, index) => (
                <div key={breadcrumb.path} className="flex items-center space-x-2">
                  <ChevronRight className="w-4 h-4 text-gray-400" />
                  <span className={`${
                    index === breadcrumbs.length - 1
                      ? 'text-indigo-600 font-semibold'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}>
                    {breadcrumb.name}
                  </span>
                </div>
              ))}
            </nav>
          </div>

          {/* Right Section - Search, Notifications, Profile */}
          <div className="flex items-center space-x-4">
            {/* Search */}
            <div className="hidden md:block relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Search className="h-4 w-4 text-gray-400" />
              </div>
              <input
                type="text"
                placeholder="Quick search..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="block w-64 pl-10 pr-3 py-2 border border-gray-200 rounded-xl text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent bg-gray-50/50"
              />
            </div>

            {/* Notifications */}
            <div className="relative">
              <button className="relative p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-xl transition-colors">
                <Bell className="h-5 w-5" />
                {/* Notification Badge */}
                <span className="absolute top-0 right-0 -mt-1 -mr-1 px-2 py-1 text-xs font-bold text-white bg-red-500 rounded-full">
                  3
                </span>
              </button>
            </div>

            {/* User Profile Dropdown */}
            <div className="relative">
              <button
                onClick={() => setIsProfileMenuOpen(!isProfileMenuOpen)}
                className="flex items-center space-x-3 p-2 text-gray-700 hover:bg-gray-100 rounded-xl transition-colors"
              >
                <div className="w-8 h-8 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-full flex items-center justify-center">
                  <span className="text-white font-semibold text-sm">AD</span>
                </div>
                <div className="hidden lg:block text-left">
                  <p className="text-sm font-semibold text-gray-900">Admin User</p>
                  <p className="text-xs text-gray-500">Administrator</p>
                </div>
              </button>

              {/* Profile Dropdown Menu */}
              {isProfileMenuOpen && (
                <>
                  <div
                    className="fixed inset-0 z-10"
                    onClick={() => setIsProfileMenuOpen(false)}
                  />
                  <div className="absolute right-0 mt-2 w-48 bg-white rounded-xl shadow-lg border border-gray-200 z-20">
                    <div className="py-1">
                      <div className="px-4 py-3 border-b border-gray-100">
                        <p className="text-sm font-semibold text-gray-900">Admin User</p>
                        <p className="text-xs text-gray-500">admin@naga.edu.kh</p>
                      </div>
                      <button className="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-50">
                        <User className="w-4 h-4 mr-3" />
                        Profile Settings
                      </button>
                      <button className="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-50">
                        <Settings className="w-4 h-4 mr-3" />
                        Account Settings
                      </button>
                      <div className="border-t border-gray-100">
                        <button className="flex items-center w-full px-4 py-2 text-sm text-red-600 hover:bg-red-50">
                          <LogOut className="w-4 h-4 mr-3" />
                          Sign Out
                        </button>
                      </div>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Mobile Search */}
        <div className="md:hidden mt-4">
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Search className="h-4 w-4 text-gray-400" />
            </div>
            <input
              type="text"
              placeholder="Search students, courses..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="block w-full pl-10 pr-3 py-2 border border-gray-200 rounded-xl text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent bg-gray-50/50"
            />
          </div>
        </div>
      </div>
    </header>
  );
};