/**
 * Financial Management Types
 * Comprehensive type definitions for the financial management module
 */

// Base financial types
export interface Invoice {
  id: string;
  invoice_number: string;
  student_id: string;
  student_name: string;
  amount: number;
  tax_amount: number;
  total_amount: number;
  status: InvoiceStatus;
  due_date: string;
  created_date: string;
  paid_date?: string;
  description: string;
  line_items: InvoiceLineItem[];
  payment_plans: PaymentPlan[];
  discounts: Discount[];
  attachments: Document[];
  payment_history: Payment[];
}

export interface InvoiceLineItem {
  id: string;
  description: string;
  quantity: number;
  unit_price: number;
  tax_rate: number;
  total: number;
  course_id?: string;
  service_type: string;
}

export interface Payment {
  id: string;
  invoice_id?: string;
  student_id: string;
  amount: number;
  payment_method: PaymentMethod;
  status: PaymentStatus;
  transaction_id: string;
  processed_date: string;
  gateway_response?: GatewayResponse;
  cashier_id?: string;
  notes?: string;
  receipt_number: string;
}

export interface PaymentPlan {
  id: string;
  invoice_id: string;
  total_amount: number;
  down_payment: number;
  installments: PaymentInstallment[];
  status: PaymentPlanStatus;
  created_date: string;
  auto_debit_enabled: boolean;
  late_fee_policy: LateFeePolicy;
}

export interface PaymentInstallment {
  id: string;
  payment_plan_id: string;
  amount: number;
  due_date: string;
  status: InstallmentStatus;
  payment_id?: string;
  late_fee?: number;
}

export interface StudentAccount {
  student_id: string;
  student_name: string;
  current_balance: number;
  available_credit: number;
  total_payments: number;
  total_charges: number;
  payment_history: Payment[];
  active_payment_plans: PaymentPlan[];
  account_holds: AccountHold[];
  auto_payment_setup?: AutoPaymentSetup;
  financial_aid: FinancialAid[];
}

export interface CashierSession {
  id: string;
  cashier_id: string;
  cashier_name: string;
  start_time: string;
  end_time?: string;
  starting_cash: number;
  expected_cash: number;
  actual_cash?: number;
  variance?: number;
  transaction_count: number;
  total_collected: number;
  payments_by_method: PaymentMethodSummary[];
  status: CashierSessionStatus;
}

export interface POSTransaction {
  id: string;
  student_id: string;
  student_name: string;
  items: POSItem[];
  subtotal: number;
  tax: number;
  total: number;
  payment_method: PaymentMethod;
  status: POSTransactionStatus;
  cashier_id: string;
  timestamp: string;
  receipt_printed: boolean;
}

export interface POSItem {
  id: string;
  description: string;
  amount: number;
  tax_rate: number;
  category: string;
}

export interface Scholarship {
  id: string;
  name: string;
  description: string;
  amount: number;
  type: ScholarshipType;
  eligibility_criteria: EligibilityCriteria;
  application_deadline?: string;
  renewable: boolean;
  max_renewals?: number;
  funding_source: string;
  active: boolean;
  recipients: ScholarshipRecipient[];
}

export interface ScholarshipRecipient {
  id: string;
  scholarship_id: string;
  student_id: string;
  student_name: string;
  award_amount: number;
  academic_year: string;
  status: ScholarshipStatus;
  disbursements: ScholarshipDisbursement[];
}

export interface FinancialAid {
  id: string;
  student_id: string;
  type: FinancialAidType;
  amount: number;
  academic_year: string;
  status: FinancialAidStatus;
  source: string;
  requirements: string[];
  disbursement_schedule: AidDisbursement[];
}

// Enums
export enum InvoiceStatus {
  DRAFT = 'draft',
  SENT = 'sent',
  PENDING = 'pending',
  PAID = 'paid',
  OVERDUE = 'overdue',
  CANCELLED = 'cancelled',
  REFUNDED = 'refunded'
}

export enum PaymentMethod {
  CASH = 'cash',
  CREDIT_CARD = 'credit_card',
  DEBIT_CARD = 'debit_card',
  BANK_TRANSFER = 'bank_transfer',
  CHECK = 'check',
  MOBILE_PAYMENT = 'mobile_payment',
  DIGITAL_WALLET = 'digital_wallet',
  CRYPTOCURRENCY = 'cryptocurrency'
}

export enum PaymentStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled',
  REFUNDED = 'refunded',
  PARTIALLY_REFUNDED = 'partially_refunded'
}

export enum PaymentPlanStatus {
  ACTIVE = 'active',
  COMPLETED = 'completed',
  DEFAULTED = 'defaulted',
  CANCELLED = 'cancelled',
  SUSPENDED = 'suspended'
}

export enum InstallmentStatus {
  PENDING = 'pending',
  PAID = 'paid',
  OVERDUE = 'overdue',
  WAIVED = 'waived'
}

