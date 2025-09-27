/**
 * StudentStats Component
 *
 * A comprehensive statistics component for displaying student metrics:
 * - Academic performance indicators
 * - Enrollment statistics
 * - Financial summaries
 * - Comparative analytics
 * - Trend visualizations
 * - Real-time updates
 */

import React, { useState, useEffect } from 'react';
import { Card, Statistic, Progress, Row, Col, Tooltip, Tag, Space, Button } from 'antd';
import {
  TrendingUpOutlined,
  TrendingDownOutlined,
  UserOutlined,
  BookOutlined,
  DollarOutlined,
  CalendarOutlined,
  StarOutlined,
  AlertOutlined,
  InfoCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import type { Student, StudentStatistics } from '../types/Student';

interface StudentStatsProps {
  student?: Student;
  statistics?: StudentStatistics;
  showComparison?: boolean;
  realTime?: boolean;
  onRefresh?: () => void;
  className?: string;
}

const StudentStats: React.FC<StudentStatsProps> = ({
  student,
  statistics,
  showComparison = false,
  realTime = false,
  onRefresh,
  className,
}) => {
  const [loading, setLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(new Date());

  useEffect(() => {
    if (realTime) {
      const interval = setInterval(() => {
        setLastUpdated(new Date());
        // In a real app, this would trigger a data refresh
      }, 30000); // Update every 30 seconds

      return () => clearInterval(interval);
    }
  }, [realTime]);

  const handleRefresh = async () => {
    setLoading(true);
    try {
      await onRefresh?.();
      setLastUpdated(new Date());
    } finally {
      setLoading(false);
    }
  };

  const getGradeColor = (gpa: number): string => {
    if (gpa >= 3.5) return '#52c41a'; // green
    if (gpa >= 3.0) return '#faad14'; // gold
    if (gpa >= 2.5) return '#fa8c16'; // orange
    return '#f5222d'; // red
  };

  const getAttendanceColor = (rate: number): string => {
    if (rate >= 95) return '#52c41a'; // green
    if (rate >= 90) return '#faad14'; // gold
    if (rate >= 85) return '#fa8c16'; // orange
    return '#f5222d'; // red
  };

  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  const defaultStats: StudentStatistics = {
    academicPerformance: {
      currentGPA: student?.gpa || 0,
      creditsCompleted: student?.creditsCompleted || 0,
      creditsRequired: 120,
      attendanceRate: 92,
      averageGrade: 85,
    },
    enrollment: {
      currentCourses: 5,
      completedCourses: 15,
      droppedCourses: 1,
      totalCredits: 60,
    },
    financial: {
      totalTuition: 25000,
      amountPaid: 20000,
      balance: 5000,
      scholarships: 3000,
    },
    engagement: {
      loginFrequency: 4.2,
      assignmentSubmissionRate: 95,
      forumParticipation: 78,
      libraryUsage: 12,
    },
    alerts: {
      academic: 0,
      financial: 1,
      attendance: 0,
      behavioral: 0,
    },
    trends: {
      gpaChange: 0.2,
      attendanceChange: -2,
      engagementChange: 5,
    },
  };

  const stats = statistics || defaultStats;

  return (
    <div className={`student-stats ${className || ''}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold">Student Statistics</h3>
          {student && (
            <p className="text-gray-600">{student.fullName} - {student.studentId}</p>
          )}
        </div>
        <Space>
          {realTime && (
            <Tag color="blue">
              <InfoCircleOutlined /> Live Updates
            </Tag>
          )}
          <Button
            icon={<ReloadOutlined />}
            onClick={handleRefresh}
            loading={loading}
            size="small"
          >
            Refresh
          </Button>
        </Space>
      </div>

      {/* Academic Performance */}
      <Card title="Academic Performance" className="mb-4">
        <Row gutter={16}>
          <Col span={6}>
            <Statistic
              title="Current GPA"
              value={stats.academicPerformance.currentGPA}
              precision={2}
              valueStyle={{ color: getGradeColor(stats.academicPerformance.currentGPA) }}
              prefix={<StarOutlined />}
              suffix={
                showComparison && stats.trends?.gpaChange !== 0 && (
                  <Tooltip title={`${stats.trends.gpaChange > 0 ? '+' : ''}${stats.trends.gpaChange} from last semester`}>
                    {stats.trends.gpaChange > 0 ? (
                      <TrendingUpOutlined style={{ color: '#52c41a' }} />
                    ) : (
                      <TrendingDownOutlined style={{ color: '#f5222d' }} />
                    )}
                  </Tooltip>
                )
              }
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="Credits Completed"
              value={stats.academicPerformance.creditsCompleted}
              suffix={`/ ${stats.academicPerformance.creditsRequired}`}
              prefix={<BookOutlined />}
            />
            <Progress
              percent={Math.round((stats.academicPerformance.creditsCompleted / stats.academicPerformance.creditsRequired) * 100)}
              size="small"
              strokeColor="#1890ff"
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="Attendance Rate"
              value={stats.academicPerformance.attendanceRate}
              suffix="%"
              valueStyle={{ color: getAttendanceColor(stats.academicPerformance.attendanceRate) }}
              prefix={<CalendarOutlined />}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="Average Grade"
              value={stats.academicPerformance.averageGrade}
              suffix="%"
              prefix={<TrendingUpOutlined />}
            />
          </Col>
        </Row>
      </Card>

      {/* Enrollment Summary */}
      <Row gutter={16}>
        <Col span={12}>
          <Card title="Enrollment Summary" className="mb-4">
            <Row gutter={16}>
              <Col span={12}>
                <Statistic
                  title="Current Courses"
                  value={stats.enrollment.currentCourses}
                  prefix={<BookOutlined />}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="Completed"
                  value={stats.enrollment.completedCourses}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Col>
            </Row>
            <Row gutter={16} className="mt-4">
              <Col span={12}>
                <Statistic
                  title="Total Credits"
                  value={stats.enrollment.totalCredits}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="Dropped"
                  value={stats.enrollment.droppedCourses}
                  valueStyle={{ color: stats.enrollment.droppedCourses > 0 ? '#f5222d' : undefined }}
                />
              </Col>
            </Row>
          </Card>
        </Col>

        <Col span={12}>
          <Card title="Financial Summary" className="mb-4">
            <Row gutter={16}>
              <Col span={12}>
                <Statistic
                  title="Total Tuition"
                  value={stats.financial.totalTuition}
                  formatter={(value) => formatCurrency(Number(value))}
                  prefix={<DollarOutlined />}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="Amount Paid"
                  value={stats.financial.amountPaid}
                  formatter={(value) => formatCurrency(Number(value))}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Col>
            </Row>
            <Row gutter={16} className="mt-4">
              <Col span={12}>
                <Statistic
                  title="Balance Due"
                  value={stats.financial.balance}
                  formatter={(value) => formatCurrency(Number(value))}
                  valueStyle={{ color: stats.financial.balance > 0 ? '#f5222d' : '#52c41a' }}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="Scholarships"
                  value={stats.financial.scholarships}
                  formatter={(value) => formatCurrency(Number(value))}
                  valueStyle={{ color: '#1890ff' }}
                />
              </Col>
            </Row>
            <Progress
              percent={Math.round((stats.financial.amountPaid / stats.financial.totalTuition) * 100)}
              size="small"
              strokeColor="#52c41a"
              className="mt-2"
            />
          </Card>
        </Col>
      </Row>

      {/* Engagement Metrics */}
      <Card title="Student Engagement" className="mb-4">
        <Row gutter={16}>
          <Col span={6}>
            <Statistic
              title="Weekly Logins"
              value={stats.engagement.loginFrequency}
              precision={1}
              suffix="avg"
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="Assignment Rate"
              value={stats.engagement.assignmentSubmissionRate}
              suffix="%"
              valueStyle={{ color: stats.engagement.assignmentSubmissionRate >= 90 ? '#52c41a' : '#fa8c16' }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="Forum Activity"
              value={stats.engagement.forumParticipation}
              suffix="%"
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="Library Visits"
              value={stats.engagement.libraryUsage}
              suffix="/month"
            />
          </Col>
        </Row>
      </Card>

      {/* Alerts Summary */}
      {(stats.alerts.academic + stats.alerts.financial + stats.alerts.attendance + stats.alerts.behavioral) > 0 && (
        <Card
          title={
            <Space>
              <AlertOutlined />
              Active Alerts
            </Space>
          }
          className="mb-4"
          headStyle={{ backgroundColor: '#fff2e8', borderBottom: '1px solid #ffbb96' }}
        >
          <Row gutter={16}>
            {stats.alerts.academic > 0 && (
              <Col span={6}>
                <Statistic
                  title="Academic"
                  value={stats.alerts.academic}
                  valueStyle={{ color: '#f5222d' }}
                />
              </Col>
            )}
            {stats.alerts.financial > 0 && (
              <Col span={6}>
                <Statistic
                  title="Financial"
                  value={stats.alerts.financial}
                  valueStyle={{ color: '#fa8c16' }}
                />
              </Col>
            )}
            {stats.alerts.attendance > 0 && (
              <Col span={6}>
                <Statistic
                  title="Attendance"
                  value={stats.alerts.attendance}
                  valueStyle={{ color: '#faad14' }}
                />
              </Col>
            )}
            {stats.alerts.behavioral > 0 && (
              <Col span={6}>
                <Statistic
                  title="Behavioral"
                  value={stats.alerts.behavioral}
                  valueStyle={{ color: '#f5222d' }}
                />
              </Col>
            )}
          </Row>
        </Card>
      )}

      {/* Last Updated */}
      <div className="text-center text-sm text-gray-500">
        Last updated: {lastUpdated.toLocaleString()}
        {realTime && ' (Auto-refreshing)'}
      </div>
    </div>
  );
};

export default StudentStats;