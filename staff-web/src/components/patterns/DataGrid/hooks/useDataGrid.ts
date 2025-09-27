/**
 * Enhanced DataGrid Hook
 * Manages all DataGrid state and operations
 */

import { useCallback, useMemo, useReducer, useEffect, useRef } from 'react';
import { debounce } from 'lodash';
import {
  DataGridState,
  DataGridFilter,
  DataGridSort,
  DataGridPagination,
  UseDataGridReturn
} from '../types';

// Action types for reducer
type DataGridAction<T> =
  | { type: 'SET_DATA'; payload: T[] }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | undefined }
  | { type: 'TOGGLE_ROW_SELECTION'; payload: string | number }
  | { type: 'SELECT_ALL' }
  | { type: 'CLEAR_SELECTION' }
  | { type: 'ADD_FILTER'; payload: DataGridFilter }
  | { type: 'REMOVE_FILTER'; payload: string }
  | { type: 'CLEAR_FILTERS' }
  | { type: 'SET_SORT'; payload: DataGridSort }
  | { type: 'CLEAR_SORT' }
  | { type: 'SET_SEARCH'; payload: string }
  | { type: 'SET_PAGINATION'; payload: Partial<DataGridPagination> }
  | { type: 'SET_COLUMN_VISIBILITY'; payload: { columnId: string; visible: boolean } }
  | { type: 'SET_COLUMN_ORDER'; payload: string[] }
  | { type: 'SET_COLUMN_WIDTH'; payload: { columnId: string; width: number } }
  | { type: 'RESET' };

// Initial state factory
function createInitialState<T>(keyField: keyof T): DataGridState<T> {
  return {
    data: [],
    loading: false,
    error: undefined,
    selectedRows: new Set(),
    filters: [],
    sorts: [],
    pagination: {
      page: 1,
      pageSize: 25,
      total: 0,
      pageSizeOptions: [10, 25, 50, 100, 200]
    },
    searchQuery: '',
    columnVisibility: {},
    columnOrder: [],
    columnWidths: {}
  };
}

// Reducer function
function dataGridReducer<T>(
  state: DataGridState<T>,
  action: DataGridAction<T>
): DataGridState<T> {
  switch (action.type) {
    case 'SET_DATA':
      return {
        ...state,
        data: action.payload,
        pagination: {
          ...state.pagination,
          total: action.payload.length
        }
      };

    case 'SET_LOADING':
      return {
        ...state,
        loading: action.payload
      };

    case 'SET_ERROR':
      return {
        ...state,
        error: action.payload,
        loading: false
      };

    case 'TOGGLE_ROW_SELECTION': {
      const newSelection = new Set(state.selectedRows);
      if (newSelection.has(action.payload)) {
        newSelection.delete(action.payload);
      } else {
        newSelection.add(action.payload);
      }
      return {
        ...state,
        selectedRows: newSelection
      };
    }

    case 'SELECT_ALL': {
      const allIds = state.data.map((_, index) => index);
      return {
        ...state,
        selectedRows: new Set(allIds)
      };
    }

    case 'CLEAR_SELECTION':
      return {
        ...state,
        selectedRows: new Set()
      };

    case 'ADD_FILTER': {
      const existingFilterIndex = state.filters.findIndex(
        f => f.column === action.payload.column
      );

      let newFilters: DataGridFilter[];
      if (existingFilterIndex >= 0) {
        // Replace existing filter for this column
        newFilters = [...state.filters];
        newFilters[existingFilterIndex] = action.payload;
      } else {
        // Add new filter
        newFilters = [...state.filters, action.payload];
      }

      return {
        ...state,
        filters: newFilters,
        pagination: {
          ...state.pagination,
          page: 1 // Reset to first page when filtering
        }
      };
    }

    case 'REMOVE_FILTER':
      return {
        ...state,
        filters: state.filters.filter(f => f.column !== action.payload),
        pagination: {
          ...state.pagination,
          page: 1
        }
      };

    case 'CLEAR_FILTERS':
      return {
        ...state,
        filters: [],
        searchQuery: '',
        pagination: {
          ...state.pagination,
          page: 1
        }
      };

    case 'SET_SORT': {
      // Toggle sort direction if same column, otherwise set new sort
      const existingSort = state.sorts.find(s => s.column === action.payload.column);
      let newSorts: DataGridSort[];

      if (existingSort) {
        if (existingSort.direction === 'asc') {
          newSorts = state.sorts.map(s =>
            s.column === action.payload.column
              ? { ...s, direction: 'desc' as const }
              : s
          );
        } else {
          // Remove sort if clicking desc again
          newSorts = state.sorts.filter(s => s.column !== action.payload.column);
        }
      } else {
        // Add new sort (supports multi-column sorting)
        newSorts = [...state.sorts, action.payload];
      }

      return {
        ...state,
        sorts: newSorts
      };
    }

    case 'CLEAR_SORT':
      return {
        ...state,
        sorts: []
      };

    case 'SET_SEARCH':
      return {
        ...state,
        searchQuery: action.payload,
        pagination: {
          ...state.pagination,
          page: 1
        }
      };

    case 'SET_PAGINATION':
      return {
        ...state,
        pagination: {
          ...state.pagination,
          ...action.payload
        }
      };

    case 'SET_COLUMN_VISIBILITY':
      return {
        ...state,
        columnVisibility: {
          ...state.columnVisibility,
          [action.payload.columnId]: action.payload.visible
        }
      };

    case 'SET_COLUMN_ORDER':
      return {
        ...state,
        columnOrder: action.payload
      };

    case 'SET_COLUMN_WIDTH':
      return {
        ...state,
        columnWidths: {
          ...state.columnWidths,
          [action.payload.columnId]: action.payload.width
        }
      };

    case 'RESET':
      return createInitialState(state.data[0] ? Object.keys(state.data[0])[0] as keyof T : 'id' as keyof T);

    default:
      return state;
  }
}

