/**
 * Student GraphQL Service
 *
 * GraphQL client for efficient student data fetching:
 * - Optimized queries with field selection
 * - Real-time subscriptions
 * - Caching and normalization
 * - Batch operations
 * - Error handling
 */

import { gql } from 'graphql-request';
import { GraphQLClient } from '../../../services/graphql';
import type { Student, StudentSearchParams } from '../types/Student';

class StudentGraphQLService {
  private client: GraphQLClient;

  constructor() {
    this.client = new GraphQLClient();
  }

  // Fragment definitions for reusable field sets
  private readonly STUDENT_CORE_FIELDS = gql`
    fragment StudentCoreFields on Student {
      id
      studentId
      firstName
      lastName
      fullName
      email
      phone
      status
      photoUrl
      hasAlerts
      createdAt
      updatedAt
    }
  `;

  private readonly STUDENT_DETAIL_FIELDS = gql`
    fragment StudentDetailFields on Student {
      ...StudentCoreFields
      dateOfBirth
      gender
      nationality
      address
      city
      state
      postalCode
      country
      program
      academicYear
      enrollmentDate
      gpa
      creditsCompleted
      emergencyContact {
        name
        relationship
        phone
        email
      }
      tags
      notes {
        id
        content
        author
        timestamp
      }
      alerts {
        id
        type
        severity
        message
        createdAt
      }
    }
    ${this.STUDENT_CORE_FIELDS}
  `;

  private readonly ENROLLMENT_FIELDS = gql`
    fragment EnrollmentFields on Enrollment {
      id
      status
      enrollmentDate
      completionDate
      grade
      course {
        id
        code
        name
        credits
      }
      classHeader {
        id
        section
        schedule
        instructor {
          id
          name
        }
      }
    }
  `;

  // Query definitions

  /**
   * Get students with pagination and filtering
   */
  async getStudents(params: {
    first?: number;
    after?: string;
    search?: string;
    filters?: any;
    orderBy?: string;
  }) {
    const query = gql`
      query GetStudents(
        $first: Int
        $after: String
        $search: String
        $filters: StudentFiltersInput
        $orderBy: StudentOrderByInput
      ) {
        students(
          first: $first
          after: $after
          search: $search
          filters: $filters
          orderBy: $orderBy
        ) {
          edges {
            node {
              ...StudentCoreFields
            }
            cursor
          }
          pageInfo {
            hasNextPage
            hasPreviousPage
            startCursor
            endCursor
          }
          totalCount
        }
      }
      ${this.STUDENT_CORE_FIELDS}
    `;

    return this.client.request(query, params);
  }

  /**
   * Get detailed student information
   */
  async getStudentDetail(id: string) {
    const query = gql`
      query GetStudentDetail($id: ID!) {
        student(id: $id) {
          ...StudentDetailFields
          enrollments {
            ...EnrollmentFields
          }
          academicHistory {
            term
            gpa
            credits
            courses {
              code
              name
              grade
            }
          }
          financialSummary {
            totalTuition
            amountPaid
            balance
            scholarships
          }
          communicationHistory {
            id
            type
            subject
            content
            sentAt
            status
          }
        }
      }
      ${this.STUDENT_DETAIL_FIELDS}
      ${this.ENROLLMENT_FIELDS}
    `;

    return this.client.request(query, { id });
  }

  /**
   * Search students with advanced filters
   */
  async searchStudents(searchParams: StudentSearchParams) {
    const query = gql`
      query SearchStudents($input: StudentSearchInput!) {
        searchStudents(input: $input) {
          students {
            ...StudentCoreFields
            matchScore
            matchReasons
          }
          totalCount
          suggestions
          facets {
            field
            values {
              value
              count
            }
          }
        }
      }
      ${this.STUDENT_CORE_FIELDS}
    `;

    return this.client.request(query, { input: searchParams });
  }

