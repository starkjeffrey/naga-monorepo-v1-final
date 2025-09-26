/**
 * CourseDataGrid Component (CourseList.tsx)
 *
 * Advanced course management with AI-powered features:
 * - Enhanced DataGrid with advanced search capabilities
 * - Course details modal with prerequisites visualization
 * - Capacity management with waitlist tracking
 * - Course scheduling conflicts detection
 * - Bulk course operations
 * - AI-powered course recommendations
 * - Prerequisite dependency visualization
 * - Automated course scheduling optimization
 */

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  Card,
  Button,
  Space,
  Tag,
  Tooltip,
  Progress,
  Badge,
  Modal,
  Form,
  Input,
  Select,
  InputNumber,
  Switch,
  Divider,
  Statistic,
  Alert,
  Tree,
  notification,
  message,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  CopyOutlined,
  BulbOutlined,
  ShareAltOutlined,
  CalendarOutlined,
  TeamOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  BarChartOutlined,
  RobotOutlined,
  NodeIndexOutlined,
} from '@ant-design/icons';
import {
  EnhancedDataGrid,
  DetailModal,
  type DataGridColumn,
  type DataGridAction,
  type DetailTab,
} from '../../../components/patterns';

const { Option } = Select;
const { TextArea } = Input;

interface Course {
  id: string;
  code: string;
  name: string;
  description: string;
  department: string;
  credits: number;
  level: 'undergraduate' | 'graduate' | 'doctoral';
  status: 'active' | 'inactive' | 'draft' | 'archived';
  maxCapacity: number;
  currentEnrollment: number;
  waitlistCount: number;
  prerequisites: string[];
  corequisites: string[];
  instructors: Instructor[];
  schedule: CourseSchedule[];
  tuition: number;
  tags: string[];
  lastModified: string;
  createdAt: string;
  successRate: number;
  difficulty: number;
  popularity: number;
  aiRecommendations?: AIRecommendation[];
}

interface Instructor {
  id: string;
  name: string;
  email: string;
  avatar?: string;
  department: string;
  rating: number;
}

interface CourseSchedule {
  id: string;
  dayOfWeek: string;
  startTime: string;
  endTime: string;
  room: string;
  building: string;
  capacity: number;
  conflicts?: ScheduleConflict[];
}

interface ScheduleConflict {
  type: 'room' | 'instructor' | 'student';
  description: string;
  severity: 'low' | 'medium' | 'high';
  affectedCount: number;
}

interface AIRecommendation {
  type: 'enrollment' | 'schedule' | 'prerequisite' | 'capacity';
  title: string;
  description: string;
  confidence: number;
  impact: 'low' | 'medium' | 'high';
  action?: string;
}

interface PrerequisiteNode {
  key: string;
  title: string;
  children?: PrerequisiteNode[];
  required: boolean;
  completed?: boolean;
}

interface CourseListProps {
  courses: Course[];
  loading?: boolean;
  onCourseCreate: (course: Partial<Course>) => Promise<void>;
  onCourseUpdate: (id: string, course: Partial<Course>) => Promise<void>;
  onCourseDelete: (id: string) => Promise<void>;
  onCourseDuplicate: (course: Course) => Promise<void>;
  onBulkOperation: (operation: string, courseIds: string[]) => Promise<void>;
  onExport: (format: 'excel' | 'csv' | 'pdf') => void;
  showAIRecommendations?: boolean;
}

