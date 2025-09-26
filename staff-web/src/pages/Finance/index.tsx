/**
 * Finance Module Main Page
 * Central hub for all financial management features
 */

import React, { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import {
  DollarSign, CreditCard, FileText, BarChart3, Users, Calculator,
  PlusCircle, TrendingUp, AlertTriangle, Clock
} from 'lucide-react';

// Import all finance components
import InvoiceList from './Invoices/InvoiceList';
import POSInterface from './Payments/POSInterface';
import StudentAccountDashboard from './Accounts/StudentAccount';
import CashierDashboard from './Cashier/CashierDashboard';
import FinanceAnalytics from './Analytics/FinanceAnalytics';

export const FinancePage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('overview');
  const [selectedStudentId, setSelectedStudentId] = useState<string | null>(null);

  // Mock summary data
  const summaryData = {
    totalRevenue: 284650.75,
    outstandingBalance: 45280.25,
    monthlyTarget: 300000,
    collectionRate: 89.5,
    activeInvoices: 156,
    paidInvoices: 642,
    overdueInvoices: 23,
    todayTransactions: 18,
    todayRevenue: 4850.00
  };

  const progressPercentage = (summaryData.totalRevenue / summaryData.monthlyTarget) * 100;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold">Financial Management</h1>
          <p className="text-gray-600">Comprehensive financial operations and analytics</p>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={() => setActiveTab('pos')}>
            <PlusCircle className="h-4 w-4 mr-2" />
            New Transaction
          </Button>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-6">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="invoices">Invoices</TabsTrigger>
          <TabsTrigger value="pos">POS System</TabsTrigger>
          <TabsTrigger value="accounts">Accounts</TabsTrigger>
          <TabsTrigger value="cashier">Cashier</TabsTrigger>
          <TabsTrigger value="analytics">Analytics</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          {/* Overview Dashboard */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {/* Revenue Card */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Monthly Revenue</CardTitle>
                <DollarSign className="h-4 w-4 text-green-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-green-600">
                  ${summaryData.totalRevenue.toLocaleString()}
                </div>
                <div className="text-xs text-gray-600 mt-1">
                  Target: ${summaryData.monthlyTarget.toLocaleString()}
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                  <div
                    className="bg-green-500 h-2 rounded-full"
                    style={{ width: `${Math.min(progressPercentage, 100)}%` }}
                  ></div>
                </div>
                <p className="text-xs text-gray-600 mt-1">
                  {progressPercentage.toFixed(1)}% of monthly target
                </p>
              </CardContent>
            </Card>

            {/* Collection Rate Card */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Collection Rate</CardTitle>
                <TrendingUp className="h-4 w-4 text-blue-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-blue-600">
                  {summaryData.collectionRate}%
                </div>
                <p className="text-xs text-gray-600">
                  +2.3% from last month
                </p>
                <Badge variant={summaryData.collectionRate >= 90 ? "default" : "secondary"} className="mt-2">
                  {summaryData.collectionRate >= 90 ? "Excellent" : "Good"}
                </Badge>
              </CardContent>
            </Card>

            {/* Outstanding Balance Card */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Outstanding</CardTitle>
                <AlertTriangle className="h-4 w-4 text-orange-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-orange-600">
                  ${summaryData.outstandingBalance.toLocaleString()}
                </div>
                <p className="text-xs text-gray-600">
                  {summaryData.overdueInvoices} overdue invoices
                </p>
                <Badge variant="destructive" className="mt-2">
                  Needs Attention
                </Badge>
              </CardContent>
            </Card>

            {/* Today's Activity Card */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Today's Activity</CardTitle>
                <Clock className="h-4 w-4 text-purple-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-purple-600">
                  {summaryData.todayTransactions}
                </div>
                <p className="text-xs text-gray-600">
                  ${summaryData.todayRevenue.toLocaleString()} collected
                </p>
                <Badge variant="default" className="mt-2">
                  Active
                </Badge>
              </CardContent>
            </Card>
          </div>

          {/* Quick Actions */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card className="cursor-pointer hover:shadow-lg transition-shadow" onClick={() => setActiveTab('invoices')}>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="h-5 w-5 text-blue-500" />
                  Invoice Management
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">Active:</span>
                    <span className="font-medium">{summaryData.activeInvoices}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">Paid:</span>
                    <span className="font-medium text-green-600">{summaryData.paidInvoices}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">Overdue:</span>
                    <span className="font-medium text-red-600">{summaryData.overdueInvoices}</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="cursor-pointer hover:shadow-lg transition-shadow" onClick={() => setActiveTab('pos')}>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <CreditCard className="h-5 w-5 text-green-500" />
                  Point of Sale
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-gray-600 mb-4">Process payments, handle transactions, and manage cash operations</p>
                <Button className="w-full">
                  Open POS System
                </Button>
              </CardContent>
            </Card>

            <Card className="cursor-pointer hover:shadow-lg transition-shadow" onClick={() => setActiveTab('analytics')}>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="h-5 w-5 text-purple-500" />
                  Financial Analytics
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-gray-600 mb-4">AI-powered insights, forecasting, and comprehensive reporting</p>
                <Button variant="outline" className="w-full">
                  View Analytics
                </Button>
              </CardContent>
            </Card>
          </div>

          {/* Recent Activity */}
          <Card>
            <CardHeader>
              <CardTitle>Recent Activity</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-green-100 rounded-full">
                      <DollarSign className="h-4 w-4 text-green-600" />
                    </div>
                    <div>
                      <p className="font-medium">Payment Received</p>
                      <p className="text-sm text-gray-600">John Doe - $540.00 via Credit Card</p>
                    </div>
                  </div>
                  <span className="text-sm text-gray-500">2 min ago</span>
                </div>

                <div className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-blue-100 rounded-full">
                      <FileText className="h-4 w-4 text-blue-600" />
                    </div>
                    <div>
                      <p className="font-medium">Invoice Created</p>
                      <p className="text-sm text-gray-600">INV-2024-158 - Jane Smith - $1,200.00</p>
                    </div>
                  </div>
                  <span className="text-sm text-gray-500">15 min ago</span>
                </div>

                <div className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-yellow-100 rounded-full">
                      <AlertTriangle className="h-4 w-4 text-yellow-600" />
                    </div>
                    <div>
                      <p className="font-medium">Payment Overdue</p>
                      <p className="text-sm text-gray-600">INV-2024-143 - Michael Johnson - $485.75</p>
                    </div>
                  </div>
                  <span className="text-sm text-gray-500">1 hour ago</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="invoices">
          <InvoiceList />
        </TabsContent>

        <TabsContent value="pos">
          <POSInterface />
        </TabsContent>

        <TabsContent value="accounts">
          {selectedStudentId ? (
            <div className="space-y-4">
              <Button
                variant="outline"
                onClick={() => setSelectedStudentId(null)}
                className="mb-4"
              >
                ← Back to Student Search
              </Button>
              <StudentAccountDashboard studentId={selectedStudentId} />
            </div>
          ) : (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Users className="h-5 w-5" />
                  Student Account Management
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-gray-600 mb-6">Select a student to view their financial account details</p>

                {/* Student Selection - Mock for demo */}
                <div className="space-y-3">
                  {[
                    { id: '1', name: 'John Doe', studentId: 'STU001', balance: -485.75 },
                    { id: '2', name: 'Jane Smith', studentId: 'STU002', balance: 0.00 },
                    { id: '3', name: 'Michael Johnson', studentId: 'STU003', balance: -150.25 }
                  ].map(student => (
                    <div
                      key={student.id}
                      className="flex items-center justify-between p-4 border rounded-lg cursor-pointer hover:bg-gray-50"
                      onClick={() => setSelectedStudentId(student.id)}
                    >
                      <div>
                        <p className="font-medium">{student.name}</p>
                        <p className="text-sm text-gray-600">{student.studentId}</p>
                      </div>
                      <Badge variant={student.balance < 0 ? "destructive" : "default"}>
                        ${Math.abs(student.balance).toFixed(2)}
                        {student.balance < 0 && ' Owed'}
                      </Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="cashier">
          <CashierDashboard />
        </TabsContent>

        <TabsContent value="analytics">
          <FinanceAnalytics />
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default FinancePage;