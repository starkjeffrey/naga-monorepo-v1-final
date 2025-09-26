/**
 * Invoice Data Grid Component
 * Advanced invoice management with search, filters, and bulk operations
 */

import React, { useState, useCallback, useEffect } from 'react';
import { EnhancedDataGrid, DataGridColumn, DataGridAction, DataGridFilters } from '../../../components/patterns';
import { Button } from '../../../components/ui/button';
import { Badge } from '../../../components/ui/badge';
import { Input } from '../../../components/ui/input';
import { Label } from '../../../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../components/ui/select';
import { Card, CardContent } from '../../../components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../../../components/ui/dialog';
import { Popover, PopoverContent, PopoverTrigger } from '../../../components/ui/popover';
import { Calendar } from '../../../components/ui/calendar';
import { Checkbox } from '../../../components/ui/checkbox';
import { useToast } from '../../../hooks/use-toast';
import {
  Search, Filter, Download, Mail, FileText, DollarSign, Calendar as CalendarIcon,
  AlertCircle, CheckCircle, Clock, XCircle, Send, Printer, MoreHorizontal, Eye
} from 'lucide-react';
import { financeService } from '../../../services/financeService';
import { Invoice, InvoiceStatus, InvoiceFilters } from '../../../types/finance.types';
import { format } from 'date-fns';
import InvoiceDetail from './InvoiceDetail';
import InvoiceWizard from './InvoiceCreate';

interface InvoiceListProps {
  studentId?: string; // Optional filter for specific student
}

