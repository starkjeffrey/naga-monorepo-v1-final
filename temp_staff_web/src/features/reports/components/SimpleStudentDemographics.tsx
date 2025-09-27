import React, { useState } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
} from 'recharts';
import {
  Users,
  MapPin,
  GraduationCap,
  Calendar,
  Clock,
  Globe,
  UserCheck,
  Star,
} from 'lucide-react';

// Simple student data
const students = [
  { name: 'CHEA SOKHA', gender: 'M', age: 23, province: 'Phnom Penh', major: 'Computer Science', status: 'Active', gpa: 3.75 },
  { name: 'LIM SREYPICH', gender: 'F', age: 24, province: 'Siem Reap', major: 'Business', status: 'Active', gpa: 3.92 },
  { name: 'PREAH VICHEKA', gender: 'M', age: 25, province: 'Battambang', major: 'Buddhist Studies', status: 'Active', gpa: 4.0 },
  { name: 'NGUYEN THI LINH', gender: 'F', age: 22, province: 'International', major: 'International Relations', status: 'Active', gpa: 3.85 },
  { name: 'KONG PISACH', gender: 'M', age: 22, province: 'Kandal', major: 'Engineering', status: 'Suspended', gpa: 2.45 },
  { name: 'SOM CHANMONY', gender: 'F', age: 26, province: 'Takeo', major: 'English Literature', status: 'Graduated', gpa: 3.68 },
  { name: 'PICH SOKHA', gender: 'F', age: 19, province: 'Kampong Cham', major: 'Psychology', status: 'Active', gpa: 3.2 },
  { name: 'JAMES SMITH', gender: 'M', age: 28, province: 'International', major: 'Teaching', status: 'Active', gpa: 3.5 },
];

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#06B6D4'];

