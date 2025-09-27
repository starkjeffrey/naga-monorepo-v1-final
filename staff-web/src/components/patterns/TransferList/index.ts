/**
 * Enhanced TransferList Pattern Exports
 * Complete export file for the TransferList pattern
 */

// Main component
export { default as TransferList } from './TransferList';

// Sub-components
export { TransferListPanel } from './components/TransferListPanel';
export { TransferControls } from './components/TransferControls';

// Hooks
export { useTransferList } from './hooks/useTransferList';

// Types
export type {
  TransferItem,
  TransferCategory,
  TransferListFilter,
  TransferOperation,
  TransferDraft,
  TransferValidationRule,
  TransferListState,
  TransferListProps,
  TransferListRef,
  UseTransferListReturn,
  TransferItemClickEvent,
  TransferItemDoubleClickEvent,
  TransferDragEvent,
  CollaborationEvent,
  CollaborationState
} from './types';

// Utility functions for common use cases
export const createTransferItem = (
  id: string | number,
  label: string,
  options: Partial<Omit<TransferItem, 'id' | 'label'>> = {}
): TransferItem => ({
  id,
  label,
  searchableText: `${label} ${options.description || ''}`.toLowerCase(),
  ...options
});

export const createTransferCategory = (
  id: string,
  label: string,
  options: Partial<Omit<TransferCategory, 'id' | 'label'>> = {}
): TransferCategory => ({
  id,
  label,
  ...options
});

export const createTransferFilter = (
  id: string,
  label: string,
  type: TransferListFilter['type'],
  options: Partial<Omit<TransferListFilter, 'id' | 'label' | 'type'>> = {}
): TransferListFilter => ({
  id,
  label,
  type,
  ...options
});

export const createValidationRule = (
  id: string,
  name: string,
  validate: TransferValidationRule['validate'],
  options: Partial<Omit<TransferValidationRule, 'id' | 'name' | 'validate'>> = {}
): TransferValidationRule => ({
  id,
  name,
  validate,
  enabled: true,
  ...options
});

// Common validation rules
export const validationRules = {
  maxItems: (max: number) => createValidationRule(
    'max-items',
    'Maximum items limit',
    (leftItems, rightItems) => ({
      valid: rightItems.length <= max,
      message: `Cannot exceed ${max} items (currently ${rightItems.length})`,
      severity: 'error' as const
    })
  ),

  minItems: (min: number) => createValidationRule(
    'min-items',
    'Minimum items requirement',
    (leftItems, rightItems) => ({
      valid: rightItems.length >= min,
      message: `Must have at least ${min} items (currently ${rightItems.length})`,
      severity: 'error' as const
    })
  ),

  requiredCategories: (categories: string[]) => createValidationRule(
    'required-categories',
    'Required categories',
    (leftItems, rightItems) => {
      const selectedCategories = new Set(
        rightItems.map(item => item.category).filter(Boolean)
      );
      const missingCategories = categories.filter(cat => !selectedCategories.has(cat));

      return {
        valid: missingCategories.length === 0,
        message: missingCategories.length > 0
          ? `Missing required categories: ${missingCategories.join(', ')}`
          : undefined,
        severity: 'warning' as const
      };
    }
  ),

  noDuplicates: () => createValidationRule(
    'no-duplicates',
    'No duplicate items',
    (leftItems, rightItems) => {
      const rightIds = new Set(rightItems.map(item => item.id));
      const duplicates = leftItems.filter(item => rightIds.has(item.id));

      return {
        valid: duplicates.length === 0,
        message: duplicates.length > 0
          ? `Found ${duplicates.length} duplicate items`
          : undefined,
        severity: 'error' as const
      };
    }
  ),

  balancedSelection: (tolerance = 0.2) => createValidationRule(
    'balanced-selection',
    'Balanced selection',
    (leftItems, rightItems) => {
      const total = leftItems.length + rightItems.length;
      const selectedRatio = rightItems.length / total;
      const expectedRatio = 0.5;
      const difference = Math.abs(selectedRatio - expectedRatio);

      return {
        valid: difference <= tolerance,
        message: difference > tolerance
          ? `Selection is unbalanced (${Math.round(selectedRatio * 100)}% selected)`
          : undefined,
        severity: 'info' as const
      };
    }
  )
};

