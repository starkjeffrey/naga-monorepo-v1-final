/**
 * StudentCard Component
 *
 * A versatile student card component for displaying student information
 * in various layouts (list, grid, compact views).
 *
 * Features:
 * - Photo display with fallback
 * - Status indicators
 * - Quick actions
 * - Responsive design
 * - Accessibility compliant
 */

import React from 'react';
import { Card, Avatar, Tag, Button, Space, Tooltip, Badge } from 'antd';
import {
  UserOutlined,
  MailOutlined,
  PhoneOutlined,
  EyeOutlined,
  EditOutlined,
  MessageOutlined,
  IdcardOutlined,
} from '@ant-design/icons';
import type { Student } from '../types/Student';

interface StudentCardProps {
  student: Student;
  variant?: 'default' | 'compact' | 'detailed';
  actions?: boolean;
  selectable?: boolean;
  selected?: boolean;
  onSelect?: (student: Student) => void;
  onView?: (student: Student) => void;
  onEdit?: (student: Student) => void;
  onContact?: (student: Student, type: 'email' | 'phone' | 'message') => void;
  className?: string;
}

const getStatusColor = (status: string): string => {
  const statusColors: Record<string, string> = {
    active: 'green',
    inactive: 'red',
    graduated: 'blue',
    suspended: 'orange',
    transferred: 'purple',
    pending: 'gold',
  };
  return statusColors[status.toLowerCase()] || 'default';
};

