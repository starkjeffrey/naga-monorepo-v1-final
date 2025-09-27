/**
 * Finance Utilities
 * Comprehensive utility functions for financial calculations, formatting, and compliance
 */

import { PaymentMethod, InvoiceStatus, PaymentStatus } from '../types/finance.types';
import { CreditCard, Banknote, Smartphone, Building, Bitcoin, Wallet } from 'lucide-react';

// Currency formatting
export const formatCurrency = (amount: number, currency = 'USD', locale = 'en-US'): string => {
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(amount);
};

// Percentage formatting
export const formatPercentage = (value: number, decimals = 1): string => {
  return `${value.toFixed(decimals)}%`;
};

// Date formatting
export const formatDate = (dateString: string, format: 'short' | 'long' | 'relative' = 'short'): string => {
  const date = new Date(dateString);

  if (format === 'relative') {
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays === -1) return 'Tomorrow';
    if (diffDays < 7 && diffDays > 0) return `${diffDays} days ago`;
    if (diffDays > -7 && diffDays < 0) return `In ${Math.abs(diffDays)} days`;
  }

  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: format === 'long' ? 'long' : 'short',
    day: 'numeric'
  });
};

// Get days until due date
export const getDaysUntilDue = (dueDateString: string): number => {
  const dueDate = new Date(dueDateString);
  const today = new Date();
  const diffMs = dueDate.getTime() - today.getTime();
  return Math.ceil(diffMs / (1000 * 60 * 60 * 24));
};

// Status color mapping
export const getStatusColor = (status: InvoiceStatus | PaymentStatus): string => {
  const colorMap = {
    // Invoice statuses
    [InvoiceStatus.DRAFT]: 'text-gray-600',
    [InvoiceStatus.SENT]: 'text-blue-600',
    [InvoiceStatus.PENDING]: 'text-yellow-600',
    [InvoiceStatus.PAID]: 'text-green-600',
    [InvoiceStatus.OVERDUE]: 'text-red-600',
    [InvoiceStatus.CANCELLED]: 'text-gray-600',
    [InvoiceStatus.REFUNDED]: 'text-purple-600',

    // Payment statuses
    [PaymentStatus.PENDING]: 'text-yellow-600',
    [PaymentStatus.PROCESSING]: 'text-blue-600',
    [PaymentStatus.COMPLETED]: 'text-green-600',
    [PaymentStatus.FAILED]: 'text-red-600',
    [PaymentStatus.CANCELLED]: 'text-gray-600',
    [PaymentStatus.REFUNDED]: 'text-purple-600',
    [PaymentStatus.PARTIALLY_REFUNDED]: 'text-orange-600'
  };

  return colorMap[status] || 'text-gray-600';
};

// Payment method icon mapping
export const getPaymentMethodIcon = (method: PaymentMethod) => {
  const iconMap = {
    [PaymentMethod.CASH]: Banknote,
    [PaymentMethod.CREDIT_CARD]: CreditCard,
    [PaymentMethod.DEBIT_CARD]: CreditCard,
    [PaymentMethod.BANK_TRANSFER]: Building,
    [PaymentMethod.CHECK]: Banknote,
    [PaymentMethod.MOBILE_PAYMENT]: Smartphone,
    [PaymentMethod.DIGITAL_WALLET]: Wallet,
    [PaymentMethod.CRYPTOCURRENCY]: Bitcoin
  };

  return iconMap[method] || CreditCard;
};

// Payment method display name
export const getPaymentMethodName = (method: PaymentMethod): string => {
  const nameMap = {
    [PaymentMethod.CASH]: 'Cash',
    [PaymentMethod.CREDIT_CARD]: 'Credit Card',
    [PaymentMethod.DEBIT_CARD]: 'Debit Card',
    [PaymentMethod.BANK_TRANSFER]: 'Bank Transfer',
    [PaymentMethod.CHECK]: 'Check',
    [PaymentMethod.MOBILE_PAYMENT]: 'Mobile Payment',
    [PaymentMethod.DIGITAL_WALLET]: 'Digital Wallet',
    [PaymentMethod.CRYPTOCURRENCY]: 'Cryptocurrency'
  };

  return nameMap[method] || 'Unknown';
};

// Tax calculations
export const calculateTax = (amount: number, taxRate: number): number => {
  return amount * (taxRate / 100);
};

