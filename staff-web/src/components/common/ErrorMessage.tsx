/**
 * ErrorMessage component for displaying error states
 */

import React from 'react';
import { Alert, Button } from 'antd';
import { ExclamationCircleOutlined, ReloadOutlined, CloseCircleOutlined } from '@ant-design/icons';

interface ErrorMessageProps {
  /** Error message to display */
  message: string;
  /** Error description (optional) */
  description?: string;
  /** Type of error */
  type?: 'error' | 'warning' | 'info';
  /** Whether the error can be dismissed */
  closable?: boolean;
  /** Callback when error is dismissed */
  onClose?: () => void;
  /** Whether to show a retry button */
  showRetry?: boolean;
  /** Callback for retry action */
  onRetry?: () => void;
  /** Custom CSS classes */
  className?: string;
  /** Whether to show the error inline */
  inline?: boolean;
}

/**
 * Reusable error message component
 */
export const ErrorMessage: React.FC<ErrorMessageProps> = ({
  message,
  description,
  type = 'error',
  closable = true,
  onClose,
  showRetry = false,
  onRetry,
  className = '',
  inline = false,
}) => {
  const getIcon = () => {
    switch (type) {
      case 'warning':
        return <ExclamationCircleOutlined />;
      case 'info':
        return <ExclamationCircleOutlined />;
      default:
        return <CloseCircleOutlined />;
    }
  };

  const action = showRetry && onRetry ? (
    <Button
      size="small"
      type="text"
      icon={<ReloadOutlined />}
      onClick={onRetry}
    >
      Retry
    </Button>
  ) : undefined;

  return (
    <div
      className={`
        ${!inline ? 'my-4' : ''}
        ${className}
      `}
    >
      <Alert
        message={message}
        description={description}
        type={type}
        showIcon
        icon={getIcon()}
        closable={closable}
        onClose={onClose}
        action={action}
        className="rounded-md"
      />
    </div>
  );
};

/**
 * Inline error message for forms
 */
export const FormErrorMessage: React.FC<{
  message?: string;
  className?: string;
}> = ({ message, className = '' }) => {
  if (!message) return null;

  return (
    <div className={`error-message ${className}`}>
      {message}
    </div>
  );
};

/**
 * Page-level error component
 */
export const PageError: React.FC<{
  title?: string;
  message: string;
  onRetry?: () => void;
}> = ({
  title = 'Something went wrong',
  message,
  onRetry,
}) => (
  <div className="min-h-[400px] flex items-center justify-center">
    <div className="text-center max-w-md mx-auto px-4">
      <CloseCircleOutlined className="text-6xl text-red-500 mb-4" />
      <h2 className="text-xl font-semibold text-gray-900 mb-2">
        {title}
      </h2>
      <p className="text-gray-600 mb-6">
        {message}
      </p>
      {onRetry && (
        <Button
          type="primary"
          icon={<ReloadOutlined />}
          onClick={onRetry}
        >
          Try Again
        </Button>
      )}
    </div>
  </div>
);

/**
 * Network error component
 */
export const NetworkError: React.FC<{
  onRetry?: () => void;
}> = ({ onRetry }) => (
  <PageError
    title="Connection Problem"
    message="Unable to connect to the server. Please check your internet connection and try again."
    onRetry={onRetry}
  />
);

/**
 * Authentication error component
 */
export const AuthError: React.FC<{
  onRetry?: () => void;
}> = ({ onRetry }) => (
  <PageError
    title="Authentication Required"
    message="Your session has expired. Please log in again to continue."
    onRetry={onRetry}
  />
);

/**
 * Generic API error component
 */
export const ApiError: React.FC<{
  error: any;
  onRetry?: () => void;
  onDismiss?: () => void;
}> = ({ error, onRetry, onDismiss }) => {
  const getMessage = () => {
    if (typeof error === 'string') return error;
    if (error?.message) return error.message;
    return 'An unexpected error occurred';
  };

  const getDescription = () => {
    if (error?.detail) return error.detail;
    if (error?.status) return `Error code: ${error.status}`;
    return undefined;
  };

  return (
    <ErrorMessage
      message={getMessage()}
      description={getDescription()}
      showRetry={Boolean(onRetry)}
      onRetry={onRetry}
      onClose={onDismiss}
    />
  );
};

export default ErrorMessage;