const StudentCard: React.FC<StudentCardProps> = ({
  student,
  variant = 'default',
  actions = true,
  selectable = false,
  selected = false,
  onSelect,
  onView,
  onEdit,
  onContact,
  className,
}) => {
  const handleCardClick = () => {
    if (selectable && onSelect) {
      onSelect(student);
    }
  };

  const cardActions = actions ? [
    <Tooltip title="View Details" key="view">
      <Button
        type="text"
        icon={<EyeOutlined />}
        onClick={(e) => {
          e.stopPropagation();
          onView?.(student);
        }}
      />
    </Tooltip>,
    <Tooltip title="Edit Student" key="edit">
      <Button
        type="text"
        icon={<EditOutlined />}
        onClick={(e) => {
          e.stopPropagation();
          onEdit?.(student);
        }}
      />
    </Tooltip>,
    <Tooltip title="Send Email" key="email">
      <Button
        type="text"
        icon={<MailOutlined />}
        onClick={(e) => {
          e.stopPropagation();
          onContact?.(student, 'email');
        }}
      />
    </Tooltip>,
    <Tooltip title="Send Message" key="message">
      <Button
        type="text"
        icon={<MessageOutlined />}
        onClick={(e) => {
          e.stopPropagation();
          onContact?.(student, 'message');
        }}
      />
    </Tooltip>,
  ] : undefined;

  if (variant === 'compact') {
    return (
      <Card
        size="small"
        hoverable={selectable}
        className={`student-card-compact ${selected ? 'selected' : ''} ${className || ''}`}
        onClick={handleCardClick}
        style={{
          border: selected ? '2px solid #1890ff' : undefined,
          cursor: selectable ? 'pointer' : 'default',
        }}
      >
        <div className="flex items-center space-x-3">
          <Badge dot={student.hasAlerts} status={student.hasAlerts ? 'error' : 'default'}>
            <Avatar
              size={40}
              src={student.photoUrl}
              icon={<UserOutlined />}
              className="flex-shrink-0"
            />
          </Badge>
          <div className="flex-1 min-w-0">
            <div className="font-medium text-gray-900 truncate">
              {student.fullName}
            </div>
            <div className="text-sm text-gray-500 truncate">
              ID: {student.studentId} • {student.program}
            </div>
          </div>
          <Tag color={getStatusColor(student.status)} className="flex-shrink-0">
            {student.status}
          </Tag>
        </div>
      </Card>
    );
  }

  if (variant === 'detailed') {
    return (
      <Card
        hoverable={selectable}
        actions={cardActions}
        className={`student-card-detailed ${selected ? 'selected' : ''} ${className || ''}`}
        onClick={handleCardClick}
        style={{
          border: selected ? '2px solid #1890ff' : undefined,
          cursor: selectable ? 'pointer' : 'default',
        }}
        cover={
          <div className="p-4 bg-gradient-to-r from-blue-50 to-indigo-50">
            <div className="flex items-center space-x-4">
              <Badge dot={student.hasAlerts} status={student.hasAlerts ? 'error' : 'default'}>
                <Avatar
                  size={80}
                  src={student.photoUrl}
                  icon={<UserOutlined />}
                />
              </Badge>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-gray-900 mb-1">
                  {student.fullName}
                </h3>
                <div className="flex items-center space-x-2 mb-2">
                  <IdcardOutlined className="text-gray-400" />
                  <span className="text-gray-600">{student.studentId}</span>
                  <Tag color={getStatusColor(student.status)}>{student.status}</Tag>
                </div>
                <div className="text-sm text-gray-600">
                  {student.program} • {student.academicYear}
                </div>
              </div>
            </div>
          </div>
        }
      >
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-500">Email:</span>
              <div className="font-medium">{student.email}</div>
            </div>
            <div>
              <span className="text-gray-500">Phone:</span>
              <div className="font-medium">{student.phone || 'Not provided'}</div>
            </div>
            <div>
              <span className="text-gray-500">Enrollment Date:</span>
              <div className="font-medium">{student.enrollmentDate}</div>
            </div>
            <div>
              <span className="text-gray-500">GPA:</span>
              <div className="font-medium">{student.gpa || 'N/A'}</div>
            </div>
          </div>

          {student.emergencyContact && (
            <div className="p-3 bg-orange-50 rounded border-l-4 border-orange-200">
              <div className="text-sm font-medium text-orange-800">Emergency Contact</div>
              <div className="text-sm text-orange-700">
                {student.emergencyContact.name} - {student.emergencyContact.phone}
              </div>
            </div>
          )}

          {student.tags && student.tags.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {student.tags.map((tag, index) => (
                <Tag key={index} size="small">{tag}</Tag>
              ))}
            </div>
          )}
        </div>
      </Card>
    );
  }

  // Default variant
  return (
    <Card
      hoverable={selectable}
      actions={cardActions}
      className={`student-card-default ${selected ? 'selected' : ''} ${className || ''}`}
      onClick={handleCardClick}
      style={{
        border: selected ? '2px solid #1890ff' : undefined,
        cursor: selectable ? 'pointer' : 'default',
      }}
    >
      <Card.Meta
        avatar={
          <Badge dot={student.hasAlerts} status={student.hasAlerts ? 'error' : 'default'}>
            <Avatar
              size={64}
              src={student.photoUrl}
              icon={<UserOutlined />}
            />
          </Badge>
        }
        title={
          <div className="flex items-center justify-between">
            <span className="font-semibold">{student.fullName}</span>
            <Tag color={getStatusColor(student.status)}>{student.status}</Tag>
          </div>
        }
        description={
          <div className="space-y-2">
            <div className="flex items-center space-x-2 text-sm">
              <IdcardOutlined className="text-gray-400" />
              <span>ID: {student.studentId}</span>
            </div>
            <div className="text-sm text-gray-600">
              {student.program} • {student.academicYear}
            </div>
            <div className="flex items-center space-x-4 text-sm">
              {student.email && (
                <div className="flex items-center space-x-1">
                  <MailOutlined className="text-gray-400" />
                  <span className="truncate">{student.email}</span>
                </div>
              )}
              {student.phone && (
                <div className="flex items-center space-x-1">
                  <PhoneOutlined className="text-gray-400" />
                  <span>{student.phone}</span>
                </div>
              )}
            </div>
          </div>
        }
      />
    </Card>
  );
};

export default StudentCard;