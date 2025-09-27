/**
 * Academic Module Types
 *
 * Comprehensive type definitions for academic management system
 * including grades, courses, enrollments, schedules, and collaboration features.
 */

// ============================================================================
// Grade Management Types
// ============================================================================

export interface Student {
  id: string;
  studentId: string;
  name: string;
  email: string;
  avatar?: string;
  attendanceRate: number;
  participationScore: number;
  status: 'active' | 'inactive' | 'dropped' | 'graduated';
  program: string;
  level: string;
  gpa: number;
  credits: number;
  advisorId: string;
  financialHold: boolean;
  academicHold: boolean;
  enrollmentDate: string;
  phone: string;
}

export interface Assignment {
  id: string;
  name: string;
  category: string;
  maxPoints: number;
  weight: number;
  dueDate: string;
  type: 'homework' | 'quiz' | 'exam' | 'project' | 'participation';
  rubric?: RubricCriteria[];
  allowsPartialCredit: boolean;
  description?: string;
  instructions?: string;
  submissionFormat: string[];
}

export interface RubricCriteria {
  id: string;
  name: string;
  description: string;
  maxPoints: number;
  levels: RubricLevel[];
}

export interface RubricLevel {
  id: string;
  name: string;
  description: string;
  points: number;
}

export interface Grade {
  id: string;
  studentId: string;
  assignmentId: string;
  points: number | null;
  percentage: number | null;
  letterGrade: string | null;
  comments?: string;
  rubricScores: { [criteriaId: string]: number };
  submitted: boolean;
  late: boolean;
  excused: boolean;
  attemptNumber: number;
  lastModified: string;
  modifiedBy: string;
  version: number;
}

export interface GradeCell {
  studentId: string;
  assignmentId: string;
  value: number | null;
  isEditing: boolean;
  isLocked: boolean;
  editingBy?: string;
  lastSaved: string;
  hasConflict: boolean;
}

// ============================================================================
// Course Management Types
// ============================================================================

export interface Course {
  id: string;
  code: string;
  name: string;
  description: string;
  department: string;
  credits: number;
  level: 'undergraduate' | 'graduate' | 'doctoral';
  status: 'active' | 'inactive' | 'draft' | 'archived';
  maxCapacity: number;
  currentEnrollment: number;
  waitlistCount: number;
  prerequisites: string[];
  corequisites: string[];
  instructors: Instructor[];
  schedule: CourseSchedule[];
  tuition: number;
  tags: string[];
  lastModified: string;
  createdAt: string;
  successRate: number;
  difficulty: number;
  popularity: number;
  aiRecommendations?: AIRecommendation[];
  duration: number; // minutes
  requiredResources: string[];
  preferredTimeSlots: string[];
  frequency: 'weekly' | 'biweekly' | 'monthly';
  color: string;
  restrictions: string[];
}

export interface Instructor {
  id: string;
  name: string;
  email: string;
  avatar?: string;
  department: string;
  rating: number;
  preferences: InstructorPreferences;
  availability: TimeSlot[];
  maxHoursPerWeek: number;
  currentHours: number;
}

export interface InstructorPreferences {
  preferredDays: string[];
  preferredTimes: { start: string; end: string }[];
  avoidBackToBack: boolean;
  maxConsecutiveHours: number;
  lunchBreakRequired: boolean;
}

export interface CourseSchedule {
  id: string;
  dayOfWeek: string;
  startTime: string;
  endTime: string;
  room: string;
  building: string;
  capacity: number;
  conflicts?: ScheduleConflict[];
}

export interface ScheduleConflict {
  type: 'room' | 'instructor' | 'student';
  description: string;
  severity: 'low' | 'medium' | 'high';
  affectedCount: number;
  resolutionSuggestions: string[];
}

// ============================================================================
// Enrollment Management Types
// ============================================================================

export interface Enrollment {
  id: string;
  studentId: string;
  courseId: string;
  status: 'enrolled' | 'waitlisted' | 'dropped' | 'completed' | 'pending_payment';
  enrollmentDate: string;
  dropDate?: string;
  paymentStatus: 'paid' | 'pending' | 'overdue' | 'cancelled';
  paymentAmount: number;
  paymentDueDate: string;
  grade?: string;
  priority: number;
  waitlistPosition?: number;
  notes?: string;
}

