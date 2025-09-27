/**
 * Student Management Services Index
 *
 * Centralized export for all student API services.
 * These services provide comprehensive backend integration
 * for the student management module.
 */

export { studentService, default as studentApi } from './studentApi';
export { studentGraphQLService, default as studentGraphQL } from './studentGraphQL';
export { studentWebSocketService, default as studentWebSocket } from './studentWebSocket';

// Service utilities
export const studentServices = {
  api: studentApi,
  graphql: studentGraphQL,
  websocket: studentWebSocket,
};

// Re-export service-related types for convenience
export type {
  Student,
  StudentFormData,
  StudentUpdateData,
  StudentSearchParams,
  StudentSearchResult,
  StudentAnalytics,
  StudentPrediction,
  StudentRiskAssessment,
  BulkOperationResult,
  ImportResult,
  ExportOptions,
  CommunicationCampaign,
} from '../types/Student';