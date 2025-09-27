/**
 * Student Management Types Index
 *
 * Centralized export for all TypeScript type definitions
 * in the Student Management module.
 */

// Core Student Types
export type {
  Student,
  StudentStatus,
  EmergencyContact,
  StudentNote,
  StudentAlert,
  AlertType,
  AlertSeverity,
  StudentFormData,
  StudentUpdateData,
} from './Student';

// Search and Analytics Types
export type {
  StudentSearchParams,
  StudentSearchResult,
  StudentFilters,
  StudentSorting,
  StudentPagination,
  DateRange,
  NumberRange,
  SearchFacet,
  SearchAggregations,
  StudentAnalytics,
  StudentMetrics,
  AcademicMetrics,
  EngagementMetrics,
  FinancialMetrics,
  AttendanceMetrics,
  StudentTrends,
  TrendData,
  StudentComparisons,
  CohortComparison,
  StudentInsight,
  StudentPrediction,
  GPAProjection,
  TimeToGraduation,
  RiskFactor,
  Intervention,
  StudentRiskAssessment,
  RiskLevel,
  RiskFactorDetail,
  MitigationStrategy,
  EarlyWarningIndicator,
} from './Student';

// Event and Communication Types
export type {
  StudentEvent,
  StudentEventType,
  StudentStatistics,
  EnrollmentStatistics,
  AlertStatistics,
  AnalyticsTimeframe,
  AnalyticsMetric,
  CommunicationLog,
  ApiResponse,
  PaginatedResponse,
  ErrorResponse,
} from './Student';

// Enrollment Types
export type {
  Enrollment,
  EnrollmentStatus,
  Grade,
  Course,
  Prerequisite,
  Corequisite,
  CourseRestriction,
  CourseAttribute,
  Textbook,
  Class,
  ClassSchedule,
  DayOfWeek,
  ClassFormat,
  ClassFee,
  EnrollmentRequest,
  EnrollmentResponse,
  EnrollmentWarning,
  EnrollmentError,
  WithdrawalRequest,
  WithdrawalResponse,
  AcademicImpact,
  TransferListItem,
  TransferListOperation,
  TransferOptions,
  TransferListValidation,
  StudentSchedule,
  ScheduleEnrollment,
  ScheduleConflict,
  ScheduleGap,
  ScheduleSummary,
  WaitlistEntry,
  WaitlistNotification,
  PrerequisiteValidation,
  MissingRequirement,
  CompletedRequirement,
  InProgressRequirement,
  AlternativePathway,
  CapacityInfo,
  RegistrationPeriod,
  RegistrationEligibility,
  RegistrationRestriction,
  BulkEnrollmentRequest,
  BulkEnrollmentOptions,
  BulkEnrollmentResult,
  BulkEnrollmentItemResult,
  AcademicPlan,
  PlannedSemester,
  PlannedCourse,
  AcademicMilestone,
} from './Enrollment';

// Operations Types
export type {
  ImportOperation,
  ImportStatus,
  ImportOptions,
  FieldMapping,
  ImportValidationError,
  ImportDataError,
  ImportWarning,
  ImportSummary,
  ExportOperation,
  ExportFormat,
  ExportStatus,
  ExportOptions as OperationExportOptions,
  ExportFilters,
  ExportField,
  BulkUpdateOperation,
  BulkUpdateType,
  BulkUpdateStatus,
  BulkUpdateItem,
  BulkUpdateError,
  BulkUpdateOptions,
  CommunicationCampaign,
  CommunicationChannelType,
  CampaignStatus,
  CampaignRecipient,
  RecipientStatus,
  CampaignPersonalization,
  CampaignAttachment,
  CampaignTracking,
  CampaignOptions,
  CampaignMetrics,
  OperationProgress,
  ProgressError,
  ProgressWarning,
  ProgressMetrics,
  ValidationRule,
  ValidationType,
  ValidationConstraints,
  ValidationResult,
  ValidationError,
  ValidationWarning,
  FieldValidationResult,
  AuditLog,
  AuditChange,
  AuditMetadata,
  RollbackOperation,
  RollbackStatus,
  RollbackAction,
  OperationNotification,
  NotificationType,
  NotificationPriority,
  NotificationStatus,
  NotificationRecipient,
} from './StudentOperations';

// Common utility types
export interface StudentModuleConfig {
  enableRealTimeUpdates: boolean;
  enablePredictiveAnalytics: boolean;
  enableBulkOperations: boolean;
  enableAdvancedSearch: boolean;
  enablePhotoRecognition: boolean;
  enableOCR: boolean;
  enableAuditLogging: boolean;
  maxBulkOperationSize: number;
  defaultPageSize: number;
  maxExportSize: number;
  sessionTimeoutMinutes: number;
  autoSaveIntervalSeconds: number;
}

export interface StudentModulePermissions {
  canView: boolean;
  canCreate: boolean;
  canUpdate: boolean;
  canDelete: boolean;
  canExport: boolean;
  canImport: boolean;
  canBulkUpdate: boolean;
  canViewAnalytics: boolean;
  canViewPredictions: boolean;
  canManageAlerts: boolean;
  canAccessAuditLog: boolean;
  canApproveOperations: boolean;
  canRollbackOperations: boolean;
  canViewSensitiveData: boolean;
  canOverrideRestrictions: boolean;
}

export interface StudentModuleFeatures {
  advancedSearch: boolean;
  voiceSearch: boolean;
  photoSearch: boolean;
  qrScanner: boolean;
  realTimeUpdates: boolean;
  predictiveAnalytics: boolean;
  riskAssessment: boolean;
  bulkOperations: boolean;
  communicationCampaigns: boolean;
  documentOCR: boolean;
  photoManagement: boolean;
  auditTrail: boolean;
  rollbackSupport: boolean;
  workflowAutomation: boolean;
  mobileSupport: boolean;
}

// Re-export commonly used types for convenience
export type {
  ExportOptions,
  BulkOperationResult,
  ImportResult,
} from './Student';