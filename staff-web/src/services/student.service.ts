/**
 * Student API service for managing student, people, enrollment, and curriculum data
 * Provides comprehensive access to all student-related endpoints
 */

import { api } from './api';
import type {
  PersonDetail,
  StudentListItem,
  PersonSearchResult,
  StudentFilters,
  PersonSearchFilters,
  PaginatedResponse,
  SelectOption,
  CreatePersonData,
  UpdatePersonData,
  CreateStudentProfileData,
  UpdateStudentProfileData,
  PhoneNumber,
  Contact,
  Division,
  Cycle,
  Major,
  Term,
  Course,
  ProgramEnrollment,
  MajorDeclaration,
  ClassEnrollment,
  StudentEnrollmentSummary,
} from '../types/student.types';

/**
 * Student API endpoints
 */
export class StudentService {
  private static readonly BASE_URL = '/api';

  // ===== PEOPLE API =====

  /**
   * Get detailed person information by ID
   */
  static async getPersonDetail(personId: number): Promise<PersonDetail> {
    return api.get<PersonDetail>(`${this.BASE_URL}/people/persons/${personId}/`);
  }

  /**
   * Search persons across all roles
   */
  static async searchPersons(filters: PersonSearchFilters): Promise<PaginatedResponse<PersonSearchResult>> {
    const params = new URLSearchParams({
      q: filters.q,
      page: (filters.page || 1).toString(),
      page_size: (filters.page_size || 20).toString(),
    });

    if (filters.roles?.length) {
      filters.roles.forEach(role => params.append('roles', role));
    }

    return api.get<PaginatedResponse<PersonSearchResult>>(
      `${this.BASE_URL}/people/persons/search/?${params}`
    );
  }

  /**
   * List students with filtering and pagination
   */
  static async listStudents(filters: StudentFilters = {}): Promise<PaginatedResponse<StudentListItem>> {
    const params = new URLSearchParams({
      page: (filters.page || 1).toString(),
      page_size: (filters.page_size || 20).toString(),
    });

    if (filters.status) {
      params.append('status', filters.status);
    }

    if (filters.search) {
      params.append('search', filters.search);
    }

    return api.get<PaginatedResponse<StudentListItem>>(
      `${this.BASE_URL}/people/students/?${params}`
    );
  }

  /**
   * Get student details by student ID
   */
  static async getStudentById(studentId: number): Promise<PersonDetail> {
    return api.get<PersonDetail>(`${this.BASE_URL}/people/students/${studentId}/`);
  }

  /**
   * Get phone numbers for a person
   */
  static async getPersonPhoneNumbers(personId: number): Promise<PhoneNumber[]> {
    return api.get<PhoneNumber[]>(`${this.BASE_URL}/people/persons/${personId}/phone-numbers/`);
  }

  /**
   * Get contacts for a person
   */
  static async getPersonContacts(personId: number): Promise<Contact[]> {
    return api.get<Contact[]>(`${this.BASE_URL}/people/persons/${personId}/emergency-contacts/`);
  }

  /**
   * Get student status choices for forms
   */
  static async getStudentStatuses(): Promise<SelectOption[]> {
    return api.get<SelectOption[]>(`${this.BASE_URL}/people/students/statuses/`);
  }

  /**
   * Get relationship choices for emergency contacts
   */
  static async getRelationshipChoices(): Promise<SelectOption[]> {
    return api.get<SelectOption[]>(`${this.BASE_URL}/people/emergency-contacts/relationships/`);
  }

  // ===== ENROLLMENT API =====

