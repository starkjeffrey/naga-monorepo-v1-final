/**
 * Standardized Component Patterns Index
 *
 * This file exports all standardized component patterns used throughout
 * the student management system for consistent UI/UX.
 */

// Enhanced DataGrid Pattern
export {
  EnhancedDataGrid,
  type DataGridColumn,
  type DataGridAction,
  type DataGridFilters,
  type DataGridProps,
} from './EnhancedDataGrid';

// Detail Modal Pattern
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

// Wizard Pattern
export {
  Wizard,
  type WizardStep,
  type WizardProps,
} from './Wizard';

// Dashboard Pattern
export {
  Dashboard,
  type MetricCard,
  type ChartWidget,
  type ListWidget,
  type Filter,
  type DashboardProps,
} from './Dashboard';

// Re-export TransferList from existing components (already implemented)
export {
  TransferList,
  type TransferItem,
  type TransferListProps,
} from '../TransferList';