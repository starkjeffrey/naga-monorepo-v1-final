/**
 * useStudentAnalytics Hook
 *
 * A comprehensive hook for student analytics and insights:
 * - AI-powered predictions and recommendations
 * - Performance trend analysis
 * - Risk assessment and early warning systems
 * - Comparative analytics with cohorts
 * - Real-time metric updates
 * - Custom dashboard configuration
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { message } from 'antd';
import type {
  Student,
  StudentAnalytics,
  StudentPrediction,
  StudentRiskAssessment,
  AnalyticsTimeframe,
  AnalyticsMetric,
} from '../types/Student';
import { studentService } from '../services/studentApi';

interface UseStudentAnalyticsOptions {
  studentId?: string;
  timeframe?: AnalyticsTimeframe;
  enablePredictions?: boolean;
  enableRiskAssessment?: boolean;
  enableComparisons?: boolean;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

interface UseStudentAnalyticsReturn {
  // Analytics data
  analytics: StudentAnalytics | null;
  predictions: StudentPrediction | null;
  riskAssessment: StudentRiskAssessment | null;
  loading: boolean;
  error: string | null;

  // Data operations
  fetchAnalytics: (studentId: string, timeframe?: AnalyticsTimeframe) => Promise<void>;
  fetchPredictions: (studentId: string) => Promise<void>;
  fetchRiskAssessment: (studentId: string) => Promise<void>;
  refreshAll: () => Promise<void>;

  // Comparative analytics
  compareWithCohort: (studentId: string, cohortType: 'program' | 'year' | 'gpa') => Promise<void>;
  cohortComparison: any | null;

  // Insight generation
  generateInsights: (studentId: string) => Promise<string[]>;
  insights: string[];

  // Metric utilities
  getMetricTrend: (metric: AnalyticsMetric) => 'up' | 'down' | 'stable';
  getMetricValue: (metric: AnalyticsMetric) => number | null;
  getMetricChange: (metric: AnalyticsMetric) => number | null;

  // Configuration
  timeframe: AnalyticsTimeframe;
  setTimeframe: (timeframe: AnalyticsTimeframe) => void;
  enabledFeatures: {
    predictions: boolean;
    riskAssessment: boolean;
    comparisons: boolean;
  };
}

export const useStudentAnalytics = (options: UseStudentAnalyticsOptions = {}): UseStudentAnalyticsReturn => {
  const {
    studentId,
    timeframe: initialTimeframe = 'semester',
    enablePredictions = true,
    enableRiskAssessment = true,
    enableComparisons = true,
    autoRefresh = false,
    refreshInterval = 60000, // 1 minute
  } = options;

  // Analytics state
  const [analytics, setAnalytics] = useState<StudentAnalytics | null>(null);
  const [predictions, setPredictions] = useState<StudentPrediction | null>(null);
  const [riskAssessment, setRiskAssessment] = useState<StudentRiskAssessment | null>(null);
  const [cohortComparison, setCohortComparison] = useState<any | null>(null);
  const [insights, setInsights] = useState<string[]>([]);

  // UI state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [timeframe, setTimeframe] = useState<AnalyticsTimeframe>(initialTimeframe);

  // Auto-refresh timer
  useEffect(() => {
    if (autoRefresh && studentId && refreshInterval > 0) {
      const timer = setInterval(() => {
        refreshAll();
      }, refreshInterval);

      return () => clearInterval(timer);
    }
  }, [autoRefresh, studentId, refreshInterval]);

  // Initial data fetch
  useEffect(() => {
    if (studentId) {
      fetchAnalytics(studentId, timeframe);
      if (enablePredictions) {
        fetchPredictions(studentId);
      }
      if (enableRiskAssessment) {
        fetchRiskAssessment(studentId);
      }
    }
  }, [studentId, timeframe, enablePredictions, enableRiskAssessment]);

  // Fetch analytics data
  const fetchAnalytics = useCallback(async (id: string, tf: AnalyticsTimeframe = timeframe) => {
    setLoading(true);
    setError(null);

    try {
      const analyticsData = await studentService.getStudentAnalytics(id, tf);
      setAnalytics(analyticsData);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch analytics';
      setError(errorMessage);
      message.error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [timeframe]);

  // Fetch AI predictions
  const fetchPredictions = useCallback(async (id: string) => {
    try {
      const predictionData = await studentService.getStudentPredictions(id);
      setPredictions(predictionData);
    } catch (err) {
      console.error('Failed to fetch predictions:', err);
      // Don't show error message for predictions as they're supplementary
    }
  }, []);

  // Fetch risk assessment
  const fetchRiskAssessment = useCallback(async (id: string) => {
    try {
      const riskData = await studentService.getStudentRiskAssessment(id);
      setRiskAssessment(riskData);
    } catch (err) {
      console.error('Failed to fetch risk assessment:', err);
      // Don't show error message for risk assessment as it's supplementary
    }
  }, []);

  // Refresh all data
  const refreshAll = useCallback(async () => {
    if (studentId) {
      await Promise.all([
        fetchAnalytics(studentId),
        enablePredictions ? fetchPredictions(studentId) : Promise.resolve(),
        enableRiskAssessment ? fetchRiskAssessment(studentId) : Promise.resolve(),
      ]);
    }
  }, [studentId, fetchAnalytics, fetchPredictions, fetchRiskAssessment, enablePredictions, enableRiskAssessment]);

  // Compare with cohort
  const compareWithCohort = useCallback(async (id: string, cohortType: 'program' | 'year' | 'gpa') => {
    setLoading(true);

    try {
      const comparisonData = await studentService.compareWithCohort(id, cohortType);
      setCohortComparison(comparisonData);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch cohort comparison';
      message.error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, []);

  // Generate AI insights
  const generateInsights = useCallback(async (id: string): Promise<string[]> => {
    try {
      const insightsData = await studentService.generateInsights(id);
      setInsights(insightsData);
      return insightsData;
    } catch (err) {
      console.error('Failed to generate insights:', err);
      return [];
    }
  }, []);

  // Get metric trend
  const getMetricTrend = useCallback((metric: AnalyticsMetric): 'up' | 'down' | 'stable' => {
    if (!analytics?.trends) return 'stable';

    const trend = analytics.trends[metric];
    if (!trend || trend.change === 0) return 'stable';
    return trend.change > 0 ? 'up' : 'down';
  }, [analytics]);

  // Get metric value
  const getMetricValue = useCallback((metric: AnalyticsMetric): number | null => {
    if (!analytics?.metrics) return null;
    return analytics.metrics[metric]?.current || null;
  }, [analytics]);

  // Get metric change
  const getMetricChange = useCallback((metric: AnalyticsMetric): number | null => {
    if (!analytics?.trends) return null;
    return analytics.trends[metric]?.change || null;
  }, [analytics]);

  // Computed enabled features
  const enabledFeatures = useMemo(() => ({
    predictions: enablePredictions,
    riskAssessment: enableRiskAssessment,
    comparisons: enableComparisons,
  }), [enablePredictions, enableRiskAssessment, enableComparisons]);

  // Update timeframe and refetch data
  const handleTimeframeChange = useCallback((newTimeframe: AnalyticsTimeframe) => {
    setTimeframe(newTimeframe);
    if (studentId) {
      fetchAnalytics(studentId, newTimeframe);
    }
  }, [studentId, fetchAnalytics]);

  return {
    // Analytics data
    analytics,
    predictions,
    riskAssessment,
    loading,
    error,

    // Data operations
    fetchAnalytics,
    fetchPredictions,
    fetchRiskAssessment,
    refreshAll,

    // Comparative analytics
    compareWithCohort,
    cohortComparison,

    // Insight generation
    generateInsights,
    insights,

    // Metric utilities
    getMetricTrend,
    getMetricValue,
    getMetricChange,

    // Configuration
    timeframe,
    setTimeframe: handleTimeframeChange,
    enabledFeatures,
  };
};