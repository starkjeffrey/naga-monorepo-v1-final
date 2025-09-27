/**
 * Academic API Test Suite
 *
 * Comprehensive tests for the Academic API service including:
 * - API endpoint validation
 * - Real-time collaboration features
 * - AI integration functionality
 * - Error handling and retry logic
 */

import { describe, test, expect, beforeEach, afterEach, vi } from 'vitest';
import { academicApi, AcademicApiService } from '../services/academicApi';
import type { Course, Student, Grade, Enrollment } from '../types';

// Mock fetch globally
global.fetch = vi.fn();

describe('AcademicApiService', () => {
  let apiService: AcademicApiService;

  beforeEach(() => {
    apiService = new AcademicApiService({
      baseUrl: 'http://localhost:8000/api/v1',
      timeout: 5000,
      retryAttempts: 2,
      retryDelay: 100,
    });

    // Reset all mocks
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Authentication', () => {
    test('should set auth token correctly', () => {
      const token = 'test-token-123';
      apiService.setAuthToken(token);

      // Access private headers through any to test
      const headers = (apiService as any).baseHeaders;
      expect(headers['Authorization']).toBe(`Bearer ${token}`);
    });

    test('should remove auth token correctly', () => {
      apiService.setAuthToken('test-token');
      apiService.removeAuthToken();

      const headers = (apiService as any).baseHeaders;
      expect(headers['Authorization']).toBeUndefined();
    });
  });

  describe('Grade Management', () => {
    const mockGradeResponse = {
      success: true,
      data: {
        students: [],
        assignments: [],
        grades: [],
      },
      message: 'Success',
      timestamp: new Date().toISOString(),
      version: '1.0.0',
    };

    test('should fetch class grades successfully', async () => {
      (fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockGradeResponse,
        headers: new Headers({ 'content-type': 'application/json' }),
      });

      const result = await apiService.getClassGrades('class-123', 'fall-2024');

      expect(fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/grades/class/class-123?term=fall-2024',
        expect.objectContaining({
          method: 'GET',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
          }),
        })
      );

      expect(result).toEqual(mockGradeResponse);
    });

    test('should update grade successfully', async () => {
      const gradeUpdate = {
        points: 85,
        comments: 'Good work',
        lastModified: new Date().toISOString(),
      };

      const mockResponse = {
        success: true,
        data: { id: 'grade-123', ...gradeUpdate },
        message: 'Grade updated',
        timestamp: new Date().toISOString(),
        version: '1.0.0',
      };

      (fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
        headers: new Headers({ 'content-type': 'application/json' }),
      });

      const result = await apiService.updateGrade('grade-123', gradeUpdate);

      expect(fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/grades/grade-123',
        expect.objectContaining({
          method: 'PUT',
          body: JSON.stringify(gradeUpdate),
        })
      );

      expect(result).toEqual(mockResponse);
    });

    test('should handle bulk grade updates', async () => {
      const bulkGrades = [
        { id: 'grade-1', points: 85 },
        { id: 'grade-2', points: 90 },
        { id: 'grade-3', points: 78 },
      ];

      const mockResponse = {
        success: true,
        processed: 3,
        succeeded: 3,
        failed: 0,
        errors: {},
        warnings: {},
      };

      (fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
        headers: new Headers({ 'content-type': 'application/json' }),
      });

      const result = await apiService.bulkUpdateGrades(bulkGrades);

      expect(fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/grades/bulk',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ grades: bulkGrades }),
        })
      );

      expect(result).toEqual(mockResponse);
    });
  });

  describe('Course Management', () => {
    const mockCourse: Course = {
      id: 'course-123',
      code: 'CS101',
      name: 'Introduction to Computer Science',
      description: 'Basic programming concepts',
      department: 'Computer Science',
      credits: 3,
      level: 'undergraduate',
      status: 'active',
      maxCapacity: 30,
      currentEnrollment: 25,
      waitlistCount: 5,
      prerequisites: [],
      corequisites: [],
      instructors: [],
      schedule: [],
      tuition: 1500,
      tags: ['programming', 'intro'],
      lastModified: new Date().toISOString(),
      createdAt: new Date().toISOString(),
      successRate: 85,
      difficulty: 0.6,
      popularity: 0.8,
      duration: 120,
      requiredResources: ['computer', 'textbook'],
      preferredTimeSlots: ['morning'],
      frequency: 'weekly',
      color: '#1890ff',
      restrictions: [],
    };

    test('should fetch courses with pagination', async () => {
      const mockResponse = {
        success: true,
        data: [mockCourse],
        message: 'Success',
        timestamp: new Date().toISOString(),
        version: '1.0.0',
        pagination: {
          page: 1,
          limit: 10,
          total: 1,
          totalPages: 1,
          hasNext: false,
          hasPrev: false,
        },
      };

      (fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
        headers: new Headers({ 'content-type': 'application/json' }),
      });

      const result = await apiService.getCourses({
        page: 1,
        limit: 10,
        department: 'Computer Science',
      });

      expect(fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/courses?page=1&limit=10&department=Computer%20Science',
        expect.objectContaining({
          method: 'GET',
        })
      );

      expect(result).toEqual(mockResponse);
    });

    test('should create new course', async () => {
      const newCourseData = {
        code: 'CS102',
        name: 'Data Structures',
        description: 'Introduction to data structures',
        department: 'Computer Science',
        credits: 3,
        level: 'undergraduate' as const,
        status: 'draft' as const,
        maxCapacity: 25,
        currentEnrollment: 0,
        waitlistCount: 0,
        prerequisites: ['CS101'],
        corequisites: [],
        instructors: [],
        schedule: [],
        tuition: 1500,
        tags: ['programming', 'data-structures'],
        successRate: 0,
        difficulty: 0.7,
        popularity: 0.6,
        duration: 120,
        requiredResources: ['computer'],
        preferredTimeSlots: ['afternoon'],
        frequency: 'weekly' as const,
        color: '#52c41a',
        restrictions: [],
      };

      const mockResponse = {
        success: true,
        data: { id: 'course-456', ...newCourseData },
        message: 'Course created',
        timestamp: new Date().toISOString(),
        version: '1.0.0',
      };

      (fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
        headers: new Headers({ 'content-type': 'application/json' }),
      });

      const result = await apiService.createCourse(newCourseData);

      expect(fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/courses',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(newCourseData),
        })
      );

      expect(result).toEqual(mockResponse);
    });
  });

  describe('Enrollment Management', () => {
    test('should validate enrollment eligibility', async () => {
      const mockResponse = {
        success: true,
        data: {
          eligible: true,
          issues: [],
          warnings: ['Course is nearly full'],
          recommendations: ['Register soon to secure a spot'],
        },
        message: 'Eligibility checked',
        timestamp: new Date().toISOString(),
        version: '1.0.0',
      };

      (fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
        headers: new Headers({ 'content-type': 'application/json' }),
      });

      const result = await apiService.validateEnrollmentEligibility(
        'student-123',
        'course-456'
      );

      expect(fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/enrollments/validate',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            studentId: 'student-123',
            courseId: 'course-456',
          }),
        })
      );

      expect(result).toEqual(mockResponse);
    });
  });

  describe('Schedule Management', () => {
    test('should detect schedule conflicts', async () => {
      const mockResponse = {
        success: true,
        data: {
          conflicts: [
            {
              type: 'room',
              description: 'Room A101 is double-booked',
              severity: 'high',
              affectedItems: ['course-123', 'course-456'],
              suggestions: ['Move one course to a different room'],
            },
          ],
        },
        message: 'Conflicts detected',
        timestamp: new Date().toISOString(),
        version: '1.0.0',
      };

      (fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
        headers: new Headers({ 'content-type': 'application/json' }),
      });

      const result = await apiService.detectScheduleConflicts();

      expect(fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/schedule/conflicts/current',
        expect.objectContaining({
          method: 'GET',
        })
      );

      expect(result).toEqual(mockResponse);
    });

    test('should optimize schedule with AI', async () => {
      const constraints = {
        minimizeConflicts: true,
        maximizeUtilization: true,
        respectPreferences: false,
        balanceWorkload: true,
      };

      const mockResponse = {
        success: true,
        data: {
          optimizedSchedule: {},
          improvements: {
            conflictsReduced: 5,
            utilizationIncrease: 15,
            satisfactionScore: 85,
          },
          suggestions: [
            {
              type: 'move',
              description: 'Move CS101 to Room B202',
              impact: 'Resolves room conflict',
              effort: 'low',
            },
          ],
        },
        message: 'Schedule optimized',
        timestamp: new Date().toISOString(),
        version: '1.0.0',
      };

      (fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
        headers: new Headers({ 'content-type': 'application/json' }),
      });

      const result = await apiService.optimizeSchedule(constraints);

      expect(fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/schedule/optimize',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(constraints),
        })
      );

      expect(result).toEqual(mockResponse);
    });
  });

  describe('AI Integration', () => {
    test('should get student recommendations', async () => {
      const context = {
        careerGoals: ['software-engineering'],
        interests: ['programming', 'algorithms'],
        timeConstraints: ['morning', 'afternoon'],
      };

      const mockResponse = {
        success: true,
        data: {
          courses: [
            {
              course: mockCourse,
              score: 0.92,
              reasoning: ['Strong match for career goals', 'Good prerequisite alignment'],
              successProbability: 0.87,
            },
          ],
          insights: ['Your strong GPA opens many advanced course options'],
        },
        message: 'Recommendations generated',
        timestamp: new Date().toISOString(),
        version: '1.0.0',
      };

      (fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
        headers: new Headers({ 'content-type': 'application/json' }),
      });

      const result = await apiService.getStudentRecommendations(
        'student-123',
        context
      );

      expect(fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/ai/students/student-123/recommendations',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(context),
        })
      );

      expect(result).toEqual(mockResponse);
    });

    test('should identify at-risk students', async () => {
      const params = {
        threshold: 0.7,
        courseId: 'course-123',
      };

      const mockResponse = {
        success: true,
        data: [
          {
            student: { id: 'student-456', name: 'John Doe' } as Student,
            riskLevel: 'high',
            riskFactors: ['Low GPA', 'Poor attendance'],
            interventions: ['Schedule counseling', 'Recommend tutoring'],
            probability: 0.85,
          },
        ],
        message: 'At-risk students identified',
        timestamp: new Date().toISOString(),
        version: '1.0.0',
      };

      (fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
        headers: new Headers({ 'content-type': 'application/json' }),
      });

      const result = await apiService.getAtRiskStudents(params);

      expect(fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/ai/students/at-risk?threshold=0.7&courseId=course-123',
        expect.objectContaining({
          method: 'GET',
        })
      );

      expect(result).toEqual(mockResponse);
    });
  });

  describe('Error Handling', () => {
    test('should handle HTTP errors', async () => {
      (fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: async () => ({ message: 'Course not found' }),
      });

      await expect(apiService.getCourse('nonexistent-course')).rejects.toThrow(
        'Course not found'
      );
    });

    test('should retry on network errors', async () => {
      // First two calls fail, third succeeds
      (fetch as any)
        .mockRejectedValueOnce(new Error('Network error'))
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ success: true, data: mockCourse }),
          headers: new Headers({ 'content-type': 'application/json' }),
        });

      const result = await apiService.getCourse('course-123');

      expect(fetch).toHaveBeenCalledTimes(3);
      expect(result.data).toEqual(mockCourse);
    });

    test('should fail after max retries', async () => {
      // All calls fail
      (fetch as any)
        .mockRejectedValueOnce(new Error('Network error'))
        .mockRejectedValueOnce(new Error('Network error'))
        .mockRejectedValueOnce(new Error('Network error'));

      await expect(apiService.getCourse('course-123')).rejects.toThrow(
        'Network error'
      );

      expect(fetch).toHaveBeenCalledTimes(3); // Original + 2 retries
    });
  });

  describe('File Operations', () => {
    test('should upload file successfully', async () => {
      const mockFile = new File(['test content'], 'test.csv', {
        type: 'text/csv',
      });

      const mockResponse = {
        success: true,
        data: {
          fileId: 'file-123',
          url: 'http://example.com/file-123',
        },
        message: 'File uploaded',
        timestamp: new Date().toISOString(),
        version: '1.0.0',
      };

      (fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
        headers: new Headers({ 'content-type': 'application/json' }),
      });

      const result = await apiService.uploadFile(
        mockFile,
        '/uploads/grades',
        { courseId: 'course-123' }
      );

      expect(fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/uploads/grades',
        expect.objectContaining({
          method: 'POST',
          body: expect.any(FormData),
        })
      );

      expect(result).toEqual(mockResponse);
    });
  });

  describe('Caching and Performance', () => {
    test('should handle request timeout', async () => {
      // Mock a slow response
      (fetch as any).mockImplementationOnce(
        () => new Promise(resolve => setTimeout(resolve, 10000))
      );

      await expect(
        apiService.getCourse('course-123')
      ).rejects.toThrow();
    });
  });
});

