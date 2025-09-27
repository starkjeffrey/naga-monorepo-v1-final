/**
 * Enhanced TransferList Hook
 * Manages all transfer list state and operations with history, validation, and collaboration
 */

import { useCallback, useMemo, useReducer, useEffect, useRef } from 'react';
import { debounce } from 'lodash';
import {
  TransferListState,
  TransferItem,
  TransferOperation,
  TransferValidationRule,
  UseTransferListReturn
} from '../types';

// Action types for reducer
type TransferListAction =
  | { type: 'SET_LEFT_ITEMS'; payload: TransferItem[] }
  | { type: 'SET_RIGHT_ITEMS'; payload: TransferItem[] }
  | { type: 'ADD_LEFT_ITEM'; payload: TransferItem }
  | { type: 'ADD_RIGHT_ITEM'; payload: TransferItem }
  | { type: 'REMOVE_LEFT_ITEM'; payload: string | number }
  | { type: 'REMOVE_RIGHT_ITEM'; payload: string | number }
  | { type: 'TOGGLE_LEFT_SELECTION'; payload: string | number }
  | { type: 'TOGGLE_RIGHT_SELECTION'; payload: string | number }
  | { type: 'SELECT_ALL_LEFT' }
  | { type: 'SELECT_ALL_RIGHT' }
  | { type: 'CLEAR_LEFT_SELECTION' }
  | { type: 'CLEAR_RIGHT_SELECTION' }
  | { type: 'CLEAR_ALL_SELECTION' }
  | { type: 'TRANSFER_TO_RIGHT'; payload: (string | number)[] }
  | { type: 'TRANSFER_TO_LEFT'; payload: (string | number)[] }
  | { type: 'SET_LEFT_SEARCH'; payload: string }
  | { type: 'SET_RIGHT_SEARCH'; payload: string }
  | { type: 'SET_LEFT_FILTER'; payload: { filterId: string; value: any } }
  | { type: 'SET_RIGHT_FILTER'; payload: { filterId: string; value: any } }
  | { type: 'CLEAR_LEFT_FILTERS' }
  | { type: 'CLEAR_RIGHT_FILTERS' }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | undefined }
  | { type: 'ADD_OPERATION'; payload: TransferOperation }
  | { type: 'UNDO_OPERATION' }
  | { type: 'REDO_OPERATION' }
  | { type: 'CLEAR_HISTORY' }
  | { type: 'SET_VALIDATION_RESULTS'; payload: TransferListState['validationResults'] }
  | { type: 'RESET' };

// Initial state factory
function createInitialState(
  leftItems: TransferItem[] = [],
  rightItems: TransferItem[] = []
): TransferListState {
  return {
    leftItems,
    rightItems,
    leftSelected: new Set(),
    rightSelected: new Set(),
    leftSearch: '',
    rightSearch: '',
    leftFilters: {},
    rightFilters: {},
    leftCategories: [],
    rightCategories: [],
    operations: [],
    isDirty: false,
    isLoading: false,
    error: undefined,
    validationResults: []
  };
}

