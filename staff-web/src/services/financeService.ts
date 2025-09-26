/**
 * Financial Service API Layer
 * Handles all financial-related API communications with enhanced error handling
 * and real-time capabilities
 */

import { apiClient } from './apiClient';
import {
  Invoice,
  Payment,
  StudentAccount,
  CashierSession,
  POSTransaction,
  Scholarship,
  FinancialMetrics,
  PaymentPrediction,
  FraudAlert,
  InvoiceFilters,
  PaymentFilters,
  FinancialReportParams,
  FinancialApiResponse,
  PaymentPlan,
  FinancialAid
} from '../types/finance.types';

class FinanceService {
  private baseUrl = '/api/v2/finance';
  private wsConnection: WebSocket | null = null;

  // Real-time WebSocket connection for payment updates
  initializeWebSocket(callbacks: {
    onPaymentUpdate?: (payment: Payment) => void;
    onInvoiceUpdate?: (invoice: Invoice) => void;
    onFraudAlert?: (alert: FraudAlert) => void;
  }) {
    const wsUrl = `ws://localhost:8000/ws/finance/`;
    this.wsConnection = new WebSocket(wsUrl);

    this.wsConnection.onmessage = (event) => {
      const data = JSON.parse(event.data);

      switch (data.type) {
        case 'payment_update':
          callbacks.onPaymentUpdate?.(data.payload);
          break;
        case 'invoice_update':
          callbacks.onInvoiceUpdate?.(data.payload);
          break;
        case 'fraud_alert':
          callbacks.onFraudAlert?.(data.payload);
          break;
      }
    };

    this.wsConnection.onclose = () => {
      // Auto-reconnect after 5 seconds
      setTimeout(() => this.initializeWebSocket(callbacks), 5000);
    };
  }

  disconnectWebSocket() {
    if (this.wsConnection) {
      this.wsConnection.close();
      this.wsConnection = null;
    }
  }

