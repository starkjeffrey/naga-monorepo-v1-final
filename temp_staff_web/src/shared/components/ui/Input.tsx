/**
 * Input Component
 * Reusable input with consistent styling and validation
 */

import React from 'react';
import { inputVariants } from './index';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  variant?: keyof typeof inputVariants;
  label?: string;
  helperText?: string;
  error?: string;
  icon?: React.ReactNode;
  iconPosition?: 'left' | 'right';
  fullWidth?: boolean;
}

export const Input: React.FC<InputProps> = ({
  variant = 'default',
  label,
  helperText,
  error,
  icon,
  iconPosition = 'left',
  fullWidth = false,
  className = '',
  id,
  ...props
}) => {
  const inputId = id || `input-${Math.random().toString(36).substr(2, 9)}`;
  const hasError = Boolean(error);
  const actualVariant = hasError ? 'error' : variant;

  const baseClasses = 'block rounded-md border px-3 py-2 text-sm placeholder-gray-400 focus:outline-none focus:ring-1 transition-colors duration-150';
  const variantClasses = inputVariants[actualVariant];
  const widthClass = fullWidth ? 'w-full' : '';
  const iconPaddingClass = icon ? (iconPosition === 'left' ? 'pl-10' : 'pr-10') : '';

  const inputClasses = `${baseClasses} ${variantClasses} ${widthClass} ${iconPaddingClass} ${className}`.trim();

  return (
    <div className={fullWidth ? 'w-full' : ''}>
      {label && (
        <label
          htmlFor={inputId}
          className="block text-sm font-medium text-gray-700 mb-1"
        >
          {label}
        </label>
      )}

      <div className="relative">
        {icon && iconPosition === 'left' && (
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <span className="text-gray-400">{icon}</span>
          </div>
        )}

        <input
          id={inputId}
          className={inputClasses}
          {...props}
        />

        {icon && iconPosition === 'right' && (
          <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
            <span className="text-gray-400">{icon}</span>
          </div>
        )}
      </div>

      {(error || helperText) && (
        <div className="mt-1">
          {error && (
            <p className="text-sm text-red-600">{error}</p>
          )}
          {helperText && !error && (
            <p className="text-sm text-gray-500">{helperText}</p>
          )}
        </div>
      )}
    </div>
  );
};