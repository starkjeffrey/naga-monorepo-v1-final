/**
 * Enrollment Management Dashboard
 *
 * Comprehensive enrollment management interface with:
 * - Program enrollment overview and management
 * - Major declaration tracking
 * - Class enrollment monitoring
 * - Bulk operations and analytics
 */

import React, { useState, useEffect } from 'react';
import {
  Users,
  GraduationCap,
  BookOpen,
  TrendingUp,
  AlertCircle,
  CheckCircle2,
  Clock,
  Plus,
  Search,
  Filter,
  Download,
  Upload,
  MoreHorizontal,
  ChevronRight,
  Calendar,
  Award,
  FileText,
  Eye,
  Edit,
  Trash2
} from 'lucide-react';
import { EnrollmentService } from '../../services/enrollment.service';
import { StudentService } from '../../services/student.service';
import type {
  ProgramEnrollmentDetail,
  MajorDeclarationDetail,
  ClassEnrollmentDetail,
  EnrollmentStatistics,
  EnrollmentFilters
} from '../../types/enrollment.types';
import type { PaginatedResponse } from '../../types/student.types';

interface EnrollmentTab {
  id: 'programs' | 'majors' | 'classes';
  name: string;
  icon: React.ElementType;
  count?: number;
}

export const EnrollmentDashboard: React.FC = () => {
  // State management
  const [activeTab, setActiveTab] = useState<'programs' | 'majors' | 'classes'>('programs');
  const [programEnrollments, setProgramEnrollments] = useState<ProgramEnrollmentDetail[]>([]);
  const [majorDeclarations, setMajorDeclarations] = useState<MajorDeclarationDetail[]>([]);
  const [classEnrollments, setClassEnrollments] = useState<ClassEnrollmentDetail[]>([]);
  const [statistics, setStatistics] = useState<EnrollmentStatistics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<EnrollmentFilters>({});
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedItems, setSelectedItems] = useState<number[]>([]);
  const [pagination, setPagination] = useState({
    page: 1,
    pageSize: 20,
    total: 0
  });

  const tabs: EnrollmentTab[] = [
    {
      id: 'programs',
      name: 'Program Enrollments',
      icon: GraduationCap,
      count: programEnrollments.length
    },
    {
      id: 'majors',
      name: 'Major Declarations',
      icon: Award,
      count: majorDeclarations.length
    },
    {
      id: 'classes',
      name: 'Class Enrollments',
      icon: BookOpen,
      count: classEnrollments.length
    },
  ];

  useEffect(() => {
    loadDashboardData();
  }, [activeTab, filters, pagination.page]);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [stats] = await Promise.all([
        EnrollmentService.getEnrollmentStatistics()
      ]);

      setStatistics(stats);

      // Load data based on active tab
      const paginationFilters = {
        ...filters,
        page: pagination.page,
        page_size: pagination.pageSize
      };

      switch (activeTab) {
        case 'programs':
          const programResponse = await EnrollmentService.listProgramEnrollments(paginationFilters);
          setProgramEnrollments(programResponse.results);
          setPagination(prev => ({ ...prev, total: programResponse.count }));
          break;
        case 'majors':
          const majorResponse = await EnrollmentService.listMajorDeclarations(paginationFilters);
          setMajorDeclarations(majorResponse.results);
          setPagination(prev => ({ ...prev, total: majorResponse.count }));
          break;
        case 'classes':
          const classResponse = await EnrollmentService.listClassEnrollments(paginationFilters);
          setClassEnrollments(classResponse.results);
          setPagination(prev => ({ ...prev, total: classResponse.count }));
          break;
      }
    } catch (err) {
      console.error('Failed to load enrollment data:', err);
      setError('Failed to load enrollment data');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (query: string) => {
    setSearchQuery(query);
    // Implement search logic based on active tab
    // For now, we'll use client-side filtering
  };

  const handleBulkAction = async (action: string) => {
    if (selectedItems.length === 0) return;

    try {
      switch (action) {
        case 'activate':
          await EnrollmentService.bulkUpdateEnrollmentStatuses(selectedItems, 'ENROLLED');
          break;
        case 'deactivate':
          await EnrollmentService.bulkUpdateEnrollmentStatuses(selectedItems, 'WITHDRAWN');
          break;
        case 'delete':
          // Implement bulk delete
          break;
      }

      setSelectedItems([]);
      loadDashboardData();
    } catch (err) {
      console.error('Bulk action failed:', err);
    }
  };

  const filteredData = () => {
    let data: any[] = [];

    switch (activeTab) {
      case 'programs':
        data = programEnrollments;
        break;
      case 'majors':
        data = majorDeclarations;
        break;
      case 'classes':
        data = classEnrollments;
        break;
    }

    if (searchQuery.trim()) {
      data = data.filter(item =>
        item.student_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (item.major?.name || item.class_header?.course_name || '')?.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    return data;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-4 border-indigo-200 border-t-indigo-600 mx-auto mb-6"></div>
          <h2 className="text-xl font-semibold text-gray-700 mb-2">Loading Enrollment Data</h2>
          <p className="text-gray-500">Fetching student enrollment information...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-red-50 via-white to-pink-50 flex items-center justify-center">
        <div className="bg-white p-8 rounded-2xl shadow-lg border border-red-100 text-center max-w-md">
          <div className="text-red-500 text-6xl mb-4">⚠️</div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Error Loading Data</h2>
          <p className="text-gray-600 mb-6">{error}</p>
          <button
            onClick={loadDashboardData}
            className="bg-red-600 hover:bg-red-700 text-white px-8 py-3 rounded-xl font-medium transition-all duration-200 hover:shadow-lg"
          >
            Retry Loading
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">
      <div className="container mx-auto px-6 py-8">
        {/* Header Section */}
        <div className="mb-10">
          <div className="flex flex-col xl:flex-row xl:items-center xl:justify-between mb-8">
            <div className="mb-6 xl:mb-0">
              <h1 className="text-5xl font-bold text-gray-900 mb-3 bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
                Enrollment Management
              </h1>
              <p className="text-xl text-gray-600 leading-relaxed">
                Comprehensive enrollment tracking and program management system
              </p>
            </div>
            <div className="flex items-center space-x-4">
              <button className="flex items-center px-6 py-3 bg-white border border-gray-200 rounded-xl hover:bg-gray-50 transition-colors">
                <Download className="w-5 h-5 mr-2" />
                Export Data
              </button>
              <button className="flex items-center px-6 py-3 bg-white border border-gray-200 rounded-xl hover:bg-gray-50 transition-colors">
                <Upload className="w-5 h-5 mr-2" />
                Import Data
              </button>
              <button className="flex items-center px-6 py-3 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 transition-colors">
                <Plus className="w-5 h-5 mr-2" />
                New Enrollment
              </button>
            </div>
          </div>
        </div>

        {/* Statistics Cards */}
        {statistics && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 mb-12">
            <div className="group bg-white/90 backdrop-blur-sm rounded-3xl p-8 shadow-xl border border-gray-100 hover:shadow-2xl hover:scale-105 transition-all duration-300">
              <div className="flex items-center justify-between mb-6">
                <div className="text-5xl opacity-80 group-hover:opacity-100 transition-opacity">🎓</div>
                <div className="text-right">
                  <div className="text-4xl font-bold text-indigo-600 mb-1">{statistics.total_enrollments.toLocaleString()}</div>
                  <div className="text-sm font-medium text-gray-600 uppercase tracking-wide">Total Enrollments</div>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span className="text-green-600 font-semibold flex items-center">
                    <span className="text-lg">↗</span> 8.2%
                  </span>
                  <span className="text-gray-500 text-sm">this term</span>
                </div>
                <div className="w-16 h-1 bg-gradient-to-r from-indigo-200 to-indigo-400 rounded-full"></div>
              </div>
            </div>

            <div className="group bg-white/90 backdrop-blur-sm rounded-3xl p-8 shadow-xl border border-gray-100 hover:shadow-2xl hover:scale-105 transition-all duration-300">
              <div className="flex items-center justify-between mb-6">
                <div className="text-5xl opacity-80 group-hover:opacity-100 transition-opacity">📚</div>
                <div className="text-right">
                  <div className="text-4xl font-bold text-blue-600 mb-1">{statistics.current_term_enrollments.toLocaleString()}</div>
                  <div className="text-sm font-medium text-gray-600 uppercase tracking-wide">Current Term</div>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span className="text-blue-600 font-semibold flex items-center">
                    <span className="text-lg">↗</span> 15.3%
                  </span>
                  <span className="text-gray-500 text-sm">vs last term</span>
                </div>
                <div className="w-16 h-1 bg-gradient-to-r from-blue-200 to-blue-400 rounded-full"></div>
              </div>
            </div>

            <div className="group bg-white/90 backdrop-blur-sm rounded-3xl p-8 shadow-xl border border-gray-100 hover:shadow-2xl hover:scale-105 transition-all duration-300">
              <div className="flex items-center justify-between mb-6">
                <div className="text-5xl opacity-80 group-hover:opacity-100 transition-opacity">👥</div>
                <div className="text-right">
                  <div className="text-4xl font-bold text-green-600 mb-1">{statistics.active_students.toLocaleString()}</div>
                  <div className="text-sm font-medium text-gray-600 uppercase tracking-wide">Active Students</div>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span className="text-green-600 font-semibold flex items-center">
                    <span className="text-lg">↗</span> 3.7%
                  </span>
                  <span className="text-gray-500 text-sm">this month</span>
                </div>
                <div className="w-16 h-1 bg-gradient-to-r from-green-200 to-green-400 rounded-full"></div>
              </div>
            </div>

            <div className="group bg-white/90 backdrop-blur-sm rounded-3xl p-8 shadow-xl border border-gray-100 hover:shadow-2xl hover:scale-105 transition-all duration-300">
              <div className="flex items-center justify-between mb-6">
                <div className="text-5xl opacity-80 group-hover:opacity-100 transition-opacity">⚠️</div>
                <div className="text-right">
                  <div className="text-4xl font-bold text-yellow-600 mb-1">
                    {statistics.total_students - statistics.active_students}
                  </div>
                  <div className="text-sm font-medium text-gray-600 uppercase tracking-wide">Needs Review</div>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span className="text-yellow-600 font-semibold flex items-center">
                    <span className="text-lg">↘</span> 2.1%
                  </span>
                  <span className="text-gray-500 text-sm">from last month</span>
                </div>
                <div className="w-16 h-1 bg-gradient-to-r from-yellow-200 to-yellow-400 rounded-full"></div>
              </div>
            </div>
          </div>
        )}

        {/* Main Content */}
        <div className="bg-white/90 backdrop-blur-sm rounded-3xl shadow-2xl border border-gray-100">
          {/* Tabs Navigation */}
          <div className="border-b border-gray-200">
            <nav className="flex space-x-8 px-8 pt-6">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex items-center space-x-2 pb-4 border-b-2 font-medium transition-colors ${
                      activeTab === tab.id
                        ? 'border-indigo-500 text-indigo-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    }`}
                  >
                    <Icon className="w-5 h-5" />
                    <span>{tab.name}</span>
                    {tab.count !== undefined && (
                      <span className={`px-2 py-1 text-xs rounded-full ${
                        activeTab === tab.id
                          ? 'bg-indigo-100 text-indigo-600'
                          : 'bg-gray-100 text-gray-600'
                      }`}>
                        {tab.count}
                      </span>
                    )}
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Search and Filters */}
          <div className="p-8 border-b border-gray-200">
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between space-y-4 lg:space-y-0">
              <div className="flex-1 max-w-lg">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                  <input
                    type="text"
                    placeholder="Search students, programs, or courses..."
                    value={searchQuery}
                    onChange={(e) => handleSearch(e.target.value)}
                    className="w-full pl-10 pr-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="flex items-center space-x-4">
                <button className="flex items-center px-4 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
                  <Filter className="w-4 h-4 mr-2" />
                  Filters
                </button>

                {selectedItems.length > 0 && (
                  <div className="flex items-center space-x-2">
                    <span className="text-sm text-gray-600">{selectedItems.length} selected</span>
                    <button
                      onClick={() => handleBulkAction('activate')}
                      className="px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700 transition-colors"
                    >
                      Activate
                    </button>
                    <button
                      onClick={() => handleBulkAction('deactivate')}
                      className="px-3 py-1 bg-yellow-600 text-white text-sm rounded hover:bg-yellow-700 transition-colors"
                    >
                      Deactivate
                    </button>
                    <button
                      onClick={() => handleBulkAction('delete')}
                      className="px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700 transition-colors"
                    >
                      Delete
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Content Area */}
          <div className="p-8">
            {activeTab === 'programs' && (
              <ProgramEnrollmentsTable
                enrollments={filteredData() as ProgramEnrollmentDetail[]}
                selectedItems={selectedItems}
                onSelectionChange={setSelectedItems}
              />
            )}

            {activeTab === 'majors' && (
              <MajorDeclarationsTable
                declarations={filteredData() as MajorDeclarationDetail[]}
                selectedItems={selectedItems}
                onSelectionChange={setSelectedItems}
              />
            )}

            {activeTab === 'classes' && (
              <ClassEnrollmentsTable
                enrollments={filteredData() as ClassEnrollmentDetail[]}
                selectedItems={selectedItems}
                onSelectionChange={setSelectedItems}
              />
            )}

            {filteredData().length === 0 && (
              <div className="text-center py-16">
                <div className="text-6xl mb-4 opacity-50">📋</div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">No Data Found</h3>
                <p className="text-gray-500 mb-6">No enrollment records match your current filters.</p>
                <button
                  onClick={() => {
                    setSearchQuery('');
                    setFilters({});
                    loadDashboardData();
                  }}
                  className="bg-indigo-600 text-white px-6 py-2 rounded-lg hover:bg-indigo-700 transition-colors"
                >
                  Clear Filters
                </button>
              </div>
            )}
          </div>

          {/* Pagination */}
          {pagination.total > pagination.pageSize && (
            <div className="px-8 py-6 border-t border-gray-200">
              <div className="flex items-center justify-between">
                <div className="text-sm text-gray-700">
                  Showing {((pagination.page - 1) * pagination.pageSize) + 1} to {Math.min(pagination.page * pagination.pageSize, pagination.total)} of {pagination.total} results
                </div>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => setPagination(prev => ({ ...prev, page: Math.max(1, prev.page - 1) }))}
                    disabled={pagination.page === 1}
                    className="px-3 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Previous
                  </button>
                  <span className="px-4 py-2 text-sm text-gray-700">
                    Page {pagination.page} of {Math.ceil(pagination.total / pagination.pageSize)}
                  </span>
                  <button
                    onClick={() => setPagination(prev => ({ ...prev, page: prev.page + 1 }))}
                    disabled={pagination.page >= Math.ceil(pagination.total / pagination.pageSize)}
                    className="px-3 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Next
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Sub-components for different enrollment tables
const ProgramEnrollmentsTable: React.FC<{
  enrollments: ProgramEnrollmentDetail[];
  selectedItems: number[];
  onSelectionChange: (items: number[]) => void;
}> = ({ enrollments, selectedItems, onSelectionChange }) => {
  const toggleSelection = (id: number) => {
    if (selectedItems.includes(id)) {
      onSelectionChange(selectedItems.filter(item => item !== id));
    } else {
      onSelectionChange([...selectedItems, id]);
    }
  };

  const toggleAll = () => {
    if (selectedItems.length === enrollments.length) {
      onSelectionChange([]);
    } else {
      onSelectionChange(enrollments.map(e => e.id));
    }
  };

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left">
              <input
                type="checkbox"
                checked={selectedItems.length === enrollments.length && enrollments.length > 0}
                onChange={toggleAll}
                className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
              />
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Student
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Program
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Status
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Progress
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              GPA
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {enrollments.map((enrollment) => (
            <tr key={enrollment.id} className="hover:bg-gray-50">
              <td className="px-6 py-4">
                <input
                  type="checkbox"
                  checked={selectedItems.includes(enrollment.id)}
                  onChange={() => toggleSelection(enrollment.id)}
                  className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                />
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="font-medium text-gray-900">{enrollment.student_name}</div>
                <div className="text-sm text-gray-500">ID: {enrollment.student_id}</div>
              </td>
              <td className="px-6 py-4">
                <div className="font-medium text-gray-900">{enrollment.major.name}</div>
                <div className="text-sm text-gray-500">
                  {enrollment.major.division.name} • {enrollment.major.program_type}
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                  EnrollmentService.getEnrollmentStatusBadgeClass(enrollment.enrollment_status)
                }`}>
                  {EnrollmentService.formatEnrollmentStatus(enrollment.enrollment_status)}
                </span>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="flex items-center">
                  <div className="w-full bg-gray-200 rounded-full h-2 mr-2">
                    <div
                      className="bg-indigo-600 h-2 rounded-full"
                      style={{
                        width: `${EnrollmentService.calculateEnrollmentProgress(enrollment)}%`
                      }}
                    ></div>
                  </div>
                  <span className="text-sm text-gray-600">
                    {EnrollmentService.calculateEnrollmentProgress(enrollment)}%
                  </span>
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                {EnrollmentService.formatGPA(enrollment.overall_gpa)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                <div className="flex items-center space-x-2">
                  <button className="text-indigo-600 hover:text-indigo-900">
                    <Eye className="w-4 h-4" />
                  </button>
                  <button className="text-gray-400 hover:text-gray-600">
                    <Edit className="w-4 h-4" />
                  </button>
                  <button className="text-red-400 hover:text-red-600">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const MajorDeclarationsTable: React.FC<{
  declarations: MajorDeclarationDetail[];
  selectedItems: number[];
  onSelectionChange: (items: number[]) => void;
}> = ({ declarations, selectedItems, onSelectionChange }) => {
  // Similar implementation to ProgramEnrollmentsTable
  return (
    <div className="text-center py-8">
      <p className="text-gray-500">Major declarations table implementation...</p>
    </div>
  );
};

const ClassEnrollmentsTable: React.FC<{
  enrollments: ClassEnrollmentDetail[];
  selectedItems: number[];
  onSelectionChange: (items: number[]) => void;
}> = ({ enrollments, selectedItems, onSelectionChange }) => {
  // Similar implementation to ProgramEnrollmentsTable
  return (
    <div className="text-center py-8">
      <p className="text-gray-500">Class enrollments table implementation...</p>
    </div>
  );
};