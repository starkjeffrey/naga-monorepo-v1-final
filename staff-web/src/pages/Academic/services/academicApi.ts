/**
 * Academic API Service
 *
 * Centralized API service for all academic management operations including
 * grades, courses, enrollments, and schedules with real-time capabilities.
 */

import type {
  Student,
  Course,
  Grade,
  Enrollment,
  Instructor,
  Room,
  TimeSlot,
  Assignment,
  ApiResponse,
  PaginatedResponse,
  BulkOperationResult,
  Analytics,
  AIRecommendation,
} from '../types';

// ============================================================================
// API Configuration
// ============================================================================

interface ApiConfig {
  baseUrl: string;
  timeout: number;
  retryAttempts: number;
  retryDelay: number;
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  headers?: Record<string, string>;
  body?: any;
  params?: Record<string, any>;
  timeout?: number;
  retries?: number;
}

// ============================================================================
// Main Academic API Service
// ============================================================================

export class AcademicApiService {
  private config: ApiConfig;
  private baseHeaders: Record<string, string>;

  constructor(config: Partial<ApiConfig> = {}) {
    this.config = {
      baseUrl: process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api/v1',
      timeout: 30000,
      retryAttempts: 3,
      retryDelay: 1000,
      ...config,
    };

    this.baseHeaders = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
  }

  /**
   * Set authentication token
   */
  setAuthToken(token: string): void {
    this.baseHeaders['Authorization'] = `Bearer ${token}`;
  }

  /**
   * Remove authentication token
   */
  removeAuthToken(): void {
    delete this.baseHeaders['Authorization'];
  }

  // ============================================================================
  // Grade Management API
  // ============================================================================

  /**
   * Get grades for a specific class
   */
  async getClassGrades(classId: string, term?: string): Promise<ApiResponse<{
    students: Student[];
    assignments: Assignment[];
    grades: Grade[];
  }>> {
    const params = term ? { term } : {};
    return this.request(`/grades/class/${classId}`, { params });
  }

  /**
   * Get individual grade entry
   */
  async getGradeEntry(gradeId: string): Promise<ApiResponse<Grade>> {
    return this.request(`/grades/${gradeId}`);
  }

  /**
   * Update a single grade
   */
  async updateGrade(gradeId: string, data: Partial<Grade>): Promise<ApiResponse<Grade>> {
    return this.request(`/grades/${gradeId}`, {
      method: 'PUT',
      body: data,
    });
  }

  /**
   * Bulk update grades
   */
  async bulkUpdateGrades(grades: Array<Partial<Grade> & { id: string }>): Promise<BulkOperationResult> {
    return this.request('/grades/bulk', {
      method: 'POST',
      body: { grades },
    });
  }

  /**
   * Calculate grade statistics
   */
  async getGradeStatistics(classId: string): Promise<ApiResponse<{
    average: number;
    median: number;
    distribution: { [grade: string]: number };
    trends: { date: string; average: number }[];
  }>> {
    return this.request(`/grades/class/${classId}/statistics`);
  }

  /**
   * Apply grade curve
   */
  async applyGradeCurve(
    classId: string,
    curveType: 'linear' | 'sqrt' | 'bell',
    targetAverage: number
  ): Promise<ApiResponse<{ affected: number; preview: Grade[] }>> {
    return this.request(`/grades/class/${classId}/curve`, {
      method: 'POST',
      body: { curveType, targetAverage },
    });
  }

  /**
   * Get grade change history
   */
  async getGradeHistory(gradeId: string): Promise<ApiResponse<any[]>> {
    return this.request(`/grades/${gradeId}/history`);
  }

  // ============================================================================
  // Course Management API
  // ============================================================================

  /**
   * Get all courses with filtering and pagination
   */
  async getCourses(params: {
    page?: number;
    limit?: number;
    department?: string;
    level?: string;
    status?: string;
    search?: string;
  } = {}): Promise<PaginatedResponse<Course>> {
    return this.request('/courses', { params });
  }

  /**
   * Get single course details
   */
  async getCourse(courseId: string): Promise<ApiResponse<Course>> {
    return this.request(`/courses/${courseId}`);
  }

