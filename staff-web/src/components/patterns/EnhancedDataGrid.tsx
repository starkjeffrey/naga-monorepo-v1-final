/**
 * Enhanced DataGrid Pattern
 *
 * A comprehensive data grid component with advanced features:
 * - Search and filtering capabilities
 * - Sortable columns
 * - Selection management
 * - Bulk operations
 * - Export functionality
 * - Responsive design
 * - Performance optimized
 */

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  Table,
  Input,
  Button,
  Select,
  Checkbox,
  Space,
  Dropdown,
  Tooltip,
  Badge,
  Pagination,
  Card,
  Empty,
  Spin,
  Tag,
  Avatar,
  message,
} from 'antd';
import {
  SearchOutlined,
  FilterOutlined,
  DownloadOutlined,
  ReloadOutlined,
  MoreOutlined,
  EyeOutlined,
  EditOutlined,
  DeleteOutlined,
  UserOutlined,
} from '@ant-design/icons';
import type { ColumnType, TableRowSelection } from 'antd/es/table/interface';

const { Option } = Select;

export interface DataGridColumn<T = any> {
  key: string;
  title: string;
  dataIndex?: string;
  sortable?: boolean;
  filterable?: boolean;
  searchable?: boolean;
  width?: number;
  fixed?: 'left' | 'right';
  render?: (value: any, record: T, index: number) => React.ReactNode;
  filterOptions?: Array<{ label: string; value: any }>;
}

export interface DataGridAction<T = any> {
  key: string;
  label: string;
  icon?: React.ReactNode;
  onClick: (record: T) => void;
  disabled?: (record: T) => boolean;
  visible?: (record: T) => boolean;
  danger?: boolean;
}

export interface DataGridFilters {
  [key: string]: any;
}

export interface DataGridProps<T = any> {
  // Data
  data: T[];
  loading?: boolean;

  // Columns
  columns: DataGridColumn<T>[];
  rowKey: string | ((record: T) => string);

  // Search & Filtering
  searchable?: boolean;
  searchPlaceholder?: string;
  globalSearch?: boolean;
  filters?: DataGridFilters;
  onFiltersChange?: (filters: DataGridFilters) => void;

  // Selection
  selectable?: boolean;
  selectedRowKeys?: React.Key[];
  onSelectionChange?: (selectedRowKeys: React.Key[], selectedRows: T[]) => void;

  // Actions
  actions?: DataGridAction<T>[];
  bulkActions?: Array<{
    key: string;
    label: string;
    icon?: React.ReactNode;
    onClick: (selectedRows: T[]) => void;
    disabled?: boolean;
    danger?: boolean;
  }>;

  // Pagination
  pagination?: {
    current: number;
    pageSize: number;
    total: number;
    showSizeChanger?: boolean;
    pageSizeOptions?: string[];
    onChange?: (page: number, pageSize: number) => void;
  };

  // Export
  exportable?: boolean;
  onExport?: (data: T[], filters: DataGridFilters) => void;

  // Styling
  size?: 'small' | 'middle' | 'large';
  bordered?: boolean;
  showHeader?: boolean;

  // Events
  onRowClick?: (record: T) => void;
  onRefresh?: () => void;

  // Empty state
  emptyText?: string;
  emptyDescription?: string;
  emptyAction?: React.ReactNode;
}

