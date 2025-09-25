/**
 * Enrollment management TypeScript type definitions
 * Comprehensive types for program enrollments, major declarations, and class enrollments
 */

export interface EnrollmentBase {
  id: number;
  student_id: number;
  student_name: string;
  start_date?: string;
  end_date?: string;
  is_active: boolean;
  is_current: boolean;
}

export interface ProgramEnrollmentDetail extends EnrollmentBase {
  major: {
    id: number;
    name: string;
    short_name: string;
    program_type: string;
    degree_type: string;
    division: {
      id: number;
      name: string;
      short_name: string;
    };
    cycle: {
      id: number;
      name: string;
      level_order: number;
    };
  };
  enrollment_type: string;
  enrollment_status: string;
  expected_graduation?: string;
  entry_level?: number;
  finishing_level?: number;
  terms_active: number;
  terms_on_hold: number;
  overall_gpa?: number;
}

export interface MajorDeclarationDetail {
  id: number;
  student_id: number;
  student_name: string;
  major: {
    id: number;
    name: string;
    short_name: string;
    program_type: string;
    degree_type: string;
    division: {
      name: string;
      short_name: string;
    };
  };
  declaration_date: string;
  is_active: boolean;
  is_prospective: boolean;
  intended_graduation_term?: string;
  notes: string;
}

export interface ClassEnrollmentDetail {
  id: number;
  student: {
    id: number;
    student_id: number;
    name: string;
    formatted_student_id: string;
  };
  class_header: {
    id: number;
    class_number: string;
    course_code: string;
    course_name: string;
    term_name: string;
    teacher_name?: string;
    room_name?: string;
    max_enrollment?: number;
    current_enrollment: number;
  };
  enrollment_date: string;
  status: string;
  grade_override?: string;
  is_auditing: boolean;
  notes: string;
  tuition_waived: boolean;
  discount_percentage?: number;
}

export interface EnrollmentSummary {
  student_id: number;
  student_name: string;
  current_status: string;
  active_program_enrollments: ProgramEnrollmentDetail[];
  major_declarations: MajorDeclarationDetail[];
  current_class_enrollments: ClassEnrollmentDetail[];
  total_active_enrollments: number;
  total_completed_courses: number;
  current_term_credit_hours: number;
}

export interface EnrollmentFilters {
  student_id?: number;
  major_id?: number;
  division_id?: number;
  status?: string;
  enrollment_type?: string;
  term_id?: number;
  class_header_id?: number;
  active_only?: boolean;
  current_term_only?: boolean;
  prospective_only?: boolean;
  page?: number;
  page_size?: number;
}

export interface CreateProgramEnrollment {
  student_id: number;
  major_id: number;
  enrollment_type: string;
  enrollment_status: string;
  start_date?: string;
  expected_graduation?: string;
  entry_level?: number;
  finishing_level?: number;
}

export interface UpdateProgramEnrollment {
  enrollment_status?: string;
  expected_graduation?: string;
  entry_level?: number;
  finishing_level?: number;
  end_date?: string;
  is_active?: boolean;
}

export interface CreateMajorDeclaration {
  student_id: number;
  major_id: number;
  declaration_date: string;
  is_prospective?: boolean;
  intended_graduation_term?: string;
  notes?: string;
}

export interface UpdateMajorDeclaration {
  major_id?: number;
  is_active?: boolean;
  is_prospective?: boolean;
  intended_graduation_term?: string;
  notes?: string;
}

export interface CreateClassEnrollment {
  student_id: number;
  class_header_id: number;
  enrollment_date: string;
  status: string;
  is_auditing?: boolean;
  notes?: string;
  tuition_waived?: boolean;
  discount_percentage?: number;
}

export interface UpdateClassEnrollment {
  status?: string;
  grade_override?: string;
  is_auditing?: boolean;
  notes?: string;
  tuition_waived?: boolean;
  discount_percentage?: number;
}

// Enrollment statistics
export interface EnrollmentStatistics {
  total_students: number;
  active_students: number;
  total_enrollments: number;
  current_term_enrollments: number;
  status_breakdown: Record<string, number>;
  program_type_breakdown: Record<string, number>;
  division_breakdown: Record<string, number>;
}

// Constants
export const ENROLLMENT_STATUSES = [
  'ENROLLED',
  'WITHDRAWN',
  'COMPLETED',
  'DEFERRED',
  'SUSPENDED',
  'TRANSFERRED'
] as const;

export type EnrollmentStatus = typeof ENROLLMENT_STATUSES[number];

export const ENROLLMENT_TYPES = [
  'FULL_TIME',
  'PART_TIME',
  'AUDIT',
  'EXCHANGE',
  'VISITING'
] as const;

export type EnrollmentType = typeof ENROLLMENT_TYPES[number];

export const CLASS_ENROLLMENT_STATUSES = [
  'ENROLLED',
  'DROPPED',
  'WITHDRAWN',
  'COMPLETED',
  'INCOMPLETE',
  'FAILED',
  'AUDITED'
] as const;

export type ClassEnrollmentStatus = typeof CLASS_ENROLLMENT_STATUSES[number];

export const PROGRAM_TYPES = [
  'BACHELOR',
  'MASTER',
  'DOCTORATE',
  'CERTIFICATE',
  'DIPLOMA'
] as const;

export type ProgramType = typeof PROGRAM_TYPES[number];