  /**
   * Create new course
   */
  async createCourse(courseData: Omit<Course, 'id' | 'createdAt' | 'lastModified'>): Promise<ApiResponse<Course>> {
    return this.request('/courses', {
      method: 'POST',
      body: courseData,
    });
  }

  /**
   * Update course
   */
  async updateCourse(courseId: string, data: Partial<Course>): Promise<ApiResponse<Course>> {
    return this.request(`/courses/${courseId}`, {
      method: 'PUT',
      body: data,
    });
  }

  /**
   * Delete course
   */
  async deleteCourse(courseId: string): Promise<ApiResponse<void>> {
    return this.request(`/courses/${courseId}`, {
      method: 'DELETE',
    });
  }

  /**
   * Duplicate course
   */
  async duplicateCourse(courseId: string, modifications?: Partial<Course>): Promise<ApiResponse<Course>> {
    return this.request(`/courses/${courseId}/duplicate`, {
      method: 'POST',
      body: modifications,
    });
  }

  /**
   * Get course analytics
   */
  async getCourseAnalytics(courseId: string): Promise<ApiResponse<{
    enrollmentTrend: { date: string; enrolled: number }[];
    performanceMetrics: { average: number; successRate: number };
    feedback: any[];
  }>> {
    return this.request(`/courses/${courseId}/analytics`);
  }

  /**
   * Get AI recommendations for course
   */
  async getCourseRecommendations(courseId: string): Promise<ApiResponse<AIRecommendation[]>> {
    return this.request(`/courses/${courseId}/ai-recommendations`);
  }

  /**
   * Bulk course operations
   */
  async bulkCourseOperation(
    operation: 'activate' | 'deactivate' | 'archive' | 'delete',
    courseIds: string[]
  ): Promise<BulkOperationResult> {
    return this.request('/courses/bulk', {
      method: 'POST',
      body: { operation, courseIds },
    });
  }

  // ============================================================================
  // Enrollment Management API
  // ============================================================================

  /**
   * Get enrollment data with filtering
   */
  async getEnrollments(params: {
    courseId?: string;
    studentId?: string;
    status?: string;
    term?: string;
    page?: number;
    limit?: number;
  } = {}): Promise<PaginatedResponse<Enrollment>> {
    return this.request('/enrollments', { params });
  }

  /**
   * Create new enrollment
   */
  async createEnrollment(enrollmentData: Omit<Enrollment, 'id' | 'enrollmentDate'>): Promise<ApiResponse<Enrollment>> {
    return this.request('/enrollments', {
      method: 'POST',
      body: enrollmentData,
    });
  }

  /**
   * Update enrollment status
   */
  async updateEnrollment(enrollmentId: string, data: Partial<Enrollment>): Promise<ApiResponse<Enrollment>> {
    return this.request(`/enrollments/${enrollmentId}`, {
      method: 'PUT',
      body: data,
    });
  }

  /**
   * Process enrollment from waitlist
   */
  async processWaitlistEnrollment(waitlistId: string): Promise<ApiResponse<Enrollment>> {
    return this.request(`/enrollments/waitlist/${waitlistId}/process`, {
      method: 'POST',
    });
  }

  /**
   * Get enrollment statistics
   */
  async getEnrollmentStatistics(params: {
    term?: string;
    department?: string;
    timeRange?: string;
  } = {}): Promise<ApiResponse<{
    totalEnrollments: number;
    capacityUtilization: number;
    waitlistCounts: number;
    revenueProjection: number;
    trends: { date: string; enrollments: number; revenue: number }[];
  }>> {
    return this.request('/enrollments/statistics', { params });
  }

  /**
   * Get enrollment forecasting
   */
  async getEnrollmentForecast(
    courseIds: string[],
    periods: number = 3
  ): Promise<ApiResponse<{
    forecasts: Array<{
      courseId: string;
      predictions: Array<{
        period: string;
        predictedEnrollment: number;
        confidence: number;
      }>;
    }>;
  }>> {
    return this.request('/enrollments/forecast', {
      method: 'POST',
      body: { courseIds, periods },
    });
  }

