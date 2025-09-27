/**
 * Enrollment Type Definitions
 *
 * TypeScript interfaces for student enrollment management:
 * - Course enrollment data structures
 * - Transfer list operations
 * - Schedule management
 * - Prerequisite validation
 * - Capacity tracking
 */

import type { Student, CourseInfo, ClassHeader, InstructorInfo } from './Student';

// Core Enrollment Types

export interface Enrollment {
  id: string;
  studentId: string;
  student?: Student;
  courseId: string;
  course?: CourseInfo;
  classHeaderId: string;
  classHeader?: ClassHeader;
  status: EnrollmentStatus;
  enrollmentDate: string;
  completionDate?: string;
  withdrawalDate?: string;
  withdrawalReason?: string;
  grade?: Grade;
  gradePoints?: number;
  credits: number;
  isActive: boolean;
  isWaitlisted: boolean;
  waitlistPosition?: number;
  priority?: number;
  notes?: string;
  createdAt: string;
  updatedAt: string;
  createdBy?: string;
  updatedBy?: string;
}

export type EnrollmentStatus =
  | 'enrolled'
  | 'waitlisted'
  | 'dropped'
  | 'completed'
  | 'failed'
  | 'withdrawn'
  | 'incomplete'
  | 'audit'
  | 'pass_fail';

export interface Grade {
  letter: string;
  points: number;
  percentage?: number;
  isPassing: boolean;
  isComplete: boolean;
  enteredDate?: string;
  enteredBy?: string;
  comments?: string;
}

// Course and Class Types

export interface Course {
  id: string;
  code: string;
  name: string;
  description: string;
  credits: number;
  department: string;
  level: string;
  isActive: boolean;
  prerequisites: Prerequisite[];
  corequisites: Corequisite[];
  restrictions?: CourseRestriction[];
  attributes?: CourseAttribute[];
  learningOutcomes?: string[];
  syllabus?: string;
  textbooks?: Textbook[];
}

export interface Prerequisite {
  type: 'course' | 'test' | 'gpa' | 'credits' | 'program';
  courseId?: string;
  course?: CourseInfo;
  testType?: string;
  minScore?: number;
  minGPA?: number;
  minCredits?: number;
  programs?: string[];
  description: string;
  isRequired: boolean;
  alternatives?: Prerequisite[];
}

export interface Corequisite {
  courseId: string;
  course?: CourseInfo;
  canBePrerequisite: boolean;
  description: string;
}

export interface CourseRestriction {
  type: 'program' | 'level' | 'classification' | 'permission';
  programs?: string[];
  levels?: string[];
  classifications?: string[];
  requiresPermission: boolean;
  description: string;
}

export interface CourseAttribute {
  type: string;
  value: string;
  description?: string;
}

export interface Textbook {
  isbn: string;
  title: string;
  author: string;
  edition?: string;
  publisher?: string;
  isRequired: boolean;
  estimatedCost?: number;
}

// Class and Schedule Types

export interface Class {
  id: string;
  courseId: string;
  course?: Course;
  section: string;
  term: string;
  capacity: number;
  enrolled: number;
  waitlisted: number;
  available: number;
  instructors: InstructorInfo[];
  schedule: ClassSchedule[];
  room?: string;
  building?: string;
  isActive: boolean;
  isOnline: boolean;
  isHybrid: boolean;
  format: ClassFormat;
  startDate: string;
  endDate: string;
  registrationStartDate?: string;
  registrationEndDate?: string;
  dropDeadline?: string;
  withdrawDeadline?: string;
  notes?: string;
  fees?: ClassFee[];
}

export interface ClassSchedule {
  id: string;
  day: DayOfWeek;
  startTime: string;
  endTime: string;
  location?: string;
  building?: string;
  room?: string;
  isOnline: boolean;
  meetingUrl?: string;
  notes?: string;
}

export type DayOfWeek = 'monday' | 'tuesday' | 'wednesday' | 'thursday' | 'friday' | 'saturday' | 'sunday';

export type ClassFormat = 'lecture' | 'lab' | 'seminar' | 'online' | 'hybrid' | 'independent_study' | 'practicum';

export interface ClassFee {
  type: string;
  amount: number;
  description: string;
  isRequired: boolean;
}

// Enrollment Operations

export interface EnrollmentRequest {
  studentId: string;
  classHeaderId: string;
  enrollmentType: 'enroll' | 'waitlist' | 'audit';
  overrideRestrictions?: boolean;
  overrideCapacity?: boolean;
  notes?: string;
  requestedBy?: string;
}

export interface EnrollmentResponse {
  success: boolean;
  enrollment?: Enrollment;
  warnings: EnrollmentWarning[];
  errors: EnrollmentError[];
  waitlistPosition?: number;
}

export interface EnrollmentWarning {
  type: 'prerequisite' | 'corequisite' | 'schedule_conflict' | 'credit_overload' | 'restriction';
  message: string;
  details?: any;
  canOverride: boolean;
}