// Utility functions for filtering and sorting
function applyFilters<T>(data: T[], filters: DataGridFilter[], searchQuery: string): T[] {
  let filtered = [...data];

  // Apply column filters
  filters.forEach(filter => {
    filtered = filtered.filter(row => {
      const value = row[filter.column as keyof T];

      switch (filter.operator) {
        case 'equals':
          return value === filter.value;
        case 'contains':
          return String(value).toLowerCase().includes(String(filter.value).toLowerCase());
        case 'startsWith':
          return String(value).toLowerCase().startsWith(String(filter.value).toLowerCase());
        case 'endsWith':
          return String(value).toLowerCase().endsWith(String(filter.value).toLowerCase());
        case 'gt':
          return Number(value) > Number(filter.value);
        case 'lt':
          return Number(value) < Number(filter.value);
        case 'gte':
          return Number(value) >= Number(filter.value);
        case 'lte':
          return Number(value) <= Number(filter.value);
        case 'in':
          return Array.isArray(filter.value) && filter.value.includes(value);
        case 'between':
          return Array.isArray(filter.value) &&
                 Number(value) >= Number(filter.value[0]) &&
                 Number(value) <= Number(filter.value[1]);
        default:
          return true;
      }
    });
  });

  // Apply search query (searches all string fields)
  if (searchQuery.trim()) {
    const query = searchQuery.toLowerCase();
    filtered = filtered.filter(row =>
      Object.values(row as any).some(value =>
        String(value).toLowerCase().includes(query)
      )
    );
  }

  return filtered;
}

function applySorts<T>(data: T[], sorts: DataGridSort[]): T[] {
  if (sorts.length === 0) return data;

  return [...data].sort((a, b) => {
    for (const sort of sorts) {
      const aValue = a[sort.column as keyof T];
      const bValue = b[sort.column as keyof T];

      let comparison = 0;

      if (aValue < bValue) comparison = -1;
      else if (aValue > bValue) comparison = 1;

      if (comparison !== 0) {
        return sort.direction === 'asc' ? comparison : -comparison;
      }
    }
    return 0;
  });
}

function applyPagination<T>(data: T[], pagination: DataGridPagination): T[] {
  const { page, pageSize } = pagination;
  const startIndex = (page - 1) * pageSize;
  const endIndex = startIndex + pageSize;
  return data.slice(startIndex, endIndex);
}

