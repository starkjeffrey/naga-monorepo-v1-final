/**
 * useFinancialAnalytics Hook
 * AI-powered financial analytics with predictive insights and real-time monitoring
 */

import { useState, useCallback, useEffect, useMemo } from 'react';
import { useToast } from '../../../hooks/use-toast';
import { financeService } from '../../../services/financeService';
import {
  FinancialMetrics,
  MonthlyTrend,
  RevenueSource,
  PaymentPrediction,
  FinancialReportParams,
  InvoiceFilters,
  PaymentFilters
} from '../../../types/finance.types';
import { forecastRevenue, calculateBudgetVariance, generateReportId } from '../../../utils/financeUtils';

interface AnalyticsFilters {
  dateRange: {
    start: string;
    end: string;
  };
  groupBy?: 'day' | 'week' | 'month' | 'quarter';
  includeForecasts?: boolean;
  includePredictions?: boolean;
}

interface AnalyticsState {
  loading: boolean;
  error: string | null;
  lastUpdated: string | null;
  metrics: FinancialMetrics | null;
  trends: MonthlyTrend[];
  revenueSources: RevenueSource[];
  predictions: PaymentPrediction[];
  forecasts: Array<{ month: string; forecast: number; confidence: number }>;
  budgetVariance: {
    variance: number;
    percentageVariance: number;
    status: 'over' | 'under' | 'on-track';
  } | null;
}

interface AnalyticsInsights {
  keyInsights: string[];
  riskFactors: string[];
  opportunities: string[];
  recommendations: string[];
}

