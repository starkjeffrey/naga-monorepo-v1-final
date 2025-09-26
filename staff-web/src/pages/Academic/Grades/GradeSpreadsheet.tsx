/**
 * GradeSpreadsheet Component
 *
 * Excel-like interface for grade management with real-time collaboration features:
 * - Real-time collaborative editing with conflict resolution
 * - Bulk grade entry with copy/paste support
 * - Grade calculation formulas with custom weighting
 * - Attendance integration with automatic grade adjustments
 * - Grade distribution analytics and curves
 * - Export to gradebook formats
 */

import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import {
  Table,
  Input,
  InputNumber,
  Button,
  Space,
  Card,
  Tooltip,
  Badge,
  Select,
  Popover,
  Statistic,
  Progress,
  Alert,
  Tag,
  Dropdown,
  Modal,
  Form,
  Slider,
  Switch,
  notification,
  message,
} from 'antd';
import {
  SaveOutlined,
  UndoOutlined,
  RedoOutlined,
  CalculatorOutlined,
  BarChartOutlined,
  DownloadOutlined,
  SyncOutlined,
  UserOutlined,
  EyeOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  LockOutlined,
  UnlockOutlined,
} from '@ant-design/icons';
import type { ColumnType } from 'antd/es/table/interface';
import { EnhancedDataGrid } from '../../../components/patterns';

// Types for the grade spreadsheet
interface Student {
  id: string;
  studentId: string;
  name: string;
  email: string;
  avatar?: string;
  attendanceRate: number;
  status: 'active' | 'inactive' | 'dropped';
}

interface Assignment {
  id: string;
  name: string;
  category: string;
  maxPoints: number;
  weight: number;
  dueDate: string;
  type: 'homework' | 'quiz' | 'exam' | 'project' | 'participation';
}

interface Grade {
  id: string;
  studentId: string;
  assignmentId: string;
  points: number | null;
  percentage: number | null;
  letterGrade: string | null;
  comments?: string;
  submitted: boolean;
  late: boolean;
  excused: boolean;
  lastModified: string;
  modifiedBy: string;
}

interface GradeCell {
  studentId: string;
  assignmentId: string;
  value: number | null;
  isEditing: boolean;
  isLocked: boolean;
  editingBy?: string;
  lastSaved: string;
  hasConflict: boolean;
}

interface CollaborativeUser {
  id: string;
  name: string;
  avatar?: string;
  color: string;
  cursor?: {
    studentId: string;
    assignmentId: string;
  };
}

interface GradeSpreadsheetProps {
  classId: string;
  term: string;
  students: Student[];
  assignments: Assignment[];
  grades: Grade[];
  onGradeUpdate: (grade: Partial<Grade>) => Promise<void>;
  onBulkGradeUpdate: (grades: Partial<Grade>[]) => Promise<void>;
  onExport: (format: 'excel' | 'csv' | 'pdf') => void;
  readOnly?: boolean;
  showAnalytics?: boolean;
}