export function EnhancedDataGrid<T = any>({
  data,
  loading = false,
  columns,
  rowKey,
  searchable = true,
  searchPlaceholder = "Search...",
  globalSearch = true,
  filters = {},
  onFiltersChange,
  selectable = false,
  selectedRowKeys = [],
  onSelectionChange,
  actions = [],
  bulkActions = [],
  pagination,
  exportable = false,
  onExport,
  size = 'middle',
  bordered = true,
  showHeader = true,
  onRowClick,
  onRefresh,
  emptyText = "No data found",
  emptyDescription,
  emptyAction,
}: DataGridProps<T>) {
  const [searchTerm, setSearchTerm] = useState('');
  const [localFilters, setLocalFilters] = useState<DataGridFilters>(filters);
  const [sortConfig, setSortConfig] = useState<{ key: string; direction: 'asc' | 'desc' } | null>(null);

  // Update local filters when external filters change
  useEffect(() => {
    setLocalFilters(filters);
  }, [filters]);

  // Debounced search
  const [debouncedSearchTerm, setDebouncedSearchTerm] = useState(searchTerm);
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchTerm(searchTerm);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  // Filter data based on search term and filters
  const filteredData = useMemo(() => {
    let result = [...data];

    // Apply global search
    if (globalSearch && debouncedSearchTerm) {
      const searchLower = debouncedSearchTerm.toLowerCase();
      result = result.filter(item => {
        return columns.some(column => {
          if (!column.searchable && column.searchable !== undefined) return false;

          const value = column.dataIndex ? item[column.dataIndex] : item;
          if (value == null) return false;

          return String(value).toLowerCase().includes(searchLower);
        });
      });
    }

    // Apply column filters
    Object.entries(localFilters).forEach(([key, value]) => {
      if (value != null && value !== '') {
        result = result.filter(item => {
          const itemValue = item[key];
          if (Array.isArray(value)) {
            return value.includes(itemValue);
          }
          return itemValue === value;
        });
      }
    });

    // Apply sorting
    if (sortConfig) {
      result.sort((a, b) => {
        const aVal = a[sortConfig.key];
        const bVal = b[sortConfig.key];

        if (aVal == null && bVal == null) return 0;
        if (aVal == null) return sortConfig.direction === 'asc' ? -1 : 1;
        if (bVal == null) return sortConfig.direction === 'asc' ? 1 : -1;

        if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
        if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
        return 0;
      });
    }

    return result;
  }, [data, debouncedSearchTerm, localFilters, sortConfig, columns, globalSearch]);

  // Handle filter changes
  const handleFilterChange = useCallback((key: string, value: any) => {
    const newFilters = { ...localFilters, [key]: value };
    setLocalFilters(newFilters);
    onFiltersChange?.(newFilters);
  }, [localFilters, onFiltersChange]);

  // Handle sort changes
  const handleSort = useCallback((key: string) => {
    setSortConfig(current => {
      if (current?.key === key) {
        return current.direction === 'asc'
          ? { key, direction: 'desc' }
          : null;
      }
      return { key, direction: 'asc' };
    });
  }, []);

  // Handle export
  const handleExport = useCallback(() => {
    onExport?.(filteredData, localFilters);
  }, [onExport, filteredData, localFilters]);

  // Convert columns to Ant Design table columns
  const tableColumns: ColumnType<T>[] = useMemo(() => {
    const result = columns.map(column => {
      const antColumn: ColumnType<T> = {
        key: column.key,
        title: (
          <div className="flex items-center justify-between">
            <span>{column.title}</span>
            {column.sortable && (
              <Button
                type="text"
                size="small"
                onClick={() => handleSort(column.dataIndex || column.key)}
                icon={
                  sortConfig?.key === (column.dataIndex || column.key)
                    ? sortConfig.direction === 'asc' ? '↑' : '↓'
                    : '↕'
                }
              />
            )}
          </div>
        ),
        dataIndex: column.dataIndex,
        width: column.width,
        fixed: column.fixed,
        render: column.render,
        sorter: column.sortable ? true : false,
        filterDropdown: column.filterable && column.filterOptions ? (
          <div className="p-3">
            <Select
              style={{ width: 200 }}
              placeholder={`Filter ${column.title}`}
              allowClear
              value={localFilters[column.dataIndex || column.key]}
              onChange={(value) => handleFilterChange(column.dataIndex || column.key, value)}
            >
              {column.filterOptions?.map(option => (
                <Option key={option.value} value={option.value}>
                  {option.label}
                </Option>
              ))}
            </Select>
          </div>
        ) : undefined,
      };

      return antColumn;
    });

    // Add actions column if actions are provided
    if (actions.length > 0) {
      result.push({
        key: 'actions',
        title: 'Actions',
        width: 120,
        fixed: 'right',
        render: (_, record) => {
          const visibleActions = actions.filter(action =>
            action.visible ? action.visible(record) : true
          );

          if (visibleActions.length === 0) return null;

          if (visibleActions.length === 1) {
            const action = visibleActions[0];
            return (
              <Button
                type="link"
                size="small"
                icon={action.icon}
                onClick={() => action.onClick(record)}
                disabled={action.disabled ? action.disabled(record) : false}
                danger={action.danger}
              >
                {action.label}
              </Button>
            );
          }

          return (
            <Dropdown
              menu={{
                items: visibleActions.map(action => ({
                  key: action.key,
                  label: action.label,
                  icon: action.icon,
                  danger: action.danger,
                  disabled: action.disabled ? action.disabled(record) : false,
                  onClick: () => action.onClick(record),
                })),
              }}
              trigger={['click']}
            >
              <Button type="link" size="small" icon={<MoreOutlined />} />
            </Dropdown>
          );
        },
      });
    }

    return result;
  }, [columns, actions, sortConfig, localFilters, handleSort, handleFilterChange]);

  // Row selection configuration
  const rowSelection: TableRowSelection<T> | undefined = selectable ? {
    selectedRowKeys,
    onChange: onSelectionChange,
    selections: [
      Table.SELECTION_ALL,
      Table.SELECTION_INVERT,
      Table.SELECTION_NONE,
    ],
  } : undefined;

  // Get selected rows for bulk actions
  const selectedRows = useMemo(() => {
    return filteredData.filter(item => {
      const key = typeof rowKey === 'function' ? rowKey(item) : item[rowKey];
      return selectedRowKeys.includes(key);
    });
  }, [filteredData, selectedRowKeys, rowKey]);

  return (
    <Card className="enhanced-data-grid">
      {/* Header with search, filters, and actions */}
      <div className="mb-4 space-y-3">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
          <div className="flex-1 max-w-md">
            {searchable && (
              <Input
                placeholder={searchPlaceholder}
                prefix={<SearchOutlined />}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                allowClear
              />
            )}
          </div>

          <Space>
            {exportable && (
              <Button
                icon={<DownloadOutlined />}
                onClick={handleExport}
                disabled={filteredData.length === 0}
              >
                Export
              </Button>
            )}

            {onRefresh && (
              <Button
                icon={<ReloadOutlined />}
                onClick={onRefresh}
                loading={loading}
              >
                Refresh
              </Button>
            )}
          </Space>
        </div>

        {/* Bulk actions */}
        {selectable && selectedRowKeys.length > 0 && bulkActions.length > 0 && (
          <div className="bg-blue-50 p-3 rounded-lg">
            <div className="flex items-center justify-between">
              <span className="text-blue-700 font-medium">
                {selectedRowKeys.length} item{selectedRowKeys.length !== 1 ? 's' : ''} selected
              </span>
              <Space>
                {bulkActions.map(action => (
                  <Button
                    key={action.key}
                    type="primary"
                    size="small"
                    icon={action.icon}
                    onClick={() => action.onClick(selectedRows)}
                    disabled={action.disabled}
                    danger={action.danger}
                  >
                    {action.label}
                  </Button>
                ))}
              </Space>
            </div>
          </div>
        )}
      </div>

      {/* Table */}
      <Table<T>
        columns={tableColumns}
        dataSource={filteredData}
        rowKey={rowKey}
        rowSelection={rowSelection}
        loading={loading}
        size={size}
        bordered={bordered}
        showHeader={showHeader}
        pagination={pagination ? {
          ...pagination,
          showTotal: (total, range) => `${range[0]}-${range[1]} of ${total} items`,
          showSizeChanger: pagination.showSizeChanger !== false,
          pageSizeOptions: pagination.pageSizeOptions || ['10', '20', '50', '100'],
        } : false}
        onRow={(record) => ({
          onClick: () => onRowClick?.(record),
          className: onRowClick ? 'cursor-pointer hover:bg-gray-50' : '',
        })}
        locale={{
          emptyText: filteredData.length === 0 && data.length > 0 ? (
            <Empty
              description="No results found"
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            >
              <Button type="primary" onClick={() => {
                setSearchTerm('');
                setLocalFilters({});
                onFiltersChange?.({});
              }}>
                Clear Filters
              </Button>
            </Empty>
          ) : (
            <Empty
              description={emptyDescription || emptyText}
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            >
              {emptyAction}
            </Empty>
          ),
        }}
      />
    </Card>
  );
}

export default EnhancedDataGrid;