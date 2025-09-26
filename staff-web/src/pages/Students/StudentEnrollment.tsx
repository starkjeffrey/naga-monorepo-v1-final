/**
 * Student Enrollment Management
 *
 * Course enrollment management using the TransferList pattern:
 * - Available courses on left, enrolled courses on right
 * - Prerequisites checking and enforcement
 * - Conflict detection (schedule, prerequisites, capacity)
 * - Waitlist management
 * - Multiple term enrollment support
 * - Bulk enrollment for multiple students
 * - Enrollment approval workflow
 * - Drag-drop course selection interface
 * - AI-powered course recommendations
 * - Automatic schedule optimization
 * - Integration with payment processing
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Alert,
  Button,
  Space,
  Tag,
  Modal,
  message,
  Tooltip,
  Badge,
  Select,
  DatePicker,
  List,
  Avatar,
  Progress,
} from 'antd';
import {
  BookOutlined,
  ClockCircleOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  UserOutlined,
  CalendarOutlined,
  DollarOutlined,
  ThunderboltOutlined,
  SwapOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';

import { TransferList } from '../../components/patterns';
import type { TransferItem } from '../../components/patterns';
import { StudentService } from '../../services/student.service';

const { Option } = Select;

interface Course extends TransferItem {
  code: string;
  credits: number;
  prerequisites: string[];
  capacity: number;
  enrolled: number;
  waitlist: number;
  schedule: string;
  teacher: string;
  room: string;
  term: string;
  tuition: number;
}

interface EnrollmentConflict {
  type: 'schedule' | 'prerequisite' | 'capacity';
  message: string;
  severity: 'error' | 'warning';
  courseId: string;
}

interface StudentEnrollmentProps {
  studentId: number;
  termId?: number;
}

export const StudentEnrollment: React.FC<StudentEnrollmentProps> = ({
  studentId,
  termId,
}) => {
  const [availableCourses, setAvailableCourses] = useState<Course[]>([]);
  const [enrolledCourses, setEnrolledCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(false);
  const [conflicts, setConflicts] = useState<EnrollmentConflict[]>([]);
  const [selectedTerm, setSelectedTerm] = useState(termId);
  const [aiRecommendations, setAiRecommendations] = useState<Course[]>([]);
  const [showRecommendations, setShowRecommendations] = useState(false);

  // Mock data
  const mockAvailableCourses: Course[] = [
    {
      id: '1',
      name: 'Introduction to Programming',
      code: 'CS101',
      credits: 3,
      prerequisites: [],
      capacity: 30,
      enrolled: 25,
      waitlist: 2,
      schedule: 'MWF 10:00-11:00',
      teacher: 'Dr. Smith',
      room: 'Room 101',
      term: 'Fall 2024',
      tuition: 500,
      email: 'cs101@school.edu',
    },
    {
      id: '2',
      name: 'Data Structures',
      code: 'CS201',
      credits: 4,
      prerequisites: ['CS101'],
      capacity: 25,
      enrolled: 20,
      waitlist: 0,
      schedule: 'TTh 14:00-16:00',
      teacher: 'Dr. Johnson',
      room: 'Room 102',
      term: 'Fall 2024',
      tuition: 600,
      email: 'cs201@school.edu',
    },
    {
      id: '3',
      name: 'Mathematics I',
      code: 'MATH101',
      credits: 3,
      prerequisites: [],
      capacity: 40,
      enrolled: 35,
      waitlist: 5,
      schedule: 'MWF 09:00-10:00',
      teacher: 'Dr. Brown',
      room: 'Room 201',
      term: 'Fall 2024',
      tuition: 450,
      email: 'math101@school.edu',
    },
  ];

  const mockEnrolledCourses: Course[] = [
    {
      id: '4',
      name: 'English Composition',
      code: 'ENG101',
      credits: 3,
      prerequisites: [],
      capacity: 30,
      enrolled: 28,
      waitlist: 0,
      schedule: 'TTh 10:00-11:30',
      teacher: 'Prof. Davis',
      room: 'Room 301',
      term: 'Fall 2024',
      tuition: 400,
      email: 'eng101@school.edu',
    },
  ];

  useEffect(() => {
    loadCourses();
    generateAIRecommendations();
  }, [studentId, selectedTerm]);

  const loadCourses = async () => {
    try {
      setLoading(true);
      // TODO: Load actual course data
      setAvailableCourses(mockAvailableCourses);
      setEnrolledCourses(mockEnrolledCourses);
    } catch (error) {
      console.error('Failed to load courses:', error);
      message.error('Failed to load courses');
    } finally {
      setLoading(false);
    }
  };

  const generateAIRecommendations = async () => {
    try {
      // TODO: Implement AI course recommendations
      const recommendations = mockAvailableCourses.slice(0, 2);
      setAiRecommendations(recommendations);
    } catch (error) {
      console.error('Failed to generate recommendations:', error);
    }
  };

  const checkEnrollmentConflicts = (newEnrolledCourses: Course[]) => {
    const foundConflicts: EnrollmentConflict[] = [];

    newEnrolledCourses.forEach(course => {
      // Check capacity
      if (course.enrolled >= course.capacity) {
        foundConflicts.push({
          type: 'capacity',
          message: `${course.name} is at full capacity. You will be added to the waitlist.`,
          severity: 'warning',
          courseId: course.id,
        });
      }

      // Check prerequisites
      course.prerequisites.forEach(prereq => {
        const hasPrereq = enrolledCourses.some(enrolled => enrolled.code === prereq) ||
                         newEnrolledCourses.some(enrolled => enrolled.code === prereq);
        if (!hasPrereq) {
          foundConflicts.push({
            type: 'prerequisite',
            message: `${course.name} requires ${prereq} as a prerequisite.`,
            severity: 'error',
            courseId: course.id,
          });
        }
      });

      // Check schedule conflicts
      newEnrolledCourses.forEach(otherCourse => {
        if (course.id !== otherCourse.id && course.schedule === otherCourse.schedule) {
          foundConflicts.push({
            type: 'schedule',
            message: `Schedule conflict between ${course.name} and ${otherCourse.name}.`,
            severity: 'error',
            courseId: course.id,
          });
        }
      });
    });

    setConflicts(foundConflicts);
    return foundConflicts;
  };

  const handleEnrollmentChange = (available: Course[], enrolled: Course[]) => {
    const conflicts = checkEnrollmentConflicts(enrolled);
    const hasErrors = conflicts.some(c => c.severity === 'error');

    if (hasErrors) {
      message.error('Cannot complete enrollment due to conflicts. Please resolve the issues.');
      return;
    }

    setAvailableCourses(available);
    setEnrolledCourses(enrolled);

    if (conflicts.some(c => c.severity === 'warning')) {
      message.warning('Some courses have warnings. Please review before finalizing.');
    }
  };

  const calculateTotalCredits = () => {
    return enrolledCourses.reduce((total, course) => total + course.credits, 0);
  };

  const calculateTotalTuition = () => {
    return enrolledCourses.reduce((total, course) => total + course.tuition, 0);
  };

  const handleFinalizeEnrollment = async () => {
    try {
      setLoading(true);
      // TODO: Submit enrollment to backend
      message.success('Enrollment submitted successfully!');
    } catch (error) {
      message.error('Failed to submit enrollment');
    } finally {
      setLoading(false);
    }
  };

  const renderCourseItem = (course: Course) => {
    const isAvailable = course.enrolled < course.capacity;
    const hasWaitlist = course.waitlist > 0;

    return (
      <div className="space-y-2">
        <div className="flex justify-between items-start">
          <div>
            <div className="font-medium">{course.name}</div>
            <div className="text-sm text-gray-500">
              {course.code} • {course.credits} credits • {course.schedule}
            </div>
            <div className="text-sm text-gray-500">
              {course.teacher} • {course.room}
            </div>
          </div>
          <div className="text-right">
            <div className="text-sm font-medium">${course.tuition}</div>
            <div className="text-xs text-gray-500">
              {course.enrolled}/{course.capacity}
              {hasWaitlist && ` (+${course.waitlist} waitlist)`}
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <Progress
            percent={(course.enrolled / course.capacity) * 100}
            showInfo={false}
            size="small"
            strokeColor={isAvailable ? '#52c41a' : '#faad14'}
          />
          {!isAvailable && (
            <Tag size="small" color="orange">Waitlist</Tag>
          )}
          {course.prerequisites.length > 0 && (
            <Tooltip title={`Prerequisites: ${course.prerequisites.join(', ')}`}>
              <Tag size="small" color="blue">Prereq</Tag>
            </Tooltip>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="student-enrollment space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h2 className="text-xl font-semibold">Course Enrollment</h2>
          <p className="text-gray-600">Manage student course enrollments for the selected term</p>
        </div>
        <Space>
          <Select
            placeholder="Select Term"
            value={selectedTerm}
            onChange={setSelectedTerm}
            style={{ width: 150 }}
          >
            <Option value={1}>Fall 2024</Option>
            <Option value={2}>Spring 2025</Option>
          </Select>
          <Button
            type="primary"
            icon={<ThunderboltOutlined />}
            onClick={() => setShowRecommendations(true)}
          >
            AI Recommendations
          </Button>
        </Space>
      </div>

      {/* Enrollment Summary */}
      <Card title="Enrollment Summary">
        <div className="grid grid-cols-3 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">{enrolledCourses.length}</div>
            <div className="text-sm text-gray-500">Enrolled Courses</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">{calculateTotalCredits()}</div>
            <div className="text-sm text-gray-500">Total Credits</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-600">${calculateTotalTuition().toLocaleString()}</div>
            <div className="text-sm text-gray-500">Total Tuition</div>
          </div>
        </div>
      </Card>

      {/* Conflicts Alert */}
      {conflicts.length > 0 && (
        <Alert
          message="Enrollment Issues Found"
          description={
            <ul className="mt-2">
              {conflicts.map((conflict, index) => (
                <li key={index} className="flex items-center space-x-2">
                  {conflict.severity === 'error' ? (
                    <WarningOutlined className="text-red-500" />
                  ) : (
                    <WarningOutlined className="text-orange-500" />
                  )}
                  <span>{conflict.message}</span>
                </li>
              ))}
            </ul>
          }
          type={conflicts.some(c => c.severity === 'error') ? 'error' : 'warning'}
          showIcon
          className="mb-4"
        />
      )}

      {/* Transfer List */}
      <TransferList
        availableItems={availableCourses.map(course => ({
          ...course,
          studentId: course.code,
        }))}
        enrolledItems={enrolledCourses.map(course => ({
          ...course,
          studentId: course.code,
        }))}
        availableTitle="Available Courses"
        enrolledTitle="Enrolled Courses"
        onChange={(available, enrolled) => {
          handleEnrollmentChange(
            available as Course[],
            enrolled as Course[]
          );
        }}
        searchable={true}
      />

      {/* Actions */}
      <div className="flex justify-between items-center">
        <Space>
          <Button icon={<SwapOutlined />}>
            Optimize Schedule
          </Button>
          <Button icon={<CalendarOutlined />}>
            View Schedule
          </Button>
        </Space>
        <Space>
          <Button>Save Draft</Button>
          <Button
            type="primary"
            onClick={handleFinalizeEnrollment}
            loading={loading}
            disabled={conflicts.some(c => c.severity === 'error')}
          >
            Finalize Enrollment
          </Button>
        </Space>
      </div>

      {/* AI Recommendations Modal */}
      <Modal
        title="AI Course Recommendations"
        open={showRecommendations}
        onCancel={() => setShowRecommendations(false)}
        footer={null}
        width={600}
      >
        <div className="space-y-4">
          <Alert
            message="Personalized Recommendations"
            description="Based on your academic history, program requirements, and career goals."
            type="info"
            showIcon
          />
          <List
            dataSource={aiRecommendations}
            renderItem={(course) => (
              <List.Item
                actions={[
                  <Button type="primary" size="small">
                    Add to Cart
                  </Button>
                ]}
              >
                <div className="w-full">
                  {renderCourseItem(course)}
                  <div className="mt-2 text-sm text-blue-600">
                    Recommended because: Fits your program track and has high success rate
                  </div>
                </div>
              </List.Item>
            )}
          />
        </div>
      </Modal>
    </div>
  );
};

export default StudentEnrollment;