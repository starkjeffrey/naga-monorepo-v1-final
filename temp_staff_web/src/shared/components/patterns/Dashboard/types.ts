/**
 * Analytics Dashboard Types
 * Complete type definitions for the analytics dashboard pattern
 */

export interface DashboardMetric {
  id: string;
  title: string;
  value: number | string;
  previousValue?: number | string;
  change?: number;
  changeType?: 'increase' | 'decrease' | 'neutral';
  unit?: string;
  format?: 'number' | 'currency' | 'percentage' | 'duration';
  icon?: React.ReactNode;
  color?: string;
  target?: number;
  threshold?: {
    warning: number;
    critical: number;
  };
  trend?: {
    data: number[];
    period: string;
  };
  description?: string;
  lastUpdated?: Date;
}

export interface ChartDataPoint {
  x: string | number | Date;
  y: number;
  label?: string;
  color?: string;
  metadata?: Record<string, any>;
}

export interface ChartSeries {
  id: string;
  label: string;
  data: ChartDataPoint[];
  color?: string;
  type?: 'line' | 'bar' | 'area' | 'scatter';
  yAxis?: 'left' | 'right';
}

export interface ChartWidget {
  id: string;
  title: string;
  type: 'line' | 'bar' | 'pie' | 'doughnut' | 'area' | 'scatter' | 'heatmap' | 'gauge';
  series: ChartSeries[];
  options?: {
    height?: number;
    responsive?: boolean;
    legend?: boolean;
    tooltip?: boolean;
    grid?: boolean;
    zoom?: boolean;
    brush?: boolean;
    animation?: boolean;
    xAxis?: {
      title?: string;
      type?: 'category' | 'time' | 'numeric';
      format?: string;
    };
    yAxis?: {
      title?: string;
      min?: number;
      max?: number;
      format?: string;
    };
    colors?: string[];
    annotations?: Array<{
      type: 'line' | 'box' | 'point';
      value: number | string;
      label?: string;
      color?: string;
    }>;
  };
  loading?: boolean;
  error?: string;
  lastUpdated?: Date;
  refreshInterval?: number;
}

export interface ListItem {
  id: string | number;
  primary: string;
  secondary?: string;
  tertiary?: string;
  value?: number | string;
  change?: number;
  changeType?: 'increase' | 'decrease' | 'neutral';
  icon?: React.ReactNode;
  avatar?: string;
  status?: 'active' | 'inactive' | 'pending' | 'error';
  actions?: Array<{
    id: string;
    label: string;
    icon?: React.ReactNode;
    onClick: () => void;
  }>;
  metadata?: Record<string, any>;
}

export interface ListWidget {
  id: string;
  title: string;
  items: ListItem[];
  showMore?: {
    label: string;
    onClick: () => void;
  };
  emptyState?: {
    title: string;
    description: string;
    action?: {
      label: string;
      onClick: () => void;
    };
  };
  loading?: boolean;
  error?: string;
  lastUpdated?: Date;
  refreshInterval?: number;
}

export interface ActivityItem {
  id: string;
  type: 'user_action' | 'system_event' | 'notification' | 'alert';
  title: string;
  description?: string;
  timestamp: Date;
  user?: {
    id: string;
    name: string;
    avatar?: string;
  };
  severity?: 'low' | 'medium' | 'high' | 'critical';
  status?: 'pending' | 'completed' | 'failed';
  metadata?: Record<string, any>;
}

export interface ActivityWidget {
  id: string;
  title: string;
  items: ActivityItem[];
  filters?: Array<{
    id: string;
    label: string;
    type: 'all' | 'user_action' | 'system_event' | 'notification' | 'alert';
  }>;
  showMore?: {
    label: string;
    onClick: () => void;
  };
  loading?: boolean;
  error?: string;
  refreshInterval?: number;
}

export interface DashboardWidget {
  id: string;
  type: 'metric' | 'chart' | 'list' | 'activity' | 'custom';
  title: string;
  size: 'small' | 'medium' | 'large' | 'full';
  position: {
    x: number;
    y: number;
    w: number;
    h: number;
  };
  data: DashboardMetric | ChartWidget | ListWidget | ActivityWidget | any;
  refreshInterval?: number;
  autoRefresh?: boolean;
  loading?: boolean;
  error?: string;
  lastUpdated?: Date;
  permissions?: string[];
  visible?: boolean;
  minimized?: boolean;
}

