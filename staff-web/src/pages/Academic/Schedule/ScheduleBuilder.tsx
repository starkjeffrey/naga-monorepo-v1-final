/**
 * DragDropScheduleBuilder Component
 *
 * Advanced drag-and-drop schedule builder with AI optimization:
 * - Drag-and-drop interface for schedule creation
 * - Real-time conflict detection and resolution
 * - Resource availability checking (rooms, equipment)
 * - Automated optimization suggestions
 * - Multiple scenario planning
 * - Integration with room booking system
 * - Instructor preference and availability management
 * - AI-powered schedule optimization
 */

import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import {
  Card,
  Button,
  Space,
  Alert,
  Modal,
  Form,
  Select,
  TimePicker,
  Input,
  Switch,
  Slider,
  Tag,
  Tooltip,
  Badge,
  Progress,
  Statistic,
  Tabs,
  Divider,
  notification,
  message,
} from 'antd';
import {
  CalendarOutlined,
  ClockCircleOutlined,
  RobotOutlined,
  ThunderboltOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  HomeOutlined,
  TeamOutlined,
  SaveOutlined,
  UndoOutlined,
  RedoOutlined,
  CopyOutlined,
  ShareAltOutlined,
  BarChartOutlined,
} from '@ant-design/icons';
import { DndProvider, useDrag, useDrop } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';
import dayjs from 'dayjs';

const { Option } = Select;
const { TabPane } = Tabs;

interface Course {
  id: string;
  code: string;
  name: string;
  credits: number;
  duration: number; // minutes
  instructorId: string;
  maxCapacity: number;
  requiredResources: string[];
  preferredTimeSlots: string[];
  frequency: 'weekly' | 'biweekly' | 'monthly';
  color: string;
}

interface Instructor {
  id: string;
  name: string;
  email: string;
  department: string;
  preferences: InstructorPreferences;
  availability: TimeSlot[];
  maxHoursPerWeek: number;
  currentHours: number;
}

interface InstructorPreferences {
  preferredDays: string[];
  preferredTimes: { start: string; end: string }[];
  avoidBackToBack: boolean;
  maxConsecutiveHours: number;
  lunchBreakRequired: boolean;
}

interface Room {
  id: string;
  name: string;
  building: string;
  capacity: number;
  resources: string[];
  availability: TimeSlot[];
  bookingBuffer: number; // minutes between bookings
}

interface TimeSlot {
  id: string;
  dayOfWeek: string;
  startTime: string;
  endTime: string;
  available: boolean;
  courseId?: string;
  roomId?: string;
  instructorId?: string;
}

interface ScheduleItem {
  id: string;
  courseId: string;
  instructorId: string;
  roomId: string;
  dayOfWeek: string;
  startTime: string;
  endTime: string;
  duration: number;
  conflicts: Conflict[];
  locked: boolean;
}

interface Conflict {
  type: 'room' | 'instructor' | 'time' | 'resource';
  severity: 'error' | 'warning' | 'info';
  message: string;
  suggestion?: string;
}

interface OptimizationResult {
  score: number;
  conflicts: number;
  utilizationRate: number;
  instructorSatisfaction: number;
  studentSatisfaction: number;
  suggestions: OptimizationSuggestion[];
}

interface OptimizationSuggestion {
  type: 'move' | 'swap' | 'split' | 'combine';
  scheduleItemId: string;
  suggestion: string;
  impact: number;
  effort: 'low' | 'medium' | 'high';
}

interface ScheduleBuilderProps {
  courses: Course[];
  instructors: Instructor[];
  rooms: Room[];
  existingSchedule: ScheduleItem[];
  onScheduleUpdate: (schedule: ScheduleItem[]) => Promise<void>;
  onOptimizeSchedule: (constraints: any) => Promise<OptimizationResult>;
  onSaveScenario: (name: string, schedule: ScheduleItem[]) => Promise<void>;
  onLoadScenario: (scenarioId: string) => Promise<ScheduleItem[]>;
  aiOptimizationEnabled?: boolean;
}

