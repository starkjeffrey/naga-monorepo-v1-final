/**
 * Enhanced DataGrid Component
 * Complete universal CRUD DataGrid with all features
 */

import React, { forwardRef, useImperativeHandle, useMemo } from 'react';
import { DataGridProps, DataGridRef } from './types';
import { useDataGrid } from './hooks/useDataGrid';
import { DataGridToolbar } from './components/DataGridToolbar';
import { DataGridHeader } from './components/DataGridHeader';
import { DataGridBody } from './components/DataGridBody';
import { DataGridPagination } from './components/DataGridPagination';

export const DataGrid = forwardRef<DataGridRef, DataGridProps>(function DataGrid(
  {
    // Data
    data,
    columns,
    keyField,

    // Loading states
    loading = false,
    error,

    // Actions
    actions = [],
    bulkActions = [],

    // Selection
    selectable = false,
    selectedRows: externalSelectedRows,
    onSelectionChange,

    // Sorting
    sortable = true,
    sorts: externalSorts,
    onSortChange,

    // Filtering
    filterable = true,
    filters: externalFilters,
    onFilterChange,
    searchable = true,
    searchQuery: externalSearchQuery,
    onSearchChange,

    // Pagination
    pagination: externalPagination,
    onPaginationChange,

    // Export/Import
    exportable = true,
    onExport,
    importable = false,
    onImport,

    // Column management
    columnResizable = true,
    columnReorderable = false,
    columnHideable = true,
    onColumnVisibilityChange,
    onColumnOrderChange,
    onColumnWidthChange,

    // Saved presets
    savedPresets = [],
    onPresetSave,
    onPresetLoad,
    onPresetDelete,

    // Virtual scrolling
    virtualScrolling = false,
    rowHeight = 48,
    overscan = 10,

    // Styling
    height = 'auto',
    maxHeight,
    striped = true,
    bordered = true,
    compact = false,
    className = '',

    // Performance
    memoizeRows = true,
    debounceMs = 300,

    // Accessibility
    ariaLabel = 'Data grid',
    ariaDescribedBy,

    // Events
    onRowClick,
    onRowDoubleClick,
    onRowHover
  },
  ref
) {
  // Use internal state management hook
  const {
    state,
    actions: dataGridActions,
    computed
  } = useDataGrid(data, keyField, {
    debounceMs,
    persistState: true,
    storageKey: `datagrid-${keyField.toString()}`
  });

  // Use external state if provided, otherwise use internal state
  const selectedRows = externalSelectedRows ?? state.selectedRows;
  const sorts = externalSorts ?? state.sorts;
  const filters = externalFilters ?? state.filters;
  const searchQuery = externalSearchQuery ?? state.searchQuery;
  const pagination = externalPagination ?? state.pagination;

  // Column visibility setup
  const columnVisibility = useMemo(() => {
    const visibility: Record<string, boolean> = {};
    columns.forEach(col => {
      visibility[col.id] = !col.hidden && (state.columnVisibility[col.id] ?? true);
    });
    return visibility;
  }, [columns, state.columnVisibility]);

  // Handlers that use external callbacks or internal actions
  const handleSelectionChange = (newSelection: Set<string | number>) => {
    if (onSelectionChange) {
      onSelectionChange(newSelection);
    } else {
      // Use internal state
      const diff = Array.from(newSelection).filter(id => !selectedRows.has(id));
      diff.forEach(id => dataGridActions.toggleRowSelection(id));
    }
  };

  const handleSortChange = (sort: any) => {
    if (onSortChange) {
      onSortChange([sort]);
    } else {
      dataGridActions.setSort(sort);
    }
  };

  const handleFilterChange = (filter: any) => {
    if (onFilterChange) {
      const newFilters = filters.filter(f => f.column !== filter.column);
      newFilters.push(filter);
      onFilterChange(newFilters);
    } else {
      dataGridActions.addFilter(filter);
    }
  };

  const handleSearchChange = (query: string) => {
    if (onSearchChange) {
      onSearchChange(query);
    } else {
      dataGridActions.setSearch(query);
    }
  };

  const handlePaginationChange = (newPagination: any) => {
    if (onPaginationChange) {
      onPaginationChange(newPagination);
    } else {
      dataGridActions.setPagination(newPagination);
    }
  };

  const handleColumnVisibilityChange = (columnId: string, visible: boolean) => {
    if (onColumnVisibilityChange) {
      onColumnVisibilityChange({ ...columnVisibility, [columnId]: visible });
    } else {
      dataGridActions.setColumnVisibility(columnId, visible);
    }
  };

  const handleColumnOrderChange = (order: string[]) => {
    if (onColumnOrderChange) {
      onColumnOrderChange(order);
    } else {
      dataGridActions.setColumnOrder(order);
    }
  };

  const handleColumnWidthChange = (columnId: string, width: number) => {
    if (onColumnWidthChange) {
      onColumnWidthChange({ ...state.columnWidths, [columnId]: width });
    } else {
      dataGridActions.setColumnWidth(columnId, width);
    }
  };

  // Expose imperative API
  useImperativeHandle(ref, () => ({
    refresh: () => {
      // Trigger a refresh - could call external onRefresh or reset state
      dataGridActions.reset();
    },
    clearSelection: () => {
      dataGridActions.clearSelection();
    },
    selectAll: () => {
      dataGridActions.selectAll();
    },
    exportData: (options) => {
      if (onExport) {
        onExport(options);
      }
    },
    applyFilter: (filter) => {
      dataGridActions.addFilter(filter);
    },
    clearFilters: () => {
      dataGridActions.clearFilters();
    },
    resetToDefaults: () => {
      dataGridActions.reset();
    },
    getState: () => state,
    setState: (newState) => {
      // Apply partial state updates
      Object.entries(newState).forEach(([key, value]) => {
        // Would need to implement setState actions
      });
    }
  }), [state, dataGridActions, onExport]);

  // Use computed data from hook
  const displayData = computed.paginatedData;
  const selectedRowsData = computed.selectedRowsData;

  const containerStyle: React.CSSProperties = {
    height: typeof height === 'number' ? `${height}px` : height,
    maxHeight: typeof maxHeight === 'number' ? `${maxHeight}px` : maxHeight,
  };

  return (
    <div
      className={`bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden ${className}`}
      style={containerStyle}
      role="grid"
      aria-label={ariaLabel}
      aria-describedby={ariaDescribedBy}
    >
      {/* Toolbar */}
      <DataGridToolbar
        searchable={searchable}
        searchQuery={searchQuery}
        onSearchChange={handleSearchChange}
        selectedCount={selectedRows.size}
        totalCount={computed.filteredData.length}
        bulkActions={bulkActions}
        selectedRows={selectedRowsData}
        onClearSelection={dataGridActions.clearSelection}
        onSelectAll={dataGridActions.selectAll}
        exportable={exportable}
        importable={importable}
        onExport={onExport}
        onImport={onImport}
        savedPresets={savedPresets}
        currentFilters={filters}
        onPresetSave={onPresetSave}
        onPresetLoad={onPresetLoad}
        onPresetDelete={onPresetDelete}
        loading={loading}
      />

      {/* Table */}
      <div className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            {/* Header */}
            <DataGridHeader
              columns={columns}
              sorts={sorts}
              filters={filters}
              columnVisibility={columnVisibility}
              columnWidths={state.columnWidths}
              onSortChange={handleSortChange}
              onFilterChange={handleFilterChange}
              onColumnVisibilityChange={handleColumnVisibilityChange}
              onColumnWidthChange={handleColumnWidthChange}
              sortable={sortable}
              filterable={filterable}
              resizable={columnResizable}
              hideable={columnHideable}
            />

            {/* Body */}
            <DataGridBody
              data={displayData}
              columns={columns}
              keyField={keyField}
              actions={actions}
              selectedRows={selectedRows}
              columnVisibility={columnVisibility}
              columnWidths={state.columnWidths}
              onRowClick={onRowClick}
              onRowDoubleClick={onRowDoubleClick}
              onRowSelection={(rowId) => {
                if (selectable) {
                  dataGridActions.toggleRowSelection(rowId);
                }
              }}
              selectable={selectable}
              virtualScrolling={virtualScrolling}
              height={typeof height === 'number' ? height - 200 : 400} // Account for header/footer
              rowHeight={rowHeight}
              overscan={overscan}
              striped={striped}
              bordered={bordered}
              compact={compact}
              loading={loading}
              error={error}
            />
          </table>
        </div>
      </div>

      {/* Pagination */}
      {pagination && pagination.total > 0 && (
        <DataGridPagination
          pagination={pagination}
          onPaginationChange={handlePaginationChange}
          compact={compact}
        />
      )}
    </div>
  );
});

DataGrid.displayName = 'DataGrid';

export default DataGrid;