export interface EnrollmentError {
  type: 'capacity' | 'prerequisite' | 'restriction' | 'schedule_conflict' | 'registration_closed' | 'duplicate';
  message: string;
  details?: any;
  field?: string;
}

export interface WithdrawalRequest {
  enrollmentId: string;
  reason: string;
  effectiveDate?: string;
  refundEligible?: boolean;
  requestedBy?: string;
  notes?: string;
}

export interface WithdrawalResponse {
  success: boolean;
  effectiveDate: string;
  refundAmount?: number;
  academicImpact?: AcademicImpact;
  warnings: string[];
  errors: string[];
}

export interface AcademicImpact {
  creditsAffected: number;
  gpaImpact?: number;
  graduationImpact?: string;
  prerequisiteImpact?: string[];
}

// Transfer List Types

export interface TransferListItem {
  id: string;
  type: 'course' | 'class' | 'enrollment';
  courseId?: string;
  classHeaderId?: string;
  enrollmentId?: string;
  course?: Course;
  classHeader?: Class;
  enrollment?: Enrollment;
  isAvailable: boolean;
  isEligible: boolean;
  restrictions?: string[];
  warnings?: string[];
  priority?: number;
  metadata?: Record<string, any>;
}

export interface TransferListOperation {
  type: 'move' | 'copy' | 'swap';
  sourceItems: TransferListItem[];
  targetList: 'enrolled' | 'available' | 'waitlist';
  position?: number;
  options?: TransferOptions;
}

export interface TransferOptions {
  overrideRestrictions?: boolean;
  overrideCapacity?: boolean;
  maintainWaitlistOrder?: boolean;
  validatePrerequisites?: boolean;
  checkScheduleConflicts?: boolean;
  allowCreditOverload?: boolean;
  notes?: string;
}

export interface TransferListValidation {
  isValid: boolean;
  canTransfer: boolean;
  warnings: EnrollmentWarning[];
  errors: EnrollmentError[];
  suggestedActions?: string[];
}

// Schedule Types

export interface StudentSchedule {
  studentId: string;
  term: string;
  enrollments: ScheduleEnrollment[];
  totalCredits: number;
  conflicts: ScheduleConflict[];
  gaps: ScheduleGap[];
  summary: ScheduleSummary;
  lastUpdated: string;
}

export interface ScheduleEnrollment {
  enrollment: Enrollment;
  course: Course;
  classHeader: Class;
  schedule: ClassSchedule[];
  status: EnrollmentStatus;
  color?: string;
}

export interface ScheduleConflict {
  type: 'time' | 'room' | 'instructor';
  enrollmentIds: string[];
  description: string;
  severity: 'minor' | 'major' | 'critical';
  suggestions?: string[];
}

export interface ScheduleGap {
  day: DayOfWeek;
  startTime: string;
  endTime: string;
  duration: number; // minutes
}

export interface ScheduleSummary {
  totalClasses: number;
  totalCredits: number;
  daysPerWeek: number;
  earliestClass: string;
  latestClass: string;
  longestDay: DayOfWeek;
  averageDayLength: number; // minutes
  breakTime: number; // total minutes of breaks
  travelTime?: number; // estimated travel time between classes
}

// Waitlist Types

export interface WaitlistEntry {
  id: string;
  enrollmentId: string;
  studentId: string;
  student?: Student;
  classHeaderId: string;
  classHeader?: Class;
  position: number;
  addedDate: string;
  notificationsSent: number;
  lastNotificationDate?: string;
  expirationDate?: string;
  isActive: boolean;
  priority?: number;
  notes?: string;
}

export interface WaitlistNotification {
  id: string;
  waitlistEntryId: string;
  type: 'spot_available' | 'position_update' | 'enrollment_deadline' | 'class_cancelled';
  sentDate: string;
  method: 'email' | 'sms' | 'push';
  status: 'sent' | 'delivered' | 'opened' | 'failed';
  content: string;
  responseDeadline?: string;
  response?: 'accept' | 'decline' | 'expired';
  responseDate?: string;
}

// Prerequisite Validation

export interface PrerequisiteValidation {
  studentId: string;
  courseId: string;
  isMet: boolean;
  missingRequirements: MissingRequirement[];
  completedRequirements: CompletedRequirement[];
  inProgressRequirements: InProgressRequirement[];
  alternativePathways?: AlternativePathway[];
  overrideAvailable: boolean;
  recommendations?: string[];
}

export interface MissingRequirement {
  type: 'course' | 'test' | 'gpa' | 'credits' | 'program';
  description: string;
  courseId?: string;
  course?: CourseInfo;
  requiredGPA?: number;
  currentGPA?: number;
  requiredCredits?: number;
  currentCredits?: number;
  requiredScore?: number;
  testType?: string;
  canBeWaived: boolean;
  severity: 'required' | 'recommended';
}

