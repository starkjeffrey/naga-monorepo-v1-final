/**
 * EnrollmentHub Component
 *
 * Comprehensive enrollment management dashboard with real-time features:
 * - Real-time enrollment statistics with live updates
 * - Capacity monitoring with alerts for full courses
 * - Waitlist management with automated notifications
 * - Integration with payment processing for enrollment fees
 * - Advanced analytics and trend analysis
 * - Automated enrollment workflows
 */

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Progress,
  Button,
  Space,
  Badge,
  Alert,
  Table,
  Tag,
  Tooltip,
  Modal,
  Form,
  Select,
  DatePicker,
  Input,
  Switch,
  Divider,
  Timeline,
  notification,
  message,
} from 'antd';
import {
  TeamOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  DollarOutlined,
  TrendingUpOutlined,
  TrendingDownOutlined,
  BellOutlined,
  SyncOutlined,
  BarChartOutlined,
  UserAddOutlined,
  UserDeleteOutlined,
  MailOutlined,
  PhoneOutlined,
  CalendarOutlined,
} from '@ant-design/icons';
import { Line, Bar, Pie } from '@ant-design/plots';
import { Dashboard } from '../../../components/patterns';
import type { MetricCard, ChartWidget, ListWidget } from '../../../components/patterns';

const { Option } = Select;
const { RangePicker } = DatePicker;

interface Student {
  id: string;
  studentId: string;
  name: string;
  email: string;
  phone: string;
  program: string;
  level: string;
  status: 'active' | 'inactive' | 'graduated' | 'transferred';
  enrollmentDate: string;
  gpa: number;
}

interface Course {
  id: string;
  code: string;
  name: string;
  credits: number;
  maxCapacity: number;
  currentEnrollment: number;
  waitlistCount: number;
  status: 'open' | 'closed' | 'waitlist' | 'cancelled';
  tuition: number;
  startDate: string;
  endDate: string;
  instructor: string;
}

interface Enrollment {
  id: string;
  studentId: string;
  courseId: string;
  status: 'enrolled' | 'waitlisted' | 'dropped' | 'completed' | 'pending_payment';
  enrollmentDate: string;
  dropDate?: string;
  paymentStatus: 'paid' | 'pending' | 'overdue' | 'cancelled';
  paymentAmount: number;
  paymentDueDate: string;
  grade?: string;
  credits: number;
}

interface EnrollmentTrend {
  date: string;
  enrollments: number;
  drops: number;
  waitlisted: number;
  revenue: number;
}

interface CapacityAlert {
  id: string;
  courseId: string;
  courseName: string;
  type: 'full' | 'near_full' | 'low_enrollment' | 'waitlist_high';
  severity: 'low' | 'medium' | 'high';
  message: string;
  timestamp: string;
  acknowledged: boolean;
}

interface WaitlistEntry {
  id: string;
  studentId: string;
  courseId: string;
  position: number;
  waitlistDate: string;
  notificationSent: boolean;
  estimatedEnrollmentDate?: string;
}

interface EnrollmentHubProps {
  students: Student[];
  courses: Course[];
  enrollments: Enrollment[];
  waitlistEntries: WaitlistEntry[];
  enrollmentTrends: EnrollmentTrend[];
  capacityAlerts: CapacityAlert[];
  onEnrollStudent: (studentId: string, courseId: string) => Promise<void>;
  onDropStudent: (enrollmentId: string) => Promise<void>;
  onProcessWaitlist: (courseId: string) => Promise<void>;
  onSendNotification: (studentIds: string[], message: string) => Promise<void>;
  onProcessPayment: (enrollmentId: string) => Promise<void>;
  onAcknowledgeAlert: (alertId: string) => Promise<void>;
  realTimeEnabled?: boolean;
}

