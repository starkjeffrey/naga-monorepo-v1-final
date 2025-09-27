/**
 * LoadingSpinner component for displaying loading states
 */

import React from 'react';
import { Spin } from 'antd';
import { LoadingOutlined } from '@ant-design/icons';

interface LoadingSpinnerProps {
  /** Size of the spinner */
  size?: 'small' | 'default' | 'large';
  /** Custom text to display below spinner */
  text?: string;
  /** Whether to show the spinner inline */
  inline?: boolean;
  /** Custom CSS classes */
  className?: string;
  /** Whether to center the spinner */
  centered?: boolean;
}

/**
 * Reusable loading spinner component
 */
export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'default',
  text,
  inline = false,
  className = '',
  centered = true,
}) => {
  const antIcon = <LoadingOutlined style={{ fontSize: getSpinnerSize(size) }} spin />;

  const spinner = (
    <Spin
      indicator={antIcon}
      size={size}
      tip={text}
      className={className}
    />
  );

  if (inline) {
    return spinner;
  }

  return (
    <div
      className={`
        ${centered ? 'flex items-center justify-center' : ''}
        ${!inline ? 'min-h-[100px]' : ''}
        ${className}
      `}
      role="status"
      aria-label={text || 'Loading'}
    >
      {spinner}
    </div>
  );
};

/**
 * Helper function to get spinner size in pixels
 */
const getSpinnerSize = (size: 'small' | 'default' | 'large'): number => {
  switch (size) {
    case 'small':
      return 16;
    case 'large':
      return 32;
    default:
      return 24;
  }
};

/**
 * Inline loading spinner for buttons
 */
export const ButtonLoadingSpinner: React.FC = () => (
  <LoadingOutlined className="loading-spinner mr-2" />
);

/**
 * Full page loading spinner
 */
export const PageLoadingSpinner: React.FC<{ text?: string }> = ({ text = 'Loading...' }) => (
  <div className="min-h-screen flex items-center justify-center bg-gray-50">
    <div className="text-center">
      <LoadingSpinner size="large" text={text} />
    </div>
  </div>
);

/**
 * Card loading spinner
 */
export const CardLoadingSpinner: React.FC<{ text?: string }> = ({ text }) => (
  <div className="p-8 text-center">
    <LoadingSpinner text={text} />
  </div>
);

export default LoadingSpinner;