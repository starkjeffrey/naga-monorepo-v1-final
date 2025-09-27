/**
 * Enhanced TransferList Types
 * Complete type definitions for the enhanced transfer/assignment list pattern
 */

export interface TransferItem {
  id: string | number;
  label: string;
  description?: string;
  avatar?: string;
  metadata?: Record<string, any>;
  disabled?: boolean;
  category?: string;
  tags?: string[];
  searchableText?: string;
}

export interface TransferCategory {
  id: string;
  label: string;
  color?: string;
  icon?: React.ReactNode;
  description?: string;
}

export interface TransferListFilter {
  id: string;
  label: string;
  type: 'text' | 'select' | 'multiSelect' | 'category';
  options?: Array<{ label: string; value: any }>;
  placeholder?: string;
}

export interface TransferOperation {
  type: 'move' | 'copy' | 'remove';
  items: TransferItem[];
  fromSide: 'left' | 'right';
  toSide: 'left' | 'right';
  timestamp: Date;
  metadata?: Record<string, any>;
}

export interface TransferDraft {
  id: string;
  name: string;
  operations: TransferOperation[];
  leftItems: TransferItem[];
  rightItems: TransferItem[];
  createdAt: Date;
  updatedAt: Date;
  metadata?: Record<string, any>;
}

export interface TransferValidationRule {
  id: string;
  name: string;
  validate: (leftItems: TransferItem[], rightItems: TransferItem[]) => {
    valid: boolean;
    message?: string;
    severity?: 'error' | 'warning' | 'info';
  };
  enabled?: boolean;
}

export interface TransferListState {
  leftItems: TransferItem[];
  rightItems: TransferItem[];
  leftSelected: Set<string | number>;
  rightSelected: Set<string | number>;
  leftSearch: string;
  rightSearch: string;
  leftFilters: Record<string, any>;
  rightFilters: Record<string, any>;
  leftCategories: string[];
  rightCategories: string[];
  operations: TransferOperation[];
  isDirty: boolean;
  isLoading: boolean;
  error?: string;
  validationResults: Array<{
    ruleId: string;
    valid: boolean;
    message?: string;
    severity?: 'error' | 'warning' | 'info';
  }>;
}

export interface TransferListProps {
  // Data
  leftItems?: TransferItem[];
  rightItems?: TransferItem[];
  availableItems?: TransferItem[];

  // Configuration
  leftTitle?: string;
  rightTitle?: string;
  leftSubtitle?: string;
  rightSubtitle?: string;
  keyField?: keyof TransferItem;

  // Features
  searchable?: boolean;
  filterable?: boolean;
  categorizable?: boolean;
  sortable?: boolean;
  virtualScrolling?: boolean;

  // Search configuration
  leftSearchPlaceholder?: string;
  rightSearchPlaceholder?: string;
  searchDebounceMs?: number;

  // Filter configuration
  leftFilters?: TransferListFilter[];
  rightFilters?: TransferListFilter[];

  // Category configuration
  categories?: TransferCategory[];
  showCategoryLabels?: boolean;

  // Transfer operations
  allowCopy?: boolean;
  allowMove?: boolean;
  allowBulkOperations?: boolean;
  maxLeftItems?: number;
  maxRightItems?: number;

  // Draft functionality
  draftable?: boolean;
  currentDraft?: TransferDraft;
  savedDrafts?: TransferDraft[];
  onDraftSave?: (draft: Omit<TransferDraft, 'id' | 'createdAt' | 'updatedAt'>) => void;
  onDraftLoad?: (draft: TransferDraft) => void;
  onDraftDelete?: (draftId: string) => void;

  // Validation
  validationRules?: TransferValidationRule[];
  validateOnChange?: boolean;

  // Undo/Redo
  undoable?: boolean;
  maxHistorySize?: number;

  // Real-time collaboration
  collaborative?: boolean;
  collaborators?: Array<{ id: string; name: string; avatar?: string; color?: string }>;
  onCollaboratorJoin?: (collaboratorId: string) => void;
  onCollaboratorLeave?: (collaboratorId: string) => void;

  // Progress tracking
  showProgress?: boolean;
  progressTarget?: number;

  // Styling
  height?: number | string;
  itemHeight?: number;
  className?: string;
  leftClassName?: string;
  rightClassName?: string;

  // Customization
  renderItem?: (item: TransferItem, side: 'left' | 'right', selected: boolean) => React.ReactNode;
  renderEmpty?: (side: 'left' | 'right') => React.ReactNode;
  renderHeader?: (side: 'left' | 'right', title: string, subtitle?: string) => React.ReactNode;
  renderFooter?: (side: 'left' | 'right', items: TransferItem[]) => React.ReactNode;

