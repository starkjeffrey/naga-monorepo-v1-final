/**
 * Student Type Definitions
 *
 * Comprehensive TypeScript interfaces for the Student Management module:
 * - Core student data structures
 * - Search and filtering types
 * - Analytics and reporting types
 * - Bulk operations types
 * - API response types
 */

// Core Student Types

export interface Student {
  id: string;
  studentId: string;
  firstName: string;
  lastName: string;
  fullName: string;
  email: string;
  phone?: string;
  dateOfBirth?: string;
  gender?: 'male' | 'female' | 'other' | 'prefer_not_to_say';
  nationality?: string;

  // Address Information
  address?: string;
  city?: string;
  state?: string;
  postalCode?: string;
  country?: string;

  // Academic Information
  program: string;
  academicYear: string;
  enrollmentDate: string;
  status: StudentStatus;
  gpa?: number;
  creditsCompleted?: number;
  creditsRequired?: number;

  // Contact Information
  emergencyContact?: EmergencyContact;

  // System Information
  photoUrl?: string;
  hasAlerts: boolean;
  tags?: string[];
  notes?: StudentNote[];
  alerts?: StudentAlert[];

  // Metadata
  createdAt: string;
  updatedAt: string;
  createdBy?: string;
  updatedBy?: string;
}

export type StudentStatus =
  | 'active'
  | 'inactive'
  | 'graduated'
  | 'suspended'
  | 'transferred'
  | 'pending'
  | 'withdrawn';

export interface EmergencyContact {
  name: string;
  relationship: string;
  phone: string;
  email?: string;
  address?: string;
}

export interface StudentNote {
  id: string;
  content: string;
  author: string;
  timestamp: string;
  isPrivate?: boolean;
  category?: string;
}

export interface StudentAlert {
  id: string;
  type: AlertType;
  severity: AlertSeverity;
  message: string;
  details?: string;
  createdAt: string;
  resolvedAt?: string;
  resolvedBy?: string;
  isActive: boolean;
}

export type AlertType =
  | 'academic'
  | 'financial'
  | 'attendance'
  | 'behavioral'
  | 'system'
  | 'health'
  | 'communication';

export type AlertSeverity = 'low' | 'medium' | 'high' | 'critical';

// Form Types

export interface StudentFormData {
  studentId: string;
  firstName: string;
  lastName: string;
  email: string;
  phone?: string;
  dateOfBirth?: string;
  gender?: string;
  nationality?: string;
  address?: string;
  city?: string;
  state?: string;
  postalCode?: string;
  country?: string;
  program: string;
  academicYear: string;
  enrollmentDate: string;
  status: StudentStatus;
  gpa?: number;
  creditsCompleted?: number;
  emergencyContact?: EmergencyContact;
  notes?: string;
  hasAlerts?: boolean;
  tags?: string[];
  photoFile?: File;
}

export interface StudentUpdateData extends Partial<Omit<StudentFormData, 'studentId'>> {
  // Additional fields that can be updated but not created
  lastLoginAt?: string;
  passwordResetRequired?: boolean;
}

// Search Types

export interface StudentSearchParams {
  id?: string;
  query?: string;
  filters: StudentFilters;
  sorting: StudentSorting;
  pagination: StudentPagination;
  facets?: string[];
  includeInactive?: boolean;
}

export interface StudentFilters {
  status?: StudentStatus[];
  program?: string[];
  academicYear?: string[];
  enrollmentDateRange?: DateRange;
  gpaRange?: NumberRange;
  hasAlerts?: boolean;
  tags?: string[];
  country?: string[];
  alertTypes?: AlertType[];
  createdDateRange?: DateRange;
}

export interface StudentSorting {
  field: StudentSortField;
  direction: 'asc' | 'desc';
}

export type StudentSortField =
  | 'fullName'
  | 'studentId'
  | 'email'
  | 'status'
  | 'program'
  | 'academicYear'
  | 'enrollmentDate'
  | 'gpa'
  | 'creditsCompleted'
  | 'createdAt'
  | 'updatedAt';

