/**
 * Student Management Components Index
 *
 * Centralized export for all shared student components.
 * These components are designed to be reusable across
 * the student management module.
 */

export { default as StudentCard } from './StudentCard';
export { default as StudentPhoto } from './StudentPhoto';
export { default as StudentTimeline } from './StudentTimeline';
export { default as StudentForm } from './StudentForm';
export { default as StudentStats } from './StudentStats';

// Re-export types for convenience
export type { Student, StudentEvent, StudentFormData, StudentStatistics } from '../types/Student';