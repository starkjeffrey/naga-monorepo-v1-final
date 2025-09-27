/**
 * usePaymentProcessing Hook
 * Advanced payment processing hook with fraud detection, PCI compliance, and real-time monitoring
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import { useToast } from '../../../hooks/use-toast';
import { financeService } from '../../../services/financeService';
import {
  Payment,
  PaymentMethod,
  PaymentStatus,
  FraudAlert,
  PaymentPrediction
} from '../../../types/finance.types';
import { calculateFraudRiskScore, logFinancialAction } from '../../../utils/financeUtils';

interface PaymentProcessingOptions {
  enableFraudDetection?: boolean;
  requireIdVerification?: boolean;
  autoConfirmation?: boolean;
  maxRetries?: number;
  timeoutMs?: number;
}

interface PaymentData {
  studentId: string;
  amount: number;
  paymentMethod: PaymentMethod;
  invoiceId?: string;
  notes?: string;
  paymentDetails?: any;
}

interface PaymentProcessingState {
  isProcessing: boolean;
  currentPayment: Payment | null;
  fraudAlerts: FraudAlert[];
  fraudRiskScore: number;
  processingStep: 'validation' | 'fraud_check' | 'processing' | 'confirmation' | 'complete';
  error: string | null;
  retryCount: number;
  processingTime: number;
}

export const usePaymentProcessing = (options: PaymentProcessingOptions = {}) => {
  const {
    enableFraudDetection = true,
    requireIdVerification = false,
    autoConfirmation = true,
    maxRetries = 3,
    timeoutMs = 30000
  } = options;

  const { toast } = useToast();
  const startTimeRef = useRef<number>(0);
  const timeoutRef = useRef<NodeJS.Timeout>();

  const [state, setState] = useState<PaymentProcessingState>({
    isProcessing: false,
    currentPayment: null,
    fraudAlerts: [],
    fraudRiskScore: 0,
    processingStep: 'validation',
    error: null,
    retryCount: 0,
    processingTime: 0
  });

  // WebSocket connection for real-time updates
  useEffect(() => {
    const handlePaymentUpdate = (payment: Payment) => {
      if (state.currentPayment?.id === payment.id) {
        setState(prev => ({ ...prev, currentPayment: payment }));
      }
    };

    const handleFraudAlert = (alert: FraudAlert) => {
      setState(prev => ({
        ...prev,
        fraudAlerts: [...prev.fraudAlerts, alert]
      }));
    };

    financeService.initializeWebSocket({
      onPaymentUpdate: handlePaymentUpdate,
      onFraudAlert: handleFraudAlert
    });

    return () => {
      financeService.disconnectWebSocket();
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [state.currentPayment?.id]);

  // Calculate fraud risk score
  const calculateFraudRisk = useCallback(async (paymentData: PaymentData): Promise<number> => {
    const now = new Date();
    const factors = {
      amount: paymentData.amount,
      timeOfDay: now.getHours(),
      dayOfWeek: now.getDay(),
      paymentMethod: paymentData.paymentMethod,
      previousFailures: state.retryCount,
      unusualPattern: false // Would be determined by ML model in production
    };

    return calculateFraudRiskScore(factors);
  }, [state.retryCount]);

  // Validate payment data
  const validatePayment = useCallback((paymentData: PaymentData): string[] => {
    const errors: string[] = [];

    if (!paymentData.studentId) {
      errors.push('Student ID is required');
    }

    if (!paymentData.amount || paymentData.amount <= 0) {
      errors.push('Valid payment amount is required');
    }

    if (paymentData.amount > 50000) {
      errors.push('Payment amount exceeds maximum limit');
    }

    if (!paymentData.paymentMethod) {
      errors.push('Payment method is required');
    }

    // Payment method specific validations
    if (paymentData.paymentMethod === PaymentMethod.CREDIT_CARD ||
        paymentData.paymentMethod === PaymentMethod.DEBIT_CARD) {
      if (!paymentData.paymentDetails?.card_token) {
        errors.push('Valid card information is required');
      }
    }

    if (paymentData.paymentMethod === PaymentMethod.BANK_TRANSFER) {
      if (!paymentData.paymentDetails?.account_token) {
        errors.push('Valid bank account information is required');
      }
    }

    return errors;
  }, []);

  // Check fraud detection
  const performFraudCheck = useCallback(async (paymentData: PaymentData): Promise<boolean> => {
    if (!enableFraudDetection) return true;

    setState(prev => ({ ...prev, processingStep: 'fraud_check' }));

    const riskScore = await calculateFraudRisk(paymentData);
    setState(prev => ({ ...prev, fraudRiskScore: riskScore }));

    // High-risk transaction handling
    if (riskScore > 85) {
      const alert: FraudAlert = {
        id: `fraud_${Date.now()}`,
        transaction_id: '',
        risk_score: riskScore,
        alert_type: 'high_risk_transaction',
        description: 'High-risk transaction detected. Manual review required.',
        timestamp: new Date().toISOString(),
        status: 'pending'
      };

      setState(prev => ({
        ...prev,
        fraudAlerts: [...prev.fraudAlerts, alert],
        error: 'Transaction blocked due to high fraud risk. Please contact support.'
      }));

      return false;
    }

    // Medium-risk transaction handling
    if (riskScore > 50) {
      toast({
        title: "Security Notice",
        description: "Additional verification may be required for this transaction.",
        variant: "default"
      });
    }

    return true;
  }, [enableFraudDetection, calculateFraudRisk, toast]);

  // Process payment with comprehensive error handling
  const processPayment = useCallback(async (paymentData: PaymentData): Promise<Payment | null> => {
    // Reset state
    setState(prev => ({
      ...prev,
      isProcessing: true,
      currentPayment: null,
      error: null,
      processingStep: 'validation',
      fraudAlerts: [],
      retryCount: 0
    }));

    startTimeRef.current = Date.now();

    // Set timeout
    timeoutRef.current = setTimeout(() => {
      setState(prev => ({
        ...prev,
        isProcessing: false,
        error: 'Payment processing timeout. Please try again.',
        processingTime: Date.now() - startTimeRef.current
      }));
    }, timeoutMs);

    try {
      // Step 1: Validation
      const validationErrors = validatePayment(paymentData);
      if (validationErrors.length > 0) {
        throw new Error(validationErrors[0]);
      }

      // Step 2: Fraud Detection
      const fraudCheckPassed = await performFraudCheck(paymentData);
      if (!fraudCheckPassed) {
        return null;
      }

      // Step 3: Payment Processing
      setState(prev => ({ ...prev, processingStep: 'processing' }));

      const response = await financeService.processPayment({
        student_id: paymentData.studentId,
        amount: paymentData.amount,
        payment_method: paymentData.paymentMethod,
        invoice_id: paymentData.invoiceId,
        notes: paymentData.notes,
        payment_details: paymentData.paymentDetails
      });

      if (!response.success) {
        throw new Error(response.message || 'Payment processing failed');
      }

      const payment = response.data;

      // Step 4: Confirmation
      setState(prev => ({
        ...prev,
        processingStep: 'confirmation',
        currentPayment: payment
      }));

      // Auto-confirmation for low-risk transactions
      if (autoConfirmation && state.fraudRiskScore < 30) {
        await financeService.sendPaymentConfirmation(payment.id, 'email');
      }

      // Step 5: Complete
      setState(prev => ({
        ...prev,
        processingStep: 'complete',
        isProcessing: false,
        processingTime: Date.now() - startTimeRef.current
      }));

      // Log successful transaction
      logFinancialAction('payment_processed', {
        paymentId: payment.id,
        amount: paymentData.amount,
        method: paymentData.paymentMethod,
        fraudScore: state.fraudRiskScore
      }, 'current_user_id');

      toast({
        title: "Payment Processed Successfully",
        description: `Payment of $${paymentData.amount.toFixed(2)} has been processed.`,
      });

      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }

      return payment;

    } catch (error: any) {
      const errorMessage = error.message || 'Payment processing failed';

      setState(prev => ({
        ...prev,
        isProcessing: false,
        error: errorMessage,
        retryCount: prev.retryCount + 1,
        processingTime: Date.now() - startTimeRef.current
      }));

      // Log failed transaction
      logFinancialAction('payment_failed', {
        error: errorMessage,
        amount: paymentData.amount,
        method: paymentData.paymentMethod,
        retryCount: state.retryCount + 1
      }, 'current_user_id');

      toast({
        title: "Payment Failed",
        description: errorMessage,
        variant: "destructive"
      });

      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }

      return null;
    }
  }, [validatePayment, performFraudCheck, autoConfirmation, state.fraudRiskScore, state.retryCount, timeoutMs, toast]);

  // Retry payment processing
  const retryPayment = useCallback(async (paymentData: PaymentData): Promise<Payment | null> => {
    if (state.retryCount >= maxRetries) {
      toast({
        title: "Maximum Retries Exceeded",
        description: "Please contact support for assistance.",
        variant: "destructive"
      });
      return null;
    }

    return processPayment(paymentData);
  }, [state.retryCount, maxRetries, processPayment, toast]);

  // Cancel payment processing
  const cancelPayment = useCallback(() => {
    setState(prev => ({
      ...prev,
      isProcessing: false,
      error: 'Payment cancelled by user',
      processingTime: Date.now() - startTimeRef.current
    }));

    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    if (state.currentPayment) {
      financeService.voidPayment(state.currentPayment.id, 'Cancelled by user');
    }
  }, [state.currentPayment]);

  // Get payment predictions for student
  const getPaymentPredictions = useCallback(async (studentId: string): Promise<PaymentPrediction[]> => {
    try {
      const response = await financeService.getPaymentPredictions(studentId);
      return response.success ? response.data : [];
    } catch (error) {
      console.error('Failed to get payment predictions:', error);
      return [];
    }
  }, []);

  // Refund payment
  const refundPayment = useCallback(async (paymentId: string, amount?: number, reason?: string): Promise<boolean> => {
    try {
      setState(prev => ({ ...prev, isProcessing: true }));

      const response = await financeService.refundPayment(paymentId, amount, reason);

      if (response.success) {
        toast({
          title: "Refund Processed",
          description: `Refund of $${amount?.toFixed(2) || 'full amount'} has been processed.`,
        });

        logFinancialAction('payment_refunded', {
          paymentId,
          refundAmount: amount,
          reason
        }, 'current_user_id');

        return true;
      }

      return false;
    } catch (error: any) {
      toast({
        title: "Refund Failed",
        description: error.message || 'Failed to process refund',
        variant: "destructive"
      });
      return false;
    } finally {
      setState(prev => ({ ...prev, isProcessing: false }));
    }
  }, [toast]);

  // Clear errors
  const clearError = useCallback(() => {
    setState(prev => ({ ...prev, error: null }));
  }, []);

  // Clear fraud alerts
  const clearFraudAlerts = useCallback(() => {
    setState(prev => ({ ...prev, fraudAlerts: [] }));
  }, []);

  return {
    // State
    isProcessing: state.isProcessing,
    currentPayment: state.currentPayment,
    fraudAlerts: state.fraudAlerts,
    fraudRiskScore: state.fraudRiskScore,
    processingStep: state.processingStep,
    error: state.error,
    retryCount: state.retryCount,
    processingTime: state.processingTime,
    canRetry: state.retryCount < maxRetries,

    // Actions
    processPayment,
    retryPayment,
    cancelPayment,
    refundPayment,
    getPaymentPredictions,
    clearError,
    clearFraudAlerts,

    // Utilities
    calculateFraudRisk,
    validatePayment
  };
};

export default usePaymentProcessing;