// Common filters
export const commonFilters = {
  category: (categories: TransferCategory[]) => createTransferFilter(
    'category',
    'Category',
    'select',
    {
      options: categories.map(cat => ({ label: cat.label, value: cat.id }))
    }
  ),

  tags: (availableTags: string[]) => createTransferFilter(
    'tags',
    'Tags',
    'multiSelect',
    {
      options: availableTags.map(tag => ({ label: tag, value: tag }))
    }
  ),

  search: () => createTransferFilter(
    'search',
    'Search',
    'text',
    {
      placeholder: 'Search items...'
    }
  )
};

// Preset configurations
export const presets = {
  simple: {
    searchable: true,
    filterable: false,
    categorizable: false,
    undoable: false,
    draftable: false
  },

  standard: {
    searchable: true,
    filterable: true,
    categorizable: true,
    undoable: true,
    draftable: false,
    allowBulkOperations: true
  },

  advanced: {
    searchable: true,
    filterable: true,
    categorizable: true,
    undoable: true,
    draftable: true,
    allowCopy: true,
    allowBulkOperations: true,
    validateOnChange: true,
    virtualScrolling: true
  },

  collaborative: {
    searchable: true,
    filterable: true,
    categorizable: true,
    undoable: true,
    draftable: true,
    allowCopy: true,
    allowBulkOperations: true,
    validateOnChange: true,
    virtualScrolling: true,
    collaborative: true
  }
};

// Helper functions
export const transferListUtils = {
  // Create items from array of objects
  createItemsFromObjects: <T extends Record<string, any>>(
    objects: T[],
    config: {
      idField: keyof T;
      labelField: keyof T;
      descriptionField?: keyof T;
      categoryField?: keyof T;
      tagsField?: keyof T;
      metadataFields?: (keyof T)[];
    }
  ): TransferItem[] => {
    return objects.map(obj => createTransferItem(
      obj[config.idField],
      String(obj[config.labelField]),
      {
        description: config.descriptionField ? String(obj[config.descriptionField]) : undefined,
        category: config.categoryField ? String(obj[config.categoryField]) : undefined,
        tags: config.tagsField ? obj[config.tagsField] : undefined,
        metadata: config.metadataFields ?
          Object.fromEntries(config.metadataFields.map(field => [field, obj[field]])) :
          undefined
      }
    ));
  },

  // Filter items by search query
  filterItemsBySearch: (items: TransferItem[], query: string): TransferItem[] => {
    if (!query.trim()) return items;

    const lowerQuery = query.toLowerCase();
    return items.filter(item => {
      const searchText = item.searchableText ||
        `${item.label} ${item.description || ''}`.toLowerCase();
      return searchText.includes(lowerQuery);
    });
  },

  // Group items by category
  groupItemsByCategory: (items: TransferItem[]): Record<string, TransferItem[]> => {
    return items.reduce((groups, item) => {
      const category = item.category || 'uncategorized';
      if (!groups[category]) {
        groups[category] = [];
      }
      groups[category].push(item);
      return groups;
    }, {} as Record<string, TransferItem[]>);
  },

  // Export transfer state to JSON
  exportToJSON: (leftItems: TransferItem[], rightItems: TransferItem[]): string => {
    return JSON.stringify({
      leftItems,
      rightItems,
      exportedAt: new Date().toISOString()
    }, null, 2);
  },

  // Import transfer state from JSON
  importFromJSON: (json: string): { leftItems: TransferItem[]; rightItems: TransferItem[] } => {
    try {
      const data = JSON.parse(json);
      return {
        leftItems: data.leftItems || [],
        rightItems: data.rightItems || []
      };
    } catch (error) {
      throw new Error('Invalid JSON format');
    }
  }
};

// Default export for convenience
export {
  TransferList as default,
  type TransferItem,
  type TransferListProps,
  type TransferListRef
} from './TransferList';