export const InvoiceList: React.FC<InvoiceListProps> = ({ studentId }) => {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedInvoices, setSelectedInvoices] = useState<string[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<InvoiceStatus | 'all'>('all');
  const [dateRange, setDateRange] = useState<{ start?: Date; end?: Date }>({});
  const [amountRange, setAmountRange] = useState<{ min?: number; max?: number }>({});
  const [showOverdueOnly, setShowOverdueOnly] = useState(false);
  const [showPaymentPlanOnly, setShowPaymentPlanOnly] = useState(false);
  const [selectedInvoiceId, setSelectedInvoiceId] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);

  const { toast } = useToast();

  // Mock data for demonstration
  const mockInvoices: Invoice[] = [
    {
      id: '1',
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
      line_items: [],
      payment_plans: [],
      discounts: [],
      attachments: [],
      payment_history: []
    },
    {
      id: '2',
      invoice_number: 'INV-2024-002',
      student_id: '2',
      student_name: 'Jane Smith',
      amount: 850.00,
      tax_amount: 68.00,
      total_amount: 918.00,
      status: InvoiceStatus.PAID,
      due_date: '2024-09-30',
      created_date: '2024-09-01',
      paid_date: '2024-09-25',
      description: 'Books and Materials',
      line_items: [],
      payment_plans: [],
      discounts: [],
      attachments: [],
      payment_history: []
    },
    {
      id: '3',
      invoice_number: 'INV-2024-003',
      student_id: '3',
      student_name: 'Michael Johnson',
      amount: 2200.00,
      tax_amount: 176.00,
      total_amount: 2376.00,
      status: InvoiceStatus.OVERDUE,
      due_date: '2024-09-15',
      created_date: '2024-08-15',
      description: 'Fall 2024 Tuition - Late Registration',
      line_items: [],
      payment_plans: [],
      discounts: [],
      attachments: [],
      payment_history: []
    }
  ];

  // Load invoices
  const loadInvoices = useCallback(async (page = 1) => {
    setLoading(true);
    try {
      const filters: InvoiceFilters = {
        ...(statusFilter !== 'all' && { status: [statusFilter as InvoiceStatus] }),
        ...(studentId && { student_ids: [studentId] }),
        ...(dateRange.start && dateRange.end && {
          date_range: {
            start: format(dateRange.start, 'yyyy-MM-dd'),
            end: format(dateRange.end, 'yyyy-MM-dd')
          }
        }),
        ...(amountRange.min !== undefined && amountRange.max !== undefined && {
          amount_range: amountRange
        }),
        overdue_only: showOverdueOnly,
        payment_plan_only: showPaymentPlanOnly
      };

      // For demo, use mock data with client-side filtering
      let filteredInvoices = mockInvoices;

      if (searchTerm) {
        filteredInvoices = filteredInvoices.filter(invoice =>
          invoice.invoice_number.toLowerCase().includes(searchTerm.toLowerCase()) ||
          invoice.student_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
          invoice.description.toLowerCase().includes(searchTerm.toLowerCase())
        );
      }

      if (statusFilter !== 'all') {
        filteredInvoices = filteredInvoices.filter(invoice => invoice.status === statusFilter);
      }

      if (showOverdueOnly) {
        filteredInvoices = filteredInvoices.filter(invoice => invoice.status === InvoiceStatus.OVERDUE);
      }

      setInvoices(filteredInvoices);
      setTotalCount(filteredInvoices.length);
      setCurrentPage(page);
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to load invoices",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  }, [statusFilter, studentId, dateRange, amountRange, showOverdueOnly, showPaymentPlanOnly, searchTerm, toast]);

  // Initial load
  useEffect(() => {
    loadInvoices();
  }, [loadInvoices]);

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

  // Columns configuration
  const columns: DataGridColumn<Invoice>[] = [
    {
      key: 'invoice_number',
      title: 'Invoice #',
      sortable: true,
      render: (invoice) => (
        <div className="font-medium">
          {invoice.invoice_number}
        </div>
      )
    },
    {
      key: 'student_name',
      title: 'Student',
      sortable: true,
      render: (invoice) => (
        <div>
          <div className="font-medium">{invoice.student_name}</div>
          <div className="text-sm text-gray-500">{invoice.student_id}</div>
        </div>
      )
    },
    {
      key: 'description',
      title: 'Description',
      render: (invoice) => (
        <div className="max-w-xs truncate">
          {invoice.description}
        </div>
      )
    },
    {
      key: 'total_amount',
      title: 'Amount',
      sortable: true,
      render: (invoice) => (
        <div className="text-right">
          <div className="font-medium">${invoice.total_amount.toFixed(2)}</div>
          {invoice.tax_amount > 0 && (
            <div className="text-sm text-gray-500">
              Tax: ${invoice.tax_amount.toFixed(2)}
            </div>
          )}
        </div>
      )
    },
    {
      key: 'status',
      title: 'Status',
      sortable: true,
      render: (invoice) => {
        const Icon = getStatusIcon(invoice.status);
        return (
          <Badge variant={getStatusVariant(invoice.status)} className="flex items-center gap-1">
            <Icon className="h-3 w-3" />
            {invoice.status.charAt(0).toUpperCase() + invoice.status.slice(1)}
          </Badge>
        );
      }
    },
    {
      key: 'due_date',
      title: 'Due Date',
      sortable: true,
      render: (invoice) => {
        const isOverdue = invoice.status === InvoiceStatus.OVERDUE;
        return (
          <div className={isOverdue ? 'text-red-600 font-medium' : ''}>
            {format(new Date(invoice.due_date), 'MMM dd, yyyy')}
          </div>
        );
      }
    },
    {
      key: 'created_date',
      title: 'Created',
      sortable: true,
      render: (invoice) => format(new Date(invoice.created_date), 'MMM dd, yyyy')
    }
  ];

  // Row actions
  const rowActions: DataGridAction<Invoice>[] = [
    {
      label: 'View Details',
      icon: Eye,
      onClick: (invoice) => setSelectedInvoiceId(invoice.id)
    },
    {
      label: 'Send Reminder',
      icon: Send,
      onClick: async (invoice) => {
        try {
          await financeService.sendInvoiceReminder(invoice.id);
          toast({
            title: "Reminder Sent",
            description: `Reminder sent for ${invoice.invoice_number}`,
          });
        } catch (error) {
          toast({
            title: "Error",
            description: "Failed to send reminder",
            variant: "destructive"
          });
        }
      },
      disabled: (invoice) => invoice.status === InvoiceStatus.PAID || invoice.status === InvoiceStatus.CANCELLED
    },
    {
      label: 'Print',
      icon: Printer,
      onClick: (invoice) => {
        // Mock print functionality
        toast({
          title: "Printing",
          description: `Printing ${invoice.invoice_number}`,
        });
      }
    }
  ];

  // Bulk actions
  const bulkActions = [
    {
      label: 'Send Reminders',
      icon: Mail,
      onClick: async () => {
        try {
          await financeService.bulkInvoiceOperations(selectedInvoices, 'send_reminder');
          toast({
            title: "Reminders Sent",
            description: `Sent reminders for ${selectedInvoices.length} invoices`,
          });
          setSelectedInvoices([]);
        } catch (error) {
          toast({
            title: "Error",
            description: "Failed to send reminders",
            variant: "destructive"
          });
        }
      }
    },
    {
      label: 'Export Selected',
      icon: Download,
      onClick: async () => {
        try {
          const blob = await financeService.exportData('invoices', { invoice_ids: selectedInvoices }, 'pdf');
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `invoices-${format(new Date(), 'yyyy-MM-dd')}.pdf`;
          a.click();
          URL.revokeObjectURL(url);
        } catch (error) {
          toast({
            title: "Export Failed",
            description: "Failed to export invoices",
            variant: "destructive"
          });
        }
      }
    },
    {
      label: 'Generate Statements',
      icon: FileText,
      onClick: async () => {
        try {
          await financeService.bulkInvoiceOperations(selectedInvoices, 'generate_statement');
          toast({
            title: "Statements Generated",
            description: `Generated statements for ${selectedInvoices.length} invoices`,
          });
          setSelectedInvoices([]);
        } catch (error) {
          toast({
            title: "Error",
            description: "Failed to generate statements",
            variant: "destructive"
          });
        }
      }
    }
  ];

  // Filters configuration
  const filters: DataGridFilters = {
    searchPlaceholder: "Search invoices, students, or descriptions...",
    searchValue: searchTerm,
    onSearchChange: setSearchTerm,
    customFilters: (
      <div className="flex flex-wrap items-center gap-4">
        {/* Status Filter */}
        <div className="flex items-center gap-2">
          <Label htmlFor="status-filter">Status:</Label>
          <Select value={statusFilter} onValueChange={(value) => setStatusFilter(value as InvoiceStatus | 'all')}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value={InvoiceStatus.PENDING}>Pending</SelectItem>
              <SelectItem value={InvoiceStatus.PAID}>Paid</SelectItem>
              <SelectItem value={InvoiceStatus.OVERDUE}>Overdue</SelectItem>
              <SelectItem value={InvoiceStatus.CANCELLED}>Cancelled</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Date Range Filter */}
        <Popover>
          <PopoverTrigger asChild>
            <Button variant="outline" className="flex items-center gap-2">
              <CalendarIcon className="h-4 w-4" />
              Date Range
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-auto p-0" align="start">
            <Calendar
              mode="range"
              selected={{ from: dateRange.start, to: dateRange.end }}
              onSelect={(range) => setDateRange({ start: range?.from, end: range?.to })}
              numberOfMonths={2}
            />
          </PopoverContent>
        </Popover>

        {/* Amount Range Filter */}
        <div className="flex items-center gap-2">
          <Label>Amount:</Label>
          <Input
            type="number"
            placeholder="Min"
            value={amountRange.min || ''}
            onChange={(e) => setAmountRange(prev => ({ ...prev, min: parseFloat(e.target.value) || undefined }))}
            className="w-20"
          />
          <span>-</span>
          <Input
            type="number"
            placeholder="Max"
            value={amountRange.max || ''}
            onChange={(e) => setAmountRange(prev => ({ ...prev, max: parseFloat(e.target.value) || undefined }))}
            className="w-20"
          />
        </div>

        {/* Quick Filters */}
        <div className="flex items-center gap-4">
          <div className="flex items-center space-x-2">
            <Checkbox
              id="overdue-only"
              checked={showOverdueOnly}
              onCheckedChange={setShowOverdueOnly}
            />
            <Label htmlFor="overdue-only">Overdue Only</Label>
          </div>
          <div className="flex items-center space-x-2">
            <Checkbox
              id="payment-plan-only"
              checked={showPaymentPlanOnly}
              onCheckedChange={setShowPaymentPlanOnly}
            />
            <Label htmlFor="payment-plan-only">Payment Plans</Label>
          </div>
        </div>
      </div>
    )
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Invoice Management</h1>
          <p className="text-gray-600">Manage student invoices and billing</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => loadInvoices()}>
            <Search className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          <Dialog open={showCreateModal} onOpenChange={setShowCreateModal}>
            <DialogTrigger asChild>
              <Button>
                <DollarSign className="h-4 w-4 mr-2" />
                Create Invoice
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>Create New Invoice</DialogTitle>
              </DialogHeader>
              <InvoiceWizard
                onComplete={(invoice) => {
                  setShowCreateModal(false);
                  loadInvoices();
                  toast({
                    title: "Invoice Created",
                    description: `Invoice ${invoice.invoice_number} created successfully`,
                  });
                }}
                onCancel={() => setShowCreateModal(false)}
              />
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Total Invoices</p>
                <p className="text-2xl font-bold">{totalCount}</p>
              </div>
              <FileText className="h-8 w-8 text-blue-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Outstanding</p>
                <p className="text-2xl font-bold text-orange-600">
                  {invoices.filter(i => i.status === InvoiceStatus.PENDING).length}
                </p>
              </div>
              <Clock className="h-8 w-8 text-orange-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Overdue</p>
                <p className="text-2xl font-bold text-red-600">
                  {invoices.filter(i => i.status === InvoiceStatus.OVERDUE).length}
                </p>
              </div>
              <AlertCircle className="h-8 w-8 text-red-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Total Amount</p>
                <p className="text-2xl font-bold">
                  ${invoices.reduce((sum, i) => sum + i.total_amount, 0).toFixed(2)}
                </p>
              </div>
              <DollarSign className="h-8 w-8 text-green-500" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Data Grid */}
      <EnhancedDataGrid
        data={invoices}
        columns={columns}
        loading={loading}
        selectable
        selectedIds={selectedInvoices}
        onSelectionChange={setSelectedInvoices}
        rowActions={rowActions}
        bulkActions={bulkActions}
        filters={filters}
        pagination={{
          total: totalCount,
          pageSize: 50,
          currentPage,
          onPageChange: setCurrentPage
        }}
        emptyState={{
          title: "No invoices found",
          description: "No invoices match your current filters",
          action: (
            <Button onClick={() => setShowCreateModal(true)}>
              <DollarSign className="h-4 w-4 mr-2" />
              Create First Invoice
            </Button>
          )
        }}
      />

      {/* Invoice Detail Modal */}
      {selectedInvoiceId && (
        <InvoiceDetail
          invoiceId={selectedInvoiceId}
          isOpen={!!selectedInvoiceId}
          onClose={() => setSelectedInvoiceId(null)}
          onUpdate={() => loadInvoices()}
        />
      )}
    </div>
  );
};

export default InvoiceList;