export const useFinancialAnalytics = (filters: AnalyticsFilters) => {
  const { toast } = useToast();
  const [state, setState] = useState<AnalyticsState>({
    loading: false,
    error: null,
    lastUpdated: null,
    metrics: null,
    trends: [],
    revenueSources: [],
    predictions: [],
    forecasts: [],
    budgetVariance: null
  });

  const [refreshInterval, setRefreshInterval] = useState<number>(300000); // 5 minutes default
  const [autoRefresh, setAutoRefresh] = useState(true);

  // Memoized insights based on current data
  const insights = useMemo((): AnalyticsInsights => {
    const keyInsights: string[] = [];
    const riskFactors: string[] = [];
    const opportunities: string[] = [];
    const recommendations: string[] = [];

    if (!state.metrics) {
      return { keyInsights, riskFactors, opportunities, recommendations };
    }

    const { metrics, trends, predictions, budgetVariance } = state;

    // Collection rate analysis
    if (metrics.collection_rate >= 95) {
      keyInsights.push(`Excellent collection rate of ${metrics.collection_rate.toFixed(1)}%`);
    } else if (metrics.collection_rate < 85) {
      riskFactors.push(`Low collection rate of ${metrics.collection_rate.toFixed(1)}%`);
      recommendations.push('Implement automated payment reminders to improve collections');
    }

    // Outstanding balance analysis
    const outstandingRatio = metrics.outstanding_balance / metrics.total_revenue;
    if (outstandingRatio > 0.3) {
      riskFactors.push('High outstanding balance ratio indicates cash flow concerns');
      recommendations.push('Consider offering payment plans to reduce outstanding balances');
    }

    // Trend analysis
    if (trends.length >= 2) {
      const latestTrend = trends[trends.length - 1];
      const previousTrend = trends[trends.length - 2];
      const revenueGrowth = ((latestTrend.revenue - previousTrend.revenue) / previousTrend.revenue) * 100;

      if (revenueGrowth > 10) {
        keyInsights.push(`Strong revenue growth of ${revenueGrowth.toFixed(1)}% this month`);
        opportunities.push('Scale successful revenue streams');
      } else if (revenueGrowth < -5) {
        riskFactors.push(`Revenue declined by ${Math.abs(revenueGrowth).toFixed(1)}% this month`);
        recommendations.push('Investigate causes of revenue decline and implement corrective measures');
      }
    }

    // Payment predictions analysis
    const highRiskPayments = predictions.filter(p => p.probability < 0.7);
    if (highRiskPayments.length > 0) {
      riskFactors.push(`${highRiskPayments.length} payments at risk of default`);
      recommendations.push('Proactively contact students with high-risk payment predictions');
    }

    // Budget variance analysis
    if (budgetVariance) {
      if (budgetVariance.status === 'over' && budgetVariance.percentageVariance > 10) {
        opportunities.push(`Revenue exceeds budget by ${budgetVariance.percentageVariance.toFixed(1)}%`);
      } else if (budgetVariance.status === 'under' && budgetVariance.percentageVariance < -10) {
        riskFactors.push(`Revenue below budget by ${Math.abs(budgetVariance.percentageVariance).toFixed(1)}%`);
        recommendations.push('Review budget assumptions and implement revenue recovery strategies');
      }
    }

    // Seasonal patterns
    const avgPaymentTime = metrics.average_payment_time;
    if (avgPaymentTime > 45) {
      riskFactors.push(`Average payment time of ${avgPaymentTime} days is concerning`);
      recommendations.push('Implement early payment incentives to reduce payment delays');
    }

    return { keyInsights, riskFactors, opportunities, recommendations };
  }, [state.metrics, state.trends, state.predictions, state.budgetVariance]);

  // Load financial metrics
  const loadMetrics = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null }));

    try {
      const response = await financeService.getFinancialMetrics(
        filters.dateRange.start,
        filters.dateRange.end,
        filters.groupBy
      );

      if (response.success) {
        setState(prev => ({
          ...prev,
          metrics: response.data,
          lastUpdated: new Date().toISOString()
        }));
      }
    } catch (error: any) {
      setState(prev => ({
        ...prev,
        error: error.message || 'Failed to load financial metrics'
      }));
    }
  }, [filters.dateRange.start, filters.dateRange.end, filters.groupBy]);

  // Load trend data
  const loadTrends = useCallback(async () => {
    if (!state.metrics) return;

    try {
      // Use the monthly trends from metrics if available
      if (state.metrics.monthly_trends) {
        setState(prev => ({ ...prev, trends: state.metrics!.monthly_trends }));
      }
    } catch (error: any) {
      console.error('Failed to load trend data:', error);
    }
  }, [state.metrics]);

  // Load revenue sources
  const loadRevenueSources = useCallback(async () => {
    if (!state.metrics) return;

    try {
      // Use the revenue sources from metrics if available
      if (state.metrics.top_revenue_sources) {
        setState(prev => ({ ...prev, revenueSources: state.metrics!.top_revenue_sources }));
      }
    } catch (error: any) {
      console.error('Failed to load revenue sources:', error);
    }
  }, [state.metrics]);

  // Load payment predictions
  const loadPredictions = useCallback(async () => {
    if (!filters.includePredictions) return;

    try {
      const response = await financeService.getPaymentPredictions();
      if (response.success) {
        setState(prev => ({ ...prev, predictions: response.data }));
      }
    } catch (error: any) {
      console.error('Failed to load payment predictions:', error);
    }
  }, [filters.includePredictions]);

  // Generate forecasts
  const generateForecasts = useCallback(async () => {
    if (!filters.includeForecasts || state.trends.length < 3) return;

    try {
      const historicalData = state.trends.map(trend => ({
        month: trend.month,
        revenue: trend.revenue
      }));

      const forecasts = forecastRevenue(historicalData, 6); // 6 month forecast
      setState(prev => ({ ...prev, forecasts }));
    } catch (error: any) {
      console.error('Failed to generate forecasts:', error);
    }
  }, [filters.includeForecasts, state.trends]);

  // Calculate budget variance
  const calculateVariance = useCallback(async (budgetAmount: number) => {
    if (!state.metrics) return;

    try {
      const variance = calculateBudgetVariance(state.metrics.total_revenue, budgetAmount);
      setState(prev => ({ ...prev, budgetVariance: variance }));
    } catch (error: any) {
      console.error('Failed to calculate budget variance:', error);
    }
  }, [state.metrics]);

  // Generate comprehensive report
  const generateReport = useCallback(async (reportParams: FinancialReportParams): Promise<string | null> => {
    try {
      setState(prev => ({ ...prev, loading: true }));

      const response = await financeService.generateReport(reportParams);

      if (response.success) {
        const reportId = generateReportId();

        toast({
          title: "Report Generated",
          description: `Financial report ${reportId} has been generated successfully.`,
        });

        return reportId;
      }

      return null;
    } catch (error: any) {
      toast({
        title: "Report Generation Failed",
        description: error.message || 'Failed to generate report',
        variant: "destructive"
      });
      return null;
    } finally {
      setState(prev => ({ ...prev, loading: false }));
    }
  }, [toast]);

  // Export analytics data
  const exportData = useCallback(async (format: 'csv' | 'excel' | 'pdf' = 'csv'): Promise<Blob | null> => {
    try {
      setState(prev => ({ ...prev, loading: true }));

      const data = await financeService.exportData('analytics', {
        dateRange: filters.dateRange,
        groupBy: filters.groupBy
      }, format);

      toast({
        title: "Export Complete",
        description: `Analytics data exported as ${format.toUpperCase()}.`,
      });

      return data;
    } catch (error: any) {
      toast({
        title: "Export Failed",
        description: error.message || 'Failed to export data',
        variant: "destructive"
      });
      return null;
    } finally {
      setState(prev => ({ ...prev, loading: false }));
    }
  }, [filters.dateRange, filters.groupBy, toast]);

  // Refresh all analytics data
  const refreshAll = useCallback(async () => {
    await Promise.all([
      loadMetrics(),
      loadPredictions()
    ]);
  }, [loadMetrics, loadPredictions]);

  // Set up auto-refresh
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(refreshAll, refreshInterval);
    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, refreshAll]);

  // Load dependent data when metrics change
  useEffect(() => {
    if (state.metrics) {
      loadTrends();
      loadRevenueSources();
      generateForecasts();
    }
  }, [state.metrics, loadTrends, loadRevenueSources, generateForecasts]);

  // Initial data load
  useEffect(() => {
    refreshAll();
  }, [filters.dateRange.start, filters.dateRange.end, filters.groupBy]);

  // Real-time alerts for significant changes
  useEffect(() => {
    if (state.metrics && state.lastUpdated) {
      const collectionRate = state.metrics.collection_rate;

      if (collectionRate < 80) {
        toast({
          title: "Collection Rate Alert",
          description: `Collection rate has dropped to ${collectionRate.toFixed(1)}%. Immediate attention required.`,
          variant: "destructive"
        });
      }

      const outstandingRatio = state.metrics.outstanding_balance / state.metrics.total_revenue;
      if (outstandingRatio > 0.4) {
        toast({
          title: "Cash Flow Warning",
          description: "Outstanding balance ratio is concerning. Review payment collection strategies.",
          variant: "destructive"
        });
      }
    }
  }, [state.metrics, state.lastUpdated, toast]);

  // Performance metrics
  const performanceMetrics = useMemo(() => {
    if (!state.metrics) return null;

    return {
      revenuePercentile: state.metrics.collection_rate >= 95 ? 'Excellent' :
                        state.metrics.collection_rate >= 85 ? 'Good' :
                        state.metrics.collection_rate >= 75 ? 'Fair' : 'Poor',

      trendsDirection: state.trends.length >= 2 ?
        (state.trends[state.trends.length - 1].revenue > state.trends[state.trends.length - 2].revenue ? 'up' : 'down') :
        'stable',

      riskLevel: state.predictions.length > 0 ?
        (state.predictions.filter(p => p.probability < 0.7).length / state.predictions.length > 0.2 ? 'high' : 'low') :
        'unknown',

      forecastAccuracy: state.forecasts.length > 0 ?
        state.forecasts.reduce((sum, f) => sum + f.confidence, 0) / state.forecasts.length :
        0
    };
  }, [state.metrics, state.trends, state.predictions, state.forecasts]);

  return {
    // State
    loading: state.loading,
    error: state.error,
    lastUpdated: state.lastUpdated,

    // Core Data
    metrics: state.metrics,
    trends: state.trends,
    revenueSources: state.revenueSources,
    predictions: state.predictions,
    forecasts: state.forecasts,
    budgetVariance: state.budgetVariance,

    // Insights
    insights,
    performanceMetrics,

    // Actions
    refreshAll,
    loadMetrics,
    calculateVariance,
    generateReport,
    exportData,

    // Configuration
    autoRefresh,
    setAutoRefresh,
    refreshInterval,
    setRefreshInterval,

    // Utilities
    clearError: () => setState(prev => ({ ...prev, error: null }))
  };
};

export default useFinancialAnalytics;