  /**
   * Validate enrollment eligibility
   */
  async validateEnrollmentEligibility(
    studentId: string,
    courseId: string
  ): Promise<ApiResponse<{
    eligible: boolean;
    issues: string[];
    warnings: string[];
    recommendations: string[];
  }>> {
    return this.request('/enrollments/validate', {
      method: 'POST',
      body: { studentId, courseId },
    });
  }

  // ============================================================================
  // Schedule Management API
  // ============================================================================

  /**
   * Get schedule data
   */
  async getSchedule(params: {
    term?: string;
    instructorId?: string;
    roomId?: string;
    departmentId?: string;
  } = {}): Promise<ApiResponse<{
    courses: Course[];
    timeSlots: TimeSlot[];
    conflicts: any[];
  }>> {
    return this.request('/schedule', { params });
  }

  /**
   * Update schedule item
   */
  async updateScheduleItem(
    scheduleId: string,
    data: {
      timeSlot?: TimeSlot;
      roomId?: string;
      instructorId?: string;
    }
  ): Promise<ApiResponse<any>> {
    return this.request(`/schedule/${scheduleId}`, {
      method: 'PUT',
      body: data,
    });
  }

  /**
   * Detect schedule conflicts
   */
  async detectScheduleConflicts(scheduleData?: any): Promise<ApiResponse<{
    conflicts: Array<{
      type: string;
      description: string;
      severity: string;
      affectedItems: string[];
      suggestions: string[];
    }>;
  }>> {
    const url = scheduleData ? '/schedule/conflicts' : '/schedule/conflicts/current';
    return this.request(url, scheduleData ? {
      method: 'POST',
      body: scheduleData,
    } : {});
  }

  /**
   * Optimize schedule using AI
   */
  async optimizeSchedule(
    constraints: {
      minimizeConflicts?: boolean;
      maximizeUtilization?: boolean;
      respectPreferences?: boolean;
      balanceWorkload?: boolean;
    }
  ): Promise<ApiResponse<{
    optimizedSchedule: any;
    improvements: {
      conflictsReduced: number;
      utilizationIncrease: number;
      satisfactionScore: number;
    };
    suggestions: Array<{
      type: string;
      description: string;
      impact: string;
      effort: string;
    }>;
  }>> {
    return this.request('/schedule/optimize', {
      method: 'POST',
      body: constraints,
    });
  }

  /**
   * Get room availability
   */
  async getRoomAvailability(
    roomId: string,
    timeRange: { start: string; end: string }
  ): Promise<ApiResponse<{
    available: boolean;
    conflicts: any[];
    suggestions: string[];
  }>> {
    return this.request(`/schedule/rooms/${roomId}/availability`, {
      method: 'POST',
      body: timeRange,
    });
  }

  /**
   * Get instructor availability
   */
  async getInstructorAvailability(
    instructorId: string,
    timeRange: { start: string; end: string }
  ): Promise<ApiResponse<{
    available: boolean;
    preferences: any;
    conflicts: any[];
    workloadStatus: string;
  }>> {
    return this.request(`/schedule/instructors/${instructorId}/availability`, {
      method: 'POST',
      body: timeRange,
    });
  }

  // ============================================================================
  // Analytics and Reporting API
  // ============================================================================

  /**
   * Get comprehensive academic analytics
   */
  async getAcademicAnalytics(params: {
    timeRange?: string;
    department?: string;
    level?: string;
  } = {}): Promise<ApiResponse<Analytics>> {
    return this.request('/analytics/academic', { params });
  }

  /**
   * Generate academic report
   */
  async generateReport(
    reportType: 'enrollment' | 'performance' | 'utilization' | 'financial',
    params: {
      format?: 'pdf' | 'excel' | 'csv';
      dateRange?: { start: string; end: string };
      filters?: any;
    }
  ): Promise<ApiResponse<{
    reportId: string;
    downloadUrl: string;
    expiresAt: string;
  }>> {
    return this.request('/reports/generate', {
      method: 'POST',
      body: { reportType, ...params },
    });
  }

  /**
   * Get report status
   */
  async getReportStatus(reportId: string): Promise<ApiResponse<{
    status: 'pending' | 'processing' | 'completed' | 'failed';
    progress: number;
    downloadUrl?: string;
    error?: string;
  }>> {
    return this.request(`/reports/${reportId}/status`);
  }