export const calculateAmountWithTax = (amount: number, taxRate: number): number => {
  return amount + calculateTax(amount, taxRate);
};

export const calculateAmountFromTotal = (totalAmount: number, taxRate: number): number => {
  return totalAmount / (1 + taxRate / 100);
};

// Payment plan calculations
export const calculateInstallmentAmount = (
  principal: number,
  numberOfInstallments: number,
  interestRate: number = 0
): number => {
  if (interestRate === 0) {
    return principal / numberOfInstallments;
  }

  const monthlyRate = interestRate / 100 / 12;
  const factor = Math.pow(1 + monthlyRate, numberOfInstallments);
  return (principal * monthlyRate * factor) / (factor - 1);
};

// Interest calculations
export const calculateSimpleInterest = (
  principal: number,
  rate: number,
  timeInYears: number
): number => {
  return principal * (rate / 100) * timeInYears;
};

export const calculateCompoundInterest = (
  principal: number,
  rate: number,
  timeInYears: number,
  compoundingFrequency: number = 12
): number => {
  const factor = Math.pow(1 + (rate / 100) / compoundingFrequency, compoundingFrequency * timeInYears);
  return principal * factor - principal;
};

// Late fee calculations
export const calculateLateFee = (
  amount: number,
  feeType: 'percentage' | 'fixed',
  feeValue: number,
  daysLate: number,
  gracePeriod: number = 0
): number => {
  if (daysLate <= gracePeriod) return 0;

  if (feeType === 'percentage') {
    return amount * (feeValue / 100);
  } else {
    return feeValue;
  }
};

// Credit score impact calculations
export const calculateCreditScoreImpact = (
  daysOverdue: number,
  amount: number
): { impact: number; severity: 'low' | 'medium' | 'high' | 'severe' } => {
  let impact = 0;
  let severity: 'low' | 'medium' | 'high' | 'severe' = 'low';

  if (daysOverdue <= 30) {
    impact = Math.min(amount * 0.01, 10);
    severity = 'low';
  } else if (daysOverdue <= 60) {
    impact = Math.min(amount * 0.03, 30);
    severity = 'medium';
  } else if (daysOverdue <= 90) {
    impact = Math.min(amount * 0.05, 50);
    severity = 'high';
  } else {
    impact = Math.min(amount * 0.1, 100);
    severity = 'severe';
  }

  return { impact, severity };
};

// Financial ratios
export const calculateCollectionRate = (collected: number, total: number): number => {
  if (total === 0) return 0;
  return (collected / total) * 100;
};

export const calculateDaysInAR = (
  averageAccountsReceivable: number,
  netCreditSales: number,
  days: number = 365
): number => {
  if (netCreditSales === 0) return 0;
  return (averageAccountsReceivable / netCreditSales) * days;
};

// Fraud detection utilities
export const calculateFraudRiskScore = (factors: {
  amount: number;
  timeOfDay: number;
  dayOfWeek: number;
  paymentMethod: PaymentMethod;
  previousFailures: number;
  unusualPattern: boolean;
}): number => {
  let score = 0;

  // Amount-based risk
  if (factors.amount > 10000) score += 40;
  else if (factors.amount > 5000) score += 25;
  else if (factors.amount > 2000) score += 15;
  else if (factors.amount > 1000) score += 10;

  // Time-based risk
  if (factors.timeOfDay < 6 || factors.timeOfDay > 22) score += 15;
  if ([0, 6].includes(factors.dayOfWeek)) score += 10; // Weekend

  // Payment method risk
  const methodRisk = {
    [PaymentMethod.CRYPTOCURRENCY]: 30,
    [PaymentMethod.DIGITAL_WALLET]: 15,
    [PaymentMethod.MOBILE_PAYMENT]: 10,
    [PaymentMethod.CREDIT_CARD]: 5,
    [PaymentMethod.DEBIT_CARD]: 5,
    [PaymentMethod.BANK_TRANSFER]: 3,
    [PaymentMethod.CHECK]: 8,
    [PaymentMethod.CASH]: 0
  };
  score += methodRisk[factors.paymentMethod] || 0;

  // Previous failures
  score += Math.min(factors.previousFailures * 5, 20);

  // Unusual pattern
  if (factors.unusualPattern) score += 20;

  return Math.min(score, 100);
};

