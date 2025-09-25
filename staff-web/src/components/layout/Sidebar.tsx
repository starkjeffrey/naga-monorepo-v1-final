/**
 * Modern Sidebar Navigation Component
 *
 * Beautiful, responsive sidebar with:
 * - Modern glassmorphism design
 * - Smooth animations and hover effects
 * - Hierarchical navigation structure
 * - Collapsible sub-menus
 * - Active state indicators
 * - Mobile-responsive behavior
 */

import React, { useState } from 'react';
import { useLocation, Link } from 'react-router-dom';
import {
  LayoutDashboard,
  Users,
  GraduationCap,
  BookOpen,
  ClipboardList,
  DollarSign,
  Calendar,
  BarChart3,
  Settings,
  ChevronDown,
  ChevronRight,
  Home,
  UserCheck,
  Award,
  FileText,
  Clock,
  CreditCard,
  TrendingUp,
  Bell,
  LogOut,
  Menu,
  X
} from 'lucide-react';

interface NavigationItem {
  id: string;
  label: string;
  icon: React.ElementType;
  path?: string;
  badge?: string | number;
  children?: NavigationItem[];
}

const navigationItems: NavigationItem[] = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    icon: LayoutDashboard,
    path: '/students/dashboard'
  },
  {
    id: 'students',
    label: 'Student Management',
    icon: Users,
    badge: 'Hot',
    children: [
      {
        id: 'students-overview',
        label: 'Student Dashboard',
        icon: LayoutDashboard,
        path: '/students/dashboard'
      },
      {
        id: 'students-list',
        label: 'All Students',
        icon: Users,
        path: '/students/list'
      },
      {
        id: 'students-search',
        label: 'Quick Search',
        icon: Users,
        path: '/students/search'
      }
    ]
  },
  {
    id: 'enrollment',
    label: 'Enrollment',
    icon: UserCheck,
    children: [
      {
        id: 'enrollment-dashboard',
        label: 'Enrollment Dashboard',
        icon: LayoutDashboard,
        path: '/enrollment/dashboard'
      },
      {
        id: 'program-enrollments',
        label: 'Program Enrollments',
        icon: GraduationCap,
        path: '/enrollment/programs'
      },
      {
        id: 'class-enrollments',
        label: 'Class Enrollments',
        icon: BookOpen,
        path: '/enrollment/classes'
      }
    ]
  },
  {
    id: 'academic',
    label: 'Academic Records',
    icon: BookOpen,
    badge: 'New',
    children: [
      {
        id: 'transcripts',
        label: 'Transcripts',
        icon: FileText,
        path: '/academic/transcripts'
      },
      {
        id: 'grades',
        label: 'Grade Management',
        icon: Award,
        path: '/academic/grades'
      },
      {
        id: 'attendance',
        label: 'Attendance',
        icon: Clock,
        path: '/academic/attendance'
      }
    ]
  },
  {
    id: 'curriculum',
    label: 'Curriculum',
    icon: GraduationCap,
    children: [
      {
        id: 'courses',
        label: 'Course Catalog',
        icon: BookOpen,
        path: '/curriculum/courses'
      },
      {
        id: 'majors',
        label: 'Major Programs',
        icon: Award,
        path: '/curriculum/majors'
      },
      {
        id: 'requirements',
        label: 'Requirements',
        icon: ClipboardList,
        path: '/curriculum/requirements'
      }
    ]
  },
  {
    id: 'finance',
    label: 'Financial',
    icon: DollarSign,
    children: [
      {
        id: 'billing',
        label: 'Billing & Invoices',
        icon: FileText,
        path: '/finance/billing'
      },
      {
        id: 'payments',
        label: 'Payment Tracking',
        icon: CreditCard,
        path: '/finance/payments'
      },
      {
        id: 'scholarships',
        label: 'Scholarships',
        icon: Award,
        path: '/finance/scholarships'
      }
    ]
  },
  {
    id: 'scheduling',
    label: 'Scheduling',
    icon: Calendar,
    children: [
      {
        id: 'class-schedule',
        label: 'Class Schedule',
        icon: Calendar,
        path: '/scheduling/classes'
      },
      {
        id: 'rooms',
        label: 'Room Management',
        icon: Home,
        path: '/scheduling/rooms'
      },
      {
        id: 'calendar',
        label: 'Academic Calendar',
        icon: Calendar,
        path: '/scheduling/calendar'
      }
    ]
  },
  {
    id: 'reports',
    label: 'Reports & Analytics',
    icon: BarChart3,
    children: [
      {
        id: 'student-reports',
        label: 'Student Reports',
        icon: Users,
        path: '/reports/students'
      },
      {
        id: 'academic-reports',
        label: 'Academic Reports',
        icon: BookOpen,
        path: '/reports/academic'
      },
      {
        id: 'financial-reports',
        label: 'Financial Reports',
        icon: TrendingUp,
        path: '/reports/financial'
      }
    ]
  },
  {
    id: 'settings',
    label: 'Settings',
    icon: Settings,
    children: [
      {
        id: 'general-settings',
        label: 'General',
        icon: Settings,
        path: '/settings/general'
      },
      {
        id: 'user-management',
        label: 'Users & Roles',
        icon: Users,
        path: '/settings/users'
      },
      {
        id: 'notifications',
        label: 'Notifications',
        icon: Bell,
        path: '/settings/notifications'
      }
    ]
  }
];