// Integration tests
describe('Academic API Integration', () => {
  test('should handle complete grade workflow', async () => {
    // Mock sequence: get grades -> update grade -> get updated grades
    const mockGrades = {
      success: true,
      data: { students: [], assignments: [], grades: [] },
      message: 'Success',
      timestamp: new Date().toISOString(),
      version: '1.0.0',
    };

    const mockUpdateResponse = {
      success: true,
      data: { id: 'grade-123', points: 85 },
      message: 'Grade updated',
      timestamp: new Date().toISOString(),
      version: '1.0.0',
    };

    (fetch as any)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockGrades,
        headers: new Headers({ 'content-type': 'application/json' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockUpdateResponse,
        headers: new Headers({ 'content-type': 'application/json' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockGrades,
        headers: new Headers({ 'content-type': 'application/json' }),
      });

    // Execute workflow
    const initialGrades = await academicApi.getClassGrades('class-123');
    expect(initialGrades.success).toBe(true);

    const updateResult = await academicApi.updateGrade('grade-123', { points: 85 });
    expect(updateResult.success).toBe(true);

    const updatedGrades = await academicApi.getClassGrades('class-123');
    expect(updatedGrades.success).toBe(true);

    expect(fetch).toHaveBeenCalledTimes(3);
  });
});