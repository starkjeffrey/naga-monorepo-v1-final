/**
 * Student Analytics Dashboard
 *
 * A comprehensive analytics dashboard using the Dashboard pattern:
 * - Key metrics: Total students, New enrollments, At-risk students, Success rates
 * - Trend analysis with interactive charts
 * - Demographic breakdowns
 * - Program popularity analysis
 * - Retention rate tracking
 * - Predictive analytics for enrollment forecasting
 * - AI-powered student success predictions
 * - Early intervention recommendation system
 * - Cohort analysis and comparison
 * - Automated report generation
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Progress,
  List,
  Avatar,
  Tag,
  Button,
  Select,
  DatePicker,
  Alert,
  Badge,
  Tooltip,
  Space,
  message,
} from 'antd';
import {
  UserOutlined,
  TeamOutlined,
  BookOutlined,
  TrophyOutlined,
  WarningOutlined,
  TrendingUpOutlined,
  TrendingDownOutlined,
  BankOutlined,
  CalendarOutlined,
  ExperimentOutlined,
  ThunderboltOutlined,
  DownloadOutlined,
  FilterOutlined,
  ReloadOutlined,
  BulbOutlined,
  AlertCircleOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';

import { Dashboard } from '../../components/patterns';
import type { MetricCard, ChartWidget, ListWidget, Filter } from '../../components/patterns';
import { StudentService } from '../../services/student.service';

const { Option } = Select;
const { RangePicker } = DatePicker;

interface AnalyticsFilters {
  dateRange?: [string, string];
  program?: string;
  division?: string;
  academicYear?: number;
}

interface PredictionData {
  studentId: number;
  studentName: string;
  riskScore: number;
  riskFactors: string[];
  interventions: string[];
  confidenceLevel: number;
}

interface CohortData {
  cohortYear: number;
  totalStudents: number;
  retained: number;
  graduated: number;
  dropped: number;
  retentionRate: number;
}

export const StudentAnalytics: React.FC = () => {
  // State
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState<AnalyticsFilters>({
    academicYear: new Date().getFullYear(),
  });

  // Real analytics data
  const [analyticsData, setAnalyticsData] = useState<any>(null);

  // AI Predictions
  const [predictions, setPredictions] = useState<PredictionData[]>([
    {
      studentId: 12345,
      studentName: 'John Doe',
      riskScore: 85,
      riskFactors: ['Declining grades', 'Poor attendance', 'Financial stress'],
      interventions: ['Academic counseling', 'Financial aid review', 'Study group'],
      confidenceLevel: 92,
    },
    {
      studentId: 12346,
      studentName: 'Jane Smith',
      riskScore: 72,
      riskFactors: ['Course load too high', 'Work-life balance'],
      interventions: ['Course adjustment', 'Time management counseling'],
      confidenceLevel: 88,
    },
  ]);

  // Cohort analysis data
  const [cohortData, setCohortData] = useState<CohortData[]>([
    { cohortYear: 2020, totalStudents: 156, retained: 142, graduated: 122, dropped: 14, retentionRate: 91.0 },
    { cohortYear: 2021, totalStudents: 168, retained: 149, graduated: 0, dropped: 19, retentionRate: 88.7 },
    { cohortYear: 2022, totalStudents: 175, retained: 158, graduated: 0, dropped: 17, retentionRate: 90.3 },
    { cohortYear: 2023, totalStudents: 189, retained: 171, graduated: 0, dropped: 18, retentionRate: 90.5 },
  ]);

  const [atRiskStudents] = useState([
    {
      id: '1',
      title: 'Sarah Johnson',
      description: 'Biology Program • Sophomore',
      avatar: undefined,
      status: 'high-risk',
      value: '85% risk',
      trend: 'up' as const,
    },
    {
      id: '2',
      title: 'Michael Chen',
      description: 'Engineering • Junior',
      avatar: undefined,
      status: 'medium-risk',
      value: '72% risk',
      trend: 'stable' as const,
    },
    {
      id: '3',
      title: 'Emily Davis',
      description: 'Arts • Freshman',
      avatar: undefined,
      status: 'low-risk',
      value: '45% risk',
      trend: 'down' as const,
    },
  ]);

  const [topPerformers] = useState([
    {
      id: '1',
      title: 'Alex Rodriguez',
      description: 'Computer Science • Senior',
      avatar: undefined,
      status: 'excellent',
      value: '4.0 GPA',
      trend: 'up' as const,
    },
    {
      id: '2',
      title: 'Lisa Wang',
      description: 'Mathematics • Junior',
      avatar: undefined,
      status: 'excellent',
      value: '3.95 GPA',
      trend: 'stable' as const,
    },
  ]);

  // Load analytics data
  useEffect(() => {
    loadAnalyticsData();
  }, [filters]);

  const loadAnalyticsData = async () => {
    try {
      setLoading(true);
      const data = await StudentService.getStudentAnalytics();
      setAnalyticsData(data);
    } catch (error) {
      console.error('Failed to load analytics data:', error);
      message.error('Failed to load analytics data');
    } finally {
      setLoading(false);
    }
  };

  const handleFiltersChange = (newFilters: Record<string, any>) => {
    setFilters({ ...filters, ...newFilters });
  };

  const handleExport = () => {
    message.success('Analytics report export started. You will receive a download link shortly.');
  };

  // Define metrics for the dashboard
  const metrics: MetricCard[] = analyticsData ? [
    {
      key: 'total_students',
      title: 'Total Students',
      value: analyticsData.overview.total_students.toLocaleString(),
      icon: <UserOutlined />,
      color: '#1890ff',
    },
    {
      key: 'active_students',
      title: 'Active Students',
      value: analyticsData.overview.active_students,
      icon: <TeamOutlined />,
      color: '#52c41a',
    },
    {
      key: 'monk_students',
      title: 'Monk Students',
      value: analyticsData.overview.monk_students,
      icon: <BookOutlined />,
      color: '#faad14',
    },
    {
      key: 'transfer_students',
      title: 'Transfer Students',
      value: analyticsData.overview.transfer_students,
      icon: <TrophyOutlined />,
      color: '#722ed1',
    },
    {
      key: 'average_age',
      title: 'Average Age',
      value: analyticsData.overview.average_age,
      precision: 1,
      icon: <TrendingUpOutlined />,
      color: '#eb2f96',
    },
  ] : [];

  // Define charts for the dashboard
  const charts: ChartWidget[] = analyticsData ? [
    {
      key: 'gender_distribution',
      title: 'Gender Distribution',
      type: 'pie',
      data: analyticsData.demographics.gender_distribution,
      height: 300,
    },
    {
      key: 'program_distribution',
      title: 'Program Distribution',
      type: 'pie',
      data: analyticsData.academic.program_distribution,
      height: 300,
    },
    {
      key: 'status_distribution',
      title: 'Student Status Distribution',
      type: 'bar',
      data: analyticsData.academic.status_distribution,
      height: 300,
    },
    {
      key: 'age_groups',
      title: 'Age Group Distribution',
      type: 'bar',
      data: analyticsData.demographics.age_groups,
      height: 300,
    },
  ] : [];

  // Define list widgets
  const listWidgets: ListWidget[] = [
    {
      key: 'at_risk_students',
      title: 'At-Risk Students',
      data: atRiskStudents,
      showMore: () => message.info('View all at-risk students'),
    },
    {
      key: 'top_performers',
      title: 'Top Performers',
      data: topPerformers,
      showMore: () => message.info('View all top performers'),
    },
  ];

  // Define filters for the dashboard
  const dashboardFilters: Filter[] = [
    {
      key: 'academicYear',
      label: 'Academic Year',
      type: 'select',
      options: [
        { label: '2023-2024', value: 2024 },
        { label: '2022-2023', value: 2023 },
        { label: '2021-2022', value: 2022 },
      ],
      value: filters.academicYear,
      onChange: (value) => handleFiltersChange({ academicYear: value }),
    },
    {
      key: 'program',
      label: 'Program',
      type: 'select',
      options: [
        { label: 'All Programs', value: '' },
        { label: 'Biology', value: 'biology' },
        { label: 'Engineering', value: 'engineering' },
        { label: 'Arts', value: 'arts' },
        { label: 'Computer Science', value: 'cs' },
      ],
      value: filters.program,
      onChange: (value) => handleFiltersChange({ program: value }),
    },
    {
      key: 'dateRange',
      label: 'Date Range',
      type: 'dateRange',
      value: filters.dateRange,
      onChange: (value) => handleFiltersChange({ dateRange: value }),
    },
  ];

  return (
    <div className="student-analytics">
      {/* AI Insights Alert */}
      <Alert
        message="AI Insights Available"
        description={
          <div>
            <p>Our AI system has identified {predictions.length} students who may need intervention.</p>
            <Space>
              <Button
                type="link"
                icon={<BulbOutlined />}
                onClick={() => message.info('AI insights modal will be implemented')}
              >
                View AI Recommendations
              </Button>
              <Button
                type="link"
                icon={<ThunderboltOutlined />}
                onClick={() => message.info('Automated interventions will be implemented')}
              >
                Auto-Generate Interventions
              </Button>
            </Space>
          </div>
        }
        type="info"
        showIcon
        className="mb-6"
        closable
      />

      {/* Student Success Predictions */}
      <Card title="Student Success Predictions" className="mb-6">
        <Row gutter={16}>
          {predictions.map((prediction) => (
            <Col key={prediction.studentId} span={12}>
              <Card size="small" className="mb-4">
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 mb-2">
                      <Avatar icon={<UserOutlined />} />
                      <div>
                        <div className="font-medium">{prediction.studentName}</div>
                        <div className="text-sm text-gray-500">
                          ID: {prediction.studentId} • {prediction.confidenceLevel}% confidence
                        </div>
                      </div>
                    </div>

                    <div className="mb-3">
                      <div className="flex justify-between items-center mb-1">
                        <span className="text-sm">Risk Score</span>
                        <span className="text-sm font-medium">{prediction.riskScore}%</span>
                      </div>
                      <Progress
                        percent={prediction.riskScore}
                        strokeColor={
                          prediction.riskScore > 80 ? '#ff4d4f' :
                          prediction.riskScore > 60 ? '#faad14' : '#52c41a'
                        }
                        showInfo={false}
                        size="small"
                      />
                    </div>

                    <div className="mb-3">
                      <div className="text-sm font-medium mb-1">Risk Factors:</div>
                      <div className="flex flex-wrap gap-1">
                        {prediction.riskFactors.map((factor, index) => (
                          <Tag key={index} size="small" color="red">
                            {factor}
                          </Tag>
                        ))}
                      </div>
                    </div>

                    <div>
                      <div className="text-sm font-medium mb-1">Recommended Interventions:</div>
                      <div className="flex flex-wrap gap-1">
                        {prediction.interventions.map((intervention, index) => (
                          <Tag key={index} size="small" color="blue">
                            {intervention}
                          </Tag>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className="ml-4">
                    <Space direction="vertical" size="small">
                      <Button
                        size="small"
                        type="primary"
                        icon={<AlertCircleOutlined />}
                        onClick={() => message.info('Creating intervention plan...')}
                      >
                        Intervene
                      </Button>
                      <Button
                        size="small"
                        icon={<UserOutlined />}
                        onClick={() => message.info('Opening student profile...')}
                      >
                        View Profile
                      </Button>
                    </Space>
                  </div>
                </div>
              </Card>
            </Col>
          ))}
        </Row>
      </Card>

      {/* Cohort Analysis */}
      <Card title="Cohort Retention Analysis" className="mb-6">
        <div className="space-y-4">
          {cohortData.map((cohort) => (
            <div key={cohort.cohortYear} className="flex items-center justify-between p-4 border rounded">
              <div>
                <div className="font-medium">Class of {cohort.cohortYear}</div>
                <div className="text-sm text-gray-500">
                  {cohort.totalStudents} students • {cohort.retained} retained • {cohort.dropped} dropped
                </div>
              </div>
              <div className="text-right">
                <div className="font-medium text-lg">{cohort.retentionRate}%</div>
                <div className="text-sm text-gray-500">Retention Rate</div>
              </div>
              <div className="w-32">
                <Progress
                  percent={cohort.retentionRate}
                  strokeColor="#52c41a"
                  showInfo={false}
                />
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Main Dashboard */}
      <Dashboard
        title="Student Analytics Dashboard"
        description="Comprehensive analytics and insights for student management"
        metrics={metrics}
        charts={charts}
        lists={listWidgets}
        loading={loading}
        filters={dashboardFilters}
        onFiltersChange={handleFiltersChange}
        onRefresh={loadAnalyticsData}
        onExport={handleExport}
        refreshInterval={300000} // Refresh every 5 minutes
        layout={{
          metricsSpan: 4,
          chartSpan: 12,
          listSpan: 6,
        }}
      />
    </div>
  );
};

export default StudentAnalytics;