export interface EnrollmentTrend {
  date: string;
  enrolled: number;
  dropped: number;
  waitlisted: number;
  revenue: number;
}

export interface CapacityAlert {
  id: string;
  courseId: string;
  type: 'full' | 'overbooked' | 'low_enrollment' | 'waitlist_high';
  message: string;
  severity: 'low' | 'medium' | 'high';
  createdAt: string;
  resolved: boolean;
}

export interface WaitlistEntry {
  id: string;
  studentId: string;
  courseId: string;
  position: number;
  addedDate: string;
  priority: number;
  notificationSent: boolean;
  autoEnroll: boolean;
}

export interface Program {
  id: string;
  name: string;
  code: string;
  department: string;
  level: string;
  requiredCredits: number;
  requiredCourses: string[];
  electiveCourses: string[];
  duration: number; // in semesters
  tuition: number;
}

export interface PaymentPlan {
  id: string;
  name: string;
  description: string;
  installments: number;
  downPaymentPercent: number;
  interestRate: number;
  penaltyRate: number;
}

// ============================================================================
// Schedule Management Types
// ============================================================================

export interface TimeSlot {
  id: string;
  dayOfWeek: string;
  startTime: string;
  endTime: string;
  available: boolean;
  recurring: boolean;
  exceptions: string[]; // dates when not available
}

export interface ScheduleItem {
  id: string;
  courseId: string;
  instructorId: string;
  roomId: string;
  timeSlot: TimeSlot;
  students: string[];
  resources: string[];
  status: 'scheduled' | 'confirmed' | 'cancelled' | 'conflict';
}

export interface Room {
  id: string;
  name: string;
  building: string;
  capacity: number;
  resources: string[];
  availability: TimeSlot[];
  type: 'classroom' | 'lab' | 'seminar' | 'auditorium';
  floor: number;
  accessible: boolean;
}

export interface Conflict {
  id: string;
  type: 'time' | 'room' | 'instructor' | 'resource';
  description: string;
  severity: 'low' | 'medium' | 'high';
  affectedItems: string[];
  resolutionOptions: ConflictResolution[];
  autoResolvable: boolean;
}

export interface ConflictResolution {
  id: string;
  description: string;
  impact: string;
  feasibility: number; // 0-100
  cost: number;
  timeToImplement: number; // hours
}

export interface OptimizationResult {
  id: string;
  score: number;
  conflictsResolved: number;
  utilizationImproved: number;
  instructorSatisfaction: number;
  studentSatisfaction: number;
  suggestions: OptimizationSuggestion[];
}

export interface OptimizationSuggestion {
  type: 'move' | 'swap' | 'reschedule' | 'add_resource';
  description: string;
  impact: string;
  confidence: number;
  effort: 'low' | 'medium' | 'high';
  implementation: string;
}

// ============================================================================
// AI and Analytics Types
// ============================================================================

export interface AIRecommendation {
  type: 'enrollment' | 'schedule' | 'prerequisite' | 'capacity' | 'performance';
  title: string;
  description: string;
  confidence: number;
  impact: 'low' | 'medium' | 'high';
  action?: string;
  data?: any;
  createdAt: string;
  implemented: boolean;
}

export interface PrerequisiteNode {
  key: string;
  title: string;
  children?: PrerequisiteNode[];
  required: boolean;
  completed?: boolean;
  inProgress?: boolean;
  available?: boolean;
}

export interface Analytics {
  enrollmentTrends: EnrollmentTrend[];
  capacityUtilization: number;
  revenueProjection: number;
  completionRates: { [courseId: string]: number };
  instructorWorkload: { [instructorId: string]: number };
  roomUtilization: { [roomId: string]: number };
  studentSatisfaction: { [courseId: string]: number };
}

// ============================================================================
// Collaboration Types
// ============================================================================

export interface CollaborativeUser {
  id: string;
  name: string;
  avatar?: string;
  color: string;
  isOnline: boolean;
  currentField?: string;
  currentView?: string;
  cursor?: {
    studentId: string;
    assignmentId: string;
    x: number;
    y: number;
  };
  lastSeen: string;
  permissions: CollaborationPermission[];
}

