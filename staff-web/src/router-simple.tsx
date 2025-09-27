import React from 'react';
import { createBrowserRouter } from 'react-router-dom';
import { DatabaseIntegrityReport } from './pages/Reports/DatabaseIntegrityReport';
import { Sidebar } from './components/layout/Sidebar';
import { Header } from './components/layout/Header';

const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">
      <div className="flex">
        <Sidebar />
        <div className="flex-1 lg:ml-80">
          <Header />
          <main className="min-h-screen">
            {children}
          </main>
        </div>
      </div>
    </div>
  );
};

export const simpleRouter = createBrowserRouter([
  {
    path: '/',
    element: (
      <Layout>
        <div className="p-6">
          <h1 className="text-2xl font-bold text-gray-900">PUCSR Staff Portal</h1>
          <p className="text-gray-600">Select a report from the sidebar to get started.</p>
        </div>
      </Layout>
    )
  },
  {
    path: '/reports/database-integrity',
    element: (
      <Layout>
        <DatabaseIntegrityReport />
      </Layout>
    )
  },
  {
    path: '*',
    element: (
      <Layout>
        <div className="p-6">
          <h1 className="text-xl font-bold text-red-600">Page Not Found</h1>
          <p className="text-gray-600">This page is still under development.</p>
        </div>
      </Layout>
    )
  }
]);