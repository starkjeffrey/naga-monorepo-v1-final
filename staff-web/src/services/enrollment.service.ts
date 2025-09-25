/**
 * Enrollment API service for managing student enrollments
 * Provides comprehensive access to program enrollments, major declarations, and class enrollments
 */

import { api } from './api';
import type {
  ProgramEnrollmentDetail,
  MajorDeclarationDetail,
  ClassEnrollmentDetail,
  EnrollmentSummary,
  EnrollmentStatistics,
  EnrollmentFilters,
  CreateProgramEnrollment,
  UpdateProgramEnrollment,
  CreateMajorDeclaration,
  UpdateMajorDeclaration,
  CreateClassEnrollment,
  UpdateClassEnrollment
} from '../types/enrollment.types';
import type { PaginatedResponse, SelectOption } from '../types/student.types';

/**
 * Enrollment API endpoints
 */
export class EnrollmentService {
  private static readonly BASE_URL = '/api';

  // ===== PROGRAM ENROLLMENTS =====

  /**
   * List program enrollments with filtering
   */
  static async listProgramEnrollments(filters: EnrollmentFilters = {}): Promise<PaginatedResponse<ProgramEnrollmentDetail>> {
    const params = new URLSearchParams({
      page: (filters.page || 1).toString(),
      page_size: (filters.page_size || 20).toString(),
    });

    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && key !== 'page' && key !== 'page_size') {
        params.append(key, value.toString());
      }
    });

    return api.get<PaginatedResponse<ProgramEnrollmentDetail>>(
      `${this.BASE_URL}/enrollment/program-enrollments/?${params}`
    );
  }

  /**
   * Get program enrollment by ID
   */
  static async getProgramEnrollment(enrollmentId: number): Promise<ProgramEnrollmentDetail> {
    return api.get<ProgramEnrollmentDetail>(`${this.BASE_URL}/enrollment/program-enrollments/${enrollmentId}/`);
  }

  /**
   * Create new program enrollment
   */
  static async createProgramEnrollment(data: CreateProgramEnrollment): Promise<ProgramEnrollmentDetail> {
    return api.post<ProgramEnrollmentDetail>(`${this.BASE_URL}/enrollment/program-enrollments/`, data);
  }

  /**
   * Update program enrollment
   */
  static async updateProgramEnrollment(enrollmentId: number, data: UpdateProgramEnrollment): Promise<ProgramEnrollmentDetail> {
    return api.put<ProgramEnrollmentDetail>(`${this.BASE_URL}/enrollment/program-enrollments/${enrollmentId}/`, data);
  }

  /**
   * Delete program enrollment
   */
  static async deleteProgramEnrollment(enrollmentId: number): Promise<void> {
    return api.delete(`${this.BASE_URL}/enrollment/program-enrollments/${enrollmentId}/`);
  }

  // ===== MAJOR DECLARATIONS =====

  /**
   * List major declarations with filtering
   */
  static async listMajorDeclarations(filters: EnrollmentFilters = {}): Promise<PaginatedResponse<MajorDeclarationDetail>> {
    const params = new URLSearchParams({
      page: (filters.page || 1).toString(),
      page_size: (filters.page_size || 20).toString(),
    });

    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && key !== 'page' && key !== 'page_size') {
        params.append(key, value.toString());
      }
    });

    return api.get<PaginatedResponse<MajorDeclarationDetail>>(
      `${this.BASE_URL}/enrollment/major-declarations/?${params}`
    );
  }

  /**
   * Get major declaration by ID
   */
  static async getMajorDeclaration(declarationId: number): Promise<MajorDeclarationDetail> {
    return api.get<MajorDeclarationDetail>(`${this.BASE_URL}/enrollment/major-declarations/${declarationId}/`);
  }

  /**
   * Create new major declaration
   */
  static async createMajorDeclaration(data: CreateMajorDeclaration): Promise<MajorDeclarationDetail> {
    return api.post<MajorDeclarationDetail>(`${this.BASE_URL}/enrollment/major-declarations/`, data);
  }

  /**
   * Update major declaration
   */
  static async updateMajorDeclaration(declarationId: number, data: UpdateMajorDeclaration): Promise<MajorDeclarationDetail> {
    return api.put<MajorDeclarationDetail>(`${this.BASE_URL}/enrollment/major-declarations/${declarationId}/`, data);
  }

  /**
   * Delete major declaration
   */
  static async deleteMajorDeclaration(declarationId: number): Promise<void> {
    return api.delete(`${this.BASE_URL}/enrollment/major-declarations/${declarationId}/`);
  }

  // ===== CLASS ENROLLMENTS =====

  /**
   * List class enrollments with filtering
   */
  static async listClassEnrollments(filters: EnrollmentFilters = {}): Promise<PaginatedResponse<ClassEnrollmentDetail>> {
    const params = new URLSearchParams({
      page: (filters.page || 1).toString(),
      page_size: (filters.page_size || 20).toString(),
    });

    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && key !== 'page' && key !== 'page_size') {
        params.append(key, value.toString());
      }
    });

    return api.get<PaginatedResponse<ClassEnrollmentDetail>>(
      `${this.BASE_URL}/enrollment/class-enrollments/?${params}`
    );
  }

  /**
   * Get class enrollment by ID
   */
  static async getClassEnrollment(enrollmentId: number): Promise<ClassEnrollmentDetail> {
    return api.get<ClassEnrollmentDetail>(`${this.BASE_URL}/enrollment/class-enrollments/${enrollmentId}/`);
  }

  /**
   * Create new class enrollment
   */
  static async createClassEnrollment(data: CreateClassEnrollment): Promise<ClassEnrollmentDetail> {
    return api.post<ClassEnrollmentDetail>(`${this.BASE_URL}/enrollment/class-enrollments/`, data);
  }

  /**
   * Update class enrollment
   */
  static async updateClassEnrollment(enrollmentId: number, data: UpdateClassEnrollment): Promise<ClassEnrollmentDetail> {
    return api.put<ClassEnrollmentDetail>(`${this.BASE_URL}/enrollment/class-enrollments/${enrollmentId}/`, data);
  }

  /**
   * Delete class enrollment
   */
  static async deleteClassEnrollment(enrollmentId: number): Promise<void> {
    return api.delete(`${this.BASE_URL}/enrollment/class-enrollments/${enrollmentId}/`);
  }

  // ===== ENROLLMENT SUMMARIES =====

  /**
   * Get comprehensive enrollment summary for a student
   */
  static async getStudentEnrollmentSummary(studentId: number): Promise<EnrollmentSummary> {
    return api.get<EnrollmentSummary>(`${this.BASE_URL}/enrollment/students/${studentId}/enrollment-summary/`);
  }

  /**
   * Get enrollment statistics
   */
  static async getEnrollmentStatistics(): Promise<EnrollmentStatistics> {
    return api.get(`${this.BASE_URL}/enrollment/statistics/`);
  }

  // ===== UTILITY ENDPOINTS =====

  /**
   * Get enrollment status choices
   */
  static async getEnrollmentStatuses(): Promise<SelectOption[]> {
    return api.get<SelectOption[]>(`${this.BASE_URL}/enrollment/enrollment-statuses/`);
  }

  /**
   * Get enrollment type choices
   */
  static async getEnrollmentTypes(): Promise<SelectOption[]> {
    return api.get<SelectOption[]>(`${this.BASE_URL}/enrollment/enrollment-types/`);
  }

  /**
   * Get class enrollment status choices
   */
  static async getClassEnrollmentStatuses(): Promise<SelectOption[]> {
    return api.get<SelectOption[]>(`${this.BASE_URL}/enrollment/class-enrollment-statuses/`);
  }

  // ===== BULK OPERATIONS =====

  /**
   * Bulk update enrollment statuses
   */
  static async bulkUpdateEnrollmentStatuses(enrollmentIds: number[], status: string): Promise<{ updated: number }> {
    return api.post(`${this.BASE_URL}/enrollment/bulk-update-status/`, {
      enrollment_ids: enrollmentIds,
      status
    });
  }

  /**
   * Bulk enrollment creation
   */
  static async bulkCreateEnrollments(enrollments: CreateClassEnrollment[]): Promise<{
    created: number;
    errors: Array<{ index: number; error: string }>;
  }> {
    return api.post(`${this.BASE_URL}/enrollment/bulk-create/`, {
      enrollments
    });
  }

  // ===== UTILITY METHODS =====

  /**
   * Format enrollment status for display
   */
  static formatEnrollmentStatus(status: string): string {
    const statusMap: Record<string, string> = {
      'ENROLLED': 'Enrolled',
      'WITHDRAWN': 'Withdrawn',
      'COMPLETED': 'Completed',
      'DEFERRED': 'Deferred',
      'SUSPENDED': 'Suspended',
      'TRANSFERRED': 'Transferred',
      'DROPPED': 'Dropped',
      'INCOMPLETE': 'Incomplete',
      'FAILED': 'Failed',
      'AUDITED': 'Audited',
    };
    return statusMap[status] || status;
  }

  /**
   * Get enrollment status badge color class
   */
  static getEnrollmentStatusBadgeClass(status: string): string {
    const statusClasses: Record<string, string> = {
      'ENROLLED': 'bg-green-100 text-green-800',
      'WITHDRAWN': 'bg-red-100 text-red-800',
      'COMPLETED': 'bg-blue-100 text-blue-800',
      'DEFERRED': 'bg-yellow-100 text-yellow-800',
      'SUSPENDED': 'bg-orange-100 text-orange-800',
      'TRANSFERRED': 'bg-purple-100 text-purple-800',
      'DROPPED': 'bg-red-100 text-red-800',
      'INCOMPLETE': 'bg-yellow-100 text-yellow-800',
      'FAILED': 'bg-red-100 text-red-800',
      'AUDITED': 'bg-gray-100 text-gray-800',
    };
    return statusClasses[status] || 'bg-gray-100 text-gray-800';
  }

  /**
   * Format enrollment type for display
   */
  static formatEnrollmentType(type: string): string {
    const typeMap: Record<string, string> = {
      'FULL_TIME': 'Full Time',
      'PART_TIME': 'Part Time',
      'AUDIT': 'Audit',
      'EXCHANGE': 'Exchange',
      'VISITING': 'Visiting',
    };
    return typeMap[type] || type;
  }

  /**
   * Calculate enrollment progress percentage
   */
  static calculateEnrollmentProgress(enrollment: ProgramEnrollmentDetail): number {
    if (!enrollment.finishing_level || !enrollment.entry_level) {
      return 0;
    }

    const totalLevels = enrollment.finishing_level - enrollment.entry_level + 1;
    const completedLevels = enrollment.terms_active;

    return Math.min(100, Math.round((completedLevels / totalLevels) * 100));
  }

  /**
   * Format GPA for display
   */
  static formatGPA(gpa?: number): string {
    if (gpa === undefined || gpa === null) {
      return 'N/A';
    }
    return gpa.toFixed(2);
  }

  /**
   * Get program type badge color
   */
  static getProgramTypeBadgeClass(programType: string): string {
    const typeClasses: Record<string, string> = {
      'BACHELOR': 'bg-blue-100 text-blue-800',
      'MASTER': 'bg-purple-100 text-purple-800',
      'DOCTORATE': 'bg-indigo-100 text-indigo-800',
      'CERTIFICATE': 'bg-green-100 text-green-800',
      'DIPLOMA': 'bg-orange-100 text-orange-800',
    };
    return typeClasses[programType] || 'bg-gray-100 text-gray-800';
  }
}