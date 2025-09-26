/**
 * EnrollmentWizard Component
 *
 * Multi-step enrollment process with comprehensive validation:
 * - Step 1: Student selection with search
 * - Step 2: Program/course selection with prerequisites checking
 * - Step 3: Schedule conflict detection and resolution
 * - Step 4: Financial requirements and payment options
 * - Step 5: Review and confirmation
 * - Real-time validation and conflict detection
 * - Save draft capability with student notifications
 */

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  Card,
  Steps,
  Button,
  Space,
  Form,
  Input,
  Select,
  Table,
  Checkbox,
  Radio,
  DatePicker,
  Alert,
  Tag,
  Badge,
  Tooltip,
  Progress,
  Divider,
  Modal,
  Statistic,
  Timeline,
  notification,
  message,
} from 'antd';
import {
  UserOutlined,
  BookOutlined,
  CalendarOutlined,
  DollarOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  ClockCircleOutlined,
  SaveOutlined,
  SendOutlined,
  SearchOutlined,
  InfoCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import { Wizard, type WizardStep } from '../../../components/patterns';

const { Option } = Select;
const { Search } = Input;
const { TextArea } = Input;

interface Student {
  id: string;
  studentId: string;
  name: string;
  email: string;
  phone: string;
  program: string;
  level: string;
  gpa: number;
  credits: number;
  status: string;
  advisorId: string;
  financialHold: boolean;
  academicHold: boolean;
}

interface Course {
  id: string;
  code: string;
  name: string;
  credits: number;
  prerequisites: string[];
  corequisites: string[];
  maxCapacity: number;
  currentEnrollment: number;
  waitlistCount: number;
  tuition: number;
  schedule: CourseSchedule[];
  instructor: string;
  status: 'open' | 'closed' | 'waitlist' | 'cancelled';
  restrictions: string[];
}

interface CourseSchedule {
  dayOfWeek: string;
  startTime: string;
  endTime: string;
  room: string;
  building: string;
}

interface Program {
  id: string;
  name: string;
  code: string;
  level: string;
  department: string;
  requiredCredits: number;
  maxCredits: number;
  tuitionPerCredit: number;
  prerequisites: string[];
}

interface ScheduleConflict {
  type: 'time' | 'prerequisite' | 'capacity' | 'restriction';
  severity: 'error' | 'warning' | 'info';
  message: string;
  courseId: string;
  resolution?: string;
}

interface PaymentPlan {
  id: string;
  name: string;
  description: string;
  installments: number;
  downPayment: number;
  interestRate: number;
  fees: number;
}

interface EnrollmentDraft {
  id?: string;
  studentId: string;
  courses: string[];
  program?: string;
  paymentPlan?: string;
  specialRequests?: string;
  timestamp: string;
  step: number;
}

interface EnrollmentWizardProps {
  students: Student[];
  courses: Course[];
  programs: Program[];
  paymentPlans: PaymentPlan[];
  currentEnrollments: any[];
  onStudentSearch: (query: string) => Promise<Student[]>;
  onPrerequisiteCheck: (studentId: string, courseId: string) => Promise<{ satisfied: boolean; missing: string[] }>;
  onScheduleConflictCheck: (studentId: string, courseIds: string[]) => Promise<ScheduleConflict[]>;
  onCalculateTuition: (courseIds: string[], paymentPlanId?: string) => Promise<{ total: number; breakdown: any[] }>;
  onSaveDraft: (draft: EnrollmentDraft) => Promise<void>;
  onLoadDraft: (studentId: string) => Promise<EnrollmentDraft | null>;
  onSubmitEnrollment: (enrollment: any) => Promise<void>;
  onSendNotification: (studentId: string, message: string) => Promise<void>;
}

export const EnrollmentWizard: React.FC<EnrollmentWizardProps> = ({
  students,
  courses,
  programs,
  paymentPlans,
  currentEnrollments,
  onStudentSearch,
  onPrerequisiteCheck,
  onScheduleConflictCheck,
  onCalculateTuition,
  onSaveDraft,
  onLoadDraft,
  onSubmitEnrollment,
  onSendNotification,
}) => {
  const [form] = Form.useForm();
  const [currentStep, setCurrentStep] = useState(0);
  const [selectedStudent, setSelectedStudent] = useState<Student | null>(null);
  const [selectedCourses, setSelectedCourses] = useState<string[]>([]);
  const [selectedProgram, setSelectedProgram] = useState<string>('');
  const [conflicts, setConflicts] = useState<ScheduleConflict[]>([]);
  const [tuitionInfo, setTuitionInfo] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [draftSaved, setDraftSaved] = useState(false);
  const [validationErrors, setValidationErrors] = useState<any>({});
  const [autoSaveEnabled, setAutoSaveEnabled] = useState(true);

  // Auto-save draft
  const autoSaveDraft = useCallback(async () => {
    if (!selectedStudent || !autoSaveEnabled) return;

    const draft: EnrollmentDraft = {
      studentId: selectedStudent.id,
      courses: selectedCourses,
      program: selectedProgram,
      paymentPlan: form.getFieldValue('paymentPlan'),
      specialRequests: form.getFieldValue('specialRequests'),
      timestamp: new Date().toISOString(),
      step: currentStep,
    };

    try {
      await onSaveDraft(draft);
      setDraftSaved(true);
    } catch (error) {
      console.error('Failed to save draft:', error);
    }
  }, [selectedStudent, selectedCourses, selectedProgram, currentStep, form, autoSaveEnabled, onSaveDraft]);

  // Auto-save every 30 seconds
  useEffect(() => {
    if (autoSaveEnabled) {
      const interval = setInterval(autoSaveDraft, 30000);
      return () => clearInterval(interval);
    }
  }, [autoSaveDraft, autoSaveEnabled]);

  // Load existing draft when student is selected
  useEffect(() => {
    const loadDraft = async () => {
      if (!selectedStudent) return;

      try {
        const draft = await onLoadDraft(selectedStudent.id);
        if (draft) {
          setSelectedCourses(draft.courses);
          setSelectedProgram(draft.program || '');
          setCurrentStep(draft.step);
          form.setFieldsValue({
            paymentPlan: draft.paymentPlan,
            specialRequests: draft.specialRequests,
          });
          message.info('Loaded existing enrollment draft');
        }
      } catch (error) {
        console.error('Failed to load draft:', error);
      }
    };

    loadDraft();
  }, [selectedStudent, onLoadDraft, form]);

  // Validate prerequisites for selected courses
  const validatePrerequisites = useCallback(async () => {
    if (!selectedStudent || selectedCourses.length === 0) return;

    const errors: any = {};

    for (const courseId of selectedCourses) {
      try {
        const result = await onPrerequisiteCheck(selectedStudent.id, courseId);
        if (!result.satisfied) {
          errors[courseId] = {
            type: 'prerequisite',
            message: `Missing prerequisites: ${result.missing.join(', ')}`,
          };
        }
      } catch (error) {
        console.error('Failed to check prerequisites for course:', courseId);
      }
    }

    setValidationErrors(errors);
  }, [selectedStudent, selectedCourses, onPrerequisiteCheck]);

  // Check for schedule conflicts
  const checkScheduleConflicts = useCallback(async () => {
    if (!selectedStudent || selectedCourses.length === 0) return;

    try {
      const conflicts = await onScheduleConflictCheck(selectedStudent.id, selectedCourses);
      setConflicts(conflicts);
    } catch (error) {
      console.error('Failed to check schedule conflicts:', error);
    }
  }, [selectedStudent, selectedCourses, onScheduleConflictCheck]);

  // Calculate tuition
  const calculateTuition = useCallback(async () => {
    if (selectedCourses.length === 0) return;

    try {
      const paymentPlan = form.getFieldValue('paymentPlan');
      const result = await onCalculateTuition(selectedCourses, paymentPlan);
      setTuitionInfo(result);
    } catch (error) {
      console.error('Failed to calculate tuition:', error);
    }
  }, [selectedCourses, form, onCalculateTuition]);

  // Update validation when courses change
  useEffect(() => {
    if (selectedCourses.length > 0) {
      validatePrerequisites();
      checkScheduleConflicts();
    }
  }, [selectedCourses, validatePrerequisites, checkScheduleConflicts]);

  // Update tuition when courses or payment plan changes
  useEffect(() => {
    if (selectedCourses.length > 0) {
      calculateTuition();
    }
  }, [selectedCourses, calculateTuition]);

  // Define wizard steps
  const steps: WizardStep[] = [
    {
      title: 'Select Student',
      icon: <UserOutlined />,
      content: (
        <Card title="Student Selection">
          <div className="space-y-4">
            <Search
              placeholder="Search students by name, ID, or email"
              allowClear
              enterButton="Search"
              size="large"
              onSearch={async (value) => {
                if (value) {
                  setLoading(true);
                  try {
                    const results = await onStudentSearch(value);
                    // Handle search results - you might want to show them in a dropdown or table
                  } finally {
                    setLoading(false);
                  }
                }
              }}
            />

            <Select
              showSearch
              placeholder="Or select from all students"
              style={{ width: '100%' }}
              value={selectedStudent?.id}
              onChange={(value) => {
                const student = students.find(s => s.id === value);
                setSelectedStudent(student || null);
              }}
              filterOption={(input, option) =>
                option?.label?.toLowerCase().includes(input.toLowerCase()) ?? false
              }
              options={students.map(student => ({
                value: student.id,
                label: `${student.name} (${student.studentId})`,
              }))}
            />

            {selectedStudent && (
              <Card size="small" className="bg-blue-50">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <h4 className="font-medium">{selectedStudent.name}</h4>
                    <p className="text-sm text-gray-600">ID: {selectedStudent.studentId}</p>
                    <p className="text-sm text-gray-600">Program: {selectedStudent.program}</p>
                    <p className="text-sm text-gray-600">GPA: {selectedStudent.gpa}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Level: {selectedStudent.level}</p>
                    <p className="text-sm text-gray-600">Credits: {selectedStudent.credits}</p>
                    <div className="flex space-x-2 mt-2">
                      {selectedStudent.financialHold && (
                        <Badge status="error" text="Financial Hold" />
                      )}
                      {selectedStudent.academicHold && (
                        <Badge status="warning" text="Academic Hold" />
                      )}
                    </div>
                  </div>
                </div>
              </Card>
            )}

            {(selectedStudent?.financialHold || selectedStudent?.academicHold) && (
              <Alert
                message="Student has active holds"
                description="This student has holds that may prevent enrollment. Please resolve before proceeding."
                type="warning"
                showIcon
              />
            )}
          </div>
        </Card>
      ),
      validation: () => {
        if (!selectedStudent) {
          message.error('Please select a student');
          return false;
        }
        return true;
      },
    },
    {
      title: 'Select Courses',
      icon: <BookOutlined />,
      content: (
        <Card title="Course Selection">
          <div className="space-y-4">
            {selectedProgram && (
              <Alert
                message={`Program: ${programs.find(p => p.id === selectedProgram)?.name}`}
                type="info"
                showIcon
              />
            )}

            <Table
              dataSource={courses.filter(course => course.status === 'open')}
              columns={[
                {
                  title: 'Select',
                  render: (_, course) => (
                    <Checkbox
                      checked={selectedCourses.includes(course.id)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedCourses([...selectedCourses, course.id]);
                        } else {
                          setSelectedCourses(selectedCourses.filter(id => id !== course.id));
                        }
                      }}
                      disabled={course.currentEnrollment >= course.maxCapacity && !selectedCourses.includes(course.id)}
                    />
                  ),
                },
                {
                  title: 'Course',
                  render: (_, course) => (
                    <div>
                      <div className="font-medium">{course.code}</div>
                      <div className="text-sm text-gray-600">{course.name}</div>
                      {validationErrors[course.id] && (
                        <div className="text-red-500 text-xs mt-1">
                          {validationErrors[course.id].message}
                        </div>
                      )}
                    </div>
                  ),
                },
                {
                  title: 'Credits',
                  dataIndex: 'credits',
                },
                {
                  title: 'Schedule',
                  render: (_, course) => (
                    <div>
                      {course.schedule.map((schedule, index) => (
                        <div key={index} className="text-sm">
                          {schedule.dayOfWeek} {schedule.startTime}-{schedule.endTime}
                        </div>
                      ))}
                    </div>
                  ),
                },
                {
                  title: 'Capacity',
                  render: (_, course) => (
                    <div>
                      <div className="text-sm">
                        {course.currentEnrollment} / {course.maxCapacity}
                      </div>
                      <Progress
                        percent={(course.currentEnrollment / course.maxCapacity) * 100}
                        size="small"
                        showInfo={false}
                        status={course.currentEnrollment >= course.maxCapacity ? 'exception' : 'active'}
                      />
                      {course.waitlistCount > 0 && (
                        <div className="text-xs text-orange-600">
                          {course.waitlistCount} waitlisted
                        </div>
                      )}
                    </div>
                  ),
                },
                {
                  title: 'Tuition',
                  render: (_, course) => `$${course.tuition.toLocaleString()}`,
                },
              ]}
              rowKey="id"
              size="small"
              pagination={{ pageSize: 10 }}
            />

            {selectedCourses.length > 0 && (
              <Card size="small" className="bg-green-50">
                <h4 className="font-medium mb-2">Selected Courses ({selectedCourses.length})</h4>
                <div className="space-y-2">
                  {selectedCourses.map(courseId => {
                    const course = courses.find(c => c.id === courseId);
                    return course ? (
                      <Tag key={courseId} closable onClose={() => {
                        setSelectedCourses(selectedCourses.filter(id => id !== courseId));
                      }}>
                        {course.code} - {course.credits} credits
                      </Tag>
                    ) : null;
                  })}
                </div>
                <div className="mt-2 text-sm text-gray-600">
                  Total Credits: {selectedCourses.reduce((total, courseId) => {
                    const course = courses.find(c => c.id === courseId);
                    return total + (course?.credits || 0);
                  }, 0)}
                </div>
              </Card>
            )}
          </div>
        </Card>
      ),
      validation: () => {
        if (selectedCourses.length === 0) {
          message.error('Please select at least one course');
          return false;
        }

        // Check for validation errors
        const hasErrors = Object.keys(validationErrors).some(courseId =>
          selectedCourses.includes(courseId) && validationErrors[courseId].type === 'prerequisite'
        );

        if (hasErrors) {
          message.error('Please resolve prerequisite issues before proceeding');
          return false;
        }

        return true;
      },
    },
    {
      title: 'Schedule Review',
      icon: <CalendarOutlined />,
      content: (
        <Card title="Schedule Conflicts">
          {conflicts.length === 0 ? (
            <Alert
              message="No schedule conflicts detected"
              description="All selected courses can be scheduled without conflicts."
              type="success"
              showIcon
            />
          ) : (
            <div className="space-y-3">
              <Alert
                message={`${conflicts.length} conflict(s) detected`}
                description="Please review and resolve conflicts before proceeding."
                type="warning"
                showIcon
              />

              {conflicts.map((conflict, index) => (
                <Card key={index} size="small" className={
                  conflict.severity === 'error' ? 'border-red-200' :
                  conflict.severity === 'warning' ? 'border-orange-200' :
                  'border-blue-200'
                }>
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="flex items-center space-x-2">
                        <Tag color={
                          conflict.severity === 'error' ? 'red' :
                          conflict.severity === 'warning' ? 'orange' : 'blue'
                        }>
                          {conflict.type.toUpperCase()}
                        </Tag>
                        <span className="font-medium">{conflict.message}</span>
                      </div>
                      {conflict.resolution && (
                        <div className="text-sm text-gray-600 mt-1">
                          Suggestion: {conflict.resolution}
                        </div>
                      )}
                    </div>
                    <Button size="small">
                      Resolve
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          )}

          {/* Weekly schedule view */}
          <Divider>Weekly Schedule Preview</Divider>
          <div className="grid grid-cols-7 gap-2 text-center">
            {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map(day => (
              <div key={day}>
                <div className="font-medium p-2 bg-gray-100">{day}</div>
                <div className="space-y-1 p-2">
                  {selectedCourses.map(courseId => {
                    const course = courses.find(c => c.id === courseId);
                    return course?.schedule
                      .filter(s => s.dayOfWeek === day)
                      .map((schedule, index) => (
                        <div key={index} className="text-xs bg-blue-100 p-1 rounded">
                          <div>{course.code}</div>
                          <div>{schedule.startTime}-{schedule.endTime}</div>
                          <div>{schedule.room}</div>
                        </div>
                      ));
                  })}
                </div>
              </div>
            ))}
          </div>
        </Card>
      ),
      validation: () => {
        const errorConflicts = conflicts.filter(c => c.severity === 'error');
        if (errorConflicts.length > 0) {
          message.error('Please resolve all critical conflicts before proceeding');
          return false;
        }
        return true;
      },
    },
    {
      title: 'Payment',
      icon: <DollarOutlined />,
      content: (
        <Card title="Payment Information">
          <div className="space-y-6">
            {tuitionInfo && (
              <Card size="small" className="bg-blue-50">
                <div className="grid grid-cols-2 gap-4">
                  <Statistic
                    title="Total Tuition"
                    value={tuitionInfo.total}
                    prefix="$"
                    precision={2}
                  />
                  <Statistic
                    title="Total Credits"
                    value={selectedCourses.reduce((total, courseId) => {
                      const course = courses.find(c => c.id === courseId);
                      return total + (course?.credits || 0);
                    }, 0)}
                  />
                </div>
              </Card>
            )}

            <Form.Item
              name="paymentPlan"
              label="Payment Plan"
              rules={[{ required: true, message: 'Please select a payment plan' }]}
            >
              <Radio.Group className="w-full">
                <div className="space-y-3">
                  {paymentPlans.map(plan => (
                    <Radio key={plan.id} value={plan.id} className="w-full">
                      <Card size="small" className="ml-2">
                        <div className="flex justify-between items-start">
                          <div>
                            <div className="font-medium">{plan.name}</div>
                            <div className="text-sm text-gray-600">{plan.description}</div>
                            <div className="text-xs text-gray-500 mt-1">
                              {plan.installments} installments • {plan.downPayment}% down payment
                            </div>
                          </div>
                          <div className="text-right">
                            <div className="font-medium">
                              {plan.interestRate > 0 ? `${plan.interestRate}% APR` : 'No Interest'}
                            </div>
                            <div className="text-sm text-gray-600">
                              ${plan.fees} fees
                            </div>
                          </div>
                        </div>
                      </Card>
                    </Radio>
                  ))}
                </div>
              </Radio.Group>
            </Form.Item>

            <Form.Item
              name="specialRequests"
              label="Special Requests or Notes"
            >
              <TextArea
                rows={4}
                placeholder="Any special requests, accommodations, or notes..."
              />
            </Form.Item>
          </div>
        </Card>
      ),
      validation: () => {
        const paymentPlan = form.getFieldValue('paymentPlan');
        if (!paymentPlan) {
          message.error('Please select a payment plan');
          return false;
        }
        return true;
      },
    },
    {
      title: 'Review & Submit',
      icon: <CheckCircleOutlined />,
      content: (
        <Card title="Enrollment Summary">
          <div className="space-y-6">
            {/* Student Summary */}
            <Card size="small">
              <h4 className="font-medium mb-3">Student Information</h4>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p><strong>Name:</strong> {selectedStudent?.name}</p>
                  <p><strong>Student ID:</strong> {selectedStudent?.studentId}</p>
                  <p><strong>Program:</strong> {selectedStudent?.program}</p>
                </div>
                <div>
                  <p><strong>Email:</strong> {selectedStudent?.email}</p>
                  <p><strong>Phone:</strong> {selectedStudent?.phone}</p>
                  <p><strong>Current GPA:</strong> {selectedStudent?.gpa}</p>
                </div>
              </div>
            </Card>

            {/* Course Summary */}
            <Card size="small">
              <h4 className="font-medium mb-3">Selected Courses</h4>
              <Table
                dataSource={selectedCourses.map(courseId => courses.find(c => c.id === courseId)).filter(Boolean)}
                columns={[
                  { title: 'Code', dataIndex: 'code' },
                  { title: 'Name', dataIndex: 'name' },
                  { title: 'Credits', dataIndex: 'credits' },
                  { title: 'Instructor', dataIndex: 'instructor' },
                  {
                    title: 'Tuition',
                    render: (_, course) => `$${course.tuition.toLocaleString()}`
                  },
                ]}
                pagination={false}
                size="small"
              />
            </Card>

            {/* Payment Summary */}
            <Card size="small">
              <h4 className="font-medium mb-3">Payment Information</h4>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p><strong>Payment Plan:</strong> {
                    paymentPlans.find(p => p.id === form.getFieldValue('paymentPlan'))?.name
                  }</p>
                  <p><strong>Total Amount:</strong> ${tuitionInfo?.total.toLocaleString()}</p>
                </div>
                <div>
                  <p><strong>Down Payment:</strong> ${
                    tuitionInfo?.total ?
                    (tuitionInfo.total * (paymentPlans.find(p => p.id === form.getFieldValue('paymentPlan'))?.downPayment || 0) / 100).toLocaleString() :
                    '0'
                  }</p>
                </div>
              </div>
            </Card>

            {/* Warnings and Conflicts */}
            {conflicts.filter(c => c.severity === 'warning').length > 0 && (
              <Alert
                message="Warnings"
                description={
                  <ul className="list-disc pl-4">
                    {conflicts.filter(c => c.severity === 'warning').map((conflict, index) => (
                      <li key={index}>{conflict.message}</li>
                    ))}
                  </ul>
                }
                type="warning"
                showIcon
              />
            )}

            {/* Confirmation */}
            <Card size="small" className="bg-green-50">
              <div className="flex items-center space-x-3">
                <Checkbox>
                  I confirm that all information is correct and authorize this enrollment.
                </Checkbox>
              </div>
            </Card>
          </div>
        </Card>
      ),
      validation: () => {
        // Final validation before submission
        return true;
      },
    },
  ];

  // Handle step change
  const handleStepChange = (step: number) => {
    const currentStepConfig = steps[currentStep];
    if (currentStepConfig.validation && !currentStepConfig.validation()) {
      return;
    }
    setCurrentStep(step);
  };

  // Handle form submission
  const handleSubmit = async () => {
    try {
      setLoading(true);

      const enrollmentData = {
        studentId: selectedStudent?.id,
        courses: selectedCourses,
        program: selectedProgram,
        paymentPlan: form.getFieldValue('paymentPlan'),
        specialRequests: form.getFieldValue('specialRequests'),
        conflicts: conflicts.filter(c => c.severity === 'warning'),
        tuitionInfo,
      };

      await onSubmitEnrollment(enrollmentData);

      // Send confirmation notification to student
      if (selectedStudent) {
        const courseCodes = selectedCourses.map(courseId => {
          const course = courses.find(c => c.id === courseId);
          return course?.code;
        }).join(', ');

        await onSendNotification(
          selectedStudent.id,
          `Your enrollment for courses ${courseCodes} has been submitted and is being processed.`
        );
      }

      message.success('Enrollment submitted successfully!');

      // Reset form
      setCurrentStep(0);
      setSelectedStudent(null);
      setSelectedCourses([]);
      setSelectedProgram('');
      setConflicts([]);
      setTuitionInfo(null);
      form.resetFields();

    } catch (error) {
      message.error('Failed to submit enrollment');
      console.error('Enrollment submission error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="enrollment-wizard">
      <Card>
        <div className="flex justify-between items-center mb-6">
          <div>
            <h2 className="text-2xl font-bold">Student Enrollment Wizard</h2>
            <p className="text-gray-600">Complete the enrollment process step by step</p>
          </div>

          <Space>
            {draftSaved && (
              <Badge status="success" text="Draft Saved" />
            )}

            <Button
              icon={<SaveOutlined />}
              onClick={autoSaveDraft}
              disabled={!selectedStudent}
            >
              Save Draft
            </Button>
          </Space>
        </div>

        <Wizard
          steps={steps}
          current={currentStep}
          onChange={handleStepChange}
          onFinish={handleSubmit}
          loading={loading}
        />
      </Card>
    </div>
  );
};

export default EnrollmentWizard;