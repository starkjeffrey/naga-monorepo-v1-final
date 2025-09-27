/**
 * GradeCell Component
 *
 * Individual grade cell with real-time collaboration features for the grade spreadsheet.
 * Supports live editing, conflict resolution, and user presence indicators.
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { InputNumber, Tooltip, Button } from 'antd';
import {
  LockOutlined,
  UnlockOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  EditOutlined,
  SaveOutlined,
} from '@ant-design/icons';
import type { GradeCell as GradeCellType, CollaborativeUser } from '../types';

interface GradeCellProps {
  cell: GradeCellType;
  maxPoints: number;
  readOnly?: boolean;
  collaborative?: boolean;
  collaborativeUsers?: CollaborativeUser[];
  onValueChange: (value: number | null) => void;
  onSave: () => Promise<void>;
  onFocus: () => void;
  onBlur: () => void;
  allowPartialCredit?: boolean;
  className?: string;
}

export const GradeCell: React.FC<GradeCellProps> = ({
  cell,
  maxPoints,
  readOnly = false,
  collaborative = false,
  collaborativeUsers = [],
  onValueChange,
  onSave,
  onFocus,
  onBlur,
  allowPartialCredit = true,
  className = '',
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [value, setValue] = useState<number | null>(cell.value);
  const [isSaving, setIsSaving] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // Update value when cell prop changes
  useEffect(() => {
    setValue(cell.value);
  }, [cell.value]);

  // Handle focus
  const handleFocus = useCallback(() => {
    if (readOnly || cell.isLocked) return;
    setIsEditing(true);
    onFocus();
  }, [readOnly, cell.isLocked, onFocus]);

  // Handle blur
  const handleBlur = useCallback(() => {
    setIsEditing(false);
    onBlur();
  }, [onBlur]);

  // Handle value change
  const handleValueChange = useCallback((newValue: number | null) => {
    setValue(newValue);
    onValueChange(newValue);
  }, [onValueChange]);

  // Handle save
  const handleSave = useCallback(async () => {
    if (isSaving) return;

    setIsSaving(true);
    try {
      await onSave();
    } finally {
      setIsSaving(false);
      setIsEditing(false);
    }
  }, [isSaving, onSave]);

  // Handle keyboard shortcuts
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSave();
    } else if (e.key === 'Escape') {
      setValue(cell.value);
      setIsEditing(false);
      onBlur();
    }
  }, [cell.value, handleSave, onBlur]);

  // Find active collaborative users for this cell
  const activeCellUsers = collaborativeUsers.filter(user =>
    user.cursor?.studentId === cell.studentId &&
    user.cursor?.assignmentId === cell.assignmentId &&
    user.isOnline
  );

  // Calculate percentage
  const percentage = value && maxPoints > 0 ? (value / maxPoints) * 100 : 0;

  // Determine cell status
  const getCellStatus = () => {
    if (cell.hasConflict) return 'conflict';
    if (cell.isLocked) return 'locked';
    if (isSaving) return 'saving';
    if (isEditing) return 'editing';
    if (value === null) return 'empty';
    return 'normal';
  };

  const status = getCellStatus();

  // Get cell styling based on status
  const getCellClassName = () => {
    const baseClass = 'grade-cell relative';
    const statusClasses = {
      conflict: 'border-red-500 bg-red-50',
      locked: 'border-orange-500 bg-orange-50',
      saving: 'border-blue-500 bg-blue-50',
      editing: 'border-green-500 bg-green-50',
      empty: 'border-gray-300 bg-gray-50',
      normal: 'border-gray-300 bg-white',
    };

    return `${baseClass} ${statusClasses[status]} ${className}`;
  };

  // Get tooltip content
  const getTooltipContent = () => {
    const content = [];

    if (cell.hasConflict) {
      content.push('⚠️ Conflict detected - another user has modified this grade');
    }

    if (cell.isLocked && cell.editingBy) {
      content.push(`🔒 Locked by ${cell.editingBy}`);
    }

    if (value !== null) {
      content.push(`Score: ${value}/${maxPoints} (${percentage.toFixed(1)}%)`);
    }

    if (cell.lastSaved) {
      const lastSaved = new Date(cell.lastSaved).toLocaleString();
      content.push(`Last saved: ${lastSaved}`);
    }

    if (activeCellUsers.length > 0) {
      const userNames = activeCellUsers.map(u => u.name).join(', ');
      content.push(`👥 ${userNames} viewing`);
    }

    return content.length > 0 ? content.join('\n') : 'Click to edit grade';
  };

  return (
    <div className={getCellClassName()}>
      {/* Main input */}
      <InputNumber
        ref={inputRef}
        value={value}
        min={0}
        max={maxPoints}
        precision={allowPartialCredit ? 1 : 0}
        size="small"
        disabled={readOnly || cell.isLocked || isSaving}
        className="w-full border-0 shadow-none bg-transparent"
        controls={false}
        onChange={handleValueChange}
        onFocus={handleFocus}
        onBlur={handleBlur}
        onKeyDown={handleKeyDown}
        placeholder="--"
        style={{
          color: value === null ? '#ccc' : percentage >= 60 ? '#52c41a' : '#ff4d4f',
        }}
      />

      {/* Status indicators */}
      <div className="absolute top-0 right-0 flex space-x-1 p-1">
        {/* Conflict indicator */}
        {cell.hasConflict && (
          <Tooltip title="Grade conflict detected">
            <WarningOutlined className="text-red-500 text-xs" />
          </Tooltip>
        )}

        {/* Lock indicator */}
        {cell.isLocked && (
          <Tooltip title={`Locked by ${cell.editingBy}`}>
            <LockOutlined className="text-orange-500 text-xs" />
          </Tooltip>
        )}

        {/* Saving indicator */}
        {isSaving && (
          <Tooltip title="Saving...">
            <SaveOutlined className="text-blue-500 text-xs animate-spin" />
          </Tooltip>
        )}

        {/* Saved indicator */}
        {!isSaving && !isEditing && value !== null && !cell.hasConflict && (
          <Tooltip title="Saved">
            <CheckCircleOutlined className="text-green-500 text-xs" />
          </Tooltip>
        )}
      </div>

      {/* Collaborative user indicators */}
      {collaborative && activeCellUsers.length > 0 && (
        <div className="absolute -top-2 -right-2 flex space-x-1">
          {activeCellUsers.slice(0, 3).map(user => (
            <Tooltip key={user.id} title={`${user.name} is here`}>
              <div
                className="w-4 h-4 rounded-full border-2 border-white shadow-lg flex items-center justify-center text-white text-xs font-bold"
                style={{ backgroundColor: user.color }}
              >
                {user.name.charAt(0).toUpperCase()}
              </div>
            </Tooltip>
          ))}
          {activeCellUsers.length > 3 && (
            <Tooltip title={`+${activeCellUsers.length - 3} more users`}>
              <div className="w-4 h-4 rounded-full border-2 border-white bg-gray-500 shadow-lg flex items-center justify-center text-white text-xs font-bold">
                +{activeCellUsers.length - 3}
              </div>
            </Tooltip>
          )}
        </div>
      )}

      {/* Percentage indicator */}
      {value !== null && maxPoints > 0 && (
        <div className="absolute bottom-0 left-0 right-0 h-1 bg-gray-200 rounded-b">
          <div
            className={`h-full rounded-b transition-all duration-300 ${
              percentage >= 90 ? 'bg-green-500' :
              percentage >= 80 ? 'bg-blue-500' :
              percentage >= 70 ? 'bg-yellow-500' :
              percentage >= 60 ? 'bg-orange-500' : 'bg-red-500'
            }`}
            style={{ width: `${Math.min(100, percentage)}%` }}
          />
        </div>
      )}

      {/* Hover tooltip */}
      <Tooltip
        title={getTooltipContent()}
        placement="top"
        overlayStyle={{ whiteSpace: 'pre-line' }}
      >
        <div className="absolute inset-0" />
      </Tooltip>
    </div>
  );
};

export default GradeCell;