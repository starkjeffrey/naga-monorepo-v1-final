/**
 * DataGrid Body Component
 * Handles row rendering with virtual scrolling support
 */

import React, { useMemo } from 'react';
import { FixedSizeList as List } from 'react-window';
import { ChevronRight, MoreHorizontal } from 'lucide-react';
import { DataGridColumn, DataGridAction } from '../types';

interface DataGridBodyProps<T> {
  data: T[];
  columns: DataGridColumn<T>[];
  keyField: keyof T;
  actions?: DataGridAction<T>[];
  selectedRows: Set<string | number>;
  columnVisibility: Record<string, boolean>;
  columnWidths: Record<string, number>;
  onRowClick?: (row: T, index: number) => void;
  onRowDoubleClick?: (row: T, index: number) => void;
  onRowSelection?: (rowId: string | number) => void;
  selectable?: boolean;
  virtualScrolling?: boolean;
  height?: number;
  rowHeight?: number;
  overscan?: number;
  striped?: boolean;
  bordered?: boolean;
  compact?: boolean;
  loading?: boolean;
  error?: string | React.ReactNode;
}

export function DataGridBody<T>({
  data,
  columns,
  keyField,
  actions = [],
  selectedRows,
  columnVisibility,
  columnWidths,
  onRowClick,
  onRowDoubleClick,
  onRowSelection,
  selectable = false,
  virtualScrolling = false,
  height = 400,
  rowHeight = 48,
  overscan = 10,
  striped = true,
  bordered = true,
  compact = false,
  loading = false,
  error
}: DataGridBodyProps<T>) {
  const visibleColumns = useMemo(
    () => columns.filter(col => columnVisibility[col.id] !== false),
    [columns, columnVisibility]
  );

  const hasActions = actions.length > 0;

  // Loading state
  if (loading) {
    return (
      <tbody>
        <tr>
          <td
            colSpan={visibleColumns.length + (selectable ? 1 : 0) + (hasActions ? 1 : 0)}
            className="px-6 py-12 text-center text-gray-500"
          >
            <div className="flex items-center justify-center space-x-2">
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
              <span>Loading...</span>
            </div>
          </td>
        </tr>
      </tbody>
    );
  }

  // Error state
  if (error) {
    return (
      <tbody>
        <tr>
          <td
            colSpan={visibleColumns.length + (selectable ? 1 : 0) + (hasActions ? 1 : 0)}
            className="px-6 py-12 text-center text-red-600"
          >
            {typeof error === 'string' ? (
              <div>
                <div className="text-lg font-medium mb-2">Error</div>
                <div className="text-sm">{error}</div>
              </div>
            ) : (
              error
            )}
          </td>
        </tr>
      </tbody>
    );
  }

  // Empty state
  if (data.length === 0) {
    return (
      <tbody>
        <tr>
          <td
            colSpan={visibleColumns.length + (selectable ? 1 : 0) + (hasActions ? 1 : 0)}
            className="px-6 py-12 text-center text-gray-500"
          >
            <div>
              <div className="text-lg font-medium mb-2">No data found</div>
              <div className="text-sm">Try adjusting your search or filter criteria</div>
            </div>
          </td>
        </tr>
      </tbody>
    );
  }

  // Row component for virtual scrolling
  const VirtualRow = ({ index, style }: { index: number; style: React.CSSProperties }) => {
    const row = data[index];
    const rowId = row[keyField] as string | number;
    const isSelected = selectedRows.has(rowId);

    return (
      <div style={style}>
        <DataGridRow
          row={row}
          index={index}
          columns={visibleColumns}
          keyField={keyField}
          actions={actions}
          isSelected={isSelected}
          columnWidths={columnWidths}
          onRowClick={onRowClick}
          onRowDoubleClick={onRowDoubleClick}
          onRowSelection={onRowSelection}
          selectable={selectable}
          striped={striped}
          bordered={bordered}
          compact={compact}
        />
      </div>
    );
  };

  // Virtual scrolling
  if (virtualScrolling && data.length > 100) {
    return (
      <div style={{ height }}>
        <List
          height={height}
          itemCount={data.length}
          itemSize={rowHeight}
          overscanCount={overscan}
        >
          {VirtualRow}
        </List>
      </div>
    );
  }

  // Regular rendering
  return (
    <tbody className={`bg-white ${bordered ? 'divide-y divide-gray-200' : ''}`}>
      {data.map((row, index) => {
        const rowId = row[keyField] as string | number;
        const isSelected = selectedRows.has(rowId);

        return (
          <DataGridRow
            key={rowId}
            row={row}
            index={index}
            columns={visibleColumns}
            keyField={keyField}
            actions={actions}
            isSelected={isSelected}
            columnWidths={columnWidths}
            onRowClick={onRowClick}
            onRowDoubleClick={onRowDoubleClick}
            onRowSelection={onRowSelection}
            selectable={selectable}
            striped={striped}
            bordered={bordered}
            compact={compact}
          />
        );
      })}
    </tbody>
  );
}