export interface StudentPagination {
  page: number;
  pageSize: number;
}

export interface DateRange {
  start: string;
  end: string;
}

export interface NumberRange {
  min: number;
  max: number;
}

export interface StudentSearchResult {
  students: Student[];
  total: number;
  page: number;
  pageSize: number;
  suggestions?: string[];
  facets?: SearchFacet[];
  aggregations?: SearchAggregations;
}

export interface SearchFacet {
  field: string;
  values: Array<{
    value: string;
    count: number;
    selected?: boolean;
  }>;
}

export interface SearchAggregations {
  totalStudents: number;
  activeStudents: number;
  programBreakdown: Record<string, number>;
  statusBreakdown: Record<string, number>;
  averageGPA: number;
  alertCounts: Record<AlertType, number>;
}

// Analytics Types

export interface StudentAnalytics {
  metrics: StudentMetrics;
  trends: StudentTrends;
  comparisons?: StudentComparisons;
  insights?: StudentInsight[];
}

export interface StudentMetrics {
  academicPerformance: AcademicMetrics;
  engagement: EngagementMetrics;
  financial: FinancialMetrics;
  attendance: AttendanceMetrics;
}

export interface AcademicMetrics {
  currentGPA: number;
  creditsCompleted: number;
  creditsRequired: number;
  averageGrade: number;
  coursesInProgress: number;
  coursesCompleted: number;
  coursesDropped: number;
}

export interface EngagementMetrics {
  loginFrequency: number; // logins per week
  assignmentSubmissionRate: number; // percentage
  forumParticipation: number; // posts per week
  libraryUsage: number; // visits per month
  onlineTimeDaily: number; // minutes per day
}

export interface FinancialMetrics {
  totalTuition: number;
  amountPaid: number;
  balance: number;
  scholarships: number;
  paymentHistory: PaymentRecord[];
}

export interface AttendanceMetrics {
  attendanceRate: number; // percentage
  absences: number;
  tardiness: number;
  excusedAbsences: number;
}

export interface PaymentRecord {
  id: string;
  amount: number;
  date: string;
  method: string;
  status: 'completed' | 'pending' | 'failed';
  reference: string;
}

export interface StudentTrends {
  gpa: TrendData;
  attendance: TrendData;
  engagement: TrendData;
  credits: TrendData;
}

export interface TrendData {
  current: number;
  previous: number;
  change: number;
  changePercent: number;
  direction: 'up' | 'down' | 'stable';
  history: Array<{ period: string; value: number }>;
}

export interface StudentComparisons {
  cohort: CohortComparison;
  program: ProgramComparison;
  historical: HistoricalComparison;
}

export interface CohortComparison {
  percentile: number;
  rank: number;
  totalStudents: number;
  averageGPA: number;
  averageAttendance: number;
}

export interface ProgramComparison {
  programAverage: number;
  studentValue: number;
  programRank: number;
  totalInProgram: number;
}

export interface HistoricalComparison {
  previousSemester: number;
  previousYear: number;
  trend: 'improving' | 'declining' | 'stable';
}

export interface StudentInsight {
  type: 'recommendation' | 'warning' | 'achievement' | 'prediction';
  priority: 'low' | 'medium' | 'high';
  title: string;
  description: string;
  actionRequired?: boolean;
  suggestedActions?: string[];
  confidence: number; // 0-1
}

// Prediction Types

export interface StudentPrediction {
  graduationProbability: number;
  gpaProjection: GPAProjection;
  timeToGraduation: TimeToGraduation;
  riskFactors: RiskFactor[];
  recommendedInterventions: Intervention[];
  confidenceScore: number;
  lastUpdated: string;
}

export interface GPAProjection {
  projected: number;
  confidence: number;
  factors: string[];
  timeline: Array<{ semester: string; projected: number }>;
}