  /**
   * Get student analytics data
   */
  async getStudentAnalytics(studentId: string, timeframe: string) {
    const query = gql`
      query GetStudentAnalytics($studentId: ID!, $timeframe: String!) {
        studentAnalytics(studentId: $studentId, timeframe: $timeframe) {
          academicPerformance {
            currentGPA
            gpaHistory {
              term
              gpa
            }
            creditsCompleted
            creditsRequired
            attendanceRate
            averageGrade
          }
          engagementMetrics {
            loginFrequency
            assignmentSubmissionRate
            forumParticipation
            libraryUsage
          }
          riskAssessment {
            overallRisk
            academicRisk
            financialRisk
            attendanceRisk
            factors {
              type
              severity
              description
            }
          }
          predictions {
            graduationProbability
            gpaProjection
            timeToGraduation
            recommendedInterventions
          }
          cohortComparison {
            percentile
            averageGPA
            averageAttendance
            rank
          }
        }
      }
    `;

    return this.client.request(query, { studentId, timeframe });
  }

  /**
   * Get available courses for enrollment
   */
  async getAvailableCoursesForStudent(studentId: string) {
    const query = gql`
      query GetAvailableCoursesForStudent($studentId: ID!) {
        student(id: $studentId) {
          id
          availableCourses {
            id
            code
            name
            description
            credits
            prerequisites {
              id
              code
              name
            }
            classHeaders {
              id
              section
              capacity
              enrolled
              waitlisted
              schedule
              instructor {
                id
                name
              }
              meetingTimes {
                day
                startTime
                endTime
                location
              }
            }
          }
        }
      }
    `;

    return this.client.request(query, { studentId });
  }

  /**
   * Get student enrollment history
   */
  async getStudentEnrollmentHistory(studentId: string) {
    const query = gql`
      query GetStudentEnrollmentHistory($studentId: ID!) {
        student(id: $studentId) {
          id
          enrollmentHistory {
            term
            enrollments {
              ...EnrollmentFields
              finalGrade
              gradePoints
            }
            termGPA
            cumulativeGPA
            creditsEarned
            creditsAttempted
          }
        }
      }
      ${this.ENROLLMENT_FIELDS}
    `;

    return this.client.request(query, { studentId });
  }

  /**
   * Get student communication preferences
   */
  async getStudentCommunicationPreferences(studentId: string) {
    const query = gql`
      query GetStudentCommunicationPreferences($studentId: ID!) {
        student(id: $studentId) {
          id
          communicationPreferences {
            email
            sms
            push
            phone
            preferredLanguage
            timezone
            frequency
          }
        }
      }
    `;

    return this.client.request(query, { studentId });
  }

  /**
   * Get student financial information
   */
  async getStudentFinancialInfo(studentId: string) {
    const query = gql`
      query GetStudentFinancialInfo($studentId: ID!) {
        student(id: $studentId) {
          id
          financialInfo {
            totalTuition
            amountPaid
            balance
            scholarships {
              id
              name
              amount
              startDate
              endDate
              status
            }
            paymentHistory {
              id
              amount
              date
              method
              status
              reference
            }
            upcomingPayments {
              amount
              dueDate
              description
            }
          }
        }
      }
    `;

    return this.client.request(query, { studentId });
  }

  // Mutation definitions

  /**
   * Create a new student
   */
  async createStudent(input: any) {
    const mutation = gql`
      mutation CreateStudent($input: CreateStudentInput!) {
        createStudent(input: $input) {
          student {
            ...StudentDetailFields
          }
          errors {
            field
            message
          }
        }
      }
      ${this.STUDENT_DETAIL_FIELDS}
    `;

    return this.client.request(mutation, { input });
  }

  /**
   * Update student information
   */
  async updateStudent(id: string, input: any) {
    const mutation = gql`
      mutation UpdateStudent($id: ID!, $input: UpdateStudentInput!) {
        updateStudent(id: $id, input: $input) {
          student {
            ...StudentDetailFields
          }
          errors {
            field
            message
          }
        }
      }
      ${this.STUDENT_DETAIL_FIELDS}
    `;

    return this.client.request(mutation, { id, input });
  }

