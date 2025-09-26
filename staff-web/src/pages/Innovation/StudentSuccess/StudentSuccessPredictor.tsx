/**
 * StudentSuccessPredictor Component
 *
 * AI-powered student success prediction system with:
 * - Machine learning models predicting student outcomes
 * - Risk factor analysis with confidence scoring
 * - Early intervention recommendation engine
 * - Academic trajectory visualization with multiple scenarios
 * - Predictive modeling for graduation likelihood
 * - Integration with academic and financial data
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Card,
  Row,
  Col,
  Select,
  Button,
  Input,
  Progress,
  Alert,
  Tabs,
  Table,
  Tag,
  Space,
  Tooltip,
  Spin,
  Modal,
  Form,
  InputNumber,
  Switch,
  Divider,
  Statistic,
  Badge,
  Timeline,
  List,
  Avatar,
} from 'antd';
import {
  UserOutlined,
  TrophyOutlined,
  WarningOutlined,
  RocketOutlined,
  BrainOutlined,
  BarChartOutlined,
  ReloadOutlined,
  SettingOutlined,
  BulbOutlined,
  TrendingUpOutlined,
  AlertOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  LineChartOutlined,
} from '@ant-design/icons';
import { Line, Bar, Scatter } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip as ChartTooltip,
  Legend,
} from 'chart.js';
import { motion, AnimatePresence } from 'framer-motion';
import { PredictionEngine, ModelManager } from '../../../utils/ai/modelUtils';
import {
  StudentSuccessPrediction,
  StudentRiskFactor,
  Intervention,
  PredictionResult,
} from '../../../types/innovation';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  ChartTooltip,
  Legend
);

const { Option } = Select;
const { TabPane } = Tabs;
const { Search } = Input;

interface StudentData {
  id: string;
  name: string;
  email: string;
  studentId: string;
  currentGPA: number;
  attendanceRate: number;
  creditsCompleted: number;
  totalCreditsRequired: number;
  financialAidStatus: boolean;
  workHoursPerWeek: number;
  distanceFromCampus: number;
  parentEducationLevel: number;
  firstGeneration: boolean;
  extracurricularCount: number;
  tutoringSessions: number;
  advisingMeetings: number;
  semester: string;
  major: string;
  yearLevel: string;
  lastActivity: Date;
}

interface PredictionScenario {
  name: string;
  adjustments: Partial<StudentData>;
  prediction?: StudentSuccessPrediction;
}

const StudentSuccessPredictor: React.FC = () => {
  // State management
  const [selectedStudent, setSelectedStudent] = useState<StudentData | null>(null);
  const [students, setStudents] = useState<StudentData[]>([]);
  const [predictions, setPredictions] = useState<Map<string, StudentSuccessPrediction>>(new Map());
  const [loading, setLoading] = useState(false);
  const [modelStatus, setModelStatus] = useState<'loading' | 'ready' | 'error'>('loading');
  const [activeTab, setActiveTab] = useState('prediction');
  const [scenarios, setScenarios] = useState<PredictionScenario[]>([]);
  const [showScenarioModal, setShowScenarioModal] = useState(false);
  const [selectedFilters, setSelectedFilters] = useState({
    riskLevel: 'all',
    semester: 'all',
    major: 'all',
    yearLevel: 'all',
  });

  // Refs
  const chartRef = useRef<any>(null);
  const [form] = Form.useForm();

  // Load model and initial data
  useEffect(() => {
    initializeModel();
    loadStudents();
  }, []);

  const initializeModel = async () => {
    try {
      setModelStatus('loading');
      // In a real implementation, this would load from a trained model file
      // For demo purposes, we'll simulate model loading
      await new Promise(resolve => setTimeout(resolve, 2000));
      setModelStatus('ready');
    } catch (error) {
      console.error('Model loading failed:', error);
      setModelStatus('error');
    }
  };

  const loadStudents = async () => {
    try {
      setLoading(true);
      // Simulate API call to load student data
      const mockStudents: StudentData[] = [
        {
          id: '1',
          name: 'Sarah Johnson',
          email: 'sarah.johnson@university.edu',
          studentId: 'STU001',
          currentGPA: 3.2,
          attendanceRate: 0.85,
          creditsCompleted: 45,
          totalCreditsRequired: 120,
          financialAidStatus: true,
          workHoursPerWeek: 15,
          distanceFromCampus: 5,
          parentEducationLevel: 3,
          firstGeneration: false,
          extracurricularCount: 2,
          tutoringSessions: 3,
          advisingMeetings: 2,
          semester: 'Fall 2024',
          major: 'Computer Science',
          yearLevel: 'Sophomore',
          lastActivity: new Date('2024-09-26'),
        },
        {
          id: '2',
          name: 'Michael Chen',
          email: 'michael.chen@university.edu',
          studentId: 'STU002',
          currentGPA: 2.1,
          attendanceRate: 0.65,
          creditsCompleted: 28,
          totalCreditsRequired: 120,
          financialAidStatus: false,
          workHoursPerWeek: 35,
          distanceFromCampus: 25,
          parentEducationLevel: 1,
          firstGeneration: true,
          extracurricularCount: 0,
          tutoringSessions: 0,
          advisingMeetings: 1,
          semester: 'Fall 2024',
          major: 'Business',
          yearLevel: 'Sophomore',
          lastActivity: new Date('2024-09-25'),
        },
        {
          id: '3',
          name: 'Emily Rodriguez',
          email: 'emily.rodriguez@university.edu',
          studentId: 'STU003',
          currentGPA: 3.8,
          attendanceRate: 0.95,
          creditsCompleted: 90,
          totalCreditsRequired: 120,
          financialAidStatus: true,
          workHoursPerWeek: 10,
          distanceFromCampus: 2,
          parentEducationLevel: 5,
          firstGeneration: false,
          extracurricularCount: 4,
          tutoringSessions: 1,
          advisingMeetings: 4,
          semester: 'Fall 2024',
          major: 'Engineering',
          yearLevel: 'Senior',
          lastActivity: new Date('2024-09-26'),
        },
      ];

      setStudents(mockStudents);

      // Generate predictions for all students
      const newPredictions = new Map<string, StudentSuccessPrediction>();
      for (const student of mockStudents) {
        const prediction = await generatePrediction(student);
        newPredictions.set(student.id, prediction);
      }
      setPredictions(newPredictions);

    } catch (error) {
      console.error('Failed to load students:', error);
    } finally {
      setLoading(false);
    }
  };

  const generatePrediction = async (student: StudentData): Promise<StudentSuccessPrediction> => {
    try {
      if (modelStatus !== 'ready') {
        throw new Error('Model not ready');
      }

      return await PredictionEngine.predictStudentSuccess(student);
    } catch (error) {
      console.error('Prediction failed:', error);
      // Return mock prediction for demo
      return {
        studentId: student.id,
        riskLevel: student.currentGPA < 2.5 ? 'high' : student.currentGPA < 3.0 ? 'medium' : 'low',
        graduationProbability: Math.max(0.1, Math.min(0.95, student.currentGPA / 4.0 + Math.random() * 0.2 - 0.1)),
        nextTermGPA: Math.max(0, Math.min(4.0, student.currentGPA + (Math.random() - 0.5) * 0.5)),
        riskFactors: generateMockRiskFactors(student),
        interventions: generateMockInterventions(student),
        lastUpdated: new Date(),
      };
    }
  };

  const generateMockRiskFactors = (student: StudentData): StudentRiskFactor[] => {
    const factors: StudentRiskFactor[] = [];

    if (student.currentGPA < 2.5) {
      factors.push({
        category: 'academic',
        factor: 'Low GPA',
        impact: -0.8,
        confidence: 0.9,
        description: 'Current GPA is significantly below graduation requirements',
        recommendation: 'Immediate academic intervention and tutoring support required',
      });
    }

    if (student.attendanceRate < 0.8) {
      factors.push({
        category: 'attendance',
        factor: 'Poor Attendance',
        impact: -0.6,
        confidence: 0.85,
        description: 'Attendance rate indicates potential engagement issues',
        recommendation: 'Attendance monitoring and intervention program',
      });
    }

    if (student.workHoursPerWeek > 30 && !student.financialAidStatus) {
      factors.push({
        category: 'financial',
        factor: 'Work-Study Balance',
        impact: -0.4,
        confidence: 0.7,
        description: 'Heavy work schedule may impact academic performance',
        recommendation: 'Financial aid counseling and time management support',
      });
    }

    if (student.firstGeneration && student.advisingMeetings < 2) {
      factors.push({
        category: 'social',
        factor: 'First-Generation Support',
        impact: -0.3,
        confidence: 0.75,
        description: 'First-generation students benefit from additional guidance',
        recommendation: 'Enhanced advising and mentorship programs',
      });
    }

    return factors;
  };

  const generateMockInterventions = (student: StudentData): Intervention[] => {
    const interventions: Intervention[] = [];

    if (student.currentGPA < 2.5) {
      interventions.push({
        id: `int_${student.id}_1`,
        type: 'academic_support',
        title: 'Intensive Academic Support',
        description: 'Weekly tutoring sessions and study skills workshops',
        priority: 'urgent',
        estimatedImpact: 0.7,
        timeToImplement: '1 week',
        cost: 500,
        status: 'recommended',
        successRate: 0.75,
      });
    }

    if (!student.financialAidStatus && student.workHoursPerWeek > 25) {
      interventions.push({
        id: `int_${student.id}_2`,
        type: 'financial_aid',
        title: 'Financial Aid Assessment',
        description: 'Comprehensive financial aid review and application assistance',
        priority: 'high',
        estimatedImpact: 0.5,
        timeToImplement: '2 weeks',
        cost: 0,
        status: 'recommended',
        successRate: 0.6,
      });
    }

    return interventions;
  };

  const handleStudentSelect = useCallback(async (studentId: string) => {
    const student = students.find(s => s.id === studentId);
    if (student) {
      setSelectedStudent(student);
      if (!predictions.has(studentId)) {
        setLoading(true);
        const prediction = await generatePrediction(student);
        setPredictions(prev => new Map(prev).set(studentId, prediction));
        setLoading(false);
      }
    }
  }, [students, predictions]);

  const handleRefreshPrediction = useCallback(async () => {
    if (!selectedStudent) return;

    setLoading(true);
    const prediction = await generatePrediction(selectedStudent);
    setPredictions(prev => new Map(prev).set(selectedStudent.id, prediction));
    setLoading(false);
  }, [selectedStudent]);

  const createScenario = useCallback((values: any) => {
    if (!selectedStudent) return;

    const scenario: PredictionScenario = {
      name: values.scenarioName,
      adjustments: {
        currentGPA: values.gpa,
        attendanceRate: values.attendance / 100,
        tutoringSessions: values.tutoring,
        advisingMeetings: values.advising,
        workHoursPerWeek: values.workHours,
      },
    };

    setScenarios(prev => [...prev, scenario]);
    form.resetFields();
    setShowScenarioModal(false);

    // Generate prediction for scenario
    generateScenarioPrediction(scenario);
  }, [selectedStudent, form]);

  const generateScenarioPrediction = async (scenario: PredictionScenario) => {
    if (!selectedStudent) return;

    const adjustedStudent = { ...selectedStudent, ...scenario.adjustments };
    const prediction = await generatePrediction(adjustedStudent);

    setScenarios(prev =>
      prev.map(s => s.name === scenario.name ? { ...s, prediction } : s)
    );
  };

  const getRiskLevelColor = (riskLevel: string) => {
    switch (riskLevel) {
      case 'low': return 'green';
      case 'medium': return 'orange';
      case 'high': return 'red';
      case 'critical': return 'purple';
      default: return 'gray';
    }
  };

  const getRiskLevelIcon = (riskLevel: string) => {
    switch (riskLevel) {
      case 'low': return <CheckCircleOutlined />;
      case 'medium': return <ClockCircleOutlined />;
      case 'high': return <WarningOutlined />;
      case 'critical': return <AlertOutlined />;
      default: return <UserOutlined />;
    }
  };

  const filteredStudents = students.filter(student => {
    const prediction = predictions.get(student.id);
    return (
      (selectedFilters.riskLevel === 'all' || prediction?.riskLevel === selectedFilters.riskLevel) &&
      (selectedFilters.semester === 'all' || student.semester === selectedFilters.semester) &&
      (selectedFilters.major === 'all' || student.major === selectedFilters.major) &&
      (selectedFilters.yearLevel === 'all' || student.yearLevel === selectedFilters.yearLevel)
    );
  });

  const currentPrediction = selectedStudent ? predictions.get(selectedStudent.id) : null;

  const trajectoryData = {
    labels: ['Current', 'Next Term', 'Term 2', 'Term 3', 'Term 4', 'Graduation'],
    datasets: [
      {
        label: 'Predicted GPA',
        data: currentPrediction ? [
          selectedStudent?.currentGPA,
          currentPrediction.nextTermGPA,
          Math.max(0, currentPrediction.nextTermGPA + 0.1),
          Math.max(0, currentPrediction.nextTermGPA + 0.15),
          Math.max(0, currentPrediction.nextTermGPA + 0.2),
          Math.max(0, currentPrediction.nextTermGPA + 0.25),
        ] : [],
        borderColor: 'rgb(59, 130, 246)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        tension: 0.4,
      },
      ...(scenarios.map((scenario, index) => ({
        label: scenario.name,
        data: scenario.prediction ? [
          selectedStudent?.currentGPA,
          scenario.prediction.nextTermGPA,
          Math.max(0, scenario.prediction.nextTermGPA + 0.15),
          Math.max(0, scenario.prediction.nextTermGPA + 0.25),
          Math.max(0, scenario.prediction.nextTermGPA + 0.35),
          Math.max(0, scenario.prediction.nextTermGPA + 0.4),
        ] : [],
        borderColor: `hsl(${120 + index * 60}, 70%, 50%)`,
        backgroundColor: `hsla(${120 + index * 60}, 70%, 50%, 0.1)`,
        tension: 0.4,
        borderDash: [5, 5],
      })))
    ],
  };

  const riskFactorsData = {
    labels: currentPrediction?.riskFactors.map(f => f.factor) || [],
    datasets: [
      {
        label: 'Impact Score',
        data: currentPrediction?.riskFactors.map(f => Math.abs(f.impact) * 100) || [],
        backgroundColor: currentPrediction?.riskFactors.map(f =>
          f.impact < -0.6 ? 'rgba(239, 68, 68, 0.8)' :
          f.impact < -0.3 ? 'rgba(245, 158, 11, 0.8)' :
          'rgba(34, 197, 94, 0.8)'
        ) || [],
        borderWidth: 1,
      },
    ],
  };

  if (modelStatus === 'loading') {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <Spin size="large" />
          <div className="mt-4">
            <h3 className="text-lg font-semibold">Loading AI Models...</h3>
            <p className="text-gray-600">Initializing student success prediction engine</p>
          </div>
        </div>
      </div>
    );
  }

  if (modelStatus === 'error') {
    return (
      <Alert
        message="Model Loading Error"
        description="Failed to load the AI prediction models. Please check your connection and try again."
        type="error"
        action={
          <Button size="small" onClick={initializeModel}>
            Retry
          </Button>
        }
      />
    );
  }

  return (
    <div className="student-success-predictor p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
              <BrainOutlined className="text-blue-600" />
              Student Success Prediction Center
            </h1>
            <p className="text-gray-600 mt-2">
              AI-powered analytics to predict student outcomes and recommend interventions
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              icon={<ReloadOutlined />}
              onClick={handleRefreshPrediction}
              loading={loading}
              disabled={!selectedStudent}
            >
              Refresh Prediction
            </Button>
            <Button
              icon={<SettingOutlined />}
              onClick={() => setShowScenarioModal(true)}
              disabled={!selectedStudent}
            >
              Create Scenario
            </Button>
          </div>
        </div>
      </div>

      <Row gutter={[24, 24]}>
        {/* Student Selection Panel */}
        <Col xs={24} lg={8}>
          <Card title="Student Selection" className="h-full">
            {/* Filters */}
            <div className="mb-4 space-y-3">
              <Select
                placeholder="Filter by Risk Level"
                style={{ width: '100%' }}
                value={selectedFilters.riskLevel}
                onChange={(value) => setSelectedFilters(prev => ({ ...prev, riskLevel: value }))}
              >
                <Option value="all">All Risk Levels</Option>
                <Option value="critical">Critical</Option>
                <Option value="high">High</Option>
                <Option value="medium">Medium</Option>
                <Option value="low">Low</Option>
              </Select>

              <Row gutter={8}>
                <Col span={12}>
                  <Select
                    placeholder="Semester"
                    style={{ width: '100%' }}
                    value={selectedFilters.semester}
                    onChange={(value) => setSelectedFilters(prev => ({ ...prev, semester: value }))}
                  >
                    <Option value="all">All Semesters</Option>
                    <Option value="Fall 2024">Fall 2024</Option>
                    <Option value="Spring 2024">Spring 2024</Option>
                  </Select>
                </Col>
                <Col span={12}>
                  <Select
                    placeholder="Major"
                    style={{ width: '100%' }}
                    value={selectedFilters.major}
                    onChange={(value) => setSelectedFilters(prev => ({ ...prev, major: value }))}
                  >
                    <Option value="all">All Majors</Option>
                    <Option value="Computer Science">Computer Science</Option>
                    <Option value="Business">Business</Option>
                    <Option value="Engineering">Engineering</Option>
                  </Select>
                </Col>
              </Row>
            </div>

            <Divider />

            {/* Student List */}
            <List
              dataSource={filteredStudents}
              renderItem={(student) => {
                const prediction = predictions.get(student.id);
                return (
                  <List.Item
                    className={`cursor-pointer transition-colors hover:bg-gray-50 ${
                      selectedStudent?.id === student.id ? 'bg-blue-50 border-blue-200' : ''
                    }`}
                    onClick={() => handleStudentSelect(student.id)}
                  >
                    <List.Item.Meta
                      avatar={
                        <Badge
                          dot
                          color={prediction ? getRiskLevelColor(prediction.riskLevel) : 'gray'}
                        >
                          <Avatar icon={<UserOutlined />} />
                        </Badge>
                      }
                      title={
                        <div className="flex justify-between items-center">
                          <span>{student.name}</span>
                          {prediction && (
                            <Tag color={getRiskLevelColor(prediction.riskLevel)}>
                              {getRiskLevelIcon(prediction.riskLevel)}
                              {prediction.riskLevel.toUpperCase()}
                            </Tag>
                          )}
                        </div>
                      }
                      description={
                        <div>
                          <div>{student.major} • {student.yearLevel}</div>
                          <div className="text-xs text-gray-500">
                            GPA: {student.currentGPA.toFixed(2)} • Attendance: {(student.attendanceRate * 100).toFixed(0)}%
                          </div>
                        </div>
                      }
                    />
                  </List.Item>
                );
              }}
            />
          </Card>
        </Col>

        {/* Main Prediction Panel */}
        <Col xs={24} lg={16}>
          {selectedStudent && currentPrediction ? (
            <Card className="h-full">
              <div className="mb-4">
                <h2 className="text-xl font-semibold flex items-center gap-2">
                  <TrophyOutlined className="text-yellow-500" />
                  {selectedStudent.name} - Success Prediction
                </h2>
                <p className="text-gray-600">{selectedStudent.studentId} • {selectedStudent.major}</p>
              </div>

              <Tabs activeKey={activeTab} onChange={setActiveTab}>
                <TabPane tab="Prediction Overview" key="prediction">
                  <Row gutter={[16, 16]}>
                    <Col xs={24} sm={8}>
                      <Card>
                        <Statistic
                          title="Graduation Probability"
                          value={(currentPrediction.graduationProbability * 100).toFixed(1)}
                          suffix="%"
                          valueStyle={{
                            color: currentPrediction.graduationProbability > 0.7 ? '#3f8600' :
                                   currentPrediction.graduationProbability > 0.5 ? '#d4b106' : '#cf1322'
                          }}
                          prefix={<TrendingUpOutlined />}
                        />
                        <Progress
                          percent={currentPrediction.graduationProbability * 100}
                          strokeColor={{
                            '0%': currentPrediction.graduationProbability > 0.7 ? '#87d068' : '#ff4d4f',
                            '100%': currentPrediction.graduationProbability > 0.7 ? '#3f8600' : '#a8071a',
                          }}
                          showInfo={false}
                          className="mt-2"
                        />
                      </Card>
                    </Col>

                    <Col xs={24} sm={8}>
                      <Card>
                        <Statistic
                          title="Predicted Next Term GPA"
                          value={currentPrediction.nextTermGPA.toFixed(2)}
                          valueStyle={{
                            color: currentPrediction.nextTermGPA > 3.0 ? '#3f8600' :
                                   currentPrediction.nextTermGPA > 2.5 ? '#d4b106' : '#cf1322'
                          }}
                          prefix={<BarChartOutlined />}
                        />
                        <div className="text-xs text-gray-500 mt-2">
                          Current: {selectedStudent.currentGPA.toFixed(2)}
                        </div>
                      </Card>
                    </Col>

                    <Col xs={24} sm={8}>
                      <Card>
                        <Statistic
                          title="Risk Level"
                          value={currentPrediction.riskLevel.toUpperCase()}
                          valueStyle={{ color: getRiskLevelColor(currentPrediction.riskLevel) }}
                          prefix={getRiskLevelIcon(currentPrediction.riskLevel)}
                        />
                        <div className="text-xs text-gray-500 mt-2">
                          {currentPrediction.riskFactors.length} risk factors identified
                        </div>
                      </Card>
                    </Col>
                  </Row>

                  <div className="mt-6">
                    <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                      <LineChartOutlined />
                      Academic Trajectory Prediction
                    </h3>
                    <div style={{ height: '300px' }}>
                      <Line
                        ref={chartRef}
                        data={trajectoryData}
                        options={{
                          responsive: true,
                          maintainAspectRatio: false,
                          plugins: {
                            legend: {
                              position: 'top' as const,
                            },
                            title: {
                              display: true,
                              text: 'GPA Trajectory Prediction',
                            },
                          },
                          scales: {
                            y: {
                              beginAtZero: true,
                              max: 4.0,
                              title: {
                                display: true,
                                text: 'GPA',
                              },
                            },
                          },
                        }}
                      />
                    </div>
                  </div>
                </TabPane>

                <TabPane tab="Risk Factors" key="risk-factors">
                  <div className="space-y-4">
                    <div>
                      <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                        <WarningOutlined className="text-orange-500" />
                        Risk Factor Analysis
                      </h3>
                      <div style={{ height: '250px' }}>
                        <Bar
                          data={riskFactorsData}
                          options={{
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                              legend: {
                                display: false,
                              },
                            },
                            scales: {
                              y: {
                                beginAtZero: true,
                                max: 100,
                                title: {
                                  display: true,
                                  text: 'Impact Score (%)',
                                },
                              },
                            },
                          }}
                        />
                      </div>
                    </div>

                    <Divider />

                    <List
                      header={<div className="font-semibold">Detailed Risk Factors</div>}
                      dataSource={currentPrediction.riskFactors}
                      renderItem={(factor) => (
                        <List.Item>
                          <div className="w-full">
                            <div className="flex justify-between items-start mb-2">
                              <div>
                                <h4 className="font-medium">{factor.factor}</h4>
                                <Tag color={factor.category === 'academic' ? 'blue' :
                                           factor.category === 'financial' ? 'orange' :
                                           factor.category === 'attendance' ? 'red' :
                                           factor.category === 'social' ? 'green' : 'gray'}>
                                  {factor.category.toUpperCase()}
                                </Tag>
                              </div>
                              <div className="text-right">
                                <div className="text-lg font-semibold text-red-600">
                                  {(Math.abs(factor.impact) * 100).toFixed(0)}%
                                </div>
                                <div className="text-xs text-gray-500">
                                  Confidence: {(factor.confidence * 100).toFixed(0)}%
                                </div>
                              </div>
                            </div>
                            <p className="text-gray-600 text-sm mb-2">{factor.description}</p>
                            {factor.recommendation && (
                              <div className="bg-blue-50 p-2 rounded text-sm">
                                <strong>Recommendation:</strong> {factor.recommendation}
                              </div>
                            )}
                          </div>
                        </List.Item>
                      )}
                    />
                  </div>
                </TabPane>

                <TabPane tab="Interventions" key="interventions">
                  <div>
                    <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                      <BulbOutlined className="text-green-500" />
                      Recommended Interventions
                    </h3>

                    <List
                      dataSource={currentPrediction.interventions}
                      renderItem={(intervention) => (
                        <List.Item>
                          <Card className="w-full" size="small">
                            <div className="flex justify-between items-start mb-3">
                              <div>
                                <h4 className="font-semibold text-lg">{intervention.title}</h4>
                                <Tag color={
                                  intervention.priority === 'urgent' ? 'red' :
                                  intervention.priority === 'high' ? 'orange' :
                                  intervention.priority === 'medium' ? 'blue' : 'green'
                                }>
                                  {intervention.priority.toUpperCase()} PRIORITY
                                </Tag>
                                <Tag color="blue">{intervention.type.replace('_', ' ').toUpperCase()}</Tag>
                              </div>
                              <div className="text-right">
                                <div className="text-lg font-semibold text-green-600">
                                  {(intervention.estimatedImpact * 100).toFixed(0)}% Impact
                                </div>
                                {intervention.successRate && (
                                  <div className="text-sm text-gray-500">
                                    Success Rate: {(intervention.successRate * 100).toFixed(0)}%
                                  </div>
                                )}
                              </div>
                            </div>

                            <p className="text-gray-600 mb-3">{intervention.description}</p>

                            <Row gutter={16}>
                              <Col span={8}>
                                <div className="text-center">
                                  <div className="text-lg font-semibold">{intervention.timeToImplement}</div>
                                  <div className="text-xs text-gray-500">Time to Implement</div>
                                </div>
                              </Col>
                              <Col span={8}>
                                <div className="text-center">
                                  <div className="text-lg font-semibold">
                                    ${intervention.cost || 0}
                                  </div>
                                  <div className="text-xs text-gray-500">Estimated Cost</div>
                                </div>
                              </Col>
                              <Col span={8}>
                                <div className="text-center">
                                  <Tag color={intervention.status === 'recommended' ? 'blue' : 'green'}>
                                    {intervention.status.toUpperCase()}
                                  </Tag>
                                </div>
                              </Col>
                            </Row>

                            <div className="mt-3 flex gap-2">
                              <Button type="primary" size="small">
                                Implement
                              </Button>
                              <Button size="small">
                                More Details
                              </Button>
                              <Button size="small">
                                Assign to Staff
                              </Button>
                            </div>
                          </Card>
                        </List.Item>
                      )}
                    />
                  </div>
                </TabPane>

                <TabPane tab="Scenarios" key="scenarios">
                  <div>
                    <div className="flex justify-between items-center mb-4">
                      <h3 className="text-lg font-semibold flex items-center gap-2">
                        <RocketOutlined className="text-blue-500" />
                        Prediction Scenarios
                      </h3>
                      <Button
                        type="primary"
                        icon={<BulbOutlined />}
                        onClick={() => setShowScenarioModal(true)}
                      >
                        Create New Scenario
                      </Button>
                    </div>

                    {scenarios.length > 0 ? (
                      <div className="space-y-4">
                        <div style={{ height: '300px' }}>
                          <Line
                            data={trajectoryData}
                            options={{
                              responsive: true,
                              maintainAspectRatio: false,
                              plugins: {
                                legend: {
                                  position: 'top' as const,
                                },
                                title: {
                                  display: true,
                                  text: 'Scenario Comparison',
                                },
                              },
                              scales: {
                                y: {
                                  beginAtZero: true,
                                  max: 4.0,
                                  title: {
                                    display: true,
                                    text: 'GPA',
                                  },
                                },
                              },
                            }}
                          />
                        </div>

                        <List
                          header={<div className="font-semibold">Scenario Details</div>}
                          dataSource={scenarios}
                          renderItem={(scenario, index) => (
                            <List.Item>
                              <Card className="w-full" size="small">
                                <div className="flex justify-between items-start">
                                  <div>
                                    <h4 className="font-semibold">{scenario.name}</h4>
                                    <div className="text-sm text-gray-600 space-y-1">
                                      {Object.entries(scenario.adjustments).map(([key, value]) => (
                                        <div key={key}>
                                          <strong>{key}:</strong> {
                                            typeof value === 'number'
                                              ? key.includes('Rate') ? (value * 100).toFixed(0) + '%'
                                                : value.toFixed(2)
                                              : String(value)
                                          }
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                  {scenario.prediction && (
                                    <div className="text-right">
                                      <div className="text-lg font-semibold text-green-600">
                                        {(scenario.prediction.graduationProbability * 100).toFixed(1)}%
                                      </div>
                                      <div className="text-sm text-gray-500">Graduation Probability</div>
                                      <Tag color={getRiskLevelColor(scenario.prediction.riskLevel)}>
                                        {scenario.prediction.riskLevel.toUpperCase()}
                                      </Tag>
                                    </div>
                                  )}
                                </div>
                              </Card>
                            </List.Item>
                          )}
                        />
                      </div>
                    ) : (
                      <div className="text-center py-8">
                        <RocketOutlined className="text-6xl text-gray-300 mb-4" />
                        <h3 className="text-lg font-semibold text-gray-500 mb-2">
                          No Scenarios Created
                        </h3>
                        <p className="text-gray-400 mb-4">
                          Create scenarios to explore how different interventions might impact student outcomes
                        </p>
                        <Button
                          type="primary"
                          icon={<BulbOutlined />}
                          onClick={() => setShowScenarioModal(true)}
                        >
                          Create First Scenario
                        </Button>
                      </div>
                    )}
                  </div>
                </TabPane>
              </Tabs>
            </Card>
          ) : (
            <Card className="h-full flex items-center justify-center">
              <div className="text-center">
                <UserOutlined className="text-6xl text-gray-300 mb-4" />
                <h3 className="text-lg font-semibold text-gray-500">Select a Student</h3>
                <p className="text-gray-400">Choose a student from the list to view their success prediction</p>
              </div>
            </Card>
          )}
        </Col>
      </Row>

      {/* Scenario Creation Modal */}
      <Modal
        title="Create Prediction Scenario"
        open={showScenarioModal}
        onCancel={() => {
          setShowScenarioModal(false);
          form.resetFields();
        }}
        footer={null}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={createScenario}
          initialValues={{
            gpa: selectedStudent?.currentGPA,
            attendance: selectedStudent ? selectedStudent.attendanceRate * 100 : 85,
            tutoring: selectedStudent?.tutoringSessions || 0,
            advising: selectedStudent?.advisingMeetings || 0,
            workHours: selectedStudent?.workHoursPerWeek || 0,
          }}
        >
          <Form.Item
            name="scenarioName"
            label="Scenario Name"
            rules={[{ required: true, message: 'Please enter a scenario name' }]}
          >
            <Input placeholder="e.g., 'With Enhanced Tutoring'" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="gpa"
                label="Target GPA"
                rules={[{ required: true, message: 'Please enter a GPA' }]}
              >
                <InputNumber
                  min={0}
                  max={4}
                  step={0.1}
                  precision={2}
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="attendance"
                label="Attendance Rate (%)"
                rules={[{ required: true, message: 'Please enter attendance rate' }]}
              >
                <InputNumber
                  min={0}
                  max={100}
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="tutoring"
                label="Tutoring Sessions per Month"
              >
                <InputNumber
                  min={0}
                  max={20}
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="advising"
                label="Advising Meetings per Semester"
              >
                <InputNumber
                  min={0}
                  max={10}
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="workHours"
            label="Work Hours per Week"
          >
            <InputNumber
              min={0}
              max={40}
              style={{ width: '100%' }}
            />
          </Form.Item>

          <div className="flex justify-end gap-2">
            <Button onClick={() => {
              setShowScenarioModal(false);
              form.resetFields();
            }}>
              Cancel
            </Button>
            <Button type="primary" htmlType="submit">
              Create Scenario
            </Button>
          </div>
        </Form>
      </Modal>
    </div>
  );
};

export default StudentSuccessPredictor;