// Payment validation
export const validateCreditCard = (cardNumber: string): {
  isValid: boolean;
  cardType: string;
  errors: string[];
} => {
  const errors: string[] = [];
  const cleanNumber = cardNumber.replace(/\D/g, '');

  // Length validation
  if (cleanNumber.length < 13 || cleanNumber.length > 19) {
    errors.push('Card number must be between 13 and 19 digits');
  }

  // Luhn algorithm validation
  let sum = 0;
  let alternate = false;

  for (let i = cleanNumber.length - 1; i >= 0; i--) {
    let n = parseInt(cleanNumber.charAt(i), 10);

    if (alternate) {
      n *= 2;
      if (n > 9) n = (n % 10) + 1;
    }

    sum += n;
    alternate = !alternate;
  }

  const isValidLuhn = sum % 10 === 0;
  if (!isValidLuhn) {
    errors.push('Invalid card number');
  }

  // Card type detection
  let cardType = 'Unknown';
  if (/^4/.test(cleanNumber)) cardType = 'Visa';
  else if (/^5[1-5]/.test(cleanNumber)) cardType = 'MasterCard';
  else if (/^3[47]/.test(cleanNumber)) cardType = 'American Express';
  else if (/^6011/.test(cleanNumber)) cardType = 'Discover';

  return {
    isValid: errors.length === 0,
    cardType,
    errors
  };
};

export const validateBankAccount = (accountNumber: string, routingNumber: string): {
  isValid: boolean;
  errors: string[];
} => {
  const errors: string[] = [];

  // Account number validation
  if (!/^\d{8,17}$/.test(accountNumber)) {
    errors.push('Account number must be 8-17 digits');
  }

  // Routing number validation
  if (!/^\d{9}$/.test(routingNumber)) {
    errors.push('Routing number must be exactly 9 digits');
  }

  // ABA routing number checksum validation
  if (routingNumber.length === 9) {
    const weights = [3, 7, 1, 3, 7, 1, 3, 7, 1];
    let sum = 0;

    for (let i = 0; i < 9; i++) {
      sum += parseInt(routingNumber[i]) * weights[i];
    }

    if (sum % 10 !== 0) {
      errors.push('Invalid routing number');
    }
  }

  return {
    isValid: errors.length === 0,
    errors
  };
};

// PCI DSS compliance utilities
export const maskCardNumber = (cardNumber: string): string => {
  const cleaned = cardNumber.replace(/\D/g, '');
  if (cleaned.length < 4) return cardNumber;

  const lastFour = cleaned.slice(-4);
  const masked = '*'.repeat(cleaned.length - 4);
  return masked + lastFour;
};

export const maskBankAccount = (accountNumber: string): string => {
  if (accountNumber.length < 4) return accountNumber;

  const lastFour = accountNumber.slice(-4);
  const masked = '*'.repeat(accountNumber.length - 4);
  return masked + lastFour;
};

// Encryption utilities (placeholders for real encryption)
export const encryptSensitiveData = (data: string): string => {
  // In production, use proper encryption libraries
  return btoa(data); // Base64 encoding as placeholder
};

export const decryptSensitiveData = (encryptedData: string): string => {
  // In production, use proper decryption libraries
  try {
    return atob(encryptedData); // Base64 decoding as placeholder
  } catch {
    return '';
  }
};

