/**
 * Student Management Dashboard
 *
 * A comprehensive overview screen with rich analytics and visual insights:
 * - Key metrics with trend indicators
 * - Interactive charts and visualizations
 * - Quick actions and shortcuts
 * - Recent activity feeds
 * - Status breakdowns with visual indicators
 * - Academic progress tracking
 * - Financial overview
 * - Alert system for issues requiring attention
 */

import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  TrendingDown,
  Users,
  GraduationCap,
  AlertTriangle,
  CheckCircle,
  Clock,
  DollarSign,
  BookOpen,
  Crown,
  Mail,
  Phone,
  FileText,
  Calendar,
  Award,
  Activity,
  Eye,
  Plus,
  Search,
  Filter,
  BarChart3,
  PieChart,
  Target,
  Zap,
} from 'lucide-react';
import { StudentService } from '../../services/student.service';

interface DashboardMetric {
  title: string;
  value: number;
  change?: number;
  changeType: 'increase' | 'decrease' | 'neutral';
  icon: React.ElementType;
  color: string;
  trend?: number[];
}

interface AlertItem {
  id: string;
  type: 'warning' | 'error' | 'info';
  title: string;
  description: string;
  count?: number;
  action?: string;
}

interface ActivityItem {
  id: string;
  type: string;
  title: string;
  description: string;
  timestamp: string;
  user?: string;
  metadata?: Record<string, any>;
}

