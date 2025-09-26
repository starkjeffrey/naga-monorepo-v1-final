/**
 * Student Management Module Index
 *
 * Comprehensive student management system with 8 main components:
 * - Enhanced Student List with DataGrid pattern
 * - Student Detail Modal with 360° view
 * - Student Creation Wizard with multi-step form
 * - Advanced Student Search with multiple modes
 * - Student Locator with maps and quick access
 * - Student Enrollment Management with TransferList
 * - Student Analytics Dashboard with AI predictions
 * - Bulk Operations Center for mass operations
 */

// Main student list page
export { default as StudentListPage } from './StudentList';

// Student detail modal
export { default as StudentDetail } from './StudentDetail';

// Student creation wizard
export { default as StudentCreate } from './StudentCreate';

// Advanced search functionality
export { default as StudentSearch } from './StudentSearch';

// Student locator and quick access
export { default as StudentLocator } from './StudentLocator';

// Enrollment management
export { default as StudentEnrollment } from './StudentEnrollment';

// Analytics and reporting
export { default as StudentAnalytics } from './StudentAnalytics';

// Bulk operations center
export { default as BulkOperations } from './BulkOperations';

// Export patterns for reuse
export * from '../../components/patterns';