export const CourseList: React.FC<CourseListProps> = ({
  courses,
  loading = false,
  onCourseCreate,
  onCourseUpdate,
  onCourseDelete,
  onCourseDuplicate,
  onBulkOperation,
  onExport,
  showAIRecommendations = true,
}) => {
  const [selectedCourses, setSelectedCourses] = useState<string[]>([]);
  const [courseModalVisible, setCourseModalVisible] = useState(false);
  const [editingCourse, setEditingCourse] = useState<Course | null>(null);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [selectedCourse, setSelectedCourse] = useState<Course | null>(null);
  const [prerequisiteModalVisible, setPrerequisiteModalVisible] = useState(false);
  const [aiRecommendationsVisible, setAIRecommendationsVisible] = useState(false);
  const [form] = Form.useForm();

  // Filter and search state
  const [filters, setFilters] = useState({
    department: '',
    level: '',
    status: '',
    instructor: '',
    hasConflicts: false,
    hasWaitlist: false,
  });

  // AI-powered course analytics
  const courseAnalytics = useMemo(() => {
    const totalCourses = courses.length;
    const activeCourses = courses.filter(c => c.status === 'active').length;
    const totalEnrollment = courses.reduce((sum, c) => sum + c.currentEnrollment, 0);
    const totalCapacity = courses.reduce((sum, c) => sum + c.maxCapacity, 0);
    const averageSuccessRate = courses.reduce((sum, c) => sum + c.successRate, 0) / totalCourses;
    const coursesWithConflicts = courses.filter(c =>
      c.schedule.some(s => s.conflicts && s.conflicts.length > 0)
    ).length;
    const coursesWithWaitlist = courses.filter(c => c.waitlistCount > 0).length;

    return {
      totalCourses,
      activeCourses,
      totalEnrollment,
      totalCapacity,
      utilizationRate: totalCapacity > 0 ? (totalEnrollment / totalCapacity) * 100 : 0,
      averageSuccessRate,
      coursesWithConflicts,
      coursesWithWaitlist,
    };
  }, [courses]);

  // Generate AI recommendations for course optimization
  const generateAIRecommendations = useCallback(async (course: Course): Promise<AIRecommendation[]> => {
    const recommendations: AIRecommendation[] = [];

    // Enrollment recommendations
    if (course.currentEnrollment < course.maxCapacity * 0.5) {
      recommendations.push({
        type: 'enrollment',
        title: 'Low Enrollment Alert',
        description: `This course is at ${((course.currentEnrollment / course.maxCapacity) * 100).toFixed(0)}% capacity. Consider marketing or prerequisite adjustments.`,
        confidence: 85,
        impact: 'medium',
        action: 'Review marketing strategy',
      });
    }

    // Schedule optimization
    const hasScheduleConflicts = course.schedule.some(s => s.conflicts && s.conflicts.length > 0);
    if (hasScheduleConflicts) {
      recommendations.push({
        type: 'schedule',
        title: 'Schedule Conflicts Detected',
        description: 'Multiple scheduling conflicts found. Consider adjusting time slots or rooms.',
        confidence: 95,
        impact: 'high',
        action: 'Optimize schedule',
      });
    }

    // Capacity recommendations
    if (course.waitlistCount > course.maxCapacity * 0.2) {
      recommendations.push({
        type: 'capacity',
        title: 'High Waitlist Demand',
        description: `${course.waitlistCount} students on waitlist. Consider increasing capacity or adding sections.`,
        confidence: 90,
        impact: 'high',
        action: 'Increase capacity',
      });
    }

    // Prerequisite optimization
    if (course.prerequisites.length > 3) {
      recommendations.push({
        type: 'prerequisite',
        title: 'Complex Prerequisites',
        description: 'Multiple prerequisites may be limiting enrollment. Review necessity.',
        confidence: 70,
        impact: 'medium',
        action: 'Simplify prerequisites',
      });
    }

    return recommendations;
  }, []);

  // Build prerequisite tree for visualization
  const buildPrerequisiteTree = useCallback((course: Course): PrerequisiteNode[] => {
    const buildNode = (courseCode: string, visited = new Set<string>()): PrerequisiteNode => {
      if (visited.has(courseCode)) {
        return {
          key: `${courseCode}-circular`,
          title: `${courseCode} (Circular Reference)`,
          required: true,
        };
      }

      visited.add(courseCode);
      const prereqCourse = courses.find(c => c.code === courseCode);

      if (!prereqCourse) {
        return {
          key: courseCode,
          title: `${courseCode} (Not Found)`,
          required: true,
        };
      }

      const children = prereqCourse.prerequisites.map(prereq =>
        buildNode(prereq, new Set(visited))
      );

      return {
        key: prereqCourse.id,
        title: `${prereqCourse.code} - ${prereqCourse.name}`,
        children: children.length > 0 ? children : undefined,
        required: true,
        completed: false, // Would come from student data
      };
    };

    return course.prerequisites.map(prereq => buildNode(prereq));
  }, [courses]);

  // Define data grid columns
  const columns: DataGridColumn<Course>[] = [
    {
      key: 'code',
      title: 'Course Code',
      dataIndex: 'code',
      sortable: true,
      searchable: true,
      width: 120,
      fixed: 'left',
      render: (code: string, record: Course) => (
        <div>
          <div className="font-medium">{code}</div>
          <div className="text-xs text-gray-500">{record.credits} credits</div>
        </div>
      ),
    },
    {
      key: 'name',
      title: 'Course Name',
      dataIndex: 'name',
      sortable: true,
      searchable: true,
      width: 250,
      render: (name: string, record: Course) => (
        <div>
          <div className="font-medium">{name}</div>
          <div className="text-xs text-gray-500 truncate" style={{ maxWidth: 200 }}>
            {record.description}
          </div>
          {record.aiRecommendations && record.aiRecommendations.length > 0 && (
            <Tooltip title="AI recommendations available">
              <RobotOutlined className="text-blue-500 ml-1" />
            </Tooltip>
          )}
        </div>
      ),
    },
    {
      key: 'department',
      title: 'Department',
      dataIndex: 'department',
      sortable: true,
      filterable: true,
      filterOptions: [...new Set(courses.map(c => c.department))].map(dept => ({
        label: dept,
        value: dept,
      })),
      width: 150,
    },
    {
      key: 'level',
      title: 'Level',
      dataIndex: 'level',
      sortable: true,
      filterable: true,
      filterOptions: [
        { label: 'Undergraduate', value: 'undergraduate' },
        { label: 'Graduate', value: 'graduate' },
        { label: 'Doctoral', value: 'doctoral' },
      ],
      width: 120,
      render: (level: string) => (
        <Tag color={level === 'undergraduate' ? 'blue' : level === 'graduate' ? 'green' : 'purple'}>
          {level.charAt(0).toUpperCase() + level.slice(1)}
        </Tag>
      ),
    },
    {
      key: 'status',
      title: 'Status',
      dataIndex: 'status',
      sortable: true,
      filterable: true,
      filterOptions: [
        { label: 'Active', value: 'active' },
        { label: 'Inactive', value: 'inactive' },
        { label: 'Draft', value: 'draft' },
        { label: 'Archived', value: 'archived' },
      ],
      width: 100,
      render: (status: string) => {
        const color = {
          active: 'green',
          inactive: 'red',
          draft: 'orange',
          archived: 'gray',
        }[status] || 'default';
        return <Badge status={color as any} text={status.charAt(0).toUpperCase() + status.slice(1)} />;
      },
    },
    {
      key: 'enrollment',
      title: 'Enrollment',
      width: 150,
      render: (_, record: Course) => {
        const percentage = (record.currentEnrollment / record.maxCapacity) * 100;
        const status = percentage >= 90 ? 'exception' : percentage >= 70 ? 'active' : 'normal';

        return (
          <div>
            <div className="flex justify-between text-sm">
              <span>{record.currentEnrollment}</span>
              <span>/ {record.maxCapacity}</span>
            </div>
            <Progress
              percent={percentage}
              size="small"
              status={status}
              showInfo={false}
            />
            {record.waitlistCount > 0 && (
              <div className="text-xs text-orange-600 mt-1">
                {record.waitlistCount} on waitlist
              </div>
            )}
          </div>
        );
      },
    },
    {
      key: 'instructors',
      title: 'Instructors',
      width: 200,
      render: (_, record: Course) => (
        <div>
          {record.instructors.slice(0, 2).map(instructor => (
            <div key={instructor.id} className="text-sm">
              {instructor.name}
              <span className="text-gray-500 ml-1">({instructor.rating}★)</span>
            </div>
          ))}
          {record.instructors.length > 2 && (
            <div className="text-xs text-gray-500">
              +{record.instructors.length - 2} more
            </div>
          )}
        </div>
      ),
    },
    {
      key: 'schedule',
      title: 'Schedule',
      width: 150,
      render: (_, record: Course) => {
        const hasConflicts = record.schedule.some(s => s.conflicts && s.conflicts.length > 0);
        return (
          <div>
            {record.schedule.slice(0, 2).map((schedule, index) => (
              <div key={index} className="text-sm">
                {schedule.dayOfWeek} {schedule.startTime}-{schedule.endTime}
                {hasConflicts && (
                  <WarningOutlined className="text-orange-500 ml-1" />
                )}
              </div>
            ))}
            {record.schedule.length > 2 && (
              <div className="text-xs text-gray-500">
                +{record.schedule.length - 2} more sessions
              </div>
            )}
          </div>
        );
      },
    },
    {
      key: 'metrics',
      title: 'Metrics',
      width: 120,
      render: (_, record: Course) => (
        <div className="space-y-1">
          <div className="flex items-center text-xs">
            <span className="text-gray-500">Success:</span>
            <span className={`ml-1 ${record.successRate >= 80 ? 'text-green-600' : 'text-red-600'}`}>
              {record.successRate}%
            </span>
          </div>
          <div className="flex items-center text-xs">
            <span className="text-gray-500">Popularity:</span>
            <Progress
              percent={record.popularity}
              size="small"
              showInfo={false}
              className="ml-1"
              style={{ width: 40 }}
            />
          </div>
        </div>
      ),
    },
  ];

  // Define action buttons
  const actions: DataGridAction<Course>[] = [
    {
      key: 'view',
      label: 'View Details',
      icon: <EyeOutlined />,
      onClick: (course) => {
        setSelectedCourse(course);
        setDetailModalVisible(true);
      },
    },
    {
      key: 'edit',
      label: 'Edit',
      icon: <EditOutlined />,
      onClick: (course) => {
        setEditingCourse(course);
        form.setFieldsValue(course);
        setCourseModalVisible(true);
      },
    },
    {
      key: 'duplicate',
      label: 'Duplicate',
      icon: <CopyOutlined />,
      onClick: (course) => onCourseDuplicate(course),
    },
    {
      key: 'prerequisites',
      label: 'Prerequisites',
      icon: <NodeIndexOutlined />,
      onClick: (course) => {
        setSelectedCourse(course);
        setPrerequisiteModalVisible(true);
      },
      visible: (course) => course.prerequisites.length > 0,
    },
    {
      key: 'ai-recommendations',
      label: 'AI Insights',
      icon: <BulbOutlined />,
      onClick: async (course) => {
        const recommendations = await generateAIRecommendations(course);
        // Update course with recommendations
        await onCourseUpdate(course.id, { aiRecommendations: recommendations });
        setSelectedCourse({ ...course, aiRecommendations: recommendations });
        setAIRecommendationsVisible(true);
      },
      visible: () => showAIRecommendations,
    },
    {
      key: 'delete',
      label: 'Delete',
      icon: <DeleteOutlined />,
      danger: true,
      onClick: (course) => {
        Modal.confirm({
          title: 'Delete Course',
          content: `Are you sure you want to delete ${course.code} - ${course.name}?`,
          onOk: () => onCourseDelete(course.id),
        });
      },
      disabled: (course) => course.currentEnrollment > 0,
    },
  ];

  // Bulk actions
  const bulkActions = [
    {
      key: 'activate',
      label: 'Activate Selected',
      icon: <CheckCircleOutlined />,
      onClick: (selectedRows: Course[]) => {
        onBulkOperation('activate', selectedRows.map(c => c.id));
      },
    },
    {
      key: 'deactivate',
      label: 'Deactivate Selected',
      icon: <ClockCircleOutlined />,
      onClick: (selectedRows: Course[]) => {
        onBulkOperation('deactivate', selectedRows.map(c => c.id));
      },
    },
    {
      key: 'archive',
      label: 'Archive Selected',
      icon: <DeleteOutlined />,
      danger: true,
      onClick: (selectedRows: Course[]) => {
        Modal.confirm({
          title: 'Archive Courses',
          content: `Archive ${selectedRows.length} selected courses?`,
          onOk: () => onBulkOperation('archive', selectedRows.map(c => c.id)),
        });
      },
    },
  ];

  // Detail modal tabs
  const detailTabs: DetailTab[] = [
    {
      key: 'info',
      label: 'Course Information',
      content: selectedCourse ? (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <h4 className="font-medium">Basic Information</h4>
              <div className="space-y-2 mt-2">
                <div><span className="text-gray-500">Code:</span> {selectedCourse.code}</div>
                <div><span className="text-gray-500">Credits:</span> {selectedCourse.credits}</div>
                <div><span className="text-gray-500">Level:</span> {selectedCourse.level}</div>
                <div><span className="text-gray-500">Department:</span> {selectedCourse.department}</div>
              </div>
            </div>
            <div>
              <h4 className="font-medium">Enrollment</h4>
              <div className="space-y-2 mt-2">
                <div><span className="text-gray-500">Capacity:</span> {selectedCourse.maxCapacity}</div>
                <div><span className="text-gray-500">Enrolled:</span> {selectedCourse.currentEnrollment}</div>
                <div><span className="text-gray-500">Waitlist:</span> {selectedCourse.waitlistCount}</div>
                <div><span className="text-gray-500">Success Rate:</span> {selectedCourse.successRate}%</div>
              </div>
            </div>
          </div>
          <div>
            <h4 className="font-medium">Description</h4>
            <p className="mt-2 text-gray-600">{selectedCourse.description}</p>
          </div>
          <div>
            <h4 className="font-medium">Prerequisites</h4>
            <div className="mt-2">
              {selectedCourse.prerequisites.length > 0 ? (
                <div className="space-x-2">
                  {selectedCourse.prerequisites.map(prereq => (
                    <Tag key={prereq}>{prereq}</Tag>
                  ))}
                </div>
              ) : (
                <span className="text-gray-500">No prerequisites</span>
              )}
            </div>
          </div>
        </div>
      ) : null,
    },
    {
      key: 'schedule',
      label: 'Schedule',
      content: selectedCourse ? (
        <div className="space-y-4">
          {selectedCourse.schedule.map((schedule, index) => (
            <Card key={index} size="small">
              <div className="flex justify-between items-start">
                <div>
                  <div className="font-medium">
                    {schedule.dayOfWeek} {schedule.startTime} - {schedule.endTime}
                  </div>
                  <div className="text-gray-600">
                    {schedule.room}, {schedule.building}
                  </div>
                  <div className="text-sm text-gray-500">
                    Capacity: {schedule.capacity}
                  </div>
                </div>
                {schedule.conflicts && schedule.conflicts.length > 0 && (
                  <div>
                    <Badge count={schedule.conflicts.length} color="orange">
                      <WarningOutlined className="text-orange-500" />
                    </Badge>
                  </div>
                )}
              </div>
              {schedule.conflicts && schedule.conflicts.length > 0 && (
                <div className="mt-3 space-y-2">
                  {schedule.conflicts.map((conflict, conflictIndex) => (
                    <Alert
                      key={conflictIndex}
                      message={conflict.description}
                      type={conflict.severity === 'high' ? 'error' : 'warning'}
                      size="small"
                      showIcon
                    />
                  ))}
                </div>
              )}
            </Card>
          ))}
        </div>
      ) : null,
    },
    {
      key: 'instructors',
      label: 'Instructors',
      content: selectedCourse ? (
        <div className="space-y-3">
          {selectedCourse.instructors.map(instructor => (
            <Card key={instructor.id} size="small">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-blue-500 rounded-full flex items-center justify-center text-white">
                  {instructor.name.charAt(0)}
                </div>
                <div className="flex-1">
                  <div className="font-medium">{instructor.name}</div>
                  <div className="text-sm text-gray-600">{instructor.email}</div>
                  <div className="text-sm text-gray-500">{instructor.department}</div>
                </div>
                <div className="text-right">
                  <div className="text-lg font-medium">{instructor.rating}★</div>
                  <div className="text-xs text-gray-500">Rating</div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      ) : null,
    },
  ];

  // Handle course form submission
  const handleCourseSubmit = async (values: any) => {
    try {
      if (editingCourse) {
        await onCourseUpdate(editingCourse.id, values);
        message.success('Course updated successfully');
      } else {
        await onCourseCreate(values);
        message.success('Course created successfully');
      }
      setCourseModalVisible(false);
      setEditingCourse(null);
      form.resetFields();
    } catch (error) {
      message.error('Failed to save course');
    }
  };

  return (
    <div className="course-list space-y-6">
      {/* Analytics Dashboard */}
      <Card title="Course Analytics">
        <div className="grid grid-cols-4 gap-4 mb-4">
          <Statistic title="Total Courses" value={courseAnalytics.totalCourses} />
          <Statistic title="Active Courses" value={courseAnalytics.activeCourses} />
          <Statistic
            title="Utilization Rate"
            value={courseAnalytics.utilizationRate}
            precision={1}
            suffix="%"
            valueStyle={{
              color: courseAnalytics.utilizationRate >= 70 ? '#3f8600' : '#cf1322',
            }}
          />
          <Statistic
            title="Average Success Rate"
            value={courseAnalytics.averageSuccessRate}
            precision={1}
            suffix="%"
          />
        </div>

        {/* Alerts */}
        <div className="grid grid-cols-2 gap-4">
          {courseAnalytics.coursesWithConflicts > 0 && (
            <Alert
              message={`${courseAnalytics.coursesWithConflicts} courses have scheduling conflicts`}
              type="warning"
              showIcon
              action={
                <Button size="small">
                  Resolve Conflicts
                </Button>
              }
            />
          )}
          {courseAnalytics.coursesWithWaitlist > 0 && (
            <Alert
              message={`${courseAnalytics.coursesWithWaitlist} courses have waitlists`}
              type="info"
              showIcon
              action={
                <Button size="small">
                  Review Capacity
                </Button>
              }
            />
          )}
        </div>
      </Card>

      {/* Course Data Grid */}
      <EnhancedDataGrid
        data={courses}
        columns={columns}
        loading={loading}
        rowKey="id"
        searchable
        searchPlaceholder="Search courses by code, name, or instructor..."
        globalSearch
        selectable
        selectedRowKeys={selectedCourses}
        onSelectionChange={(keys) => setSelectedCourses(keys as string[])}
        actions={actions}
        bulkActions={bulkActions}
        pagination={{
          current: 1,
          pageSize: 20,
          total: courses.length,
          showSizeChanger: true,
          pageSizeOptions: ['10', '20', '50', '100'],
        }}
        exportable
        onExport={onExport}
        emptyText="No courses found"
        emptyDescription="Start by creating your first course"
        emptyAction={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCourseModalVisible(true)}>
            Create Course
          </Button>
        }
        filters={filters}
        onFiltersChange={setFilters}
      />

      {/* Course Form Modal */}
      <Modal
        title={editingCourse ? 'Edit Course' : 'Create Course'}
        open={courseModalVisible}
        onCancel={() => {
          setCourseModalVisible(false);
          setEditingCourse(null);
          form.resetFields();
        }}
        onOk={() => form.submit()}
        width={800}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCourseSubmit}
        >
          <div className="grid grid-cols-2 gap-4">
            <Form.Item
              name="code"
              label="Course Code"
              rules={[{ required: true, message: 'Please enter course code' }]}
            >
              <Input placeholder="e.g., CS101" />
            </Form.Item>

            <Form.Item
              name="credits"
              label="Credits"
              rules={[{ required: true, message: 'Please enter credits' }]}
            >
              <InputNumber min={1} max={12} className="w-full" />
            </Form.Item>

            <Form.Item
              name="name"
              label="Course Name"
              rules={[{ required: true, message: 'Please enter course name' }]}
              className="col-span-2"
            >
              <Input placeholder="e.g., Introduction to Computer Science" />
            </Form.Item>

            <Form.Item
              name="department"
              label="Department"
              rules={[{ required: true, message: 'Please select department' }]}
            >
              <Select placeholder="Select department">
                <Option value="Computer Science">Computer Science</Option>
                <Option value="Mathematics">Mathematics</Option>
                <Option value="Physics">Physics</Option>
                <Option value="Chemistry">Chemistry</Option>
                <Option value="Biology">Biology</Option>
              </Select>
            </Form.Item>

            <Form.Item
              name="level"
              label="Level"
              rules={[{ required: true, message: 'Please select level' }]}
            >
              <Select placeholder="Select level">
                <Option value="undergraduate">Undergraduate</Option>
                <Option value="graduate">Graduate</Option>
                <Option value="doctoral">Doctoral</Option>
              </Select>
            </Form.Item>

            <Form.Item
              name="maxCapacity"
              label="Max Capacity"
              rules={[{ required: true, message: 'Please enter max capacity' }]}
            >
              <InputNumber min={1} max={500} className="w-full" />
            </Form.Item>

            <Form.Item
              name="tuition"
              label="Tuition ($)"
              rules={[{ required: true, message: 'Please enter tuition' }]}
            >
              <InputNumber
                min={0}
                formatter={value => `$ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                parser={value => value!.replace(/\$\s?|(,*)/g, '')}
                className="w-full"
              />
            </Form.Item>

            <Form.Item
              name="description"
              label="Description"
              className="col-span-2"
            >
              <TextArea rows={4} placeholder="Course description..." />
            </Form.Item>

            <Form.Item
              name="prerequisites"
              label="Prerequisites"
              className="col-span-2"
            >
              <Select
                mode="tags"
                placeholder="Enter prerequisite course codes"
                style={{ width: '100%' }}
              />
            </Form.Item>

            <Form.Item
              name="status"
              label="Status"
            >
              <Select defaultValue="draft">
                <Option value="draft">Draft</Option>
                <Option value="active">Active</Option>
                <Option value="inactive">Inactive</Option>
              </Select>
            </Form.Item>
          </div>
        </Form>
      </Modal>

      {/* Course Detail Modal */}
      <DetailModal
        title={selectedCourse ? `${selectedCourse.code} - ${selectedCourse.name}` : ''}
        open={detailModalVisible}
        onClose={() => {
          setDetailModalVisible(false);
          setSelectedCourse(null);
        }}
        tabs={detailTabs}
        actions={[
          {
            key: 'edit',
            label: 'Edit Course',
            type: 'primary',
            onClick: () => {
              if (selectedCourse) {
                setEditingCourse(selectedCourse);
                form.setFieldsValue(selectedCourse);
                setCourseModalVisible(true);
                setDetailModalVisible(false);
              }
            },
          },
        ]}
      />

      {/* Prerequisites Visualization Modal */}
      <Modal
        title="Prerequisites Tree"
        open={prerequisiteModalVisible}
        onCancel={() => setPrerequisiteModalVisible(false)}
        footer={null}
        width={800}
      >
        {selectedCourse && (
          <div>
            <div className="mb-4">
              <h4 className="font-medium">{selectedCourse.code} - {selectedCourse.name}</h4>
              <p className="text-gray-600">Prerequisites dependency tree</p>
            </div>
            <Tree
              treeData={buildPrerequisiteTree(selectedCourse)}
              defaultExpandAll
              showIcon
              icon={({ required, completed }) => (
                <div className={`w-4 h-4 rounded-full border-2 ${
                  completed ? 'bg-green-500 border-green-500' :
                  required ? 'border-red-500' : 'border-gray-300'
                }`} />
              )}
            />
          </div>
        )}
      </Modal>

      {/* AI Recommendations Modal */}
      <Modal
        title="AI-Powered Course Insights"
        open={aiRecommendationsVisible}
        onCancel={() => setAIRecommendationsVisible(false)}
        footer={null}
        width={700}
      >
        {selectedCourse?.aiRecommendations && (
          <div className="space-y-4">
            <div className="flex items-center space-x-2 mb-4">
              <RobotOutlined className="text-blue-500" />
              <span className="font-medium">AI Analysis for {selectedCourse.code}</span>
            </div>

            {selectedCourse.aiRecommendations.map((recommendation, index) => (
              <Card key={index} size="small">
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 mb-2">
                      <Tag color={recommendation.impact === 'high' ? 'red' : recommendation.impact === 'medium' ? 'orange' : 'blue'}>
                        {recommendation.impact.toUpperCase()}
                      </Tag>
                      <span className="font-medium">{recommendation.title}</span>
                    </div>
                    <p className="text-gray-600 mb-2">{recommendation.description}</p>
                    {recommendation.action && (
                      <Button size="small" type="primary">
                        {recommendation.action}
                      </Button>
                    )}
                  </div>
                  <div className="text-right">
                    <div className="text-lg font-medium text-blue-600">
                      {recommendation.confidence}%
                    </div>
                    <div className="text-xs text-gray-500">Confidence</div>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default CourseList;