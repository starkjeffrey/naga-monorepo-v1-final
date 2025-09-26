/**
 * Invoice Creation Wizard Component
 * Multi-step invoice creation with automated pricing and validation
 */

import React, { useState, useCallback, useEffect } from 'react';
import { Wizard, WizardStep } from '../../../components/patterns';
import { Button } from '../../../components/ui/button';
import { Input } from '../../../components/ui/input';
import { Label } from '../../../components/ui/label';
import { Textarea } from '../../../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../components/ui/select';
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/card';
import { Badge } from '../../../components/ui/badge';
import { Alert, AlertDescription } from '../../../components/ui/alert';
import { Separator } from '../../../components/ui/separator';
import { Checkbox } from '../../../components/ui/checkbox';
import { useToast } from '../../../hooks/use-toast';
import {
  User, DollarSign, Calendar, FileText, Search, Plus, Trash2,
  AlertCircle, CheckCircle, Calculator, Percent
} from 'lucide-react';
import { financeService } from '../../../services/financeService';
import { Student, Invoice, InvoiceLineItem, Discount, Course } from '../../../types/finance.types';

interface InvoiceWizardProps {
  onComplete: (invoice: Invoice) => void;
  onCancel: () => void;
  preselectedStudent?: Student;
}

interface InvoiceFormData {
  student?: Student;
  lineItems: Partial<InvoiceLineItem>[];
  discounts: Partial<Discount>[];
  dueDate: string;
  description: string;
  notes: string;
  sendNotification: boolean;
  paymentTerms: string;
}

const INITIAL_FORM_DATA: InvoiceFormData = {
  lineItems: [],
  discounts: [],
  dueDate: '',
  description: '',
  notes: '',
  sendNotification: true,
  paymentTerms: 'net_30'
};

const PAYMENT_TERMS = [
  { value: 'due_on_receipt', label: 'Due on Receipt' },
  { value: 'net_15', label: 'Net 15 Days' },
  { value: 'net_30', label: 'Net 30 Days' },
  { value: 'net_60', label: 'Net 60 Days' }
];

const SERVICE_TEMPLATES = [
  {
    id: 'tuition_basic',
    description: 'Basic Language Course Tuition',
    amount: 800.00,
    category: 'tuition',
    tax_rate: 0.08
  },
  {
    id: 'tuition_advanced',
    description: 'Advanced Language Course Tuition',
    amount: 1200.00,
    category: 'tuition',
    tax_rate: 0.08
  },
  {
    id: 'registration_fee',
    description: 'Registration Fee',
    amount: 50.00,
    category: 'fee',
    tax_rate: 0.08
  },
  {
    id: 'materials_fee',
    description: 'Course Materials',
    amount: 150.00,
    category: 'materials',
    tax_rate: 0.08
  },
  {
    id: 'lab_fee',
    description: 'Language Lab Fee',
    amount: 75.00,
    category: 'fee',
    tax_rate: 0.08
  },
  {
    id: 'exam_fee',
    description: 'Placement Exam Fee',
    amount: 25.00,
    category: 'fee',
    tax_rate: 0.08
  }
];

