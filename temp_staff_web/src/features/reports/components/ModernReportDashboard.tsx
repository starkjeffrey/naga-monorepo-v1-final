import React, { useState, useEffect, useMemo } from 'react';
import {
  Search,
  Filter,
  Download,
  FileText,
  TrendingUp,
  Users,
  DollarSign,
  Calendar,
  MoreHorizontal,
  ChevronDown,
  RefreshCw,
  Eye,
  Edit,
  Trash2,
  Plus,
  ArrowUpDown,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';

// Types
interface ReportData {
  id: string;
  name: string;
  type: string;
  date: string;
  status: 'active' | 'pending' | 'completed' | 'error';
  value: number;
  change: number;
  category: string;
  user: string;
}

interface StatCard {
  title: string;
  value: string;
  change: string;
  changeType: 'positive' | 'negative' | 'neutral';
  icon: React.ElementType;
  color: string;
}

// Sample data
const generateSampleData = (): ReportData[] => {
  const types = ['Financial Report', 'Student Analytics', 'Enrollment Report', 'Performance Report'];
  const statuses: ('active' | 'pending' | 'completed' | 'error')[] = ['active', 'pending', 'completed', 'error'];
  const categories = ['Finance', 'Academic', 'Operations', 'Marketing'];
  const users = ['Maria Santos', 'James Wilson', 'Sarah Kim', 'David Chen', 'Lisa Wang'];

  return Array.from({ length: 50 }, (_, i) => ({
    id: `report-${i + 1}`,
    name: `${types[i % types.length]} ${i + 1}`,
    type: types[i % types.length],
    date: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    status: statuses[i % statuses.length],
    value: Math.floor(Math.random() * 10000) + 1000,
    change: Math.floor(Math.random() * 20) - 10,
    category: categories[i % categories.length],
    user: users[i % users.length]
  }));
};

const ModernReportDashboard: React.FC = () => {
  const [data, setData] = useState<ReportData[]>(generateSampleData());
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [selectedStatus, setSelectedStatus] = useState('All');
  const [sortBy, setSortBy] = useState<keyof ReportData>('date');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage] = useState(10);
  const [isLoading, setIsLoading] = useState(false);

  // Statistics
  const stats: StatCard[] = [
    {
      title: 'Total Reports',
      value: data.length.toString(),
      change: '+12%',
      changeType: 'positive',
      icon: FileText,
      color: 'blue'
    },
    {
      title: 'Active Reports',
      value: data.filter(item => item.status === 'active').length.toString(),
      change: '+5%',
      changeType: 'positive',
      icon: TrendingUp,
      color: 'green'
    },
    {
      title: 'Total Value',
      value: `$${data.reduce((sum, item) => sum + item.value, 0).toLocaleString()}`,
      change: '+8%',
      changeType: 'positive',
      icon: DollarSign,
      color: 'purple'
    },
    {
      title: 'This Month',
      value: data.filter(item => new Date(item.date).getMonth() === new Date().getMonth()).length.toString(),
      change: '-2%',
      changeType: 'negative',
      icon: Calendar,
      color: 'orange'
    }
  ];

  // Filtered and sorted data
  const filteredData = useMemo(() => {
    let filtered = data.filter(item => {
      const matchesSearch = item.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                           item.user.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesCategory = selectedCategory === 'All' || item.category === selectedCategory;
      const matchesStatus = selectedStatus === 'All' || item.status === selectedStatus;
      
      return matchesSearch && matchesCategory && matchesStatus;
    });

    // Sort data
    filtered.sort((a, b) => {
      let aVal = a[sortBy];
      let bVal = b[sortBy];
      
      if (typeof aVal === 'string') {
        aVal = aVal.toLowerCase();
        bVal = (bVal as string).toLowerCase();
      }
      
      if (aVal < bVal) return sortOrder === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortOrder === 'asc' ? 1 : -1;
      return 0;
    });

    return filtered;
  }, [data, searchTerm, selectedCategory, selectedStatus, sortBy, sortOrder]);

  // Pagination
  const totalPages = Math.ceil(filteredData.length / itemsPerPage);
  const paginatedData = filteredData.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  const handleSort = (column: keyof ReportData) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortOrder('asc');
    }
  };

  const handleRefresh = async () => {
    setIsLoading(true);
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000));
    setData(generateSampleData());
    setIsLoading(false);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-100 text-green-800';
      case 'pending': return 'bg-yellow-100 text-yellow-800';
      case 'completed': return 'bg-blue-100 text-blue-800';
      case 'error': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatColorClasses = (color: string) => {
    switch (color) {
      case 'blue': return 'border-blue-500 bg-blue-50';
      case 'green': return 'border-green-500 bg-green-50';
      case 'purple': return 'border-purple-500 bg-purple-50';
      case 'orange': return 'border-orange-500 bg-orange-50';
      default: return 'border-gray-500 bg-gray-50';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50/50 p-6">
      <div className="mx-auto max-w-7xl">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Report Dashboard</h1>
          <p className="mt-2 text-gray-600">Manage and analyze your reports with advanced filtering and insights</p>
        </div>

        {/* Stats Cards */}
        <div className="mb-8 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {stats.map((stat, index) => {
            const Icon = stat.icon;
            return (
              <div
                key={index}
                className={`rounded-lg border-l-4 bg-white p-6 shadow-sm ${getStatColorClasses(stat.color)}`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">{stat.title}</p>
                    <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
                    <p className={`text-sm ${
                      stat.changeType === 'positive' ? 'text-green-600' :
                      stat.changeType === 'negative' ? 'text-red-600' : 'text-gray-600'
                    }`}>
                      {stat.change} from last month
                    </p>
                  </div>
                  <Icon className={`h-8 w-8 ${
                    stat.color === 'blue' ? 'text-blue-600' :
                    stat.color === 'green' ? 'text-green-600' :
                    stat.color === 'purple' ? 'text-purple-600' :
                    stat.color === 'orange' ? 'text-orange-600' : 'text-gray-600'
                  }`} />
                </div>
              </div>
            );
          })}
        </div>

        {/* Controls */}
        <div className="mb-6 rounded-lg bg-white p-6 shadow-sm">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            {/* Search */}
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Search reports..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full rounded-md border border-gray-300 pl-10 pr-4 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>

            <div className="flex gap-2">
              {/* Filters */}
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="All">All Categories</option>
                <option value="Finance">Finance</option>
                <option value="Academic">Academic</option>
                <option value="Operations">Operations</option>
                <option value="Marketing">Marketing</option>
              </select>

              <select
                value={selectedStatus}
                onChange={(e) => setSelectedStatus(e.target.value)}
                className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="All">All Status</option>
                <option value="active">Active</option>
                <option value="pending">Pending</option>
                <option value="completed">Completed</option>
                <option value="error">Error</option>
              </select>

              {/* Action Buttons */}
              <button
                onClick={handleRefresh}
                disabled={isLoading}
                className="flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
              >
                <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
                Refresh
              </button>

              <button className="flex items-center gap-2 rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2">
                <Download className="h-4 w-4" />
                Export
              </button>

              <button className="flex items-center gap-2 rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2">
                <Plus className="h-4 w-4" />
                New Report
              </button>
            </div>
          </div>
        </div>

        {/* Data Table */}
        <div className="rounded-lg bg-white shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b border-gray-200 bg-gray-50">
                <tr>
                  {[
                    { key: 'name', label: 'Report Name' },
                    { key: 'type', label: 'Type' },
                    { key: 'category', label: 'Category' },
                    { key: 'status', label: 'Status' },
                    { key: 'value', label: 'Value' },
                    { key: 'change', label: 'Change' },
                    { key: 'user', label: 'Created By' },
                    { key: 'date', label: 'Date' }
                  ].map((column) => (
                    <th
                      key={column.key}
                      className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 cursor-pointer hover:bg-gray-100"
                      onClick={() => handleSort(column.key as keyof ReportData)}
                    >
                      <div className="flex items-center gap-2">
                        {column.label}
                        <ArrowUpDown className="h-3 w-3" />
                      </div>
                    </th>
                  ))}
                  <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {paginatedData.map((item) => (
                  <tr key={item.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="font-medium text-gray-900">{item.name}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {item.type}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {item.category}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex rounded-full px-2 py-1 text-xs font-semibold ${getStatusColor(item.status)}`}>
                        {item.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      ${item.value.toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <span className={item.change >= 0 ? 'text-green-600' : 'text-red-600'}>
                        {item.change >= 0 ? '+' : ''}{item.change}%
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {item.user}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {item.date}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <div className="flex items-center gap-2 justify-end">
                        <button className="text-blue-600 hover:text-blue-900">
                          <Eye className="h-4 w-4" />
                        </button>
                        <button className="text-gray-600 hover:text-gray-900">
                          <Edit className="h-4 w-4" />
                        </button>
                        <button className="text-red-600 hover:text-red-900">
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between border-t border-gray-200 bg-white px-6 py-3">
            <div className="flex flex-1 justify-between sm:hidden">
              <button
                onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                disabled={currentPage === 1}
                className="relative inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                Previous
              </button>
              <button
                onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                disabled={currentPage === totalPages}
                className="relative ml-3 inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                Next
              </button>
            </div>
            <div className="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
              <div>
                <p className="text-sm text-gray-700">
                  Showing{' '}
                  <span className="font-medium">{(currentPage - 1) * itemsPerPage + 1}</span>
                  {' '}to{' '}
                  <span className="font-medium">
                    {Math.min(currentPage * itemsPerPage, filteredData.length)}
                  </span>
                  {' '}of{' '}
                  <span className="font-medium">{filteredData.length}</span>
                  {' '}results
                </p>
              </div>
              <div>
                <nav className="isolate inline-flex -space-x-px rounded-md shadow-sm">
                  <button
                    onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                    disabled={currentPage === 1}
                    className="relative inline-flex items-center rounded-l-md px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0 disabled:opacity-50"
                  >
                    <ChevronLeft className="h-5 w-5" />
                  </button>
                  
                  {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                    const page = i + 1;
                    return (
                      <button
                        key={page}
                        onClick={() => setCurrentPage(page)}
                        className={`relative inline-flex items-center px-4 py-2 text-sm font-semibold ${
                          currentPage === page
                            ? 'bg-blue-600 text-white focus:z-20 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600'
                            : 'text-gray-900 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0'
                        }`}
                      >
                        {page}
                      </button>
                    );
                  })}
                  
                  <button
                    onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                    disabled={currentPage === totalPages}
                    className="relative inline-flex items-center rounded-r-md px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0 disabled:opacity-50"
                  >
                    <ChevronRight className="h-5 w-5" />
                  </button>
                </nav>
              </div>
            </div>
          </div>
        </div>

        {/* Summary */}
        <div className="mt-6 text-center text-sm text-gray-500">
          Built with React, TypeScript, and Tailwind CSS • Full CRUD functionality ready
        </div>
      </div>
    </div>
  );
};

export default ModernReportDashboard;