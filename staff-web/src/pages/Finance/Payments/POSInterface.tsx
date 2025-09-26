/**
 * POS Interface Component
 * Modern point-of-sale interface optimized for cashier operations
 * Features touch-friendly design, real-time payment processing, and fraud detection
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/card';
import { Button } from '../../../components/ui/button';
import { Input } from '../../../components/ui/input';
import { Badge } from '../../../components/ui/badge';
import { Alert, AlertDescription } from '../../../components/ui/alert';
import { Separator } from '../../../components/ui/separator';
import { Progress } from '../../../components/ui/progress';
import { Loader2, CreditCard, Banknote, Smartphone, AlertTriangle, CheckCircle, XCircle, Scanner, Printer, Users, DollarSign } from 'lucide-react';
import { useToast } from '../../../hooks/use-toast';
import { financeService } from '../../../services/financeService';
import { POSTransaction, POSItem, PaymentMethod, Student, CashierSession } from '../../../types/finance.types';

interface POSInterfaceProps {
  cashierSession?: CashierSession;
  onTransactionComplete?: (transaction: POSTransaction) => void;
}

interface CartItem extends POSItem {
  tempId: string;
  quantity: number;
}

const QUICK_AMOUNTS = [10, 20, 50, 100, 200, 500];
const COMMON_SERVICES = [
  { id: 'tuition', description: 'Tuition Payment', amount: 0, category: 'academic' },
  { id: 'books', description: 'Books & Materials', amount: 0, category: 'supplies' },
  { id: 'registration', description: 'Registration Fee', amount: 50, category: 'fees' },
  { id: 'transcript', description: 'Official Transcript', amount: 15, category: 'services' },
  { id: 'parking', description: 'Parking Pass', amount: 75, category: 'services' },
  { id: 'lab_fee', description: 'Lab Fee', amount: 30, category: 'fees' }
];

export const POSInterface: React.FC<POSInterfaceProps> = ({
  cashierSession,
  onTransactionComplete
}) => {
  const [selectedStudent, setSelectedStudent] = useState<Student | null>(null);
  const [studentSearch, setStudentSearch] = useState('');
  const [searchResults, setSearchResults] = useState<Student[]>([]);
  const [cart, setCart] = useState<CartItem[]>([]);
  const [customAmount, setCustomAmount] = useState('');
  const [customDescription, setCustomDescription] = useState('');
  const [selectedPaymentMethod, setSelectedPaymentMethod] = useState<PaymentMethod>(PaymentMethod.CASH);
  const [paymentAmount, setPaymentAmount] = useState('');
  const [processing, setProcessing] = useState(false);
  const [fraudAlert, setFraudAlert] = useState<string | null>(null);
  const [cardReaderConnected, setCardReaderConnected] = useState(true);
  const [barcodeScanning, setBarcodeScanning] = useState(false);

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
    }
  ];

  // Search students
  useEffect(() => {
    if (studentSearch.length >= 2) {
      const filtered = mockStudents.filter(student =>
        student.first_name.toLowerCase().includes(studentSearch.toLowerCase()) ||
        student.last_name.toLowerCase().includes(studentSearch.toLowerCase()) ||
        student.student_id.toLowerCase().includes(studentSearch.toLowerCase()) ||
        student.email.toLowerCase().includes(studentSearch.toLowerCase())
      );
      setSearchResults(filtered);
    } else {
      setSearchResults([]);
    }
  }, [studentSearch]);

  // Calculate totals
  const subtotal = cart.reduce((sum, item) => sum + (item.amount * item.quantity), 0);
  const taxRate = 0.08; // 8% tax rate
  const taxAmount = subtotal * taxRate;
  const total = subtotal + taxAmount;

  // Add item to cart
  const addToCart = useCallback((item: Omit<CartItem, 'tempId'>) => {
    const tempId = Date.now().toString();
    setCart(prev => [...prev, { ...item, tempId, quantity: 1 }]);
  }, []);

  // Remove item from cart
  const removeFromCart = useCallback((tempId: string) => {
    setCart(prev => prev.filter(item => item.tempId !== tempId));
  }, []);

  // Update item quantity
  const updateQuantity = useCallback((tempId: string, quantity: number) => {
    if (quantity <= 0) {
      removeFromCart(tempId);
      return;
    }
    setCart(prev => prev.map(item =>
      item.tempId === tempId ? { ...item, quantity } : item
    ));
  }, [removeFromCart]);

  // Add custom item
  const addCustomItem = useCallback(() => {
    if (!customDescription || !customAmount) {
      toast({
        title: "Missing Information",
        description: "Please enter both description and amount",
        variant: "destructive"
      });
      return;
    }

    const amount = parseFloat(customAmount);
    if (isNaN(amount) || amount <= 0) {
      toast({
        title: "Invalid Amount",
        description: "Please enter a valid amount",
        variant: "destructive"
      });
      return;
    }

    addToCart({
      id: `custom_${Date.now()}`,
      description: customDescription,
      amount,
      tax_rate: taxRate,
      category: 'custom'
    });

    setCustomDescription('');
    setCustomAmount('');
  }, [customDescription, customAmount, addToCart, toast, taxRate]);

  // Add quick amount
  const addQuickAmount = useCallback((amount: number) => {
    addToCart({
      id: `quick_${Date.now()}`,
      description: `Payment - $${amount}`,
      amount,
      tax_rate: 0, // Quick amounts usually don't include tax
      category: 'payment'
    });
  }, [addToCart]);

  // Barcode scanner simulation
  const handleBarcodeScanner = useCallback(() => {
    setBarcodeScanning(true);
    // Simulate barcode scan
    setTimeout(() => {
      const mockBarcode = 'STU001'; // Simulate student ID scan
      setStudentSearch(mockBarcode);
      setBarcodeScanning(false);
      toast({
        title: "Barcode Scanned",
        description: `Student ID: ${mockBarcode}`,
      });
    }, 2000);
  }, [toast]);

  // Fraud detection simulation
  const checkForFraud = useCallback((amount: number) => {
    // Simple fraud detection rules
    if (amount > 5000) {
      setFraudAlert('High amount transaction - requires supervisor approval');
      return true;
    }
    if (selectedPaymentMethod === PaymentMethod.CREDIT_CARD && amount > 2000) {
      setFraudAlert('Large credit card transaction - verify ID');
      return true;
    }
    setFraudAlert(null);
    return false;
  }, [selectedPaymentMethod]);

  // Process payment
  const processPayment = useCallback(async () => {
    if (!selectedStudent) {
      toast({
        title: "No Student Selected",
        description: "Please select a student before processing payment",
        variant: "destructive"
      });
      return;
    }

    if (cart.length === 0) {
      toast({
        title: "Empty Cart",
        description: "Please add items before processing payment",
        variant: "destructive"
      });
      return;
    }

    const paymentAmountNum = parseFloat(paymentAmount) || total;

    if (paymentAmountNum < total) {
      toast({
        title: "Insufficient Payment",
        description: `Payment amount ($${paymentAmountNum.toFixed(2)}) is less than total ($${total.toFixed(2)})`,
        variant: "destructive"
      });
      return;
    }

    // Check for fraud
    if (checkForFraud(paymentAmountNum)) {
      return;
    }

    setProcessing(true);

    try {
      const transactionData = {
        student_id: selectedStudent.id,
        items: cart.map(item => ({
          description: item.description,
          amount: item.amount * item.quantity,
          tax_rate: item.tax_rate,
          category: item.category
        })),
        payment_method: selectedPaymentMethod
      };

      const response = await financeService.createPOSTransaction(transactionData);

      if (response.success) {
        const change = paymentAmountNum - total;

        toast({
          title: "Payment Processed Successfully",
          description: change > 0 ? `Change due: $${change.toFixed(2)}` : "Payment complete",
        });

        // Reset form
        setCart([]);
        setPaymentAmount('');
        setSelectedStudent(null);
        setStudentSearch('');
        setFraudAlert(null);

        onTransactionComplete?.(response.data);

        // Auto-print receipt
        if (response.data.id) {
          await financeService.printReceipt(response.data.id);
        }
      }
    } catch (error) {
      toast({
        title: "Payment Failed",
        description: "There was an error processing the payment. Please try again.",
        variant: "destructive"
      });
    } finally {
      setProcessing(false);
    }
  }, [selectedStudent, cart, paymentAmount, total, selectedPaymentMethod, checkForFraud, onTransactionComplete, toast]);

  // Clear fraud alert
  const clearFraudAlert = useCallback(() => {
    setFraudAlert(null);
  }, []);

  return (
    <div className="h-screen flex bg-gray-50">
      {/* Left Panel - Student & Cart */}
      <div className="flex-1 p-6 overflow-y-auto">
        {/* Student Selection */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              Student Selection
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex gap-2 mb-4">
              <div className="flex-1">
                <Input
                  placeholder="Search by name, student ID, or email..."
                  value={studentSearch}
                  onChange={(e) => setStudentSearch(e.target.value)}
                  className="text-lg"
                />
              </div>
              <Button
                variant="outline"
                onClick={handleBarcodeScanner}
                disabled={barcodeScanning}
                className="px-6"
              >
                {barcodeScanning ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Scanner className="h-4 w-4" />
                )}
              </Button>
            </div>

            {searchResults.length > 0 && (
              <div className="space-y-2">
                {searchResults.map(student => (
                  <div
                    key={student.id}
                    className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                      selectedStudent?.id === student.id
                        ? 'bg-blue-50 border-blue-300'
                        : 'hover:bg-gray-50'
                    }`}
                    onClick={() => setSelectedStudent(student)}
                  >
                    <div className="flex justify-between items-center">
                      <div>
                        <p className="font-medium">{student.first_name} {student.last_name}</p>
                        <p className="text-sm text-gray-600">{student.student_id} • {student.email}</p>
                      </div>
                      <div className="text-right">
                        <Badge variant={student.account_balance < 0 ? "destructive" : "default"}>
                          Balance: ${student.account_balance.toFixed(2)}
                        </Badge>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {selectedStudent && (
              <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg">
                <p className="font-medium text-green-800">
                  Selected: {selectedStudent.first_name} {selectedStudent.last_name}
                </p>
                <p className="text-sm text-green-600">{selectedStudent.student_id}</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Quick Services */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Common Services</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-3">
              {COMMON_SERVICES.map(service => (
                <Button
                  key={service.id}
                  variant="outline"
                  className="h-16 flex flex-col justify-center"
                  onClick={() => addToCart(service)}
                >
                  <span className="font-medium">{service.description}</span>
                  {service.amount > 0 && (
                    <span className="text-sm text-gray-600">${service.amount}</span>
                  )}
                </Button>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Custom Item */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Add Custom Item</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex gap-2">
              <Input
                placeholder="Description"
                value={customDescription}
                onChange={(e) => setCustomDescription(e.target.value)}
                className="flex-1"
              />
              <Input
                placeholder="Amount"
                type="number"
                step="0.01"
                value={customAmount}
                onChange={(e) => setCustomAmount(e.target.value)}
                className="w-32"
              />
              <Button onClick={addCustomItem}>Add</Button>
            </div>
          </CardContent>
        </Card>

        {/* Quick Amounts */}
        <Card>
          <CardHeader>
            <CardTitle>Quick Amounts</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-3">
              {QUICK_AMOUNTS.map(amount => (
                <Button
                  key={amount}
                  variant="outline"
                  className="h-16 text-lg font-medium"
                  onClick={() => addQuickAmount(amount)}
                >
                  ${amount}
                </Button>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Right Panel - Cart & Payment */}
      <div className="w-96 bg-white border-l flex flex-col">
        {/* Cart */}
        <div className="flex-1 p-6 overflow-y-auto">
          <h2 className="text-xl font-bold mb-4">Cart</h2>

          {cart.length === 0 ? (
            <div className="text-center text-gray-500 py-8">
              <DollarSign className="h-12 w-12 mx-auto mb-2 opacity-50" />
              <p>Cart is empty</p>
            </div>
          ) : (
            <div className="space-y-3">
              {cart.map(item => (
                <div key={item.tempId} className="flex items-center gap-2 p-3 border rounded-lg">
                  <div className="flex-1">
                    <p className="font-medium text-sm">{item.description}</p>
                    <p className="text-xs text-gray-600">${item.amount.toFixed(2)} each</p>
                  </div>
                  <div className="flex items-center gap-1">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => updateQuantity(item.tempId, item.quantity - 1)}
                    >
                      -
                    </Button>
                    <span className="w-8 text-center">{item.quantity}</span>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => updateQuantity(item.tempId, item.quantity + 1)}
                    >
                      +
                    </Button>
                  </div>
                  <Button
                    size="sm"
                    variant="destructive"
                    onClick={() => removeFromCart(item.tempId)}
                  >
                    ×
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Totals & Payment */}
        {cart.length > 0 && (
          <div className="border-t p-6">
            {/* Totals */}
            <div className="space-y-2 mb-4">
              <div className="flex justify-between">
                <span>Subtotal:</span>
                <span>${subtotal.toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span>Tax (8%):</span>
                <span>${taxAmount.toFixed(2)}</span>
              </div>
              <Separator />
              <div className="flex justify-between text-lg font-bold">
                <span>Total:</span>
                <span>${total.toFixed(2)}</span>
              </div>
            </div>

            {/* Payment Method */}
            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">Payment Method</label>
              <div className="grid grid-cols-2 gap-2">
                <Button
                  variant={selectedPaymentMethod === PaymentMethod.CASH ? "default" : "outline"}
                  onClick={() => setSelectedPaymentMethod(PaymentMethod.CASH)}
                  className="flex items-center gap-2"
                >
                  <Banknote className="h-4 w-4" />
                  Cash
                </Button>
                <Button
                  variant={selectedPaymentMethod === PaymentMethod.CREDIT_CARD ? "default" : "outline"}
                  onClick={() => setSelectedPaymentMethod(PaymentMethod.CREDIT_CARD)}
                  className="flex items-center gap-2"
                  disabled={!cardReaderConnected}
                >
                  <CreditCard className="h-4 w-4" />
                  Card
                </Button>
                <Button
                  variant={selectedPaymentMethod === PaymentMethod.MOBILE_PAYMENT ? "default" : "outline"}
                  onClick={() => setSelectedPaymentMethod(PaymentMethod.MOBILE_PAYMENT)}
                  className="flex items-center gap-2"
                >
                  <Smartphone className="h-4 w-4" />
                  Mobile
                </Button>
                <Button
                  variant={selectedPaymentMethod === PaymentMethod.BANK_TRANSFER ? "default" : "outline"}
                  onClick={() => setSelectedPaymentMethod(PaymentMethod.BANK_TRANSFER)}
                  className="flex items-center gap-2"
                >
                  Bank
                </Button>
              </div>
            </div>

            {/* Payment Amount */}
            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">Payment Amount</label>
              <Input
                type="number"
                step="0.01"
                placeholder={`$${total.toFixed(2)}`}
                value={paymentAmount}
                onChange={(e) => setPaymentAmount(e.target.value)}
              />
            </div>

            {/* Fraud Alert */}
            {fraudAlert && (
              <Alert className="mb-4 border-yellow-300 bg-yellow-50">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription className="flex justify-between items-center">
                  <span>{fraudAlert}</span>
                  <Button size="sm" variant="outline" onClick={clearFraudAlert}>
                    Override
                  </Button>
                </AlertDescription>
              </Alert>
            )}

            {/* Card Reader Status */}
            {!cardReaderConnected && (
              <Alert className="mb-4 border-red-300 bg-red-50">
                <XCircle className="h-4 w-4" />
                <AlertDescription>
                  Card reader disconnected. Cash only.
                </AlertDescription>
              </Alert>
            )}

            {/* Process Payment Button */}
            <Button
              className="w-full h-12 text-lg"
              onClick={processPayment}
              disabled={processing || !selectedStudent || cart.length === 0}
            >
              {processing ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Processing...
                </>
              ) : (
                <>
                  <CheckCircle className="h-4 w-4 mr-2" />
                  Process Payment
                </>
              )}
            </Button>

            {/* Cashier Session Info */}
            {cashierSession && (
              <div className="mt-4 p-3 bg-gray-50 rounded-lg text-sm">
                <p className="font-medium">Session: {cashierSession.cashier_name}</p>
                <p>Transactions: {cashierSession.transaction_count}</p>
                <p>Total: ${cashierSession.total_collected.toFixed(2)}</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default POSInterface;