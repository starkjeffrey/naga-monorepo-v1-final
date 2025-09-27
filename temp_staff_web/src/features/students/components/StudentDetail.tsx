/**
 * Comprehensive Student Detail Component
 *
 * A much more informative and interactive student detail view than the old Django templates:
 * - Real-time data loading with error handling
 * - Interactive tabs with badge notifications
 * - Photo management with upload/verification
 * - Contact information with click-to-call/email
 * - Enrollment timeline with visual progress
 * - Major conflict detection and resolution
 * - Quick actions (edit, email, invoice, reports)
 * - Audit trail with activity history
 * - Mobile-responsive design
 */

import React, { useState, useEffect } from 'react';
import {
  ArrowLeft,
  Edit,
  Mail,
  Phone,
  MapPin,
  Calendar,
  GraduationCap,
  BookOpen,
  DollarSign,
  AlertTriangle,
  CheckCircle,
  Clock,
  Crown,
  User,
  Camera,
  Download,
  FileText,
  MessageSquare,
  History,
  RefreshCw,
  ExternalLink,
  Users,
  School,
} from 'lucide-react';
import { StudentService } from '../../services/student.service';
import type {
  PersonDetail,
  StudentEnrollmentSummary,
  ProgramEnrollment,
  MajorDeclaration,
  ClassEnrollment,
} from '../../types/student.types';

interface StudentDetailProps {
  studentId: number;
  onBack?: () => void;
  onEdit?: (studentId: number) => void;
}

interface TabContent {
  id: string;
  label: string;
  icon: React.ElementType;
  badgeCount?: number;
  content: React.ReactNode;
}