export interface CompletedRequirement {
  type: 'course' | 'test' | 'gpa' | 'credits';
  description: string;
  completedDate: string;
  grade?: Grade;
  score?: number;
  courseId?: string;
  course?: CourseInfo;
}

export interface InProgressRequirement {
  type: 'course' | 'credits';
  description: string;
  enrollmentId?: string;
  enrollment?: Enrollment;
  expectedCompletion: string;
  currentGrade?: string;
  willSatisfy: boolean;
}

export interface AlternativePathway {
  description: string;
  requirements: Prerequisite[];
  difficulty: 'easy' | 'moderate' | 'difficult';
  timeToComplete: string;
  recommendation: string;
}

// Capacity and Registration

export interface CapacityInfo {
  total: number;
  enrolled: number;
  waitlisted: number;
  available: number;
  reserved: number;
  holds: number;
  utilization: number; // percentage
  isOverbooked: boolean;
  projectedDemand?: number;
}

export interface RegistrationPeriod {
  id: string;
  name: string;
  startDate: string;
  endDate: string;
  isActive: boolean;
  eligibleStudents?: RegistrationEligibility[];
  restrictions?: RegistrationRestriction[];
  priority?: number;
  description?: string;
}

export interface RegistrationEligibility {
  type: 'program' | 'level' | 'credits' | 'gpa' | 'classification';
  programs?: string[];
  levels?: string[];
  minCredits?: number;
  minGPA?: number;
  classifications?: string[];
  description: string;
}

export interface RegistrationRestriction {
  type: 'holds' | 'balance' | 'advising' | 'documentation';
  description: string;
  canOverride: boolean;
  overrideAuthority?: string;
}

// Bulk Enrollment Operations

export interface BulkEnrollmentRequest {
  studentIds: string[];
  classHeaderIds: string[];
  enrollmentType: 'enroll' | 'waitlist';
  options: BulkEnrollmentOptions;
  requestedBy: string;
  notes?: string;
}

export interface BulkEnrollmentOptions {
  overrideRestrictions: boolean;
  overrideCapacity: boolean;
  validatePrerequisites: boolean;
  checkScheduleConflicts: boolean;
  allowPartialSuccess: boolean;
  sendNotifications: boolean;
  createAuditLog: boolean;
}

export interface BulkEnrollmentResult {
  totalRequested: number;
  successful: number;
  failed: number;
  waitlisted: number;
  results: BulkEnrollmentItemResult[];
  summary: string;
  completedAt: string;
  auditLogId?: string;
}

export interface BulkEnrollmentItemResult {
  studentId: string;
  classHeaderId: string;
  status: 'success' | 'waitlisted' | 'failed';
  enrollmentId?: string;
  waitlistPosition?: number;
  errors: EnrollmentError[];
  warnings: EnrollmentWarning[];
}

// Academic Planning

export interface AcademicPlan {
  studentId: string;
  programId: string;
  version: string;
  plannedGraduation: string;
  totalCreditsRequired: number;
  creditsCompleted: number;
  creditsInProgress: number;
  creditsRemaining: number;
  semesters: PlannedSemester[];
  milestones: AcademicMilestone[];
  lastUpdated: string;
  approvedBy?: string;
  approvedDate?: string;
}

export interface PlannedSemester {
  term: string;
  year: number;
  plannedCourses: PlannedCourse[];
  totalCredits: number;
  isCompleted: boolean;
  actualGPA?: number;
  notes?: string;
}

export interface PlannedCourse {
  courseId: string;
  course?: Course;
  credits: number;
  isRequired: boolean;
  category: string; // e.g., "Core", "Elective", "Major Requirement"
  priority: number;
  alternatives?: string[]; // alternative course IDs
  status: 'planned' | 'enrolled' | 'completed' | 'substituted' | 'waived';
  actualGrade?: Grade;
  enrollmentId?: string;
  notes?: string;
}

export interface AcademicMilestone {
  id: string;
  name: string;
  description: string;
  requiredCredits?: number;
  requiredCourses?: string[];
  targetDate: string;
  completedDate?: string;
  isCompleted: boolean;
  isRequired: boolean;
  category: string;
}

// Export Types for External Use

export type {
  // Core types
  Enrollment,
  EnrollmentStatus,
  Grade,
  Course,
  Class,
  ClassSchedule,

  // Operation types
  EnrollmentRequest,
  EnrollmentResponse,
  WithdrawalRequest,
  WithdrawalResponse,

  // Transfer list types
  TransferListItem,
  TransferListOperation,
  TransferListValidation,

  // Schedule types
  StudentSchedule,
  ScheduleConflict,
  ScheduleSummary,

  // Prerequisite types
  PrerequisiteValidation,
  MissingRequirement,

  // Bulk operation types
  BulkEnrollmentRequest,
  BulkEnrollmentResult,

  // Planning types
  AcademicPlan,
  PlannedSemester,
};