// Individual row component
interface DataGridRowProps<T> {
  row: T;
  index: number;
  columns: DataGridColumn<T>[];
  keyField: keyof T;
  actions: DataGridAction<T>[];
  isSelected: boolean;
  columnWidths: Record<string, number>;
  onRowClick?: (row: T, index: number) => void;
  onRowDoubleClick?: (row: T, index: number) => void;
  onRowSelection?: (rowId: string | number) => void;
  selectable: boolean;
  striped: boolean;
  bordered: boolean;
  compact: boolean;
}

function DataGridRow<T>({
  row,
  index,
  columns,
  keyField,
  actions,
  isSelected,
  columnWidths,
  onRowClick,
  onRowDoubleClick,
  onRowSelection,
  selectable,
  striped,
  bordered,
  compact
}: DataGridRowProps<T>) {
  const rowId = row[keyField] as string | number;
  const hasActions = actions.length > 0;

  const handleRowClick = (e: React.MouseEvent) => {
    // Don't trigger row click if clicking on checkbox or action buttons
    if (
      (e.target as HTMLElement).closest('input[type="checkbox"]') ||
      (e.target as HTMLElement).closest('.action-menu')
    ) {
      return;
    }

    onRowClick?.(row, index);
  };

  const handleRowDoubleClick = () => {
    onRowDoubleClick?.(row, index);
  };

  const handleCheckboxChange = () => {
    onRowSelection?.(rowId);
  };

  const getCellValue = (column: DataGridColumn<T>) => {
    if (typeof column.accessor === 'function') {
      return column.accessor(row);
    }
    return row[column.accessor];
  };

  const renderCellContent = (column: DataGridColumn<T>, value: any) => {
    if (column.format) {
      return column.format(value, row);
    }

    // Default formatting based on type
    if (value === null || value === undefined) {
      return <span className="text-gray-400">—</span>;
    }

    if (typeof value === 'boolean') {
      return (
        <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
          value
            ? 'bg-green-100 text-green-800'
            : 'bg-red-100 text-red-800'
        }`}>
          {value ? 'Yes' : 'No'}
        </span>
      );
    }

    if (value instanceof Date) {
      return value.toLocaleDateString();
    }

    return String(value);
  };

  const rowClasses = `
    ${striped && index % 2 === 0 ? 'bg-gray-50' : 'bg-white'}
    ${isSelected ? 'bg-blue-50 border-blue-200' : ''}
    ${onRowClick ? 'cursor-pointer hover:bg-gray-100' : ''}
    ${compact ? 'text-sm' : ''}
    transition-colors duration-150
  `;

  return (
    <tr
      className={rowClasses}
      onClick={handleRowClick}
      onDoubleClick={handleRowDoubleClick}
    >
      {/* Selection checkbox */}
      {selectable && (
        <td className={`${compact ? 'px-2 py-2' : 'px-4 py-3'} w-4`}>
          <input
            type="checkbox"
            checked={isSelected}
            onChange={handleCheckboxChange}
            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
        </td>
      )}

      {/* Data columns */}
      {columns.map(column => {
        const value = getCellValue(column);
        const width = columnWidths[column.id] || column.width || 'auto';

        return (
          <td
            key={column.id}
            style={{
              width: typeof width === 'number' ? `${width}px` : width,
              minWidth: column.minWidth || 'auto',
              maxWidth: column.maxWidth || 'none'
            }}
            className={`
              ${compact ? 'px-2 py-2' : 'px-4 py-3'}
              ${column.align === 'center' ? 'text-center' : ''}
              ${column.align === 'right' ? 'text-right' : ''}
              ${column.sticky === 'left' ? 'sticky left-0 z-10 bg-inherit' : ''}
              ${column.sticky === 'right' ? 'sticky right-0 z-10 bg-inherit' : ''}
              text-sm text-gray-900
            `}
          >
            {renderCellContent(column, value)}
          </td>
        );
      })}

      {/* Actions */}
      {hasActions && (
        <td className={`${compact ? 'px-2 py-2' : 'px-4 py-3'} w-4 relative`}>
          <RowActionsMenu row={row} actions={actions} />
        </td>
      )}
    </tr>
  );
}

// Row actions menu component
interface RowActionsMenuProps<T> {
  row: T;
  actions: DataGridAction<T>[];
}

function RowActionsMenu<T>({ row, actions }: RowActionsMenuProps<T>) {
  const [isOpen, setIsOpen] = React.useState(false);

  const visibleActions = actions.filter(action => !action.showInMenu);
  const menuActions = actions.filter(action => action.showInMenu);

  const executeAction = (action: DataGridAction<T>) => {
    if (action.requiresConfirmation) {
      const confirmed = window.confirm(
        action.confirmationMessage || `Are you sure you want to ${action.label.toLowerCase()}?`
      );
      if (!confirmed) return;
    }

    action.onClick(row);
    setIsOpen(false);
  };

  return (
    <div className="action-menu flex items-center justify-end space-x-1">
      {/* Visible actions */}
      {visibleActions.map(action => (
        <button
          key={action.id}
          onClick={() => executeAction(action)}
          disabled={action.disabled?.(row)}
          className={`
            p-1 rounded text-gray-400 hover:text-gray-600
            disabled:opacity-50 disabled:cursor-not-allowed
            ${action.variant === 'danger' ? 'hover:text-red-600' : ''}
            ${action.variant === 'primary' ? 'hover:text-blue-600' : ''}
          `}
          title={action.label}
        >
          {action.icon || <ChevronRight className="w-4 h-4" />}
        </button>
      ))}

      {/* Menu for additional actions */}
      {menuActions.length > 0 && (
        <div className="relative">
          <button
            onClick={() => setIsOpen(!isOpen)}
            className="p-1 rounded text-gray-400 hover:text-gray-600"
          >
            <MoreHorizontal className="w-4 h-4" />
          </button>

          {isOpen && (
            <>
              <div
                className="fixed inset-0 z-40"
                onClick={() => setIsOpen(false)}
              />
              <div className="absolute right-0 top-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg py-1 z-50 min-w-32">
                {menuActions.map(action => (
                  <button
                    key={action.id}
                    onClick={() => executeAction(action)}
                    disabled={action.disabled?.(row)}
                    className={`
                      w-full px-3 py-2 text-left text-sm hover:bg-gray-100
                      disabled:opacity-50 disabled:cursor-not-allowed
                      ${action.variant === 'danger' ? 'text-red-700 hover:bg-red-50' : 'text-gray-700'}
                      flex items-center
                    `}
                  >
                    {action.icon && <span className="mr-2">{action.icon}</span>}
                    {action.label}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}