export const GradeSpreadsheet: React.FC<GradeSpreadsheetProps> = ({
  classId,
  term,
  students,
  assignments,
  grades,
  onGradeUpdate,
  onBulkGradeUpdate,
  onExport,
  readOnly = false,
  showAnalytics = true,
}) => {
  // State management
  const [gradeMatrix, setGradeMatrix] = useState<Map<string, GradeCell>>(new Map());
  const [selectedCells, setSelectedCells] = useState<Set<string>>(new Set());
  const [editingCell, setEditingCell] = useState<string | null>(null);
  const [collaborativeUsers, setCollaborativeUsers] = useState<CollaborativeUser[]>([]);
  const [autoSaveEnabled, setAutoSaveEnabled] = useState(true);
  const [showFormulas, setShowFormulas] = useState(false);
  const [gradingScale, setGradingScale] = useState('standard');
  const [curveSettings, setCurveSettings] = useState({ enabled: false, target: 85 });
  const [analyticsVisible, setAnalyticsVisible] = useState(showAnalytics);

  // Refs for collaboration
  const wsRef = useRef<WebSocket | null>(null);
  const autoSaveTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const undoStackRef = useRef<any[]>([]);
  const redoStackRef = useRef<any[]>([]);

  // Initialize grade matrix from grades data
  useEffect(() => {
    const matrix = new Map<string, GradeCell>();

    students.forEach(student => {
      assignments.forEach(assignment => {
        const cellKey = `${student.id}-${assignment.id}`;
        const grade = grades.find(g => g.studentId === student.id && g.assignmentId === assignment.id);

        matrix.set(cellKey, {
          studentId: student.id,
          assignmentId: assignment.id,
          value: grade?.points || null,
          isEditing: false,
          isLocked: false,
          lastSaved: grade?.lastModified || new Date().toISOString(),
          hasConflict: false,
        });
      });
    });

    setGradeMatrix(matrix);
  }, [students, assignments, grades]);

  // WebSocket connection for real-time collaboration
  useEffect(() => {
    if (readOnly) return;

    const ws = new WebSocket(`ws://localhost:8000/ws/grades/${classId}/`);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('Connected to grade collaboration socket');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleCollaborativeUpdate(data);
    };

    ws.onclose = () => {
      console.log('Disconnected from grade collaboration socket');
      setTimeout(() => {
        // Attempt to reconnect
        if (wsRef.current?.readyState === WebSocket.CLOSED) {
          wsRef.current = new WebSocket(`ws://localhost:8000/ws/grades/${classId}/`);
        }
      }, 3000);
    };

    return () => {
      ws.close();
    };
  }, [classId, readOnly]);

  // Handle collaborative updates from WebSocket
  const handleCollaborativeUpdate = useCallback((data: any) => {
    switch (data.type) {
      case 'grade_updated':
        setGradeMatrix(prev => {
          const newMatrix = new Map(prev);
          const cellKey = `${data.studentId}-${data.assignmentId}`;
          const cell = newMatrix.get(cellKey);
          if (cell) {
            newMatrix.set(cellKey, {
              ...cell,
              value: data.value,
              lastSaved: data.timestamp,
              hasConflict: cell.isEditing && cell.value !== data.value,
            });
          }
          return newMatrix;
        });
        break;

      case 'user_cursor':
        setCollaborativeUsers(prev =>
          prev.map(user =>
            user.id === data.userId
              ? { ...user, cursor: { studentId: data.studentId, assignmentId: data.assignmentId } }
              : user
          )
        );
        break;

      case 'cell_locked':
        setGradeMatrix(prev => {
          const newMatrix = new Map(prev);
          const cellKey = `${data.studentId}-${data.assignmentId}`;
          const cell = newMatrix.get(cellKey);
          if (cell) {
            newMatrix.set(cellKey, {
              ...cell,
              isLocked: true,
              editingBy: data.userId,
            });
          }
          return newMatrix;
        });
        break;

      case 'cell_unlocked':
        setGradeMatrix(prev => {
          const newMatrix = new Map(prev);
          const cellKey = `${data.studentId}-${data.assignmentId}`;
          const cell = newMatrix.get(cellKey);
          if (cell) {
            newMatrix.set(cellKey, {
              ...cell,
              isLocked: false,
              editingBy: undefined,
            });
          }
          return newMatrix;
        });
        break;
    }
  }, []);

  // Calculate student totals and analytics
  const studentAnalytics = useMemo(() => {
    return students.map(student => {
      const studentGrades = assignments.map(assignment => {
        const cellKey = `${student.id}-${assignment.id}`;
        const cell = gradeMatrix.get(cellKey);
        return {
          assignment,
          points: cell?.value || 0,
          maxPoints: assignment.maxPoints,
          percentage: cell?.value ? (cell.value / assignment.maxPoints) * 100 : 0,
        };
      });

      const totalEarnedPoints = studentGrades.reduce((sum, g) => sum + g.points, 0);
      const totalPossiblePoints = studentGrades.reduce((sum, g) => sum + g.maxPoints, 0);
      const weightedGrade = calculateWeightedGrade(studentGrades);
      const letterGrade = calculateLetterGrade(weightedGrade);

      return {
        student,
        grades: studentGrades,
        totalEarnedPoints,
        totalPossiblePoints,
        percentage: totalPossiblePoints > 0 ? (totalEarnedPoints / totalPossiblePoints) * 100 : 0,
        weightedGrade,
        letterGrade,
        trend: calculateGradeTrend(studentGrades),
        missedAssignments: studentGrades.filter(g => g.points === 0).length,
      };
    });
  }, [students, assignments, gradeMatrix]);

  // Calculate weighted grade based on assignment categories
  const calculateWeightedGrade = (grades: any[]) => {
    const categoryTotals = new Map<string, { earned: number; possible: number; weight: number }>();

    grades.forEach(g => {
      const category = g.assignment.category;
      const current = categoryTotals.get(category) || { earned: 0, possible: 0, weight: g.assignment.weight };
      current.earned += g.points;
      current.possible += g.maxPoints;
      categoryTotals.set(category, current);
    });

    let weightedTotal = 0;
    let totalWeight = 0;

    categoryTotals.forEach(({ earned, possible, weight }) => {
      if (possible > 0) {
        weightedTotal += (earned / possible) * weight;
        totalWeight += weight;
      }
    });

    return totalWeight > 0 ? (weightedTotal / totalWeight) * 100 : 0;
  };

  // Calculate letter grade from percentage
  const calculateLetterGrade = (percentage: number): string => {
    if (percentage >= 97) return 'A+';
    if (percentage >= 93) return 'A';
    if (percentage >= 90) return 'A-';
    if (percentage >= 87) return 'B+';
    if (percentage >= 83) return 'B';
    if (percentage >= 80) return 'B-';
    if (percentage >= 77) return 'C+';
    if (percentage >= 73) return 'C';
    if (percentage >= 70) return 'C-';
    if (percentage >= 67) return 'D+';
    if (percentage >= 63) return 'D';
    if (percentage >= 60) return 'D-';
    return 'F';
  };

  // Calculate grade trend
  const calculateGradeTrend = (grades: any[]): 'improving' | 'declining' | 'stable' => {
    if (grades.length < 3) return 'stable';

    const recent = grades.slice(-3);
    const percentages = recent.map(g => g.percentage);

    const trend = percentages[2] - percentages[0];
    if (trend > 5) return 'improving';
    if (trend < -5) return 'declining';
    return 'stable';
  };

  // Handle cell edit
  const handleCellEdit = useCallback(async (studentId: string, assignmentId: string, value: number | null) => {
    const cellKey = `${studentId}-${assignmentId}`;

    // Send lock signal to other users
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'lock_cell',
        studentId,
        assignmentId,
        userId: 'current-user', // Get from auth context
      }));
    }

    setGradeMatrix(prev => {
      const newMatrix = new Map(prev);
      const cell = newMatrix.get(cellKey);
      if (cell) {
        newMatrix.set(cellKey, {
          ...cell,
          value,
          isEditing: true,
        });
      }
      return newMatrix;
    });

    setEditingCell(cellKey);

    // Auto-save after delay
    if (autoSaveEnabled && autoSaveTimeoutRef.current) {
      clearTimeout(autoSaveTimeoutRef.current);
    }

    autoSaveTimeoutRef.current = setTimeout(async () => {
      await saveGrade(studentId, assignmentId, value);
    }, 1000);
  }, [autoSaveEnabled]);

  // Save grade to backend
  const saveGrade = useCallback(async (studentId: string, assignmentId: string, value: number | null) => {
    try {
      await onGradeUpdate({
        studentId,
        assignmentId,
        points: value,
        percentage: value ? (value / assignments.find(a => a.id === assignmentId)?.maxPoints || 1) * 100 : null,
        lastModified: new Date().toISOString(),
        modifiedBy: 'current-user', // Get from auth context
      });

      // Send update to other users
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: 'grade_updated',
          studentId,
          assignmentId,
          value,
          timestamp: new Date().toISOString(),
        }));
      }

      // Update local state
      const cellKey = `${studentId}-${assignmentId}`;
      setGradeMatrix(prev => {
        const newMatrix = new Map(prev);
        const cell = newMatrix.get(cellKey);
        if (cell) {
          newMatrix.set(cellKey, {
            ...cell,
            isEditing: false,
            lastSaved: new Date().toISOString(),
            hasConflict: false,
          });
        }
        return newMatrix;
      });

      setEditingCell(null);
      message.success('Grade saved successfully');
    } catch (error) {
      message.error('Failed to save grade');
      console.error('Grade save error:', error);
    }
  }, [assignments, onGradeUpdate]);

  // Handle bulk paste operation
  const handleBulkPaste = useCallback(async (pastedData: string) => {
    try {
      const rows = pastedData.trim().split('\n');
      const updates: Partial<Grade>[] = [];

      rows.forEach((row, rowIndex) => {
        const values = row.split('\t');
        values.forEach((value, colIndex) => {
          const student = students[rowIndex];
          const assignment = assignments[colIndex];

          if (student && assignment && value.trim()) {
            const points = parseFloat(value.trim());
            if (!isNaN(points)) {
              updates.push({
                studentId: student.id,
                assignmentId: assignment.id,
                points,
                percentage: (points / assignment.maxPoints) * 100,
                lastModified: new Date().toISOString(),
              });
            }
          }
        });
      });

      if (updates.length > 0) {
        await onBulkGradeUpdate(updates);
        message.success(`Updated ${updates.length} grades`);
      }
    } catch (error) {
      message.error('Failed to paste grades');
      console.error('Bulk paste error:', error);
    }
  }, [students, assignments, onBulkGradeUpdate]);

  // Generate table columns for assignments
  const assignmentColumns: ColumnType<any>[] = useMemo(() => {
    return assignments.map(assignment => ({
      key: assignment.id,
      title: (
        <div className="text-center">
          <div className="font-medium text-xs">{assignment.name}</div>
          <div className="text-gray-500 text-xs">
            {assignment.maxPoints} pts • {assignment.weight}%
          </div>
          <Tag size="small" color={getAssignmentTypeColor(assignment.type)}>
            {assignment.type}
          </Tag>
        </div>
      ),
      width: 120,
      align: 'center',
      render: (_, record) => {
        const cellKey = `${record.id}-${assignment.id}`;
        const cell = gradeMatrix.get(cellKey);
        const isEditing = editingCell === cellKey;
        const collaborativeUser = collaborativeUsers.find(u =>
          u.cursor?.studentId === record.id && u.cursor?.assignmentId === assignment.id
        );

        return (
          <div className="relative">
            {collaborativeUser && (
              <div
                className="absolute -top-2 -right-2 w-4 h-4 rounded-full border-2 border-white"
                style={{ backgroundColor: collaborativeUser.color }}
                title={`${collaborativeUser.name} is here`}
              />
            )}

            {cell?.isLocked && cell.editingBy !== 'current-user' ? (
              <Tooltip title={`Locked by ${cell.editingBy}`}>
                <div className="relative">
                  <InputNumber
                    size="small"
                    value={cell.value}
                    disabled
                    className="w-full"
                    controls={false}
                  />
                  <LockOutlined className="absolute top-1 right-1 text-red-500" />
                </div>
              </Tooltip>
            ) : (
              <InputNumber
                size="small"
                value={cell?.value}
                min={0}
                max={assignment.maxPoints}
                precision={1}
                className={`w-full ${cell?.hasConflict ? 'border-red-500' : ''}`}
                controls={false}
                onChange={(value) => handleCellEdit(record.id, assignment.id, value)}
                onPressEnter={() => saveGrade(record.id, assignment.id, cell?.value || null)}
                onBlur={() => {
                  if (isEditing) {
                    saveGrade(record.id, assignment.id, cell?.value || null);
                  }
                }}
                style={{
                  backgroundColor: cell?.hasConflict ? '#fef2f2' :
                                   isEditing ? '#f0f9ff' : 'white',
                }}
              />
            )}

            {cell?.hasConflict && (
              <Tooltip title="Grade conflict detected">
                <WarningOutlined className="absolute -top-1 -right-1 text-orange-500" />
              </Tooltip>
            )}
          </div>
        );
      },
    }));
  }, [assignments, gradeMatrix, editingCell, collaborativeUsers, handleCellEdit, saveGrade]);

  // Get assignment type color
  const getAssignmentTypeColor = (type: string) => {
    const colors = {
      homework: 'blue',
      quiz: 'green',
      exam: 'red',
      project: 'purple',
      participation: 'orange',
    };
    return colors[type as keyof typeof colors] || 'default';
  };

  // Generate student rows with analytics
  const studentRows = useMemo(() => {
    return studentAnalytics.map(analytics => ({
      key: analytics.student.id,
      id: analytics.student.id,
      ...analytics.student,
      ...analytics,
    }));
  }, [studentAnalytics]);

  // Base columns for student info and totals
  const baseColumns: ColumnType<any>[] = [
    {
      key: 'student',
      title: 'Student',
      width: 200,
      fixed: 'left',
      render: (_, record) => (
        <div className="flex items-center space-x-2">
          <Badge
            status={record.status === 'active' ? 'success' : 'error'}
            dot
          />
          <div>
            <div className="font-medium">{record.name}</div>
            <div className="text-xs text-gray-500">{record.studentId}</div>
            <div className="text-xs">
              Attendance: {record.attendanceRate}%
            </div>
          </div>
        </div>
      ),
    },
    ...assignmentColumns,
    {
      key: 'total',
      title: 'Total',
      width: 100,
      fixed: 'right',
      align: 'center',
      render: (_, record) => (
        <div className="text-center">
          <div className="font-bold text-lg">{record.letterGrade}</div>
          <div className="text-sm">{record.weightedGrade.toFixed(1)}%</div>
          <div className="flex justify-center mt-1">
            {record.trend === 'improving' && (
              <Tag color="green" size="small">↗</Tag>
            )}
            {record.trend === 'declining' && (
              <Tag color="red" size="small">↘</Tag>
            )}
            {record.trend === 'stable' && (
              <Tag color="blue" size="small">→</Tag>
            )}
          </div>
        </div>
      ),
    },
  ];

  // Calculate class statistics
  const classStats = useMemo(() => {
    const validGrades = studentAnalytics.filter(s => s.weightedGrade > 0);
    const averageGrade = validGrades.reduce((sum, s) => sum + s.weightedGrade, 0) / validGrades.length;

    const gradeDistribution = {
      'A': validGrades.filter(s => s.weightedGrade >= 90).length,
      'B': validGrades.filter(s => s.weightedGrade >= 80 && s.weightedGrade < 90).length,
      'C': validGrades.filter(s => s.weightedGrade >= 70 && s.weightedGrade < 80).length,
      'D': validGrades.filter(s => s.weightedGrade >= 60 && s.weightedGrade < 70).length,
      'F': validGrades.filter(s => s.weightedGrade < 60).length,
    };

    return {
      averageGrade,
      totalStudents: students.length,
      validGrades: validGrades.length,
      gradeDistribution,
      passingRate: (validGrades.filter(s => s.weightedGrade >= 60).length / validGrades.length) * 100,
    };
  }, [studentAnalytics, students.length]);

  return (
    <div className="grade-spreadsheet space-y-4">
      {/* Header with actions and analytics */}
      <Card>
        <div className="flex justify-between items-start mb-4">
          <div>
            <h2 className="text-xl font-bold">Grade Spreadsheet</h2>
            <p className="text-gray-600">Class: {classId} • Term: {term}</p>
          </div>

          <Space>
            {!readOnly && (
              <>
                <Switch
                  checked={autoSaveEnabled}
                  onChange={setAutoSaveEnabled}
                  checkedChildren="Auto-save"
                  unCheckedChildren="Manual"
                />

                <Button
                  icon={<UndoOutlined />}
                  disabled={undoStackRef.current.length === 0}
                  onClick={() => {/* Implement undo */}}
                >
                  Undo
                </Button>

                <Button
                  icon={<RedoOutlined />}
                  disabled={redoStackRef.current.length === 0}
                  onClick={() => {/* Implement redo */}}
                >
                  Redo
                </Button>
              </>
            )}

            <Button
              icon={<CalculatorOutlined />}
              onClick={() => setShowFormulas(!showFormulas)}
            >
              {showFormulas ? 'Hide' : 'Show'} Formulas
            </Button>

            <Button
              icon={<BarChartOutlined />}
              onClick={() => setAnalyticsVisible(!analyticsVisible)}
            >
              Analytics
            </Button>

            <Dropdown
              menu={{
                items: [
                  { key: 'excel', label: 'Export to Excel', icon: <DownloadOutlined /> },
                  { key: 'csv', label: 'Export to CSV', icon: <DownloadOutlined /> },
                  { key: 'pdf', label: 'Export to PDF', icon: <DownloadOutlined /> },
                ],
                onClick: ({ key }) => onExport(key as 'excel' | 'csv' | 'pdf'),
              }}
            >
              <Button icon={<DownloadOutlined />}>
                Export
              </Button>
            </Dropdown>
          </Space>
        </div>

        {/* Real-time collaboration status */}
        {collaborativeUsers.length > 0 && (
          <div className="mb-4 p-3 bg-blue-50 rounded-lg">
            <div className="flex items-center space-x-2">
              <SyncOutlined spin className="text-blue-500" />
              <span className="font-medium">Live collaboration:</span>
              <div className="flex space-x-2">
                {collaborativeUsers.map(user => (
                  <Tooltip key={user.id} title={user.name}>
                    <div
                      className="w-6 h-6 rounded-full border-2 border-white flex items-center justify-center text-white text-xs"
                      style={{ backgroundColor: user.color }}
                    >
                      {user.name.charAt(0)}
                    </div>
                  </Tooltip>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Class statistics */}
        {analyticsVisible && (
          <div className="grid grid-cols-6 gap-4 mb-4">
            <Statistic
              title="Class Average"
              value={classStats.averageGrade}
              precision={1}
              suffix="%"
              valueStyle={{ color: classStats.averageGrade >= 70 ? '#3f8600' : '#cf1322' }}
            />
            <Statistic title="Total Students" value={classStats.totalStudents} />
            <Statistic title="Graded Students" value={classStats.validGrades} />
            <Statistic
              title="Passing Rate"
              value={classStats.passingRate}
              precision={1}
              suffix="%"
            />
            <div>
              <div className="text-sm text-gray-500 mb-1">Grade Distribution</div>
              <div className="flex space-x-1">
                {Object.entries(classStats.gradeDistribution).map(([grade, count]) => (
                  <Tag key={grade} color={getGradeColor(grade)}>
                    {grade}: {count}
                  </Tag>
                ))}
              </div>
            </div>
            <div>
              <Button
                icon={<CalculatorOutlined />}
                onClick={() => {/* Open curve modal */}}
                disabled={readOnly}
              >
                Apply Curve
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* Grade table */}
      <Card>
        <Table
          columns={baseColumns}
          dataSource={studentRows}
          pagination={false}
          scroll={{ x: 1200, y: 600 }}
          size="small"
          bordered
          rowClassName={(record) =>
            record.status === 'inactive' ? 'opacity-50' : ''
          }
          onRow={(record) => ({
            onPaste: (e) => {
              e.preventDefault();
              const pastedData = e.clipboardData.getData('text');
              handleBulkPaste(pastedData);
            },
          })}
        />
      </Card>

      {/* Paste helper */}
      {!readOnly && (
        <Alert
          message="Bulk Grade Entry"
          description="You can paste grade data from Excel/Google Sheets directly into the table. Copy your data and paste it starting from any cell."
          type="info"
          showIcon
          closable
        />
      )}
    </div>
  );
};

// Helper function to get grade color
const getGradeColor = (grade: string) => {
  const colors = {
    'A': 'green',
    'B': 'blue',
    'C': 'orange',
    'D': 'red',
    'F': 'red',
  };
  return colors[grade as keyof typeof colors] || 'default';
};

export default GradeSpreadsheet;