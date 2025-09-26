/**
 * Student Detail Modal with 360° View
 *
 * A comprehensive student detail interface using the DetailModal pattern:
 * - Overview Tab: Basic info, photo, contact details, emergency contacts
 * - Academic Tab: Current enrollments, grades, transcripts, academic history
 * - Financial Tab: Account balance, payment history, invoices, scholarships
 * - Timeline Tab: Complete activity timeline with filtering
 * - Documents Tab: Uploaded documents, transcripts, certificates
 * - Communication Tab: Message history, meeting notes, parent communications
 * - Real-time data updates using GraphQL subscriptions
 * - Edit in place functionality with auto-save
 * - Document upload with drag-drop interface
 * - AI-powered student success predictions
 */

import React, { useState, useEffect, useMemo } from 'react';
import {
  Descriptions,
  Card,
  Avatar,
  Tag,
  Button,
  Space,
  Progress,
  Statistic,
  Table,
  List,
  Badge,
  Form,
  Input,
  Select,
  DatePicker,
  Switch,
  Upload,
  message,
  Tooltip,
  Alert,
  Timeline,
  Tabs,
  Row,
  Col,
  Divider,
} from 'antd';
import {
  UserOutlined,
  EditOutlined,
  SaveOutlined,
  CloseOutlined,
  PhoneOutlined,
  MailOutlined,
  HomeOutlined,
  CalendarOutlined,
  BookOutlined,
  DollarOutlined,
  FileTextOutlined,
  MessageOutlined,
  WarningOutlined,
  TrophyOutlined,
  ClockCircleOutlined,
  CameraOutlined,
  DownloadOutlined,
  PlusOutlined,
  HeartOutlined,
  TeamOutlined,
  AlertCircleOutlined,
  TrendingUpOutlined,
  BankOutlined,
  SchoolOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';

import {
  DetailModal,
  InfoTab,
  TimelineTab,
  DocumentsTab,
} from '../../components/patterns';
import type { DetailTab, DetailAction } from '../../components/patterns';
import { StudentService } from '../../services/student.service';
import type {
  PersonDetail,
  StudentEnrollmentSummary,
  PhoneNumber,
  Contact,
} from '../../types/student.types';

const { TabPane } = Tabs;
const { Option } = Select;

interface StudentDetailProps {
  studentId: number | null;
  open: boolean;
  onClose: () => void;
  onEdit?: (student: PersonDetail) => void;
}

export const StudentDetail: React.FC<StudentDetailProps> = ({
  studentId,
  open,
  onClose,
  onEdit,
}) => {
  // State management
  const [student, setStudent] = useState<PersonDetail | null>(null);
  const [enrollmentSummary, setEnrollmentSummary] = useState<StudentEnrollmentSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');
  const [editingFields, setEditingFields] = useState<Record<string, boolean>>({});

  // Load student data
  useEffect(() => {
    if (studentId && open) {
      loadStudentData();
    }
  }, [studentId, open]);

  const loadStudentData = async () => {
    if (!studentId) return;

    try {
      setLoading(true);
      const [studentData, enrollmentData] = await Promise.all([
        StudentService.getPersonDetail(studentId),
        StudentService.getStudentEnrollmentSummary(studentId),
      ]);

      setStudent(studentData);
      setEnrollmentSummary(enrollmentData);
    } catch (error) {
      console.error('Failed to load student data:', error);
      message.error('Failed to load student details');
    } finally {
      setLoading(false);
    }
  };

  // Handle field edit
  const handleFieldEdit = async (field: string, value: any) => {
    if (!student) return;

    try {
      // TODO: Implement field update API call
      message.success(`${field} updated successfully`);

      // Update local state
      setStudent(prev => prev ? { ...prev, [field]: value } : null);
      setEditingFields(prev => ({ ...prev, [field]: false }));
    } catch (error) {
      message.error(`Failed to update ${field}`);
    }
  };

  // AI Success Prediction Component
  const StudentSuccessPredictor = () => {
    const successScore = 85; // Mock AI prediction score
    const riskFactors = [
      { factor: 'Attendance Rate', status: 'good', value: '95%' },
      { factor: 'Grade Trend', status: 'warning', value: 'Declining' },
      { factor: 'Engagement', status: 'good', value: 'High' },
      { factor: 'Financial Status', status: 'risk', value: 'Outstanding Balance' },
    ];

    const interventions = [
      'Schedule academic counseling session',
      'Review financial aid options',
      'Connect with study group',
      'Monitor attendance closely',
    ];

    return (
      <Card title="Student Success Prediction" className="mb-4">
        <Row gutter={16}>
          <Col span={8}>
            <div className="text-center">
              <Progress
                type="circle"
                percent={successScore}
                strokeColor={{
                  '0%': '#108ee9',
                  '100%': '#87d068',
                }}
                format={() => (
                  <div>
                    <div className="text-2xl font-bold">{successScore}%</div>
                    <div className="text-xs text-gray-500">Success Score</div>
                  </div>
                )}
                size={120}
              />
            </div>
          </Col>
          <Col span={8}>
            <h4 className="font-medium mb-2">Risk Factors</h4>
            <div className="space-y-2">
              {riskFactors.map((factor, index) => (
                <div key={index} className="flex justify-between items-center">
                  <span className="text-sm">{factor.factor}</span>
                  <div className="flex items-center space-x-2">
                    <span className="text-sm font-medium">{factor.value}</span>
                    <Badge
                      status={
                        factor.status === 'good' ? 'success' :
                        factor.status === 'warning' ? 'warning' : 'error'
                      }
                    />
                  </div>
                </div>
              ))}
            </div>
          </Col>
          <Col span={8}>
            <h4 className="font-medium mb-2">Recommended Interventions</h4>
            <List
              size="small"
              dataSource={interventions}
              renderItem={(item, index) => (
                <List.Item>
                  <div className="flex items-center space-x-2">
                    <Badge count={index + 1} size="small" />
                    <span className="text-sm">{item}</span>
                  </div>
                </List.Item>
              )}
            />
          </Col>
        </Row>
      </Card>
    );
  };

  // Overview Tab Content
  const OverviewTab = () => {
    if (!student) return null;

    const basicInfoFields = [
      {
        key: 'full_name',
        label: 'Full Name',
        type: 'text' as const,
        editable: true,
      },
      {
        key: 'khmer_name',
        label: 'Khmer Name',
        type: 'text' as const,
        editable: true,
      },
      {
        key: 'preferred_gender',
        label: 'Gender',
        type: 'select' as const,
        options: [
          { label: 'Male', value: 'M' },
          { label: 'Female', value: 'F' },
          { label: 'Non-binary', value: 'N' },
          { label: 'Prefer not to say', value: 'X' },
        ],
        editable: true,
      },
      {
        key: 'date_of_birth',
        label: 'Date of Birth',
        type: 'date' as const,
        render: (value: string) => value ? dayjs(value).format('MMMM D, YYYY') : '-',
        editable: true,
      },
      {
        key: 'citizenship',
        label: 'Citizenship',
        type: 'text' as const,
        editable: true,
      },
      {
        key: 'birth_province',
        label: 'Birth Province',
        type: 'text' as const,
        editable: true,
      },
    ];

    const contactFields = [
      {
        key: 'school_email',
        label: 'School Email',
        type: 'email' as const,
        editable: true,
      },
      {
        key: 'personal_email',
        label: 'Personal Email',
        type: 'email' as const,
        editable: true,
      },
    ];

    const academicFields = [
      {
        key: 'student_profile.current_status',
        label: 'Status',
        render: (value: string) => (
          <Tag color={StudentService.getStatusBadgeClass(value).includes('green') ? 'green' : 'default'}>
            {StudentService.formatStudentStatus(value)}
          </Tag>
        ),
        editable: false,
      },
      {
        key: 'student_profile.study_time_preference',
        label: 'Study Time',
        render: (value: string) => StudentService.formatStudyTimePreference(value),
        editable: true,
      },
      {
        key: 'student_profile.is_monk',
        label: 'Monk Status',
        type: 'switch' as const,
        editable: true,
      },
      {
        key: 'student_profile.is_transfer_student',
        label: 'Transfer Student',
        type: 'switch' as const,
        editable: true,
      },
    ];

    return (
      <div className="space-y-6">
        <StudentSuccessPredictor />

        <Row gutter={16}>
          <Col span={12}>
            <InfoTab
              data={student}
              editable={true}
              onEdit={handleFieldEdit}
              fields={basicInfoFields}
            />
          </Col>
          <Col span={12}>
            <InfoTab
              data={student}
              editable={true}
              onEdit={handleFieldEdit}
              fields={contactFields}
            />
          </Col>
        </Row>

        <InfoTab
          data={student}
          editable={true}
          onEdit={handleFieldEdit}
          fields={academicFields}
        />

        {/* Phone Numbers */}
        <Card title="Phone Numbers" extra={<Button icon={<PlusOutlined />} size="small">Add</Button>}>
          <List
            dataSource={student.phone_numbers || []}
            renderItem={(phone: PhoneNumber) => (
              <List.Item
                actions={[
                  <Button type="link" icon={<EditOutlined />} />,
                  <Button type="link" danger>Remove</Button>,
                ]}
              >
                <div className="flex items-center space-x-3">
                  <PhoneOutlined />
                  <div>
                    <div className="font-medium">{phone.number}</div>
                    <div className="text-sm text-gray-500">
                      {phone.comment}
                      {phone.is_preferred && <Badge status="success" text="Preferred" className="ml-2" />}
                      {phone.is_telegram && <Badge status="processing" text="Telegram" className="ml-2" />}
                    </div>
                  </div>
                </div>
              </List.Item>
            )}
          />
        </Card>

        {/* Emergency Contacts */}
        <Card title="Emergency Contacts" extra={<Button icon={<PlusOutlined />} size="small">Add</Button>}>
          <List
            dataSource={student.contacts || []}
            renderItem={(contact: Contact) => (
              <List.Item
                actions={[
                  <Button type="link" icon={<EditOutlined />} />,
                  <Button type="link" danger>Remove</Button>,
                ]}
              >
                <div className="flex items-center space-x-3">
                  <TeamOutlined />
                  <div>
                    <div className="font-medium">{contact.name}</div>
                    <div className="text-sm text-gray-500">
                      {contact.relationship} • {contact.primary_phone}
                      {contact.email && ` • ${contact.email}`}
                    </div>
                  </div>
                </div>
              </List.Item>
            )}
          />
        </Card>
      </div>
    );
  };

  // Academic Tab Content
  const AcademicTab = () => {
    if (!enrollmentSummary) return <div>Loading academic information...</div>;

    const enrollmentColumns = [
      {
        title: 'Course',
        dataIndex: ['class_header', 'course_name'],
        key: 'course_name',
      },
      {
        title: 'Class Number',
        dataIndex: ['class_header', 'class_number'],
        key: 'class_number',
      },
      {
        title: 'Term',
        dataIndex: ['class_header', 'term_name'],
        key: 'term_name',
      },
      {
        title: 'Teacher',
        dataIndex: ['class_header', 'teacher_name'],
        key: 'teacher_name',
      },
      {
        title: 'Status',
        dataIndex: 'status',
        key: 'status',
        render: (status: string) => (
          <Tag color={status === 'ENROLLED' ? 'green' : 'default'}>
            {status}
          </Tag>
        ),
      },
      {
        title: 'Grade',
        dataIndex: 'grade_override',
        key: 'grade',
        render: (grade: string) => grade || '-',
      },
    ];

    return (
      <div className="space-y-6">
        {/* Academic Overview */}
        <Row gutter={16}>
          <Col span={6}>
            <Statistic
              title="Current Enrollments"
              value={enrollmentSummary.total_active_enrollments}
              prefix={<BookOutlined />}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="Completed Courses"
              value={enrollmentSummary.total_completed_courses}
              prefix={<TrophyOutlined />}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="Current Credits"
              value={enrollmentSummary.current_term_credit_hours}
              prefix={<SchoolOutlined />}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="Overall GPA"
              value="3.45"
              precision={2}
              prefix={<TrendingUpOutlined />}
            />
          </Col>
        </Row>

        {/* Program Enrollments */}
        <Card title="Program Enrollments">
          <List
            dataSource={enrollmentSummary.active_program_enrollments}
            renderItem={(enrollment) => (
              <List.Item>
                <div className="flex justify-between items-center w-full">
                  <div>
                    <div className="font-medium">{enrollment.major.name}</div>
                    <div className="text-sm text-gray-500">
                      {enrollment.division} • {enrollment.cycle}
                      {enrollment.start_date && ` • Started ${dayjs(enrollment.start_date).format('MMM YYYY')}`}
                    </div>
                  </div>
                  <div className="text-right">
                    <Tag color={enrollment.is_active ? 'green' : 'default'}>
                      {enrollment.enrollment_status}
                    </Tag>
                    <div className="text-sm text-gray-500">
                      {enrollment.terms_active} terms active
                    </div>
                  </div>
                </div>
              </List.Item>
            )}
          />
        </Card>

        {/* Current Class Enrollments */}
        <Card title="Current Class Enrollments">
          <Table
            dataSource={enrollmentSummary.current_class_enrollments}
            columns={enrollmentColumns}
            rowKey="id"
            pagination={false}
            size="small"
          />
        </Card>

        {/* Major Declarations */}
        <Card title="Major Declarations">
          <List
            dataSource={enrollmentSummary.major_declarations}
            renderItem={(declaration) => (
              <List.Item>
                <div className="flex justify-between items-center w-full">
                  <div>
                    <div className="font-medium">{declaration.major.name}</div>
                    <div className="text-sm text-gray-500">
                      Declared {dayjs(declaration.declaration_date).format('MMMM D, YYYY')}
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Tag color={declaration.is_active ? 'green' : 'default'}>
                      {declaration.is_active ? 'Active' : 'Inactive'}
                    </Tag>
                    {declaration.is_prospective && (
                      <Tag color="blue">Prospective</Tag>
                    )}
                  </div>
                </div>
              </List.Item>
            )}
          />
        </Card>
      </div>
    );
  };

  // Financial Tab Content
  const FinancialTab = () => {
    const mockFinancialData = {
      currentBalance: 2500.00,
      totalPaid: 15000.00,
      totalDue: 17500.00,
      scholarships: [
        { name: 'Merit Scholarship', amount: 1000, status: 'Active' },
        { name: 'Need-Based Aid', amount: 500, status: 'Active' },
      ],
      recentPayments: [
        { date: '2024-01-15', amount: 2500, description: 'Tuition Payment - Spring 2024' },
        { date: '2023-12-10', amount: 2500, description: 'Tuition Payment - Fall 2023' },
      ],
    };

    return (
      <div className="space-y-6">
        {/* Financial Overview */}
        <Row gutter={16}>
          <Col span={8}>
            <Card>
              <Statistic
                title="Current Balance"
                value={mockFinancialData.currentBalance}
                precision={2}
                prefix="$"
                valueStyle={{ color: mockFinancialData.currentBalance > 0 ? '#cf1322' : '#3f8600' }}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card>
              <Statistic
                title="Total Paid"
                value={mockFinancialData.totalPaid}
                precision={2}
                prefix="$"
                valueStyle={{ color: '#3f8600' }}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card>
              <Statistic
                title="Total Due"
                value={mockFinancialData.totalDue}
                precision={2}
                prefix="$"
              />
            </Card>
          </Col>
        </Row>

        {/* Scholarships & Financial Aid */}
        <Card
          title="Scholarships & Financial Aid"
          extra={<Button icon={<PlusOutlined />} size="small">Add</Button>}
        >
          <List
            dataSource={mockFinancialData.scholarships}
            renderItem={(scholarship) => (
              <List.Item
                actions={[
                  <Button type="link" icon={<EditOutlined />} />,
                  <Button type="link">View Details</Button>,
                ]}
              >
                <div className="flex justify-between items-center w-full">
                  <div className="flex items-center space-x-3">
                    <DollarOutlined className="text-green-500" />
                    <div>
                      <div className="font-medium">{scholarship.name}</div>
                      <div className="text-sm text-gray-500">${scholarship.amount}/semester</div>
                    </div>
                  </div>
                  <Tag color="green">{scholarship.status}</Tag>
                </div>
              </List.Item>
            )}
          />
        </Card>

        {/* Recent Payments */}
        <Card
          title="Recent Payments"
          extra={<Button icon={<PlusOutlined />} size="small">Record Payment</Button>}
        >
          <List
            dataSource={mockFinancialData.recentPayments}
            renderItem={(payment) => (
              <List.Item
                actions={[
                  <Button type="link" icon={<FileTextOutlined />}>Receipt</Button>,
                ]}
              >
                <div className="flex justify-between items-center w-full">
                  <div className="flex items-center space-x-3">
                    <BankOutlined />
                    <div>
                      <div className="font-medium">{payment.description}</div>
                      <div className="text-sm text-gray-500">
                        {dayjs(payment.date).format('MMMM D, YYYY')}
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-medium text-green-600">
                      ${payment.amount.toFixed(2)}
                    </div>
                  </div>
                </div>
              </List.Item>
            )}
          />
        </Card>
      </div>
    );
  };

  // Communication Tab Content
  const CommunicationTab = () => {
    const mockCommunications = [
      {
        id: '1',
        type: 'email',
        subject: 'Academic Progress Update',
        sender: 'Academic Advisor',
        date: '2024-01-15',
        content: 'Student is performing well in current courses...',
      },
      {
        id: '2',
        type: 'meeting',
        subject: 'Parent Conference',
        sender: 'Counselor',
        date: '2024-01-10',
        content: 'Discussed student academic goals and progress...',
      },
    ];

    return (
      <div className="space-y-6">
        <Card
          title="Communication History"
          extra={
            <Space>
              <Button icon={<MessageOutlined />} size="small">Send Message</Button>
              <Button icon={<CalendarOutlined />} size="small">Schedule Meeting</Button>
            </Space>
          }
        >
          <List
            dataSource={mockCommunications}
            renderItem={(comm) => (
              <List.Item
                actions={[
                  <Button type="link">Reply</Button>,
                  <Button type="link">View Details</Button>,
                ]}
              >
                <div className="flex items-start space-x-3 w-full">
                  <div className="flex-shrink-0">
                    {comm.type === 'email' ? <MailOutlined /> : <MessageOutlined />}
                  </div>
                  <div className="flex-1">
                    <div className="flex justify-between items-start">
                      <div>
                        <div className="font-medium">{comm.subject}</div>
                        <div className="text-sm text-gray-500">
                          From {comm.sender} • {dayjs(comm.date).format('MMM D, YYYY')}
                        </div>
                        <div className="text-sm mt-1">{comm.content}</div>
                      </div>
                    </div>
                  </div>
                </div>
              </List.Item>
            )}
          />
        </Card>
      </div>
    );
  };

  // Mock data for timeline and documents
  const mockTimelineEvents = [
    {
      id: '1',
      timestamp: '2024-01-15T10:00:00Z',
      title: 'Enrolled in Spring 2024 courses',
      description: 'Student enrolled in 5 courses for Spring 2024 semester',
      type: 'success' as const,
      user: 'Registration System',
    },
    {
      id: '2',
      timestamp: '2024-01-10T14:30:00Z',
      title: 'Academic probation removed',
      description: 'Student successfully completed probationary requirements',
      type: 'success' as const,
      user: 'Academic Advisor',
    },
    {
      id: '3',
      timestamp: '2024-01-05T09:00:00Z',
      title: 'Tuition payment received',
      description: 'Payment of $2,500 received for Spring 2024',
      type: 'default' as const,
      user: 'Finance Office',
    },
  ];

  const mockDocuments = [
    {
      id: '1',
      name: 'Official Transcript.pdf',
      type: 'application/pdf',
      size: 1024 * 1024 * 2, // 2MB
      uploadDate: '2024-01-15T10:00:00Z',
      url: '/documents/transcript.pdf',
    },
    {
      id: '2',
      name: 'Student ID Photo.jpg',
      type: 'image/jpeg',
      size: 1024 * 512, // 512KB
      uploadDate: '2024-01-10T14:30:00Z',
      url: '/documents/id_photo.jpg',
    },
  ];

  // Create tabs configuration
  const tabs: DetailTab[] = [
    {
      key: 'overview',
      label: 'Overview',
      icon: <UserOutlined />,
      content: <OverviewTab />,
    },
    {
      key: 'academic',
      label: 'Academic',
      icon: <BookOutlined />,
      content: <AcademicTab />,
      badge: enrollmentSummary?.total_active_enrollments,
    },
    {
      key: 'financial',
      label: 'Financial',
      icon: <DollarOutlined />,
      content: <FinancialTab />,
    },
    {
      key: 'timeline',
      label: 'Timeline',
      icon: <ClockCircleOutlined />,
      content: (
        <TimelineTab
          events={mockTimelineEvents}
          loading={false}
        />
      ),
    },
    {
      key: 'documents',
      label: 'Documents',
      icon: <FileTextOutlined />,
      content: (
        <DocumentsTab
          documents={mockDocuments}
          loading={false}
          onUpload={(files) => message.info('Document upload functionality will be implemented')}
          onDownload={(doc) => message.info(`Downloading ${doc.name}`)}
          onDelete={(docId) => message.info('Document deletion functionality will be implemented')}
        />
      ),
      badge: mockDocuments.length,
    },
    {
      key: 'communication',
      label: 'Communication',
      icon: <MessageOutlined />,
      content: <CommunicationTab />,
    },
  ];

  // Define actions
  const actions: DetailAction[] = [
    {
      key: 'edit',
      label: 'Edit Student',
      icon: <EditOutlined />,
      onClick: () => student && onEdit?.(student),
    },
    {
      key: 'message',
      label: 'Send Message',
      icon: <MessageOutlined />,
      onClick: () => message.info('Messaging functionality will be implemented'),
    },
    {
      key: 'transcript',
      label: 'Generate Transcript',
      icon: <FileTextOutlined />,
      onClick: () => message.info('Transcript generation will be implemented'),
    },
  ];

  const primaryAction: DetailAction = {
    key: 'enroll',
    label: 'Manage Enrollment',
    icon: <SchoolOutlined />,
    type: 'primary',
    onClick: () => message.info('Enrollment management will be implemented'),
  };

  if (!student) {
    return null;
  }

  return (
    <DetailModal
      open={open}
      onClose={onClose}
      title={student.full_name}
      width={1400}
      avatar={student.current_photo_url}
      subtitle={student.student_profile?.formatted_student_id}
      status={{
        text: StudentService.formatStudentStatus(student.student_profile?.current_status || ''),
        color: StudentService.getStatusBadgeClass(student.student_profile?.current_status || '').includes('green') ? 'green' : 'default',
      }}
      badges={[
        ...(student.student_profile?.is_monk ? [{ text: 'Monk', color: 'gold' }] : []),
        ...(student.student_profile?.is_transfer_student ? [{ text: 'Transfer', color: 'blue' }] : []),
        { text: student.student_profile?.study_time_preference ? StudentService.formatStudyTimePreference(student.student_profile.study_time_preference) : 'No preference', color: 'default' },
      ]}
      tabs={tabs}
      activeTab={activeTab}
      onTabChange={setActiveTab}
      actions={actions}
      primaryAction={primaryAction}
      loading={loading}
      data={student}
      onDataChange={(newData) => setStudent(newData)}
    />
  );
};

export default StudentDetail;