  // Events
  onTransfer?: (operation: TransferOperation) => void;
  onSelectionChange?: (leftSelected: Set<string | number>, rightSelected: Set<string | number>) => void;
  onChange?: (leftItems: TransferItem[], rightItems: TransferItem[]) => void;
  onValidation?: (results: TransferListState['validationResults']) => void;
  onSearch?: (leftQuery: string, rightQuery: string) => void;
  onFilter?: (leftFilters: Record<string, any>, rightFilters: Record<string, any>) => void;

  // Accessibility
  ariaLabel?: string;
  leftAriaLabel?: string;
  rightAriaLabel?: string;
}

export interface TransferListRef {
  // State access
  getState: () => TransferListState;
  setState: (state: Partial<TransferListState>) => void;

  // Operations
  transferSelected: (fromSide: 'left' | 'right') => void;
  transferAll: (fromSide: 'left' | 'right') => void;
  clearSelection: (side?: 'left' | 'right') => void;
  selectAll: (side: 'left' | 'right') => void;

  // History
  undo: () => boolean;
  redo: () => boolean;
  canUndo: () => boolean;
  canRedo: () => boolean;
  clearHistory: () => void;

  // Validation
  validate: () => TransferListState['validationResults'];
  isValid: () => boolean;

  // Draft management
  saveDraft: (name: string, metadata?: Record<string, any>) => void;
  loadDraft: (draftId: string) => void;
  resetToOriginal: () => void;

  // Search and filter
  setSearch: (side: 'left' | 'right', query: string) => void;
  setFilter: (side: 'left' | 'right', filterId: string, value: any) => void;
  clearFilters: (side?: 'left' | 'right') => void;

  // Utility
  refresh: () => void;
  reset: () => void;
  export: () => TransferDraft;
  import: (data: TransferDraft) => void;
}

// Hook return types
export interface UseTransferListReturn {
  state: TransferListState;
  actions: {
    // Item management
    setLeftItems: (items: TransferItem[]) => void;
    setRightItems: (items: TransferItem[]) => void;
    addLeftItem: (item: TransferItem) => void;
    addRightItem: (item: TransferItem) => void;
    removeLeftItem: (itemId: string | number) => void;
    removeRightItem: (itemId: string | number) => void;

    // Selection
    toggleLeftSelection: (itemId: string | number) => void;
    toggleRightSelection: (itemId: string | number) => void;
    selectAllLeft: () => void;
    selectAllRight: () => void;
    clearLeftSelection: () => void;
    clearRightSelection: () => void;
    clearAllSelection: () => void;

    // Transfer operations
    transferToRight: (itemIds?: (string | number)[]) => void;
    transferToLeft: (itemIds?: (string | number)[]) => void;
    transferAllToRight: () => void;
    transferAllToLeft: () => void;

    // Search and filter
    setLeftSearch: (query: string) => void;
    setRightSearch: (query: string) => void;
    setLeftFilter: (filterId: string, value: any) => void;
    setRightFilter: (filterId: string, value: any) => void;
    clearLeftFilters: () => void;
    clearRightFilters: () => void;

    // History
    undo: () => void;
    redo: () => void;
    clearHistory: () => void;

    // Validation
    validate: () => void;

    // State management
    setLoading: (loading: boolean) => void;
    setError: (error: string | undefined) => void;
    reset: () => void;
  };
  computed: {
    filteredLeftItems: TransferItem[];
    filteredRightItems: TransferItem[];
    leftSelectedItems: TransferItem[];
    rightSelectedItems: TransferItem[];
    canTransferToRight: boolean;
    canTransferToLeft: boolean;
    canUndo: boolean;
    canRedo: boolean;
    isValid: boolean;
    hasChanges: boolean;
    progress: number;
  };
}

// Event types
export interface TransferItemClickEvent {
  item: TransferItem;
  side: 'left' | 'right';
  selected: boolean;
  originalEvent: React.MouseEvent;
}

export interface TransferItemDoubleClickEvent {
  item: TransferItem;
  side: 'left' | 'right';
  originalEvent: React.MouseEvent;
}

export interface TransferDragEvent {
  items: TransferItem[];
  fromSide: 'left' | 'right';
  toSide: 'left' | 'right';
  originalEvent: React.DragEvent;
}

// WebSocket types for real-time collaboration
export interface CollaborationEvent {
  type: 'user_joined' | 'user_left' | 'selection_changed' | 'transfer_operation' | 'draft_saved';
  userId: string;
  data: any;
  timestamp: Date;
}

export interface CollaborationState {
  isConnected: boolean;
  collaborators: Map<string, {
    id: string;
    name: string;
    avatar?: string;
    color?: string;
    selections: {
      left: Set<string | number>;
      right: Set<string | number>;
    };
    lastSeen: Date;
  }>;
  events: CollaborationEvent[];
}