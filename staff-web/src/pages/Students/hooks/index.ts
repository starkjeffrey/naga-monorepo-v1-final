/**
 * Student Management Hooks Index
 *
 * Centralized export for all student-specific hooks.
 * These hooks provide comprehensive functionality for
 * student data management, search, analytics, and operations.
 */

export { useStudentSearch } from './useStudentSearch';
export { useStudentData } from './useStudentData';
export { useStudentAnalytics } from './useStudentAnalytics';
export { useStudentOperations } from './useStudentOperations';

// Re-export hook-related types for convenience
export type {
  StudentSearchParams,
  StudentSearchResult,
  StudentFormData,
  StudentUpdateData,
  StudentAnalytics,
  StudentPrediction,
  StudentRiskAssessment,
  BulkOperation,
  BulkOperationResult,
  ImportResult,
  ExportOptions,
  CommunicationCampaign,
} from '../types/Student';