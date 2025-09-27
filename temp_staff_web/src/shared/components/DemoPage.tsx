import React from 'react';
import { Link } from 'react-router-dom';
import { BarChart3, Users, Calendar, Eye } from 'lucide-react';

const DemoPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-8">
      <div className="max-w-4xl mx-auto">
        <div className="bg-white rounded-2xl shadow-xl p-8">
          <div className="text-center mb-8">
            <h1 className="text-4xl font-bold text-gray-900 mb-4">
              🎓 Demo Components
            </h1>
            <p className="text-gray-600 text-lg">
              Quick access to the demo components we've created
            </p>
          </div>

          <div className="grid gap-6">
            {/* Student Demographics */}
            <div className="group">
              <Link 
                to="/reports/demographics"
                className="block p-6 border-2 border-gray-200 rounded-xl hover:border-blue-500 hover:shadow-lg transition-all duration-200 group-hover:bg-blue-50"
              >
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                    <BarChart3 className="h-6 w-6 text-white" />
                  </div>
                  <div className="flex-1">
                    <h3 className="text-xl font-semibold text-gray-900 group-hover:text-blue-700">
                      📊 Student Demographics Dashboard
                    </h3>
                    <p className="text-gray-600 mt-1">
                      Interactive charts showing gender, age, provinces, majors, and status distributions with hover effects
                    </p>
                    <div className="flex items-center gap-2 mt-2">
                      <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full">Charts</span>
                      <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full">Interactive</span>
                      <span className="text-xs bg-purple-100 text-purple-800 px-2 py-1 rounded-full">Responsive</span>
                    </div>
                  </div>
                  <Eye className="h-5 w-5 text-gray-400 group-hover:text-blue-500" />
                </div>
              </Link>
            </div>

            {/* Other Demo Components */}
            <div className="group">
              <Link 
                to="/components/reports/AdvancedDataTable"
                className="block p-6 border-2 border-gray-200 rounded-xl hover:border-green-500 hover:shadow-lg transition-all duration-200 group-hover:bg-green-50"
              >
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-gradient-to-r from-green-500 to-teal-600 rounded-lg flex items-center justify-center">
                    <Users className="h-6 w-6 text-white" />
                  </div>
                  <div className="flex-1">
                    <h3 className="text-xl font-semibold text-gray-900 group-hover:text-green-700">
                      🗃️ Advanced Student Table (Created Earlier)
                    </h3>
                    <p className="text-gray-600 mt-1">
                      Drag & drop columns, sorting, filtering, and pagination with complete student data
                    </p>
                    <div className="flex items-center gap-2 mt-2">
                      <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full">Drag & Drop</span>
                      <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full">TanStack Table</span>
                    </div>
                  </div>
                  <Eye className="h-5 w-5 text-gray-400 group-hover:text-green-500" />
                </div>
              </Link>
            </div>

            {/* Quick Access Info */}
            <div className="mt-8 p-6 bg-gradient-to-r from-indigo-500 to-purple-600 rounded-xl text-white">
              <h3 className="text-lg font-bold mb-2">🚀 Quick Access</h3>
              <p className="text-indigo-100">
                Direct URL: <code className="bg-white/20 px-2 py-1 rounded">http://localhost:5173/reports/demographics</code>
              </p>
              <p className="text-indigo-100 mt-2">
                Or use the sidebar: Reports & Analytics → Student Demographics
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DemoPage;