// Audit trail utilities
export const generateAuditId = (): string => {
  return `audit_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
};

export const logFinancialAction = (action: string, data: any, userId: string): void => {
  const auditEntry = {
    id: generateAuditId(),
    action,
    data: JSON.stringify(data),
    userId,
    timestamp: new Date().toISOString(),
    ip: 'client-ip', // Would be extracted from request
    userAgent: navigator.userAgent
  };

  // In production, send to audit logging service
  console.log('Audit Log:', auditEntry);
};

// Exchange rate utilities
export const convertCurrency = (
  amount: number,
  fromCurrency: string,
  toCurrency: string,
  exchangeRate: number
): number => {
  if (fromCurrency === toCurrency) return amount;
  return amount * exchangeRate;
};

// Reporting utilities
export const generateReportId = (): string => {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  return `report_${timestamp}_${Math.random().toString(36).substr(2, 6)}`;
};

export const formatForExport = (data: any[], format: 'csv' | 'excel' | 'pdf'): string => {
  switch (format) {
    case 'csv':
      return convertToCSV(data);
    case 'excel':
      return convertToExcel(data);
    case 'pdf':
      return convertToPDF(data);
    default:
      return JSON.stringify(data, null, 2);
  }
};

const convertToCSV = (data: any[]): string => {
  if (data.length === 0) return '';

  const headers = Object.keys(data[0]);
  const csvHeaders = headers.join(',');

  const csvRows = data.map(row =>
    headers.map(header => {
      const value = row[header];
      return typeof value === 'string' && value.includes(',') ? `"${value}"` : value;
    }).join(',')
  );

  return [csvHeaders, ...csvRows].join('\n');
};

const convertToExcel = (data: any[]): string => {
  // Placeholder for Excel conversion
  return convertToCSV(data);
};

const convertToPDF = (data: any[]): string => {
  // Placeholder for PDF conversion
  return JSON.stringify(data, null, 2);
};

// Business logic utilities
export const calculateNetAmount = (grossAmount: number, discounts: number[], taxes: number[]): number => {
  const totalDiscounts = discounts.reduce((sum, discount) => sum + discount, 0);
  const totalTaxes = taxes.reduce((sum, tax) => sum + tax, 0);
  return grossAmount - totalDiscounts + totalTaxes;
};

export const applyDiscount = (amount: number, discountType: 'percentage' | 'fixed', discountValue: number): number => {
  if (discountType === 'percentage') {
    return amount * (1 - discountValue / 100);
  } else {
    return Math.max(0, amount - discountValue);
  }
};

// Rounding utilities for financial calculations
export const roundToNearestCent = (amount: number): number => {
  return Math.round(amount * 100) / 100;
};

export const roundToNearestDollar = (amount: number): number => {
  return Math.round(amount);
};

// Budget and forecasting utilities
export const calculateBudgetVariance = (actual: number, budgeted: number): {
  variance: number;
  percentageVariance: number;
  status: 'over' | 'under' | 'on-track';
} => {
  const variance = actual - budgeted;
  const percentageVariance = budgeted !== 0 ? (variance / budgeted) * 100 : 0;

  let status: 'over' | 'under' | 'on-track' = 'on-track';
  if (Math.abs(percentageVariance) > 5) {
    status = variance > 0 ? 'over' : 'under';
  }

  return { variance, percentageVariance, status };
};

export const forecastRevenue = (
  historicalData: Array<{ month: string; revenue: number }>,
  periods: number
): Array<{ month: string; forecast: number; confidence: number }> => {
  // Simple linear regression forecast
  const n = historicalData.length;
  const sumX = historicalData.reduce((sum, _, index) => sum + index, 0);
  const sumY = historicalData.reduce((sum, data) => sum + data.revenue, 0);
  const sumXY = historicalData.reduce((sum, data, index) => sum + index * data.revenue, 0);
  const sumXX = historicalData.reduce((sum, _, index) => sum + index * index, 0);

  const slope = (n * sumXY - sumX * sumY) / (n * sumXX - sumX * sumX);
  const intercept = (sumY - slope * sumX) / n;

  const forecasts = [];
  for (let i = 0; i < periods; i++) {
    const nextIndex = n + i;
    const forecast = slope * nextIndex + intercept;
    const confidence = Math.max(0, 100 - (i * 10)); // Decreasing confidence over time

    const futureDate = new Date();
    futureDate.setMonth(futureDate.getMonth() + i + 1);
    const month = futureDate.toLocaleDateString('en-US', { year: 'numeric', month: 'short' });

    forecasts.push({ month, forecast: roundToNearestCent(forecast), confidence });
  }

  return forecasts;
};

export default {
  formatCurrency,
  formatPercentage,
  formatDate,
  getDaysUntilDue,
  getStatusColor,
  getPaymentMethodIcon,
  getPaymentMethodName,
  calculateTax,
  calculateAmountWithTax,
  calculateInstallmentAmount,
  calculateLateFee,
  calculateCollectionRate,
  calculateFraudRiskScore,
  validateCreditCard,
  validateBankAccount,
  maskCardNumber,
  maskBankAccount,
  encryptSensitiveData,
  logFinancialAction,
  convertCurrency,
  generateReportId,
  formatForExport,
  calculateNetAmount,
  applyDiscount,
  roundToNearestCent,
  calculateBudgetVariance,
  forecastRevenue
};