export interface TimeToGraduation {
  estimatedSemesters: number;
  estimatedDate: string;
  onTrack: boolean;
  delayFactors?: string[];
}

export interface RiskFactor {
  type: 'academic' | 'financial' | 'engagement' | 'attendance';
  severity: 'low' | 'medium' | 'high';
  description: string;
  impact: string;
  trend: 'improving' | 'worsening' | 'stable';
}

export interface Intervention {
  type: 'academic_support' | 'financial_aid' | 'counseling' | 'tutoring';
  priority: 'low' | 'medium' | 'high';
  title: string;
  description: string;
  estimatedImpact: string;
  resources: string[];
}

// Risk Assessment Types

export interface StudentRiskAssessment {
  overallRisk: RiskLevel;
  riskFactors: RiskFactorDetail[];
  mitigationStrategies: MitigationStrategy[];
  earlyWarningIndicators: EarlyWarningIndicator[];
  riskScore: number; // 0-100
  lastAssessment: string;
  nextAssessment: string;
}

export type RiskLevel = 'low' | 'moderate' | 'high' | 'critical';

export interface RiskFactorDetail {
  category: 'academic' | 'financial' | 'personal' | 'institutional';
  factor: string;
  weight: number;
  currentValue: number;
  threshold: number;
  trend: 'improving' | 'stable' | 'declining';
  evidencePoints: string[];
}

export interface MitigationStrategy {
  id: string;
  title: string;
  description: string;
  targetRiskFactors: string[];
  estimatedEffectiveness: number;
  timeframe: string;
  requiredResources: string[];
  responsibleParty: string;
  status: 'recommended' | 'in_progress' | 'completed';
}

export interface EarlyWarningIndicator {
  indicator: string;
  threshold: number;
  currentValue: number;
  severity: AlertSeverity;
  triggered: boolean;
  triggeredDate?: string;
  description: string;
}

// Enrollment Types

export interface StudentEnrollment {
  id: string;
  studentId: string;
  courseId: string;
  classHeaderId: string;
  status: EnrollmentStatus;
  enrollmentDate: string;
  completionDate?: string;
  withdrawalDate?: string;
  withdrawalReason?: string;
  grade?: string;
  gradePoints?: number;
  credits: number;
  isActive: boolean;
}

export type EnrollmentStatus =
  | 'enrolled'
  | 'waitlisted'
  | 'dropped'
  | 'completed'
  | 'failed'
  | 'withdrawn'
  | 'incomplete';

export interface CourseInfo {
  id: string;
  code: string;
  name: string;
  description: string;
  credits: number;
  department: string;
  level: string;
  prerequisites: string[];
  corequisites: string[];
}

export interface ClassHeader {
  id: string;
  courseId: string;
  section: string;
  term: string;
  capacity: number;
  enrolled: number;
  waitlisted: number;
  instructor: InstructorInfo;
  schedule: ClassSchedule[];
  room?: string;
  isActive: boolean;
}

export interface InstructorInfo {
  id: string;
  name: string;
  email: string;
  department: string;
}

export interface ClassSchedule {
  day: string;
  startTime: string;
  endTime: string;
  location?: string;
  building?: string;
  room?: string;
}

// Bulk Operations Types

export interface BulkOperation {
  id: string;
  type: BulkOperationType;
  status: BulkOperationStatus;
  description: string;
  itemCount: number;
  processedCount?: number;
  successfulCount?: number;
  failedCount?: number;
  startTime: Date;
  endTime?: Date;
  estimatedDuration?: number;
  progress?: number;
  errors?: BulkOperationError[];
  createdBy?: string;
}

export type BulkOperationType =
  | 'import'
  | 'export'
  | 'export_all'
  | 'status_update'
  | 'program_update'
  | 'tag_update'
  | 'bulk_email'
  | 'bulk_sms'
  | 'bulk_enroll'
  | 'bulk_withdraw'
  | 'bulk_transfer'
  | 'data_migration'
  | 'bulk_delete';

export type BulkOperationStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'paused';

