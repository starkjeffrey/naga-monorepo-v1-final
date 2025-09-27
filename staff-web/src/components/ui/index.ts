/**
 * UI Components Library
 * Reusable design system components
 */

export { Button, type ButtonProps } from './Button';
export { Input, type InputProps } from './Input';
export { Card, type CardProps } from './Card';
export { Modal, type ModalProps } from './Modal';
export { LoadingSpinner, type LoadingSpinnerProps } from './LoadingSpinner';

// Component variants and utilities
export const buttonVariants = {
  primary: 'bg-blue-600 text-white hover:bg-blue-700',
  secondary: 'bg-gray-200 text-gray-900 hover:bg-gray-300',
  success: 'bg-green-600 text-white hover:bg-green-700',
  danger: 'bg-red-600 text-white hover:bg-red-700',
  warning: 'bg-yellow-500 text-white hover:bg-yellow-600',
  ghost: 'bg-transparent text-gray-700 hover:bg-gray-100',
  outline: 'bg-transparent border border-gray-300 text-gray-700 hover:bg-gray-50',
} as const;

export const inputVariants = {
  default: 'border-gray-300 focus:border-blue-500 focus:ring-blue-500',
  error: 'border-red-300 focus:border-red-500 focus:ring-red-500',
  success: 'border-green-300 focus:border-green-500 focus:ring-green-500',
} as const;

export const cardVariants = {
  default: 'bg-white border border-gray-200 shadow-sm',
  elevated: 'bg-white border border-gray-200 shadow-md',
  bordered: 'bg-white border border-gray-300',
  ghost: 'bg-transparent',
} as const;