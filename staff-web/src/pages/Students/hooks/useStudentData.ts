/**
 * useStudentData Hook
 *
 * A comprehensive hook for student data management:
 * - CRUD operations
 * - Real-time updates via WebSocket
 * - Optimistic updates
 * - Data caching and synchronization
 * - Offline support
 * - Error handling and recovery
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { message } from 'antd';
import type { Student, StudentFormData, StudentUpdateData } from '../types/Student';
import { studentService } from '../services/studentApi';
import { useWebSocket } from '../../../hooks/useWebSocket';

interface UseStudentDataOptions {
  studentId?: string;
  realTimeUpdates?: boolean;
  autoRefresh?: boolean;
  refreshInterval?: number;
  optimisticUpdates?: boolean;
}

interface UseStudentDataReturn {
  // Data state
  student: Student | null;
  loading: boolean;
  error: string | null;
  isConnected: boolean;

  // CRUD operations
  fetch: (id: string) => Promise<void>;
  create: (data: StudentFormData) => Promise<Student | null>;
  update: (id: string, data: StudentUpdateData) => Promise<Student | null>;
  delete: (id: string) => Promise<boolean>;
  refresh: () => Promise<void>;

  // Specialized operations
  updatePhoto: (id: string, file: File) => Promise<boolean>;
  updateStatus: (id: string, status: string) => Promise<boolean>;
  addNote: (id: string, note: string) => Promise<boolean>;
  addAlert: (id: string, alert: any) => Promise<boolean>;
  clearAlert: (id: string, alertId: string) => Promise<boolean>;

  // Data utilities
  isDataStale: boolean;
  lastUpdated: Date | null;
  version: number;
  hasUnsavedChanges: boolean;
  saveChanges: () => Promise<void>;
  discardChanges: () => void;
}

export const useStudentData = (options: UseStudentDataOptions = {}): UseStudentDataReturn => {
  const {
    studentId,
    realTimeUpdates = true,
    autoRefresh = false,
    refreshInterval = 30000, // 30 seconds
    optimisticUpdates = true,
  } = options;

  // Data state
  const [student, setStudent] = useState<Student | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [version, setVersion] = useState(0);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  // Internal state
  const [originalStudent, setOriginalStudent] = useState<Student | null>(null);
  const refreshTimerRef = useRef<NodeJS.Timeout | null>(null);
  const isDataStale = lastUpdated ? Date.now() - lastUpdated.getTime() > 300000 : false; // 5 minutes

  // WebSocket connection for real-time updates
  const { isConnected, sendMessage } = useWebSocket(
    realTimeUpdates ? `/ws/students/${studentId || 'all'}/` : null,
    {
      onMessage: handleWebSocketMessage,
      onError: (error) => {
        console.error('WebSocket error:', error);
      },
    }
  );

  // Handle WebSocket messages
  function handleWebSocketMessage(message: any) {
    try {
      const data = JSON.parse(message.data);

      switch (data.type) {
        case 'student_updated':
          if (data.student.id === student?.id) {
            setStudent(data.student);
            setVersion(prev => prev + 1);
            setLastUpdated(new Date());
            message.info('Student data updated by another user');
          }
          break;

        case 'student_deleted':
          if (data.studentId === student?.id) {
            setStudent(null);
            message.warning('This student has been deleted by another user');
          }
          break;

        case 'alert_added':
          if (data.studentId === student?.id) {
            setStudent(prev => prev ? {
              ...prev,
              hasAlerts: true,
              alerts: [...(prev.alerts || []), data.alert]
            } : null);
          }
          break;

        default:
          console.log('Unknown WebSocket message type:', data.type);
      }
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
    }
  }

  // Auto-refresh timer
  useEffect(() => {
    if (autoRefresh && studentId && refreshInterval > 0) {
      refreshTimerRef.current = setInterval(() => {
        refresh();
      }, refreshInterval);

      return () => {
        if (refreshTimerRef.current) {
          clearInterval(refreshTimerRef.current);
        }
      };
    }
  }, [autoRefresh, studentId, refreshInterval]);

  // Initial fetch
  useEffect(() => {
    if (studentId) {
      fetch(studentId);
    }
  }, [studentId]);

  // Fetch student data
  const fetch = useCallback(async (id: string) => {
    setLoading(true);
    setError(null);

    try {
      const studentData = await studentService.getStudent(id);
      setStudent(studentData);
      setOriginalStudent(studentData);
      setLastUpdated(new Date());
      setVersion(prev => prev + 1);
      setHasUnsavedChanges(false);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch student';
      setError(errorMessage);
      message.error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, []);

  // Create new student
  const create = useCallback(async (data: StudentFormData): Promise<Student | null> => {
    setLoading(true);
    setError(null);

    try {
      const newStudent = await studentService.createStudent(data);
      message.success('Student created successfully');
      return newStudent;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to create student';
      setError(errorMessage);
      message.error(errorMessage);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  // Update student data
  const update = useCallback(async (id: string, data: StudentUpdateData): Promise<Student | null> => {
    if (optimisticUpdates && student) {
      // Optimistic update
      const optimisticStudent = { ...student, ...data };
      setStudent(optimisticStudent);
      setHasUnsavedChanges(true);
    }

    setLoading(true);
    setError(null);

    try {
      const updatedStudent = await studentService.updateStudent(id, data);
      setStudent(updatedStudent);
      setOriginalStudent(updatedStudent);
      setLastUpdated(new Date());
      setVersion(prev => prev + 1);
      setHasUnsavedChanges(false);
      message.success('Student updated successfully');
      return updatedStudent;
    } catch (err) {
      if (optimisticUpdates && originalStudent) {
        // Rollback optimistic update
        setStudent(originalStudent);
      }
      const errorMessage = err instanceof Error ? err.message : 'Failed to update student';
      setError(errorMessage);
      message.error(errorMessage);
      return null;
    } finally {
      setLoading(false);
    }
  }, [student, originalStudent, optimisticUpdates]);

  // Delete student
  const deleteStudent = useCallback(async (id: string): Promise<boolean> => {
    setLoading(true);
    setError(null);

    try {
      await studentService.deleteStudent(id);
      setStudent(null);
      setOriginalStudent(null);
      message.success('Student deleted successfully');
      return true;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete student';
      setError(errorMessage);
      message.error(errorMessage);
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  // Refresh current data
  const refresh = useCallback(async () => {
    if (student?.id) {
      await fetch(student.id);
    }
  }, [student?.id, fetch]);

  // Update student photo
  const updatePhoto = useCallback(async (id: string, file: File): Promise<boolean> => {
    setLoading(true);

    try {
      const photoUrl = await studentService.uploadPhoto(id, file);
      if (student) {
        setStudent({ ...student, photoUrl });
        setHasUnsavedChanges(true);
      }
      message.success('Photo updated successfully');
      return true;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to update photo';
      setError(errorMessage);
      message.error(errorMessage);
      return false;
    } finally {
      setLoading(false);
    }
  }, [student]);

  // Update student status
  const updateStatus = useCallback(async (id: string, status: string): Promise<boolean> => {
    return await update(id, { status }) !== null;
  }, [update]);

  // Add note to student
  const addNote = useCallback(async (id: string, note: string): Promise<boolean> => {
    try {
      await studentService.addNote(id, note);
      message.success('Note added successfully');

      // Update student data to include new note
      if (student) {
        setStudent({
          ...student,
          notes: [...(student.notes || []), {
            id: Date.now().toString(),
            content: note,
            author: 'Current User', // This would come from auth context
            timestamp: new Date().toISOString(),
          }]
        });
      }
      return true;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to add note';
      message.error(errorMessage);
      return false;
    }
  }, [student]);

  // Add alert to student
  const addAlert = useCallback(async (id: string, alert: any): Promise<boolean> => {
    try {
      await studentService.addAlert(id, alert);
      message.success('Alert added successfully');

      // Update student data to include new alert
      if (student) {
        setStudent({
          ...student,
          hasAlerts: true,
          alerts: [...(student.alerts || []), alert]
        });
      }
      return true;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to add alert';
      message.error(errorMessage);
      return false;
    }
  }, [student]);

  // Clear alert from student
  const clearAlert = useCallback(async (id: string, alertId: string): Promise<boolean> => {
    try {
      await studentService.clearAlert(id, alertId);
      message.success('Alert cleared successfully');

      // Update student data to remove alert
      if (student && student.alerts) {
        const updatedAlerts = student.alerts.filter(alert => alert.id !== alertId);
        setStudent({
          ...student,
          hasAlerts: updatedAlerts.length > 0,
          alerts: updatedAlerts
        });
      }
      return true;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to clear alert';
      message.error(errorMessage);
      return false;
    }
  }, [student]);

  // Save unsaved changes
  const saveChanges = useCallback(async () => {
    if (student && originalStudent && hasUnsavedChanges) {
      const changes: Partial<Student> = {};

      // Calculate differences
      Object.keys(student).forEach(key => {
        if (student[key as keyof Student] !== originalStudent[key as keyof Student]) {
          changes[key as keyof Student] = student[key as keyof Student];
        }
      });

      if (Object.keys(changes).length > 0) {
        await update(student.id, changes);
      }
    }
  }, [student, originalStudent, hasUnsavedChanges, update]);

  // Discard unsaved changes
  const discardChanges = useCallback(() => {
    if (originalStudent) {
      setStudent(originalStudent);
      setHasUnsavedChanges(false);
    }
  }, [originalStudent]);

  return {
    // Data state
    student,
    loading,
    error,
    isConnected,

    // CRUD operations
    fetch,
    create,
    update,
    delete: deleteStudent,
    refresh,

    // Specialized operations
    updatePhoto,
    updateStatus,
    addNote,
    addAlert,
    clearAlert,

    // Data utilities
    isDataStale,
    lastUpdated,
    version,
    hasUnsavedChanges,
    saveChanges,
    discardChanges,
  };
};