export interface BulkOperationError {
  itemId?: string;
  itemIdentifier?: string;
  field?: string;
  message: string;
  code?: string;
  line?: number;
}

export interface BulkOperationResult {
  successful: number;
  failed: number;
  errors: BulkOperationError[];
  warnings: string[];
  summary?: string;
  processedAt: Date;
}

export interface ImportResult extends BulkOperationResult {
  duplicatesFound: number;
  duplicatesSkipped: number;
  newRecords: number;
  updatedRecords: number;
  validationErrors: ValidationError[];
}

export interface ValidationError {
  row: number;
  field: string;
  value: any;
  message: string;
  suggestion?: string;
}

export interface ExportOptions {
  format: 'csv' | 'excel' | 'pdf' | 'json';
  includeHeaders: boolean;
  fields: string[];
  filters?: StudentFilters;
  groupBy?: string;
  includePhotos: boolean;
  includeNotes: boolean;
  includeAlerts: boolean;
  dateFormat?: string;
  encoding?: string;
}

// Communication Types

export interface CommunicationCampaign {
  id?: string;
  name: string;
  subject: string;
  content: string;
  type: 'email' | 'sms' | 'push' | 'in_app';
  recipientIds: string[];
  recipientFilters?: StudentFilters;
  scheduledDate?: string;
  attachments?: File[];
  personalizeContent: boolean;
  trackDelivery: boolean;
  trackOpens: boolean;
  trackClicks: boolean;
  template?: string;
  variables?: Record<string, any>;
}

export interface CommunicationLog {
  id: string;
  campaignId?: string;
  studentId: string;
  type: 'email' | 'sms' | 'phone' | 'meeting' | 'note';
  subject?: string;
  content: string;
  sentAt: string;
  deliveredAt?: string;
  openedAt?: string;
  clickedAt?: string;
  status: 'sent' | 'delivered' | 'opened' | 'clicked' | 'failed' | 'bounced';
  error?: string;
  sentBy: string;
}

// Event Types

export interface StudentEvent {
  id: string;
  studentId: string;
  type: StudentEventType;
  title: string;
  description: string;
  details?: any;
  timestamp: string;
  category?: string;
  priority?: 'low' | 'medium' | 'high';
  status?: 'pending' | 'completed' | 'failed';
  actor?: {
    id: string;
    name: string;
    avatar?: string;
  };
  attachments?: Array<{
    name: string;
    url: string;
    type: string;
  }>;
  automated?: boolean;
}

export type StudentEventType =
  | 'enrollment'
  | 'academic'
  | 'financial'
  | 'communication'
  | 'document'
  | 'payment'
  | 'graduation'
  | 'alert'
  | 'call'
  | 'email'
  | 'edit'
  | 'achievement'
  | 'grade'
  | 'warning'
  | 'attendance'
  | 'disciplinary';

// Statistics Types

export interface StudentStatistics {
  academicPerformance: AcademicMetrics;
  enrollment: EnrollmentStatistics;
  financial: FinancialMetrics;
  engagement: EngagementMetrics;
  alerts: AlertStatistics;
  trends?: StudentTrends;
}

export interface EnrollmentStatistics {
  currentCourses: number;
  completedCourses: number;
  droppedCourses: number;
  totalCredits: number;
  creditsInProgress: number;
  waitlistedCourses: number;
}

export interface AlertStatistics {
  academic: number;
  financial: number;
  attendance: number;
  behavioral: number;
  total: number;
}

// Utility Types

export type AnalyticsTimeframe = 'week' | 'month' | 'semester' | 'year' | 'all';
export type AnalyticsMetric = keyof StudentMetrics;

export interface ApiResponse<T> {
  data: T;
  message?: string;
  success: boolean;
  timestamp: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  pageSize: number;
  hasNext: boolean;
  hasPrevious: boolean;
}

export interface ErrorResponse {
  error: string;
  details?: string;
  code?: string;
  field?: string;
  timestamp: string;
}