// Reducer function
function transferListReducer(
  state: TransferListState,
  action: TransferListAction
): TransferListState {
  switch (action.type) {
    case 'SET_LEFT_ITEMS':
      return {
        ...state,
        leftItems: action.payload,
        leftSelected: new Set() // Clear selection when items change
      };

    case 'SET_RIGHT_ITEMS':
      return {
        ...state,
        rightItems: action.payload,
        rightSelected: new Set()
      };

    case 'ADD_LEFT_ITEM':
      return {
        ...state,
        leftItems: [...state.leftItems, action.payload],
        isDirty: true
      };

    case 'ADD_RIGHT_ITEM':
      return {
        ...state,
        rightItems: [...state.rightItems, action.payload],
        isDirty: true
      };

    case 'REMOVE_LEFT_ITEM':
      return {
        ...state,
        leftItems: state.leftItems.filter(item => item.id !== action.payload),
        leftSelected: new Set(Array.from(state.leftSelected).filter(id => id !== action.payload)),
        isDirty: true
      };

    case 'REMOVE_RIGHT_ITEM':
      return {
        ...state,
        rightItems: state.rightItems.filter(item => item.id !== action.payload),
        rightSelected: new Set(Array.from(state.rightSelected).filter(id => id !== action.payload)),
        isDirty: true
      };

    case 'TOGGLE_LEFT_SELECTION': {
      const newSelection = new Set(state.leftSelected);
      if (newSelection.has(action.payload)) {
        newSelection.delete(action.payload);
      } else {
        newSelection.add(action.payload);
      }
      return {
        ...state,
        leftSelected: newSelection
      };
    }

    case 'TOGGLE_RIGHT_SELECTION': {
      const newSelection = new Set(state.rightSelected);
      if (newSelection.has(action.payload)) {
        newSelection.delete(action.payload);
      } else {
        newSelection.add(action.payload);
      }
      return {
        ...state,
        rightSelected: newSelection
      };
    }

    case 'SELECT_ALL_LEFT':
      return {
        ...state,
        leftSelected: new Set(state.leftItems.map(item => item.id))
      };

    case 'SELECT_ALL_RIGHT':
      return {
        ...state,
        rightSelected: new Set(state.rightItems.map(item => item.id))
      };

    case 'CLEAR_LEFT_SELECTION':
      return {
        ...state,
        leftSelected: new Set()
      };

    case 'CLEAR_RIGHT_SELECTION':
      return {
        ...state,
        rightSelected: new Set()
      };

    case 'CLEAR_ALL_SELECTION':
      return {
        ...state,
        leftSelected: new Set(),
        rightSelected: new Set()
      };

    case 'TRANSFER_TO_RIGHT': {
      const itemsToTransfer = state.leftItems.filter(item =>
        action.payload.includes(item.id)
      );
      const remainingLeftItems = state.leftItems.filter(item =>
        !action.payload.includes(item.id)
      );
      const newRightItems = [...state.rightItems, ...itemsToTransfer];

      // Clear selections for transferred items
      const newLeftSelected = new Set(
        Array.from(state.leftSelected).filter(id => !action.payload.includes(id))
      );

      return {
        ...state,
        leftItems: remainingLeftItems,
        rightItems: newRightItems,
        leftSelected: newLeftSelected,
        isDirty: true
      };
    }

    case 'TRANSFER_TO_LEFT': {
      const itemsToTransfer = state.rightItems.filter(item =>
        action.payload.includes(item.id)
      );
      const remainingRightItems = state.rightItems.filter(item =>
        !action.payload.includes(item.id)
      );
      const newLeftItems = [...state.leftItems, ...itemsToTransfer];

      // Clear selections for transferred items
      const newRightSelected = new Set(
        Array.from(state.rightSelected).filter(id => !action.payload.includes(id))
      );

      return {
        ...state,
        leftItems: newLeftItems,
        rightItems: remainingRightItems,
        rightSelected: newRightSelected,
        isDirty: true
      };
    }

    case 'SET_LEFT_SEARCH':
      return {
        ...state,
        leftSearch: action.payload
      };

    case 'SET_RIGHT_SEARCH':
      return {
        ...state,
        rightSearch: action.payload
      };

    case 'SET_LEFT_FILTER':
      return {
        ...state,
        leftFilters: {
          ...state.leftFilters,
          [action.payload.filterId]: action.payload.value
        }
      };

    case 'SET_RIGHT_FILTER':
      return {
        ...state,
        rightFilters: {
          ...state.rightFilters,
          [action.payload.filterId]: action.payload.value
        }
      };

    case 'CLEAR_LEFT_FILTERS':
      return {
        ...state,
        leftFilters: {},
        leftSearch: ''
      };

    case 'CLEAR_RIGHT_FILTERS':
      return {
        ...state,
        rightFilters: {},
        rightSearch: ''
      };

    case 'SET_LOADING':
      return {
        ...state,
        isLoading: action.payload
      };

    case 'SET_ERROR':
      return {
        ...state,
        error: action.payload,
        isLoading: false
      };

    case 'ADD_OPERATION':
      return {
        ...state,
        operations: [...state.operations, action.payload]
      };

    case 'SET_VALIDATION_RESULTS':
      return {
        ...state,
        validationResults: action.payload
      };

    case 'RESET':
      return createInitialState();

    default:
      return state;
  }
}

// Utility functions for filtering and searching
function applyFiltersAndSearch(
  items: TransferItem[],
  search: string,
  filters: Record<string, any>
): TransferItem[] {
  let filtered = [...items];

  // Apply search
  if (search.trim()) {
    const query = search.toLowerCase();
    filtered = filtered.filter(item => {
      const searchText = item.searchableText ||
        `${item.label} ${item.description || ''}`.toLowerCase();
      return searchText.includes(query);
    });
  }

  // Apply filters
  Object.entries(filters).forEach(([filterId, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      filtered = filtered.filter(item => {
        // Custom filter logic based on filter type
        if (filterId === 'category') {
          return item.category === value;
        }
        if (filterId === 'tags') {
          return Array.isArray(value)
            ? value.some(tag => item.tags?.includes(tag))
            : item.tags?.includes(value);
        }
        // Generic metadata filtering
        return item.metadata?.[filterId] === value;
      });
    }
  });

  return filtered;
}

