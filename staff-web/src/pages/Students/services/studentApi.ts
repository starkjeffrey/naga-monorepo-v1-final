/**
 * Student API Service
 *
 * Comprehensive API service for student management operations:
 * - CRUD operations for student data
 * - Advanced search and filtering
 * - Bulk operations and imports/exports
 * - Photo management and OCR processing
 * - Analytics and reporting
 * - Real-time communication
 */

import { ApiClient } from '../../../services/api';
import type {
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

class StudentApiService {
  private api: ApiClient;

  constructor() {
    this.api = new ApiClient('/api/v2/students');
  }

  // CRUD Operations

  /**
   * Get all students with pagination and filtering
   */
  async getStudents(params?: {
    page?: number;
    pageSize?: number;
    search?: string;
    filters?: any;
    sorting?: any;
  }): Promise<StudentSearchResult> {
    const response = await this.api.get('/', { params });
    return response.data;
  }

  /**
   * Get a specific student by ID
   */
  async getStudent(id: string): Promise<Student> {
    const response = await this.api.get(`/${id}`);
    return response.data;
  }

  /**
   * Create a new student
   */
  async createStudent(data: StudentFormData): Promise<Student> {
    const formData = new FormData();

    // Add student data
    Object.entries(data).forEach(([key, value]) => {
      if (key === 'photoFile' && value instanceof File) {
        formData.append('photo', value);
      } else if (value !== null && value !== undefined) {
        formData.append(key, typeof value === 'object' ? JSON.stringify(value) : String(value));
      }
    });

    const response = await this.api.post('/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  }

  /**
   * Update an existing student
   */
  async updateStudent(id: string, data: StudentUpdateData): Promise<Student> {
    const response = await this.api.patch(`/${id}`, data);
    return response.data;
  }

  /**
   * Delete a student
   */
  async deleteStudent(id: string): Promise<void> {
    await this.api.delete(`/${id}`);
  }

  // Search Operations

  /**
   * Advanced student search
   */
  async searchStudents(params: StudentSearchParams): Promise<StudentSearchResult> {
    const response = await this.api.post('/search', params);
    return response.data;
  }

  /**
   * Search students by photo using facial recognition
   */
  async searchByPhoto(file: File): Promise<StudentSearchResult> {
    const formData = new FormData();
    formData.append('photo', file);

    const response = await this.api.post('/search/photo', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  }

  /**
   * Quick search for student locator
   */
  async quickSearch(query: string): Promise<Student[]> {
    const response = await this.api.get('/quick-search', {
      params: { q: query }
    });
    return response.data;
  }

  /**
   * Get search suggestions
   */
  async getSearchSuggestions(query: string): Promise<string[]> {
    const response = await this.api.get('/search/suggestions', {
      params: { q: query }
    });
    return response.data;
  }

  // Photo Management

  /**
   * Upload student photo
   */
  async uploadPhoto(studentId: string, file: File): Promise<string> {
    const formData = new FormData();
    formData.append('photo', file);

    const response = await this.api.post(`/${studentId}/photo`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data.photoUrl;
  }

  /**
   * Delete student photo
   */
  async deletePhoto(studentId: string): Promise<void> {
    await this.api.delete(`/${studentId}/photo`);
  }

  /**
   * Process document with OCR
   */
  async processOCR(file: File): Promise<any> {
    const formData = new FormData();
    formData.append('document', file);

    const response = await this.api.post('/ocr/process', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  }

  // Notes and Alerts

  /**
   * Add note to student
   */
  async addNote(studentId: string, note: string): Promise<void> {
    await this.api.post(`/${studentId}/notes`, { content: note });
  }

  /**
   * Get student notes
   */
  async getNotes(studentId: string): Promise<any[]> {
    const response = await this.api.get(`/${studentId}/notes`);
    return response.data;
  }

  /**
   * Add alert to student
   */
  async addAlert(studentId: string, alert: any): Promise<void> {
    await this.api.post(`/${studentId}/alerts`, alert);
  }

  /**
   * Clear student alert
   */
  async clearAlert(studentId: string, alertId: string): Promise<void> {
    await this.api.delete(`/${studentId}/alerts/${alertId}`);
  }

  /**
   * Get student alerts
   */
  async getAlerts(studentId: string): Promise<any[]> {
    const response = await this.api.get(`/${studentId}/alerts`);
    return response.data;
  }

  // Analytics and Reporting

  /**
   * Get student analytics
   */
  async getStudentAnalytics(studentId: string, timeframe: string): Promise<StudentAnalytics> {
    const response = await this.api.get(`/${studentId}/analytics`, {
      params: { timeframe }
    });
    return response.data;
  }

  /**
   * Get AI predictions for student
   */
  async getStudentPredictions(studentId: string): Promise<StudentPrediction> {
    const response = await this.api.get(`/${studentId}/predictions`);
    return response.data;
  }

  /**
   * Get student risk assessment
   */
  async getStudentRiskAssessment(studentId: string): Promise<StudentRiskAssessment> {
    const response = await this.api.get(`/${studentId}/risk-assessment`);
    return response.data;
  }

  /**
   * Compare student with cohort
   */
  async compareWithCohort(studentId: string, cohortType: string): Promise<any> {
    const response = await this.api.get(`/${studentId}/compare`, {
      params: { cohort_type: cohortType }
    });
    return response.data;
  }

  /**
   * Generate AI insights for student
   */
  async generateInsights(studentId: string): Promise<string[]> {
    const response = await this.api.post(`/${studentId}/insights`);
    return response.data;
  }

  // Enrollment Operations

  /**
   * Get student enrollments
   */
  async getEnrollments(studentId: string): Promise<any[]> {
    const response = await this.api.get(`/${studentId}/enrollments`);
    return response.data;
  }

  /**
   * Enroll student in courses
   */
  async enrollInCourses(studentId: string, courseIds: string[]): Promise<any> {
    const response = await this.api.post(`/${studentId}/enrollments`, {
      course_ids: courseIds
    });
    return response.data;
  }

  /**
   * Withdraw student from course
   */
  async withdrawFromCourse(studentId: string, enrollmentId: string): Promise<void> {
    await this.api.delete(`/${studentId}/enrollments/${enrollmentId}`);
  }

  /**
   * Get available courses for student
   */
  async getAvailableCourses(studentId: string): Promise<any[]> {
    const response = await this.api.get(`/${studentId}/available-courses`);
    return response.data;
  }

  // Communication

  /**
   * Send email to student
   */
  async sendEmail(studentId: string, email: {
    subject: string;
    body: string;
    attachments?: File[];
  }): Promise<void> {
    const formData = new FormData();
    formData.append('subject', email.subject);
    formData.append('body', email.body);

    if (email.attachments) {
      email.attachments.forEach((file, index) => {
        formData.append(`attachment_${index}`, file);
      });
    }

    await this.api.post(`/${studentId}/email`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  }

  /**
   * Send SMS to student
   */
  async sendSMS(studentId: string, message: string): Promise<void> {
    await this.api.post(`/${studentId}/sms`, { message });
  }

  /**
   * Get communication history
   */
  async getCommunicationHistory(studentId: string): Promise<any[]> {
    const response = await this.api.get(`/${studentId}/communications`);
    return response.data;
  }

  // Bulk Operations

  /**
   * Import students from file
   */
  async importStudents(
    file: File,
    options: any,
    onProgress?: (progress: number) => void,
    signal?: AbortSignal
  ): Promise<ImportResult> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('options', JSON.stringify(options));

    const response = await this.api.post('/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      signal,
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(progress);
        }
      },
    });
    return response.data;
  }

  /**
   * Validate import file
   */
  async validateImportFile(file: File): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await this.api.post('/import/validate', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  }

  /**
   * Export students
   */
  async exportStudents(
    studentIds: string[],
    options: ExportOptions,
    onProgress?: (progress: number) => void,
    signal?: AbortSignal
  ): Promise<void> {
    const response = await this.api.post('/export', {
      student_ids: studentIds,
      ...options
    }, {
      responseType: 'blob',
      signal,
      onDownloadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(progress);
        }
      },
    });

    // Handle file download
    const blob = new Blob([response.data]);
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `students_export.${options.format}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  }

  /**
   * Export all students with filters
   */
  async exportAllStudents(
    filters: any,
    options: ExportOptions,
    onProgress?: (progress: number) => void,
    signal?: AbortSignal
  ): Promise<void> {
    const response = await this.api.post('/export/all', {
      filters,
      ...options
    }, {
      responseType: 'blob',
      signal,
      onDownloadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(progress);
        }
      },
    });

    // Handle file download
    const blob = new Blob([response.data]);
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `all_students_export.${options.format}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  }

  /**
   * Export search results
   */
  async exportSearchResults(
    searchParams: StudentSearchParams,
    format: string
  ): Promise<void> {
    const response = await this.api.post('/export/search', {
      search_params: searchParams,
      format
    }, {
      responseType: 'blob',
    });

    // Handle file download
    const blob = new Blob([response.data]);
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `search_results.${format}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  }

  /**
   * Bulk update student status
   */
  async bulkUpdateStatus(
    studentIds: string[],
    status: string,
    onProgress?: (progress: number) => void,
    signal?: AbortSignal
  ): Promise<BulkOperationResult> {
    const response = await this.api.post('/bulk/update-status', {
      student_ids: studentIds,
      status
    }, { signal });
    return response.data;
  }

  /**
   * Send bulk email campaign
   */
  async sendBulkEmail(
    campaign: CommunicationCampaign,
    onProgress?: (progress: number) => void,
    signal?: AbortSignal
  ): Promise<BulkOperationResult> {
    const formData = new FormData();
    formData.append('campaign', JSON.stringify(campaign));

    if (campaign.attachments) {
      campaign.attachments.forEach((file, index) => {
        formData.append(`attachment_${index}`, file);
      });
    }

    const response = await this.api.post('/bulk/email', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      signal,
    });
    return response.data;
  }

  /**
   * Bulk enrollment
   */
  async bulkEnroll(
    studentIds: string[],
    courseIds: string[],
    onProgress?: (progress: number) => void,
    signal?: AbortSignal
  ): Promise<BulkOperationResult> {
    const response = await this.api.post('/bulk/enroll', {
      student_ids: studentIds,
      course_ids: courseIds
    }, { signal });
    return response.data;
  }

  // Utility Methods

  /**
   * Get student statistics
   */
  async getStatistics(): Promise<any> {
    const response = await this.api.get('/statistics');
    return response.data;
  }

  /**
   * Get lookup data for forms
   */
  async getLookupData(): Promise<{
    programs: string[];
    academicYears: string[];
    statuses: string[];
    countries: string[];
  }> {
    const response = await this.api.get('/lookup-data');
    return response.data;
  }

  /**
   * Validate student ID format
   */
  async validateStudentId(studentId: string): Promise<{ isValid: boolean; message?: string }> {
    const response = await this.api.post('/validate/student-id', { student_id: studentId });
    return response.data;
  }

  /**
   * Check if email exists
   */
  async checkEmailExists(email: string, excludeId?: string): Promise<boolean> {
    const response = await this.api.post('/validate/email', {
      email,
      exclude_id: excludeId
    });
    return response.data.exists;
  }

  /**
   * Get audit trail for student
   */
  async getAuditTrail(studentId: string): Promise<any[]> {
    const response = await this.api.get(`/${studentId}/audit-trail`);
    return response.data;
  }
}

// Export singleton instance
export const studentService = new StudentApiService();
export default studentService;