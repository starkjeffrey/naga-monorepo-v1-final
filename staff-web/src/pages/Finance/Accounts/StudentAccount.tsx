/**
 * Student Account Dashboard Component
 * Comprehensive financial overview for individual students
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Dashboard, MetricCard, ChartWidget, ListWidget } from '../../../components/patterns';
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/card';
import { Button } from '../../../components/ui/button';
import { Badge } from '../../../components/ui/badge';
import { Input } from '../../../components/ui/input';
import { Label } from '../../../components/ui/label';
import { Alert, AlertDescription } from '../../../components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../../components/ui/tabs';
import { useToast } from '../../../hooks/use-toast';
import {
  DollarSign, CreditCard, Calendar, AlertTriangle, TrendingUp, TrendingDown,
  User, Phone, Mail, MapPin, Clock, CheckCircle, XCircle, Plus, Settings
} from 'lucide-react';
import { financeService } from '../../../services/financeService';
import { StudentAccount, Payment, Invoice, PaymentPlan, FinancialAid } from '../../../types/finance.types';
import { format } from 'date-fns';
import QuickPayment from '../Payments/QuickPayment';

interface StudentAccountProps {
  studentId: string;
}

export const StudentAccountDashboard: React.FC<StudentAccountProps> = ({ studentId }) => {
  const [account, setAccount] = useState<StudentAccount | null>(null);
  const [loading, setLoading] = useState(true);
  const [showQuickPayment, setShowQuickPayment] = useState(false);
  const [creditAdjustment, setCreditAdjustment] = useState('');
  const [adjustmentReason, setAdjustmentReason] = useState('');
  const [activeTab, setActiveTab] = useState('overview');

  const { toast } = useToast();

  // Mock data for demonstration
  const mockAccount: StudentAccount = {
    student_id: studentId,
    student_name: 'John Doe',
    current_balance: -485.75,
    available_credit: 1000.00,
    total_payments: 2314.25,
    total_charges: 2800.00,
    payment_history: [
      {
        id: '1',
        student_id: studentId,
        amount: 500.00,
        payment_method: 'credit_card',
        status: 'completed',
        transaction_id: 'TXN-001',
        processed_date: '2024-09-20T10:30:00Z',
        receipt_number: 'RCP-001',
        notes: 'Partial tuition payment'
      },
      {
        id: '2',
        student_id: studentId,
        amount: 1200.00,
        payment_method: 'bank_transfer',
        status: 'completed',
        transaction_id: 'TXN-002',
        processed_date: '2024-08-15T14:22:00Z',
        receipt_number: 'RCP-002',
        notes: 'Summer session payment'
      },
      {
        id: '3',
        student_id: studentId,
        amount: 614.25,
        payment_method: 'cash',
        status: 'completed',
        transaction_id: 'TXN-003',
        processed_date: '2024-07-10T09:15:00Z',
        receipt_number: 'RCP-003',
        notes: 'Registration and materials'
      }
    ],
    active_payment_plans: [
      {
        id: '1',
        invoice_id: 'INV-2024-001',
        total_amount: 1620.00,
        down_payment: 500.00,
        installments: [
          {
            id: '1',
            payment_plan_id: '1',
            amount: 560.00,
            due_date: '2024-10-15',
            status: 'pending'
          },
          {
            id: '2',
            payment_plan_id: '1',
            amount: 560.00,
            due_date: '2024-11-15',
            status: 'pending'
          }
        ],
        status: 'active',
        created_date: '2024-09-15',
        auto_debit_enabled: false,
        late_fee_policy: {
          grace_period_days: 5,
          fee_amount: 25.00,
          fee_type: 'fixed',
          max_fees: 3
        }
      }
    ],
    account_holds: [
      {
        id: '1',
        type: 'academic',
        description: 'Outstanding balance hold - registration restricted',
        amount: 485.75,
        placed_date: '2024-09-25',
        active: true
      }
    ],
    auto_payment_setup: {
      id: '1',
      payment_method: 'credit_card',
      account_details: { last_four: '1234' },
      enabled: false,
      next_payment_date: '2024-10-15'
    },
    financial_aid: [
      {
        id: '1',
        student_id: studentId,
        type: 'scholarship',
        amount: 1000.00,
        academic_year: '2024-2025',
        status: 'disbursed',
        source: 'Merit Scholarship Program',
        requirements: ['Maintain 3.5 GPA', 'Full-time enrollment'],
        disbursement_schedule: [
          {
            id: '1',
            amount: 500.00,
            disbursement_date: '2024-08-15',
            status: 'disbursed',
            requirements_met: true
          },
          {
            id: '2',
            amount: 500.00,
            disbursement_date: '2024-01-15',
            status: 'pending',
            requirements_met: true
          }
        ]
      }
    ]
  };

  // Load account data
  const loadAccount = useCallback(async () => {
    setLoading(true);
    try {
      // For demo, use mock data
      setAccount(mockAccount);
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to load student account",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  }, [studentId, toast]);

  useEffect(() => {
    loadAccount();
  }, [loadAccount]);

  if (!account) return null;

  // Calculate metrics
  const balanceStatus = account.current_balance >= 0 ? 'positive' : 'negative';
  const utilizationPercentage = Math.abs(account.current_balance) / account.available_credit * 100;
  const averagePayment = account.payment_history.length > 0
    ? account.total_payments / account.payment_history.length
    : 0;

  // Adjust account credit
  const adjustCredit = useCallback(async () => {
    const amount = parseFloat(creditAdjustment);
    if (isNaN(amount) || !adjustmentReason) {
      toast({
        title: "Invalid Input",
        description: "Please enter a valid amount and reason",
        variant: "destructive"
      });
      return;
    }

    try {
      await financeService.updateAccountCredit(studentId, amount, adjustmentReason);
      toast({
        title: "Credit Adjusted",
        description: `Account credit adjusted by $${amount.toFixed(2)}`,
      });
      setCreditAdjustment('');
      setAdjustmentReason('');
      loadAccount();
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to adjust account credit",
        variant: "destructive"
      });
    }
  }, [creditAdjustment, adjustmentReason, studentId, toast, loadAccount]);

  // Enable auto payment
  const enableAutoPayment = useCallback(async () => {
    try {
      // Mock implementation
      toast({
        title: "Auto Payment Setup",
        description: "Auto payment has been enabled",
      });
      loadAccount();
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to setup auto payment",
        variant: "destructive"
      });
    }
  }, [toast, loadAccount]);

  // Metric cards configuration
  const metricCards: MetricCard[] = [
    {
      title: "Current Balance",
      value: `$${Math.abs(account.current_balance).toFixed(2)}`,
      change: balanceStatus === 'positive' ? '+5.2%' : '-2.1%',
      trend: balanceStatus === 'positive' ? 'up' : 'down',
      icon: DollarSign,
      color: balanceStatus === 'positive' ? 'green' : 'red'
    },
    {
      title: "Available Credit",
      value: `$${account.available_credit.toFixed(2)}`,
      change: `${utilizationPercentage.toFixed(1)}% used`,
      trend: utilizationPercentage > 50 ? 'down' : 'up',
      icon: CreditCard,
      color: utilizationPercentage > 75 ? 'red' : 'blue'
    },
    {
      title: "Total Payments",
      value: `$${account.total_payments.toFixed(2)}`,
      change: '+12.5%',
      trend: 'up',
      icon: TrendingUp,
      color: 'green'
    },
    {
      title: "Average Payment",
      value: `$${averagePayment.toFixed(2)}`,
      change: `${account.payment_history.length} payments`,
      trend: 'neutral',
      icon: Calendar,
      color: 'blue'
    }
  ];

  // Chart widgets configuration
  const chartWidgets: ChartWidget[] = [
    {
      title: "Payment History",
      type: "line",
      data: {
        labels: account.payment_history.slice(-6).map(p =>
          format(new Date(p.processed_date), 'MMM dd')
        ),
        datasets: [{
          label: "Payment Amount",
          data: account.payment_history.slice(-6).map(p => p.amount),
          borderColor: 'rgb(59, 130, 246)',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          tension: 0.4
        }]
      },
      height: 300
    },
    {
      title: "Balance Trend",
      type: "bar",
      data: {
        labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
        datasets: [{
          label: "Monthly Balance",
          data: [-200, -150, -300, -100, -250, -486],
          backgroundColor: 'rgba(239, 68, 68, 0.6)',
          borderColor: 'rgb(239, 68, 68)',
          borderWidth: 1
        }]
      },
      height: 300
    }
  ];

  // List widgets configuration
  const listWidgets: ListWidget[] = [
    {
      title: "Recent Payments",
      items: account.payment_history.slice(0, 5).map(payment => ({
        id: payment.id,
        title: `$${payment.amount.toFixed(2)}`,
        subtitle: `${payment.payment_method} • ${payment.receipt_number}`,
        timestamp: payment.processed_date,
        status: payment.status === 'completed' ? 'success' : 'pending',
        metadata: {
          'Transaction ID': payment.transaction_id,
          'Notes': payment.notes || 'No notes'
        }
      })),
      action: {
        label: "View All",
        onClick: () => setActiveTab('payments')
      }
    },
    {
      title: "Active Holds",
      items: account.account_holds.filter(hold => hold.active).map(hold => ({
        id: hold.id,
        title: hold.type.charAt(0).toUpperCase() + hold.type.slice(1),
        subtitle: hold.description,
        timestamp: hold.placed_date,
        status: 'warning',
        metadata: {
          'Amount': hold.amount ? `$${hold.amount.toFixed(2)}` : 'N/A',
          'Date Placed': format(new Date(hold.placed_date), 'MMM dd, yyyy')
        }
      })),
      emptyState: {
        title: "No Active Holds",
        description: "Account is in good standing"
      }
    }
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold">{account.student_name}</h1>
          <p className="text-gray-600">Student ID: {account.student_id}</p>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={() => setShowQuickPayment(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Record Payment
          </Button>
          <Button variant="outline" onClick={loadAccount}>
            Refresh
          </Button>
        </div>
      </div>

      {/* Balance Alert */}
      {account.current_balance < 0 && (
        <Alert className="border-red-300 bg-red-50">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            <strong>Outstanding Balance:</strong> ${Math.abs(account.current_balance).toFixed(2)}
            {account.account_holds.some(h => h.active) && (
              <span> • Account holds are in place restricting services</span>
            )}
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

      {/* Detailed Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="payments">Payments</TabsTrigger>
          <TabsTrigger value="plans">Payment Plans</TabsTrigger>
          <TabsTrigger value="aid">Financial Aid</TabsTrigger>
          <TabsTrigger value="settings">Settings</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Account Summary */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <User className="h-5 w-5" />
                  Account Summary
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-gray-600">Current Balance</p>
                    <p className={`text-lg font-bold ${balanceStatus === 'positive' ? 'text-green-600' : 'text-red-600'}`}>
                      ${Math.abs(account.current_balance).toFixed(2)}
                      {balanceStatus === 'negative' && ' (Owed)'}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Available Credit</p>
                    <p className="text-lg font-bold text-blue-600">${account.available_credit.toFixed(2)}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Total Charges</p>
                    <p className="text-lg font-medium">${account.total_charges.toFixed(2)}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Total Payments</p>
                    <p className="text-lg font-medium text-green-600">${account.total_payments.toFixed(2)}</p>
                  </div>
                </div>

                {/* Credit Utilization */}
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span>Credit Utilization</span>
                    <span>{utilizationPercentage.toFixed(1)}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${
                        utilizationPercentage > 75 ? 'bg-red-500' :
                        utilizationPercentage > 50 ? 'bg-yellow-500' : 'bg-green-500'
                      }`}
                      style={{ width: `${Math.min(utilizationPercentage, 100)}%` }}
                    ></div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Quick Actions */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings className="h-5 w-5" />
                  Quick Actions
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Credit Adjustment */}
                <div className="space-y-2">
                  <Label>Adjust Account Credit</Label>
                  <div className="flex gap-2">
                    <Input
                      type="number"
                      step="0.01"
                      placeholder="Amount"
                      value={creditAdjustment}
                      onChange={(e) => setCreditAdjustment(e.target.value)}
                      className="w-32"
                    />
                    <Input
                      placeholder="Reason"
                      value={adjustmentReason}
                      onChange={(e) => setAdjustmentReason(e.target.value)}
                      className="flex-1"
                    />
                    <Button onClick={adjustCredit} disabled={!creditAdjustment || !adjustmentReason}>
                      Apply
                    </Button>
                  </div>
                </div>

                {/* Auto Payment */}
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">Auto Payment</p>
                    <p className="text-sm text-gray-600">
                      {account.auto_payment_setup?.enabled ? 'Enabled' : 'Disabled'}
                    </p>
                  </div>
                  <Button
                    variant={account.auto_payment_setup?.enabled ? "destructive" : "default"}
                    onClick={enableAutoPayment}
                  >
                    {account.auto_payment_setup?.enabled ? 'Disable' : 'Enable'}
                  </Button>
                </div>

                {/* Payment Plan */}
                {account.current_balance < 0 && account.active_payment_plans.length === 0 && (
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium">Payment Plan</p>
                      <p className="text-sm text-gray-600">Setup installment payments</p>
                    </div>
                    <Button variant="outline">
                      Create Plan
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="payments" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Payment History</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {account.payment_history.map(payment => (
                  <div key={payment.id} className="flex items-center justify-between p-4 border rounded-lg">
                    <div className="flex items-center gap-4">
                      <div className={`p-2 rounded-full ${payment.status === 'completed' ? 'bg-green-100' : 'bg-yellow-100'}`}>
                        {payment.status === 'completed' ? (
                          <CheckCircle className="h-4 w-4 text-green-600" />
                        ) : (
                          <Clock className="h-4 w-4 text-yellow-600" />
                        )}
                      </div>
                      <div>
                        <p className="font-medium">${payment.amount.toFixed(2)}</p>
                        <p className="text-sm text-gray-600">
                          {payment.payment_method} • {payment.receipt_number}
                        </p>
                        <p className="text-sm text-gray-600">
                          {format(new Date(payment.processed_date), 'MMM dd, yyyy HH:mm')}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <Badge variant={payment.status === 'completed' ? 'default' : 'secondary'}>
                        {payment.status}
                      </Badge>
                      <p className="text-sm text-gray-600 mt-1">{payment.transaction_id}</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="plans" className="space-y-4">
          {account.active_payment_plans.length > 0 ? (
            account.active_payment_plans.map(plan => (
              <Card key={plan.id}>
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <span>Payment Plan #{plan.id}</span>
                    <Badge variant="default">{plan.status}</Badge>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <p className="text-sm text-gray-600">Total Amount</p>
                      <p className="font-medium">${plan.total_amount.toFixed(2)}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600">Down Payment</p>
                      <p className="font-medium text-green-600">${plan.down_payment.toFixed(2)}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600">Auto Debit</p>
                      <p className="font-medium">{plan.auto_debit_enabled ? 'Enabled' : 'Disabled'}</p>
                    </div>
                  </div>

                  <div>
                    <h4 className="font-medium mb-2">Installments</h4>
                    <div className="space-y-2">
                      {plan.installments.map((installment, index) => (
                        <div key={installment.id} className="flex justify-between items-center p-3 bg-gray-50 rounded">
                          <div>
                            <p className="font-medium">Installment {index + 1}</p>
                            <p className="text-sm text-gray-600">Due: {format(new Date(installment.due_date), 'MMM dd, yyyy')}</p>
                          </div>
                          <div className="text-right">
                            <p className="font-medium">${installment.amount.toFixed(2)}</p>
                            <Badge variant={installment.status === 'paid' ? 'default' : installment.status === 'overdue' ? 'destructive' : 'secondary'}>
                              {installment.status}
                            </Badge>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))
          ) : (
            <Card>
              <CardContent className="text-center py-8">
                <Calendar className="h-12 w-12 mx-auto mb-4 text-gray-400" />
                <p className="text-gray-600">No active payment plans</p>
                {account.current_balance < 0 && (
                  <Button className="mt-4">Create Payment Plan</Button>
                )}
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="aid" className="space-y-4">
          {account.financial_aid.length > 0 ? (
            account.financial_aid.map(aid => (
              <Card key={aid.id}>
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <span>{aid.source}</span>
                    <Badge variant="default">{aid.status}</Badge>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <p className="text-sm text-gray-600">Type</p>
                      <p className="font-medium">{aid.type}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600">Amount</p>
                      <p className="font-medium">${aid.amount.toFixed(2)}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600">Academic Year</p>
                      <p className="font-medium">{aid.academic_year}</p>
                    </div>
                  </div>

                  {aid.requirements.length > 0 && (
                    <div>
                      <h4 className="font-medium mb-2">Requirements</h4>
                      <ul className="space-y-1">
                        {aid.requirements.map((req, index) => (
                          <li key={index} className="text-sm text-gray-600 flex items-center gap-2">
                            <CheckCircle className="h-4 w-4 text-green-500" />
                            {req}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div>
                    <h4 className="font-medium mb-2">Disbursements</h4>
                    <div className="space-y-2">
                      {aid.disbursement_schedule.map((disbursement, index) => (
                        <div key={disbursement.id} className="flex justify-between items-center p-3 bg-gray-50 rounded">
                          <div>
                            <p className="font-medium">Disbursement {index + 1}</p>
                            <p className="text-sm text-gray-600">
                              {format(new Date(disbursement.disbursement_date), 'MMM dd, yyyy')}
                            </p>
                          </div>
                          <div className="text-right">
                            <p className="font-medium">${disbursement.amount.toFixed(2)}</p>
                            <Badge variant={disbursement.status === 'disbursed' ? 'default' : 'secondary'}>
                              {disbursement.status}
                            </Badge>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))
          ) : (
            <Card>
              <CardContent className="text-center py-8">
                <DollarSign className="h-12 w-12 mx-auto mb-4 text-gray-400" />
                <p className="text-gray-600">No financial aid records</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="settings" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Account Settings</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Auto Payment Settings */}
              <div>
                <h4 className="font-medium mb-4">Auto Payment Settings</h4>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium">Auto Payment</p>
                      <p className="text-sm text-gray-600">
                        {account.auto_payment_setup?.enabled
                          ? `Enabled • Next payment: ${account.auto_payment_setup.next_payment_date}`
                          : 'Disabled'
                        }
                      </p>
                    </div>
                    <Button variant="outline">
                      {account.auto_payment_setup?.enabled ? 'Update' : 'Setup'}
                    </Button>
                  </div>

                  {account.auto_payment_setup?.enabled && (
                    <div className="p-4 bg-blue-50 rounded-lg">
                      <p className="text-sm font-medium text-blue-900">Payment Method</p>
                      <p className="text-sm text-blue-700">
                        {account.auto_payment_setup.payment_method} ending in {account.auto_payment_setup.account_details.last_four}
                      </p>
                    </div>
                  )}
                </div>
              </div>

              {/* Notification Preferences */}
              <div>
                <h4 className="font-medium mb-4">Notification Preferences</h4>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium">Payment Reminders</p>
                      <p className="text-sm text-gray-600">Email notifications for upcoming payments</p>
                    </div>
                    <Button variant="outline">Configure</Button>
                  </div>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium">Balance Alerts</p>
                      <p className="text-sm text-gray-600">Notifications when balance is low</p>
                    </div>
                    <Button variant="outline">Configure</Button>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Quick Payment Modal */}
      <QuickPayment
        isOpen={showQuickPayment}
        onClose={() => setShowQuickPayment(false)}
        preselectedStudent={{
          id: studentId,
          student_id: account.student_id,
          first_name: account.student_name.split(' ')[0],
          last_name: account.student_name.split(' ').slice(1).join(' '),
          email: '',
          phone: '',
          account_balance: account.current_balance
        }}
        onPaymentComplete={() => {
          setShowQuickPayment(false);
          loadAccount();
        }}
      />
    </div>
  );
};

export default StudentAccountDashboard;