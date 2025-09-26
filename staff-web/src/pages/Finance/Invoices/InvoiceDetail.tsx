/**
 * Invoice Detail Modal Component
 * Comprehensive invoice view with payment history and management
 */

import React, { useState, useEffect, useCallback } from 'react';
import { DetailModal, InfoTab, TimelineTab, DocumentsTab, DetailTab, DetailAction } from '../../../components/patterns';
import { Button } from '../../../components/ui/button';
import { Badge } from '../../../components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/card';
import { Input } from '../../../components/ui/input';
import { Label } from '../../../components/ui/label';
import { Textarea } from '../../../components/ui/textarea';
import { Alert, AlertDescription } from '../../../components/ui/alert';
import { Separator } from '../../../components/ui/separator';
import { useToast } from '../../../hooks/use-toast';
import {
  DollarSign, Calendar, User, FileText, CreditCard, Send, Printer,
  Edit, Plus, Trash2, AlertCircle, CheckCircle, Clock, XCircle
} from 'lucide-react';
import { financeService } from '../../../services/financeService';
import { Invoice, InvoiceStatus, Payment, PaymentPlan, InvoiceLineItem } from '../../../types/finance.types';
import { format } from 'date-fns';

interface InvoiceDetailProps {
  invoiceId: string;
  isOpen: boolean;
  onClose: () => void;
  onUpdate?: () => void;
}

