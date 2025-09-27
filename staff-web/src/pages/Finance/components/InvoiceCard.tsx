/**
 * InvoiceCard Component
 * Reusable invoice display card with comprehensive status indicators and actions
 */

import React, { useState, useCallback } from 'react';
import { Card, CardContent, CardHeader } from '../../../components/ui/card';
import { Button } from '../../../components/ui/button';
import { Badge } from '../../../components/ui/badge';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '../../../components/ui/dropdown-menu';
import { Progress } from '../../../components/ui/progress';
import { Separator } from '../../../components/ui/separator';
import {
  FileText,
  MoreVertical,
  Eye,
  Edit,
  Send,
  Download,
  CreditCard,
  AlertTriangle,
  CheckCircle,
  Clock,
  DollarSign,
  Calendar,
  User,
  Receipt,
  Copy,
  Trash2,
  Phone,
  Mail
} from 'lucide-react';
import { Invoice, InvoiceStatus, PaymentMethod } from '../../../types/finance.types';
import { formatCurrency, formatDate, getStatusColor, getDaysUntilDue, getPaymentMethodIcon } from '../../../utils/financeUtils';
import { useToast } from '../../../hooks/use-toast';

interface InvoiceCardProps {
  invoice: Invoice;
  onView?: (invoiceId: string) => void;
  onEdit?: (invoiceId: string) => void;
  onDelete?: (invoiceId: string) => void;
  onSendReminder?: (invoiceId: string) => void;
  onDownload?: (invoiceId: string) => void;
  onMarkPaid?: (invoiceId: string) => void;
  onDuplicate?: (invoiceId: string) => void;
  showActions?: boolean;
  compact?: boolean;
  selectable?: boolean;
  selected?: boolean;
  onSelect?: (invoiceId: string, selected: boolean) => void;
}

