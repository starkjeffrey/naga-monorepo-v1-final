/**
 * Main App component for the PUCSR Staff Portal
 */

import { useEffect } from 'react';
import { RouterProvider } from 'react-router-dom';
import { ConfigProvider, App as AntdApp } from 'antd';
import { router } from './router';
import { useAxiosInterceptor } from './hooks/useAxiosInterceptor';
import { useAuthInitialization } from './hooks/useAuth';
import { PageLoadingSpinner } from './components/common/LoadingSpinner';
import { APP_NAME } from './utils/constants';

// Ant Design theme configuration
const theme = {
  token: {
    colorPrimary: '#1890ff',
    colorSuccess: '#52c41a',
    colorWarning: '#faad14',
    colorError: '#f5222d',
    colorBgContainer: '#ffffff',
    colorBgLayout: '#f0f2f5',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    fontSize: 14,
    borderRadius: 6,
  },
  components: {
    Button: {
      borderRadius: 6,
    },
    Input: {
      borderRadius: 6,
    },
    Card: {
      borderRadius: 8,
    },
  },
};

/**
 * App component with authentication and routing
 */
function App() {
  const { isInitialized, initializeAuth } = useAuthInitialization();

  // Set up axios interceptors
  useAxiosInterceptor();

  // Initialize authentication on app startup
  useEffect(() => {
    document.title = APP_NAME;

    if (!isInitialized) {
      initializeAuth();
    }
  }, [isInitialized, initializeAuth]);

  // Show loading screen while initializing
  if (!isInitialized) {
    return <PageLoadingSpinner text="Initializing application..." />;
  }

  return (
    <ConfigProvider theme={theme}>
      <AntdApp>
        <div className="min-h-screen">
          <RouterProvider router={router} />
        </div>
      </AntdApp>
    </ConfigProvider>
  );
}

export default App;
