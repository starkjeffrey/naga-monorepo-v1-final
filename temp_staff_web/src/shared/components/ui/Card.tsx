/**
 * Card Component
 * Reusable card container with consistent styling
 */

import React from 'react';
import { cardVariants } from './index';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: keyof typeof cardVariants;
  padding?: 'none' | 'sm' | 'base' | 'lg';
  header?: React.ReactNode;
  footer?: React.ReactNode;
}

export const Card: React.FC<CardProps> = ({
  variant = 'default',
  padding = 'base',
  header,
  footer,
  children,
  className = '',
  ...props
}) => {
  const baseClasses = 'rounded-lg';
  const variantClasses = cardVariants[variant];

  const paddingClasses = {
    none: '',
    sm: 'p-4',
    base: 'p-6',
    lg: 'p-8',
  };

  const paddingClass = paddingClasses[padding];
  const classes = `${baseClasses} ${variantClasses} ${className}`.trim();

  return (
    <div className={classes} {...props}>
      {header && (
        <div className={`${padding !== 'none' ? 'border-b border-gray-200 pb-4 mb-4' : 'mb-4'}`}>
          {header}
        </div>
      )}

      <div className={padding !== 'none' ? paddingClass : ''}>
        {children}
      </div>

      {footer && (
        <div className={`${padding !== 'none' ? 'border-t border-gray-200 pt-4 mt-4' : 'mt-4'}`}>
          {footer}
        </div>
      )}
    </div>
  );
};