export const InvoiceDetail: React.FC<InvoiceDetailProps> = ({
  invoiceId,
  isOpen,
  onClose,
  onUpdate
}) => {
  const [invoice, setInvoice] = useState<Invoice | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('info');
  const [editingLineItems, setEditingLineItems] = useState(false);
  const [newLineItem, setNewLineItem] = useState<Partial<InvoiceLineItem>>({});
  const [paymentPlanAmount, setPaymentPlanAmount] = useState('');
  const [reminderNotes, setReminderNotes] = useState('');

  const { toast } = useToast();

  // Mock data for demonstration
  const mockInvoice: Invoice = {
    id: invoiceId,
    invoice_number: 'INV-2024-001',
    student_id: '1',
    student_name: 'John Doe',
    amount: 1500.00,
    tax_amount: 120.00,
    total_amount: 1620.00,
    status: InvoiceStatus.PENDING,
    due_date: '2024-10-15',
    created_date: '2024-09-15',
    description: 'Fall 2024 Tuition',
    line_items: [
      {
        id: '1',
        description: 'Tuition - Advanced English',
        quantity: 1,
        unit_price: 800.00,
        tax_rate: 0.08,
        total: 800.00,
        course_id: 'ENG-ADV-001',
        service_type: 'tuition'
      },
      {
        id: '2',
        description: 'Lab Fee - Language Lab',
        quantity: 1,
        unit_price: 150.00,
        tax_rate: 0.08,
        total: 150.00,
        service_type: 'fee'
      },
      {
        id: '3',
        description: 'Materials Fee',
        quantity: 1,
        unit_price: 550.00,
        tax_rate: 0.08,
        total: 550.00,
        service_type: 'materials'
      }
    ],
    payment_plans: [],
    discounts: [],
    attachments: [
      {
        id: '1',
        name: 'enrollment_form.pdf',
        type: 'application/pdf',
        url: '/documents/enrollment_form.pdf',
        uploaded_date: '2024-09-15',
        size: 245760
      }
    ],
    payment_history: [
      {
        id: '1',
        invoice_id: invoiceId,
        student_id: '1',
        amount: 500.00,
        payment_method: 'credit_card',
        status: 'completed',
        transaction_id: 'TXN-001',
        processed_date: '2024-09-20',
        receipt_number: 'RCP-001',
        notes: 'Partial payment'
      }
    ]
  };

  // Load invoice details
  const loadInvoice = useCallback(async () => {
    setLoading(true);
    try {
      // For demo, use mock data
      setInvoice(mockInvoice);
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to load invoice details",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  }, [invoiceId, toast]);

  useEffect(() => {
    if (isOpen && invoiceId) {
      loadInvoice();
    }
  }, [isOpen, invoiceId, loadInvoice]);

  if (!invoice) return null;

  // Status badge variant
  const getStatusVariant = (status: InvoiceStatus) => {
    switch (status) {
      case InvoiceStatus.PAID: return 'default';
      case InvoiceStatus.PENDING: return 'secondary';
      case InvoiceStatus.OVERDUE: return 'destructive';
      case InvoiceStatus.CANCELLED: return 'outline';
      default: return 'secondary';
    }
  };

  // Status icon
  const getStatusIcon = (status: InvoiceStatus) => {
    switch (status) {
      case InvoiceStatus.PAID: return CheckCircle;
      case InvoiceStatus.PENDING: return Clock;
      case InvoiceStatus.OVERDUE: return AlertCircle;
      case InvoiceStatus.CANCELLED: return XCircle;
      default: return Clock;
    }
  };

  // Calculate remaining balance
  const totalPaid = invoice.payment_history.reduce((sum, payment) =>
    payment.status === 'completed' ? sum + payment.amount : sum, 0
  );
  const remainingBalance = invoice.total_amount - totalPaid;

  // Send reminder
  const sendReminder = useCallback(async () => {
    try {
      await financeService.sendInvoiceReminder(invoice.id);
      toast({
        title: "Reminder Sent",
        description: "Payment reminder has been sent to the student",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to send reminder",
        variant: "destructive"
      });
    }
  }, [invoice.id, toast]);

  // Add line item
  const addLineItem = useCallback(async () => {
    if (!newLineItem.description || !newLineItem.unit_price) {
      toast({
        title: "Missing Information",
        description: "Please enter description and unit price",
        variant: "destructive"
      });
      return;
    }

    try {
      // Mock implementation - in real app, would call API
      const lineItem: InvoiceLineItem = {
        id: Date.now().toString(),
        description: newLineItem.description,
        quantity: newLineItem.quantity || 1,
        unit_price: newLineItem.unit_price,
        tax_rate: newLineItem.tax_rate || 0.08,
        total: (newLineItem.quantity || 1) * newLineItem.unit_price,
        service_type: newLineItem.service_type || 'custom'
      };

      invoice.line_items.push(lineItem);
      setNewLineItem({});
      toast({
        title: "Line Item Added",
        description: "Invoice line item has been added",
      });
      onUpdate?.();
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to add line item",
        variant: "destructive"
      });
    }
  }, [newLineItem, invoice, toast, onUpdate]);

  // Create payment plan
  const createPaymentPlan = useCallback(async () => {
    const downPayment = parseFloat(paymentPlanAmount);
    if (isNaN(downPayment) || downPayment <= 0 || downPayment >= remainingBalance) {
      toast({
        title: "Invalid Amount",
        description: "Please enter a valid down payment amount",
        variant: "destructive"
      });
      return;
    }

    try {
      const paymentPlanData = {
        invoice_id: invoice.id,
        total_amount: remainingBalance,
        down_payment: downPayment
      };

      await financeService.createPaymentPlan(paymentPlanData);
      toast({
        title: "Payment Plan Created",
        description: "Payment plan has been set up for this invoice",
      });
      setPaymentPlanAmount('');
      loadInvoice();
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to create payment plan",
        variant: "destructive"
      });
    }
  }, [paymentPlanAmount, remainingBalance, invoice.id, toast, loadInvoice]);

  // Print invoice
  const printInvoice = useCallback(() => {
    // Mock print functionality
    toast({
      title: "Printing",
      description: `Printing invoice ${invoice.invoice_number}`,
    });
  }, [invoice.invoice_number, toast]);

  // Update invoice status
  const updateStatus = useCallback(async (newStatus: InvoiceStatus) => {
    try {
      await financeService.updateInvoice(invoice.id, { status: newStatus });
      toast({
        title: "Status Updated",
        description: `Invoice status updated to ${newStatus}`,
      });
      loadInvoice();
      onUpdate?.();
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to update invoice status",
        variant: "destructive"
      });
    }
  }, [invoice.id, toast, loadInvoice, onUpdate]);

  // Define tabs
  const tabs: DetailTab[] = [
    {
      id: 'info',
      label: 'Invoice Details',
      icon: FileText,
      content: (
        <InfoTab
          title={`Invoice ${invoice.invoice_number}`}
          subtitle={`Created on ${format(new Date(invoice.created_date), 'MMMM dd, yyyy')}`}
          status={
            <Badge variant={getStatusVariant(invoice.status)} className="flex items-center gap-1">
              {React.createElement(getStatusIcon(invoice.status), { className: "h-3 w-3" })}
              {invoice.status.charAt(0).toUpperCase() + invoice.status.slice(1)}
            </Badge>
          }
          sections={[
            {
              title: 'Student Information',
              icon: User,
              content: (
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Name:</span>
                    <span className="font-medium">{invoice.student_name}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Student ID:</span>
                    <span className="font-medium">{invoice.student_id}</span>
                  </div>
                </div>
              )
            },
            {
              title: 'Invoice Summary',
              icon: DollarSign,
              content: (
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Subtotal:</span>
                    <span>${invoice.amount.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Tax:</span>
                    <span>${invoice.tax_amount.toFixed(2)}</span>
                  </div>
                  <Separator />
                  <div className="flex justify-between text-lg font-bold">
                    <span>Total:</span>
                    <span>${invoice.total_amount.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Total Paid:</span>
                    <span className="text-green-600">${totalPaid.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Remaining Balance:</span>
                    <span className={remainingBalance > 0 ? 'text-red-600 font-medium' : 'text-green-600'}>
                      ${remainingBalance.toFixed(2)}
                    </span>
                  </div>
                </div>
              )
            },
            {
              title: 'Line Items',
              icon: FileText,
              content: (
                <div className="space-y-4">
                  {/* Existing Line Items */}
                  <div className="space-y-2">
                    {invoice.line_items.map((item, index) => (
                      <div key={item.id} className="flex justify-between items-center p-3 border rounded-lg">
                        <div className="flex-1">
                          <p className="font-medium">{item.description}</p>
                          <p className="text-sm text-gray-600">
                            {item.quantity} × ${item.unit_price.toFixed(2)}
                            {item.course_id && ` • Course: ${item.course_id}`}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="font-medium">${item.total.toFixed(2)}</p>
                          {item.tax_rate > 0 && (
                            <p className="text-sm text-gray-600">
                              +${(item.total * item.tax_rate).toFixed(2)} tax
                            </p>
                          )}
                        </div>
                        {editingLineItems && (
                          <Button size="sm" variant="destructive" className="ml-2">
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        )}
                      </div>
                    ))}
                  </div>

                  {/* Add New Line Item */}
                  {editingLineItems && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-lg">Add Line Item</CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <Label htmlFor="description">Description</Label>
                            <Input
                              id="description"
                              value={newLineItem.description || ''}
                              onChange={(e) => setNewLineItem(prev => ({ ...prev, description: e.target.value }))}
                              placeholder="Item description"
                            />
                          </div>
                          <div>
                            <Label htmlFor="service-type">Service Type</Label>
                            <Input
                              id="service-type"
                              value={newLineItem.service_type || ''}
                              onChange={(e) => setNewLineItem(prev => ({ ...prev, service_type: e.target.value }))}
                              placeholder="tuition, fee, materials, etc."
                            />
                          </div>
                        </div>
                        <div className="grid grid-cols-3 gap-4">
                          <div>
                            <Label htmlFor="quantity">Quantity</Label>
                            <Input
                              id="quantity"
                              type="number"
                              value={newLineItem.quantity || 1}
                              onChange={(e) => setNewLineItem(prev => ({ ...prev, quantity: parseInt(e.target.value) || 1 }))}
                              min="1"
                            />
                          </div>
                          <div>
                            <Label htmlFor="unit-price">Unit Price</Label>
                            <Input
                              id="unit-price"
                              type="number"
                              step="0.01"
                              value={newLineItem.unit_price || ''}
                              onChange={(e) => setNewLineItem(prev => ({ ...prev, unit_price: parseFloat(e.target.value) || 0 }))}
                              placeholder="0.00"
                            />
                          </div>
                          <div>
                            <Label htmlFor="tax-rate">Tax Rate</Label>
                            <Input
                              id="tax-rate"
                              type="number"
                              step="0.01"
                              value={newLineItem.tax_rate || 0.08}
                              onChange={(e) => setNewLineItem(prev => ({ ...prev, tax_rate: parseFloat(e.target.value) || 0 }))}
                              placeholder="0.08"
                            />
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <Button onClick={addLineItem}>
                            <Plus className="h-4 w-4 mr-2" />
                            Add Item
                          </Button>
                          <Button variant="outline" onClick={() => setEditingLineItems(false)}>
                            Done
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {!editingLineItems && (
                    <Button variant="outline" onClick={() => setEditingLineItems(true)}>
                      <Edit className="h-4 w-4 mr-2" />
                      Edit Line Items
                    </Button>
                  )}
                </div>
              )
            },
            {
              title: 'Payment Plan Setup',
              icon: Calendar,
              content: remainingBalance > 0 ? (
                <div className="space-y-4">
                  <Alert>
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                      Remaining balance: ${remainingBalance.toFixed(2)}
                    </AlertDescription>
                  </Alert>

                  <div className="space-y-2">
                    <Label htmlFor="down-payment">Down Payment Amount</Label>
                    <Input
                      id="down-payment"
                      type="number"
                      step="0.01"
                      value={paymentPlanAmount}
                      onChange={(e) => setPaymentPlanAmount(e.target.value)}
                      placeholder="Enter down payment amount"
                    />
                  </div>

                  <Button onClick={createPaymentPlan} disabled={!paymentPlanAmount}>
                    Create Payment Plan
                  </Button>
                </div>
              ) : (
                <div className="text-center py-4 text-green-600">
                  <CheckCircle className="h-8 w-8 mx-auto mb-2" />
                  <p>Invoice is fully paid</p>
                </div>
              )
            }
          ]}
        />
      )
    },
    {
      id: 'payments',
      label: 'Payment History',
      icon: CreditCard,
      content: (
        <TimelineTab
          title="Payment History"
          subtitle={`${invoice.payment_history.length} payments recorded`}
          items={invoice.payment_history.map(payment => ({
            id: payment.id,
            date: payment.processed_date,
            title: `Payment - ${payment.payment_method}`,
            description: `$${payment.amount.toFixed(2)} • Receipt: ${payment.receipt_number}`,
            status: payment.status === 'completed' ? 'completed' : 'pending',
            metadata: {
              'Transaction ID': payment.transaction_id,
              'Payment Method': payment.payment_method,
              'Status': payment.status,
              'Notes': payment.notes || 'No notes'
            }
          }))}
          emptyState={{
            title: "No payments recorded",
            description: "No payments have been made for this invoice yet",
            action: (
              <Button onClick={() => {/* Open payment modal */}}>
                Record Payment
              </Button>
            )
          }}
        />
      )
    },
    {
      id: 'documents',
      label: 'Documents',
      icon: FileText,
      content: (
        <DocumentsTab
          title="Invoice Documents"
          subtitle="Attachments and related documents"
          documents={invoice.attachments.map(doc => ({
            id: doc.id,
            name: doc.name,
            type: doc.type,
            size: doc.size,
            uploadedAt: doc.uploaded_date,
            url: doc.url
          }))}
          onUpload={(files) => {
            // Handle file upload
            toast({
              title: "Files Uploaded",
              description: `${files.length} files uploaded successfully`,
            });
          }}
          onDelete={(documentId) => {
            // Handle file deletion
            toast({
              title: "Document Deleted",
              description: "Document has been removed",
            });
          }}
        />
      )
    }
  ];

  // Define actions
  const actions: DetailAction[] = [
    {
      label: 'Send Reminder',
      icon: Send,
      onClick: sendReminder,
      disabled: invoice.status === InvoiceStatus.PAID || invoice.status === InvoiceStatus.CANCELLED
    },
    {
      label: 'Print Invoice',
      icon: Printer,
      onClick: printInvoice
    },
    {
      label: 'Mark as Paid',
      icon: CheckCircle,
      onClick: () => updateStatus(InvoiceStatus.PAID),
      disabled: invoice.status === InvoiceStatus.PAID,
      variant: 'default'
    },
    {
      label: 'Cancel Invoice',
      icon: XCircle,
      onClick: () => updateStatus(InvoiceStatus.CANCELLED),
      disabled: invoice.status === InvoiceStatus.PAID || invoice.status === InvoiceStatus.CANCELLED,
      variant: 'destructive'
    }
  ];

  return (
    <DetailModal
      isOpen={isOpen}
      onClose={onClose}
      title={`Invoice ${invoice.invoice_number}`}
      subtitle={invoice.description}
      tabs={tabs}
      actions={actions}
      loading={loading}
      className="max-w-4xl"
    />
  );
};

export default InvoiceDetail;