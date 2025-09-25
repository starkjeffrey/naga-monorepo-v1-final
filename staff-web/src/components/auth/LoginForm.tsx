/**
 * Login form component for user authentication
 */

import React, { useState, useEffect } from 'react';
import { Form, Input, Button, Checkbox, Card, Typography, Divider } from 'antd';
import { UserOutlined, LockOutlined, EyeInvisibleOutlined, EyeTwoTone } from '@ant-design/icons';
import { useAuth } from '../../hooks/useAuth';
import { ErrorMessage } from '../common/ErrorMessage';
import { ButtonLoadingSpinner } from '../common/LoadingSpinner';
import { VALIDATION_RULES, APP_NAME } from '../../utils/constants';
import type { LoginCredentials, LoginFormData } from '../../types/auth.types';

const { Title, Text } = Typography;

interface LoginFormProps {
  /** Callback when login is successful */
  onSuccess?: () => void;
  /** Callback when login fails */
  onError?: (error: string) => void;
  /** Whether to show the "Remember Me" checkbox */
  showRememberMe?: boolean;
  /** Custom CSS classes */
  className?: string;
}

/**
 * Login form component with validation and error handling
 */
export const LoginForm: React.FC<LoginFormProps> = ({
  onSuccess,
  onError,
  showRememberMe = true,
  className = '',
}) => {
  const { login, isLoading, error, clearError } = useAuth();
  const [form] = Form.useForm<LoginFormData>();
  const [localLoading, setLocalLoading] = useState(false);

  // Auto-focus email field on mount
  useEffect(() => {
    const emailInput = document.getElementById('email');
    if (emailInput) {
      emailInput.focus();
    }
  }, []);

  // Clear errors when form values change
  useEffect(() => {
    if (error) {
      clearError();
    }
  }, [error, clearError]);

  const handleSubmit = async (values: LoginFormData) => {
    setLocalLoading(true);
    clearError();

    try {
      const credentials: LoginCredentials = {
        email: values.email.trim(),
        password: values.password,
        rememberMe: values.rememberMe || false,
      };

      await login(credentials);

      // Login successful
      if (onSuccess) {
        onSuccess();
      }
    } catch (err: any) {
      const errorMessage = err?.message || 'Login failed. Please try again.';

      if (onError) {
        onError(errorMessage);
      }

      // Focus back to email field for retry
      setTimeout(() => {
        const emailInput = document.getElementById('email');
        if (emailInput) {
          emailInput.focus();
        }
      }, 100);
    } finally {
      setLocalLoading(false);
    }
  };

  const handleKeyPress = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter') {
      form.submit();
    }
  };

  const isSubmitDisabled = localLoading || isLoading;

  return (
    <Card className={`login-card ${className}`} bordered={false}>
      {/* Header */}
      <div className="text-center mb-8">
        <Title level={2} className="text-gray-900 mb-2">
          Welcome Back
        </Title>
        <Text type="secondary" className="text-base">
          Sign in to {APP_NAME}
        </Text>
      </div>

      {/* Error Display */}
      {error && (
        <div className="mb-6">
          <ErrorMessage
            message={error}
            type="error"
            closable
            onClose={clearError}
            inline
          />
        </div>
      )}

      {/* Login Form */}
      <Form
        form={form}
        name="login"
        onFinish={handleSubmit}
        autoComplete="on"
        size="large"
        className="space-y-4"
        onKeyPress={handleKeyPress}
      >
        {/* Email Field */}
        <Form.Item
          name="email"
          rules={[
            {
              required: true,
              message: VALIDATION_RULES.EMAIL.REQUIRED,
            },
            {
              type: 'email',
              message: VALIDATION_RULES.EMAIL.INVALID,
            },
          ]}
          className="mb-4"
        >
          <Input
            id="email"
            prefix={<UserOutlined className="text-gray-500" />}
            placeholder="Email address"
            autoComplete="email"
            className="form-input"
            disabled={isSubmitDisabled}
          />
        </Form.Item>

        {/* Password Field */}
        <Form.Item
          name="password"
          rules={[
            {
              required: true,
              message: VALIDATION_RULES.PASSWORD.REQUIRED,
            },
          ]}
          className="mb-4"
        >
          <Input.Password
            id="password"
            prefix={<LockOutlined className="text-gray-500" />}
            placeholder="Password"
            autoComplete="current-password"
            className="form-input"
            iconRender={(visible) =>
              visible ? <EyeTwoTone /> : <EyeInvisibleOutlined />
            }
            disabled={isSubmitDisabled}
          />
        </Form.Item>

        {/* Remember Me */}
        {showRememberMe && (
          <Form.Item name="rememberMe" valuePropName="checked" className="mb-6">
            <Checkbox disabled={isSubmitDisabled}>
              <span className="text-gray-600">Remember me for 30 days</span>
            </Checkbox>
          </Form.Item>
        )}

        {/* Submit Button */}
        <Form.Item className="mb-0">
          <Button
            type="primary"
            htmlType="submit"
            className="btn-primary"
            size="large"
            loading={isSubmitDisabled}
            disabled={isSubmitDisabled}
            icon={isSubmitDisabled ? <ButtonLoadingSpinner /> : undefined}
          >
            {isSubmitDisabled ? 'Signing in...' : 'Sign In'}
          </Button>
        </Form.Item>
      </Form>

      {/* Footer */}
      <Divider className="my-6" />
      <div className="text-center">
        <span className="text-gray-600 text-sm">
          Having trouble signing in? Contact your administrator.
        </span>
      </div>
    </Card>
  );
};

/**
 * Simplified login form for modal usage
 */
export const ModalLoginForm: React.FC<{
  onSuccess: () => void;
  onCancel: () => void;
}> = ({ onSuccess, onCancel }) => {
  return (
    <div className="p-4">
      <LoginForm
        onSuccess={onSuccess}
        showRememberMe={false}
        className="shadow-none"
      />
      <div className="text-center mt-4">
        <Button onClick={onCancel}>Cancel</Button>
      </div>
    </div>
  );
};

export default LoginForm;