const SimpleStudentDemographics: React.FC = () => {
  const [activeChart, setActiveChart] = useState<string | null>(null);

  // Calculate demographics
  const genderData = [
    { name: 'Male', value: students.filter(s => s.gender === 'M').length },
    { name: 'Female', value: students.filter(s => s.gender === 'F').length },
  ];

  const ageData = [
    { name: '18-22', value: students.filter(s => s.age >= 18 && s.age <= 22).length },
    { name: '23-25', value: students.filter(s => s.age >= 23 && s.age <= 25).length },
    { name: '26+', value: students.filter(s => s.age >= 26).length },
  ];

  const provinceData = [...new Set(students.map(s => s.province))]
    .map(province => ({
      name: province,
      value: students.filter(s => s.province === province).length
    }))
    .sort((a, b) => b.value - a.value);

  const statusData = [...new Set(students.map(s => s.status))]
    .map(status => ({
      name: status,
      value: students.filter(s => s.status === status).length
    }));

  const majorData = [...new Set(students.map(s => s.major))]
    .map(major => ({
      name: major,
      value: students.filter(s => s.major === major).length
    }))
    .sort((a, b) => b.value - a.value);

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            🎓 Student Demographics
          </h1>
          <p className="text-gray-600">
            Simple overview of our student population
          </p>
        </div>

        {/* Key Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
                  <Users className="h-5 w-5 text-white" />
                </div>
              </div>
              <div className="ml-5">
                <p className="text-sm font-medium text-gray-500">Total Students</p>
                <p className="text-2xl font-semibold text-gray-900">{students.length}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-green-500 rounded-lg flex items-center justify-center">
                  <UserCheck className="h-5 w-5 text-white" />
                </div>
              </div>
              <div className="ml-5">
                <p className="text-sm font-medium text-gray-500">Active</p>
                <p className="text-2xl font-semibold text-gray-900">
                  {students.filter(s => s.status === 'Active').length}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-purple-500 rounded-lg flex items-center justify-center">
                  <Star className="h-5 w-5 text-white" />
                </div>
              </div>
              <div className="ml-5">
                <p className="text-sm font-medium text-gray-500">Avg GPA</p>
                <p className="text-2xl font-semibold text-gray-900">
                  {(students.reduce((sum, s) => sum + s.gpa, 0) / students.length).toFixed(2)}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-orange-500 rounded-lg flex items-center justify-center">
                  <GraduationCap className="h-5 w-5 text-white" />
                </div>
              </div>
              <div className="ml-5">
                <p className="text-sm font-medium text-gray-500">Majors</p>
                <p className="text-2xl font-semibold text-gray-900">{majorData.length}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Charts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Gender Distribution */}
          <div 
            className={`bg-white rounded-lg shadow-lg p-6 transition-all duration-200 ${
              activeChart === 'gender' ? 'ring-2 ring-blue-500 shadow-xl' : ''
            }`}
            onMouseEnter={() => setActiveChart('gender')}
            onMouseLeave={() => setActiveChart(null)}
          >
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Users className="h-5 w-5 text-blue-600" />
              Gender Distribution
            </h3>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={genderData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  dataKey="value"
                >
                  {genderData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
            <div className="flex justify-center gap-4 mt-4">
              {genderData.map((entry, index) => (
                <div key={entry.name} className="flex items-center gap-2">
                  <div 
                    className="w-3 h-3 rounded-full" 
                    style={{ backgroundColor: COLORS[index] }}
                  />
                  <span className="text-sm text-gray-600">{entry.name}: {entry.value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Age Distribution */}
          <div 
            className={`bg-white rounded-lg shadow-lg p-6 transition-all duration-200 ${
              activeChart === 'age' ? 'ring-2 ring-green-500 shadow-xl' : ''
            }`}
            onMouseEnter={() => setActiveChart('age')}
            onMouseLeave={() => setActiveChart(null)}
          >
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Calendar className="h-5 w-5 text-green-600" />
              Age Groups
            </h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={ageData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="value" fill="#10B981" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Province Distribution */}
          <div 
            className={`bg-white rounded-lg shadow-lg p-6 transition-all duration-200 ${
              activeChart === 'province' ? 'ring-2 ring-purple-500 shadow-xl' : ''
            }`}
            onMouseEnter={() => setActiveChart('province')}
            onMouseLeave={() => setActiveChart(null)}
          >
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <MapPin className="h-5 w-5 text-purple-600" />
              Birth Provinces
            </h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={provinceData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" angle={-45} textAnchor="end" height={80} />
                <YAxis />
                <Tooltip />
                <Bar dataKey="value" fill="#8B5CF6" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Student Status */}
          <div 
            className={`bg-white rounded-lg shadow-lg p-6 transition-all duration-200 ${
              activeChart === 'status' ? 'ring-2 ring-orange-500 shadow-xl' : ''
            }`}
            onMouseEnter={() => setActiveChart('status')}
            onMouseLeave={() => setActiveChart(null)}
          >
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <UserCheck className="h-5 w-5 text-orange-600" />
              Student Status
            </h3>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={statusData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  dataKey="value"
                >
                  {statusData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index + 2]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
            <div className="flex justify-center gap-4 mt-4">
              {statusData.map((entry, index) => (
                <div key={entry.name} className="flex items-center gap-2">
                  <div 
                    className="w-3 h-3 rounded-full" 
                    style={{ backgroundColor: COLORS[index + 2] }}
                  />
                  <span className="text-sm text-gray-600">{entry.name}: {entry.value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Major Distribution - Full Width */}
        <div 
          className={`mt-8 bg-white rounded-lg shadow-lg p-6 transition-all duration-200 ${
            activeChart === 'major' ? 'ring-2 ring-indigo-500 shadow-xl' : ''
          }`}
          onMouseEnter={() => setActiveChart('major')}
          onMouseLeave={() => setActiveChart(null)}
        >
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <GraduationCap className="h-5 w-5 text-indigo-600" />
            Popular Majors
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={majorData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" angle={-45} textAnchor="end" height={100} />
              <YAxis />
              <Tooltip />
              <Bar dataKey="value" fill="#6366F1" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Student List Preview */}
        <div className="mt-8 bg-white rounded-lg shadow-lg p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Users className="h-5 w-5 text-gray-600" />
            Recent Students
          </h3>
          <div className="grid gap-4">
            {students.slice(0, 4).map((student, index) => (
              <div key={index} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white font-semibold">
                    {student.name.split(' ').map(n => n[0]).join('')}
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">{student.name}</p>
                    <p className="text-sm text-gray-500">{student.major} • Age {student.age}</p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                    student.status === 'Active' ? 'bg-green-100 text-green-800' :
                    student.status === 'Graduated' ? 'bg-blue-100 text-blue-800' :
                    'bg-yellow-100 text-yellow-800'
                  }`}>
                    {student.status}
                  </span>
                  <div className="text-right">
                    <p className="text-sm font-medium text-gray-900">GPA: {student.gpa}</p>
                    <p className="text-xs text-gray-500">{student.province}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 text-center">
            <button className="text-blue-600 hover:text-blue-800 text-sm font-medium">
              View All Students →
            </button>
          </div>
        </div>

        {/* Simple Info Card */}
        <div className="mt-8 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg p-6 text-white">
          <h3 className="text-xl font-bold mb-2">📊 Simple Demographics Dashboard</h3>
          <p className="text-blue-100">
            Clean, visual overview of student population with hover effects and responsive charts. 
            Perfect for getting a quick sense of your student demographics!
          </p>
        </div>
      </div>
    </div>
  );
};

export default SimpleStudentDemographics;