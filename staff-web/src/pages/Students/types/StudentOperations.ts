/**
 * Student Operations Type Definitions
 *
 * TypeScript interfaces for student bulk operations:
 * - Import/Export operations
 * - Mass updates and modifications
 * - Communication campaigns
 * - Progress tracking
 * - Error handling and validation
 */

// Import/Export Types

export interface ImportOperation {
  id: string;
  filename: string;
  fileSize: number;
  mimeType: string;
  status: ImportStatus;
  totalRows: number;
  processedRows: number;
  successfulRows: number;
  failedRows: number;
  validationErrors: ImportValidationError[];
  dataErrors: ImportDataError[];
  warnings: ImportWarning[];
  options: ImportOptions;
  mapping: FieldMapping;
  startTime: string;
  endTime?: string;
  duration?: number;
  createdBy: string;
  summary?: ImportSummary;
}

export type ImportStatus =
  | 'pending'
  | 'validating'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'paused';

export interface ImportOptions {
  skipDuplicates: boolean;
  updateExisting: boolean;
  validateOnly: boolean;
  sendNotifications: boolean;
  createAuditLog: boolean;
  batchSize: number;
  allowPartialSuccess: boolean;
  encoding: string;
  delimiter?: string;
  hasHeader: boolean;
  dateFormat: string;
  requireAllFields: boolean;
}

export interface FieldMapping {
  [fileField: string]: {
    targetField: string;
    transformer?: string;
    validator?: string;
    required: boolean;
    defaultValue?: any;
  };
}

export interface ImportValidationError {
  row: number;
  field: string;
  value: any;
  message: string;
  code: string;
  severity: 'error' | 'warning';
  suggestion?: string;
}

export interface ImportDataError {
  row: number;
  studentData: any;
  errors: Array<{
    field: string;
    message: string;
    code: string;
  }>;
  canRetry: boolean;
  suggestedFix?: any;
}

export interface ImportWarning {
  type: 'duplicate' | 'missing_field' | 'format' | 'validation' | 'business_rule';
  message: string;
  affectedRows: number[];
  suggestion?: string;
  autoFixed?: boolean;
}

export interface ImportSummary {
  newStudents: number;
  updatedStudents: number;
  skippedStudents: number;
  duplicatesFound: number;
  validationErrors: number;
  dataErrors: number;
  processingTime: number;
  throughput: number; // rows per second
  memoryUsage?: number;
  errorRate: number;
}

// Export Types

export interface ExportOperation {
  id: string;
  name: string;
  format: ExportFormat;
  status: ExportStatus;
  totalRecords: number;
  processedRecords: number;
  fileSize?: number;
  downloadUrl?: string;
  expiresAt?: string;
  options: ExportOptions;
  filters: ExportFilters;
  fields: ExportField[];
  startTime: string;
  endTime?: string;
  duration?: number;
  createdBy: string;
  downloadCount: number;
  lastDownloaded?: string;
}

export type ExportFormat = 'csv' | 'excel' | 'pdf' | 'json' | 'xml';

export type ExportStatus =
  | 'pending'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'expired'
  | 'cancelled';

export interface ExportOptions {
  includeHeaders: boolean;
  includePhotos: boolean;
  includeNotes: boolean;
  includeAlerts: boolean;
  includeHistory: boolean;
  compressionLevel?: number;
  passwordProtect?: boolean;
  watermark?: string;
  pageOrientation?: 'portrait' | 'landscape';
  dateFormat: string;
  encoding: string;
  delimiter?: string;
  escapeCharacter?: string;
  nullValue?: string;
}

export interface ExportFilters {
  studentIds?: string[];
  programs?: string[];
  statuses?: string[];
  academicYears?: string[];
  enrollmentDateRange?: {
    start: string;
    end: string;
  };
  gpaRange?: {
    min: number;
    max: number;
  };
  hasAlerts?: boolean;
  tags?: string[];
  customFilters?: Array<{
    field: string;
    operator: string;
    value: any;
  }>;
}