  /**
   * Delete a student
   */
  async deleteStudent(id: string) {
    const mutation = gql`
      mutation DeleteStudent($id: ID!) {
        deleteStudent(id: $id) {
          success
          errors {
            field
            message
          }
        }
      }
    `;

    return this.client.request(mutation, { id });
  }

  /**
   * Enroll student in courses
   */
  async enrollStudentInCourses(studentId: string, courseIds: string[]) {
    const mutation = gql`
      mutation EnrollStudentInCourses($studentId: ID!, $courseIds: [ID!]!) {
        enrollStudentInCourses(studentId: $studentId, courseIds: $courseIds) {
          enrollments {
            ...EnrollmentFields
          }
          errors {
            courseId
            message
          }
        }
      }
      ${this.ENROLLMENT_FIELDS}
    `;

    return this.client.request(mutation, { studentId, courseIds });
  }

  /**
   * Withdraw student from course
   */
  async withdrawStudentFromCourse(enrollmentId: string, reason?: string) {
    const mutation = gql`
      mutation WithdrawStudentFromCourse($enrollmentId: ID!, $reason: String) {
        withdrawStudentFromCourse(enrollmentId: $enrollmentId, reason: $reason) {
          success
          enrollment {
            ...EnrollmentFields
          }
          errors {
            field
            message
          }
        }
      }
      ${this.ENROLLMENT_FIELDS}
    `;

    return this.client.request(mutation, { enrollmentId, reason });
  }

  /**
   * Add note to student
   */
  async addStudentNote(studentId: string, content: string) {
    const mutation = gql`
      mutation AddStudentNote($studentId: ID!, $content: String!) {
        addStudentNote(studentId: $studentId, content: $content) {
          note {
            id
            content
            author
            timestamp
          }
          errors {
            field
            message
          }
        }
      }
    `;

    return this.client.request(mutation, { studentId, content });
  }

  // Subscription definitions

  /**
   * Subscribe to student updates
   */
  subscribeToStudentUpdates(studentId: string) {
    const subscription = gql`
      subscription StudentUpdates($studentId: ID!) {
        studentUpdates(studentId: $studentId) {
          type
          student {
            ...StudentCoreFields
          }
          changes {
            field
            oldValue
            newValue
          }
          timestamp
        }
      }
      ${this.STUDENT_CORE_FIELDS}
    `;

    return this.client.subscribe(subscription, { studentId });
  }

  /**
   * Subscribe to enrollment updates
   */
  subscribeToEnrollmentUpdates(studentId: string) {
    const subscription = gql`
      subscription EnrollmentUpdates($studentId: ID!) {
        enrollmentUpdates(studentId: $studentId) {
          type
          enrollment {
            ...EnrollmentFields
          }
          timestamp
        }
      }
      ${this.ENROLLMENT_FIELDS}
    `;

    return this.client.subscribe(subscription, { studentId });
  }

  // Batch operations

  /**
   * Batch fetch students by IDs
   */
  async batchGetStudents(ids: string[]) {
    const query = gql`
      query BatchGetStudents($ids: [ID!]!) {
        students: nodes(ids: $ids) {
          ... on Student {
            ...StudentCoreFields
          }
        }
      }
      ${this.STUDENT_CORE_FIELDS}
    `;

    return this.client.request(query, { ids });
  }

  /**
   * Batch update student statuses
   */
  async batchUpdateStudentStatuses(updates: Array<{ id: string; status: string }>) {
    const mutation = gql`
      mutation BatchUpdateStudentStatuses($updates: [StudentStatusUpdateInput!]!) {
        batchUpdateStudentStatuses(updates: $updates) {
          results {
            studentId
            success
            student {
              ...StudentCoreFields
            }
            errors {
              field
              message
            }
          }
        }
      }
      ${this.STUDENT_CORE_FIELDS}
    `;

    return this.client.request(mutation, { updates });
  }
}

// Export singleton instance
export const studentGraphQLService = new StudentGraphQLService();
export default studentGraphQLService;