export const Sidebar: React.FC = () => {
  const location = useLocation();
  const [expandedItems, setExpandedItems] = useState<string[]>(['students', 'enrollment']);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const toggleExpanded = (itemId: string) => {
    setExpandedItems(prev =>
      prev.includes(itemId)
        ? prev.filter(id => id !== itemId)
        : [...prev, itemId]
    );
  };

  const isActiveRoute = (path?: string) => {
    if (!path) return false;
    return location.pathname === path || location.pathname.startsWith(path);
  };

  const isParentActive = (item: NavigationItem) => {
    if (item.path && isActiveRoute(item.path)) return true;
    return item.children?.some(child => isActiveRoute(child.path)) || false;
  };

  const getBadgeColor = (badge?: string | number) => {
    if (badge === 'Hot') return 'bg-red-500 text-white';
    if (badge === 'New') return 'bg-green-500 text-white';
    return 'bg-blue-500 text-white';
  };

  const NavigationItemComponent: React.FC<{
    item: NavigationItem;
    level?: number;
    isExpanded?: boolean;
  }> = ({ item, level = 0, isExpanded }) => {
    const Icon = item.icon;
    const hasChildren = item.children && item.children.length > 0;
    const isExpand = expandedItems.includes(item.id);
    const isActive = isActiveRoute(item.path);
    const isParentItemActive = isParentActive(item);

    const handleClick = () => {
      if (hasChildren) {
        toggleExpanded(item.id);
      }
      setIsMobileMenuOpen(false);
    };

    const itemContent = (
      <div
        className={`group flex items-center justify-between w-full px-4 py-3 rounded-xl text-left transition-all duration-200 ${
          level === 0 ? 'mb-1' : 'mb-0.5 ml-4'
        } ${
          isActive
            ? 'bg-gradient-to-r from-indigo-500 to-purple-600 text-white shadow-lg transform scale-[1.02]'
            : isParentItemActive && level === 0
            ? 'bg-indigo-50 text-indigo-700 border border-indigo-100'
            : level > 0
            ? 'text-gray-600 hover:text-indigo-600 hover:bg-indigo-50'
            : 'text-gray-700 hover:text-indigo-600 hover:bg-gradient-to-r hover:from-indigo-50 hover:to-purple-50 hover:shadow-md'
        }`}
        onClick={handleClick}
      >
        <div className="flex items-center space-x-3 flex-1">
          <Icon className={`flex-shrink-0 transition-colors ${
            level === 0 ? 'w-6 h-6' : 'w-5 h-5'
          } ${
            isActive
              ? 'text-white'
              : isParentItemActive && level === 0
              ? 'text-indigo-600'
              : 'text-gray-500 group-hover:text-indigo-500'
          }`} />
          <span className={`font-medium transition-colors ${
            level === 0 ? 'text-base' : 'text-sm'
          }`}>
            {item.label}
          </span>
          {item.badge && (
            <span className={`px-2 py-1 text-xs font-bold rounded-full ${getBadgeColor(item.badge)}`}>
              {item.badge}
            </span>
          )}
        </div>
        {hasChildren && (
          <div className="flex-shrink-0">
            {isExpand ? (
              <ChevronDown className={`w-4 h-4 transition-colors ${
                isActive || isParentItemActive ? 'text-current' : 'text-gray-400 group-hover:text-indigo-500'
              }`} />
            ) : (
              <ChevronRight className={`w-4 h-4 transition-colors ${
                isActive || isParentItemActive ? 'text-current' : 'text-gray-400 group-hover:text-indigo-500'
              }`} />
            )}
          </div>
        )}
      </div>
    );

    return (
      <div>
        {item.path && (level > 0 || !hasChildren) ? (
          <Link to={item.path} className="block">
            {itemContent}
          </Link>
        ) : (
          <div className="w-full">
            {itemContent}
          </div>
        )}

        {hasChildren && isExpand && (
          <div className="mt-1 space-y-1">
            {item.children!.map((child) => (
              <NavigationItemComponent
                key={child.id}
                item={child}
                level={level + 1}
              />
            ))}
          </div>
        )}
      </div>
    );
  };

  return (
    <>
      {/* Mobile Menu Button */}
      <button
        onClick={() => setIsMobileMenuOpen(true)}
        className="lg:hidden fixed top-4 left-4 z-50 p-3 bg-white rounded-xl shadow-lg border border-gray-200"
      >
        <Menu className="w-6 h-6 text-gray-600" />
      </button>

      {/* Mobile Overlay */}
      {isMobileMenuOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black bg-opacity-50 z-40"
          onClick={() => setIsMobileMenuOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div className={`
        fixed lg:static inset-y-0 left-0 z-50 w-80 bg-white/95 backdrop-blur-xl
        border-r border-gray-200/50 shadow-2xl transition-transform duration-300 ease-in-out
        ${isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        {/* Header with NAGA Logo */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200/50">
          <div className="flex items-center space-x-4">
            <div className="relative">
              <img
                src="/naga-logo.png"
                alt="PUCSR University"
                className="w-16 h-16 object-contain drop-shadow-lg"
              />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900 bg-gradient-to-r from-orange-600 to-amber-600 bg-clip-text text-transparent">
                PUCSR Staff Portal
              </h1>
              <p className="text-sm text-gray-600 font-medium">University Management System</p>
            </div>
          </div>
          <button
            onClick={() => setIsMobileMenuOpen(false)}
            className="lg:hidden p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="p-4 flex-1 overflow-y-auto">
          <div className="space-y-2">
            {navigationItems.map((item) => (
              <NavigationItemComponent key={item.id} item={item} />
            ))}
          </div>
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200/50">
          <div className="flex items-center space-x-3 p-3 bg-gradient-to-r from-orange-50 via-amber-50 to-yellow-50 rounded-xl border border-orange-100">
            <div className="w-10 h-10 bg-gradient-to-br from-orange-500 to-amber-600 rounded-full flex items-center justify-center shadow-md">
              <span className="text-white font-semibold text-sm">AD</span>
            </div>
            <div className="flex-1">
              <p className="text-sm font-semibold text-gray-900">Admin User</p>
              <p className="text-xs text-orange-600 font-medium">PUCSR Staff Portal</p>
            </div>
            <button className="p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors">
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </>
  );
};