export interface ExportField {
  name: string;
  label: string;
  type: 'string' | 'number' | 'date' | 'boolean' | 'object' | 'array';
  required: boolean;
  formatter?: string;
  width?: number;
  alignment?: 'left' | 'center' | 'right';
  includeInSummary?: boolean;
}

// Bulk Update Types

export interface BulkUpdateOperation {
  id: string;
  type: BulkUpdateType;
  targetCount: number;
  processedCount: number;
  successCount: number;
  failureCount: number;
  status: BulkUpdateStatus;
  updates: BulkUpdateItem[];
  errors: BulkUpdateError[];
  options: BulkUpdateOptions;
  startTime: string;
  endTime?: string;
  duration?: number;
  createdBy: string;
  approvedBy?: string;
  rollbackAvailable: boolean;
  rollbackDeadline?: string;
}

export type BulkUpdateType =
  | 'status_change'
  | 'program_change'
  | 'academic_year_change'
  | 'tag_addition'
  | 'tag_removal'
  | 'contact_update'
  | 'financial_adjustment'
  | 'note_addition'
  | 'alert_addition'
  | 'alert_clearance'
  | 'custom_field_update';

export type BulkUpdateStatus =
  | 'pending_approval'
  | 'approved'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'rolled_back';

export interface BulkUpdateItem {
  studentId: string;
  originalValues: Record<string, any>;
  newValues: Record<string, any>;
  status: 'pending' | 'success' | 'failed' | 'skipped';
  errors?: string[];
  warnings?: string[];
  processedAt?: string;
}

export interface BulkUpdateError {
  studentId: string;
  field?: string;
  originalValue?: any;
  newValue?: any;
  message: string;
  code: string;
  severity: 'error' | 'warning';
  canRetry: boolean;
  requiresManualIntervention: boolean;
}

export interface BulkUpdateOptions {
  requireApproval: boolean;
  sendNotifications: boolean;
  createAuditLog: boolean;
  allowPartialSuccess: boolean;
  validateBeforeUpdate: boolean;
  batchSize: number;
  retryFailures: boolean;
  maxRetries: number;
  rollbackOnFailure: boolean;
  notificationTemplate?: string;
  customValidation?: string[];
}

// Communication Campaign Types

export interface CommunicationCampaign {
  id: string;
  name: string;
  type: CommunicationChannelType;
  status: CampaignStatus;
  subject?: string;
  content: string;
  htmlContent?: string;
  recipients: CampaignRecipient[];
  recipientCount: number;
  sentCount: number;
  deliveredCount: number;
  openedCount: number;
  clickedCount: number;
  failedCount: number;
  unsubscribedCount: number;
  bounceCount: number;
  scheduledDate?: string;
  sentDate?: string;
  completedDate?: string;
  template?: string;
  personalizations: CampaignPersonalization[];
  attachments: CampaignAttachment[];
  tracking: CampaignTracking;
  options: CampaignOptions;
  createdBy: string;
  approvedBy?: string;
  metrics?: CampaignMetrics;
}

export type CommunicationChannelType = 'email' | 'sms' | 'push' | 'in_app' | 'phone' | 'postal';

export type CampaignStatus =
  | 'draft'
  | 'scheduled'
  | 'sending'
  | 'sent'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'paused';

export interface CampaignRecipient {
  studentId: string;
  email?: string;
  phone?: string;
  preferredLanguage?: string;
  timezone?: string;
  personalizations?: Record<string, any>;
  status: RecipientStatus;
  sentAt?: string;
  deliveredAt?: string;
  openedAt?: string;
  clickedAt?: string;
  unsubscribedAt?: string;
  bounceReason?: string;
  error?: string;
}

export type RecipientStatus =
  | 'pending'
  | 'sent'
  | 'delivered'
  | 'opened'
  | 'clicked'
  | 'unsubscribed'
  | 'bounced'
  | 'failed';