export const StudentDashboard: React.FC = () => {
  // State management
  const [metrics, setMetrics] = useState<DashboardMetric[]>([]);
  const [enrollmentStats, setEnrollmentStats] = useState<any>(null);
  const [curriculumStats, setCurriculumStats] = useState<any>(null);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [recentActivity] = useState<ActivityItem[]>([
    {
      id: '1',
      type: 'enrollment',
      title: 'New Student Enrolled',
      description: 'CHAN Sopheak enrolled in Computer Science program',
      timestamp: '2 minutes ago',
      user: 'Admin User',
    },
    {
      id: '2',
      type: 'major_change',
      title: 'Major Declaration Updated',
      description: 'LIM Dara changed major from Business to Economics',
      timestamp: '15 minutes ago',
      user: 'Academic Advisor',
    },
    {
      id: '3',
      type: 'status_change',
      title: 'Student Status Change',
      description: 'PICH Bopha status changed to Graduated',
      timestamp: '1 hour ago',
      user: 'Registrar',
    },
    {
      id: '4',
      type: 'contact_update',
      title: 'Contact Information Updated',
      description: 'Emergency contact updated for SAO Vichet',
      timestamp: '2 hours ago',
      user: 'Student Services',
    },
  ]);
  const [loading, setLoading] = useState(true);

  // Load dashboard data
  useEffect(() => {
    const loadDashboardData = async () => {
      try {
        setLoading(true);

        const [enrollmentData, curriculumData] = await Promise.all([
          StudentService.getEnrollmentStatistics(),
          StudentService.getCurriculumStatistics(),
        ]);

        setEnrollmentStats(enrollmentData);
        setCurriculumStats(curriculumData);

        // Create metrics from API data
        const dashboardMetrics: DashboardMetric[] = [
          {
            title: 'Total Students',
            value: enrollmentData.total_students,
            change: 12,
            changeType: 'increase',
            icon: Users,
            color: 'blue',
            trend: [45, 52, 48, 61, 55, 67, 69, 73, 78, 82, 85, enrollmentData.total_students],
          },
          {
            title: 'Active Students',
            value: enrollmentData.active_students,
            change: 8,
            changeType: 'increase',
            icon: CheckCircle,
            color: 'green',
            trend: [38, 45, 42, 55, 48, 58, 62, 65, 71, 75, 78, enrollmentData.active_students],
          },
          {
            title: 'Current Enrollments',
            value: enrollmentData.current_term_enrollments,
            change: 15,
            changeType: 'increase',
            icon: BookOpen,
            color: 'purple',
            trend: [120, 135, 128, 145, 138, 155, 162, 168, 175, 182, 188, enrollmentData.current_term_enrollments],
          },
          {
            title: 'Active Majors',
            value: curriculumData.active_majors,
            change: 0,
            changeType: 'neutral',
            icon: GraduationCap,
            color: 'orange',
            trend: [12, 12, 11, 12, 12, 12, 13, 12, 12, 12, 12, curriculumData.active_majors],
          },
        ];

        setMetrics(dashboardMetrics);

        // Generate alerts based on data
        const generatedAlerts: AlertItem[] = [];

        // Check for inactive students
        const inactiveCount = enrollmentData.total_students - enrollmentData.active_students;
        if (inactiveCount > 0) {
          generatedAlerts.push({
            id: 'inactive_students',
            type: 'warning',
            title: 'Inactive Students',
            description: `${inactiveCount} students are currently inactive`,
            count: inactiveCount,
            action: 'Review Status',
          });
        }

        // Check for major conflicts (simulated)
        generatedAlerts.push({
          id: 'major_conflicts',
          type: 'error',
          title: 'Major Conflicts',
          description: '3 students have conflicts between declared and enrollment majors',
          count: 3,
          action: 'Resolve Conflicts',
        });

        // Check for missing contacts (simulated)
        generatedAlerts.push({
          id: 'missing_contacts',
          type: 'info',
          title: 'Missing Emergency Contacts',
          description: '15 students are missing emergency contact information',
          count: 15,
          action: 'Update Contacts',
        });

        setAlerts(generatedAlerts);
      } catch (error) {
        console.error('Failed to load dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };

    loadDashboardData();
  }, []);

  const getColorClasses = (color: string) => {
    const colorMap = {
      blue: {
        bg: 'bg-blue-500',
        lightBg: 'bg-blue-50',
        text: 'text-blue-600',
        border: 'border-blue-200',
      },
      green: {
        bg: 'bg-green-500',
        lightBg: 'bg-green-50',
        text: 'text-green-600',
        border: 'border-green-200',
      },
      purple: {
        bg: 'bg-purple-500',
        lightBg: 'bg-purple-50',
        text: 'text-purple-600',
        border: 'border-purple-200',
      },
      orange: {
        bg: 'bg-orange-500',
        lightBg: 'bg-orange-50',
        text: 'text-orange-600',
        border: 'border-orange-200',
      },
    };
    return colorMap[color as keyof typeof colorMap] || colorMap.blue;
  };

  const getAlertIcon = (type: AlertItem['type']) => {
    switch (type) {
      case 'error':
        return <AlertTriangle className="h-5 w-5 text-red-500" />;
      case 'warning':
        return <Clock className="h-5 w-5 text-yellow-500" />;
      case 'info':
        return <Eye className="h-5 w-5 text-blue-500" />;
      default:
        return <Eye className="h-5 w-5 text-gray-500" />;
    }
  };

  const getActivityIcon = (type: string) => {
    switch (type) {
      case 'enrollment':
        return <Plus className="h-4 w-4 text-green-500" />;
      case 'major_change':
        return <GraduationCap className="h-4 w-4 text-blue-500" />;
      case 'status_change':
        return <Activity className="h-4 w-4 text-orange-500" />;
      case 'contact_update':
        return <Phone className="h-4 w-4 text-purple-500" />;
      default:
        return <FileText className="h-4 w-4 text-gray-500" />;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="animate-pulse space-y-6">
            <div className="h-8 bg-gray-200 rounded w-1/4"></div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-32 bg-gray-200 rounded-lg"></div>
              ))}
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2 h-96 bg-gray-200 rounded-lg"></div>
              <div className="h-96 bg-gray-200 rounded-lg"></div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-6">
              <div className="relative">
                <img
                  src="/naga-logo.png"
                  alt="PUCSR University"
                  className="w-20 h-20 object-contain drop-shadow-xl"
                />
              </div>
              <div>
                <h1 className="text-3xl font-bold text-gray-900">Student Management Dashboard</h1>
                <p className="mt-1 text-sm text-gray-600">
                  PUCSR University • Comprehensive overview of student data, enrollments, and academic progress
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <button className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50">
                <BarChart3 className="mr-2 h-4 w-4" />
                Reports
              </button>
              <button className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700">
                <Plus className="mr-2 h-4 w-4" />
                Add Student
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {metrics.map((metric, index) => {
            const Icon = metric.icon;
            const colors = getColorClasses(metric.color);

            return (
              <div key={index} className="bg-white overflow-hidden shadow-sm rounded-lg border">
                <div className="p-6">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center">
                      <div className={`${colors.lightBg} rounded-lg p-3`}>
                        <Icon className={`h-6 w-6 ${colors.text}`} />
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-2xl font-bold text-gray-900">{metric.value.toLocaleString()}</p>
                      {metric.change !== undefined && (
                        <div className="flex items-center justify-end">
                          {metric.changeType === 'increase' ? (
                            <TrendingUp className="h-4 w-4 text-green-500 mr-1" />
                          ) : metric.changeType === 'decrease' ? (
                            <TrendingDown className="h-4 w-4 text-red-500 mr-1" />
                          ) : null}
                          <span
                            className={`text-sm font-medium ${
                              metric.changeType === 'increase'
                                ? 'text-green-600'
                                : metric.changeType === 'decrease'
                                ? 'text-red-600'
                                : 'text-gray-600'
                            }`}
                          >
                            {metric.change > 0 ? '+' : ''}{metric.change}%
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="mt-4">
                    <h3 className="text-sm font-medium text-gray-600">{metric.title}</h3>
                    {metric.trend && (
                      <div className="mt-2">
                        <div className="flex items-end space-x-1 h-8">
                          {metric.trend.map((value, i) => (
                            <div
                              key={i}
                              className={`${colors.bg} rounded-sm flex-1 opacity-60`}
                              style={{
                                height: `${(value / Math.max(...metric.trend!)) * 100}%`,
                                minHeight: '2px',
                              }}
                            />
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Charts and Analytics */}
          <div className="lg:col-span-2 space-y-6">
            {/* Status Distribution */}
            <div className="bg-white shadow-sm rounded-lg border">
              <div className="px-6 py-4 border-b border-gray-200">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-medium text-gray-900">Student Status Distribution</h3>
                  <PieChart className="h-5 w-5 text-gray-400" />
                </div>
              </div>
              <div className="p-6">
                {enrollmentStats?.status_breakdown && (
                  <div className="space-y-4">
                    {Object.entries(enrollmentStats.status_breakdown).map(([status, count]) => (
                      <div key={status} className="flex items-center justify-between">
                        <div className="flex items-center">
                          <div
                            className={`w-4 h-4 rounded-full mr-3 ${StudentService.getStatusBadgeClass(
                              status
                            ).replace('text-', 'bg-').replace('-800', '-500').split(' ')[0]}`}
                          />
                          <span className="text-sm font-medium text-gray-900">
                            {StudentService.formatStudentStatus(status)}
                          </span>
                        </div>
                        <div className="flex items-center">
                          <span className="text-sm text-gray-600 mr-2">{count}</span>
                          <div className="w-24 bg-gray-200 rounded-full h-2">
                            <div
                              className="bg-blue-500 h-2 rounded-full"
                              style={{
                                width: `${(Number(count) / enrollmentStats.total_students) * 100}%`,
                              }}
                            />
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Division Breakdown */}
            <div className="bg-white shadow-sm rounded-lg border">
              <div className="px-6 py-4 border-b border-gray-200">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-medium text-gray-900">Students by Division</h3>
                  <BarChart3 className="h-5 w-5 text-gray-400" />
                </div>
              </div>
              <div className="p-6">
                {enrollmentStats?.division_breakdown && (
                  <div className="space-y-4">
                    {Object.entries(enrollmentStats.division_breakdown).map(([division, count], index) => (
                      <div key={division} className="flex items-center justify-between">
                        <div className="flex items-center">
                          <div className={`w-4 h-4 rounded-full mr-3 ${
                            index === 0 ? 'bg-blue-500' :
                            index === 1 ? 'bg-green-500' :
                            index === 2 ? 'bg-purple-500' :
                            index === 3 ? 'bg-orange-500' : 'bg-gray-500'
                          }`} />
                          <span className="text-sm font-medium text-gray-900">{division}</span>
                        </div>
                        <div className="flex items-center">
                          <span className="text-sm text-gray-600 mr-2">{count}</span>
                          <div className="w-32 bg-gray-200 rounded-full h-2">
                            <div
                              className={`h-2 rounded-full ${
                                index === 0 ? 'bg-blue-500' :
                                index === 1 ? 'bg-green-500' :
                                index === 2 ? 'bg-purple-500' :
                                index === 3 ? 'bg-orange-500' : 'bg-gray-500'
                              }`}
                              style={{
                                width: `${(Number(count) / Math.max(...Object.values(enrollmentStats.division_breakdown))) * 100}%`,
                              }}
                            />
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Alerts */}
            <div className="bg-white shadow-sm rounded-lg border">
              <div className="px-6 py-4 border-b border-gray-200">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-medium text-gray-900">Alerts & Issues</h3>
                  <AlertTriangle className="h-5 w-5 text-orange-400" />
                </div>
              </div>
              <div className="p-6">
                {alerts.length > 0 ? (
                  <div className="space-y-4">
                    {alerts.map((alert) => (
                      <div
                        key={alert.id}
                        className={`p-4 rounded-lg border ${
                          alert.type === 'error'
                            ? 'bg-red-50 border-red-200'
                            : alert.type === 'warning'
                            ? 'bg-yellow-50 border-yellow-200'
                            : 'bg-blue-50 border-blue-200'
                        }`}
                      >
                        <div className="flex items-start">
                          {getAlertIcon(alert.type)}
                          <div className="ml-3 flex-1">
                            <div className="flex items-center justify-between">
                              <h4 className="text-sm font-medium text-gray-900">{alert.title}</h4>
                              {alert.count && (
                                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-white text-gray-800">
                                  {alert.count}
                                </span>
                              )}
                            </div>
                            <p className="mt-1 text-sm text-gray-600">{alert.description}</p>
                            {alert.action && (
                              <button className="mt-2 text-sm font-medium text-blue-600 hover:text-blue-800">
                                {alert.action} →
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-4">
                    <CheckCircle className="mx-auto h-8 w-8 text-green-500 mb-2" />
                    <p className="text-sm text-gray-600">No active alerts</p>
                  </div>
                )}
              </div>
            </div>

            {/* Recent Activity */}
            <div className="bg-white shadow-sm rounded-lg border">
              <div className="px-6 py-4 border-b border-gray-200">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-medium text-gray-900">Recent Activity</h3>
                  <Activity className="h-5 w-5 text-gray-400" />
                </div>
              </div>
              <div className="p-6">
                <div className="flow-root">
                  <ul className="-mb-8">
                    {recentActivity.map((activity, index) => (
                      <li key={activity.id}>
                        <div className="relative pb-8">
                          {index !== recentActivity.length - 1 && (
                            <span
                              className="absolute top-4 left-4 -ml-px h-full w-0.5 bg-gray-200"
                              aria-hidden="true"
                            />
                          )}
                          <div className="relative flex space-x-3">
                            <div className="bg-white rounded-full p-2 ring-2 ring-white shadow">
                              {getActivityIcon(activity.type)}
                            </div>
                            <div className="min-w-0 flex-1">
                              <div>
                                <p className="text-sm font-medium text-gray-900">{activity.title}</p>
                                <p className="text-sm text-gray-600">{activity.description}</p>
                              </div>
                              <div className="mt-2 flex items-center text-xs text-gray-500">
                                <span>{activity.timestamp}</span>
                                {activity.user && (
                                  <>
                                    <span className="mx-2">•</span>
                                    <span>{activity.user}</span>
                                  </>
                                )}
                              </div>
                            </div>
                          </div>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg shadow-lg">
          <div className="px-6 py-8">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-xl font-semibold text-white">Quick Actions</h3>
                <p className="mt-1 text-blue-100">Frequently used operations</p>
              </div>
              <Zap className="h-8 w-8 text-blue-200" />
            </div>
            <div className="mt-6 grid grid-cols-1 md:grid-cols-4 gap-4">
              <button className="flex items-center justify-center px-4 py-3 bg-white bg-opacity-20 rounded-lg text-white hover:bg-opacity-30 transition-all">
                <Search className="mr-2 h-5 w-5" />
                Find Student
              </button>
              <button className="flex items-center justify-center px-4 py-3 bg-white bg-opacity-20 rounded-lg text-white hover:bg-opacity-30 transition-all">
                <FileText className="mr-2 h-5 w-5" />
                Generate Report
              </button>
              <button className="flex items-center justify-center px-4 py-3 bg-white bg-opacity-20 rounded-lg text-white hover:bg-opacity-30 transition-all">
                <Mail className="mr-2 h-5 w-5" />
                Bulk Email
              </button>
              <button className="flex items-center justify-center px-4 py-3 bg-white bg-opacity-20 rounded-lg text-white hover:bg-opacity-30 transition-all">
                <Award className="mr-2 h-5 w-5" />
                Awards & Recognition
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};