// Draggable course item
const DraggableCourse: React.FC<{
  course: Course;
  instructor: Instructor;
  onDragStart: () => void;
}> = ({ course, instructor, onDragStart }) => {
  const [{ isDragging }, drag] = useDrag(() => ({
    type: 'course',
    item: { course, instructor },
    collect: (monitor) => ({
      isDragging: monitor.isDragging(),
    }),
    begin: onDragStart,
  }));

  return (
    <div
      ref={drag}
      className={`p-3 mb-2 bg-white border rounded-lg cursor-move shadow-sm ${
        isDragging ? 'opacity-50' : ''
      }`}
      style={{ borderLeft: `4px solid ${course.color}` }}
    >
      <div className="flex justify-between items-start">
        <div>
          <div className="font-medium">{course.code}</div>
          <div className="text-sm text-gray-600">{course.name}</div>
          <div className="text-xs text-gray-500">
            {instructor.name} • {course.duration}min • {course.credits} credits
          </div>
        </div>
        <div className="text-right">
          <div className="text-xs text-gray-500">Cap: {course.maxCapacity}</div>
          {course.requiredResources.length > 0 && (
            <div className="text-xs text-blue-600">
              {course.requiredResources.join(', ')}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Droppable time slot
const TimeSlotCell: React.FC<{
  timeSlot: TimeSlot;
  scheduleItem?: ScheduleItem;
  onDrop: (item: any, timeSlot: TimeSlot) => void;
  onItemClick: (scheduleItem: ScheduleItem) => void;
  conflicts: Conflict[];
}> = ({ timeSlot, scheduleItem, onDrop, onItemClick, conflicts }) => {
  const [{ isOver, canDrop }, drop] = useDrop(() => ({
    accept: 'course',
    drop: (item) => onDrop(item, timeSlot),
    canDrop: () => timeSlot.available,
    collect: (monitor) => ({
      isOver: monitor.isOver(),
      canDrop: monitor.canDrop(),
    }),
  }));

  const hasConflicts = conflicts.length > 0;
  const hasErrors = conflicts.some(c => c.severity === 'error');

  return (
    <div
      ref={drop}
      className={`
        min-h-16 border border-gray-200 p-1 text-xs
        ${isOver && canDrop ? 'bg-blue-50 border-blue-300' : ''}
        ${!timeSlot.available ? 'bg-gray-50' : ''}
        ${hasConflicts ? (hasErrors ? 'bg-red-50' : 'bg-orange-50') : ''}
      `}
    >
      {scheduleItem && (
        <div
          className={`
            h-full p-2 rounded cursor-pointer
            ${scheduleItem.locked ? 'bg-gray-300' : 'bg-blue-100 hover:bg-blue-200'}
            ${hasErrors ? 'border border-red-300' : ''}
          `}
          style={{
            backgroundColor: scheduleItem.locked ? undefined :
              courses.find(c => c.id === scheduleItem.courseId)?.color + '20'
          }}
          onClick={() => onItemClick(scheduleItem)}
        >
          <div className="font-medium">
            {courses.find(c => c.id === scheduleItem.courseId)?.code}
          </div>
          <div className="text-xs text-gray-600">
            {instructors.find(i => i.id === scheduleItem.instructorId)?.name}
          </div>
          <div className="text-xs text-gray-500">
            {rooms.find(r => r.id === scheduleItem.roomId)?.name}
          </div>
          {hasConflicts && (
            <div className="mt-1">
              <Badge count={conflicts.length} size="small" />
            </div>
          )}
          {scheduleItem.locked && (
            <div className="absolute top-1 right-1">
              <Badge dot color="gray" />
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export const ScheduleBuilder: React.FC<ScheduleBuilderProps> = ({
  courses,
  instructors,
  rooms,
  existingSchedule,
  onScheduleUpdate,
  onOptimizeSchedule,
  onSaveScenario,
  onLoadScenario,
  aiOptimizationEnabled = true,
}) => {
  const [schedule, setSchedule] = useState<ScheduleItem[]>(existingSchedule);
  const [selectedItem, setSelectedItem] = useState<ScheduleItem | null>(null);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [optimizationModalVisible, setOptimizationModalVisible] = useState(false);
  const [conflicts, setConflicts] = useState<Map<string, Conflict[]>>(new Map());
  const [optimizationResult, setOptimizationResult] = useState<OptimizationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [currentView, setCurrentView] = useState<'week' | 'instructor' | 'room'>('week');
  const [selectedWeek, setSelectedWeek] = useState(dayjs().startOf('week'));
  const [undoStack, setUndoStack] = useState<ScheduleItem[][]>([]);
  const [redoStack, setRedoStack] = useState<ScheduleItem[][]>([]);

  const [form] = Form.useForm();

  // Time slots for the week view
  const timeSlots = useMemo(() => {
    const slots: TimeSlot[] = [];
    const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
    const times = [];

    // Generate time slots from 8 AM to 10 PM in 30-minute intervals
    for (let hour = 8; hour < 22; hour++) {
      for (let minute = 0; minute < 60; minute += 30) {
        times.push(`${hour.toString().padStart(2, '0')}:${minute.toString().padStart(2, '0')}`);
      }
    }

    days.forEach(day => {
      times.forEach(time => {
        const endTime = dayjs(`2024-01-01 ${time}`).add(30, 'minute').format('HH:mm');
        slots.push({
          id: `${day}-${time}`,
          dayOfWeek: day,
          startTime: time,
          endTime,
          available: true,
        });
      });
    });

    return slots;
  }, []);

  // Detect conflicts in schedule
  const detectConflicts = useCallback((scheduleItems: ScheduleItem[]) => {
    const conflictMap = new Map<string, Conflict[]>();

    scheduleItems.forEach(item => {
      const itemConflicts: Conflict[] = [];

      // Check room conflicts
      const roomConflicts = scheduleItems.filter(other =>
        other.id !== item.id &&
        other.roomId === item.roomId &&
        other.dayOfWeek === item.dayOfWeek &&
        ((other.startTime <= item.startTime && other.endTime > item.startTime) ||
         (other.startTime < item.endTime && other.endTime >= item.endTime) ||
         (other.startTime >= item.startTime && other.endTime <= item.endTime))
      );

      if (roomConflicts.length > 0) {
        itemConflicts.push({
          type: 'room',
          severity: 'error',
          message: `Room conflict with ${roomConflicts.length} other class(es)`,
          suggestion: 'Find alternative room or time slot',
        });
      }

      // Check instructor conflicts
      const instructorConflicts = scheduleItems.filter(other =>
        other.id !== item.id &&
        other.instructorId === item.instructorId &&
        other.dayOfWeek === item.dayOfWeek &&
        ((other.startTime <= item.startTime && other.endTime > item.startTime) ||
         (other.startTime < item.endTime && other.endTime >= item.endTime) ||
         (other.startTime >= item.startTime && other.endTime <= item.endTime))
      );

      if (instructorConflicts.length > 0) {
        itemConflicts.push({
          type: 'instructor',
          severity: 'error',
          message: `Instructor conflict with ${instructorConflicts.length} other class(es)`,
          suggestion: 'Assign different instructor or change time',
        });
      }

      // Check instructor preferences
      const instructor = instructors.find(i => i.id === item.instructorId);
      if (instructor) {
        if (!instructor.preferences.preferredDays.includes(item.dayOfWeek)) {
          itemConflicts.push({
            type: 'instructor',
            severity: 'warning',
            message: 'Outside instructor preferred days',
            suggestion: `Instructor prefers: ${instructor.preferences.preferredDays.join(', ')}`,
          });
        }

        const itemTime = dayjs(`2024-01-01 ${item.startTime}`);
        const isInPreferredTime = instructor.preferences.preferredTimes.some(pref => {
          const prefStart = dayjs(`2024-01-01 ${pref.start}`);
          const prefEnd = dayjs(`2024-01-01 ${pref.end}`);
          return itemTime.isBetween(prefStart, prefEnd, null, '[)');
        });

        if (!isInPreferredTime) {
          itemConflicts.push({
            type: 'time',
            severity: 'warning',
            message: 'Outside instructor preferred times',
            suggestion: 'Consider moving to preferred time slots',
          });
        }
      }

      // Check room capacity
      const room = rooms.find(r => r.id === item.roomId);
      const course = courses.find(c => c.id === item.courseId);
      if (room && course && room.capacity < course.maxCapacity) {
        itemConflicts.push({
          type: 'room',
          severity: 'warning',
          message: `Room capacity (${room.capacity}) less than course capacity (${course.maxCapacity})`,
          suggestion: 'Find larger room or split class',
        });
      }

      // Check required resources
      if (room && course) {
        const missingResources = course.requiredResources.filter(
          resource => !room.resources.includes(resource)
        );
        if (missingResources.length > 0) {
          itemConflicts.push({
            type: 'resource',
            severity: 'error',
            message: `Missing resources: ${missingResources.join(', ')}`,
            suggestion: 'Find room with required resources',
          });
        }
      }

      if (itemConflicts.length > 0) {
        conflictMap.set(item.id, itemConflicts);
      }
    });

    setConflicts(conflictMap);
  }, [courses, instructors, rooms]);

  // Update conflicts when schedule changes
  useEffect(() => {
    detectConflicts(schedule);
  }, [schedule, detectConflicts]);

  // Handle course drop
  const handleCourseDrop = useCallback((item: any, timeSlot: TimeSlot) => {
    const { course, instructor } = item;

    // Find suitable room
    const suitableRooms = rooms.filter(room =>
      room.capacity >= course.maxCapacity &&
      course.requiredResources.every(resource => room.resources.includes(resource))
    );

    if (suitableRooms.length === 0) {
      message.error('No suitable rooms available for this course');
      return;
    }

    const endTime = dayjs(`2024-01-01 ${timeSlot.startTime}`)
      .add(course.duration, 'minute')
      .format('HH:mm');

    const newScheduleItem: ScheduleItem = {
      id: `${course.id}-${timeSlot.dayOfWeek}-${timeSlot.startTime}`,
      courseId: course.id,
      instructorId: instructor.id,
      roomId: suitableRooms[0].id, // Use first suitable room
      dayOfWeek: timeSlot.dayOfWeek,
      startTime: timeSlot.startTime,
      endTime,
      duration: course.duration,
      conflicts: [],
      locked: false,
    };

    // Save current state for undo
    setUndoStack(prev => [...prev, schedule]);
    setRedoStack([]);

    setSchedule(prev => [...prev, newScheduleItem]);
    message.success(`Added ${course.code} to ${timeSlot.dayOfWeek} at ${timeSlot.startTime}`);
  }, [rooms, schedule]);

  // Handle item edit
  const handleItemEdit = (scheduleItem: ScheduleItem) => {
    setSelectedItem(scheduleItem);
    form.setFieldsValue({
      courseId: scheduleItem.courseId,
      instructorId: scheduleItem.instructorId,
      roomId: scheduleItem.roomId,
      dayOfWeek: scheduleItem.dayOfWeek,
      startTime: dayjs(`2024-01-01 ${scheduleItem.startTime}`),
      endTime: dayjs(`2024-01-01 ${scheduleItem.endTime}`),
      locked: scheduleItem.locked,
    });
    setEditModalVisible(true);
  };

  // Handle item update
  const handleItemUpdate = async (values: any) => {
    if (!selectedItem) return;

    const updatedItem: ScheduleItem = {
      ...selectedItem,
      courseId: values.courseId,
      instructorId: values.instructorId,
      roomId: values.roomId,
      dayOfWeek: values.dayOfWeek,
      startTime: values.startTime.format('HH:mm'),
      endTime: values.endTime.format('HH:mm'),
      duration: values.endTime.diff(values.startTime, 'minute'),
      locked: values.locked,
    };

    // Save current state for undo
    setUndoStack(prev => [...prev, schedule]);
    setRedoStack([]);

    setSchedule(prev =>
      prev.map(item => item.id === selectedItem.id ? updatedItem : item)
    );

    setEditModalVisible(false);
    setSelectedItem(null);
    message.success('Schedule item updated');
  };

  // Handle item deletion
  const handleItemDelete = (scheduleItem: ScheduleItem) => {
    Modal.confirm({
      title: 'Delete Schedule Item',
      content: 'Are you sure you want to delete this schedule item?',
      onOk: () => {
        // Save current state for undo
        setUndoStack(prev => [...prev, schedule]);
        setRedoStack([]);

        setSchedule(prev => prev.filter(item => item.id !== scheduleItem.id));
        message.success('Schedule item deleted');
      },
    });
  };

  // Handle AI optimization
  const handleOptimization = async (constraints: any) => {
    try {
      setLoading(true);
      const result = await onOptimizeSchedule(constraints);
      setOptimizationResult(result);

      notification.success({
        message: 'Optimization Complete',
        description: `Generated ${result.suggestions.length} optimization suggestions`,
      });
    } catch (error) {
      message.error('Failed to optimize schedule');
    } finally {
      setLoading(false);
    }
  };

  // Undo/Redo functionality
  const handleUndo = () => {
    if (undoStack.length > 0) {
      const previousState = undoStack[undoStack.length - 1];
      setRedoStack(prev => [schedule, ...prev]);
      setUndoStack(prev => prev.slice(0, -1));
      setSchedule(previousState);
    }
  };

  const handleRedo = () => {
    if (redoStack.length > 0) {
      const nextState = redoStack[0];
      setUndoStack(prev => [...prev, schedule]);
      setRedoStack(prev => prev.slice(1));
      setSchedule(nextState);
    }
  };

  // Calculate schedule statistics
  const scheduleStats = useMemo(() => {
    const totalCourses = schedule.length;
    const totalConflicts = Array.from(conflicts.values()).reduce((sum, c) => sum + c.length, 0);
    const errorConflicts = Array.from(conflicts.values())
      .flat()
      .filter(c => c.severity === 'error').length;

    const roomUtilization = rooms.map(room => {
      const roomSchedule = schedule.filter(item => item.roomId === room.id);
      const hoursUsed = roomSchedule.reduce((sum, item) => sum + item.duration, 0) / 60;
      const maxHours = 7 * 14; // 7 days * 14 hours per day
      return {
        roomId: room.id,
        roomName: room.name,
        utilization: (hoursUsed / maxHours) * 100,
      };
    });

    const avgRoomUtilization = roomUtilization.reduce((sum, r) => sum + r.utilization, 0) / roomUtilization.length;

    return {
      totalCourses,
      totalConflicts,
      errorConflicts,
      avgRoomUtilization,
      roomUtilization,
    };
  }, [schedule, conflicts, rooms]);

  // Render week view
  const renderWeekView = () => {
    const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
    const times = [];

    for (let hour = 8; hour < 22; hour++) {
      for (let minute = 0; minute < 60; minute += 30) {
        times.push(`${hour.toString().padStart(2, '0')}:${minute.toString().padStart(2, '0')}`);
      }
    }

    return (
      <div className="schedule-grid">
        <div className="grid grid-cols-8 gap-1">
          {/* Header row */}
          <div className="p-2 font-medium">Time</div>
          {days.map(day => (
            <div key={day} className="p-2 font-medium text-center bg-gray-50">
              {day}
            </div>
          ))}

          {/* Time slots */}
          {times.map(time => (
            <React.Fragment key={time}>
              <div className="p-2 text-sm text-gray-600 bg-gray-50">
                {time}
              </div>
              {days.map(day => {
                const timeSlot = timeSlots.find(
                  ts => ts.dayOfWeek === day && ts.startTime === time
                );
                const scheduleItem = schedule.find(
                  item => item.dayOfWeek === day && item.startTime === time
                );
                const itemConflicts = scheduleItem ? conflicts.get(scheduleItem.id) || [] : [];

                return (
                  <TimeSlotCell
                    key={`${day}-${time}`}
                    timeSlot={timeSlot!}
                    scheduleItem={scheduleItem}
                    onDrop={handleCourseDrop}
                    onItemClick={handleItemEdit}
                    conflicts={itemConflicts}
                  />
                );
              })}
            </React.Fragment>
          ))}
        </div>
      </div>
    );
  };

  // Render course palette
  const renderCoursePalette = () => {
    return (
      <Card title="Available Courses" size="small">
        <div className="max-h-96 overflow-y-auto">
          {courses.map(course => {
            const instructor = instructors.find(i => i.id === course.instructorId);
            return instructor ? (
              <DraggableCourse
                key={course.id}
                course={course}
                instructor={instructor}
                onDragStart={() => {}}
              />
            ) : null;
          })}
        </div>
      </Card>
    );
  };

  return (
    <DndProvider backend={HTML5Backend}>
      <div className="schedule-builder space-y-6">
        {/* Header */}
        <Card>
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-2xl font-bold">Schedule Builder</h2>
              <p className="text-gray-600">Drag and drop courses to build the optimal schedule</p>
            </div>

            <Space>
              <Button
                icon={<UndoOutlined />}
                onClick={handleUndo}
                disabled={undoStack.length === 0}
              >
                Undo
              </Button>

              <Button
                icon={<RedoOutlined />}
                onClick={handleRedo}
                disabled={redoStack.length === 0}
              >
                Redo
              </Button>

              <Button
                icon={<SaveOutlined />}
                onClick={() => onScheduleUpdate(schedule)}
              >
                Save
              </Button>

              {aiOptimizationEnabled && (
                <Button
                  type="primary"
                  icon={<RobotOutlined />}
                  onClick={() => setOptimizationModalVisible(true)}
                >
                  AI Optimize
                </Button>
              )}
            </Space>
          </div>
        </Card>

        {/* Statistics */}
        <Card>
          <div className="grid grid-cols-4 gap-4">
            <Statistic
              title="Total Classes"
              value={scheduleStats.totalCourses}
              prefix={<CalendarOutlined />}
            />
            <Statistic
              title="Conflicts"
              value={scheduleStats.totalConflicts}
              prefix={<WarningOutlined />}
              valueStyle={{ color: scheduleStats.errorConflicts > 0 ? '#ff4d4f' : '#faad14' }}
            />
            <Statistic
              title="Error Conflicts"
              value={scheduleStats.errorConflicts}
              prefix={<ExclamationCircleOutlined />}
              valueStyle={{ color: scheduleStats.errorConflicts > 0 ? '#ff4d4f' : '#52c41a' }}
            />
            <Statistic
              title="Room Utilization"
              value={scheduleStats.avgRoomUtilization}
              suffix="%"
              precision={1}
              prefix={<HomeOutlined />}
              valueStyle={{
                color: scheduleStats.avgRoomUtilization >= 70 ? '#52c41a' : '#faad14'
              }}
            />
          </div>
        </Card>

        {/* Main content */}
        <div className="grid grid-cols-4 gap-6">
          {/* Course palette */}
          <div className="col-span-1">
            {renderCoursePalette()}
          </div>

          {/* Schedule grid */}
          <div className="col-span-3">
            <Card
              title="Weekly Schedule"
              extra={
                <Space>
                  <Select value={currentView} onChange={setCurrentView}>
                    <Option value="week">Week View</Option>
                    <Option value="instructor">Instructor View</Option>
                    <Option value="room">Room View</Option>
                  </Select>
                </Space>
              }
            >
              {renderWeekView()}
            </Card>
          </div>
        </div>

        {/* Edit Modal */}
        <Modal
          title="Edit Schedule Item"
          open={editModalVisible}
          onCancel={() => setEditModalVisible(false)}
          onOk={() => form.submit()}
          width={600}
        >
          <Form
            form={form}
            layout="vertical"
            onFinish={handleItemUpdate}
          >
            <div className="grid grid-cols-2 gap-4">
              <Form.Item name="courseId" label="Course" rules={[{ required: true }]}>
                <Select>
                  {courses.map(course => (
                    <Option key={course.id} value={course.id}>
                      {course.code} - {course.name}
                    </Option>
                  ))}
                </Select>
              </Form.Item>

              <Form.Item name="instructorId" label="Instructor" rules={[{ required: true }]}>
                <Select>
                  {instructors.map(instructor => (
                    <Option key={instructor.id} value={instructor.id}>
                      {instructor.name}
                    </Option>
                  ))}
                </Select>
              </Form.Item>

              <Form.Item name="roomId" label="Room" rules={[{ required: true }]}>
                <Select>
                  {rooms.map(room => (
                    <Option key={room.id} value={room.id}>
                      {room.name} ({room.capacity} capacity)
                    </Option>
                  ))}
                </Select>
              </Form.Item>

              <Form.Item name="dayOfWeek" label="Day" rules={[{ required: true }]}>
                <Select>
                  {['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'].map(day => (
                    <Option key={day} value={day}>{day}</Option>
                  ))}
                </Select>
              </Form.Item>

              <Form.Item name="startTime" label="Start Time" rules={[{ required: true }]}>
                <TimePicker format="HH:mm" />
              </Form.Item>

              <Form.Item name="endTime" label="End Time" rules={[{ required: true }]}>
                <TimePicker format="HH:mm" />
              </Form.Item>

              <Form.Item name="locked" valuePropName="checked" className="col-span-2">
                <Switch checkedChildren="Locked" unCheckedChildren="Unlocked" />
              </Form.Item>
            </div>

            {selectedItem && (
              <div className="mt-4">
                <Button
                  danger
                  onClick={() => handleItemDelete(selectedItem)}
                >
                  Delete Schedule Item
                </Button>
              </div>
            )}
          </Form>
        </Modal>

        {/* AI Optimization Modal */}
        <Modal
          title="AI Schedule Optimization"
          open={optimizationModalVisible}
          onCancel={() => setOptimizationModalVisible(false)}
          onOk={() => {
            // Implement optimization with current constraints
            handleOptimization({
              prioritizeInstructorPreferences: true,
              minimizeConflicts: true,
              maximizeRoomUtilization: true,
            });
            setOptimizationModalVisible(false);
          }}
          width={800}
        >
          <div className="space-y-6">
            <Alert
              message="AI-Powered Schedule Optimization"
              description="Our AI will analyze your current schedule and provide optimization suggestions to minimize conflicts and improve efficiency."
              type="info"
              showIcon
            />

            {optimizationResult && (
              <Card title="Optimization Results">
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <Statistic
                    title="Optimization Score"
                    value={optimizationResult.score}
                    suffix="/100"
                  />
                  <Statistic
                    title="Conflicts Resolved"
                    value={optimizationResult.conflicts}
                  />
                </div>

                <div className="space-y-3">
                  <h4 className="font-medium">Suggestions:</h4>
                  {optimizationResult.suggestions.map((suggestion, index) => (
                    <Card key={index} size="small">
                      <div className="flex justify-between items-start">
                        <div>
                          <Tag color={suggestion.effort === 'low' ? 'green' : suggestion.effort === 'medium' ? 'orange' : 'red'}>
                            {suggestion.effort.toUpperCase()} EFFORT
                          </Tag>
                          <span className="ml-2">{suggestion.suggestion}</span>
                        </div>
                        <div className="text-right">
                          <div className="font-medium">+{suggestion.impact} points</div>
                          <Button size="small" type="primary">
                            Apply
                          </Button>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              </Card>
            )}
          </div>
        </Modal>
      </div>
    </DndProvider>
  );
};

export default ScheduleBuilder;