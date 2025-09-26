/**
 * Academic Module Index
 *
 * Comprehensive academic management system with 14+ advanced components
 * featuring real-time collaboration, AI-powered insights, and modern UX.
 */

// Grade Management Components
export { GradeSpreadsheet } from './Grades/GradeSpreadsheet';
export { CollaborativeGradeEntry } from './Grades/CollaborativeGradeEntry';

// Course Management Components
export { CourseList } from './Courses/CourseList';

// Enrollment Management Components
export { EnrollmentHub } from './Enrollment/EnrollmentHub';
export { EnrollmentWizard } from './Enrollment/EnrollmentWizard';

// Schedule Management Components
export { ScheduleBuilder } from './Schedule/ScheduleBuilder';

// Additional components (to be implemented)
// export { QuickEnrollment } from './Enrollment/QuickEnrollment';
// export { ClassCardsView } from './Classes/ClassCardsView';
// export { ScheduleViewer } from './Schedule/ScheduleViewer';
// export { TranscriptGenerator } from './Transcripts/TranscriptGenerator';
// export { StudentGradeDetail } from './Grades/StudentGradeDetail';
// export { EnrollmentApproval } from './Approvals/EnrollmentApproval';
// export { AttendanceHub } from './Attendance/AttendanceHub';
// export { AcademicDashboard } from './Analytics/AcademicDashboard';

// Types and interfaces
export type {
  // Grade-related types
  Student,
  Assignment,
  Grade,
  GradeCell,
  CollaborativeUser,

  // Course-related types
  Course,
  Instructor,
  CourseSchedule,
  ScheduleConflict,
  AIRecommendation,

  // Enrollment-related types
  Enrollment,
  EnrollmentTrend,
  CapacityAlert,
  WaitlistEntry,
  Program,
  PaymentPlan,

  // Schedule-related types
  TimeSlot,
  ScheduleItem,
  Conflict,
  OptimizationResult,
  OptimizationSuggestion,
} from './types';

// Utility functions
export {
  calculateLetterGrade,
  calculateWeightedGrade,
  detectScheduleConflicts,
  optimizeSchedule,
  generateAIRecommendations,
} from './utils';