export const InvoiceCard: React.FC<InvoiceCardProps> = ({
  invoice,
  onView,
  onEdit,
  onDelete,
  onSendReminder,
  onDownload,
  onMarkPaid,
  onDuplicate,
  showActions = true,
  compact = false,
  selectable = false,
  selected = false,
  onSelect
}) => {
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();

  // Calculate payment progress
  const totalPaid = invoice.payment_history?.reduce((sum, payment) => sum + payment.amount, 0) || 0;
  const paymentProgress = invoice.total_amount > 0 ? (totalPaid / invoice.total_amount) * 100 : 0;
  const remainingAmount = invoice.total_amount - totalPaid;

  // Get urgency level based on due date and status
  const getUrgencyLevel = useCallback((): 'low' | 'medium' | 'high' | 'critical' => {
    if (invoice.status === InvoiceStatus.PAID) return 'low';

    const daysUntilDue = getDaysUntilDue(invoice.due_date);

    if (daysUntilDue < 0) return 'critical'; // Overdue
    if (daysUntilDue <= 3) return 'high';
    if (daysUntilDue <= 7) return 'medium';
    return 'low';
  }, [invoice.due_date, invoice.status]);

  // Get status badge variant
  const getStatusBadgeVariant = (status: InvoiceStatus) => {
    switch (status) {
      case InvoiceStatus.PAID: return 'default';
      case InvoiceStatus.SENT: return 'secondary';
      case InvoiceStatus.PENDING: return 'outline';
      case InvoiceStatus.OVERDUE: return 'destructive';
      case InvoiceStatus.CANCELLED: return 'secondary';
      case InvoiceStatus.REFUNDED: return 'outline';
      default: return 'outline';
    }
  };

  // Get urgency badge color
  const getUrgencyColor = (urgency: string) => {
    switch (urgency) {
      case 'critical': return 'bg-red-100 text-red-800 border-red-200';
      case 'high': return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'medium': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      default: return 'bg-green-100 text-green-800 border-green-200';
    }
  };

  // Handle action with loading state
  const handleAction = useCallback(async (action: () => Promise<void> | void, loadingMessage: string) => {
    try {
      setIsLoading(true);
      await action();
    } catch (error) {
      toast({
        title: "Action Failed",
        description: `Failed to ${loadingMessage.toLowerCase()}`,
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  }, [toast]);

  // Handle selection
  const handleSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    onSelect?.(invoice.id, e.target.checked);
  }, [invoice.id, onSelect]);

  const urgencyLevel = getUrgencyLevel();
  const daysUntilDue = getDaysUntilDue(invoice.due_date);

  if (compact) {
    return (
      <Card className={`cursor-pointer hover:shadow-md transition-shadow ${selected ? 'ring-2 ring-blue-500' : ''}`}>
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {selectable && (
                <input
                  type="checkbox"
                  checked={selected}
                  onChange={handleSelect}
                  className="rounded border-gray-300"
                />
              )}

              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4 text-gray-500" />
                <div>
                  <p className="font-medium text-sm">{invoice.invoice_number}</p>
                  <p className="text-xs text-gray-600">{invoice.student_name}</p>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Badge variant={getStatusBadgeVariant(invoice.status)} className="text-xs">
                {invoice.status.replace('_', ' ').toUpperCase()}
              </Badge>
              <span className="font-medium text-sm">{formatCurrency(invoice.total_amount)}</span>

              {showActions && (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
                      <MoreVertical className="h-3 w-3" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem onClick={() => onView?.(invoice.id)}>
                      <Eye className="h-4 w-4 mr-2" />
                      View
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => onEdit?.(invoice.id)}>
                      <Edit className="h-4 w-4 mr-2" />
                      Edit
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={`hover:shadow-lg transition-shadow ${selected ? 'ring-2 ring-blue-500' : ''}`}>
      <CardHeader className="pb-4">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-3">
            {selectable && (
              <input
                type="checkbox"
                checked={selected}
                onChange={handleSelect}
                className="mt-1 rounded border-gray-300"
              />
            )}

            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <FileText className="h-5 w-5 text-blue-500" />
                <h3 className="font-semibold text-lg">{invoice.invoice_number}</h3>
                <Badge variant={getStatusBadgeVariant(invoice.status)}>
                  {invoice.status.replace('_', ' ').toUpperCase()}
                </Badge>

                {urgencyLevel !== 'low' && (
                  <Badge className={getUrgencyColor(urgencyLevel)}>
                    {urgencyLevel === 'critical' ? 'OVERDUE' : urgencyLevel.toUpperCase()}
                  </Badge>
                )}
              </div>

              <div className="flex items-center gap-4 text-sm text-gray-600">
                <div className="flex items-center gap-1">
                  <User className="h-4 w-4" />
                  <span>{invoice.student_name}</span>
                </div>
                <div className="flex items-center gap-1">
                  <Calendar className="h-4 w-4" />
                  <span>Due: {formatDate(invoice.due_date)}</span>
                  {daysUntilDue < 0 && (
                    <span className="text-red-600 font-medium">
                      ({Math.abs(daysUntilDue)} days overdue)
                    </span>
                  )}
                  {daysUntilDue > 0 && daysUntilDue <= 7 && (
                    <span className="text-orange-600 font-medium">
                      ({daysUntilDue} days left)
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>

          {showActions && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" disabled={isLoading}>
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => onView?.(invoice.id)}>
                  <Eye className="h-4 w-4 mr-2" />
                  View Details
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => onEdit?.(invoice.id)}>
                  <Edit className="h-4 w-4 mr-2" />
                  Edit Invoice
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => onDownload?.(invoice.id)}>
                  <Download className="h-4 w-4 mr-2" />
                  Download PDF
                </DropdownMenuItem>
                <Separator />
                <DropdownMenuItem onClick={() => onSendReminder?.(invoice.id)}>
                  <Send className="h-4 w-4 mr-2" />
                  Send Reminder
                </DropdownMenuItem>
                {invoice.status !== InvoiceStatus.PAID && (
                  <DropdownMenuItem onClick={() => onMarkPaid?.(invoice.id)}>
                    <CheckCircle className="h-4 w-4 mr-2" />
                    Mark as Paid
                  </DropdownMenuItem>
                )}
                <DropdownMenuItem onClick={() => onDuplicate?.(invoice.id)}>
                  <Copy className="h-4 w-4 mr-2" />
                  Duplicate
                </DropdownMenuItem>
                <Separator />
                <DropdownMenuItem
                  onClick={() => onDelete?.(invoice.id)}
                  className="text-red-600 focus:text-red-600"
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Financial Summary */}
        <div className="grid grid-cols-3 gap-4">
          <div className="text-center">
            <p className="text-sm text-gray-600">Total Amount</p>
            <p className="text-lg font-bold">{formatCurrency(invoice.total_amount)}</p>
          </div>
          <div className="text-center">
            <p className="text-sm text-gray-600">Paid</p>
            <p className="text-lg font-bold text-green-600">{formatCurrency(totalPaid)}</p>
          </div>
          <div className="text-center">
            <p className="text-sm text-gray-600">Remaining</p>
            <p className="text-lg font-bold text-orange-600">{formatCurrency(remainingAmount)}</p>
          </div>
        </div>

        {/* Payment Progress */}
        {paymentProgress > 0 && (
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>Payment Progress</span>
              <span>{paymentProgress.toFixed(1)}%</span>
            </div>
            <Progress value={paymentProgress} className="h-2" />
          </div>
        )}

        {/* Description */}
        {invoice.description && (
          <div>
            <p className="text-sm text-gray-600 line-clamp-2">{invoice.description}</p>
          </div>
        )}

        {/* Payment Plans */}
        {invoice.payment_plans && invoice.payment_plans.length > 0 && (
          <div className="flex items-center gap-2 text-sm">
            <Receipt className="h-4 w-4 text-blue-500" />
            <span className="text-gray-600">
              {invoice.payment_plans.length} payment plan{invoice.payment_plans.length > 1 ? 's' : ''} active
            </span>
          </div>
        )}

        {/* Recent Payments */}
        {invoice.payment_history && invoice.payment_history.length > 0 && (
          <div className="space-y-2">
            <p className="text-sm font-medium">Recent Payments</p>
            <div className="space-y-1">
              {invoice.payment_history.slice(0, 2).map((payment, index) => (
                <div key={payment.id} className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    {getPaymentMethodIcon(payment.payment_method)}
                    <span className="text-gray-600">
                      {formatDate(payment.processed_date)}
                    </span>
                  </div>
                  <span className="font-medium text-green-600">
                    {formatCurrency(payment.amount)}
                  </span>
                </div>
              ))}
              {invoice.payment_history.length > 2 && (
                <p className="text-xs text-gray-500">
                  +{invoice.payment_history.length - 2} more payments
                </p>
              )}
            </div>
          </div>
        )}

        {/* Quick Actions */}
        <div className="flex gap-2 pt-2">
          {invoice.status !== InvoiceStatus.PAID && (
            <Button
              size="sm"
              onClick={() => handleAction(() => onMarkPaid?.(invoice.id), "mark as paid")}
              disabled={isLoading}
              className="flex-1"
            >
              <CreditCard className="h-4 w-4 mr-1" />
              Record Payment
            </Button>
          )}

          <Button
            size="sm"
            variant="outline"
            onClick={() => onView?.(invoice.id)}
            className="flex-1"
          >
            <Eye className="h-4 w-4 mr-1" />
            View Details
          </Button>

          {(invoice.status === InvoiceStatus.SENT || invoice.status === InvoiceStatus.OVERDUE) && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => handleAction(() => onSendReminder?.(invoice.id), "send reminder")}
              disabled={isLoading}
            >
              <Send className="h-4 w-4 mr-1" />
              Remind
            </Button>
          )}
        </div>

        {/* Status Indicators */}
        <div className="flex items-center justify-between text-xs text-gray-500 pt-2 border-t">
          <span>Created: {formatDate(invoice.created_date)}</span>
          {invoice.status === InvoiceStatus.PAID && invoice.paid_date && (
            <span>Paid: {formatDate(invoice.paid_date)}</span>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default InvoiceCard;