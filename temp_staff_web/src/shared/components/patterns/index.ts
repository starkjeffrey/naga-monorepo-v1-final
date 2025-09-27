/**
 * Standardized Component Patterns Index
 *
 * This file exports all standardized component patterns used throughout
 * the staff management system for consistent UI/UX.
 */

// Pattern 1: Enhanced DataGrid Pattern
export {
  default as DataGrid,
  DataGridToolbar,
  DataGridHeader,
  DataGridBody,
  DataGridPagination,
  useDataGrid,
  createColumn,
  createAction,
  createBulkAction,
  formatters,
  columnPresets,
  type DataGridColumn,
  type DataGridAction,
  type DataGridBulkAction,
  type DataGridProps,
  type DataGridRef,
  type DataGridState,
} from './DataGrid';

// Pattern 2: Enhanced TransferList Pattern
export {
  default as TransferList,
  TransferListPanel,
  TransferControls,
  useTransferList,
  createTransferItem,
  createTransferCategory,
  createTransferFilter,
  createValidationRule,
  validationRules,
  commonFilters,
  presets,
  transferListUtils,
  type TransferItem,
  type TransferListProps,
  type TransferListRef,
  type TransferCategory,
  type TransferOperation,
} from './TransferList';

// Pattern 3: Analytics Dashboard Pattern
export {
  default as Dashboard,
  type DashboardProps,
  type DashboardMetric,
  type DashboardWidget,
} from './Dashboard';

// Pattern 4: Multi-Step Workflow Wizard Pattern
export {
  default as Wizard,
  type WizardStep,
  type WizardProps,
} from './Wizard';

// Legacy exports for backward compatibility
export {
  DetailModal,
  InfoTab,
  TimelineTab,
  DocumentsTab,
  type DetailTab,
  type DetailAction,
  type DetailModalProps,
  type InfoTabProps,
  type TimelineTabProps,
  type DocumentsTabProps,
} from './DetailModal';