export enum CashierSessionStatus {
  ACTIVE = 'active',
  CLOSED = 'closed',
  RECONCILED = 'reconciled',
  DISCREPANCY = 'discrepancy'
}

export enum POSTransactionStatus {
  PENDING = 'pending',
  COMPLETED = 'completed',
  FAILED = 'failed',
  REFUNDED = 'refunded'
}

export enum ScholarshipType {
  MERIT = 'merit',
  NEED_BASED = 'need_based',
  ATHLETIC = 'athletic',
  ACADEMIC = 'academic',
  DIVERSITY = 'diversity',
  COMMUNITY_SERVICE = 'community_service'
}

export enum ScholarshipStatus {
  AWARDED = 'awarded',
  ACTIVE = 'active',
  COMPLETED = 'completed',
  REVOKED = 'revoked',
  SUSPENDED = 'suspended'
}

export enum FinancialAidType {
  GRANT = 'grant',
  LOAN = 'loan',
  WORK_STUDY = 'work_study',
  SCHOLARSHIP = 'scholarship'
}

export enum FinancialAidStatus {
  APPLIED = 'applied',
  APPROVED = 'approved',
  DISBURSED = 'disbursed',
  COMPLETED = 'completed',
  DENIED = 'denied'
}

// Supporting types
export interface GatewayResponse {
  transaction_id: string;
  gateway: string;
  response_code: string;
  response_message: string;
  authorization_code?: string;
  batch_id?: string;
}

export interface PaymentMethodSummary {
  method: PaymentMethod;
  count: number;
  total_amount: number;
}

export interface Discount {
  id: string;
  name: string;
  type: 'percentage' | 'fixed';
  value: number;
  description: string;
  conditions?: string[];
}

export interface Document {
  id: string;
  name: string;
  type: string;
  url: string;
  uploaded_date: string;
  size: number;
}

export interface AccountHold {
  id: string;
  type: string;
  description: string;
  amount?: number;
  placed_date: string;
  released_date?: string;
  active: boolean;
}

export interface AutoPaymentSetup {
  id: string;
  payment_method: PaymentMethod;
  account_details: any;
  enabled: boolean;
  next_payment_date?: string;
}

export interface LateFeePolicy {
  grace_period_days: number;
  fee_amount: number;
  fee_type: 'percentage' | 'fixed';
  max_fees?: number;
}

export interface EligibilityCriteria {
  min_gpa?: number;
  max_income?: number;
  academic_program?: string[];
  citizenship_requirements?: string[];
  other_requirements?: string[];
}

export interface ScholarshipDisbursement {
  id: string;
  amount: number;
  disbursement_date: string;
  status: 'pending' | 'disbursed' | 'failed';
  payment_id?: string;
}

export interface AidDisbursement {
  id: string;
  amount: number;
  disbursement_date: string;
  status: 'pending' | 'disbursed' | 'failed';
  requirements_met: boolean;
}

// Analytics types
export interface FinancialMetrics {
  total_revenue: number;
  outstanding_balance: number;
  collection_rate: number;
  average_payment_time: number;
  monthly_trends: MonthlyTrend[];
  payment_method_breakdown: PaymentMethodSummary[];
  top_revenue_sources: RevenueSource[];
}

export interface MonthlyTrend {
  month: string;
  revenue: number;
  collections: number;
  new_invoices: number;
  payment_count: number;
}

export interface RevenueSource {
  source: string;
  amount: number;
  percentage: number;
  student_count: number;
}

// AI-powered features
export interface PaymentPrediction {
  student_id: string;
  invoice_id: string;
  predicted_payment_date: string;
  probability: number;
  risk_factors: string[];
  recommendations: string[];
}

export interface FraudAlert {
  id: string;
  transaction_id: string;
  risk_score: number;
  alert_type: string;
  description: string;
  timestamp: string;
  status: 'pending' | 'reviewed' | 'resolved' | 'false_positive';
}

// API Response types
export interface FinancialApiResponse<T> {
  data: T;
  meta?: {
    total: number;
    page: number;
    per_page: number;
    has_next: boolean;
    has_prev: boolean;
  };
  success: boolean;
  message?: string;
}

// Filter and search types
export interface InvoiceFilters {
  status?: InvoiceStatus[];
  student_ids?: string[];
  date_range?: {
    start: string;
    end: string;
  };
  amount_range?: {
    min: number;
    max: number;
  };
  overdue_only?: boolean;
  payment_plan_only?: boolean;
}

export interface PaymentFilters {
  payment_methods?: PaymentMethod[];
  status?: PaymentStatus[];
  date_range?: {
    start: string;
    end: string;
  };
  amount_range?: {
    min: number;
    max: number;
  };
  cashier_ids?: string[];
}

export interface FinancialReportParams {
  type: 'revenue' | 'collections' | 'outstanding' | 'aging' | 'payments';
  date_range: {
    start: string;
    end: string;
  };
  group_by?: 'day' | 'week' | 'month' | 'quarter';
  filters?: any;
  format?: 'json' | 'csv' | 'pdf' | 'excel';
}