/**
 * StudentInterventionHub Component
 *
 * Automated intervention recommendation system with:
 * - Automated intervention recommendation system
 * - Customizable intervention workflows
 * - Progress tracking for intervention effectiveness
 * - Integration with counseling and academic support
 * - Automated alert system for high-risk students
 * - Success story tracking and pattern recognition
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Row,
  Col,
  Table,
  Button,
  Select,
  Input,
  Tag,
  Progress,
  Modal,
  Form,
  DatePicker,
  TextArea,
  Steps,
  Timeline,
  Statistic,
  Alert,
  Tabs,
  List,
  Avatar,
  Badge,
  Space,
  Tooltip,
  Drawer,
  Switch,
  InputNumber,
  Checkbox,
  Radio,
  Divider,
  Upload,
  message,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  UserOutlined,
  TeamOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  WarningOutlined,
  TrophyOutlined,
  BulbOutlined,
  BarChartOutlined,
  LineChartOutlined,
  FileTextOutlined,
  CalendarOutlined,
  MessageOutlined,
  PhoneOutlined,
  MailOutlined,
  RocketOutlined,
  StarOutlined,
  AlertOutlined,
  ReloadOutlined,
  SettingOutlined,
  ExportOutlined,
  ImportOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  StopOutlined,
  EyeOutlined,
  SendOutlined,
} from '@ant-design/icons';
import { Line, Bar, Doughnut } from 'react-chartjs-2';
import { motion, AnimatePresence } from 'framer-motion';
import moment from 'moment';
import { Intervention, StudentRiskFactor } from '../../../types/innovation';

const { Option } = Select;
const { TextArea: AntTextArea } = Input;
const { TabPane } = Tabs;
const { Step } = Steps;
const { RangePicker } = DatePicker;

interface InterventionRecord extends Intervention {
  studentId: string;
  studentName: string;
  createdBy: string;
  createdAt: Date;
  updatedAt: Date;
  assignedStaff?: string[];
  progress: number;
  notes: InterventionNote[];
  outcomes?: InterventionOutcome;
  tags: string[];
  category: 'academic' | 'financial' | 'personal' | 'behavioral' | 'career';
  urgency: 'low' | 'medium' | 'high' | 'critical';
  automatedTriggers?: string[];
}

interface InterventionNote {
  id: string;
  author: string;
  content: string;
  timestamp: Date;
  type: 'update' | 'milestone' | 'concern' | 'success';
  attachments?: string[];
}

interface InterventionOutcome {
  status: 'success' | 'partial' | 'failed' | 'ongoing';
  impactScore: number;
  measuredResults: Record<string, number>;
  lessons: string[];
  recommendations: string[];
}

interface InterventionTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  defaultDuration: number;
  steps: InterventionStep[];
  requiredStaff: string[];
  resources: string[];
  successMetrics: string[];
  triggers: string[];
}

interface InterventionStep {
  id: string;
  title: string;
  description: string;
  duration: number;
  dependencies: string[];
  assignedRole: string;
  requiredActions: string[];
  deliverables: string[];
}

interface AutomationRule {
  id: string;
  name: string;
  description: string;
  triggers: {
    type: 'grade_drop' | 'attendance_low' | 'financial_aid' | 'advisor_referral' | 'risk_score';
    threshold: number;
    condition: string;
  }[];
  actions: {
    type: 'create_intervention' | 'send_alert' | 'schedule_meeting' | 'notify_staff';
    config: Record<string, any>;
  }[];
  active: boolean;
  priority: number;
}

const StudentInterventionHub: React.FC = () => {
  // State management
  const [interventions, setInterventions] = useState<InterventionRecord[]>([]);
  const [templates, setTemplates] = useState<InterventionTemplate[]>([]);
  const [automationRules, setAutomationRules] = useState<AutomationRule[]>([]);
  const [selectedIntervention, setSelectedIntervention] = useState<InterventionRecord | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('active');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showTemplateModal, setShowTemplateModal] = useState(false);
  const [showAutomationModal, setShowAutomationModal] = useState(false);
  const [showDetailDrawer, setShowDetailDrawer] = useState(false);
  const [filters, setFilters] = useState({
    status: 'all',
    category: 'all',
    urgency: 'all',
    assignedStaff: 'all',
    dateRange: null as any,
  });

  // Form instances
  const [createForm] = Form.useForm();
  const [templateForm] = Form.useForm();
  const [automationForm] = Form.useForm();

  // Load data on component mount
  useEffect(() => {
    loadInterventions();
    loadTemplates();
    loadAutomationRules();
  }, []);

  const loadInterventions = async () => {
    setLoading(true);
    try {
      // Mock data - in real implementation, this would be an API call
      const mockInterventions: InterventionRecord[] = [
        {
          id: 'int_001',
          studentId: 'stu_001',
          studentName: 'Sarah Johnson',
          type: 'academic_support',
          title: 'Intensive Tutoring Program',
          description: 'Weekly tutoring sessions for struggling math courses',
          priority: 'high',
          estimatedImpact: 0.7,
          timeToImplement: '1 week',
          cost: 500,
          status: 'active',
          successRate: 0.75,
          assignedTo: 'Dr. Smith',
          createdBy: 'Academic Advisor',
          createdAt: new Date('2024-09-20'),
          updatedAt: new Date('2024-09-26'),
          assignedStaff: ['tutor_001', 'advisor_001'],
          progress: 65,
          notes: [
            {
              id: 'note_001',
              author: 'Dr. Smith',
              content: 'Student showing good progress in algebra concepts',
              timestamp: new Date('2024-09-25'),
              type: 'update',
            },
            {
              id: 'note_002',
              author: 'Tutor Assistant',
              content: 'Completed week 2 of intensive tutoring. Student engagement improved.',
              timestamp: new Date('2024-09-23'),
              type: 'milestone',
            }
          ],
          tags: ['math', 'tutoring', 'at-risk'],
          category: 'academic',
          urgency: 'high',
          automatedTriggers: ['gpa_drop_below_2.5'],
        },
        {
          id: 'int_002',
          studentId: 'stu_002',
          studentName: 'Michael Chen',
          type: 'financial_aid',
          title: 'Emergency Financial Assistance',
          description: 'Financial aid assessment and emergency fund application',
          priority: 'urgent',
          estimatedImpact: 0.6,
          timeToImplement: '3 days',
          cost: 0,
          status: 'completed',
          successRate: 0.8,
          assignedTo: 'Financial Aid Office',
          createdBy: 'Academic Advisor',
          createdAt: new Date('2024-09-15'),
          updatedAt: new Date('2024-09-22'),
          assignedStaff: ['fin_001', 'advisor_002'],
          progress: 100,
          notes: [
            {
              id: 'note_003',
              author: 'Financial Aid Counselor',
              content: 'Emergency fund approved. Student can continue enrollment.',
              timestamp: new Date('2024-09-18'),
              type: 'success',
            }
          ],
          outcomes: {
            status: 'success',
            impactScore: 0.85,
            measuredResults: {
              financial_stress_reduction: 0.9,
              retention_probability: 0.8,
            },
            lessons: ['Early financial intervention prevents dropouts'],
            recommendations: ['Monitor other at-risk students for financial stress'],
          },
          tags: ['financial', 'emergency', 'retention'],
          category: 'financial',
          urgency: 'critical',
          automatedTriggers: ['work_hours_above_30'],
        },
      ];

      setInterventions(mockInterventions);
    } catch (error) {
      console.error('Failed to load interventions:', error);
      message.error('Failed to load interventions');
    } finally {
      setLoading(false);
    }
  };

  const loadTemplates = async () => {
    try {
      const mockTemplates: InterventionTemplate[] = [
        {
          id: 'temp_001',
          name: 'Academic Support Package',
          description: 'Comprehensive academic intervention for struggling students',
          category: 'academic',
          defaultDuration: 30,
          steps: [
            {
              id: 'step_001',
              title: 'Initial Assessment',
              description: 'Assess student learning gaps and challenges',
              duration: 3,
              dependencies: [],
              assignedRole: 'Academic Advisor',
              requiredActions: ['Schedule meeting', 'Conduct assessment', 'Identify gaps'],
              deliverables: ['Assessment report', 'Learning plan'],
            },
            {
              id: 'step_002',
              title: 'Tutoring Setup',
              description: 'Arrange appropriate tutoring resources',
              duration: 5,
              dependencies: ['step_001'],
              assignedRole: 'Tutoring Coordinator',
              requiredActions: ['Match tutor', 'Schedule sessions', 'Set goals'],
              deliverables: ['Tutoring schedule', 'Learning objectives'],
            }
          ],
          requiredStaff: ['Academic Advisor', 'Tutor', 'Subject Expert'],
          resources: ['Tutoring center', 'Learning materials', 'Assessment tools'],
          successMetrics: ['GPA improvement', 'Course completion', 'Student satisfaction'],
          triggers: ['gpa_below_2.5', 'failing_multiple_courses'],
        }
      ];

      setTemplates(mockTemplates);
    } catch (error) {
      console.error('Failed to load templates:', error);
    }
  };

  const loadAutomationRules = async () => {
    try {
      const mockRules: AutomationRule[] = [
        {
          id: 'rule_001',
          name: 'GPA Alert System',
          description: 'Automatically create interventions for students with GPA below 2.5',
          triggers: [
            {
              type: 'grade_drop',
              threshold: 2.5,
              condition: 'current_gpa < threshold',
            }
          ],
          actions: [
            {
              type: 'create_intervention',
              config: {
                templateId: 'temp_001',
                priority: 'high',
                assignTo: 'academic_advisor',
              },
            },
            {
              type: 'send_alert',
              config: {
                recipients: ['academic_advisor', 'department_head'],
                message: 'Student requires immediate academic intervention',
              },
            }
          ],
          active: true,
          priority: 1,
        }
      ];

      setAutomationRules(mockRules);
    } catch (error) {
      console.error('Failed to load automation rules:', error);
    }
  };

  const createIntervention = useCallback(async (values: any) => {
    try {
      setLoading(true);

      const newIntervention: InterventionRecord = {
        id: `int_${Date.now()}`,
        studentId: values.studentId,
        studentName: values.studentName,
        type: values.type,
        title: values.title,
        description: values.description,
        priority: values.priority,
        estimatedImpact: values.estimatedImpact / 100,
        timeToImplement: values.timeToImplement,
        cost: values.cost || 0,
        status: 'recommended',
        successRate: values.successRate ? values.successRate / 100 : 0.5,
        assignedTo: values.assignedTo,
        createdBy: 'Current User', // In real app, get from auth context
        createdAt: new Date(),
        updatedAt: new Date(),
        assignedStaff: values.assignedStaff || [],
        progress: 0,
        notes: [],
        tags: values.tags || [],
        category: values.category,
        urgency: values.urgency,
      };

      setInterventions(prev => [newIntervention, ...prev]);
      setShowCreateModal(false);
      createForm.resetFields();
      message.success('Intervention created successfully');

    } catch (error) {
      console.error('Failed to create intervention:', error);
      message.error('Failed to create intervention');
    } finally {
      setLoading(false);
    }
  }, [createForm]);

  const updateInterventionStatus = useCallback(async (id: string, status: string) => {
    try {
      setInterventions(prev =>
        prev.map(intervention =>
          intervention.id === id
            ? { ...intervention, status: status as any, updatedAt: new Date() }
            : intervention
        )
      );
      message.success('Intervention status updated');
    } catch (error) {
      console.error('Failed to update status:', error);
      message.error('Failed to update status');
    }
  }, []);

  const addNote = useCallback(async (interventionId: string, note: string, type: string) => {
    try {
      const newNote: InterventionNote = {
        id: `note_${Date.now()}`,
        author: 'Current User',
        content: note,
        timestamp: new Date(),
        type: type as any,
      };

      setInterventions(prev =>
        prev.map(intervention =>
          intervention.id === interventionId
            ? { ...intervention, notes: [...intervention.notes, newNote], updatedAt: new Date() }
            : intervention
        )
      );

      message.success('Note added successfully');
    } catch (error) {
      console.error('Failed to add note:', error);
      message.error('Failed to add note');
    }
  }, []);

  // Filter interventions based on current filters
  const filteredInterventions = interventions.filter(intervention => {
    return (
      (filters.status === 'all' || intervention.status === filters.status) &&
      (filters.category === 'all' || intervention.category === filters.category) &&
      (filters.urgency === 'all' || intervention.urgency === filters.urgency) &&
      (filters.assignedStaff === 'all' || intervention.assignedStaff?.includes(filters.assignedStaff))
    );
  });

  // Calculate statistics
  const stats = {
    total: interventions.length,
    active: interventions.filter(i => i.status === 'active').length,
    completed: interventions.filter(i => i.status === 'completed').length,
    averageProgress: interventions.reduce((acc, i) => acc + i.progress, 0) / interventions.length || 0,
    highPriority: interventions.filter(i => i.priority === 'urgent' || i.priority === 'high').length,
    successRate: interventions.filter(i => i.outcomes?.status === 'success').length /
                 interventions.filter(i => i.status === 'completed').length || 0,
  };

  // Chart data
  const categoryData = {
    labels: ['Academic', 'Financial', 'Personal', 'Behavioral', 'Career'],
    datasets: [{
      data: [
        interventions.filter(i => i.category === 'academic').length,
        interventions.filter(i => i.category === 'financial').length,
        interventions.filter(i => i.category === 'personal').length,
        interventions.filter(i => i.category === 'behavioral').length,
        interventions.filter(i => i.category === 'career').length,
      ],
      backgroundColor: [
        '#3B82F6',
        '#10B981',
        '#F59E0B',
        '#EF4444',
        '#8B5CF6',
      ],
    }],
  };

  const progressData = {
    labels: interventions.map(i => i.studentName),
    datasets: [{
      label: 'Progress (%)',
      data: interventions.map(i => i.progress),
      backgroundColor: 'rgba(59, 130, 246, 0.6)',
      borderColor: 'rgb(59, 130, 246)',
      borderWidth: 1,
    }],
  };

  const columns = [
    {
      title: 'Student',
      key: 'student',
      render: (record: InterventionRecord) => (
        <div className="flex items-center gap-2">
          <Avatar icon={<UserOutlined />} />
          <div>
            <div className="font-medium">{record.studentName}</div>
            <div className="text-xs text-gray-500">{record.studentId}</div>
          </div>
        </div>
      ),
    },
    {
      title: 'Intervention',
      key: 'intervention',
      render: (record: InterventionRecord) => (
        <div>
          <div className="font-medium">{record.title}</div>
          <div className="text-xs text-gray-500">{record.description}</div>
          <div className="mt-1">
            <Tag color={record.category === 'academic' ? 'blue' :
                       record.category === 'financial' ? 'green' :
                       record.category === 'personal' ? 'orange' :
                       record.category === 'behavioral' ? 'red' : 'purple'}>
              {record.category.toUpperCase()}
            </Tag>
          </div>
        </div>
      ),
    },
    {
      title: 'Priority',
      dataIndex: 'urgency',
      key: 'urgency',
      render: (urgency: string) => (
        <Tag color={urgency === 'critical' ? 'red' :
                   urgency === 'high' ? 'orange' :
                   urgency === 'medium' ? 'blue' : 'green'}>
          {urgency.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={status === 'completed' ? 'green' :
                   status === 'active' ? 'blue' :
                   status === 'paused' ? 'orange' : 'gray'}
             icon={status === 'completed' ? <CheckCircleOutlined /> :
                   status === 'active' ? <PlayCircleOutlined /> :
                   status === 'paused' ? <PauseCircleOutlined /> : <ClockCircleOutlined />}>
          {status.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: 'Progress',
      key: 'progress',
      render: (record: InterventionRecord) => (
        <div style={{ width: 100 }}>
          <Progress
            percent={record.progress}
            size="small"
            status={record.progress === 100 ? 'success' : 'active'}
          />
        </div>
      ),
    },
    {
      title: 'Assigned To',
      dataIndex: 'assignedTo',
      key: 'assignedTo',
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (record: InterventionRecord) => (
        <Space>
          <Tooltip title="View Details">
            <Button
              size="small"
              icon={<EyeOutlined />}
              onClick={() => {
                setSelectedIntervention(record);
                setShowDetailDrawer(true);
              }}
            />
          </Tooltip>
          <Tooltip title="Update Status">
            <Select
              size="small"
              value={record.status}
              style={{ width: 100 }}
              onChange={(value) => updateInterventionStatus(record.id, value)}
            >
              <Option value="recommended">Recommended</Option>
              <Option value="active">Active</Option>
              <Option value="paused">Paused</Option>
              <Option value="completed">Completed</Option>
              <Option value="declined">Declined</Option>
            </Select>
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <div className="student-intervention-hub p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
              <BulbOutlined className="text-green-600" />
              Student Intervention Hub
            </h1>
            <p className="text-gray-600 mt-2">
              Automated intervention management and success tracking system
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              icon={<PlusOutlined />}
              type="primary"
              onClick={() => setShowCreateModal(true)}
            >
              Create Intervention
            </Button>
            <Button
              icon={<SettingOutlined />}
              onClick={() => setShowTemplateModal(true)}
            >
              Templates
            </Button>
            <Button
              icon={<RocketOutlined />}
              onClick={() => setShowAutomationModal(true)}
            >
              Automation
            </Button>
            <Button icon={<ReloadOutlined />} onClick={loadInterventions}>
              Refresh
            </Button>
          </div>
        </div>
      </div>

      {/* Statistics Cards */}
      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={24} sm={8} lg={4}>
          <Card>
            <Statistic
              title="Total Interventions"
              value={stats.total}
              prefix={<TeamOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8} lg={4}>
          <Card>
            <Statistic
              title="Active"
              value={stats.active}
              prefix={<PlayCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8} lg={4}>
          <Card>
            <Statistic
              title="Completed"
              value={stats.completed}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8} lg={4}>
          <Card>
            <Statistic
              title="Avg Progress"
              value={stats.averageProgress.toFixed(1)}
              suffix="%"
              prefix={<BarChartOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8} lg={4}>
          <Card>
            <Statistic
              title="High Priority"
              value={stats.highPriority}
              prefix={<AlertOutlined />}
              valueStyle={{ color: '#f5222d' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8} lg={4}>
          <Card>
            <Statistic
              title="Success Rate"
              value={(stats.successRate * 100).toFixed(1)}
              suffix="%"
              prefix={<TrophyOutlined />}
              valueStyle={{ color: '#13c2c2' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Main Content */}
      <Row gutter={[24, 24]}>
        <Col xs={24} lg={16}>
          <Card
            title="Intervention Management"
            extra={
              <Space>
                <Select
                  placeholder="Filter by Status"
                  style={{ width: 120 }}
                  value={filters.status}
                  onChange={(value) => setFilters(prev => ({ ...prev, status: value }))}
                >
                  <Option value="all">All Status</Option>
                  <Option value="recommended">Recommended</Option>
                  <Option value="active">Active</Option>
                  <Option value="completed">Completed</Option>
                  <Option value="paused">Paused</Option>
                </Select>
                <Select
                  placeholder="Filter by Category"
                  style={{ width: 120 }}
                  value={filters.category}
                  onChange={(value) => setFilters(prev => ({ ...prev, category: value }))}
                >
                  <Option value="all">All Categories</Option>
                  <Option value="academic">Academic</Option>
                  <Option value="financial">Financial</Option>
                  <Option value="personal">Personal</Option>
                  <Option value="behavioral">Behavioral</Option>
                  <Option value="career">Career</Option>
                </Select>
              </Space>
            }
          >
            <Table
              dataSource={filteredInterventions}
              columns={columns}
              rowKey="id"
              loading={loading}
              pagination={{
                pageSize: 10,
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total, range) => `${range[0]}-${range[1]} of ${total} interventions`,
              }}
              scroll={{ x: 1200 }}
            />
          </Card>
        </Col>

        <Col xs={24} lg={8}>
          <div className="space-y-6">
            {/* Category Distribution */}
            <Card title="Intervention Categories">
              <div style={{ height: '250px' }}>
                <Doughnut
                  data={categoryData}
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                      legend: {
                        position: 'bottom' as const,
                      },
                    },
                  }}
                />
              </div>
            </Card>

            {/* Recent Activity */}
            <Card title="Recent Activity">
              <Timeline>
                {interventions.slice(0, 5).map((intervention) => (
                  <Timeline.Item
                    key={intervention.id}
                    color={
                      intervention.status === 'completed' ? 'green' :
                      intervention.status === 'active' ? 'blue' : 'gray'
                    }
                  >
                    <div className="text-sm">
                      <div className="font-medium">{intervention.title}</div>
                      <div className="text-gray-500">{intervention.studentName}</div>
                      <div className="text-xs text-gray-400">
                        {moment(intervention.updatedAt).fromNow()}
                      </div>
                    </div>
                  </Timeline.Item>
                ))}
              </Timeline>
            </Card>

            {/* Automation Status */}
            <Card title="Automation Rules" extra={
              <Tag color="green">{automationRules.filter(r => r.active).length} Active</Tag>
            }>
              <List
                size="small"
                dataSource={automationRules.slice(0, 3)}
                renderItem={(rule) => (
                  <List.Item>
                    <div className="flex justify-between items-center w-full">
                      <div>
                        <div className="font-medium text-sm">{rule.name}</div>
                        <div className="text-xs text-gray-500">{rule.description}</div>
                      </div>
                      <Switch
                        size="small"
                        checked={rule.active}
                        onChange={(checked) => {
                          setAutomationRules(prev =>
                            prev.map(r => r.id === rule.id ? { ...r, active: checked } : r)
                          );
                        }}
                      />
                    </div>
                  </List.Item>
                )}
              />
            </Card>
          </div>
        </Col>
      </Row>

      {/* Create Intervention Modal */}
      <Modal
        title="Create New Intervention"
        open={showCreateModal}
        onCancel={() => {
          setShowCreateModal(false);
          createForm.resetFields();
        }}
        footer={null}
        width={800}
      >
        <Form
          form={createForm}
          layout="vertical"
          onFinish={createIntervention}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="studentName"
                label="Student Name"
                rules={[{ required: true, message: 'Please enter student name' }]}
              >
                <Input placeholder="Enter student name" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="studentId"
                label="Student ID"
                rules={[{ required: true, message: 'Please enter student ID' }]}
              >
                <Input placeholder="Enter student ID" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="title"
            label="Intervention Title"
            rules={[{ required: true, message: 'Please enter intervention title' }]}
          >
            <Input placeholder="e.g., Academic Support Program" />
          </Form.Item>

          <Form.Item
            name="description"
            label="Description"
            rules={[{ required: true, message: 'Please enter description' }]}
          >
            <AntTextArea
              rows={3}
              placeholder="Describe the intervention and its goals"
            />
          </Form.Item>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="category"
                label="Category"
                rules={[{ required: true, message: 'Please select category' }]}
              >
                <Select placeholder="Select category">
                  <Option value="academic">Academic</Option>
                  <Option value="financial">Financial</Option>
                  <Option value="personal">Personal</Option>
                  <Option value="behavioral">Behavioral</Option>
                  <Option value="career">Career</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="urgency"
                label="Urgency"
                rules={[{ required: true, message: 'Please select urgency' }]}
              >
                <Select placeholder="Select urgency">
                  <Option value="low">Low</Option>
                  <Option value="medium">Medium</Option>
                  <Option value="high">High</Option>
                  <Option value="critical">Critical</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="type"
                label="Type"
                rules={[{ required: true, message: 'Please select type' }]}
              >
                <Select placeholder="Select type">
                  <Option value="academic_support">Academic Support</Option>
                  <Option value="financial_aid">Financial Aid</Option>
                  <Option value="counseling">Counseling</Option>
                  <Option value="tutoring">Tutoring</Option>
                  <Option value="mentoring">Mentoring</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="estimatedImpact"
                label="Estimated Impact (%)"
              >
                <InputNumber
                  min={0}
                  max={100}
                  style={{ width: '100%' }}
                  placeholder="e.g., 70"
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="timeToImplement"
                label="Time to Implement"
              >
                <Input placeholder="e.g., 1 week" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="cost"
                label="Estimated Cost ($)"
              >
                <InputNumber
                  min={0}
                  style={{ width: '100%' }}
                  placeholder="0"
                />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="assignedTo"
            label="Assigned To"
          >
            <Input placeholder="Staff member or department" />
          </Form.Item>

          <Form.Item
            name="tags"
            label="Tags"
          >
            <Select
              mode="tags"
              placeholder="Add tags for categorization"
              style={{ width: '100%' }}
            >
              <Option value="urgent">urgent</Option>
              <Option value="academic">academic</Option>
              <Option value="financial">financial</Option>
              <Option value="at-risk">at-risk</Option>
            </Select>
          </Form.Item>

          <div className="flex justify-end gap-2">
            <Button onClick={() => {
              setShowCreateModal(false);
              createForm.resetFields();
            }}>
              Cancel
            </Button>
            <Button type="primary" htmlType="submit" loading={loading}>
              Create Intervention
            </Button>
          </div>
        </Form>
      </Modal>

      {/* Intervention Detail Drawer */}
      <Drawer
        title={selectedIntervention?.title}
        placement="right"
        width={600}
        open={showDetailDrawer}
        onClose={() => {
          setShowDetailDrawer(false);
          setSelectedIntervention(null);
        }}
      >
        {selectedIntervention && (
          <div className="space-y-6">
            {/* Basic Info */}
            <div>
              <h3 className="text-lg font-semibold mb-3">Intervention Details</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm text-gray-500">Student</label>
                  <div className="font-medium">{selectedIntervention.studentName}</div>
                </div>
                <div>
                  <label className="text-sm text-gray-500">Category</label>
                  <div>
                    <Tag color={selectedIntervention.category === 'academic' ? 'blue' : 'green'}>
                      {selectedIntervention.category.toUpperCase()}
                    </Tag>
                  </div>
                </div>
                <div>
                  <label className="text-sm text-gray-500">Priority</label>
                  <div>
                    <Tag color={selectedIntervention.urgency === 'critical' ? 'red' : 'orange'}>
                      {selectedIntervention.urgency.toUpperCase()}
                    </Tag>
                  </div>
                </div>
                <div>
                  <label className="text-sm text-gray-500">Status</label>
                  <div>
                    <Tag color={selectedIntervention.status === 'active' ? 'blue' : 'green'}>
                      {selectedIntervention.status.toUpperCase()}
                    </Tag>
                  </div>
                </div>
              </div>
            </div>

            <Divider />

            {/* Progress */}
            <div>
              <h3 className="text-lg font-semibold mb-3">Progress</h3>
              <Progress
                percent={selectedIntervention.progress}
                status={selectedIntervention.progress === 100 ? 'success' : 'active'}
              />
              <div className="mt-2 text-sm text-gray-600">
                Created: {moment(selectedIntervention.createdAt).format('MMM DD, YYYY')}
              </div>
            </div>

            <Divider />

            {/* Notes */}
            <div>
              <div className="flex justify-between items-center mb-3">
                <h3 className="text-lg font-semibold">Notes & Updates</h3>
                <Button
                  size="small"
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={() => {
                    const note = prompt('Add a note:');
                    if (note) {
                      addNote(selectedIntervention.id, note, 'update');
                    }
                  }}
                >
                  Add Note
                </Button>
              </div>
              <Timeline>
                {selectedIntervention.notes.map((note) => (
                  <Timeline.Item
                    key={note.id}
                    color={
                      note.type === 'success' ? 'green' :
                      note.type === 'concern' ? 'red' :
                      note.type === 'milestone' ? 'blue' : 'gray'
                    }
                  >
                    <div>
                      <div className="font-medium">{note.author}</div>
                      <div className="text-sm text-gray-600">{note.content}</div>
                      <div className="text-xs text-gray-400">
                        {moment(note.timestamp).format('MMM DD, YYYY HH:mm')}
                      </div>
                    </div>
                  </Timeline.Item>
                ))}
              </Timeline>
            </div>

            {/* Outcomes */}
            {selectedIntervention.outcomes && (
              <>
                <Divider />
                <div>
                  <h3 className="text-lg font-semibold mb-3">Outcomes</h3>
                  <div className="space-y-3">
                    <div>
                      <label className="text-sm text-gray-500">Status</label>
                      <div>
                        <Tag color={selectedIntervention.outcomes.status === 'success' ? 'green' : 'orange'}>
                          {selectedIntervention.outcomes.status.toUpperCase()}
                        </Tag>
                      </div>
                    </div>
                    <div>
                      <label className="text-sm text-gray-500">Impact Score</label>
                      <div className="font-medium">
                        {(selectedIntervention.outcomes.impactScore * 100).toFixed(1)}%
                      </div>
                    </div>
                    {selectedIntervention.outcomes.lessons.length > 0 && (
                      <div>
                        <label className="text-sm text-gray-500">Lessons Learned</label>
                        <ul className="list-disc list-inside text-sm">
                          {selectedIntervention.outcomes.lessons.map((lesson, index) => (
                            <li key={index}>{lesson}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              </>
            )}
          </div>
        )}
      </Drawer>

      {/* Template Modal */}
      <Modal
        title="Intervention Templates"
        open={showTemplateModal}
        onCancel={() => setShowTemplateModal(false)}
        footer={null}
        width={800}
      >
        <div className="space-y-4">
          {templates.map((template) => (
            <Card key={template.id} size="small">
              <div className="flex justify-between items-start">
                <div>
                  <h4 className="font-semibold">{template.name}</h4>
                  <p className="text-gray-600 text-sm">{template.description}</p>
                  <div className="mt-2">
                    <Tag>{template.category}</Tag>
                    <Tag>Duration: {template.defaultDuration} days</Tag>
                    <Tag>Steps: {template.steps.length}</Tag>
                  </div>
                </div>
                <Button
                  type="primary"
                  size="small"
                  onClick={() => {
                    // Pre-fill create form with template data
                    createForm.setFieldsValue({
                      title: template.name,
                      description: template.description,
                      category: template.category,
                      type: template.category + '_support',
                    });
                    setShowTemplateModal(false);
                    setShowCreateModal(true);
                  }}
                >
                  Use Template
                </Button>
              </div>
            </Card>
          ))}
        </div>
      </Modal>

      {/* Automation Modal */}
      <Modal
        title="Automation Rules"
        open={showAutomationModal}
        onCancel={() => setShowAutomationModal(false)}
        footer={null}
        width={800}
      >
        <div className="space-y-4">
          {automationRules.map((rule) => (
            <Card key={rule.id} size="small">
              <div className="flex justify-between items-start">
                <div>
                  <h4 className="font-semibold">{rule.name}</h4>
                  <p className="text-gray-600 text-sm">{rule.description}</p>
                  <div className="mt-2">
                    <Tag color={rule.active ? 'green' : 'red'}>
                      {rule.active ? 'Active' : 'Inactive'}
                    </Tag>
                    <Tag>Priority: {rule.priority}</Tag>
                    <Tag>Triggers: {rule.triggers.length}</Tag>
                    <Tag>Actions: {rule.actions.length}</Tag>
                  </div>
                </div>
                <Switch
                  checked={rule.active}
                  onChange={(checked) => {
                    setAutomationRules(prev =>
                      prev.map(r => r.id === rule.id ? { ...r, active: checked } : r)
                    );
                  }}
                />
              </div>
            </Card>
          ))}
        </div>
      </Modal>
    </div>
  );
};

export default StudentInterventionHub;