export interface CampaignPersonalization {
  field: string;
  value: string;
  fallback?: string;
  formatter?: string;
}

export interface CampaignAttachment {
  id: string;
  filename: string;
  contentType: string;
  size: number;
  url?: string;
  isEmbedded: boolean;
}

export interface CampaignTracking {
  trackOpens: boolean;
  trackClicks: boolean;
  trackUnsubscribes: boolean;
  trackGeolocation: boolean;
  trackDeviceInfo: boolean;
  utmSource?: string;
  utmMedium?: string;
  utmCampaign?: string;
  customParameters?: Record<string, string>;
}

export interface CampaignOptions {
  sendInBatches: boolean;
  batchSize?: number;
  batchDelay?: number; // minutes between batches
  respectTimeZones: boolean;
  respectQuietHours: boolean;
  quietHoursStart?: string;
  quietHoursEnd?: string;
  maxRetries: number;
  retryDelay?: number; // minutes
  suppressDuplicates: boolean;
  requireOptIn: boolean;
  allowUnsubscribe: boolean;
  customHeaders?: Record<string, string>;
}

export interface CampaignMetrics {
  deliveryRate: number; // percentage
  openRate: number; // percentage
  clickRate: number; // percentage
  clickThroughRate: number; // percentage
  bounceRate: number; // percentage
  unsubscribeRate: number; // percentage
  engagementScore: number; // 0-100
  costPerDelivery?: number;
  costPerClick?: number;
  roi?: number;
  averageResponseTime?: number; // minutes
  peakEngagementTime?: string;
  deviceBreakdown?: Record<string, number>;
  locationBreakdown?: Record<string, number>;
}

// Progress Tracking Types

export interface OperationProgress {
  operationId: string;
  operationType: string;
  currentStep: string;
  totalSteps: number;
  completedSteps: number;
  progressPercentage: number;
  estimatedTimeRemaining?: number; // seconds
  currentItem?: string;
  itemsPerSecond?: number;
  startTime: string;
  lastUpdateTime: string;
  errors: ProgressError[];
  warnings: ProgressWarning[];
  metrics?: ProgressMetrics;
}

export interface ProgressError {
  timestamp: string;
  step: string;
  item?: string;
  message: string;
  code?: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  canContinue: boolean;
  retryable: boolean;
}

export interface ProgressWarning {
  timestamp: string;
  step: string;
  item?: string;
  message: string;
  code?: string;
  impact: 'none' | 'low' | 'medium' | 'high';
  suggestion?: string;
}

export interface ProgressMetrics {
  memoryUsage?: number; // MB
  cpuUsage?: number; // percentage
  diskUsage?: number; // MB
  networkUsage?: number; // KB/s
  cacheHitRate?: number; // percentage
  errorRate?: number; // percentage
  throughput?: number; // items per second
}

// Validation Types

export interface ValidationRule {
  field: string;
  type: ValidationType;
  required: boolean;
  constraints?: ValidationConstraints;
  errorMessage?: string;
  warningMessage?: string;
  dependencies?: string[]; // other fields this validation depends on
}

export type ValidationType =
  | 'required'
  | 'email'
  | 'phone'
  | 'date'
  | 'number'
  | 'string'
  | 'regex'
  | 'custom'
  | 'unique'
  | 'exists'
  | 'range'
  | 'length'
  | 'format';

export interface ValidationConstraints {
  minLength?: number;
  maxLength?: number;
  min?: number;
  max?: number;
  pattern?: string;
  allowedValues?: any[];
  customValidator?: string;
  format?: string;
  precision?: number;
  scale?: number;
}

export interface ValidationResult {
  isValid: boolean;
  errors: ValidationError[];
  warnings: ValidationWarning[];
  fieldResults: Record<string, FieldValidationResult>;
}

export interface ValidationError {
  field: string;
  value: any;
  message: string;
  code: string;
  constraint?: string;
  suggestion?: string;
}

