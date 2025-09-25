/**
 * Login page component
 */

import React, { useEffect } from 'react';
import { Navigate } from 'react-router-dom';
import { Typography, Row, Col } from 'antd';
import { LoginForm } from '../../components/auth/LoginForm';
import { PageLoadingSpinner } from '../../components/common/LoadingSpinner';
import { useAuth } from '../../hooks/useAuth';
import { useAuthInitialization } from '../../hooks/useAuth';
import { ROUTES, APP_NAME } from '../../utils/constants';

const { Title, Text } = Typography;

/**
 * Login page with branding and authentication form
 */
export const LoginPage: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();
  const { isInitialized, initializeAuth } = useAuthInitialization();

  // Initialize authentication on mount
  useEffect(() => {
    if (!isInitialized && !isLoading) {
      initializeAuth();
    }
  }, [isInitialized, isLoading, initializeAuth]);

  // Show loading spinner while initializing auth
  if (!isInitialized || isLoading) {
    return <PageLoadingSpinner text="Initializing..." />;
  }

  // Redirect if already authenticated
  if (isAuthenticated) {
    return <Navigate to={ROUTES.DASHBOARD} replace />;
  }

  const handleLoginSuccess = () => {
    // Navigation will be handled automatically by the auth state change
    // The App component will redirect to dashboard when isAuthenticated becomes true
  };

  return (
    <div className="login-container">
      <Row justify="center" align="middle" className="min-h-screen">
        <Col xs={24} sm={20} md={16} lg={12} xl={8} xxl={6}>
          <div className="w-full max-w-md mx-auto">
            {/* Branding Section */}
            <div className="text-center mb-8">
              {/* Logo placeholder - replace with actual logo */}
              <div className="mb-6">
                <div className="w-16 h-16 mx-auto bg-blue-600 rounded-full flex items-center justify-center">
                  <span className="text-white text-2xl font-bold">N</span>
                </div>
              </div>

              <Title level={1} className="text-gray-900 mb-2">
                {APP_NAME}
              </Title>

              <Text type="secondary" className="text-lg">
                Staff Portal
              </Text>
            </div>

            {/* Login Form */}
            <LoginForm
              onSuccess={handleLoginSuccess}
              showRememberMe={true}
            />

            {/* Footer Information */}
            <div className="text-center mt-8 space-y-2">
              <Text type="secondary" className="text-sm">
                Pannasastra University of Cambodia
              </Text>
              <br />
              <Text type="secondary" className="text-xs">
                Secure staff access portal
              </Text>
            </div>
          </div>
        </Col>
      </Row>
    </div>
  );
};

export default LoginPage;