export const InvoiceWizard: React.FC<InvoiceWizardProps> = ({
  onComplete,
  onCancel,
  preselectedStudent
}) => {
  const [formData, setFormData] = useState<InvoiceFormData>({
    ...INITIAL_FORM_DATA,
    student: preselectedStudent
  });
  const [studentSearch, setStudentSearch] = useState('');
  const [searchResults, setSearchResults] = useState<Student[]>([]);
  const [availableCourses, setAvailableCourses] = useState<Course[]>([]);
  const [duplicateWarning, setDuplicateWarning] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);

  const { toast } = useToast();

  // Mock students for demo
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

  // Check for duplicate invoices
  useEffect(() => {
    if (formData.student && formData.lineItems.length > 0) {
      // Mock duplicate check
      const hasTuitionItem = formData.lineItems.some(item =>
        item.description?.toLowerCase().includes('tuition')
      );
      if (hasTuitionItem) {
        setDuplicateWarning('Student may already have a tuition invoice for this period. Please verify before proceeding.');
      } else {
        setDuplicateWarning(null);
      }
    }
  }, [formData.student, formData.lineItems]);

  // Calculate totals
  const subtotal = formData.lineItems.reduce((sum, item) => {
    const itemTotal = (item.quantity || 1) * (item.unit_price || 0);
    return sum + itemTotal;
  }, 0);

  const discountAmount = formData.discounts.reduce((sum, discount) => {
    if (discount.type === 'percentage') {
      return sum + (subtotal * ((discount.value || 0) / 100));
    } else {
      return sum + (discount.value || 0);
    }
  }, 0);

  const taxableAmount = subtotal - discountAmount;
  const taxAmount = formData.lineItems.reduce((sum, item) => {
    const itemTotal = (item.quantity || 1) * (item.unit_price || 0);
    const itemTaxRate = item.tax_rate || 0;
    return sum + (itemTotal * itemTaxRate);
  }, 0);

  const total = taxableAmount + taxAmount;

  // Select student
  const selectStudent = useCallback((student: Student) => {
    setFormData(prev => ({ ...prev, student }));
    setStudentSearch('');
    setSearchResults([]);
  }, []);

  // Add line item from template
  const addServiceTemplate = useCallback((template: typeof SERVICE_TEMPLATES[0]) => {
    const lineItem: Partial<InvoiceLineItem> = {
      id: Date.now().toString(),
      description: template.description,
      quantity: 1,
      unit_price: template.amount,
      tax_rate: template.tax_rate,
      total: template.amount,
      service_type: template.category
    };

    setFormData(prev => ({
      ...prev,
      lineItems: [...prev.lineItems, lineItem]
    }));
  }, []);

  // Add custom line item
  const addCustomLineItem = useCallback(() => {
    const lineItem: Partial<InvoiceLineItem> = {
      id: Date.now().toString(),
      description: '',
      quantity: 1,
      unit_price: 0,
      tax_rate: 0.08,
      total: 0,
      service_type: 'custom'
    };

    setFormData(prev => ({
      ...prev,
      lineItems: [...prev.lineItems, lineItem]
    }));
  }, []);

  // Update line item
  const updateLineItem = useCallback((index: number, updates: Partial<InvoiceLineItem>) => {
    setFormData(prev => ({
      ...prev,
      lineItems: prev.lineItems.map((item, i) => {
        if (i === index) {
          const updated = { ...item, ...updates };
          updated.total = (updated.quantity || 1) * (updated.unit_price || 0);
          return updated;
        }
        return item;
      })
    }));
  }, []);

  // Remove line item
  const removeLineItem = useCallback((index: number) => {
    setFormData(prev => ({
      ...prev,
      lineItems: prev.lineItems.filter((_, i) => i !== index)
    }));
  }, []);

  // Add discount
  const addDiscount = useCallback(() => {
    const discount: Partial<Discount> = {
      id: Date.now().toString(),
      name: '',
      type: 'percentage',
      value: 0,
      description: ''
    };

    setFormData(prev => ({
      ...prev,
      discounts: [...prev.discounts, discount]
    }));
  }, []);

  // Update discount
  const updateDiscount = useCallback((index: number, updates: Partial<Discount>) => {
    setFormData(prev => ({
      ...prev,
      discounts: prev.discounts.map((discount, i) =>
        i === index ? { ...discount, ...updates } : discount
      )
    }));
  }, []);

  // Remove discount
  const removeDiscount = useCallback((index: number) => {
    setFormData(prev => ({
      ...prev,
      discounts: prev.discounts.filter((_, i) => i !== index)
    }));
  }, []);

  // Submit invoice
  const submitInvoice = useCallback(async () => {
    if (!formData.student) {
      toast({
        title: "Missing Student",
        description: "Please select a student",
        variant: "destructive"
      });
      return;
    }

    if (formData.lineItems.length === 0) {
      toast({
        title: "No Line Items",
        description: "Please add at least one line item",
        variant: "destructive"
      });
      return;
    }

    setProcessing(true);

    try {
      const invoiceData = {
        student_id: formData.student.id,
        student_name: `${formData.student.first_name} ${formData.student.last_name}`,
        amount: subtotal,
        tax_amount: taxAmount,
        total_amount: total,
        due_date: formData.dueDate,
        description: formData.description,
        line_items: formData.lineItems as InvoiceLineItem[],
        discounts: formData.discounts as Discount[],
        payment_plans: [],
        attachments: [],
        payment_history: []
      };

      const response = await financeService.createInvoice(invoiceData);

      if (response.success) {
        toast({
          title: "Invoice Created",
          description: `Invoice ${response.data.invoice_number} created successfully`,
        });

        // Send notification if requested
        if (formData.sendNotification) {
          await financeService.sendInvoiceReminder(response.data.id);
        }

        onComplete(response.data);
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to create invoice",
        variant: "destructive"
      });
    } finally {
      setProcessing(false);
    }
  }, [formData, subtotal, taxAmount, total, onComplete, toast]);

  // Wizard steps
  const steps: WizardStep[] = [
    {
      id: 'student',
      title: 'Select Student',
      description: 'Choose the student for this invoice',
      content: (
        <div className="space-y-6">
          {!formData.student ? (
            <>
              <div>
                <Label htmlFor="student-search">Search Student</Label>
                <div className="relative">
                  <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                  <Input
                    id="student-search"
                    placeholder="Search by name, student ID, or email..."
                    value={studentSearch}
                    onChange={(e) => setStudentSearch(e.target.value)}
                    className="pl-10"
                  />
                </div>
              </div>

              {searchResults.length > 0 && (
                <div className="space-y-2">
                  {searchResults.map(student => (
                    <Card
                      key={student.id}
                      className="cursor-pointer hover:bg-gray-50 transition-colors"
                      onClick={() => selectStudent(student)}
                    >
                      <CardContent className="p-4">
                        <div className="flex justify-between items-start">
                          <div>
                            <p className="font-medium">{student.first_name} {student.last_name}</p>
                            <p className="text-sm text-gray-600">{student.student_id}</p>
                            <p className="text-sm text-gray-600">{student.email}</p>
                          </div>
                          <div className="text-right">
                            <Badge variant={student.account_balance < 0 ? "destructive" : "default"}>
                              Balance: ${student.account_balance.toFixed(2)}
                            </Badge>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </>
          ) : (
            <Card>
              <CardContent className="p-4">
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="font-medium text-lg">
                      {formData.student.first_name} {formData.student.last_name}
                    </h3>
                    <p className="text-gray-600">{formData.student.student_id}</p>
                    <p className="text-gray-600">{formData.student.email}</p>
                  </div>
                  <div className="text-right">
                    <Badge variant={formData.student.account_balance < 0 ? "destructive" : "default"}>
                      Balance: ${formData.student.account_balance.toFixed(2)}
                    </Badge>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setFormData(prev => ({ ...prev, student: undefined }))}
                      className="ml-2"
                    >
                      Change
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      ),
      validation: () => !!formData.student
    },
    {
      id: 'services',
      title: 'Select Services',
      description: 'Add courses and services to the invoice',
      content: (
        <div className="space-y-6">
          {/* Service Templates */}
          <div>
            <h3 className="text-lg font-medium mb-4">Common Services</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {SERVICE_TEMPLATES.map(template => (
                <Card
                  key={template.id}
                  className="cursor-pointer hover:bg-gray-50 transition-colors"
                  onClick={() => addServiceTemplate(template)}
                >
                  <CardContent className="p-4">
                    <div className="flex justify-between items-center">
                      <div>
                        <p className="font-medium">{template.description}</p>
                        <p className="text-sm text-gray-600">{template.category}</p>
                      </div>
                      <div className="text-right">
                        <p className="font-medium">${template.amount.toFixed(2)}</p>
                        <Plus className="h-4 w-4 text-blue-500 mx-auto mt-1" />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>

          {/* Current Line Items */}
          {formData.lineItems.length > 0 && (
            <div>
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-medium">Invoice Items</h3>
                <Button variant="outline" onClick={addCustomLineItem}>
                  <Plus className="h-4 w-4 mr-2" />
                  Add Custom Item
                </Button>
              </div>

              <div className="space-y-3">
                {formData.lineItems.map((item, index) => (
                  <Card key={item.id}>
                    <CardContent className="p-4">
                      <div className="grid grid-cols-1 md:grid-cols-5 gap-4 items-end">
                        <div className="md:col-span-2">
                          <Label>Description</Label>
                          <Input
                            value={item.description || ''}
                            onChange={(e) => updateLineItem(index, { description: e.target.value })}
                            placeholder="Service description"
                          />
                        </div>
                        <div>
                          <Label>Quantity</Label>
                          <Input
                            type="number"
                            min="1"
                            value={item.quantity || 1}
                            onChange={(e) => updateLineItem(index, { quantity: parseInt(e.target.value) || 1 })}
                          />
                        </div>
                        <div>
                          <Label>Unit Price</Label>
                          <Input
                            type="number"
                            step="0.01"
                            value={item.unit_price || ''}
                            onChange={(e) => updateLineItem(index, { unit_price: parseFloat(e.target.value) || 0 })}
                            placeholder="0.00"
                          />
                        </div>
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="text-sm text-gray-600">Total</p>
                            <p className="font-medium">${((item.quantity || 1) * (item.unit_price || 0)).toFixed(2)}</p>
                          </div>
                          <Button
                            size="sm"
                            variant="destructive"
                            onClick={() => removeLineItem(index)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {formData.lineItems.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              <DollarSign className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No items added yet</p>
              <p className="text-sm">Select from common services above or add a custom item</p>
              <Button variant="outline" onClick={addCustomLineItem} className="mt-4">
                <Plus className="h-4 w-4 mr-2" />
                Add Custom Item
              </Button>
            </div>
          )}
        </div>
      ),
      validation: () => formData.lineItems.length > 0
    },
    {
      id: 'discounts',
      title: 'Discounts & Adjustments',
      description: 'Apply discounts or scholarships',
      content: (
        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-medium">Discounts</h3>
            <Button variant="outline" onClick={addDiscount}>
              <Percent className="h-4 w-4 mr-2" />
              Add Discount
            </Button>
          </div>

          {formData.discounts.length > 0 ? (
            <div className="space-y-3">
              {formData.discounts.map((discount, index) => (
                <Card key={discount.id}>
                  <CardContent className="p-4">
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
                      <div>
                        <Label>Discount Name</Label>
                        <Input
                          value={discount.name || ''}
                          onChange={(e) => updateDiscount(index, { name: e.target.value })}
                          placeholder="Scholarship, Early Bird, etc."
                        />
                      </div>
                      <div>
                        <Label>Type</Label>
                        <Select
                          value={discount.type || 'percentage'}
                          onValueChange={(value) => updateDiscount(index, { type: value as 'percentage' | 'fixed' })}
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="percentage">Percentage</SelectItem>
                            <SelectItem value="fixed">Fixed Amount</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div>
                        <Label>Value</Label>
                        <Input
                          type="number"
                          step="0.01"
                          value={discount.value || ''}
                          onChange={(e) => updateDiscount(index, { value: parseFloat(e.target.value) || 0 })}
                          placeholder={discount.type === 'percentage' ? '10' : '100.00'}
                        />
                      </div>
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm text-gray-600">Amount</p>
                          <p className="font-medium">
                            ${discount.type === 'percentage'
                              ? (subtotal * ((discount.value || 0) / 100)).toFixed(2)
                              : (discount.value || 0).toFixed(2)
                            }
                          </p>
                        </div>
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => removeDiscount(index)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              <Percent className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No discounts applied</p>
              <p className="text-sm">Add discounts or scholarships to reduce the total amount</p>
            </div>
          )}

          {/* Totals Preview */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Calculator className="h-5 w-5" />
                Invoice Totals
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="flex justify-between">
                <span>Subtotal:</span>
                <span>${subtotal.toFixed(2)}</span>
              </div>
              {discountAmount > 0 && (
                <div className="flex justify-between text-green-600">
                  <span>Discounts:</span>
                  <span>-${discountAmount.toFixed(2)}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span>Tax:</span>
                <span>${taxAmount.toFixed(2)}</span>
              </div>
              <Separator />
              <div className="flex justify-between text-lg font-bold">
                <span>Total:</span>
                <span>${total.toFixed(2)}</span>
              </div>
            </CardContent>
          </Card>
        </div>
      ),
      validation: () => true
    },
    {
      id: 'terms',
      title: 'Payment Terms',
      description: 'Set due date and payment terms',
      content: (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <Label htmlFor="due-date">Due Date</Label>
              <Input
                id="due-date"
                type="date"
                value={formData.dueDate}
                onChange={(e) => setFormData(prev => ({ ...prev, dueDate: e.target.value }))}
              />
            </div>
            <div>
              <Label htmlFor="payment-terms">Payment Terms</Label>
              <Select
                value={formData.paymentTerms}
                onValueChange={(value) => setFormData(prev => ({ ...prev, paymentTerms: value }))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PAYMENT_TERMS.map(term => (
                    <SelectItem key={term.value} value={term.value}>
                      {term.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div>
            <Label htmlFor="description">Invoice Description</Label>
            <Input
              id="description"
              value={formData.description}
              onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
              placeholder="e.g., Fall 2024 Language Course Fees"
            />
          </div>

          <div>
            <Label htmlFor="notes">Notes (Optional)</Label>
            <Textarea
              id="notes"
              value={formData.notes}
              onChange={(e) => setFormData(prev => ({ ...prev, notes: e.target.value }))}
              placeholder="Additional notes for the invoice..."
              rows={3}
            />
          </div>

          <div className="flex items-center space-x-2">
            <Checkbox
              id="send-notification"
              checked={formData.sendNotification}
              onCheckedChange={(checked) => setFormData(prev => ({ ...prev, sendNotification: !!checked }))}
            />
            <Label htmlFor="send-notification">
              Send email notification to student
            </Label>
          </div>

          {duplicateWarning && (
            <Alert className="border-yellow-300 bg-yellow-50">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{duplicateWarning}</AlertDescription>
            </Alert>
          )}
        </div>
      ),
      validation: () => !!formData.dueDate && !!formData.description
    },
    {
      id: 'review',
      title: 'Review & Create',
      description: 'Review invoice details before creation',
      content: (
        <div className="space-y-6">
          {/* Student Info */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User className="h-5 w-5" />
                Student Information
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-600">Name</p>
                  <p className="font-medium">
                    {formData.student?.first_name} {formData.student?.last_name}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Student ID</p>
                  <p className="font-medium">{formData.student?.student_id}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Email</p>
                  <p className="font-medium">{formData.student?.email}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Current Balance</p>
                  <p className={`font-medium ${formData.student?.account_balance && formData.student.account_balance < 0 ? 'text-red-600' : 'text-green-600'}`}>
                    ${formData.student?.account_balance?.toFixed(2)}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Invoice Details */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Invoice Details
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-600">Description</p>
                  <p className="font-medium">{formData.description}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Due Date</p>
                  <p className="font-medium">{formData.dueDate}</p>
                </div>
              </div>

              {/* Line Items */}
              <div>
                <p className="text-sm text-gray-600 mb-2">Line Items</p>
                <div className="space-y-2">
                  {formData.lineItems.map((item, index) => (
                    <div key={index} className="flex justify-between items-center p-2 bg-gray-50 rounded">
                      <div>
                        <p className="font-medium">{item.description}</p>
                        <p className="text-sm text-gray-600">
                          {item.quantity} × ${item.unit_price?.toFixed(2)}
                        </p>
                      </div>
                      <p className="font-medium">${((item.quantity || 1) * (item.unit_price || 0)).toFixed(2)}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Discounts */}
              {formData.discounts.length > 0 && (
                <div>
                  <p className="text-sm text-gray-600 mb-2">Discounts</p>
                  <div className="space-y-2">
                    {formData.discounts.map((discount, index) => (
                      <div key={index} className="flex justify-between items-center p-2 bg-green-50 rounded">
                        <div>
                          <p className="font-medium">{discount.name}</p>
                          <p className="text-sm text-gray-600">
                            {discount.type === 'percentage' ? `${discount.value}%` : `$${discount.value?.toFixed(2)}`}
                          </p>
                        </div>
                        <p className="font-medium text-green-600">
                          -${discount.type === 'percentage'
                            ? (subtotal * ((discount.value || 0) / 100)).toFixed(2)
                            : (discount.value || 0).toFixed(2)
                          }
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Final Totals */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <DollarSign className="h-5 w-5" />
                Final Totals
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span>Subtotal:</span>
                  <span>${subtotal.toFixed(2)}</span>
                </div>
                {discountAmount > 0 && (
                  <div className="flex justify-between text-green-600">
                    <span>Total Discounts:</span>
                    <span>-${discountAmount.toFixed(2)}</span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span>Tax:</span>
                  <span>${taxAmount.toFixed(2)}</span>
                </div>
                <Separator />
                <div className="flex justify-between text-xl font-bold">
                  <span>Total Amount:</span>
                  <span>${total.toFixed(2)}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {formData.sendNotification && (
            <Alert>
              <CheckCircle className="h-4 w-4" />
              <AlertDescription>
                An email notification will be sent to {formData.student?.email} after the invoice is created.
              </AlertDescription>
            </Alert>
          )}
        </div>
      ),
      validation: () => true
    }
  ];

  return (
    <Wizard
      steps={steps}
      onComplete={submitInvoice}
      onCancel={onCancel}
      loading={processing}
      completionText="Create Invoice"
    />
  );
};

export default InvoiceWizard;