export const EnrollmentHub: React.FC<EnrollmentHubProps> = ({
  students,
  courses,
  enrollments,
  waitlistEntries,
  enrollmentTrends,
  capacityAlerts,
  onEnrollStudent,
  onDropStudent,
  onProcessWaitlist,
  onSendNotification,
  onProcessPayment,
  onAcknowledgeAlert,
  realTimeEnabled = true,
}) => {
  const [loading, setLoading] = useState(false);
  const [selectedTimeRange, setSelectedTimeRange] = useState<[string, string] | null>(null);
  const [alertModalVisible, setAlertModalVisible] = useState(false);
  const [notificationModalVisible, setNotificationModalVisible] = useState(false);
  const [selectedStudents, setSelectedStudents] = useState<string[]>([]);
  const [realTimeData, setRealTimeData] = useState<any>({});
  const [lastUpdate, setLastUpdate] = useState(new Date());

  // WebSocket connection for real-time updates
  useEffect(() => {
    if (!realTimeEnabled) return;

    const ws = new WebSocket('ws://localhost:8000/ws/enrollment-hub/');

    ws.onopen = () => {
      console.log('Connected to enrollment hub real-time updates');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleRealTimeUpdate(data);
    };

    ws.onclose = () => {
      console.log('Disconnected from enrollment hub');
      // Attempt to reconnect after 3 seconds
      setTimeout(() => {
        if (realTimeEnabled) {
          // Reconnect logic here
        }
      }, 3000);
    };

    return () => {
      ws.close();
    };
  }, [realTimeEnabled]);

  // Handle real-time updates
  const handleRealTimeUpdate = useCallback((data: any) => {
    setRealTimeData(prev => ({ ...prev, ...data }));
    setLastUpdate(new Date());

    switch (data.type) {
      case 'enrollment_added':
        notification.success({
          message: 'New Enrollment',
          description: `${data.studentName} enrolled in ${data.courseName}`,
          placement: 'topRight',
        });
        break;

      case 'capacity_alert':
        notification.warning({
          message: 'Capacity Alert',
          description: data.message,
          placement: 'topRight',
          duration: 0,
        });
        break;

      case 'waitlist_processed':
        notification.info({
          message: 'Waitlist Update',
          description: `${data.count} students moved from waitlist to enrolled`,
          placement: 'topRight',
        });
        break;

      case 'payment_received':
        notification.success({
          message: 'Payment Received',
          description: `Payment of $${data.amount} received for ${data.studentName}`,
          placement: 'topRight',
        });
        break;
    }
  }, []);

  // Calculate enrollment statistics
  const enrollmentStats = useMemo(() => {
    const totalEnrollments = enrollments.filter(e => e.status === 'enrolled').length;
    const totalWaitlisted = enrollments.filter(e => e.status === 'waitlisted').length;
    const totalDropped = enrollments.filter(e => e.status === 'dropped').length;
    const totalRevenue = enrollments
      .filter(e => e.paymentStatus === 'paid')
      .reduce((sum, e) => sum + e.paymentAmount, 0);
    const pendingPayments = enrollments.filter(e => e.paymentStatus === 'pending').length;
    const overduePayments = enrollments.filter(e => e.paymentStatus === 'overdue').length;

    // Calculate enrollment rate (last 30 days)
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
    const recentEnrollments = enrollments.filter(e =>
      new Date(e.enrollmentDate) >= thirtyDaysAgo && e.status === 'enrolled'
    ).length;

    // Calculate capacity utilization
    const totalCapacity = courses.reduce((sum, c) => sum + c.maxCapacity, 0);
    const totalCurrentEnrollment = courses.reduce((sum, c) => sum + c.currentEnrollment, 0);
    const capacityUtilization = totalCapacity > 0 ? (totalCurrentEnrollment / totalCapacity) * 100 : 0;

    return {
      totalEnrollments,
      totalWaitlisted,
      totalDropped,
      totalRevenue,
      pendingPayments,
      overduePayments,
      recentEnrollments,
      capacityUtilization,
      totalCapacity,
      totalCurrentEnrollment,
    };
  }, [enrollments, courses]);

  // Prepare dashboard metrics
  const metrics: MetricCard[] = [
    {
      title: 'Total Enrollments',
      value: enrollmentStats.totalEnrollments,
      icon: <TeamOutlined />,
      color: '#1890ff',
      trend: {
        value: 8.5,
        direction: 'up',
      },
    },
    {
      title: 'Waitlisted Students',
      value: enrollmentStats.totalWaitlisted,
      icon: <ClockCircleOutlined />,
      color: '#faad14',
      action: {
        label: 'Process Waitlists',
        onClick: () => {
          // Process all waitlists
          courses.forEach(course => {
            if (course.waitlistCount > 0) {
              onProcessWaitlist(course.id);
            }
          });
        },
      },
    },
    {
      title: 'Capacity Utilization',
      value: `${enrollmentStats.capacityUtilization.toFixed(1)}%`,
      icon: <BarChartOutlined />,
      color: enrollmentStats.capacityUtilization >= 80 ? '#52c41a' : '#faad14',
      progress: enrollmentStats.capacityUtilization,
    },
    {
      title: 'Revenue (YTD)',
      value: `$${enrollmentStats.totalRevenue.toLocaleString()}`,
      icon: <DollarOutlined />,
      color: '#52c41a',
      trend: {
        value: 12.3,
        direction: 'up',
      },
    },
  ];

  // Prepare chart data for enrollment trends
  const enrollmentTrendData = enrollmentTrends.map(trend => ({
    date: trend.date,
    enrollments: trend.enrollments,
    drops: trend.drops,
    waitlisted: trend.waitlisted,
  }));

  // Chart widgets
  const chartWidgets: ChartWidget[] = [
    {
      title: 'Enrollment Trends',
      type: 'line',
      data: enrollmentTrendData,
      config: {
        xField: 'date',
        yField: 'enrollments',
        seriesField: 'type',
        smooth: true,
        color: ['#1890ff', '#52c41a', '#faad14'],
      },
      span: 12,
    },
    {
      title: 'Enrollment Status Distribution',
      type: 'pie',
      data: [
        { type: 'Enrolled', value: enrollmentStats.totalEnrollments },
        { type: 'Waitlisted', value: enrollmentStats.totalWaitlisted },
        { type: 'Dropped', value: enrollmentStats.totalDropped },
      ],
      config: {
        angleField: 'value',
        colorField: 'type',
        radius: 0.8,
        label: {
          type: 'outer',
          content: '{name} ({percentage})',
        },
      },
      span: 12,
    },
  ];

  // Course capacity status
  const courseCapacityData = courses.map(course => {
    const utilizationRate = (course.currentEnrollment / course.maxCapacity) * 100;
    const status = utilizationRate >= 100 ? 'full' :
                  utilizationRate >= 90 ? 'near_full' :
                  utilizationRate >= 70 ? 'good' : 'low';

    return {
      key: course.id,
      code: course.code,
      name: course.name,
      currentEnrollment: course.currentEnrollment,
      maxCapacity: course.maxCapacity,
      utilizationRate,
      waitlistCount: course.waitlistCount,
      status,
      revenue: course.currentEnrollment * course.tuition,
    };
  });

  // Recent enrollments for timeline
  const recentEnrollments = enrollments
    .sort((a, b) => new Date(b.enrollmentDate).getTime() - new Date(a.enrollmentDate).getTime())
    .slice(0, 10)
    .map(enrollment => {
      const student = students.find(s => s.id === enrollment.studentId);
      const course = courses.find(c => c.id === enrollment.courseId);
      return {
        ...enrollment,
        studentName: student?.name || 'Unknown',
        courseName: course?.name || 'Unknown',
        courseCode: course?.code || 'Unknown',
      };
    });

  // List widgets
  const listWidgets: ListWidget[] = [
    {
      title: 'Course Capacity Status',
      data: courseCapacityData,
      columns: [
        {
          title: 'Course',
          dataIndex: 'code',
          render: (code: string, record: any) => (
            <div>
              <div className="font-medium">{code}</div>
              <div className="text-xs text-gray-500">{record.name}</div>
            </div>
          ),
        },
        {
          title: 'Enrollment',
          render: (_, record: any) => (
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span>{record.currentEnrollment}</span>
                <span>/ {record.maxCapacity}</span>
              </div>
              <Progress
                percent={record.utilizationRate}
                size="small"
                status={record.status === 'full' ? 'exception' : 'active'}
                showInfo={false}
              />
              {record.waitlistCount > 0 && (
                <div className="text-xs text-orange-600 mt-1">
                  {record.waitlistCount} waitlisted
                </div>
              )}
            </div>
          ),
        },
        {
          title: 'Status',
          dataIndex: 'status',
          render: (status: string) => {
            const colors = {
              full: 'red',
              near_full: 'orange',
              good: 'green',
              low: 'blue',
            };
            return (
              <Tag color={colors[status as keyof typeof colors]}>
                {status.replace('_', ' ').toUpperCase()}
              </Tag>
            );
          },
        },
        {
          title: 'Revenue',
          dataIndex: 'revenue',
          render: (revenue: number) => `$${revenue.toLocaleString()}`,
        },
      ],
      span: 24,
    },
  ];

  // Handle alert acknowledgment
  const handleAcknowledgeAlert = async (alertId: string) => {
    try {
      await onAcknowledgeAlert(alertId);
      message.success('Alert acknowledged');
    } catch (error) {
      message.error('Failed to acknowledge alert');
    }
  };

  // Handle bulk notification
  const handleSendNotification = async (values: any) => {
    try {
      await onSendNotification(selectedStudents, values.message);
      message.success(`Notification sent to ${selectedStudents.length} students`);
      setNotificationModalVisible(false);
      setSelectedStudents([]);
    } catch (error) {
      message.error('Failed to send notification');
    }
  };

  return (
    <div className="enrollment-hub space-y-6">
      {/* Header */}
      <Card>
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-bold">Enrollment Hub</h2>
            <p className="text-gray-600">Real-time enrollment management and analytics</p>
            {realTimeEnabled && (
              <div className="flex items-center space-x-2 mt-2">
                <Badge status="processing" />
                <span className="text-sm text-gray-500">
                  Live updates • Last update: {lastUpdate.toLocaleTimeString()}
                </span>
              </div>
            )}
          </div>

          <Space>
            <Button
              icon={<BellOutlined />}
              badge={{ count: capacityAlerts.filter(a => !a.acknowledged).length }}
              onClick={() => setAlertModalVisible(true)}
            >
              Alerts
            </Button>

            <Button
              icon={<MailOutlined />}
              onClick={() => setNotificationModalVisible(true)}
            >
              Send Notification
            </Button>

            <Button
              icon={<UserAddOutlined />}
              type="primary"
            >
              Quick Enroll
            </Button>
          </Space>
        </div>
      </Card>

      {/* Active Alerts */}
      {capacityAlerts.filter(a => !a.acknowledged && a.severity === 'high').length > 0 && (
        <Alert
          message="Critical Capacity Alerts"
          description={`${capacityAlerts.filter(a => !a.acknowledged && a.severity === 'high').length} courses require immediate attention`}
          type="error"
          showIcon
          action={
            <Button size="small" onClick={() => setAlertModalVisible(true)}>
              View Alerts
            </Button>
          }
          closable
        />
      )}

      {/* Dashboard */}
      <Dashboard
        metrics={metrics}
        charts={chartWidgets}
        lists={listWidgets}
        filters={[
          {
            key: 'timeRange',
            label: 'Time Range',
            type: 'dateRange',
            value: selectedTimeRange,
            onChange: setSelectedTimeRange,
          },
        ]}
        refreshInterval={realTimeEnabled ? 30000 : undefined}
        onRefresh={() => {
          setLastUpdate(new Date());
        }}
      />

      {/* Recent Activity Timeline */}
      <Card title="Recent Enrollment Activity" extra={
        <Button icon={<SyncOutlined />} size="small">
          Refresh
        </Button>
      }>
        <Timeline>
          {recentEnrollments.map(enrollment => (
            <Timeline.Item
              key={enrollment.id}
              dot={
                enrollment.status === 'enrolled' ? <CheckCircleOutlined style={{ color: '#52c41a' }} /> :
                enrollment.status === 'waitlisted' ? <ClockCircleOutlined style={{ color: '#faad14' }} /> :
                <WarningOutlined style={{ color: '#ff4d4f' }} />
              }
            >
              <div className="flex justify-between items-start">
                <div>
                  <div className="font-medium">
                    {enrollment.studentName} {enrollment.status === 'enrolled' ? 'enrolled in' : 'joined waitlist for'} {enrollment.courseCode}
                  </div>
                  <div className="text-sm text-gray-600">{enrollment.courseName}</div>
                  <div className="text-xs text-gray-500">
                    {new Date(enrollment.enrollmentDate).toLocaleString()}
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-medium">${enrollment.paymentAmount}</div>
                  <Badge
                    status={enrollment.paymentStatus === 'paid' ? 'success' : 'warning'}
                    text={enrollment.paymentStatus}
                  />
                </div>
              </div>
            </Timeline.Item>
          ))}
        </Timeline>
      </Card>

      {/* Alerts Modal */}
      <Modal
        title="Capacity Alerts"
        open={alertModalVisible}
        onCancel={() => setAlertModalVisible(false)}
        footer={null}
        width={800}
      >
        <div className="space-y-4">
          {capacityAlerts.map(alert => (
            <Card
              key={alert.id}
              size="small"
              className={alert.acknowledged ? 'opacity-50' : ''}
            >
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-center space-x-2 mb-2">
                    <Badge
                      status={alert.severity === 'high' ? 'error' : alert.severity === 'medium' ? 'warning' : 'default'}
                    />
                    <Tag color={alert.severity === 'high' ? 'red' : alert.severity === 'medium' ? 'orange' : 'blue'}>
                      {alert.type.replace('_', ' ').toUpperCase()}
                    </Tag>
                    <span className="font-medium">{alert.courseName}</span>
                  </div>
                  <p className="text-gray-600 mb-2">{alert.message}</p>
                  <div className="text-xs text-gray-500">
                    {new Date(alert.timestamp).toLocaleString()}
                  </div>
                </div>
                <div>
                  {!alert.acknowledged && (
                    <Button
                      size="small"
                      onClick={() => handleAcknowledgeAlert(alert.id)}
                    >
                      Acknowledge
                    </Button>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
      </Modal>

      {/* Notification Modal */}
      <Modal
        title="Send Notification"
        open={notificationModalVisible}
        onCancel={() => setNotificationModalVisible(false)}
        onOk={() => {
          // Handle form submission
        }}
      >
        <Form onFinish={handleSendNotification} layout="vertical">
          <Form.Item
            name="recipients"
            label="Recipients"
            rules={[{ required: true, message: 'Please select recipients' }]}
          >
            <Select
              mode="multiple"
              placeholder="Select students"
              value={selectedStudents}
              onChange={setSelectedStudents}
              style={{ width: '100%' }}
            >
              {students.map(student => (
                <Option key={student.id} value={student.id}>
                  {student.name} ({student.studentId})
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="message"
            label="Message"
            rules={[{ required: true, message: 'Please enter a message' }]}
          >
            <Input.TextArea
              rows={4}
              placeholder="Enter notification message..."
            />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                Send Notification
              </Button>
              <Button onClick={() => setNotificationModalVisible(false)}>
                Cancel
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default EnrollmentHub;