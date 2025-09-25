/**
 * Student and People related TypeScript type definitions
 * Matches the Django-Ninja API schemas for consistent frontend-backend communication
 */

export interface PersonBase {
  unique_id: string;
  family_name: string;
  personal_name: string;
  full_name: string;
  khmer_name: string;
  preferred_gender: string;
  school_email?: string;
  personal_email?: string;
  date_of_birth?: string;
  birth_province?: string;
  citizenship: string;
  age?: number;
  display_name: string;
  current_photo_url?: string;
  current_thumbnail_url?: string;
}

export interface PhoneNumber {
  id: number;
  number: string;
  comment: string;
  is_preferred: boolean;
  is_telegram: boolean;
  is_verified: boolean;
}

export interface Contact {
  id: number;
  name: string;
  relationship: string;
  primary_phone: string;
  secondary_phone: string;
  email: string;
  address: string;
  is_emergency_contact: boolean;
  is_general_contact: boolean;
}

export interface StudentProfile {
  id: number;
  student_id: number;
  formatted_student_id: string;
  legacy_ipk?: number;
  is_monk: boolean;
  is_transfer_student: boolean;
  current_status: string;
  study_time_preference: string;
  last_enrollment_date?: string;
  is_student_active: boolean;
  has_major_conflict: boolean;
  declared_major_name?: string;
  enrollment_history_major_name?: string;
}

export interface TeacherProfile {
  id: number;
  terminal_degree: string;
  status: string;
  start_date: string;
  end_date?: string;
  is_teacher_active: boolean;
}

export interface StaffProfile {
  id: number;
  position: string;
  status: string;
  start_date: string;
  end_date?: string;
  is_staff_active: boolean;
}

export interface PersonDetail extends PersonBase {
  student_profile?: StudentProfile;
  teacher_profile?: TeacherProfile;
  staff_profile?: StaffProfile;
  phone_numbers: PhoneNumber[];
  contacts: Contact[];
  has_student_role: boolean;
  has_teacher_role: boolean;
  has_staff_role: boolean;
}

export interface StudentListItem {
  person_id: number;
  student_id: number;
  formatted_student_id: string;
  full_name: string;
  khmer_name: string;
  school_email?: string;
  current_status: string;
  study_time_preference: string;
  is_monk: boolean;
  current_thumbnail_url?: string;
  declared_major_name?: string;
}

export interface PersonSearchResult {
  person_id: number;
  full_name: string;
  khmer_name: string;
  school_email?: string;
  current_thumbnail_url?: string;
  roles: string[];
  student_id?: number;
  formatted_student_id?: string;
  student_status?: string;
  teacher_status?: string;
  position?: string;
}

// Curriculum types
export interface Division {
  id: number;
  name: string;
  short_name: string;
  description: string;
  is_active: boolean;
  display_order: number;
}

export interface Cycle {
  id: number;
  name: string;
  short_name: string;
  description: string;
  division: Division;
  level_order: number;
  is_active: boolean;
}

export interface Major {
  id: number;
  name: string;
  short_name: string;
  description: string;
  program_type: string;
  degree_type: string;
  division: Division;
  cycle: Cycle;
  required_credits?: number;
  max_terms?: number;
  is_active: boolean;
  is_accepting_students: boolean;
  display_order: number;
}

export interface Term {
  id: number;
  name: string;
  short_name: string;
  start_date: string;
  end_date: string;
  term_type: string;
  academic_year: number;
  is_current: boolean;
  is_registration_open: boolean;
  cohort_year?: number;
}

export interface Course {
  id: number;
  code: string;
  name: string;
  description: string;
  credit_hours?: number;
  level?: number;
  course_type: string;
  division: Division;
  is_active: boolean;
  can_repeat: boolean;
}

// Enrollment types
export interface ProgramEnrollment {
  id: number;
  student_id: number;
  student_name: string;
  major: Major;
  enrollment_type: string;
  enrollment_status: string;
  division: string;
  cycle: string;
  start_date?: string;
  end_date?: string;
  expected_graduation?: string;
  entry_level?: number;
  finishing_level?: number;
  terms_active: number;
  terms_on_hold: number;
  overall_gpa?: number;
  is_active: boolean;
  is_current: boolean;
}

export interface MajorDeclaration {
  id: number;
  student_id: number;
  student_name: string;
  major: Major;
  declaration_date: string;
  is_active: boolean;
  is_prospective: boolean;
  intended_graduation_term?: string;
  notes: string;
}

export interface ClassHeader {
  id: number;
  class_number: string;
  course_code: string;
  course_name: string;
  term_name: string;
  teacher_name?: string;
  room_name?: string;
  max_enrollment?: number;
  current_enrollment: number;
}

export interface ClassEnrollment {
  id: number;
  student: {
    id: number;
    student_id: number;
    name: string;
  };
  class_header: ClassHeader;
  enrollment_date: string;
  status: string;
  grade_override?: string;
  is_auditing: boolean;
  notes: string;
  tuition_waived: boolean;
  discount_percentage?: number;
}

export interface StudentEnrollmentSummary {
  student_id: number;
  student_name: string;
  current_status: string;
  active_program_enrollments: ProgramEnrollment[];
  major_declarations: MajorDeclaration[];
  current_class_enrollments: ClassEnrollment[];
  total_active_enrollments: number;
  total_completed_courses: number;
  current_term_credit_hours: number;
}

// API Response types
export interface PaginatedResponse<T> {
  count: number;
  next?: string;
  previous?: string;
  results: T[];
}

export interface SelectOption {
  value: string;
  label: string;
}

// Search and filter types
export interface StudentFilters {
  status?: string;
  search?: string;
  page?: number;
  page_size?: number;
}

export interface PersonSearchFilters {
  q: string;
  roles?: string[];
  page?: number;
  page_size?: number;
}

// Form types
export interface CreatePersonData {
  family_name: string;
  personal_name: string;
  khmer_name?: string;
  preferred_gender?: string;
  school_email?: string;
  personal_email?: string;
  date_of_birth?: string;
  birth_province?: string;
  citizenship?: string;
}

export interface UpdatePersonData {
  family_name?: string;
  personal_name?: string;
  khmer_name?: string;
  preferred_gender?: string;
  school_email?: string;
  personal_email?: string;
  date_of_birth?: string;
  birth_province?: string;
  citizenship?: string;
}

export interface CreateStudentProfileData {
  student_id: number;
  is_monk?: boolean;
  is_transfer_student?: boolean;
  study_time_preference?: string;
  current_status?: string;
}

export interface UpdateStudentProfileData {
  is_monk?: boolean;
  is_transfer_student?: boolean;
  study_time_preference?: string;
  current_status?: string;
}

// Student status constants
export const STUDENT_STATUSES = [
  'ACTIVE',
  'INACTIVE',
  'GRADUATED',
  'DROPPED',
  'SUSPENDED',
  'TRANSFERRED',
  'FROZEN',
  'UNKNOWN'
] as const;

export type StudentStatus = typeof STUDENT_STATUSES[number];

export const STUDY_TIME_PREFERENCES = [
  'morning',
  'afternoon',
  'evening'
] as const;

export type StudyTimePreference = typeof STUDY_TIME_PREFERENCES[number];

export const GENDER_CHOICES = [
  'M',
  'F',
  'N',
  'X'
] as const;

export type Gender = typeof GENDER_CHOICES[number];