export interface ValidationWarning {
  field: string;
  value: any;
  message: string;
  code: string;
  suggestion?: string;
}

export interface FieldValidationResult {
  isValid: boolean;
  value: any;
  normalizedValue?: any;
  errors: string[];
  warnings: string[];
  appliedTransformations?: string[];
}

// Audit and History Types

export interface AuditLog {
  id: string;
  operationType: string;
  operationId: string;
  targetType: 'student' | 'enrollment' | 'system';
  targetId?: string;
  action: string;
  changes: AuditChange[];
  metadata: AuditMetadata;
  timestamp: string;
  userId: string;
  userAgent?: string;
  ipAddress?: string;
  sessionId?: string;
}

export interface AuditChange {
  field: string;
  oldValue?: any;
  newValue?: any;
  changeType: 'create' | 'update' | 'delete' | 'archive';
}

export interface AuditMetadata {
  reason?: string;
  approvalRequired?: boolean;
  approvedBy?: string;
  approvedAt?: string;
  source: 'web' | 'api' | 'import' | 'system' | 'mobile';
  bulkOperationId?: string;
  parentOperationId?: string;
  correlationId?: string;
  additionalContext?: Record<string, any>;
}

// Rollback Types

export interface RollbackOperation {
  id: string;
  originalOperationId: string;
  operationType: string;
  targetRecords: string[];
  status: RollbackStatus;
  rollbackPlan: RollbackAction[];
  executedActions: RollbackAction[];
  failedActions: RollbackAction[];
  startTime: string;
  endTime?: string;
  createdBy: string;
  reason: string;
  requiresApproval: boolean;
  approvedBy?: string;
  approvedAt?: string;
}

export type RollbackStatus =
  | 'pending'
  | 'pending_approval'
  | 'approved'
  | 'executing'
  | 'completed'
  | 'failed'
  | 'cancelled';

export interface RollbackAction {
  id: string;
  type: 'restore_field' | 'delete_record' | 'restore_record' | 'run_script';
  targetId: string;
  targetType: string;
  field?: string;
  originalValue?: any;
  currentValue?: any;
  status: 'pending' | 'success' | 'failed' | 'skipped';
  error?: string;
  executedAt?: string;
  dependsOn?: string[]; // other action IDs
}

// Notification Types

export interface OperationNotification {
  id: string;
  operationId: string;
  type: NotificationType;
  recipients: NotificationRecipient[];
  subject: string;
  content: string;
  priority: NotificationPriority;
  status: NotificationStatus;
  scheduledAt?: string;
  sentAt?: string;
  template?: string;
  data?: Record<string, any>;
}

export type NotificationType =
  | 'operation_started'
  | 'operation_completed'
  | 'operation_failed'
  | 'approval_required'
  | 'error_occurred'
  | 'warning_issued'
  | 'milestone_reached';

export type NotificationPriority = 'low' | 'normal' | 'high' | 'urgent';

export type NotificationStatus =
  | 'pending'
  | 'sent'
  | 'delivered'
  | 'failed'
  | 'cancelled';

export interface NotificationRecipient {
  type: 'user' | 'role' | 'email';
  identifier: string;
  channel: 'email' | 'sms' | 'push' | 'in_app';
  status: RecipientStatus;
  sentAt?: string;
  deliveredAt?: string;
  error?: string;
}

// Export all types for external use
export type {
  // Import/Export
  ImportOperation,
  ImportStatus,
  ImportOptions,
  ExportOperation,
  ExportFormat,
  ExportStatus,

  // Bulk Updates
  BulkUpdateOperation,
  BulkUpdateType,
  BulkUpdateStatus,

  // Communication
  CommunicationCampaign,
  CommunicationChannelType,
  CampaignStatus,

  // Progress and Validation
  OperationProgress,
  ValidationRule,
  ValidationResult,

  // Audit and Rollback
  AuditLog,
  RollbackOperation,
  RollbackStatus,

  // Notifications
  OperationNotification,
  NotificationType,
};