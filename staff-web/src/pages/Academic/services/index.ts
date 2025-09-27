/**
 * Academic Services Index
 *
 * Centralized export of all academic services including API, collaboration,
 * AI integration, and utility services.
 */

// Core API Service
export { academicApi, AcademicApiService } from './academicApi';

// Real-time Collaboration Service
export { collaborationService, CollaborationService } from './collaborationService';

// AI/ML Integration Service
export { aiService, AIService } from './aiService';

// Re-export types for convenience
export type {
  Student,
  Course,
  Grade,
  Enrollment,
  Instructor,
  Room,
  TimeSlot,
  Assignment,
  AIRecommendation,
  Analytics,
  CollaborativeUser,
  FieldLock,
  ChangeHistory,
  OperationalTransform,
  WebSocketMessage,
} from '../types';

// Utility functions for service integration
export const ServiceUtils = {
  /**
   * Initialize all services with authentication
   */
  initializeServices(authToken: string, userId: string): void {
    academicApi.setAuthToken(authToken);
    // Additional service initialization can be added here
  },

  /**
   * Cleanup all services
   */
  cleanupServices(): void {
    academicApi.removeAuthToken();
    collaborationService.cleanup();
    aiService.clearCache();
  },

  /**
   * Health check for all services
   */
  async healthCheck(): Promise<{
    api: boolean;
    collaboration: boolean;
    ai: boolean;
  }> {
    const results = {
      api: false,
      collaboration: false,
      ai: false,
    };

    try {
      // Test API service
      await academicApi.getCourses({ limit: 1 });
      results.api = true;
    } catch (error) {
      console.warn('API service health check failed:', error);
    }

    try {
      // Test collaboration service
      const users = collaborationService.getOnlineUsers();
      results.collaboration = true;
    } catch (error) {
      console.warn('Collaboration service health check failed:', error);
    }

    try {
      // Test AI service
      const modelInfo = aiService.getModelInfo('enrollment_prediction');
      results.ai = !!modelInfo;
    } catch (error) {
      console.warn('AI service health check failed:', error);
    }

    return results;
  },

  /**
   * Get service status information
   */
  getServiceStatus(): {
    api: string;
    collaboration: string;
    ai: string;
  } {
    return {
      api: 'Connected',
      collaboration: `${collaborationService.getOnlineUsers().length} users online`,
      ai: 'Models loaded',
    };
  },
};