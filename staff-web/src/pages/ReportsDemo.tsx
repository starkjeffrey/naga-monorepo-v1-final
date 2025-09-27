import { useEffect, useState } from 'react';

interface StudentData {
  total_students: number;
  active_students: number;
  students_by_status: Array<{ status: string; count: number }>;
  students_by_gender: Array<{ person__gender: string; count: number }>;
}

export default function ReportsDemo() {
  const [studentData, setStudentData] = useState<StudentData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Fetch real data from your Django API
    fetch('http://localhost:8001/api/students/analytics/', {
      headers: {
        'Content-Type': 'application/json',
      }
    })
    .then(response => {
      if (!response.ok) {
        throw new Error('Failed to fetch data');
      }
      return response.json();
    })
    .then(data => {
      setStudentData(data);
      setLoading(false);
    })
    .catch(err => {
      // If API fails, show mock data so you can still see the report
      setStudentData({
        total_students: 1250,
        active_students: 987,
        students_by_status: [
          { status: 'ACTIVE', count: 987 },
          { status: 'INACTIVE', count: 156 },
          { status: 'GRADUATED', count: 107 },
        ],
        students_by_gender: [
          { person__gender: 'M', count: 543 },
          { person__gender: 'F', count: 707 },
        ]
      });
      setError('Using demo data - Django API not connected');
      setLoading(false);
    });
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin h-12 w-12 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-gray-600">Loading student analytics...</p>
        </div>
      </div>
    );
  }

  if (!studentData) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600">Failed to load data</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            📊 Student Analytics Dashboard
          </h1>
          <p className="text-gray-600">
            Real-time insights from your student management system
          </p>
          {error && (
            <div className="mt-2 p-3 bg-yellow-100 border border-yellow-400 text-yellow-700 rounded">
              ⚠️ {error}
            </div>
          )}
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center">
                  <span className="text-white text-lg">👥</span>
                </div>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">Total Students</p>
                <p className="text-2xl font-bold text-gray-900">{studentData.total_students.toLocaleString()}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center">
                  <span className="text-white text-lg">✅</span>
                </div>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">Active Students</p>
                <p className="text-2xl font-bold text-gray-900">{studentData.active_students.toLocaleString()}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-purple-500 rounded-full flex items-center justify-center">
                  <span className="text-white text-lg">📈</span>
                </div>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">Enrollment Rate</p>
                <p className="text-2xl font-bold text-gray-900">
                  {((studentData.active_students / studentData.total_students) * 100).toFixed(1)}%
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-orange-500 rounded-full flex items-center justify-center">
                  <span className="text-white text-lg">🎓</span>
                </div>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">Programs</p>
                <p className="text-2xl font-bold text-gray-900">12</p>
              </div>
            </div>
          </div>
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Student Status */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Students by Status</h3>
            <div className="space-y-3">
              {studentData.students_by_status.map((status, index) => {
                const percentage = (status.count / studentData.total_students) * 100;
                const colors = ['bg-green-500', 'bg-yellow-500', 'bg-blue-500', 'bg-red-500'];
                return (
                  <div key={index} className="flex items-center justify-between">
                    <div className="flex items-center">
                      <div className={`w-3 h-3 rounded-full ${colors[index % colors.length]} mr-3`}></div>
                      <span className="text-sm font-medium text-gray-700">
                        {status.status || 'Unknown'}
                      </span>
                    </div>
                    <div className="flex items-center">
                      <span className="text-sm text-gray-500 mr-2">
                        {status.count} ({percentage.toFixed(1)}%)
                      </span>
                      <div className="w-20 bg-gray-200 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full ${colors[index % colors.length]}`}
                          style={{ width: `${percentage}%` }}
                        ></div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Gender Distribution */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Gender Distribution</h3>
            <div className="space-y-3">
              {studentData.students_by_gender.map((gender, index) => {
                const percentage = (gender.count / studentData.total_students) * 100;
                const colors = ['bg-blue-500', 'bg-pink-500'];
                const labels = { 'M': 'Male', 'F': 'Female', '': 'Not Specified' };
                return (
                  <div key={index} className="flex items-center justify-between">
                    <div className="flex items-center">
                      <div className={`w-3 h-3 rounded-full ${colors[index % colors.length]} mr-3`}></div>
                      <span className="text-sm font-medium text-gray-700">
                        {labels[gender.person__gender as keyof typeof labels] || 'Not Specified'}
                      </span>
                    </div>
                    <div className="flex items-center">
                      <span className="text-sm text-gray-500 mr-2">
                        {gender.count} ({percentage.toFixed(1)}%)
                      </span>
                      <div className="w-20 bg-gray-200 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full ${colors[index % colors.length]}`}
                          style={{ width: `${percentage}%` }}
                        ></div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="mt-8 flex justify-center space-x-4">
          <button className="bg-blue-500 hover:bg-blue-600 text-white px-6 py-2 rounded-lg font-medium transition-colors">
            📊 View Detailed Analytics
          </button>
          <button className="bg-green-500 hover:bg-green-600 text-white px-6 py-2 rounded-lg font-medium transition-colors">
            📈 Export Report
          </button>
          <button className="bg-purple-500 hover:bg-purple-600 text-white px-6 py-2 rounded-lg font-medium transition-colors">
            🤖 AI Insights
          </button>
        </div>
      </div>
    </div>
  );
}