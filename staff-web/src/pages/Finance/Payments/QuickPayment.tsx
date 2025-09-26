/**
 * Quick Payment Modal Component
 * Fast payment entry for common scenarios with immediate processing
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../../../components/ui/dialog';
import { Button } from '../../../components/ui/button';
import { Input } from '../../../components/ui/input';
import { Label } from '../../../components/ui/label';
import { Badge } from '../../../components/ui/badge';
import { Alert, AlertDescription } from '../../../components/ui/alert';
import { Separator } from '../../../components/ui/separator';
import { Loader2, Search, CreditCard, Banknote, Smartphone, CheckCircle, AlertCircle, Receipt } from 'lucide-react';
import { useToast } from '../../../hooks/use-toast';
import { financeService } from '../../../services/financeService';
import { Student, Payment, PaymentMethod } from '../../../types/finance.types';

interface QuickPaymentProps {
  isOpen: boolean;
  onClose: () => void;
  onPaymentComplete?: (payment: Payment) => void;
  preselectedStudent?: Student;
  preselectedAmount?: number;
  preselectedInvoiceId?: string;
}

const PAYMENT_METHODS = [
  { method: PaymentMethod.CASH, label: 'Cash', icon: Banknote },
  { method: PaymentMethod.CREDIT_CARD, label: 'Credit Card', icon: CreditCard },
  { method: PaymentMethod.DEBIT_CARD, label: 'Debit Card', icon: CreditCard },
  { method: PaymentMethod.MOBILE_PAYMENT, label: 'Mobile Pay', icon: Smartphone },
];

const QUICK_AMOUNTS = [50, 100, 200, 500, 1000, 2000];

export const QuickPayment: React.FC<QuickPaymentProps> = ({
  isOpen,
  onClose,
  onPaymentComplete,
  preselectedStudent,
  preselectedAmount,
  preselectedInvoiceId
}) => {
  const [step, setStep] = useState<'search' | 'payment' | 'processing' | 'complete'>('search');
  const [selectedStudent, setSelectedStudent] = useState<Student | null>(preselectedStudent || null);
  const [studentSearch, setStudentSearch] = useState('');
  const [searchResults, setSearchResults] = useState<Student[]>([]);
  const [amount, setAmount] = useState(preselectedAmount?.toString() || '');
  const [selectedPaymentMethod, setSelectedPaymentMethod] = useState<PaymentMethod>(PaymentMethod.CASH);
  const [notes, setNotes] = useState('');
  const [processing, setProcessing] = useState(false);
  const [completedPayment, setCompletedPayment] = useState<Payment | null>(null);
  const [searchLoading, setSearchLoading] = useState(false);

  const { toast } = useToast();

  // Mock students for demo - replace with actual API
  const mockStudents: Student[] = [
    {
      id: '1',
      student_id: 'STU001',
      first_name: 'John',
      last_name: 'Doe',
      email: 'john.doe@email.com',
      phone: '(555) 123-4567',
      account_balance: -150.00
    },
    {
      id: '2',
      student_id: 'STU002',
      first_name: 'Jane',
      last_name: 'Smith',
      email: 'jane.smith@email.com',
      phone: '(555) 987-6543',
      account_balance: 0.00
    },
    {
      id: '3',
      student_id: 'STU003',
      first_name: 'Michael',
      last_name: 'Johnson',
      email: 'michael.johnson@email.com',
      phone: '(555) 456-7890',
      account_balance: -75.50
    }
  ];

  // Reset form when dialog opens/closes
  useEffect(() => {
    if (isOpen) {
      if (preselectedStudent) {
        setSelectedStudent(preselectedStudent);
        setStep('payment');
      } else {
        setStep('search');
      }
      setAmount(preselectedAmount?.toString() || '');
      setNotes('');
      setCompletedPayment(null);
    } else {
      setSelectedStudent(null);
      setStudentSearch('');
      setSearchResults([]);
      setAmount('');
      setNotes('');
      setStep('search');
      setProcessing(false);
      setCompletedPayment(null);
    }
  }, [isOpen, preselectedStudent, preselectedAmount]);

  // Search students
  useEffect(() => {
    if (studentSearch.length >= 2) {
      setSearchLoading(true);
      // Simulate API delay
      const timer = setTimeout(() => {
        const filtered = mockStudents.filter(student =>
          student.first_name.toLowerCase().includes(studentSearch.toLowerCase()) ||
          student.last_name.toLowerCase().includes(studentSearch.toLowerCase()) ||
          student.student_id.toLowerCase().includes(studentSearch.toLowerCase()) ||
          student.email.toLowerCase().includes(studentSearch.toLowerCase())
        );
        setSearchResults(filtered);
        setSearchLoading(false);
      }, 300);

      return () => clearTimeout(timer);
    } else {
      setSearchResults([]);
      setSearchLoading(false);
    }
  }, [studentSearch]);

  // Select student and proceed to payment
  const selectStudent = useCallback((student: Student) => {
    setSelectedStudent(student);
    setStep('payment');
  }, []);

  // Set quick amount
  const setQuickAmount = useCallback((quickAmount: number) => {
    setAmount(quickAmount.toString());
  }, []);

  // Process payment
  const processPayment = useCallback(async () => {
    if (!selectedStudent) {
      toast({
        title: "No Student Selected",
        description: "Please select a student",
        variant: "destructive"
      });
      return;
    }

    const paymentAmount = parseFloat(amount);
    if (isNaN(paymentAmount) || paymentAmount <= 0) {
      toast({
        title: "Invalid Amount",
        description: "Please enter a valid payment amount",
        variant: "destructive"
      });
      return;
    }

    setProcessing(true);
    setStep('processing');

    try {
      const paymentData = {
        student_id: selectedStudent.id,
        amount: paymentAmount,
        payment_method: selectedPaymentMethod,
        invoice_id: preselectedInvoiceId,
        notes: notes || undefined
      };

      const response = await financeService.processPayment(paymentData);

      if (response.success) {
        setCompletedPayment(response.data);
        setStep('complete');

        toast({
          title: "Payment Processed Successfully",
          description: `$${paymentAmount.toFixed(2)} payment from ${selectedStudent.first_name} ${selectedStudent.last_name}`,
        });

        onPaymentComplete?.(response.data);

        // Auto-send receipt
        await financeService.sendPaymentConfirmation(response.data.id, 'email');
      }
    } catch (error) {
      toast({
        title: "Payment Failed",
        description: "There was an error processing the payment. Please try again.",
        variant: "destructive"
      });
      setStep('payment');
    } finally {
      setProcessing(false);
    }
  }, [selectedStudent, amount, selectedPaymentMethod, notes, preselectedInvoiceId, onPaymentComplete, toast]);

  // Print receipt
  const printReceipt = useCallback(async () => {
    if (completedPayment) {
      try {
        // Mock print functionality
        toast({
          title: "Receipt Printing",
          description: "Receipt sent to printer",
        });
      } catch (error) {
        toast({
          title: "Print Error",
          description: "Failed to print receipt",
          variant: "destructive"
        });
      }
    }
  }, [completedPayment, toast]);

  // Close and reset
  const handleClose = useCallback(() => {
    onClose();
  }, [onClose]);

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Quick Payment</DialogTitle>
        </DialogHeader>

        {/* Student Search Step */}
        {step === 'search' && (
          <div className="space-y-4">
            <div>
              <Label htmlFor="student-search">Search Student</Label>
              <div className="relative">
                <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                <Input
                  id="student-search"
                  placeholder="Name, Student ID, or Email..."
                  value={studentSearch}
                  onChange={(e) => setStudentSearch(e.target.value)}
                  className="pl-10"
                  autoFocus
                />
                {searchLoading && (
                  <Loader2 className="absolute right-3 top-3 h-4 w-4 animate-spin text-gray-400" />
                )}
              </div>
            </div>

            {searchResults.length > 0 && (
              <div className="max-h-60 overflow-y-auto space-y-2">
                {searchResults.map(student => (
                  <div
                    key={student.id}
                    className="p-3 border rounded-lg cursor-pointer hover:bg-gray-50 transition-colors"
                    onClick={() => selectStudent(student)}
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <p className="font-medium">{student.first_name} {student.last_name}</p>
                        <p className="text-sm text-gray-600">{student.student_id}</p>
                        <p className="text-sm text-gray-600">{student.email}</p>
                      </div>
                      <Badge variant={student.account_balance < 0 ? "destructive" : "default"}>
                        ${student.account_balance.toFixed(2)}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {studentSearch.length >= 2 && searchResults.length === 0 && !searchLoading && (
              <div className="text-center py-4 text-gray-500">
                No students found matching "{studentSearch}"
              </div>
            )}
          </div>
        )}

        {/* Payment Entry Step */}
        {step === 'payment' && selectedStudent && (
          <div className="space-y-4">
            {/* Selected Student */}
            <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="flex justify-between items-start">
                <div>
                  <p className="font-medium text-blue-900">
                    {selectedStudent.first_name} {selectedStudent.last_name}
                  </p>
                  <p className="text-sm text-blue-700">{selectedStudent.student_id}</p>
                </div>
                <Badge variant={selectedStudent.account_balance < 0 ? "destructive" : "default"}>
                  Balance: ${selectedStudent.account_balance.toFixed(2)}
                </Badge>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setStep('search')}
                className="mt-2 text-blue-700 hover:text-blue-900"
              >
                Change Student
              </Button>
            </div>

            {/* Payment Amount */}
            <div>
              <Label htmlFor="amount">Payment Amount</Label>
              <Input
                id="amount"
                type="number"
                step="0.01"
                placeholder="0.00"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                className="text-lg font-medium"
              />
            </div>

            {/* Quick Amounts */}
            <div>
              <Label>Quick Amounts</Label>
              <div className="grid grid-cols-3 gap-2 mt-2">
                {QUICK_AMOUNTS.map(quickAmount => (
                  <Button
                    key={quickAmount}
                    variant="outline"
                    size="sm"
                    onClick={() => setQuickAmount(quickAmount)}
                    className="text-sm"
                  >
                    ${quickAmount}
                  </Button>
                ))}
              </div>
            </div>

            {/* Payment Method */}
            <div>
              <Label>Payment Method</Label>
              <div className="grid grid-cols-2 gap-2 mt-2">
                {PAYMENT_METHODS.map(({ method, label, icon: Icon }) => (
                  <Button
                    key={method}
                    variant={selectedPaymentMethod === method ? "default" : "outline"}
                    onClick={() => setSelectedPaymentMethod(method)}
                    className="flex items-center gap-2 justify-start"
                  >
                    <Icon className="h-4 w-4" />
                    {label}
                  </Button>
                ))}
              </div>
            </div>

            {/* Notes */}
            <div>
              <Label htmlFor="notes">Notes (Optional)</Label>
              <Input
                id="notes"
                placeholder="Payment notes..."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />
            </div>

            {/* Outstanding Balance Alert */}
            {selectedStudent.account_balance < 0 && (
              <Alert className="border-orange-300 bg-orange-50">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  Student has outstanding balance of ${Math.abs(selectedStudent.account_balance).toFixed(2)}
                </AlertDescription>
              </Alert>
            )}
          </div>
        )}

        {/* Processing Step */}
        {step === 'processing' && (
          <div className="text-center py-8">
            <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
            <p className="text-lg font-medium">Processing Payment...</p>
            <p className="text-sm text-gray-600">Please wait while we process the payment</p>
          </div>
        )}

        {/* Complete Step */}
        {step === 'complete' && completedPayment && selectedStudent && (
          <div className="text-center space-y-4">
            <div className="flex justify-center">
              <CheckCircle className="h-12 w-12 text-green-500" />
            </div>

            <div>
              <h3 className="text-lg font-medium text-green-900">Payment Successful!</h3>
              <p className="text-sm text-gray-600">
                ${completedPayment.amount.toFixed(2)} payment processed
              </p>
            </div>

            <div className="p-4 bg-gray-50 rounded-lg text-left">
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span>Student:</span>
                  <span className="font-medium">{selectedStudent.first_name} {selectedStudent.last_name}</span>
                </div>
                <div className="flex justify-between">
                  <span>Amount:</span>
                  <span className="font-medium">${completedPayment.amount.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Method:</span>
                  <span className="font-medium">{completedPayment.payment_method}</span>
                </div>
                <div className="flex justify-between">
                  <span>Receipt #:</span>
                  <span className="font-medium">{completedPayment.receipt_number}</span>
                </div>
                <div className="flex justify-between">
                  <span>Date:</span>
                  <span className="font-medium">
                    {new Date(completedPayment.processed_date).toLocaleString()}
                  </span>
                </div>
              </div>
            </div>

            <Button
              variant="outline"
              onClick={printReceipt}
              className="w-full"
            >
              <Receipt className="h-4 w-4 mr-2" />
              Print Receipt
            </Button>
          </div>
        )}

        <DialogFooter>
          {step === 'search' && (
            <Button variant="outline" onClick={handleClose}>
              Cancel
            </Button>
          )}

          {step === 'payment' && (
            <>
              <Button variant="outline" onClick={() => setStep('search')}>
                Back
              </Button>
              <Button
                onClick={processPayment}
                disabled={!amount || parseFloat(amount) <= 0}
              >
                Process Payment
              </Button>
            </>
          )}

          {step === 'complete' && (
            <>
              <Button variant="outline" onClick={() => setStep('search')}>
                New Payment
              </Button>
              <Button onClick={handleClose}>
                Close
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default QuickPayment;