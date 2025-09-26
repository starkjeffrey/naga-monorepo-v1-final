/**
 * Finance Analytics Component
 * AI-powered financial dashboard with predictive insights and comprehensive reporting
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Dashboard, MetricCard, ChartWidget, ListWidget, Filter } from '../../../components/patterns';
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/card';
import { Button } from '../../../components/ui/button';
import { Badge } from '../../../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../../components/ui/tabs';
import { Alert, AlertDescription } from '../../../components/ui/alert';
import { useToast } from '../../../hooks/use-toast';
import {
  TrendingUp, TrendingDown, DollarSign, Users, Calendar, BarChart3,
  PieChart, Activity, Target, AlertTriangle, Lightbulb, Download,
  RefreshCw, Brain, Zap, ArrowUpRight, ArrowDownRight
} from 'lucide-react';
import { financeService } from '../../../services/financeService';
import { FinancialMetrics, MonthlyTrend, RevenueSource, PaymentPrediction } from '../../../types/finance.types';
import { format, subDays, subMonths, startOfMonth, endOfMonth } from 'date-fns';

export const FinanceAnalytics: React.FC = () => {
  const [metrics, setMetrics] = useState<FinancialMetrics | null>(null);
  const [predictions, setPredictions] = useState<PaymentPrediction[]>([]);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState('30d');
  const [comparisonPeriod, setComparisonPeriod] = useState('previous');
  const [activeTab, setActiveTab] = useState('overview');

  const { toast } = useToast();

  // Mock data for demonstration
  const mockMetrics: FinancialMetrics = {
    total_revenue: 284650.75,
    outstanding_balance: 45280.25,
    collection_rate: 89.5,
    average_payment_time: 18.5,
    monthly_trends: [
      { month: '2024-03', revenue: 42350, collections: 38420, new_invoices: 125, payment_count: 95 },
      { month: '2024-04', revenue: 48720, collections: 45680, new_invoices: 142, payment_count: 118 },
      { month: '2024-05', revenue: 51200, collections: 47830, new_invoices: 138, payment_count: 125 },
      { month: '2024-06', revenue: 49680, collections: 46320, new_invoices: 135, payment_count: 121 },
      { month: '2024-07', revenue: 53450, collections: 48960, new_invoices: 148, payment_count: 135 },
      { month: '2024-08', revenue: 55280, collections: 52240, new_invoices: 156, payment_count: 142 },
      { month: '2024-09', revenue: 58970, collections: 54200, new_invoices: 162, payment_count: 148 }
    ],
    payment_method_breakdown: [
      { method: 'credit_card', count: 425, total_amount: 185420.50 },
      { method: 'bank_transfer', count: 156, total_amount: 95680.25 },
      { method: 'cash', count: 89, total_amount: 28450.75 },
      { method: 'debit_card', count: 67, total_amount: 15280.00 }
    ],
    top_revenue_sources: [
      { source: 'Tuition Fees', amount: 198450.50, percentage: 69.7, student_count: 342 },
      { source: 'Registration Fees', amount: 45280.25, percentage: 15.9, student_count: 425 },
      { source: 'Lab Fees', amount: 28650.00, percentage: 10.1, student_count: 287 },
      { source: 'Materials', amount: 12270.00, percentage: 4.3, student_count: 156 }
    ]
  };

  const mockPredictions: PaymentPrediction[] = [
    {
      student_id: '1',
      invoice_id: 'INV-2024-001',
      predicted_payment_date: '2024-10-05',
      probability: 0.85,
      risk_factors: ['Previous late payment', 'High balance'],
      recommendations: ['Send reminder 3 days before due date', 'Offer payment plan']
    },
    {
      student_id: '2',
      invoice_id: 'INV-2024-002',
      predicted_payment_date: '2024-10-12',
      probability: 0.92,
      risk_factors: [],
      recommendations: ['Standard processing expected']
    }
  ];

  // Load analytics data
  const loadAnalytics = useCallback(async () => {
    setLoading(true);
    try {
      // Calculate date range based on selection
      const endDate = new Date();
      let startDate: Date;

      switch (timeRange) {
        case '7d':
          startDate = subDays(endDate, 7);
          break;
        case '30d':
          startDate = subDays(endDate, 30);
          break;
        case '90d':
          startDate = subDays(endDate, 90);
          break;
        case '12m':
          startDate = subMonths(endDate, 12);
          break;
        default:
          startDate = subDays(endDate, 30);
      }

      // For demo, use mock data
      setMetrics(mockMetrics);
      setPredictions(mockPredictions);
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to load analytics data",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  }, [timeRange, toast]);

  useEffect(() => {
    loadAnalytics();
  }, [loadAnalytics]);

  if (!metrics) return null;

  // Calculate trends and insights
  const currentMonth = metrics.monthly_trends[metrics.monthly_trends.length - 1];
  const previousMonth = metrics.monthly_trends[metrics.monthly_trends.length - 2];
  const revenueGrowth = previousMonth
    ? ((currentMonth.revenue - previousMonth.revenue) / previousMonth.revenue) * 100
    : 0;
  const collectionGrowth = previousMonth
    ? ((currentMonth.collections - previousMonth.collections) / previousMonth.collections) * 100
    : 0;

  // AI Insights
  const aiInsights = [
    {
      type: 'opportunity',
      title: 'Collection Rate Optimization',
      description: 'Collection rate could improve by 3.2% with automated reminders',
      impact: '+$8,450 monthly',
      confidence: 0.89
    },
    {
      type: 'risk',
      title: 'Late Payment Pattern',
      description: 'Lab fee payments show 15% higher late payment rate',
      impact: 'Risk: $2,340',
      confidence: 0.76
    },
    {
      type: 'trend',
      title: 'Payment Method Shift',
      description: 'Credit card usage increased 12% over last quarter',
      impact: 'Lower processing time',
      confidence: 0.94
    }
  ];

  // Metric cards configuration
  const metricCards: MetricCard[] = [
    {
      title: "Total Revenue",
      value: `$${metrics.total_revenue.toLocaleString()}`,
      change: `${revenueGrowth >= 0 ? '+' : ''}${revenueGrowth.toFixed(1)}%`,
      trend: revenueGrowth >= 0 ? 'up' : 'down',
      icon: DollarSign,
      color: revenueGrowth >= 0 ? 'green' : 'red'
    },
    {
      title: "Collection Rate",
      value: `${metrics.collection_rate.toFixed(1)}%`,
      change: `${collectionGrowth >= 0 ? '+' : ''}${collectionGrowth.toFixed(1)}%`,
      trend: collectionGrowth >= 0 ? 'up' : 'down',
      icon: Target,
      color: metrics.collection_rate >= 90 ? 'green' : metrics.collection_rate >= 80 ? 'yellow' : 'red'
    },
    {
      title: "Outstanding Balance",
      value: `$${metrics.outstanding_balance.toLocaleString()}`,
      change: `${metrics.average_payment_time.toFixed(1)} days avg`,
      trend: metrics.average_payment_time <= 20 ? 'up' : 'down',
      icon: AlertTriangle,
      color: metrics.outstanding_balance <= 50000 ? 'green' : 'red'
    },
    {
      title: "Active Students",
      value: metrics.top_revenue_sources.reduce((sum, source) => sum + source.student_count, 0).toString(),
      change: '+8.3%',
      trend: 'up',
      icon: Users,
      color: 'blue'
    }
  ];

  // Chart widgets configuration
  const chartWidgets: ChartWidget[] = [
    {
      title: "Revenue Trend",
      type: "line",
      data: {
        labels: metrics.monthly_trends.map(trend =>
          format(new Date(trend.month), 'MMM yyyy')
        ),
        datasets: [
          {
            label: "Revenue",
            data: metrics.monthly_trends.map(trend => trend.revenue),
            borderColor: 'rgb(34, 197, 94)',
            backgroundColor: 'rgba(34, 197, 94, 0.1)',
            tension: 0.4,
            fill: true
          },
          {
            label: "Collections",
            data: metrics.monthly_trends.map(trend => trend.collections),
            borderColor: 'rgb(59, 130, 246)',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            tension: 0.4,
            fill: false
          }
        ]
      },
      height: 350
    },
    {
      title: "Payment Methods",
      type: "doughnut",
      data: {
        labels: metrics.payment_method_breakdown.map(method =>
          method.method.replace('_', ' ').split(' ').map(w =>
            w.charAt(0).toUpperCase() + w.slice(1)
          ).join(' ')
        ),
        datasets: [{
          data: metrics.payment_method_breakdown.map(method => method.total_amount),
          backgroundColor: [
            'rgba(34, 197, 94, 0.8)',
            'rgba(59, 130, 246, 0.8)',
            'rgba(245, 158, 11, 0.8)',
            'rgba(168, 85, 247, 0.8)',
          ],
          borderColor: [
            'rgb(34, 197, 94)',
            'rgb(59, 130, 246)',
            'rgb(245, 158, 11)',
            'rgb(168, 85, 247)',
          ],
          borderWidth: 2
        }]
      },
      height: 350
    },
    {
      title: "Collection Performance",
      type: "bar",
      data: {
        labels: metrics.monthly_trends.slice(-6).map(trend =>
          format(new Date(trend.month), 'MMM')
        ),
        datasets: [
          {
            label: "Collection Rate %",
            data: metrics.monthly_trends.slice(-6).map(trend =>
              (trend.collections / trend.revenue) * 100
            ),
            backgroundColor: 'rgba(34, 197, 94, 0.6)',
            borderColor: 'rgb(34, 197, 94)',
            borderWidth: 1,
            yAxisID: 'y'
          },
          {
            label: "Payment Count",
            data: metrics.monthly_trends.slice(-6).map(trend => trend.payment_count),
            type: 'line' as const,
            borderColor: 'rgb(239, 68, 68)',
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            yAxisID: 'y1'
          }
        ]
      },
      height: 350
    }
  ];

  // List widgets configuration
  const listWidgets: ListWidget[] = [
    {
      title: "Revenue Sources",
      items: metrics.top_revenue_sources.map(source => ({
        id: source.source,
        title: source.source,
        subtitle: `${source.student_count} students • ${source.percentage.toFixed(1)}%`,
        timestamp: new Date().toISOString(),
        status: 'neutral',
        metadata: {
          'Amount': `$${source.amount.toLocaleString()}`,
          'Avg per Student': `$${(source.amount / source.student_count).toFixed(2)}`
        }
      }))
    },
    {
      title: "AI Insights",
      items: aiInsights.map((insight, index) => ({
        id: index.toString(),
        title: insight.title,
        subtitle: insight.description,
        timestamp: new Date().toISOString(),
        status: insight.type === 'opportunity' ? 'success' :
               insight.type === 'risk' ? 'warning' : 'info',
        metadata: {
          'Impact': insight.impact,
          'Confidence': `${(insight.confidence * 100).toFixed(0)}%`
        }
      })),
      action: {
        label: "View All Insights",
        onClick: () => setActiveTab('insights')
      }
    }
  ];

  // Export report
  const exportReport = useCallback(async (format: string) => {
    try {
      const blob = await financeService.exportData('analytics', {
        time_range: timeRange,
        comparison_period: comparisonPeriod
      }, format);

      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `finance-analytics-${format(new Date(), 'yyyy-MM-dd')}.${format}`;
      a.click();
      URL.revokeObjectURL(url);

      toast({
        title: "Export Complete",
        description: `Analytics report exported as ${format.toUpperCase()}`,
      });
    } catch (error) {
      toast({
        title: "Export Failed",
        description: "Failed to export analytics report",
        variant: "destructive"
      });
    }
  }, [timeRange, comparisonPeriod, toast]);

  // Filters configuration
  const filters: Filter[] = [
    {
      id: 'timeRange',
      label: 'Time Range',
      type: 'select',
      value: timeRange,
      options: [
        { value: '7d', label: 'Last 7 days' },
        { value: '30d', label: 'Last 30 days' },
        { value: '90d', label: 'Last 90 days' },
        { value: '12m', label: 'Last 12 months' }
      ],
      onChange: (value) => setTimeRange(value as string)
    },
    {
      id: 'comparison',
      label: 'Compare to',
      type: 'select',
      value: comparisonPeriod,
      options: [
        { value: 'previous', label: 'Previous period' },
        { value: 'year_ago', label: 'Same period last year' },
        { value: 'budget', label: 'Budget target' }
      ],
      onChange: (value) => setComparisonPeriod(value as string)
    }
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold">Financial Analytics</h1>
          <p className="text-gray-600">AI-powered insights and financial performance analysis</p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={timeRange} onValueChange={setTimeRange}>
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7d">Last 7 days</SelectItem>
              <SelectItem value="30d">Last 30 days</SelectItem>
              <SelectItem value="90d">Last 90 days</SelectItem>
              <SelectItem value="12m">Last 12 months</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" onClick={() => exportReport('pdf')}>
            <Download className="h-4 w-4 mr-2" />
            Export PDF
          </Button>
          <Button variant="outline" onClick={loadAnalytics}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* AI Alert */}
      <Alert className="border-blue-300 bg-blue-50">
        <Brain className="h-4 w-4" />
        <AlertDescription>
          <strong>AI Analysis Complete:</strong> Found 3 optimization opportunities with potential
          monthly impact of $10,790. Review insights below for details.
        </AlertDescription>
      </Alert>

      {/* Dashboard */}
      <Dashboard
        metricCards={metricCards}
        chartWidgets={chartWidgets}
        listWidgets={listWidgets}
        filters={filters}
        loading={loading}
      />

      {/* Detailed Analytics Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="insights">AI Insights</TabsTrigger>
          <TabsTrigger value="forecasting">Forecasting</TabsTrigger>
          <TabsTrigger value="reports">Reports</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Performance Summary */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="h-5 w-5" />
                  Performance Summary
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-gray-600">Monthly Revenue</p>
                    <p className="text-2xl font-bold text-green-600">
                      ${currentMonth.revenue.toLocaleString()}
                    </p>
                    <div className="flex items-center text-sm">
                      {revenueGrowth >= 0 ? (
                        <ArrowUpRight className="h-4 w-4 text-green-500 mr-1" />
                      ) : (
                        <ArrowDownRight className="h-4 w-4 text-red-500 mr-1" />
                      )}
                      <span className={revenueGrowth >= 0 ? 'text-green-600' : 'text-red-600'}>
                        {revenueGrowth.toFixed(1)}% vs last month
                      </span>
                    </div>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Collections</p>
                    <p className="text-2xl font-bold text-blue-600">
                      ${currentMonth.collections.toLocaleString()}
                    </p>
                    <div className="flex items-center text-sm">
                      {collectionGrowth >= 0 ? (
                        <ArrowUpRight className="h-4 w-4 text-green-500 mr-1" />
                      ) : (
                        <ArrowDownRight className="h-4 w-4 text-red-500 mr-1" />
                      )}
                      <span className={collectionGrowth >= 0 ? 'text-green-600' : 'text-red-600'}>
                        {collectionGrowth.toFixed(1)}% vs last month
                      </span>
                    </div>
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">Collection Efficiency</span>
                    <span className="font-medium">{metrics.collection_rate.toFixed(1)}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${
                        metrics.collection_rate >= 90 ? 'bg-green-500' :
                        metrics.collection_rate >= 80 ? 'bg-yellow-500' : 'bg-red-500'
                      }`}
                      style={{ width: `${metrics.collection_rate}%` }}
                    ></div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Key Metrics */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="h-5 w-5" />
                  Key Metrics
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-gray-600">Avg Payment Time</p>
                    <p className="text-2xl font-bold">
                      {metrics.average_payment_time.toFixed(1)} days
                    </p>
                    <Badge variant={metrics.average_payment_time <= 15 ? "default" : "destructive"}>
                      {metrics.average_payment_time <= 15 ? "Excellent" : "Needs Attention"}
                    </Badge>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Outstanding Balance</p>
                    <p className="text-2xl font-bold text-orange-600">
                      ${metrics.outstanding_balance.toLocaleString()}
                    </p>
                    <p className="text-sm text-gray-600">
                      {((metrics.outstanding_balance / metrics.total_revenue) * 100).toFixed(1)}% of revenue
                    </p>
                  </div>
                </div>

                <div className="space-y-2">
                  <h4 className="font-medium">Payment Methods</h4>
                  {metrics.payment_method_breakdown.map(method => (
                    <div key={method.method} className="flex justify-between items-center">
                      <span className="text-sm">
                        {method.method.replace('_', ' ').split(' ').map(w =>
                          w.charAt(0).toUpperCase() + w.slice(1)
                        ).join(' ')}
                      </span>
                      <div className="text-right">
                        <p className="text-sm font-medium">${method.total_amount.toLocaleString()}</p>
                        <p className="text-xs text-gray-600">{method.count} payments</p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="insights" className="space-y-6">
          <div className="grid grid-cols-1 gap-6">
            {aiInsights.map((insight, index) => (
              <Card key={index}>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    {insight.type === 'opportunity' && <Lightbulb className="h-5 w-5 text-green-500" />}
                    {insight.type === 'risk' && <AlertTriangle className="h-5 w-5 text-yellow-500" />}
                    {insight.type === 'trend' && <TrendingUp className="h-5 w-5 text-blue-500" />}
                    {insight.title}
                    <Badge variant={
                      insight.type === 'opportunity' ? 'default' :
                      insight.type === 'risk' ? 'destructive' : 'secondary'
                    }>
                      {insight.confidence > 0.8 ? 'High Confidence' : 'Medium Confidence'}
                    </Badge>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-600 mb-4">{insight.description}</p>
                  <div className="flex justify-between items-center">
                    <div>
                      <p className="text-sm text-gray-600">Potential Impact</p>
                      <p className="font-bold text-lg">{insight.impact}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm text-gray-600">AI Confidence</p>
                      <p className="font-bold">{(insight.confidence * 100).toFixed(0)}%</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="forecasting" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="h-5 w-5" />
                Revenue Forecasting
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                {/* Forecast Chart would go here */}
                <div className="h-64 bg-gray-50 rounded-lg flex items-center justify-center">
                  <p className="text-gray-500">AI Revenue Forecast Chart</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <Card>
                    <CardContent className="p-4">
                      <p className="text-sm text-gray-600">Next Month Forecast</p>
                      <p className="text-2xl font-bold text-green-600">$62,450</p>
                      <p className="text-sm text-green-600">+5.8% growth</p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="p-4">
                      <p className="text-sm text-gray-600">Quarter Forecast</p>
                      <p className="text-2xl font-bold text-blue-600">$185,200</p>
                      <p className="text-sm text-blue-600">+4.2% growth</p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="p-4">
                      <p className="text-sm text-gray-600">Annual Forecast</p>
                      <p className="text-2xl font-bold text-purple-600">$720,800</p>
                      <p className="text-sm text-purple-600">+6.5% growth</p>
                    </CardContent>
                  </Card>
                </div>

                {/* Payment Predictions */}
                <div>
                  <h3 className="text-lg font-medium mb-4">Payment Predictions</h3>
                  <div className="space-y-3">
                    {predictions.map(prediction => (
                      <Card key={prediction.invoice_id}>
                        <CardContent className="p-4">
                          <div className="flex justify-between items-start">
                            <div>
                              <p className="font-medium">Invoice {prediction.invoice_id}</p>
                              <p className="text-sm text-gray-600">
                                Predicted payment: {format(new Date(prediction.predicted_payment_date), 'MMM dd, yyyy')}
                              </p>
                              {prediction.risk_factors.length > 0 && (
                                <div className="mt-2">
                                  <p className="text-sm text-yellow-600">Risk factors:</p>
                                  <ul className="list-disc list-inside text-xs text-gray-600">
                                    {prediction.risk_factors.map((factor, index) => (
                                      <li key={index}>{factor}</li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                            </div>
                            <Badge variant={prediction.probability > 0.8 ? "default" : "secondary"}>
                              {(prediction.probability * 100).toFixed(0)}% confidence
                            </Badge>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="reports" className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Quick Reports</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <Button
                  variant="outline"
                  className="w-full justify-start"
                  onClick={() => exportReport('pdf')}
                >
                  <Download className="h-4 w-4 mr-2" />
                  Revenue Summary Report
                </Button>
                <Button
                  variant="outline"
                  className="w-full justify-start"
                  onClick={() => exportReport('csv')}
                >
                  <Download className="h-4 w-4 mr-2" />
                  Payment Analysis Export
                </Button>
                <Button
                  variant="outline"
                  className="w-full justify-start"
                  onClick={() => exportReport('xlsx')}
                >
                  <Download className="h-4 w-4 mr-2" />
                  Collection Performance
                </Button>
                <Button
                  variant="outline"
                  className="w-full justify-start"
                  onClick={() => exportReport('pdf')}
                >
                  <Download className="h-4 w-4 mr-2" />
                  Outstanding Balance Report
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Scheduled Reports</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-3">
                  <div className="flex justify-between items-center p-3 border rounded">
                    <div>
                      <p className="font-medium">Weekly Revenue Summary</p>
                      <p className="text-sm text-gray-600">Every Monday at 9:00 AM</p>
                    </div>
                    <Badge variant="default">Active</Badge>
                  </div>
                  <div className="flex justify-between items-center p-3 border rounded">
                    <div>
                      <p className="font-medium">Monthly Collection Report</p>
                      <p className="text-sm text-gray-600">1st of each month</p>
                    </div>
                    <Badge variant="default">Active</Badge>
                  </div>
                  <div className="flex justify-between items-center p-3 border rounded">
                    <div>
                      <p className="font-medium">Quarterly Analytics</p>
                      <p className="text-sm text-gray-600">End of quarter</p>
                    </div>
                    <Badge variant="secondary">Inactive</Badge>
                  </div>
                </div>
                <Button variant="outline" className="w-full">
                  Manage Scheduled Reports
                </Button>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default FinanceAnalytics;