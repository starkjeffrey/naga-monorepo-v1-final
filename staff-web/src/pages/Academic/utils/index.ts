/**
 * Academic Module Utilities
 *
 * Comprehensive utility functions for academic management system
 * including grade calculations, schedule conflict detection, and AI recommendations.
 */

import dayjs from 'dayjs';
import type {
  Grade,
  Assignment,
  Course,
  Student,
  Instructor,
  TimeSlot,
  ScheduleItem,
  Room,
  Conflict,
  ConflictResolution,
  OptimizationResult,
  OptimizationSuggestion,
  AIRecommendation,
  ScheduleConflict,
  CourseSchedule,
} from '../types';

// ============================================================================
// Grade Calculation Utilities
// ============================================================================

/**
 * Calculate letter grade from percentage
 */
export const calculateLetterGrade = (percentage: number): string => {
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

/**
 * Calculate weighted grade based on assignment categories
 */
export const calculateWeightedGrade = (
  grades: Array<{ assignment: Assignment; points: number; maxPoints: number }>
): number => {
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

/**
 * Calculate GPA from letter grades
 */
export const calculateGPA = (letterGrades: string[], credits: number[]): number => {
  const gradePoints: { [key: string]: number } = {
    'A+': 4.0, 'A': 4.0, 'A-': 3.7,
    'B+': 3.3, 'B': 3.0, 'B-': 2.7,
    'C+': 2.3, 'C': 2.0, 'C-': 1.7,
    'D+': 1.3, 'D': 1.0, 'D-': 0.7,
    'F': 0.0,
  };

  let totalPoints = 0;
  let totalCredits = 0;

  letterGrades.forEach((grade, index) => {
    const credit = credits[index] || 0;
    const points = gradePoints[grade] || 0;
    totalPoints += points * credit;
    totalCredits += credit;
  });

  return totalCredits > 0 ? totalPoints / totalCredits : 0;
};

/**
 * Apply grade curve to a set of scores
 */
export const applyGradeCurve = (
  scores: number[],
  curveType: 'linear' | 'sqrt' | 'bell' | 'none',
  targetAverage: number = 85
): number[] => {
  if (curveType === 'none' || scores.length === 0) return scores;

  const currentAverage = scores.reduce((sum, score) => sum + score, 0) / scores.length;

  switch (curveType) {
    case 'linear':
      const adjustment = targetAverage - currentAverage;
      return scores.map(score => Math.min(100, Math.max(0, score + adjustment)));

    case 'sqrt':
      return scores.map(score => Math.min(100, Math.sqrt(score / 100) * 100));

    case 'bell':
      const stdDev = Math.sqrt(
        scores.reduce((sum, score) => sum + Math.pow(score - currentAverage, 2), 0) / scores.length
      );
      return scores.map(score => {
        const zScore = (score - currentAverage) / stdDev;
        return Math.min(100, Math.max(0, targetAverage + (zScore * 10)));
      });

    default:
      return scores;
  }
};

/**
 * Detect grade anomalies (outliers, unusual patterns)
 */
export const detectGradeAnomalies = (
  grades: Grade[],
  assignments: Assignment[]
): Array<{ type: string; description: string; gradeIds: string[] }> => {
  const anomalies: Array<{ type: string; description: string; gradeIds: string[] }> = [];

  // Group grades by student
  const studentGrades = new Map<string, Grade[]>();
  grades.forEach(grade => {
    if (!studentGrades.has(grade.studentId)) {
      studentGrades.set(grade.studentId, []);
    }
    studentGrades.get(grade.studentId)!.push(grade);
  });

  // Detect sudden drops in performance
  studentGrades.forEach((studentGradeList, studentId) => {
    const sortedGrades = studentGradeList
      .filter(g => g.percentage !== null)
      .sort((a, b) => new Date(a.lastModified).getTime() - new Date(b.lastModified).getTime());

    for (let i = 1; i < sortedGrades.length; i++) {
      const current = sortedGrades[i].percentage!;
      const previous = sortedGrades[i - 1].percentage!;

      if (previous - current > 20) { // 20+ point drop
        anomalies.push({
          type: 'sudden_drop',
          description: `Student ${studentId} dropped ${(previous - current).toFixed(1)}% from previous assignment`,
          gradeIds: [sortedGrades[i].id],
        });
      }
    }
  });

  // Detect consistently low performers
  studentGrades.forEach((studentGradeList, studentId) => {
    const validGrades = studentGradeList.filter(g => g.percentage !== null);
    if (validGrades.length >= 3) {
      const average = validGrades.reduce((sum, g) => sum + g.percentage!, 0) / validGrades.length;
      if (average < 60) {
        anomalies.push({
          type: 'consistently_low',
          description: `Student ${studentId} has average of ${average.toFixed(1)}% across ${validGrades.length} assignments`,
          gradeIds: validGrades.map(g => g.id),
        });
      }
    }
  });

  return anomalies;
};

// ============================================================================
// Schedule Conflict Detection
// ============================================================================

/**
 * Detect schedule conflicts between courses
 */
export const detectScheduleConflicts = (
  courses: Course[],
  instructors: Instructor[],
  rooms: Room[]
): ScheduleConflict[] => {
  const conflicts: ScheduleConflict[] = [];

  // Check for time overlaps between courses
  for (let i = 0; i < courses.length; i++) {
    for (let j = i + 1; j < courses.length; j++) {
      const course1 = courses[i];
      const course2 = courses[j];

      course1.schedule.forEach(schedule1 => {
        course2.schedule.forEach(schedule2 => {
          if (isTimeOverlap(schedule1, schedule2)) {
            // Room conflict
            if (schedule1.room === schedule2.room && schedule1.building === schedule2.building) {
              conflicts.push({
                type: 'room',
                description: `Room ${schedule1.room} in ${schedule1.building} is double-booked`,
                severity: 'high',
                affectedCount: course1.currentEnrollment + course2.currentEnrollment,
                resolutionSuggestions: [
                  'Move one course to a different room',
                  'Change the time slot for one course',
                  'Split the course into multiple sections',
                ],
              });
            }

            // Instructor conflict
            const sharedInstructors = course1.instructors.filter(inst1 =>
              course2.instructors.some(inst2 => inst1.id === inst2.id)
            );

            if (sharedInstructors.length > 0) {
              conflicts.push({
                type: 'instructor',
                description: `Instructor ${sharedInstructors[0].name} has overlapping classes`,
                severity: 'high',
                affectedCount: course1.currentEnrollment + course2.currentEnrollment,
                resolutionSuggestions: [
                  'Assign a different instructor',
                  'Change the time slot for one course',
                  'Combine the courses if appropriate',
                ],
              });
            }
          }
        });
      });
    }
  }

  return conflicts;
};

/**
 * Check if two time slots overlap
 */
const isTimeOverlap = (schedule1: CourseSchedule, schedule2: CourseSchedule): boolean => {
  if (schedule1.dayOfWeek !== schedule2.dayOfWeek) return false;

  const start1 = dayjs(`2000-01-01 ${schedule1.startTime}`);
  const end1 = dayjs(`2000-01-01 ${schedule1.endTime}`);
  const start2 = dayjs(`2000-01-01 ${schedule2.startTime}`);
  const end2 = dayjs(`2000-01-01 ${schedule2.endTime}`);

  return start1.isBefore(end2) && start2.isBefore(end1);
};

/**
 * Check instructor availability for a time slot
 */
export const checkInstructorAvailability = (
  instructor: Instructor,
  timeSlot: TimeSlot
): boolean => {
  return instructor.availability.some(availableSlot =>
    availableSlot.dayOfWeek === timeSlot.dayOfWeek &&
    dayjs(`2000-01-01 ${availableSlot.startTime}`).isSameOrBefore(dayjs(`2000-01-01 ${timeSlot.startTime}`)) &&
    dayjs(`2000-01-01 ${availableSlot.endTime}`).isSameOrAfter(dayjs(`2000-01-01 ${timeSlot.endTime}`))
  );
};

/**
 * Check room availability for a time slot
 */
export const checkRoomAvailability = (
  room: Room,
  timeSlot: TimeSlot
): boolean => {
  return room.availability.some(availableSlot =>
    availableSlot.dayOfWeek === timeSlot.dayOfWeek &&
    dayjs(`2000-01-01 ${availableSlot.startTime}`).isSameOrBefore(dayjs(`2000-01-01 ${timeSlot.startTime}`)) &&
    dayjs(`2000-01-01 ${availableSlot.endTime}`).isSameOrAfter(dayjs(`2000-01-01 ${timeSlot.endTime}`)) &&
    availableSlot.available
  );
};

// ============================================================================
// Schedule Optimization
// ============================================================================

/**
 * Optimize schedule using AI algorithms
 */
export const optimizeSchedule = (
  courses: Course[],
  instructors: Instructor[],
  rooms: Room[],
  constraints: {
    minimizeConflicts: boolean;
    maximizeRoomUtilization: boolean;
    respectInstructorPreferences: boolean;
    optimizeStudentSchedules: boolean;
  }
): OptimizationResult => {
  // This is a simplified optimization algorithm
  // In a real implementation, this would use more sophisticated algorithms

  let score = 0;
  const suggestions: OptimizationSuggestion[] = [];

  // Analyze current conflicts
  const conflicts = detectScheduleConflicts(courses, instructors, rooms);
  const conflictsResolved = conflicts.length;

  // Calculate room utilization
  const roomUtilization = calculateRoomUtilization(courses, rooms);
  const utilizationImproved = roomUtilization.averageUtilization;

  // Instructor satisfaction (based on preferences)
  const instructorSatisfaction = calculateInstructorSatisfaction(courses, instructors);

  // Generate optimization suggestions
  if (conflicts.length > 0) {
    suggestions.push({
      type: 'reschedule',
      description: `Reschedule ${conflicts.length} conflicting courses`,
      impact: `Eliminate all scheduling conflicts`,
      confidence: 85,
      effort: 'medium',
      implementation: 'Move courses to available time slots',
    });
  }

  if (roomUtilization.averageUtilization < 70) {
    suggestions.push({
      type: 'move',
      description: 'Consolidate courses to fewer rooms',
      impact: `Increase room utilization by ${(70 - roomUtilization.averageUtilization).toFixed(1)}%`,
      confidence: 75,
      effort: 'low',
      implementation: 'Move courses from underutilized rooms to busier ones',
    });
  }

  // Calculate overall score
  score = (
    (conflictsResolved === 0 ? 25 : Math.max(0, 25 - conflicts.length * 5)) +
    (utilizationImproved * 0.25) +
    (instructorSatisfaction * 0.25) +
    25 // Base score
  );

  return {
    id: `optimization_${Date.now()}`,
    score: Math.min(100, score),
    conflictsResolved,
    utilizationImproved,
    instructorSatisfaction,
    studentSatisfaction: 75, // Would be calculated based on student preferences
    suggestions,
  };
};

/**
 * Calculate room utilization statistics
 */
const calculateRoomUtilization = (
  courses: Course[],
  rooms: Room[]
): { averageUtilization: number; roomStats: { [roomId: string]: number } } => {
  const roomStats: { [roomId: string]: number } = {};

  rooms.forEach(room => {
    const roomCourses = courses.filter(course =>
      course.schedule.some(schedule =>
        schedule.room === room.name && schedule.building === room.building
      )
    );

    const totalHours = roomCourses.reduce((sum, course) => {
      return sum + course.schedule.reduce((courseSum, schedule) => {
        const start = dayjs(`2000-01-01 ${schedule.startTime}`);
        const end = dayjs(`2000-01-01 ${schedule.endTime}`);
        return courseSum + end.diff(start, 'hour');
      }, 0);
    }, 0);

    // Assume 60 hours per week maximum utilization (12 hours * 5 days)
    roomStats[room.id] = Math.min(100, (totalHours / 60) * 100);
  });

  const averageUtilization = Object.values(roomStats).reduce((sum, util) => sum + util, 0) / rooms.length;

  return { averageUtilization, roomStats };
};

/**
 * Calculate instructor satisfaction based on preferences
 */
const calculateInstructorSatisfaction = (
  courses: Course[],
  instructors: Instructor[]
): number => {
  let totalSatisfaction = 0;

  instructors.forEach(instructor => {
    const instructorCourses = courses.filter(course =>
      course.instructors.some(inst => inst.id === instructor.id)
    );

    let satisfaction = 100; // Start with perfect satisfaction

    instructorCourses.forEach(course => {
      course.schedule.forEach(schedule => {
        // Check if day is preferred
        if (!instructor.preferences.preferredDays.includes(schedule.dayOfWeek)) {
          satisfaction -= 10;
        }

        // Check if time is preferred
        const scheduleTime = dayjs(`2000-01-01 ${schedule.startTime}`);
        const timePreferred = instructor.preferences.preferredTimes.some(pref => {
          const prefStart = dayjs(`2000-01-01 ${pref.start}`);
          const prefEnd = dayjs(`2000-01-01 ${pref.end}`);
          return scheduleTime.isSameOrAfter(prefStart) && scheduleTime.isSameOrBefore(prefEnd);
        });

        if (!timePreferred) {
          satisfaction -= 15;
        }
      });
    });

    totalSatisfaction += Math.max(0, satisfaction);
  });

  return instructors.length > 0 ? totalSatisfaction / instructors.length : 0;
};

// ============================================================================
// AI Recommendation Generation
// ============================================================================

/**
 * Generate AI-powered recommendations for academic improvement
 */
export const generateAIRecommendations = (
  context: {
    courses: Course[];
    students: Student[];
    grades: Grade[];
    enrollments: any[];
    historicalData?: any;
  }
): AIRecommendation[] => {
  const recommendations: AIRecommendation[] = [];

  // Analyze enrollment patterns
  const enrollmentRecommendations = analyzeEnrollmentPatterns(context.courses, context.enrollments);
  recommendations.push(...enrollmentRecommendations);

  // Analyze grade patterns
  const gradeRecommendations = analyzeGradePatterns(context.grades, context.students);
  recommendations.push(...gradeRecommendations);

  // Analyze course performance
  const courseRecommendations = analyzeCoursePerformance(context.courses, context.grades);
  recommendations.push(...courseRecommendations);

  // Sort by impact and confidence
  return recommendations.sort((a, b) => {
    const scoreA = getRecommendationScore(a);
    const scoreB = getRecommendationScore(b);
    return scoreB - scoreA;
  });
};

/**
 * Analyze enrollment patterns and generate recommendations
 */
const analyzeEnrollmentPatterns = (courses: Course[], enrollments: any[]): AIRecommendation[] => {
  const recommendations: AIRecommendation[] = [];

  courses.forEach(course => {
    const utilizationRate = (course.currentEnrollment / course.maxCapacity) * 100;

    // Low enrollment recommendation
    if (utilizationRate < 50) {
      recommendations.push({
        type: 'enrollment',
        title: 'Low Enrollment Alert',
        description: `${course.code} is at ${utilizationRate.toFixed(0)}% capacity. Consider marketing or schedule adjustments.`,
        confidence: 85,
        impact: 'medium',
        action: 'Review marketing strategy',
        createdAt: new Date().toISOString(),
        implemented: false,
      });
    }

    // High waitlist recommendation
    if (course.waitlistCount > course.maxCapacity * 0.2) {
      recommendations.push({
        type: 'capacity',
        title: 'High Demand Course',
        description: `${course.code} has ${course.waitlistCount} students on waitlist. Consider adding sections.`,
        confidence: 95,
        impact: 'high',
        action: 'Increase capacity',
        createdAt: new Date().toISOString(),
        implemented: false,
      });
    }
  });

  return recommendations;
};

/**
 * Analyze grade patterns and generate recommendations
 */
const analyzeGradePatterns = (grades: Grade[], students: Student[]): AIRecommendation[] => {
  const recommendations: AIRecommendation[] = [];

  // Group grades by student
  const studentGrades = new Map<string, Grade[]>();
  grades.forEach(grade => {
    if (!studentGrades.has(grade.studentId)) {
      studentGrades.set(grade.studentId, []);
    }
    studentGrades.get(grade.studentId)!.push(grade);
  });

  // Identify at-risk students
  studentGrades.forEach((studentGradeList, studentId) => {
    const validGrades = studentGradeList.filter(g => g.percentage !== null);
    if (validGrades.length >= 2) {
      const average = validGrades.reduce((sum, g) => sum + g.percentage!, 0) / validGrades.length;

      if (average < 70) {
        const student = students.find(s => s.id === studentId);
        recommendations.push({
          type: 'performance',
          title: 'At-Risk Student Identified',
          description: `${student?.name || studentId} has an average of ${average.toFixed(1)}%. Consider intervention.`,
          confidence: 80,
          impact: 'high',
          action: 'Schedule academic support meeting',
          data: { studentId, average },
          createdAt: new Date().toISOString(),
          implemented: false,
        });
      }
    }
  });

  return recommendations;
};

/**
 * Analyze course performance and generate recommendations
 */
const analyzeCoursePerformance = (courses: Course[], grades: Grade[]): AIRecommendation[] => {
  const recommendations: AIRecommendation[] = [];

  courses.forEach(course => {
    const courseGrades = grades.filter(g => {
      // This would need to be properly linked through enrollments
      // For now, we'll use a simplified approach
      return true; // Placeholder
    });

    if (course.successRate < 70) {
      recommendations.push({
        type: 'performance',
        title: 'Low Success Rate Course',
        description: `${course.code} has a success rate of ${course.successRate}%. Review curriculum and teaching methods.`,
        confidence: 75,
        impact: 'medium',
        action: 'Review course content',
        createdAt: new Date().toISOString(),
        implemented: false,
      });
    }
  });

  return recommendations;
};

/**
 * Calculate recommendation score for sorting
 */
const getRecommendationScore = (recommendation: AIRecommendation): number => {
  const impactWeight = { low: 1, medium: 2, high: 3 };
  return recommendation.confidence * impactWeight[recommendation.impact];
};

// ============================================================================
// Validation Utilities
// ============================================================================

/**
 * Validate prerequisite requirements
 */
export const validatePrerequisites = (
  course: Course,
  studentCourses: string[]
): { valid: boolean; missing: string[]; errors: string[] } => {
  const missing: string[] = [];
  const errors: string[] = [];

  course.prerequisites.forEach(prereq => {
    if (!studentCourses.includes(prereq)) {
      missing.push(prereq);
    }
  });

  if (missing.length > 0) {
    errors.push(`Missing prerequisites: ${missing.join(', ')}`);
  }

  return {
    valid: missing.length === 0,
    missing,
    errors,
  };
};

/**
 * Validate schedule conflicts for a student
 */
export const validateStudentSchedule = (
  newCourse: Course,
  existingCourses: Course[]
): { valid: boolean; conflicts: string[]; warnings: string[] } => {
  const conflicts: string[] = [];
  const warnings: string[] = [];

  existingCourses.forEach(existingCourse => {
    newCourse.schedule.forEach(newSchedule => {
      existingCourse.schedule.forEach(existingSchedule => {
        if (isTimeOverlap(newSchedule, existingSchedule)) {
          conflicts.push(
            `Time conflict with ${existingCourse.code} on ${newSchedule.dayOfWeek} at ${newSchedule.startTime}`
          );
        }
      });
    });
  });

  return {
    valid: conflicts.length === 0,
    conflicts,
    warnings,
  };
};

// ============================================================================
// Export all utilities
// ============================================================================

export {
  // Grade utilities
  calculateLetterGrade,
  calculateWeightedGrade,
  calculateGPA,
  applyGradeCurve,
  detectGradeAnomalies,

  // Schedule utilities
  detectScheduleConflicts,
  checkInstructorAvailability,
  checkRoomAvailability,
  optimizeSchedule,

  // AI utilities
  generateAIRecommendations,

  // Validation utilities
  validatePrerequisites,
  validateStudentSchedule,
};