  // Invoice Management
  async getInvoices(filters?: InvoiceFilters, page = 1, pageSize = 50): Promise<FinancialApiResponse<Invoice[]>> {
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString(),
      ...filters
    });

    return apiClient.get(`${this.baseUrl}/invoices/?${params}`);
  }

  async getInvoice(invoiceId: string): Promise<FinancialApiResponse<Invoice>> {
    return apiClient.get(`${this.baseUrl}/invoices/${invoiceId}/`);
  }

  async createInvoice(invoiceData: Partial<Invoice>): Promise<FinancialApiResponse<Invoice>> {
    return apiClient.post(`${this.baseUrl}/invoices/`, invoiceData);
  }

  async updateInvoice(invoiceId: string, updates: Partial<Invoice>): Promise<FinancialApiResponse<Invoice>> {
    return apiClient.patch(`${this.baseUrl}/invoices/${invoiceId}/`, updates);
  }

  async deleteInvoice(invoiceId: string): Promise<FinancialApiResponse<void>> {
    return apiClient.delete(`${this.baseUrl}/invoices/${invoiceId}/`);
  }

  async sendInvoiceReminder(invoiceId: string): Promise<FinancialApiResponse<void>> {
    return apiClient.post(`${this.baseUrl}/invoices/${invoiceId}/send-reminder/`);
  }

  async bulkInvoiceOperations(invoiceIds: string[], operation: string, data?: any): Promise<FinancialApiResponse<void>> {
    return apiClient.post(`${this.baseUrl}/invoices/bulk-operations/`, {
      invoice_ids: invoiceIds,
      operation,
      data
    });
  }

  // Payment Processing
  async processPayment(paymentData: {
    student_id: string;
    amount: number;
    payment_method: string;
    invoice_id?: string;
    notes?: string;
  }): Promise<FinancialApiResponse<Payment>> {
    return apiClient.post(`${this.baseUrl}/payments/process/`, paymentData);
  }

  async getPayments(filters?: PaymentFilters, page = 1, pageSize = 50): Promise<FinancialApiResponse<Payment[]>> {
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString(),
      ...filters
    });

    return apiClient.get(`${this.baseUrl}/payments/?${params}`);
  }

  async getPayment(paymentId: string): Promise<FinancialApiResponse<Payment>> {
    return apiClient.get(`${this.baseUrl}/payments/${paymentId}/`);
  }

  async refundPayment(paymentId: string, amount?: number, reason?: string): Promise<FinancialApiResponse<Payment>> {
    return apiClient.post(`${this.baseUrl}/payments/${paymentId}/refund/`, {
      amount,
      reason
    });
  }

  async voidPayment(paymentId: string, reason: string): Promise<FinancialApiResponse<Payment>> {
    return apiClient.post(`${this.baseUrl}/payments/${paymentId}/void/`, { reason });
  }

  // Student Account Management
  async getStudentAccount(studentId: string): Promise<FinancialApiResponse<StudentAccount>> {
    return apiClient.get(`${this.baseUrl}/accounts/${studentId}/`);
  }

  async getStudentAccountActivity(
    studentId: string,
    startDate?: string,
    endDate?: string
  ): Promise<FinancialApiResponse<Payment[]>> {
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);

    return apiClient.get(`${this.baseUrl}/accounts/${studentId}/activity/?${params}`);
  }

  async updateAccountCredit(studentId: string, amount: number, reason: string): Promise<FinancialApiResponse<StudentAccount>> {
    return apiClient.post(`${this.baseUrl}/accounts/${studentId}/adjust-credit/`, {
      amount,
      reason
    });
  }

  async setupAutoPayment(studentId: string, autoPaymentData: any): Promise<FinancialApiResponse<void>> {
    return apiClient.post(`${this.baseUrl}/accounts/${studentId}/auto-payment/`, autoPaymentData);
  }

  // Payment Plans
  async createPaymentPlan(paymentPlanData: Partial<PaymentPlan>): Promise<FinancialApiResponse<PaymentPlan>> {
    return apiClient.post(`${this.baseUrl}/payment-plans/`, paymentPlanData);
  }

  async getPaymentPlans(studentId?: string): Promise<FinancialApiResponse<PaymentPlan[]>> {
    const params = studentId ? `?student_id=${studentId}` : '';
    return apiClient.get(`${this.baseUrl}/payment-plans/${params}`);
  }

  async updatePaymentPlan(planId: string, updates: Partial<PaymentPlan>): Promise<FinancialApiResponse<PaymentPlan>> {
    return apiClient.patch(`${this.baseUrl}/payment-plans/${planId}/`, updates);
  }

  // POS System
  async createPOSTransaction(transactionData: {
    student_id: string;
    items: Array<{
      description: string;
      amount: number;
      tax_rate?: number;
      category?: string;
    }>;
    payment_method: string;
  }): Promise<FinancialApiResponse<POSTransaction>> {
    return apiClient.post(`${this.baseUrl}/pos/transactions/`, transactionData);
  }

  async getPOSTransactions(cashierId?: string, date?: string): Promise<FinancialApiResponse<POSTransaction[]>> {
    const params = new URLSearchParams();
    if (cashierId) params.append('cashier_id', cashierId);
    if (date) params.append('date', date);

    return apiClient.get(`${this.baseUrl}/pos/transactions/?${params}`);
  }

  async refundPOSTransaction(transactionId: string, amount?: number): Promise<FinancialApiResponse<POSTransaction>> {
    return apiClient.post(`${this.baseUrl}/pos/transactions/${transactionId}/refund/`, { amount });
  }

  async printReceipt(transactionId: string): Promise<FinancialApiResponse<void>> {
    return apiClient.post(`${this.baseUrl}/pos/transactions/${transactionId}/print-receipt/`);
  }

  // Cashier Sessions
  async startCashierSession(startingCash: number): Promise<FinancialApiResponse<CashierSession>> {
    return apiClient.post(`${this.baseUrl}/cashier/sessions/start/`, {
      starting_cash: startingCash
    });
  }

  async endCashierSession(sessionId: string, actualCash: number): Promise<FinancialApiResponse<CashierSession>> {
    return apiClient.post(`${this.baseUrl}/cashier/sessions/${sessionId}/end/`, {
      actual_cash: actualCash
    });
  }

  async getCurrentCashierSession(): Promise<FinancialApiResponse<CashierSession | null>> {
    return apiClient.get(`${this.baseUrl}/cashier/sessions/current/`);
  }

  async getCashierSessions(cashierId?: string, startDate?: string, endDate?: string): Promise<FinancialApiResponse<CashierSession[]>> {
    const params = new URLSearchParams();
    if (cashierId) params.append('cashier_id', cashierId);
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);

    return apiClient.get(`${this.baseUrl}/cashier/sessions/?${params}`);
  }

  // Scholarships
  async getScholarships(active?: boolean): Promise<FinancialApiResponse<Scholarship[]>> {
    const params = active !== undefined ? `?active=${active}` : '';
    return apiClient.get(`${this.baseUrl}/scholarships/${params}`);
  }

  async getScholarship(scholarshipId: string): Promise<FinancialApiResponse<Scholarship>> {
    return apiClient.get(`${this.baseUrl}/scholarships/${scholarshipId}/`);
  }

  async createScholarship(scholarshipData: Partial<Scholarship>): Promise<FinancialApiResponse<Scholarship>> {
    return apiClient.post(`${this.baseUrl}/scholarships/`, scholarshipData);
  }

  async updateScholarship(scholarshipId: string, updates: Partial<Scholarship>): Promise<FinancialApiResponse<Scholarship>> {
    return apiClient.patch(`${this.baseUrl}/scholarships/${scholarshipId}/`, updates);
  }

  async awardScholarship(scholarshipId: string, studentId: string, amount: number, academicYear: string): Promise<FinancialApiResponse<void>> {
    return apiClient.post(`${this.baseUrl}/scholarships/${scholarshipId}/award/`, {
      student_id: studentId,
      amount,
      academic_year: academicYear
    });
  }

  // Financial Aid
  async getFinancialAid(studentId?: string): Promise<FinancialApiResponse<FinancialAid[]>> {
    const params = studentId ? `?student_id=${studentId}` : '';
    return apiClient.get(`${this.baseUrl}/financial-aid/${params}`);
  }

  async processAidDisbursement(aidId: string, amount: number): Promise<FinancialApiResponse<void>> {
    return apiClient.post(`${this.baseUrl}/financial-aid/${aidId}/disburse/`, { amount });
  }

  // Analytics and Reporting
  async getFinancialMetrics(
    startDate?: string,
    endDate?: string,
    groupBy?: string
  ): Promise<FinancialApiResponse<FinancialMetrics>> {
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    if (groupBy) params.append('group_by', groupBy);

    return apiClient.get(`${this.baseUrl}/analytics/metrics/?${params}`);
  }

  async generateReport(reportParams: FinancialReportParams): Promise<FinancialApiResponse<any>> {
    return apiClient.post(`${this.baseUrl}/reports/generate/`, reportParams);
  }

  async exportData(type: string, filters?: any, format = 'csv'): Promise<Blob> {
    const response = await apiClient.post(`${this.baseUrl}/export/`, {
      type,
      filters,
      format
    }, {
      responseType: 'blob'
    });
    return response.data;
  }

  // AI-Powered Features
  async getPaymentPredictions(studentId?: string): Promise<FinancialApiResponse<PaymentPrediction[]>> {
    const params = studentId ? `?student_id=${studentId}` : '';
    return apiClient.get(`${this.baseUrl}/ai/payment-predictions/${params}`);
  }

  async getFraudAlerts(status?: string): Promise<FinancialApiResponse<FraudAlert[]>> {
    const params = status ? `?status=${status}` : '';
    return apiClient.get(`${this.baseUrl}/ai/fraud-alerts/${params}`);
  }

  async updateFraudAlert(alertId: string, status: string, notes?: string): Promise<FinancialApiResponse<FraudAlert>> {
    return apiClient.patch(`${this.baseUrl}/ai/fraud-alerts/${alertId}/`, {
      status,
      notes
    });
  }

  async getCollectionRecommendations(studentId: string): Promise<FinancialApiResponse<any>> {
    return apiClient.get(`${this.baseUrl}/ai/collection-recommendations/${studentId}/`);
  }

  // Automation
  async getAutomationRules(): Promise<FinancialApiResponse<any[]>> {
    return apiClient.get(`${this.baseUrl}/automation/rules/`);
  }

  async createAutomationRule(ruleData: any): Promise<FinancialApiResponse<any>> {
    return apiClient.post(`${this.baseUrl}/automation/rules/`, ruleData);
  }

  async toggleAutomationRule(ruleId: string, enabled: boolean): Promise<FinancialApiResponse<any>> {
    return apiClient.patch(`${this.baseUrl}/automation/rules/${ruleId}/`, { enabled });
  }

  async runAutomationRule(ruleId: string): Promise<FinancialApiResponse<any>> {
    return apiClient.post(`${this.baseUrl}/automation/rules/${ruleId}/run/`);
  }

  // Utility methods
  async validatePaymentMethod(paymentMethodData: any): Promise<FinancialApiResponse<boolean>> {
    return apiClient.post(`${this.baseUrl}/validate/payment-method/`, paymentMethodData);
  }

  async calculateTax(amount: number, location?: string): Promise<FinancialApiResponse<{ tax_amount: number; tax_rate: number }>> {
    return apiClient.post(`${this.baseUrl}/calculate/tax/`, { amount, location });
  }

  async verifyBankAccount(accountData: any): Promise<FinancialApiResponse<boolean>> {
    return apiClient.post(`${this.baseUrl}/verify/bank-account/`, accountData);
  }

  async sendPaymentConfirmation(paymentId: string, method: 'email' | 'sms'): Promise<FinancialApiResponse<void>> {
    return apiClient.post(`${this.baseUrl}/payments/${paymentId}/send-confirmation/`, { method });
  }
}

export const financeService = new FinanceService();
export default financeService;