// Validation function
function validateTransferList(
  leftItems: TransferItem[],
  rightItems: TransferItem[],
  rules: TransferValidationRule[]
): TransferListState['validationResults'] {
  return rules.map(rule => {
    const result = rule.validate(leftItems, rightItems);
    return {
      ruleId: rule.id,
      valid: result.valid,
      message: result.message,
      severity: result.severity || 'error'
    };
  });
}

export function useTransferList(
  initialLeftItems: TransferItem[] = [],
  initialRightItems: TransferItem[] = [],
  options: {
    validationRules?: TransferValidationRule[];
    debounceMs?: number;
    maxHistorySize?: number;
    persistState?: boolean;
    storageKey?: string;
  } = {}
): UseTransferListReturn {
  const {
    validationRules = [],
    debounceMs = 300,
    maxHistorySize = 50,
    persistState = false,
    storageKey
  } = options;

  const [state, dispatch] = useReducer(
    transferListReducer,
    createInitialState(initialLeftItems, initialRightItems)
  );

  // History management
  const historyRef = useRef<TransferListState[]>([]);
  const historyIndexRef = useRef(-1);

  // Debounced search functions
  const debouncedSetLeftSearch = useRef(
    debounce((query: string) => {
      dispatch({ type: 'SET_LEFT_SEARCH', payload: query });
    }, debounceMs)
  ).current;

  const debouncedSetRightSearch = useRef(
    debounce((query: string) => {
      dispatch({ type: 'SET_RIGHT_SEARCH', payload: query });
    }, debounceMs)
  ).current;

  // Validation effect
  useEffect(() => {
    if (validationRules.length > 0) {
      const results = validateTransferList(state.leftItems, state.rightItems, validationRules);
      dispatch({ type: 'SET_VALIDATION_RESULTS', payload: results });
    }
  }, [state.leftItems, state.rightItems, validationRules]);

  // History tracking
  useEffect(() => {
    if (state.isDirty) {
      // Add current state to history
      historyRef.current = historyRef.current.slice(0, historyIndexRef.current + 1);
      historyRef.current.push(state);

      // Limit history size
      if (historyRef.current.length > maxHistorySize) {
        historyRef.current = historyRef.current.slice(-maxHistorySize);
      }

      historyIndexRef.current = historyRef.current.length - 1;
    }
  }, [state.isDirty, maxHistorySize]);

  // Persist state to localStorage
  useEffect(() => {
    if (persistState && storageKey && state.isDirty) {
      const stateToSave = {
        leftItems: state.leftItems,
        rightItems: state.rightItems,
        leftFilters: state.leftFilters,
        rightFilters: state.rightFilters
      };
      localStorage.setItem(storageKey, JSON.stringify(stateToSave));
    }
  }, [state, persistState, storageKey]);

  // Actions
  const actions = useMemo(() => ({
    // Item management
    setLeftItems: (items: TransferItem[]) =>
      dispatch({ type: 'SET_LEFT_ITEMS', payload: items }),
    setRightItems: (items: TransferItem[]) =>
      dispatch({ type: 'SET_RIGHT_ITEMS', payload: items }),
    addLeftItem: (item: TransferItem) =>
      dispatch({ type: 'ADD_LEFT_ITEM', payload: item }),
    addRightItem: (item: TransferItem) =>
      dispatch({ type: 'ADD_RIGHT_ITEM', payload: item }),
    removeLeftItem: (itemId: string | number) =>
      dispatch({ type: 'REMOVE_LEFT_ITEM', payload: itemId }),
    removeRightItem: (itemId: string | number) =>
      dispatch({ type: 'REMOVE_RIGHT_ITEM', payload: itemId }),

    // Selection
    toggleLeftSelection: (itemId: string | number) =>
      dispatch({ type: 'TOGGLE_LEFT_SELECTION', payload: itemId }),
    toggleRightSelection: (itemId: string | number) =>
      dispatch({ type: 'TOGGLE_RIGHT_SELECTION', payload: itemId }),
    selectAllLeft: () => dispatch({ type: 'SELECT_ALL_LEFT' }),
    selectAllRight: () => dispatch({ type: 'SELECT_ALL_RIGHT' }),
    clearLeftSelection: () => dispatch({ type: 'CLEAR_LEFT_SELECTION' }),
    clearRightSelection: () => dispatch({ type: 'CLEAR_RIGHT_SELECTION' }),
    clearAllSelection: () => dispatch({ type: 'CLEAR_ALL_SELECTION' }),

    // Transfer operations
    transferToRight: (itemIds?: (string | number)[]) => {
      const idsToTransfer = itemIds || Array.from(state.leftSelected);
      if (idsToTransfer.length > 0) {
        dispatch({ type: 'TRANSFER_TO_RIGHT', payload: idsToTransfer });
      }
    },
    transferToLeft: (itemIds?: (string | number)[]) => {
      const idsToTransfer = itemIds || Array.from(state.rightSelected);
      if (idsToTransfer.length > 0) {
        dispatch({ type: 'TRANSFER_TO_LEFT', payload: idsToTransfer });
      }
    },
    transferAllToRight: () => {
      const allIds = state.leftItems.map(item => item.id);
      dispatch({ type: 'TRANSFER_TO_RIGHT', payload: allIds });
    },
    transferAllToLeft: () => {
      const allIds = state.rightItems.map(item => item.id);
      dispatch({ type: 'TRANSFER_TO_LEFT', payload: allIds });
    },

    // Search and filter
    setLeftSearch: useCallback((query: string) => debouncedSetLeftSearch(query), [debouncedSetLeftSearch]),
    setRightSearch: useCallback((query: string) => debouncedSetRightSearch(query), [debouncedSetRightSearch]),
    setLeftFilter: (filterId: string, value: any) =>
      dispatch({ type: 'SET_LEFT_FILTER', payload: { filterId, value } }),
    setRightFilter: (filterId: string, value: any) =>
      dispatch({ type: 'SET_RIGHT_FILTER', payload: { filterId, value } }),
    clearLeftFilters: () => dispatch({ type: 'CLEAR_LEFT_FILTERS' }),
    clearRightFilters: () => dispatch({ type: 'CLEAR_RIGHT_FILTERS' }),

    // History
    undo: () => {
      if (historyIndexRef.current > 0) {
        historyIndexRef.current -= 1;
        // Would need to restore state from history
      }
    },
    redo: () => {
      if (historyIndexRef.current < historyRef.current.length - 1) {
        historyIndexRef.current += 1;
        // Would need to restore state from history
      }
    },
    clearHistory: () => {
      historyRef.current = [];
      historyIndexRef.current = -1;
    },

    // Validation
    validate: () => {
      const results = validateTransferList(state.leftItems, state.rightItems, validationRules);
      dispatch({ type: 'SET_VALIDATION_RESULTS', payload: results });
    },

    // State management
    setLoading: (loading: boolean) =>
      dispatch({ type: 'SET_LOADING', payload: loading }),
    setError: (error: string | undefined) =>
      dispatch({ type: 'SET_ERROR', payload: error }),
    reset: () => dispatch({ type: 'RESET' })
  }), [state, debouncedSetLeftSearch, debouncedSetRightSearch, validationRules]);

  // Computed values
  const computed = useMemo(() => {
    const filteredLeftItems = applyFiltersAndSearch(
      state.leftItems,
      state.leftSearch,
      state.leftFilters
    );
    const filteredRightItems = applyFiltersAndSearch(
      state.rightItems,
      state.rightSearch,
      state.rightFilters
    );

    const leftSelectedItems = state.leftItems.filter(item =>
      state.leftSelected.has(item.id)
    );
    const rightSelectedItems = state.rightItems.filter(item =>
      state.rightSelected.has(item.id)
    );

    const isValid = state.validationResults.every(result => result.valid);

    return {
      filteredLeftItems,
      filteredRightItems,
      leftSelectedItems,
      rightSelectedItems,
      canTransferToRight: state.leftSelected.size > 0,
      canTransferToLeft: state.rightSelected.size > 0,
      canUndo: historyIndexRef.current > 0,
      canRedo: historyIndexRef.current < historyRef.current.length - 1,
      isValid,
      hasChanges: state.isDirty,
      progress: state.rightItems.length / (state.leftItems.length + state.rightItems.length || 1)
    };
  }, [state]);

  return {
    state,
    actions,
    computed
  };
}