  /**
   * List program enrollments
   */
  static async listProgramEnrollments(filters: {
    student_id?: number;
    major_id?: number;
    status?: string;
    enrollment_type?: string;
    active_only?: boolean;
    page?: number;
    page_size?: number;
  } = {}): Promise<PaginatedResponse<ProgramEnrollment>> {
    const params = new URLSearchParams({
      page: (filters.page || 1).toString(),
      page_size: (filters.page_size || 20).toString(),
    });

    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && key !== 'page' && key !== 'page_size') {
        params.append(key, value.toString());
      }
    });

    return api.get<PaginatedResponse<ProgramEnrollment>>(
      `${this.BASE_URL}/enrollment/program-enrollments/?${params}`
    );
  }

  /**
   * Get program enrollment by ID
   */
  static async getProgramEnrollment(enrollmentId: number): Promise<ProgramEnrollment> {
    return api.get<ProgramEnrollment>(`${this.BASE_URL}/enrollment/program-enrollments/${enrollmentId}/`);
  }

  /**
   * List major declarations
   */
  static async listMajorDeclarations(filters: {
    student_id?: number;
    major_id?: number;
    active_only?: boolean;
    prospective_only?: boolean;
    page?: number;
    page_size?: number;
  } = {}): Promise<PaginatedResponse<MajorDeclaration>> {
    const params = new URLSearchParams({
      page: (filters.page || 1).toString(),
      page_size: (filters.page_size || 20).toString(),
    });

    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && key !== 'page' && key !== 'page_size') {
        params.append(key, value.toString());
      }
    });

    return api.get<PaginatedResponse<MajorDeclaration>>(
      `${this.BASE_URL}/enrollment/major-declarations/?${params}`
    );
  }

  /**
   * List class enrollments
   */
  static async listClassEnrollments(filters: {
    student_id?: number;
    class_header_id?: number;
    term_id?: number;
    status?: string;
    current_term_only?: boolean;
    page?: number;
    page_size?: number;
  } = {}): Promise<PaginatedResponse<ClassEnrollment>> {
    const params = new URLSearchParams({
      page: (filters.page || 1).toString(),
      page_size: (filters.page_size || 20).toString(),
    });

    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && key !== 'page' && key !== 'page_size') {
        params.append(key, value.toString());
      }
    });

    return api.get<PaginatedResponse<ClassEnrollment>>(
      `${this.BASE_URL}/enrollment/class-enrollments/?${params}`
    );
  }

  /**
   * Get comprehensive enrollment summary for a student
   */
  static async getStudentEnrollmentSummary(studentId: number): Promise<StudentEnrollmentSummary> {
    return api.get<StudentEnrollmentSummary>(`${this.BASE_URL}/enrollment/students/${studentId}/enrollment-summary/`);
  }

  /**
   * Get enrollment statistics
   */
  static async getEnrollmentStatistics(): Promise<{
    total_students: number;
    active_students: number;
    total_enrollments: number;
    current_term_enrollments: number;
    status_breakdown: Record<string, number>;
    program_type_breakdown: Record<string, number>;
    division_breakdown: Record<string, number>;
  }> {
    return api.get(`${this.BASE_URL}/enrollment/statistics/`);
  }

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

  // ===== CURRICULUM API =====

  /**
   * List all divisions
   */
  static async listDivisions(activeOnly: boolean = true): Promise<Division[]> {
    const params = activeOnly ? '?active_only=true' : '?active_only=false';
    return api.get<Division[]>(`${this.BASE_URL}/curriculum/divisions/${params}`);
  }

  /**
   * List cycles, optionally filtered by division
   */
  static async listCycles(filters: {
    division_id?: number;
    active_only?: boolean;
  } = {}): Promise<Cycle[]> {
    const params = new URLSearchParams({
      active_only: (filters.active_only !== false).toString(),
    });

    if (filters.division_id) {
      params.append('division_id', filters.division_id.toString());
    }

    return api.get<Cycle[]>(`${this.BASE_URL}/curriculum/cycles/?${params}`);
  }

  /**
   * List majors with comprehensive filtering
   */
  static async listMajors(filters: {
    division_id?: number;
    cycle_id?: number;
    program_type?: string;
    active_only?: boolean;
    accepting_students?: boolean;
    page?: number;
    page_size?: number;
  } = {}): Promise<PaginatedResponse<Major & { student_count?: number }>> {
    const params = new URLSearchParams({
      page: (filters.page || 1).toString(),
      page_size: (filters.page_size || 50).toString(),
    });

    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && key !== 'page' && key !== 'page_size') {
        params.append(key, value.toString());
      }
    });

    return api.get<PaginatedResponse<Major & { student_count?: number }>>(
      `${this.BASE_URL}/curriculum/majors/?${params}`
    );
  }

  /**
   * Get major by ID
   */
  static async getMajor(majorId: number): Promise<Major> {
    return api.get<Major>(`${this.BASE_URL}/curriculum/majors/${majorId}/`);
  }

  /**
   * List terms
   */
  static async listTerms(filters: {
    academic_year?: number;
    term_type?: string;
    current_only?: boolean;
    page?: number;
    page_size?: number;
  } = {}): Promise<PaginatedResponse<Term & { enrollment_count?: number }>> {
    const params = new URLSearchParams({
      page: (filters.page || 1).toString(),
      page_size: (filters.page_size || 20).toString(),
    });

    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && key !== 'page' && key !== 'page_size') {
        params.append(key, value.toString());
      }
    });

    return api.get<PaginatedResponse<Term & { enrollment_count?: number }>>(
      `${this.BASE_URL}/curriculum/terms/?${params}`
    );
  }

  /**
   * Get current term
   */
  static async getCurrentTerm(): Promise<Term> {
    return api.get<Term>(`${this.BASE_URL}/curriculum/terms/current/`);
  }

  /**
   * List courses with comprehensive filtering
   */
  static async listCourses(filters: {
    division_id?: number;
    course_type?: string;
    level?: number;
    active_only?: boolean;
    search?: string;
    page?: number;
    page_size?: number;
  } = {}): Promise<PaginatedResponse<Course & { class_count?: number }>> {
    const params = new URLSearchParams({
      page: (filters.page || 1).toString(),
      page_size: (filters.page_size || 50).toString(),
    });

    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && key !== 'page' && key !== 'page_size') {
        params.append(key, value.toString());
      }
    });

    return api.get<PaginatedResponse<Course & { class_count?: number }>>(
      `${this.BASE_URL}/curriculum/courses/?${params}`
    );
  }

  /**
   * Get academic structure overview
   */
  static async getAcademicStructure(): Promise<{
    divisions: Division[];
    cycles: Cycle[];
    majors: Major[];
    current_term?: Term;
  }> {
    return api.get(`${this.BASE_URL}/curriculum/structure/`);
  }

  /**
   * Get curriculum statistics
   */
  static async getCurriculumStatistics(): Promise<{
    total_majors: number;
    active_majors: number;
    total_courses: number;
    active_courses: number;
    total_terms: number;
    current_term_id?: number;
    division_breakdown: Record<string, number>;
    program_type_breakdown: Record<string, number>;
    course_type_breakdown: Record<string, number>;
  }> {
    return api.get(`${this.BASE_URL}/curriculum/statistics/`);
  }

  /**
   * Get program type choices
   */
  static async getProgramTypes(): Promise<SelectOption[]> {
    return api.get<SelectOption[]>(`${this.BASE_URL}/curriculum/program-types/`);
  }

  /**
   * Get course type choices
   */
  static async getCourseTypes(): Promise<SelectOption[]> {
    return api.get<SelectOption[]>(`${this.BASE_URL}/curriculum/course-types/`);
  }

  /**
   * Get term type choices
   */
  static async getTermTypes(): Promise<SelectOption[]> {
    return api.get<SelectOption[]>(`${this.BASE_URL}/curriculum/term-types/`);
  }

  // ===== UTILITY METHODS =====

  /**
   * Format student status for display
   */
  static formatStudentStatus(status: string): string {
    const statusMap: Record<string, string> = {
      'ACTIVE': 'Active',
      'INACTIVE': 'Inactive',
      'GRADUATED': 'Graduated',
      'DROPPED': 'Dropped',
      'SUSPENDED': 'Suspended',
      'TRANSFERRED': 'Transferred',
      'FROZEN': 'Frozen',
      'UNKNOWN': 'Unknown',
    };
    return statusMap[status] || status;
  }

  /**
   * Get status badge color class
   */
  static getStatusBadgeClass(status: string): string {
    const statusClasses: Record<string, string> = {
      'ACTIVE': 'bg-green-100 text-green-800',
      'INACTIVE': 'bg-gray-100 text-gray-800',
      'GRADUATED': 'bg-blue-100 text-blue-800',
      'DROPPED': 'bg-red-100 text-red-800',
      'SUSPENDED': 'bg-yellow-100 text-yellow-800',
      'TRANSFERRED': 'bg-purple-100 text-purple-800',
      'FROZEN': 'bg-indigo-100 text-indigo-800',
      'UNKNOWN': 'bg-gray-100 text-gray-800',
    };
    return statusClasses[status] || 'bg-gray-100 text-gray-800';
  }

  /**
   * Format study time preference for display
   */
  static formatStudyTimePreference(preference: string): string {
    const prefMap: Record<string, string> = {
      'morning': 'Morning',
      'afternoon': 'Afternoon',
      'evening': 'Evening',
    };
    return prefMap[preference] || preference;
  }
}