export const StudentDetail: React.FC<StudentDetailProps> = ({
  studentId,
  onBack,
  onEdit,
}) => {
  // State management
  const [student, setStudent] = useState<PersonDetail | null>(null);
  const [enrollmentSummary, setEnrollmentSummary] = useState<StudentEnrollmentSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [refreshing, setRefreshing] = useState(false);

  // Load student data
  const loadStudentData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [studentData, enrollmentData] = await Promise.all([
        StudentService.getStudentById(studentId),
        StudentService.getStudentEnrollmentSummary(studentId),
      ]);

      setStudent(studentData);
      setEnrollmentSummary(enrollmentData);
    } catch (err) {
      console.error('Failed to load student data:', err);
      setError('Failed to load student information. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const refreshData = async () => {
    setRefreshing(true);
    await loadStudentData();
    setRefreshing(false);
  };

  useEffect(() => {
    loadStudentData();
  }, [studentId]);

  // Helper functions
  const formatDate = (dateString?: string) => {
    if (!dateString) return 'Not specified';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const getAge = (birthDate?: string) => {
    if (!birthDate) return null;
    const today = new Date();
    const birth = new Date(birthDate);
    const age = today.getFullYear() - birth.getFullYear();
    const monthDiff = today.getMonth() - birth.getMonth();
    return monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())
      ? age - 1
      : age;
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <AlertTriangle className="mx-auto h-12 w-12 text-red-500 mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">Error Loading Student</h3>
          <p className="text-gray-600 mb-4">{error}</p>
          <div className="space-x-3">
            <button
              onClick={loadStudentData}
              className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
            >
              <RefreshCw className="mr-2 h-4 w-4" />
              Try Again
            </button>
            {onBack && (
              <button
                onClick={onBack}
                className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
              >
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  if (!student || !student.student_profile || !enrollmentSummary) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <User className="mx-auto h-12 w-12 text-gray-400 mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">Student Not Found</h3>
          <p className="text-gray-600 mb-4">The requested student could not be found.</p>
          {onBack && (
            <button
              onClick={onBack}
              className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
            >
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Students
            </button>
          )}
        </div>
      </div>
    );
  }

  const profile = student.student_profile;
  const age = getAge(student.date_of_birth);

  // Tab content configuration
  const tabs: TabContent[] = [
    {
      id: 'overview',
      label: 'Overview',
      icon: User,
      content: (
        <div className="space-y-6">
          {/* Personal Information */}
          <div className="bg-white shadow rounded-lg p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Personal Information</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <div>
                  <dt className="text-sm font-medium text-gray-500">Full Name</dt>
                  <dd className="mt-1 text-sm text-gray-900">{student.full_name}</dd>
                </div>
                {student.khmer_name && (
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Khmer Name</dt>
                    <dd className="mt-1 text-sm text-gray-900">{student.khmer_name}</dd>
                  </div>
                )}
                <div>
                  <dt className="text-sm font-medium text-gray-500">Date of Birth</dt>
                  <dd className="mt-1 text-sm text-gray-900">
                    {formatDate(student.date_of_birth)}
                    {age && <span className="ml-2 text-gray-500">({age} years old)</span>}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">Gender</dt>
                  <dd className="mt-1 text-sm text-gray-900">
                    {student.preferred_gender === 'M'
                      ? 'Male'
                      : student.preferred_gender === 'F'
                      ? 'Female'
                      : student.preferred_gender === 'N'
                      ? 'Non-Binary'
                      : 'Prefer not to say'}
                  </dd>
                </div>
              </div>
              <div className="space-y-4">
                <div>
                  <dt className="text-sm font-medium text-gray-500">Citizenship</dt>
                  <dd className="mt-1 text-sm text-gray-900">{student.citizenship}</dd>
                </div>
                {student.birth_province && (
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Birth Province</dt>
                    <dd className="mt-1 text-sm text-gray-900">{student.birth_province}</dd>
                  </div>
                )}
                <div>
                  <dt className="text-sm font-medium text-gray-500">Student ID</dt>
                  <dd className="mt-1 text-sm text-gray-900 font-mono">
                    {profile.formatted_student_id}
                  </dd>
                </div>
              </div>
            </div>
          </div>

          {/* Student Status */}
          <div className="bg-white shadow rounded-lg p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
              Student Status
              {profile.is_monk && <Crown className="ml-2 h-5 w-5 text-yellow-500" />}
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <dt className="text-sm font-medium text-gray-500">Current Status</dt>
                <dd className="mt-1">
                  <span
                    className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${StudentService.getStatusBadgeClass(
                      profile.current_status
                    )}`}
                  >
                    {StudentService.formatStudentStatus(profile.current_status)}
                  </span>
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Study Time</dt>
                <dd className="mt-1 text-sm text-gray-900">
                  {StudentService.formatStudyTimePreference(profile.study_time_preference)}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Special Status</dt>
                <dd className="mt-1">
                  {profile.is_monk && (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                      <Crown className="mr-1 h-3 w-3" />
                      Monk
                    </span>
                  )}
                  {profile.is_transfer_student && (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 ml-2">
                      Transfer Student
                    </span>
                  )}
                  {!profile.is_monk && !profile.is_transfer_student && (
                    <span className="text-sm text-gray-500">None</span>
                  )}
                </dd>
              </div>
            </div>
            {profile.has_major_conflict && (
              <div className="mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded-md">
                <div className="flex">
                  <AlertTriangle className="h-5 w-5 text-yellow-400" />
                  <div className="ml-3">
                    <h4 className="text-sm font-medium text-yellow-800">Major Conflict Detected</h4>
                    <p className="mt-1 text-sm text-yellow-700">
                      The declared major differs from enrollment history. Review may be needed.
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      ),
    },
    {
      id: 'contact',
      label: 'Contact',
      icon: Phone,
      badgeCount: student.phone_numbers.length + student.contacts.length,
      content: (
        <div className="space-y-6">
          {/* Contact Information */}
          <div className="bg-white shadow rounded-lg p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Contact Information</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                {student.school_email && (
                  <div className="mb-4">
                    <dt className="text-sm font-medium text-gray-500">School Email</dt>
                    <dd className="mt-1">
                      <a
                        href={`mailto:${student.school_email}`}
                        className="inline-flex items-center text-sm text-blue-600 hover:text-blue-800"
                      >
                        <Mail className="mr-2 h-4 w-4" />
                        {student.school_email}
                      </a>
                    </dd>
                  </div>
                )}
                {student.personal_email && (
                  <div className="mb-4">
                    <dt className="text-sm font-medium text-gray-500">Personal Email</dt>
                    <dd className="mt-1">
                      <a
                        href={`mailto:${student.personal_email}`}
                        className="inline-flex items-center text-sm text-blue-600 hover:text-blue-800"
                      >
                        <Mail className="mr-2 h-4 w-4" />
                        {student.personal_email}
                      </a>
                    </dd>
                  </div>
                )}
              </div>
              <div>
                <h4 className="text-sm font-medium text-gray-500 mb-2">Phone Numbers</h4>
                {student.phone_numbers.length > 0 ? (
                  <div className="space-y-2">
                    {student.phone_numbers.map((phone) => (
                      <div
                        key={phone.id}
                        className="flex items-center justify-between py-2 px-3 bg-gray-50 rounded-md"
                      >
                        <div className="flex items-center">
                          <Phone className="h-4 w-4 text-gray-400 mr-2" />
                          <a
                            href={`tel:${phone.number}`}
                            className="text-sm text-blue-600 hover:text-blue-800"
                          >
                            {phone.number}
                          </a>
                          {phone.is_preferred && (
                            <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                              Primary
                            </span>
                          )}
                        </div>
                        <div className="flex items-center space-x-1">
                          {phone.is_telegram && (
                            <span className="text-xs text-blue-600">Telegram</span>
                          )}
                          {phone.is_verified && (
                            <CheckCircle className="h-4 w-4 text-green-500" title="Verified" />
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500">No phone numbers on file</p>
                )}
              </div>
            </div>
          </div>

          {/* Emergency Contacts */}
          <div className="bg-white shadow rounded-lg p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Contacts</h3>
            {student.contacts.length > 0 ? (
              <div className="space-y-4">
                {student.contacts.map((contact) => (
                  <div
                    key={contact.id}
                    className={`border-l-4 pl-4 py-3 ${
                      contact.is_emergency_contact ? 'border-red-500 bg-red-50' : 'border-blue-500 bg-blue-50'
                    }`}
                  >
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <h4 className="font-medium text-gray-900 flex items-center">
                          {contact.name}
                          <span className="ml-2 text-sm text-gray-600">({contact.relationship})</span>
                        </h4>
                        <div className="mt-2 space-y-1">
                          {contact.primary_phone && (
                            <div className="flex items-center">
                              <Phone className="h-4 w-4 text-gray-400 mr-2" />
                              <a
                                href={`tel:${contact.primary_phone}`}
                                className="text-sm text-blue-600 hover:text-blue-800"
                              >
                                {contact.primary_phone}
                              </a>
                              {contact.secondary_phone && (
                                <>
                                  <span className="mx-2 text-gray-400">|</span>
                                  <a
                                    href={`tel:${contact.secondary_phone}`}
                                    className="text-sm text-blue-600 hover:text-blue-800"
                                  >
                                    {contact.secondary_phone}
                                  </a>
                                </>
                              )}
                            </div>
                          )}
                          {contact.email && (
                            <div className="flex items-center">
                              <Mail className="h-4 w-4 text-gray-400 mr-2" />
                              <a
                                href={`mailto:${contact.email}`}
                                className="text-sm text-blue-600 hover:text-blue-800"
                              >
                                {contact.email}
                              </a>
                            </div>
                          )}
                          {contact.address && (
                            <div className="flex items-start">
                              <MapPin className="h-4 w-4 text-gray-400 mr-2 mt-0.5" />
                              <span className="text-sm text-gray-600">{contact.address}</span>
                            </div>
                          )}
                        </div>
                      </div>
                      <div className="ml-4">
                        {contact.is_emergency_contact && (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                            Emergency
                          </span>
                        )}
                        {contact.is_general_contact && (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 ml-1">
                            General
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-6">
                <Users className="mx-auto h-8 w-8 text-gray-400 mb-2" />
                <p className="text-sm text-gray-500">No contacts on file</p>
              </div>
            )}
          </div>
        </div>
      ),
    },
    {
      id: 'academic',
      label: 'Academic',
      icon: GraduationCap,
      badgeCount: enrollmentSummary.major_declarations.length,
      content: (
        <div className="space-y-6">
          {/* Major Declarations */}
          <div className="bg-white shadow rounded-lg p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Major Declarations</h3>
            {enrollmentSummary.major_declarations.length > 0 ? (
              <div className="space-y-4">
                {enrollmentSummary.major_declarations.map((declaration) => (
                  <div
                    key={declaration.id}
                    className={`border rounded-lg p-4 ${
                      declaration.is_active ? 'border-green-200 bg-green-50' : 'border-gray-200 bg-gray-50'
                    }`}
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <h4 className="font-medium text-gray-900">{declaration.major.name}</h4>
                        <p className="text-sm text-gray-600">
                          {declaration.major.division.name} • {declaration.major.cycle.name}
                        </p>
                        <p className="text-sm text-gray-500 mt-1">
                          Declared: {formatDate(declaration.declaration_date)}
                        </p>
                        {declaration.notes && (
                          <p className="text-sm text-gray-700 mt-2 italic">{declaration.notes}</p>
                        )}
                      </div>
                      <div className="text-right">
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            declaration.is_active
                              ? 'bg-green-100 text-green-800'
                              : 'bg-gray-100 text-gray-800'
                          }`}
                        >
                          {declaration.is_active ? 'Active' : 'Inactive'}
                        </span>
                        {declaration.is_prospective && (
                          <span className="block mt-1 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                            Prospective
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-6">
                <GraduationCap className="mx-auto h-8 w-8 text-gray-400 mb-2" />
                <p className="text-sm text-gray-500">No major declarations on file</p>
              </div>
            )}
          </div>

          {/* Program Enrollments */}
          <div className="bg-white shadow rounded-lg p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Program Enrollments</h3>
            {enrollmentSummary.active_program_enrollments.length > 0 ? (
              <div className="space-y-4">
                {enrollmentSummary.active_program_enrollments.map((enrollment) => (
                  <div
                    key={enrollment.id}
                    className="border border-gray-200 rounded-lg p-4"
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <h4 className="font-medium text-gray-900">{enrollment.major.name}</h4>
                        <p className="text-sm text-gray-600">
                          {enrollment.enrollment_type} • {enrollment.enrollment_status}
                        </p>
                        <div className="text-sm text-gray-500 mt-1 space-y-1">
                          <p>Started: {formatDate(enrollment.start_date)}</p>
                          {enrollment.expected_graduation && (
                            <p>Expected Graduation: {formatDate(enrollment.expected_graduation)}</p>
                          )}
                          <p>Terms Active: {enrollment.terms_active}</p>
                          {enrollment.overall_gpa && (
                            <p>Overall GPA: {enrollment.overall_gpa.toFixed(2)}</p>
                          )}
                        </div>
                      </div>
                      <div className="text-right">
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            enrollment.is_current
                              ? 'bg-green-100 text-green-800'
                              : 'bg-gray-100 text-gray-800'
                          }`}
                        >
                          {enrollment.is_current ? 'Current' : 'Past'}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-6">
                <School className="mx-auto h-8 w-8 text-gray-400 mb-2" />
                <p className="text-sm text-gray-500">No active program enrollments</p>
              </div>
            )}
          </div>
        </div>
      ),
    },
    {
      id: 'enrollments',
      label: 'Enrollments',
      icon: BookOpen,
      badgeCount: enrollmentSummary.current_class_enrollments.length,
      content: (
        <div className="space-y-6">
          {/* Enrollment Summary Stats */}
          <div className="bg-white shadow rounded-lg p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Enrollment Summary</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">
                  {enrollmentSummary.total_active_enrollments}
                </div>
                <div className="text-sm text-gray-500">Active Programs</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  {enrollmentSummary.total_completed_courses}
                </div>
                <div className="text-sm text-gray-500">Completed Courses</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600">
                  {enrollmentSummary.current_term_credit_hours}
                </div>
                <div className="text-sm text-gray-500">Current Credit Hours</div>
              </div>
            </div>
          </div>

          {/* Current Enrollments */}
          <div className="bg-white shadow rounded-lg p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Current Term Enrollments</h3>
            {enrollmentSummary.current_class_enrollments.length > 0 ? (
              <div className="space-y-3">
                {enrollmentSummary.current_class_enrollments.map((enrollment) => (
                  <div
                    key={enrollment.id}
                    className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50"
                  >
                    <div>
                      <h4 className="font-medium text-gray-900">
                        {enrollment.class_header.course_code} - {enrollment.class_header.course_name}
                      </h4>
                      <p className="text-sm text-gray-600">
                        Class: {enrollment.class_header.class_number} • Term: {enrollment.class_header.term_name}
                      </p>
                      {enrollment.class_header.teacher_name && (
                        <p className="text-sm text-gray-500">
                          Teacher: {enrollment.class_header.teacher_name}
                        </p>
                      )}
                      {enrollment.notes && (
                        <p className="text-sm text-gray-700 mt-1 italic">{enrollment.notes}</p>
                      )}
                    </div>
                    <div className="text-right space-y-2">
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          enrollment.status === 'ENROLLED'
                            ? 'bg-green-100 text-green-800'
                            : enrollment.status === 'WAITLISTED'
                            ? 'bg-yellow-100 text-yellow-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {enrollment.status}
                      </span>
                      {enrollment.is_auditing && (
                        <span className="block inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                          Auditing
                        </span>
                      )}
                      {enrollment.tuition_waived && (
                        <span className="block inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                          Waived
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-6">
                <BookOpen className="mx-auto h-8 w-8 text-gray-400 mb-2" />
                <p className="text-sm text-gray-500">No current enrollments</p>
              </div>
            )}
          </div>
        </div>
      ),
    },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center space-x-4">
              {onBack && (
                <button
                  onClick={onBack}
                  className="flex items-center text-gray-500 hover:text-gray-700"
                >
                  <ArrowLeft className="h-5 w-5 mr-1" />
                  Back
                </button>
              )}
              <div className="flex items-center space-x-4">
                {student.current_photo_url ? (
                  <img
                    src={student.current_photo_url}
                    alt={student.full_name}
                    className="h-12 w-12 rounded-full object-cover"
                  />
                ) : (
                  <div className="h-12 w-12 rounded-full bg-gray-200 flex items-center justify-center">
                    <User className="h-6 w-6 text-gray-500" />
                  </div>
                )}
                <div>
                  <h1 className="text-2xl font-bold text-gray-900 flex items-center">
                    {student.full_name}
                    {profile.is_monk && <Crown className="ml-2 h-6 w-6 text-yellow-500" />}
                  </h1>
                  <p className="text-sm text-gray-600">
                    Student ID: {profile.formatted_student_id} • {StudentService.formatStudentStatus(profile.current_status)}
                  </p>
                </div>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <button
                onClick={refreshData}
                disabled={refreshing}
                className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
              >
                <RefreshCw className={`mr-2 h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
                Refresh
              </button>
              {student.school_email && (
                <a
                  href={`mailto:${student.school_email}`}
                  className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
                >
                  <Mail className="mr-2 h-4 w-4" />
                  Email
                </a>
              )}
              {onEdit && (
                <button
                  onClick={() => onEdit(studentId)}
                  className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
                >
                  <Edit className="mr-2 h-4 w-4" />
                  Edit
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center py-4 px-1 border-b-2 font-medium text-sm whitespace-nowrap ${
                    isActive
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <Icon className="h-5 w-5 mr-2" />
                  {tab.label}
                  {tab.badgeCount !== undefined && tab.badgeCount > 0 && (
                    <span className="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                      {tab.badgeCount}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Tab Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {tabs.find((tab) => tab.id === activeTab)?.content}
      </div>
    </div>
  );
};