export function useDataGrid<T>(
  initialData: T[] = [],
  keyField: keyof T,
  options: {
    debounceMs?: number;
    persistState?: boolean;
    storageKey?: string;
  } = {}
): UseDataGridReturn<T> {
  const { debounceMs = 300, persistState = false, storageKey } = options;

  const [state, dispatch] = useReducer(
    dataGridReducer<T>,
    createInitialState<T>(keyField)
  );

  // Initialize with data
  useEffect(() => {
    if (initialData.length > 0) {
      dispatch({ type: 'SET_DATA', payload: initialData });
    }
  }, [initialData]);

  // Debounced search
  const debouncedSetSearch = useRef(
    debounce((query: string) => {
      dispatch({ type: 'SET_SEARCH', payload: query });
    }, debounceMs)
  ).current;

  // Persist state to localStorage
  useEffect(() => {
    if (persistState && storageKey) {
      const stateToSave = {
        filters: state.filters,
        sorts: state.sorts,
        pagination: state.pagination,
        columnVisibility: state.columnVisibility,
        columnOrder: state.columnOrder,
        columnWidths: state.columnWidths
      };
      localStorage.setItem(storageKey, JSON.stringify(stateToSave));
    }
  }, [state, persistState, storageKey]);

  // Load persisted state
  useEffect(() => {
    if (persistState && storageKey) {
      try {
        const saved = localStorage.getItem(storageKey);
        if (saved) {
          const parsed = JSON.parse(saved);
          // Apply saved state (implementation would dispatch multiple actions)
        }
      } catch (error) {
        console.warn('Failed to load persisted DataGrid state:', error);
      }
    }
  }, [persistState, storageKey]);

  // Actions
  const actions = useMemo(() => ({
    setData: (data: T[]) => dispatch({ type: 'SET_DATA', payload: data }),
    setLoading: (loading: boolean) => dispatch({ type: 'SET_LOADING', payload: loading }),
    setError: (error: string | undefined) => dispatch({ type: 'SET_ERROR', payload: error }),
    toggleRowSelection: (rowId: string | number) =>
      dispatch({ type: 'TOGGLE_ROW_SELECTION', payload: rowId }),
    selectAll: () => dispatch({ type: 'SELECT_ALL' }),
    clearSelection: () => dispatch({ type: 'CLEAR_SELECTION' }),
    addFilter: (filter: DataGridFilter) => dispatch({ type: 'ADD_FILTER', payload: filter }),
    removeFilter: (columnId: string) => dispatch({ type: 'REMOVE_FILTER', payload: columnId }),
    clearFilters: () => dispatch({ type: 'CLEAR_FILTERS' }),
    setSort: (sort: DataGridSort) => dispatch({ type: 'SET_SORT', payload: sort }),
    clearSort: () => dispatch({ type: 'CLEAR_SORT' }),
    setSearch: useCallback((query: string) => debouncedSetSearch(query), [debouncedSetSearch]),
    setPagination: (pagination: Partial<DataGridPagination>) =>
      dispatch({ type: 'SET_PAGINATION', payload: pagination }),
    setColumnVisibility: (columnId: string, visible: boolean) =>
      dispatch({ type: 'SET_COLUMN_VISIBILITY', payload: { columnId, visible } }),
    setColumnOrder: (order: string[]) => dispatch({ type: 'SET_COLUMN_ORDER', payload: order }),
    setColumnWidth: (columnId: string, width: number) =>
      dispatch({ type: 'SET_COLUMN_WIDTH', payload: { columnId, width } }),
    reset: () => dispatch({ type: 'RESET' })
  }), [debouncedSetSearch]);

  // Computed values
  const computed = useMemo(() => {
    const filteredData = applyFilters(state.data, state.filters, state.searchQuery);
    const sortedData = applySorts(filteredData, state.sorts);
    const paginatedData = applyPagination(sortedData, state.pagination);

    // Update total in pagination
    const updatedPagination: DataGridPagination = {
      ...state.pagination,
      total: filteredData.length
    };

    const selectedRowsData = state.data.filter((_, index) =>
      state.selectedRows.has(index)
    );

    return {
      filteredData,
      sortedData,
      paginatedData,
      selectedRowsData,
      hasSelection: state.selectedRows.size > 0,
      hasFilters: state.filters.length > 0 || state.searchQuery.length > 0,
      canExport: filteredData.length > 0,
      updatedPagination
    };
  }, [state]);

  return {
    state: {
      ...state,
      pagination: computed.updatedPagination
    },
    actions,
    computed
  };
}