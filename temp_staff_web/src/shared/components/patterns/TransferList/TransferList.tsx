/**
 * Enhanced TransferList Component
 * Complete transfer/assignment list with all features
 */

import React, { forwardRef, useImperativeHandle } from 'react';
import { TransferListProps, TransferListRef } from './types';
import { useTransferList } from './hooks/useTransferList';
import { TransferListPanel } from './components/TransferListPanel';
import { TransferControls } from './components/TransferControls';

export const TransferList = forwardRef<TransferListRef, TransferListProps>(function TransferList(
  {
    // Data
    leftItems = [],
    rightItems = [],
    availableItems = [],

    // Configuration
    leftTitle = 'Available',
    rightTitle = 'Selected',
    leftSubtitle,
    rightSubtitle,
    keyField = 'id',

    // Features
    searchable = true,
    filterable = true,
    categorizable = false,
    sortable = true,
    virtualScrolling = false,

    // Search configuration
    leftSearchPlaceholder,
    rightSearchPlaceholder,
    searchDebounceMs = 300,

    // Filter configuration
    leftFilters = [],
    rightFilters = [],

    // Category configuration
    categories = [],
    showCategoryLabels = true,

    // Transfer operations
    allowCopy = false,
    allowMove = true,
    allowBulkOperations = true,
    maxLeftItems,
    maxRightItems,

    // Draft functionality
    draftable = false,
    currentDraft,
    savedDrafts = [],
    onDraftSave,
    onDraftLoad,
    onDraftDelete,

    // Validation
    validationRules = [],
    validateOnChange = true,

    // Undo/Redo
    undoable = false,
    maxHistorySize = 50,

    // Real-time collaboration
    collaborative = false,
    collaborators = [],
    onCollaboratorJoin,
    onCollaboratorLeave,

    // Progress tracking
    showProgress = false,
    progressTarget,

    // Styling
    height = 500,
    itemHeight = 48,
    className = '',
    leftClassName = '',
    rightClassName = '',

    // Customization
    renderItem,
    renderEmpty,
    renderHeader,
    renderFooter,

    // Events
    onTransfer,
    onSelectionChange,
    onChange,
    onValidation,
    onSearch,
    onFilter,

    // Accessibility
    ariaLabel = 'Transfer list',
    leftAriaLabel,
    rightAriaLabel
  },
  ref
) {
  // Use the hook for state management
  const {
    state,
    actions,
    computed
  } = useTransferList(
    leftItems.length > 0 ? leftItems : availableItems,
    rightItems,
    {
      validationRules,
      debounceMs: searchDebounceMs,
      maxHistorySize,
      persistState: true,
      storageKey: 'transfer-list-state'
    }
  );

  // Category state (simplified for demo)
  const [leftSelectedCategories, setLeftSelectedCategories] = React.useState<string[]>([]);
  const [rightSelectedCategories, setRightSelectedCategories] = React.useState<string[]>([]);

  // Copy mode state
  const [copyMode, setCopyMode] = React.useState(false);
  const [autoTransfer, setAutoTransfer] = React.useState(false);

  // Handle category toggles
  const handleLeftCategoryToggle = (categoryId: string) => {
    setLeftSelectedCategories(prev =>
      prev.includes(categoryId)
        ? prev.filter(id => id !== categoryId)
        : [...prev, categoryId]
    );
  };

  const handleRightCategoryToggle = (categoryId: string) => {
    setRightSelectedCategories(prev =>
      prev.includes(categoryId)
        ? prev.filter(id => id !== categoryId)
        : [...prev, categoryId]
    );
  };

  // Event handlers
  React.useEffect(() => {
    if (onSelectionChange) {
      onSelectionChange(state.leftSelected, state.rightSelected);
    }
  }, [state.leftSelected, state.rightSelected, onSelectionChange]);

  React.useEffect(() => {
    if (onChange) {
      onChange(state.leftItems, state.rightItems);
    }
  }, [state.leftItems, state.rightItems, onChange]);

  React.useEffect(() => {
    if (onValidation && state.validationResults.length > 0) {
      onValidation(state.validationResults);
    }
  }, [state.validationResults, onValidation]);

  React.useEffect(() => {
    if (onSearch) {
      onSearch(state.leftSearch, state.rightSearch);
    }
  }, [state.leftSearch, state.rightSearch, onSearch]);

  React.useEffect(() => {
    if (onFilter) {
      onFilter(state.leftFilters, state.rightFilters);
    }
  }, [state.leftFilters, state.rightFilters, onFilter]);

  // Handle draft operations
  const handleSaveDraft = () => {
    if (onDraftSave) {
      onDraftSave({
        name: `Draft ${new Date().toLocaleDateString()} ${new Date().toLocaleTimeString()}`,
        operations: state.operations,
        leftItems: state.leftItems,
        rightItems: state.rightItems,
        metadata: {
          leftFilters: state.leftFilters,
          rightFilters: state.rightFilters,
          leftSearch: state.leftSearch,
          rightSearch: state.rightSearch
        }
      });
    }
  };

  const handleLoadDraft = () => {
    // Would typically show a draft selection dialog
    if (onDraftLoad && savedDrafts.length > 0) {
      onDraftLoad(savedDrafts[0]);
    }
  };

  // Expose imperative API
  useImperativeHandle(ref, () => ({
    // State access
    getState: () => state,
    setState: (newState) => {
      // Would need to implement partial state updates
    },

    // Operations
    transferSelected: (fromSide) => {
      if (fromSide === 'left') {
        actions.transferToRight();
      } else {
        actions.transferToLeft();
      }
    },
    transferAll: (fromSide) => {
      if (fromSide === 'left') {
        actions.transferAllToRight();
      } else {
        actions.transferAllToLeft();
      }
    },
    clearSelection: (side) => {
      if (!side || side === 'left') {
        actions.clearLeftSelection();
      }
      if (!side || side === 'right') {
        actions.clearRightSelection();
      }
    },
    selectAll: (side) => {
      if (side === 'left') {
        actions.selectAllLeft();
      } else {
        actions.selectAllRight();
      }
    },

    // History
    undo: () => {
      actions.undo();
      return computed.canUndo;
    },
    redo: () => {
      actions.redo();
      return computed.canRedo;
    },
    canUndo: () => computed.canUndo,
    canRedo: () => computed.canRedo,
    clearHistory: actions.clearHistory,

    // Validation
    validate: () => {
      actions.validate();
      return state.validationResults;
    },
    isValid: () => computed.isValid,

    // Draft management
    saveDraft: handleSaveDraft,
    loadDraft: handleLoadDraft,
    resetToOriginal: actions.reset,

    // Search and filter
    setSearch: (side, query) => {
      if (side === 'left') {
        actions.setLeftSearch(query);
      } else {
        actions.setRightSearch(query);
      }
    },
    setFilter: (side, filterId, value) => {
      if (side === 'left') {
        actions.setLeftFilter(filterId, value);
      } else {
        actions.setRightFilter(filterId, value);
      }
    },
    clearFilters: (side) => {
      if (!side || side === 'left') {
        actions.clearLeftFilters();
      }
      if (!side || side === 'right') {
        actions.clearRightFilters();
      }
    },

    // Utility
    refresh: () => {
      actions.reset();
    },
    reset: actions.reset,
    export: () => ({
      id: 'export',
      name: 'Export',
      operations: state.operations,
      leftItems: state.leftItems,
      rightItems: state.rightItems,
      createdAt: new Date(),
      updatedAt: new Date()
    }),
    import: (data) => {
      actions.setLeftItems(data.leftItems);
      actions.setRightItems(data.rightItems);
    }
  }), [state, actions, computed, savedDrafts, onDraftLoad]);

  const containerHeight = typeof height === 'number' ? `${height}px` : height;

  return (
    <div
      className={`flex bg-gray-50 border border-gray-200 rounded-lg overflow-hidden ${className}`}
      style={{ height: containerHeight }}
      role="group"
      aria-label={ariaLabel}
    >
      {/* Left Panel */}
      <div className={`flex-1 ${leftClassName}`}>
        <TransferListPanel
          items={computed.filteredLeftItems}
          selectedItems={state.leftSelected}
          side="left"
          title={leftTitle}
          subtitle={leftSubtitle}
          searchable={searchable}
          filterable={filterable}
          categorizable={categorizable}
          virtualScrolling={virtualScrolling}
          searchQuery={state.leftSearch}
          searchPlaceholder={leftSearchPlaceholder}
          onSearchChange={actions.setLeftSearch}
          filters={leftFilters}
          activeFilters={state.leftFilters}
          onFilterChange={actions.setLeftFilter}
          onClearFilters={actions.clearLeftFilters}
          categories={categories}
          selectedCategories={leftSelectedCategories}
          onCategoryToggle={handleLeftCategoryToggle}
          onItemToggle={actions.toggleLeftSelection}
          onSelectAll={actions.selectAllLeft}
          onClearSelection={actions.clearLeftSelection}
          height={typeof height === 'number' ? height : 500}
          itemHeight={itemHeight}
          renderItem={renderItem}
          renderEmpty={renderEmpty}
          ariaLabel={leftAriaLabel || `${leftTitle} items`}
        />
      </div>

      {/* Transfer Controls */}
      <div className="flex items-center justify-center px-4 bg-white border-l border-r border-gray-200">
        <TransferControls
          canTransferToRight={computed.canTransferToRight}
          canTransferToLeft={computed.canTransferToLeft}
          leftSelectedCount={state.leftSelected.size}
          rightSelectedCount={state.rightSelected.size}
          leftTotalCount={state.leftItems.length}
          rightTotalCount={state.rightItems.length}
          onTransferToRight={actions.transferToRight}
          onTransferToLeft={actions.transferToLeft}
          onTransferAllToRight={actions.transferAllToRight}
          onTransferAllToLeft={actions.transferAllToLeft}
          allowCopy={allowCopy}
          copyMode={copyMode}
          onToggleCopyMode={() => setCopyMode(!copyMode)}
          undoable={undoable}
          canUndo={computed.canUndo}
          canRedo={computed.canRedo}
          onUndo={actions.undo}
          onRedo={actions.redo}
          validationResults={state.validationResults}
          isValid={computed.isValid}
          draftable={draftable}
          isDirty={computed.hasChanges}
          onSaveDraft={handleSaveDraft}
          onLoadDraft={handleLoadDraft}
          savedDrafts={savedDrafts}
          showProgress={showProgress}
          progress={computed.progress}
          progressTarget={progressTarget}
          autoTransfer={autoTransfer}
          onToggleAutoTransfer={() => setAutoTransfer(!autoTransfer)}
          orientation="vertical"
        />
      </div>

      {/* Right Panel */}
      <div className={`flex-1 ${rightClassName}`}>
        <TransferListPanel
          items={computed.filteredRightItems}
          selectedItems={state.rightSelected}
          side="right"
          title={rightTitle}
          subtitle={rightSubtitle}
          searchable={searchable}
          filterable={filterable}
          categorizable={categorizable}
          virtualScrolling={virtualScrolling}
          searchQuery={state.rightSearch}
          searchPlaceholder={rightSearchPlaceholder}
          onSearchChange={actions.setRightSearch}
          filters={rightFilters}
          activeFilters={state.rightFilters}
          onFilterChange={actions.setRightFilter}
          onClearFilters={actions.clearRightFilters}
          categories={categories}
          selectedCategories={rightSelectedCategories}
          onCategoryToggle={handleRightCategoryToggle}
          onItemToggle={actions.toggleRightSelection}
          onSelectAll={actions.selectAllRight}
          onClearSelection={actions.clearRightSelection}
          height={typeof height === 'number' ? height : 500}
          itemHeight={itemHeight}
          renderItem={renderItem}
          renderEmpty={renderEmpty}
          ariaLabel={rightAriaLabel || `${rightTitle} items`}
        />
      </div>

      {/* Collaboration indicators */}
      {collaborative && collaborators.length > 0 && (
        <div className="absolute top-2 right-2 flex -space-x-2">
          {collaborators.slice(0, 3).map(collaborator => (
            <div
              key={collaborator.id}
              className="w-8 h-8 rounded-full border-2 border-white bg-gray-300 flex items-center justify-center text-xs font-medium"
              style={{ backgroundColor: collaborator.color }}
              title={collaborator.name}
            >
              {collaborator.avatar ? (
                <img
                  src={collaborator.avatar}
                  alt={collaborator.name}
                  className="w-full h-full rounded-full"
                />
              ) : (
                collaborator.name.charAt(0).toUpperCase()
              )}
            </div>
          ))}
          {collaborators.length > 3 && (
            <div className="w-8 h-8 rounded-full border-2 border-white bg-gray-300 flex items-center justify-center text-xs font-medium">
              +{collaborators.length - 3}
            </div>
          )}
        </div>
      )}
    </div>
  );
});

TransferList.displayName = 'TransferList';

export default TransferList;