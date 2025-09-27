/**
 * DataGrid Header Component
 * Handles column headers with sorting, filtering, and resizing
 */

import React, { useState, useRef, useCallback } from 'react';
import { ChevronUp, ChevronDown, Filter, Settings, Eye, EyeOff } from 'lucide-react';
import { DataGridColumn, DataGridSort, DataGridFilter } from '../types';

interface DataGridHeaderProps<T> {
  columns: DataGridColumn<T>[];
  sorts: DataGridSort[];
  filters: DataGridFilter[];
  columnVisibility: Record<string, boolean>;
  columnWidths: Record<string, number>;
  onSortChange: (sort: DataGridSort) => void;
  onFilterChange: (filter: DataGridFilter) => void;
  onColumnVisibilityChange: (columnId: string, visible: boolean) => void;
  onColumnWidthChange: (columnId: string, width: number) => void;
  sortable?: boolean;
  filterable?: boolean;
  resizable?: boolean;
  hideable?: boolean;
}

export function DataGridHeader<T>({
  columns,
  sorts,
  filters,
  columnVisibility,
  columnWidths,
  onSortChange,
  onFilterChange,
  onColumnVisibilityChange,
  onColumnWidthChange,
  sortable = true,
  filterable = true,
  resizable = true,
  hideable = true
}: DataGridHeaderProps<T>) {
  const [resizingColumn, setResizingColumn] = useState<string | null>(null);
  const [startX, setStartX] = useState(0);
  const [startWidth, setStartWidth] = useState(0);
  const [showColumnSettings, setShowColumnSettings] = useState(false);

  const headerRef = useRef<HTMLTableRowElement>(null);

  const visibleColumns = columns.filter(col => columnVisibility[col.id] !== false);

  const getSortDirection = (columnId: string): 'asc' | 'desc' | null => {
    const sort = sorts.find(s => s.column === columnId);
    return sort?.direction || null;
  };

  const getColumnFilter = (columnId: string): DataGridFilter | undefined => {
    return filters.find(f => f.column === columnId);
  };

  const handleSort = (column: DataGridColumn<T>) => {
    if (!sortable || !column.sortable) return;

    onSortChange({
      column: column.id,
      direction: getSortDirection(column.id) === 'asc' ? 'desc' : 'asc'
    });
  };

  const handleStartResize = useCallback((columnId: string, event: React.MouseEvent) => {
    if (!resizable) return;

    event.preventDefault();
    setResizingColumn(columnId);
    setStartX(event.clientX);
    setStartWidth(columnWidths[columnId] || 150);

    const handleMouseMove = (e: MouseEvent) => {
      const diff = e.clientX - startX;
      const newWidth = Math.max(50, startWidth + diff);
      onColumnWidthChange(columnId, newWidth);
    };

    const handleMouseUp = () => {
      setResizingColumn(null);
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  }, [resizable, columnWidths, startX, startWidth, onColumnWidthChange]);

  const renderSortIcon = (column: DataGridColumn<T>) => {
    if (!sortable || !column.sortable) return null;

    const direction = getSortDirection(column.id);

    return (
      <div className="inline-flex flex-col ml-1">
        <ChevronUp
          className={`w-3 h-3 ${
            direction === 'asc' ? 'text-blue-600' : 'text-gray-300'
          }`}
        />
        <ChevronDown
          className={`w-3 h-3 -mt-1 ${
            direction === 'desc' ? 'text-blue-600' : 'text-gray-300'
          }`}
        />
      </div>
    );
  };

  const renderFilterIcon = (column: DataGridColumn<T>) => {
    if (!filterable || !column.filterable) return null;

    const hasFilter = getColumnFilter(column.id);

    return (
      <Filter
        className={`w-3 h-3 ml-1 ${
          hasFilter ? 'text-blue-600' : 'text-gray-400'
        }`}
      />
    );
  };

  const ColumnSettingsPanel = () => (
    <div className="absolute top-full right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg p-4 z-50 min-w-64">
      <h3 className="text-sm font-medium text-gray-900 mb-3">Column Visibility</h3>
      <div className="space-y-2 max-h-60 overflow-y-auto">
        {columns.map(column => (
          <label key={column.id} className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={columnVisibility[column.id] !== false}
              onChange={(e) => onColumnVisibilityChange(column.id, e.target.checked)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700">{column.label}</span>
            {columnVisibility[column.id] !== false ? (
              <Eye className="w-3 h-3 text-gray-400" />
            ) : (
              <EyeOff className="w-3 h-3 text-gray-400" />
            )}
          </label>
        ))}
      </div>
    </div>
  );

  return (
    <thead className="bg-gray-50 border-b border-gray-200">
      <tr ref={headerRef} className="relative">
        {visibleColumns.map((column, index) => {
          const width = columnWidths[column.id] || column.width || 'auto';
          const isResizing = resizingColumn === column.id;

          return (
            <th
              key={column.id}
              style={{
                width: typeof width === 'number' ? `${width}px` : width,
                minWidth: column.minWidth || 50,
                maxWidth: column.maxWidth || 'none'
              }}
              className={`
                relative px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider
                ${column.sticky === 'left' ? 'sticky left-0 z-10 bg-gray-50' : ''}
                ${column.sticky === 'right' ? 'sticky right-0 z-10 bg-gray-50' : ''}
                ${sortable && column.sortable ? 'cursor-pointer hover:bg-gray-100' : ''}
                ${isResizing ? 'select-none' : ''}
              `}
              onClick={() => handleSort(column)}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <span className={`${column.align === 'center' ? 'text-center' : column.align === 'right' ? 'text-right' : 'text-left'}`}>
                    {column.label}
                  </span>
                  {renderSortIcon(column)}
                  {renderFilterIcon(column)}
                </div>

                {/* Column settings for last column */}
                {index === visibleColumns.length - 1 && hideable && (
                  <div className="relative">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setShowColumnSettings(!showColumnSettings);
                      }}
                      className="p-1 rounded hover:bg-gray-200 text-gray-400 hover:text-gray-600"
                    >
                      <Settings className="w-3 h-3" />
                    </button>
                    {showColumnSettings && <ColumnSettingsPanel />}
                  </div>
                )}
              </div>

              {/* Resize handle */}
              {resizable && index < visibleColumns.length - 1 && (
                <div
                  className={`
                    absolute top-0 right-0 w-1 h-full cursor-col-resize
                    hover:bg-blue-300 ${isResizing ? 'bg-blue-400' : ''}
                  `}
                  onMouseDown={(e) => handleStartResize(column.id, e)}
                />
              )}
            </th>
          );
        })}
      </tr>

      {/* Filter row */}
      {filterable && (
        <FilterRow
          columns={visibleColumns}
          filters={filters}
          onFilterChange={onFilterChange}
          columnWidths={columnWidths}
        />
      )}

      {/* Click outside to close column settings */}
      {showColumnSettings && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setShowColumnSettings(false)}
        />
      )}
    </thead>
  );
}

