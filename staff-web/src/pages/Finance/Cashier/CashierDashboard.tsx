/**
 * Cashier Dashboard Component
 * Real-time cashier session management with transaction monitoring
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Dashboard, MetricCard, ChartWidget, ListWidget } from '../../../components/patterns';
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/card';
import { Button } from '../../../components/ui/button';
import { Badge } from '../../../components/ui/badge';
import { Input } from '../../../components/ui/input';
import { Label } from '../../../components/ui/label';
import { Alert, AlertDescription } from '../../../components/ui/alert';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../../../components/ui/dialog';
import { useToast } from '../../../hooks/use-toast';
import {
  DollarSign, Clock, Users, CreditCard, Banknote, TrendingUp,
  Play, Square, Calculator, AlertTriangle, CheckCircle, Printer,
  BarChart3, PieChart, Activity, RefreshCw
} from 'lucide-react';
import { financeService } from '../../../services/financeService';
import { CashierSession, POSTransaction, PaymentMethodSummary } from '../../../types/finance.types';
import { format } from 'date-fns';

interface CashierDashboardProps {
  cashierId?: string;
}

export const CashierDashboard: React.FC<CashierDashboardProps> = ({ cashierId = 'current' }) => {
  const [currentSession, setCurrentSession] = useState<CashierSession | null>(null);
  const [recentTransactions, setRecentTransactions] = useState<POSTransaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [startingCash, setStartingCash] = useState('');
  const [endingCash, setEndingCash] = useState('');
  const [showStartModal, setShowStartModal] = useState(false);
  const [showEndModal, setShowEndModal] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const { toast } = useToast();

  // Mock data for demonstration
  const mockSession: CashierSession = {
    id: '1',
    cashier_id: cashierId,
    cashier_name: 'Sarah Johnson',
    start_time: '2024-09-27T08:00:00Z',
    starting_cash: 200.00,
    expected_cash: 580.75,
    transaction_count: 23,
    total_collected: 1485.50,
    payments_by_method: [
      { method: 'cash', count: 8, total_amount: 380.75 },
      { method: 'credit_card', count: 12, total_amount: 865.00 },
      { method: 'debit_card', count: 3, total_amount: 239.75 }
    ],
    status: 'active'
  };

  const mockTransactions: POSTransaction[] = [
    {
      id: '1',
      student_id: '1',
      student_name: 'John Doe',
      items: [
        {
          id: '1',
          description: 'Tuition Payment',
          amount: 500.00,
          tax_rate: 0.08,
          category: 'tuition'
        }
      ],
      subtotal: 500.00,
      tax: 40.00,
      total: 540.00,
      payment_method: 'credit_card',
      status: 'completed',
      cashier_id: cashierId,
      timestamp: '2024-09-27T14:30:00Z',
      receipt_printed: true
    },
    {
      id: '2',
      student_id: '2',
      student_name: 'Jane Smith',
      items: [
        {
          id: '2',
          description: 'Lab Fee',
          amount: 75.00,
          tax_rate: 0.08,
          category: 'fee'
        }
      ],
      subtotal: 75.00,
      tax: 6.00,
      total: 81.00,
      payment_method: 'cash',
      status: 'completed',
      cashier_id: cashierId,
      timestamp: '2024-09-27T14:15:00Z',
      receipt_printed: true
    }
  ];

  // Load session data
  const loadSessionData = useCallback(async () => {
    setLoading(true);
    try {
      // For demo, use mock data
      setCurrentSession(mockSession);
      setRecentTransactions(mockTransactions);
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to load cashier session data",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  }, [cashierId, toast]);

  // Real-time refresh
  const refreshData = useCallback(async () => {
    setRefreshing(true);
    try {
      await loadSessionData();
      toast({
        title: "Data Refreshed",
        description: "Session data updated successfully",
      });
    } catch (error) {
      toast({
        title: "Refresh Failed",
        description: "Failed to refresh session data",
        variant: "destructive"
      });
    } finally {
      setRefreshing(false);
    }
  }, [loadSessionData, toast]);

  // Auto-refresh every 30 seconds
  useEffect(() => {
    loadSessionData();
    const interval = setInterval(refreshData, 30000);
    return () => clearInterval(interval);
  }, [loadSessionData, refreshData]);

  // Start cashier session
  const startSession = useCallback(async () => {
    const startCash = parseFloat(startingCash);
    if (isNaN(startCash) || startCash < 0) {
      toast({
        title: "Invalid Amount",
        description: "Please enter a valid starting cash amount",
        variant: "destructive"
      });
      return;
    }

    try {
      const response = await financeService.startCashierSession(startCash);
      if (response.success) {
        setCurrentSession(response.data);
        setShowStartModal(false);
        setStartingCash('');
        toast({
          title: "Session Started",
          description: "Cashier session has been started successfully",
        });
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to start cashier session",
        variant: "destructive"
      });
    }
  }, [startingCash, toast]);

  // End cashier session
  const endSession = useCallback(async () => {
    if (!currentSession) return;

    const endCash = parseFloat(endingCash);
    if (isNaN(endCash) || endCash < 0) {
      toast({
        title: "Invalid Amount",
        description: "Please enter a valid ending cash amount",
        variant: "destructive"
      });
      return;
    }

    try {
      const response = await financeService.endCashierSession(currentSession.id, endCash);
      if (response.success) {
        setCurrentSession(response.data);
        setShowEndModal(false);
        setEndingCash('');
        toast({
          title: "Session Ended",
          description: "Cashier session has been closed successfully",
        });
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to end cashier session",
        variant: "destructive"
      });
    }
  }, [currentSession, endingCash, toast]);

  // Print session report
  const printSessionReport = useCallback(() => {
    if (!currentSession) return;

    // Mock print functionality
    toast({
      title: "Printing Report",
      description: "Session report sent to printer",
    });
  }, [currentSession, toast]);

  if (!currentSession) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-center">No Active Session</CardTitle>
          </CardHeader>
          <CardContent className="text-center space-y-4">
            <p className="text-gray-600">Start a new cashier session to begin processing payments</p>
            <Dialog open={showStartModal} onOpenChange={setShowStartModal}>
              <DialogTrigger asChild>
                <Button className="w-full">
                  <Play className="h-4 w-4 mr-2" />
                  Start Session
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Start Cashier Session</DialogTitle>
                </DialogHeader>
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="starting-cash">Starting Cash Amount</Label>
                    <Input
                      id="starting-cash"
                      type="number"
                      step="0.01"
                      placeholder="200.00"
                      value={startingCash}
                      onChange={(e) => setStartingCash(e.target.value)}
                    />
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" onClick={() => setShowStartModal(false)} className="flex-1">
                      Cancel
                    </Button>
                    <Button onClick={startSession} className="flex-1">
                      Start Session
                    </Button>
                  </div>
                </div>
              </DialogContent>
            </Dialog>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Calculate variance
  const variance = currentSession.actual_cash !== undefined
    ? currentSession.actual_cash - currentSession.expected_cash
    : null;

  // Calculate session duration
  const sessionDuration = currentSession.end_time
    ? new Date(currentSession.end_time).getTime() - new Date(currentSession.start_time).getTime()
    : Date.now() - new Date(currentSession.start_time).getTime();
  const hoursWorked = Math.floor(sessionDuration / (1000 * 60 * 60));
  const minutesWorked = Math.floor((sessionDuration % (1000 * 60 * 60)) / (1000 * 60));

  // Average transaction value
  const avgTransactionValue = currentSession.transaction_count > 0
    ? currentSession.total_collected / currentSession.transaction_count
    : 0;

  // Metric cards configuration
  const metricCards: MetricCard[] = [
    {
      title: "Total Collected",
      value: `$${currentSession.total_collected.toFixed(2)}`,
      change: `${currentSession.transaction_count} transactions`,
      trend: 'up',
      icon: DollarSign,
      color: 'green'
    },
    {
      title: "Expected Cash",
      value: `$${currentSession.expected_cash.toFixed(2)}`,
      change: variance !== null ? `${variance >= 0 ? '+' : ''}$${variance.toFixed(2)} variance` : 'No variance yet',
      trend: variance === null ? 'neutral' : variance >= 0 ? 'up' : 'down',
      icon: Banknote,
      color: variance === null ? 'blue' : Math.abs(variance) <= 5 ? 'green' : 'red'
    },
    {
      title: "Transactions",
      value: currentSession.transaction_count.toString(),
      change: `$${avgTransactionValue.toFixed(2)} avg`,
      trend: 'up',
      icon: Activity,
      color: 'blue'
    },
    {
      title: "Session Time",
      value: `${hoursWorked}h ${minutesWorked}m`,
      change: currentSession.status === 'active' ? 'Active' : 'Closed',
      trend: 'neutral',
      icon: Clock,
      color: currentSession.status === 'active' ? 'green' : 'gray'
    }
  ];

  // Chart widgets configuration
  const chartWidgets: ChartWidget[] = [
    {
      title: "Payment Methods",
      type: "doughnut",
      data: {
        labels: currentSession.payments_by_method.map(p =>
          p.method.replace('_', ' ').split(' ').map(w =>
            w.charAt(0).toUpperCase() + w.slice(1)
          ).join(' ')
        ),
        datasets: [{
          data: currentSession.payments_by_method.map(p => p.total_amount),
          backgroundColor: [
            'rgba(34, 197, 94, 0.8)',   // Green for cash
            'rgba(59, 130, 246, 0.8)',  // Blue for credit
            'rgba(168, 85, 247, 0.8)',  // Purple for debit
            'rgba(245, 158, 11, 0.8)',  // Amber for mobile
          ],
          borderColor: [
            'rgb(34, 197, 94)',
            'rgb(59, 130, 246)',
            'rgb(168, 85, 247)',
            'rgb(245, 158, 11)',
          ],
          borderWidth: 2
        }]
      },
      height: 300
    },
    {
      title: "Hourly Transactions",
      type: "bar",
      data: {
        labels: ['8AM', '9AM', '10AM', '11AM', '12PM', '1PM', '2PM', '3PM'],
        datasets: [{
          label: "Transactions",
          data: [2, 4, 3, 5, 8, 6, 4, 2],
          backgroundColor: 'rgba(59, 130, 246, 0.6)',
          borderColor: 'rgb(59, 130, 246)',
          borderWidth: 1
        }]
      },
      height: 300
    }
  ];

  // List widgets configuration
  const listWidgets: ListWidget[] = [
    {
      title: "Recent Transactions",
      items: recentTransactions.slice(0, 5).map(transaction => ({
        id: transaction.id,
        title: `$${transaction.total.toFixed(2)}`,
        subtitle: `${transaction.student_name} • ${transaction.payment_method}`,
        timestamp: transaction.timestamp,
        status: transaction.status === 'completed' ? 'success' : 'pending',
        metadata: {
          'Items': transaction.items.length.toString(),
          'Receipt': transaction.receipt_printed ? 'Printed' : 'Not printed'
        }
      })),
      action: {
        label: "View All",
        onClick: () => {/* Navigate to transactions */}
      }
    },
    {
      title: "Payment Method Summary",
      items: currentSession.payments_by_method.map(method => ({
        id: method.method,
        title: method.method.replace('_', ' ').split(' ').map(w =>
          w.charAt(0).toUpperCase() + w.slice(1)
        ).join(' '),
        subtitle: `${method.count} transactions`,
        timestamp: new Date().toISOString(),
        status: 'neutral',
        metadata: {
          'Total': `$${method.total_amount.toFixed(2)}`,
          'Average': `$${(method.total_amount / method.count).toFixed(2)}`
        }
      }))
    }
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold">Cashier Dashboard</h1>
          <p className="text-gray-600">
            Session started: {format(new Date(currentSession.start_time), 'MMM dd, yyyy HH:mm')}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={refreshData}
            disabled={refreshing}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button variant="outline" onClick={printSessionReport}>
            <Printer className="h-4 w-4 mr-2" />
            Print Report
          </Button>
          {currentSession.status === 'active' && (
            <Dialog open={showEndModal} onOpenChange={setShowEndModal}>
              <DialogTrigger asChild>
                <Button variant="destructive">
                  <Square className="h-4 w-4 mr-2" />
                  End Session
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>End Cashier Session</DialogTitle>
                </DialogHeader>
                <div className="space-y-4">
                  <Alert>
                    <AlertTriangle className="h-4 w-4" />
                    <AlertDescription>
                      Please count your cash drawer and enter the actual amount below.
                    </AlertDescription>
                  </Alert>

                  <div className="space-y-2">
                    <Label>Expected Cash Amount</Label>
                    <div className="p-3 bg-gray-100 rounded font-medium">
                      ${currentSession.expected_cash.toFixed(2)}
                    </div>
                  </div>

                  <div>
                    <Label htmlFor="ending-cash">Actual Cash Amount</Label>
                    <Input
                      id="ending-cash"
                      type="number"
                      step="0.01"
                      placeholder={currentSession.expected_cash.toFixed(2)}
                      value={endingCash}
                      onChange={(e) => setEndingCash(e.target.value)}
                    />
                  </div>

                  {endingCash && !isNaN(parseFloat(endingCash)) && (
                    <div className="p-3 bg-blue-50 border border-blue-200 rounded">
                      <p className="text-sm font-medium text-blue-900">
                        Variance: ${(parseFloat(endingCash) - currentSession.expected_cash).toFixed(2)}
                      </p>
                    </div>
                  )}

                  <div className="flex gap-2">
                    <Button variant="outline" onClick={() => setShowEndModal(false)} className="flex-1">
                      Cancel
                    </Button>
                    <Button onClick={endSession} className="flex-1">
                      End Session
                    </Button>
                  </div>
                </div>
              </DialogContent>
            </Dialog>
          )}
        </div>
      </div>

      {/* Session Status Alert */}
      {currentSession.status === 'active' && (
        <Alert className="border-green-300 bg-green-50">
          <CheckCircle className="h-4 w-4" />
          <AlertDescription>
            <strong>Session Active:</strong> Cashier {currentSession.cashier_name} •
            {currentSession.transaction_count} transactions •
            ${currentSession.total_collected.toFixed(2)} collected
          </AlertDescription>
        </Alert>
      )}

      {/* Cash Variance Alert */}
      {variance !== null && Math.abs(variance) > 5 && (
        <Alert className="border-yellow-300 bg-yellow-50">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            <strong>Cash Variance Detected:</strong> ${Math.abs(variance).toFixed(2)}
            {variance > 0 ? ' over' : ' short'} - Please review transactions
          </AlertDescription>
        </Alert>
      )}

      {/* Dashboard */}
      <Dashboard
        metricCards={metricCards}
        chartWidgets={chartWidgets}
        listWidgets={listWidgets}
        loading={loading}
      />

      {/* Session Details */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Cash Reconciliation */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Calculator className="h-5 w-5" />
              Cash Reconciliation
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-600">Starting Cash</p>
                <p className="text-lg font-medium">${currentSession.starting_cash.toFixed(2)}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Cash Collected</p>
                <p className="text-lg font-medium text-green-600">
                  +${currentSession.payments_by_method
                    .find(p => p.method === 'cash')?.total_amount.toFixed(2) || '0.00'}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Expected Cash</p>
                <p className="text-lg font-medium">${currentSession.expected_cash.toFixed(2)}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Actual Cash</p>
                <p className={`text-lg font-medium ${
                  variance === null ? 'text-gray-500' :
                  Math.abs(variance) <= 1 ? 'text-green-600' :
                  Math.abs(variance) <= 5 ? 'text-yellow-600' : 'text-red-600'
                }`}>
                  {currentSession.actual_cash !== undefined
                    ? `$${currentSession.actual_cash.toFixed(2)}`
                    : 'Not counted'
                  }
                </p>
              </div>
            </div>

            {variance !== null && (
              <>
                <div className="border-t pt-4">
                  <div className="flex justify-between items-center">
                    <span className="font-medium">Variance:</span>
                    <span className={`font-bold ${
                      Math.abs(variance) <= 1 ? 'text-green-600' :
                      Math.abs(variance) <= 5 ? 'text-yellow-600' : 'text-red-600'
                    }`}>
                      {variance >= 0 ? '+' : ''}${variance.toFixed(2)}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 mt-1">
                    {Math.abs(variance) <= 1 ? 'Within acceptable range' :
                     Math.abs(variance) <= 5 ? 'Minor variance - review recommended' :
                     'Significant variance - investigation required'}
                  </p>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* Session Summary */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              Session Summary
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-600">Session Duration</p>
                <p className="text-lg font-medium">{hoursWorked}h {minutesWorked}m</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Transactions/Hour</p>
                <p className="text-lg font-medium">
                  {hoursWorked > 0 ? (currentSession.transaction_count / hoursWorked).toFixed(1) : '0'}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Avg Transaction</p>
                <p className="text-lg font-medium">${avgTransactionValue.toFixed(2)}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Status</p>
                <Badge variant={currentSession.status === 'active' ? 'default' : 'secondary'}>
                  {currentSession.status}
                </Badge>
              </div>
            </div>

            <div className="border-t pt-4">
              <h4 className="font-medium mb-2">Payment Methods</h4>
              <div className="space-y-2">
                {currentSession.payments_by_method.map(method => (
                  <div key={method.method} className="flex justify-between items-center">
                    <span className="text-sm">
                      {method.method.replace('_', ' ').split(' ').map(w =>
                        w.charAt(0).toUpperCase() + w.slice(1)
                      ).join(' ')}
                    </span>
                    <div className="text-right">
                      <p className="text-sm font-medium">${method.total_amount.toFixed(2)}</p>
                      <p className="text-xs text-gray-600">{method.count} trans</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default CashierDashboard;