export interface DashboardLayout {
  id: string;
  name: string;
  description?: string;
  widgets: DashboardWidget[];
  columns: number;
  rowHeight: number;
  breakpoints?: {
    lg: number;
    md: number;
    sm: number;
    xs: number;
  };
  margin?: [number, number];
  padding?: [number, number];
  isDefault?: boolean;
  isShared?: boolean;
  createdBy?: string;
  createdAt?: Date;
  updatedAt?: Date;
}

export interface DashboardFilter {
  id: string;
  label: string;
  type: 'date' | 'select' | 'multiSelect' | 'text' | 'number';
  value: any;
  options?: Array<{ label: string; value: any }>;
  required?: boolean;
  global?: boolean; // Applies to all widgets
}

export interface DashboardState {
  layout: DashboardLayout;
  filters: DashboardFilter[];
  timeRange: {
    start: Date;
    end: Date;
    preset?: 'today' | 'yesterday' | 'last7days' | 'last30days' | 'last90days' | 'custom';
  };
  autoRefresh: boolean;
  refreshInterval: number;
  isEditing: boolean;
  selectedWidgets: Set<string>;
  widgetData: Record<string, any>;
  loading: boolean;
  error?: string;
  lastUpdated?: Date;
}

export interface DashboardProps {
  // Layout
  layoutId?: string;
  layouts?: DashboardLayout[];
  onLayoutChange?: (layout: DashboardLayout) => void;
  onLayoutSave?: (layout: Omit<DashboardLayout, 'id' | 'createdAt' | 'updatedAt'>) => void;
  onLayoutDelete?: (layoutId: string) => void;

  // Widgets
  widgets?: DashboardWidget[];
  onWidgetAdd?: (widget: Omit<DashboardWidget, 'id'>) => void;
  onWidgetUpdate?: (widgetId: string, updates: Partial<DashboardWidget>) => void;
  onWidgetDelete?: (widgetId: string) => void;

  // Data
  onDataFetch?: (widgetId: string, filters: DashboardFilter[]) => Promise<any>;
  onDataRefresh?: () => void;

  // Filters
  filters?: DashboardFilter[];
  onFilterChange?: (filters: DashboardFilter[]) => void;

  // Time range
  timeRange?: DashboardState['timeRange'];
  onTimeRangeChange?: (timeRange: DashboardState['timeRange']) => void;

  // Real-time updates
  realTime?: boolean;
  websocketUrl?: string;
  onRealtimeData?: (widgetId: string, data: any) => void;

  // Export
  exportable?: boolean;
  onExport?: (format: 'png' | 'pdf' | 'json') => void;

  // Sharing
  shareable?: boolean;
  onShare?: (shareConfig: { public: boolean; permissions: string[] }) => void;

  // Customization
  editable?: boolean;
  customizable?: boolean;
  allowWidgetResize?: boolean;
  allowWidgetReorder?: boolean;

  // Performance
  virtualScrolling?: boolean;
  lazyLoading?: boolean;
  cacheEnabled?: boolean;
  cacheTtl?: number;

  // Styling
  theme?: 'light' | 'dark' | 'auto';
  compact?: boolean;
  className?: string;

  // Accessibility
  ariaLabel?: string;
  ariaDescribedBy?: string;
}

export interface DashboardRef {
  // Layout management
  saveLayout: (name: string, description?: string) => void;
  loadLayout: (layoutId: string) => void;
  resetLayout: () => void;
  exportLayout: () => DashboardLayout;
  importLayout: (layout: DashboardLayout) => void;

  // Widget management
  addWidget: (widget: Omit<DashboardWidget, 'id'>) => void;
  updateWidget: (widgetId: string, updates: Partial<DashboardWidget>) => void;
  removeWidget: (widgetId: string) => void;
  duplicateWidget: (widgetId: string) => void;

  // Data management
  refreshWidget: (widgetId: string) => void;
  refreshAll: () => void;
  clearCache: () => void;