// Filter row component
interface FilterRowProps<T> {
  columns: DataGridColumn<T>[];
  filters: DataGridFilter[];
  onFilterChange: (filter: DataGridFilter) => void;
  columnWidths: Record<string, number>;
}

function FilterRow<T>({
  columns,
  filters,
  onFilterChange,
  columnWidths
}: FilterRowProps<T>) {
  const getFilterValue = (columnId: string): string => {
    const filter = filters.find(f => f.column === columnId);
    return filter?.value || '';
  };

  const handleFilterChange = (column: DataGridColumn<T>, value: string) => {
    if (!value.trim()) {
      // Remove filter if empty
      return;
    }

    onFilterChange({
      column: column.id,
      operator: column.filterType === 'number' ? 'equals' : 'contains',
      value: column.filterType === 'number' ? Number(value) : value
    });
  };

  return (
    <tr className="bg-white border-b border-gray-100">
      {columns.map(column => {
        if (!column.filterable) {
          return (
            <th
              key={`filter-${column.id}`}
              style={{
                width: columnWidths[column.id] || column.width || 'auto'
              }}
              className="px-4 py-2"
            />
          );
        }

        return (
          <th
            key={`filter-${column.id}`}
            style={{
              width: columnWidths[column.id] || column.width || 'auto'
            }}
            className="px-4 py-2"
          >
            {column.filterType === 'select' ? (
              <select
                value={getFilterValue(column.id)}
                onChange={(e) => handleFilterChange(column, e.target.value)}
                className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">All</option>
                {column.filterOptions?.map(option => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            ) : (
              <input
                type={column.filterType === 'number' ? 'number' : 'text'}
                placeholder={`Filter ${column.label.toLowerCase()}...`}
                value={getFilterValue(column.id)}
                onChange={(e) => handleFilterChange(column, e.target.value)}
                className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500"
              />
            )}
          </th>
        );
      })}
    </tr>
  );
}