export interface CollaborationPermission {
  resource: string; // 'grades', 'enrollment', 'schedule'
  action: 'read' | 'write' | 'admin';
  scope: string[]; // specific IDs or 'all'
}

export interface FieldLock {
  field: string;
  userId: string;
  userName: string;
  timestamp: string;
  expiresAt: string;
}

export interface ChangeHistory {
  id: string;
  resource: string; // 'grade', 'enrollment', 'course', 'schedule'
  resourceId: string;
  field: string;
  oldValue: any;
  newValue: any;
  timestamp: string;
  userId: string;
  userName: string;
  operation: 'create' | 'update' | 'delete';
  reason?: string;
}

export interface OperationalTransform {
  id: string;
  type: 'insert' | 'delete' | 'retain' | 'replace';
  position: number;
  length: number;
  content: any;
  timestamp: string;
  userId: string;
  version: number;
}

// ============================================================================
// WebSocket Message Types
// ============================================================================

export interface WebSocketMessage {
  type: string;
  payload: any;
  timestamp: string;
  userId: string;
  messageId: string;
}

export interface GradeUpdateMessage extends WebSocketMessage {
  type: 'grade_updated';
  payload: {
    studentId: string;
    assignmentId: string;
    value: number | null;
    version: number;
  };
}

export interface UserPresenceMessage extends WebSocketMessage {
  type: 'user_presence';
  payload: {
    action: 'join' | 'leave' | 'move';
    user: CollaborativeUser;
    location?: string;
  };
}

export interface FieldLockMessage extends WebSocketMessage {
  type: 'field_lock' | 'field_unlock';
  payload: {
    field: string;
    lock?: FieldLock;
  };
}

export interface ConflictMessage extends WebSocketMessage {
  type: 'conflict_detected' | 'conflict_resolved';
  payload: {
    conflictId: string;
    description: string;
    resolution?: ConflictResolution;
  };
}

// ============================================================================
// Form and Validation Types
// ============================================================================

export interface ValidationResult {
  valid: boolean;
  errors: ValidationError[];
  warnings: ValidationWarning[];
}

export interface ValidationError {
  field: string;
  message: string;
  code: string;
  severity: 'error' | 'warning';
}

export interface ValidationWarning {
  field: string;
  message: string;
  suggestion?: string;
}

export interface FormState {
  isValid: boolean;
  isDirty: boolean;
  isSubmitting: boolean;
  errors: { [field: string]: string };
  values: { [field: string]: any };
  originalValues: { [field: string]: any };
}

// ============================================================================
// API Response Types
// ============================================================================

export interface ApiResponse<T = any> {
  success: boolean;
  data: T;
  message: string;
  errors?: string[];
  timestamp: string;
  version: string;
}

export interface PaginatedResponse<T = any> extends ApiResponse<T[]> {
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
    hasNext: boolean;
    hasPrev: boolean;
  };
}

export interface BulkOperationResult {
  success: boolean;
  processed: number;
  succeeded: number;
  failed: number;
  errors: { [id: string]: string };
  warnings: { [id: string]: string };
}

// ============================================================================
// Export all types
// ============================================================================

export type {
  // Re-export everything for convenience
  Student,
  Assignment,
  Grade,
  GradeCell,
  Course,
  Instructor,
  CourseSchedule,
  ScheduleConflict,
  Enrollment,
  EnrollmentTrend,
  CapacityAlert,
  WaitlistEntry,
  Program,
  PaymentPlan,
  TimeSlot,
  ScheduleItem,
  Room,
  Conflict,
  ConflictResolution,
  OptimizationResult,
  OptimizationSuggestion,
  AIRecommendation,
  PrerequisiteNode,
  Analytics,
  CollaborativeUser,
  CollaborationPermission,
  FieldLock,
  ChangeHistory,
  OperationalTransform,
  WebSocketMessage,
  GradeUpdateMessage,
  UserPresenceMessage,
  FieldLockMessage,
  ConflictMessage,
  ValidationResult,
  ValidationError,
  ValidationWarning,
  FormState,
  ApiResponse,
  PaginatedResponse,
  BulkOperationResult,
};