  // Filters
  setFilter: (filterId: string, value: any) => void;
  clearFilters: () => void;
  applyFilters: (filters: DashboardFilter[]) => void;

  // Time range
  setTimeRange: (timeRange: DashboardState['timeRange']) => void;
  setTimePreset: (preset: DashboardState['timeRange']['preset']) => void;

  // View modes
  enterEditMode: () => void;
  exitEditMode: () => void;
  toggleFullscreen: (widgetId?: string) => void;

  // Export
  exportDashboard: (format: 'png' | 'pdf' | 'json') => void;
  exportWidget: (widgetId: string, format: 'png' | 'pdf' | 'json') => void;

  // State
  getState: () => DashboardState;
  setState: (state: Partial<DashboardState>) => void;
}

// Hook return types
export interface UseDashboardReturn {
  state: DashboardState;
  actions: {
    // Layout
    setLayout: (layout: DashboardLayout) => void;
    updateLayout: (updates: Partial<DashboardLayout>) => void;

    // Widgets
    addWidget: (widget: Omit<DashboardWidget, 'id'>) => void;
    updateWidget: (widgetId: string, updates: Partial<DashboardWidget>) => void;
    removeWidget: (widgetId: string) => void;
    moveWidget: (widgetId: string, position: DashboardWidget['position']) => void;
    resizeWidget: (widgetId: string, size: { w: number; h: number }) => void;

    // Data
    setWidgetData: (widgetId: string, data: any) => void;
    setWidgetLoading: (widgetId: string, loading: boolean) => void;
    setWidgetError: (widgetId: string, error: string | undefined) => void;
    refreshWidget: (widgetId: string) => void;
    refreshAll: () => void;

    // Filters
    setFilters: (filters: DashboardFilter[]) => void;
    updateFilter: (filterId: string, value: any) => void;
    clearFilters: () => void;

    // Time range
    setTimeRange: (timeRange: DashboardState['timeRange']) => void;

    // UI state
    setEditing: (editing: boolean) => void;
    toggleAutoRefresh: () => void;
    setRefreshInterval: (interval: number) => void;
    selectWidget: (widgetId: string) => void;
    deselectWidget: (widgetId: string) => void;
    clearSelection: () => void;

    // Global state
    setLoading: (loading: boolean) => void;
    setError: (error: string | undefined) => void;
    reset: () => void;
  };
  computed: {
    visibleWidgets: DashboardWidget[];
    selectedWidgetsData: DashboardWidget[];
    hasSelection: boolean;
    canSave: boolean;
    needsRefresh: boolean;
    totalWidgets: number;
    loadingWidgets: string[];
    errorWidgets: string[];
  };
}

// Event types
export interface DashboardWidgetEvent {
  widgetId: string;
  widget: DashboardWidget;
  event: React.MouseEvent | React.KeyboardEvent;
}

export interface DashboardLayoutEvent {
  layout: DashboardLayout;
  changes: Partial<DashboardLayout>;
}

export interface DashboardFilterEvent {
  filters: DashboardFilter[];
  changedFilter: DashboardFilter;
}

// WebSocket message types for real-time updates
export interface RealtimeMessage {
  type: 'widget_update' | 'metric_update' | 'alert' | 'notification';
  widgetId?: string;
  data: any;
  timestamp: Date;
}

// Widget configuration types
export interface WidgetConfig {
  type: DashboardWidget['type'];
  title: string;
  size: DashboardWidget['size'];
  dataSource: {
    url?: string;
    method?: 'GET' | 'POST';
    params?: Record<string, any>;
    headers?: Record<string, string>;
    transform?: (data: any) => any;
  };
  refreshInterval?: number;
  filters?: string[]; // Filter IDs that affect this widget
}

// Performance optimization types
export interface DashboardPerformanceOptions {
  virtualScrolling: boolean;
  lazyLoading: boolean;
  debounceMs: number;
  maxConcurrentRequests: number;
  cacheStrategy: 'memory' | 'localStorage' | 'sessionStorage' | 'none';
  cacheTtl: number;
  preloadStrategy: 'none' | 'viewport' | 'all';
}