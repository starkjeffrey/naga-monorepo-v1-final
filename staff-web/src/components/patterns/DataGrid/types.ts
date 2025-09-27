/**
 * Enhanced DataGrid Types
 * Complete type definitions for the universal CRUD DataGrid pattern
 */

export interface DataGridColumn<T = any> {
  id: string;
  label: string;
  accessor: keyof T | ((row: T) => any);
  sortable?: boolean;
  filterable?: boolean;
  width?: number | string;
  minWidth?: number;
  maxWidth?: number;
  align?: 'left' | 'center' | 'right';
  format?: (value: any, row: T) => React.ReactNode;
  filterType?: 'text' | 'select' | 'date' | 'number' | 'boolean';
  filterOptions?: Array<{ label: string; value: any }>;
  sticky?: 'left' | 'right' | false;
  hidden?: boolean;
  resizable?: boolean;
}

export interface DataGridAction<T = any> {
  id: string;
  label: string;
  icon?: React.ReactNode;
  onClick: (row: T) => void;
  disabled?: (row: T) => boolean;
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  showInMenu?: boolean;
  requiresConfirmation?: boolean;
  confirmationMessage?: string;
}

export interface DataGridBulkAction<T = any> {
  id: string;
  label: string;
  icon?: React.ReactNode;
  onClick: (selectedRows: T[]) => void;
  disabled?: (selectedRows: T[]) => boolean;
  variant?: 'primary' | 'secondary' | 'danger';
  requiresConfirmation?: boolean;
  confirmationMessage?: string;
}

export interface DataGridFilter {
  column: string;
  operator: 'equals' | 'contains' | 'startsWith' | 'endsWith' | 'gt' | 'lt' | 'gte' | 'lte' | 'in' | 'between';
  value: any;
  label?: string;
}

export interface DataGridSort {
  column: string;
  direction: 'asc' | 'desc';
}

export interface DataGridPagination {
  page: number;
  pageSize: number;
  total: number;
  pageSizeOptions?: number[];
}

export interface SavedFilterPreset {
  id: string;
  name: string;
  filters: DataGridFilter[];
  sorts: DataGridSort[];
  isDefault?: boolean;
  isShared?: boolean;
  createdBy?: string;
  createdAt?: Date;
}

export interface DataGridExportOptions {
  format: 'csv' | 'excel' | 'pdf';
  filename?: string;
  selectedOnly?: boolean;
  includeHeaders?: boolean;
  customColumns?: string[];
}

export interface DataGridState<T = any> {
  data: T[];
  loading: boolean;
  error?: string;
  selectedRows: Set<string | number>;
  filters: DataGridFilter[];
  sorts: DataGridSort[];
  pagination: DataGridPagination;
  searchQuery: string;
  columnVisibility: Record<string, boolean>;
  columnOrder: string[];
  columnWidths: Record<string, number>;
}

export interface DataGridProps<T = any> {
  // Data
  data: T[];
  columns: DataGridColumn<T>[];
  keyField: keyof T;

  // Loading states
  loading?: boolean;
  error?: string | React.ReactNode;

  // Actions
  actions?: DataGridAction<T>[];
  bulkActions?: DataGridBulkAction<T>[];

  // Selection
  selectable?: boolean;
  selectedRows?: Set<string | number>;
  onSelectionChange?: (selectedRows: Set<string | number>) => void;

  // Sorting
  sortable?: boolean;
  sorts?: DataGridSort[];
  onSortChange?: (sorts: DataGridSort[]) => void;

  // Filtering
  filterable?: boolean;
  filters?: DataGridFilter[];
  onFilterChange?: (filters: DataGridFilter[]) => void;
  searchable?: boolean;
  searchQuery?: string;
  onSearchChange?: (query: string) => void;

  // Pagination
  pagination?: DataGridPagination;
  onPaginationChange?: (pagination: Partial<DataGridPagination>) => void;

  // Export
  exportable?: boolean;
  onExport?: (options: DataGridExportOptions) => void;

  // Import
  importable?: boolean;
  onImport?: (file: File) => void;
  importTemplate?: () => void;

  // Column management
  columnResizable?: boolean;
  columnReorderable?: boolean;
  columnHideable?: boolean;
  onColumnVisibilityChange?: (visibility: Record<string, boolean>) => void;
  onColumnOrderChange?: (order: string[]) => void;
  onColumnWidthChange?: (widths: Record<string, number>) => void;

  // Saved presets
  savedPresets?: SavedFilterPreset[];
  onPresetSave?: (preset: Omit<SavedFilterPreset, 'id' | 'createdAt'>) => void;
  onPresetLoad?: (preset: SavedFilterPreset) => void;
  onPresetDelete?: (presetId: string) => void;

  // Virtual scrolling
  virtualScrolling?: boolean;
  rowHeight?: number;
  overscan?: number;

  // Styling
  height?: number | string;
  maxHeight?: number | string;
  striped?: boolean;
  bordered?: boolean;
  compact?: boolean;
  className?: string;

  // Performance
  memoizeRows?: boolean;
  debounceMs?: number;

  // Accessibility
  ariaLabel?: string;
  ariaDescribedBy?: string;

  // Events
  onRowClick?: (row: T, index: number) => void;
  onRowDoubleClick?: (row: T, index: number) => void;
  onRowHover?: (row: T, index: number) => void;
}

export interface DataGridRef<T = any> {
  refresh: () => void;
  clearSelection: () => void;
  selectAll: () => void;
  exportData: (options: DataGridExportOptions) => void;
  applyFilter: (filter: DataGridFilter) => void;
  clearFilters: () => void;
  resetToDefaults: () => void;
  getState: () => DataGridState<T>;
  setState: (state: Partial<DataGridState<T>>) => void;
}

// Hook return types
export interface UseDataGridReturn<T = any> {
  state: DataGridState<T>;
  actions: {
    setData: (data: T[]) => void;
    setLoading: (loading: boolean) => void;
    setError: (error: string | undefined) => void;
    toggleRowSelection: (rowId: string | number) => void;
    selectAll: () => void;
    clearSelection: () => void;
    addFilter: (filter: DataGridFilter) => void;
    removeFilter: (columnId: string) => void;
    clearFilters: () => void;
    setSort: (sort: DataGridSort) => void;
    clearSort: () => void;
    setSearch: (query: string) => void;
    setPagination: (pagination: Partial<DataGridPagination>) => void;
    setColumnVisibility: (columnId: string, visible: boolean) => void;
    setColumnOrder: (order: string[]) => void;
    setColumnWidth: (columnId: string, width: number) => void;
    reset: () => void;
  };
  computed: {
    filteredData: T[];
    sortedData: T[];
    paginatedData: T[];
    selectedRowsData: T[];
    hasSelection: boolean;
    hasFilters: boolean;
    canExport: boolean;
  };
}

// Component event types
export interface DataGridRowClickEvent<T = any> {
  row: T;
  index: number;
  originalEvent: React.MouseEvent;
}

export interface DataGridCellClickEvent<T = any> {
  row: T;
  column: DataGridColumn<T>;
  value: any;
  rowIndex: number;
  columnIndex: number;
  originalEvent: React.MouseEvent;
}

export interface DataGridHeaderClickEvent<T = any> {
  column: DataGridColumn<T>;
  originalEvent: React.MouseEvent;
}