  // ============================================================================
  // AI and ML Integration API
  // ============================================================================

  /**
   * Get AI-powered student recommendations
   */
  async getStudentRecommendations(
    studentId: string,
    context?: {
      careerGoals?: string[];
      interests?: string[];
      timeConstraints?: string[];
    }
  ): Promise<ApiResponse<{
    courses: Array<{
      course: Course;
      score: number;
      reasoning: string[];
      successProbability: number;
    }>;
    insights: string[];
  }>> {
    return this.request(`/ai/students/${studentId}/recommendations`, {
      method: 'POST',
      body: context,
    });
  }

  /**
   * Identify at-risk students
   */
  async getAtRiskStudents(params: {
    threshold?: number;
    courseId?: string;
    department?: string;
  } = {}): Promise<ApiResponse<Array<{
    student: Student;
    riskLevel: string;
    riskFactors: string[];
    interventions: string[];
    probability: number;
  }>>> {
    return this.request('/ai/students/at-risk', { params });
  }

  /**
   * Predict student performance
   */
  async predictStudentPerformance(
    studentId: string,
    courseId: string
  ): Promise<ApiResponse<{
    successProbability: number;
    expectedGrade: string;
    confidenceLevel: number;
    factors: string[];
    recommendations: string[];
  }>> {
    return this.request('/ai/predict/performance', {
      method: 'POST',
      body: { studentId, courseId },
    });
  }

  // ============================================================================
  // Utility Methods
  // ============================================================================

  /**
   * Make HTTP request with retry logic
   */
  private async request<T = any>(
    endpoint: string,
    options: RequestOptions = {}
  ): Promise<T> {
    const {
      method = 'GET',
      headers = {},
      body,
      params,
      timeout = this.config.timeout,
      retries = this.config.retryAttempts,
    } = options;

    let url = `${this.config.baseUrl}${endpoint}`;

    // Add query parameters
    if (params) {
      const searchParams = new URLSearchParams();
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          searchParams.append(key, String(value));
        }
      });
      const queryString = searchParams.toString();
      if (queryString) {
        url += `?${queryString}`;
      }
    }

    const requestOptions: RequestInit = {
      method,
      headers: {
        ...this.baseHeaders,
        ...headers,
      },
      signal: AbortSignal.timeout(timeout),
    };

    if (body && method !== 'GET' && method !== 'DELETE') {
      requestOptions.body = JSON.stringify(body);
    }

    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        const response = await fetch(url, requestOptions);

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(
            errorData.message || `HTTP ${response.status}: ${response.statusText}`
          );
        }

        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
          return await response.json();
        }

        return response.text() as unknown as T;
      } catch (error) {
        if (attempt === retries) {
          throw error;
        }

        // Wait before retrying (exponential backoff)
        await new Promise(resolve =>
          setTimeout(resolve, this.config.retryDelay * Math.pow(2, attempt))
        );
      }
    }

    throw new Error('Max retries exceeded');
  }

  /**
   * Upload file
   */
  async uploadFile(
    file: File,
    endpoint: string,
    additionalData?: Record<string, any>
  ): Promise<ApiResponse<{ fileId: string; url: string }>> {
    const formData = new FormData();
    formData.append('file', file);

    if (additionalData) {
      Object.entries(additionalData).forEach(([key, value]) => {
        formData.append(key, String(value));
      });
    }

    const response = await fetch(`${this.config.baseUrl}${endpoint}`, {
      method: 'POST',
      headers: {
        ...this.baseHeaders,
        'Content-Type': undefined, // Let browser set the boundary
      },
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Upload failed: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Download file
   */
  async downloadFile(url: string, filename?: string): Promise<void> {
    const response = await fetch(url, {
      headers: this.baseHeaders,
    });

    if (!response.ok) {
      throw new Error(`Download failed: ${response.statusText}`);
    }

    const blob = await response.blob();
    const downloadUrl = window.URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = filename || 'download';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    window.URL.revokeObjectURL(downloadUrl);
  }
}

// ============================================================================
// Export singleton instance
// ============================================================================

export const academicApi = new AcademicApiService();