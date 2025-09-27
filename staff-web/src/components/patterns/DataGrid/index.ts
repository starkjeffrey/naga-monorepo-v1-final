/**
 * Enhanced DataGrid Pattern Exports
 * Complete export file for the DataGrid pattern
 */

// Main component
export { default as DataGrid } from './DataGrid';

// Sub-components
export { DataGridToolbar } from './components/DataGridToolbar';
export { DataGridHeader } from './components/DataGridHeader';
export { DataGridBody } from './components/DataGridBody';
export {
  DataGridPagination,
  SimplePagination,
  PageSizeSelector,
  NavigationPagination
} from './components/DataGridPagination';

// Hooks
export { useDataGrid } from './hooks/useDataGrid';

// Types
export type {
  DataGridColumn,
  DataGridAction,
  DataGridBulkAction,
  DataGridFilter,
  DataGridSort,
  DataGridPagination as DataGridPaginationType,
  SavedFilterPreset,
  DataGridExportOptions,
  DataGridState,
  DataGridProps,
  DataGridRef,
  UseDataGridReturn,
  DataGridRowClickEvent,
  DataGridCellClickEvent,
  DataGridHeaderClickEvent
} from './types';

// Utility functions for common use cases
export const createColumn = <T = any>(
  id: string,
  label: string,
  accessor: keyof T | ((row: T) => any),
  options: Partial<Omit<DataGridColumn<T>, 'id' | 'label' | 'accessor'>> = {}
): DataGridColumn<T> => ({
  id,
  label,
  accessor,
  sortable: true,
  filterable: true,
  resizable: true,
  ...options
});

export const createAction = <T = any>(
  id: string,
  label: string,
  onClick: (row: T) => void,
  options: Partial<Omit<DataGridAction<T>, 'id' | 'label' | 'onClick'>> = {}
): DataGridAction<T> => ({
  id,
  label,
  onClick,
  variant: 'secondary',
  showInMenu: false,
  ...options
});

export const createBulkAction = <T = any>(
  id: string,
  label: string,
  onClick: (rows: T[]) => void,
  options: Partial<Omit<DataGridBulkAction<T>, 'id' | 'label' | 'onClick'>> = {}
): DataGridBulkAction<T> => ({
  id,
  label,
  onClick,
  variant: 'primary',
  ...options
});

// Common column formatters
export const formatters = {
  currency: (value: number, currency = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency
    }).format(value);
  },

  date: (value: Date | string, format: 'short' | 'medium' | 'long' = 'medium') => {
    const date = value instanceof Date ? value : new Date(value);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: format === 'short' ? 'numeric' : format === 'medium' ? 'short' : 'long',
      day: 'numeric'
    });
  },

  datetime: (value: Date | string) => {
    const date = value instanceof Date ? value : new Date(value);
    return date.toLocaleString('en-US');
  },

  number: (value: number, decimals = 0) => {
    return new Intl.NumberFormat('en-US', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    }).format(value);
  },

  percentage: (value: number, decimals = 1) => {
    return `${(value * 100).toFixed(decimals)}%`;
  },

  badge: (value: string, variant: 'success' | 'warning' | 'error' | 'info' = 'info') => {
    const variants = {
      success: 'bg-green-100 text-green-800',
      warning: 'bg-yellow-100 text-yellow-800',
      error: 'bg-red-100 text-red-800',
      info: 'bg-blue-100 text-blue-800'
    };

    return (
      <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${variants[variant]}`}>
        {value}
      </span>
    );
  },

  boolean: (value: boolean, labels = { true: 'Yes', false: 'No' }) => {
    return (
      <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
        value ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
      }`}>
        {value ? labels.true : labels.false}
      </span>
    );
  },

  truncate: (value: string, maxLength = 50) => {
    if (value.length <= maxLength) return value;
    return `${value.substring(0, maxLength)}...`;
  }
};

// Predefined column configurations for common data types
export const columnPresets = {
  id: <T = any>(accessor: keyof T = 'id' as keyof T) => createColumn(
    'id',
    'ID',
    accessor,
    { width: 80, sortable: true, filterable: false }
  ),

  name: <T = any>(accessor: keyof T = 'name' as keyof T) => createColumn(
    'name',
    'Name',
    accessor,
    { minWidth: 200, sortable: true, filterable: true }
  ),

  email: <T = any>(accessor: keyof T = 'email' as keyof T) => createColumn(
    'email',
    'Email',
    accessor,
    { minWidth: 200, sortable: true, filterable: true }
  ),

  status: <T = any>(
    accessor: keyof T = 'status' as keyof T,
    options?: Array<{ label: string; value: any }>
  ) => createColumn(
    'status',
    'Status',
    accessor,
    {
      width: 120,
      sortable: true,
      filterable: true,
      filterType: 'select',
      filterOptions: options,
      format: (value) => formatters.badge(value,
        value === 'active' ? 'success' :
        value === 'pending' ? 'warning' : 'error'
      )
    }
  ),

  createdAt: <T = any>(accessor: keyof T = 'createdAt' as keyof T) => createColumn(
    'createdAt',
    'Created',
    accessor,
    {
      width: 150,
      sortable: true,
      filterable: false,
      format: (value) => formatters.datetime(value)
    }
  ),

  updatedAt: <T = any>(accessor: keyof T = 'updatedAt' as keyof T) => createColumn(
    'updatedAt',
    'Updated',
    accessor,
    {
      width: 150,
      sortable: true,
      filterable: false,
      format: (value) => formatters.datetime(value)
    }
  ),

  amount: <T = any>(accessor: keyof T = 'amount' as keyof T, currency = 'USD') => createColumn(
    'amount',
    'Amount',
    accessor,
    {
      width: 120,
      align: 'right',
      sortable: true,
      filterable: true,
      filterType: 'number',
      format: (value) => formatters.currency(value, currency)
    }
  )
};

// Default export for convenience
export {
  DataGrid as default,
  type DataGridColumn,
  type DataGridProps,
  type DataGridRef
} from './DataGrid';