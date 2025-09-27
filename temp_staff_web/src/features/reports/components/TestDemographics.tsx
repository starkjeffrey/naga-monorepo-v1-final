import React from 'react';

const TestDemographics: React.FC = () => {
  console.log("TestDemographics component rendering...");
  
  try {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-3xl font-bold text-gray-900 mb-4">
            🎓 Test Demographics Dashboard
          </h1>
          <p className="text-gray-600">
            If you see this, the basic component is working!
          </p>
          
          {/* Simple test content */}
          <div className="mt-8 bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Basic Test</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-blue-50 p-4 rounded">
                <h3 className="font-medium text-blue-900">Test Card 1</h3>
                <p className="text-blue-700">Working correctly!</p>
              </div>
              <div className="bg-green-50 p-4 rounded">
                <h3 className="font-medium text-green-900">Test Card 2</h3>
                <p className="text-green-700">No chart dependencies</p>
              </div>
              <div className="bg-purple-50 p-4 rounded">
                <h3 className="font-medium text-purple-900">Test Card 3</h3>
                <p className="text-purple-700">Basic React + Tailwind</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  } catch (error) {
    console.error("Error in TestDemographics:", error);
    return (
      <div className="min-h-screen bg-red-50 p-6">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-3xl font-bold text-red-900 mb-4">
            Error in Test Component
          </h1>
          <p className="text-red-600">
            {error instanceof Error ? error.message : 'Unknown error'}
          </p>
        </div>
      </div>
    );
  }
};

export default TestDemographics;