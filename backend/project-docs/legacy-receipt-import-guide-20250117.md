# Legacy Receipt Import Guide - Comprehensive Mapping Strategy

**Generated:** January 17, 2025  
**Author:** Claude (Finance System Analysis)  
**Purpose:** Guide for importing legacy_receipt_header data into new SIS finance structure

---

## 🗂️ **Conceptual Mapping Overview**

**Legacy Receipt → New SIS Structure:**

- `legacy_receipt_header` → `Invoice` (header) + `Payment` (if paid) + `FinancialTransaction` (audit)
- `legacy_receipt_lines` → `InvoiceLineItem` (detailed charges)

**Key Insight:** Legacy receipts represent COMPLETED transactions, while the new SIS properly separates invoicing from payment tracking.

---

## 📋 **Header Level Mapping (`legacy_receipt_header` → `Invoice`)**

### **Required Fields for Invoice Creation:**

```python
# Core Invoice fields to populate
invoice_number      ← receipt_number (with "LGY-" prefix)
student            ← lookup StudentProfile by legacy student_id
term               ← lookup Term by legacy term/semester
issue_date         ← receipt_date or creation_date
due_date           ← due_date or calculated (issue_date + 30 days)
subtotal           ← sum of positive line items
tax_amount         ← tax portion (usually 0.00)
total_amount       ← total from header
paid_amount        ← payment_amount from header
currency           ← "USD" (or from legacy if multi-currency)
status             ← PAID if fully paid, PARTIAL if partially paid
notes              ← legacy notes/comments
sent_date          ← receipt_date (since it was "sent" as receipt)
```

---

## 📄 **Line Item Mapping (`legacy_receipt_lines` → `InvoiceLineItem`)**

### **Charge Type Classifications:**

#### **1. TUITION CHARGES**

```python
line_item_type = InvoiceLineItem.LineItemType.COURSE
enrollment        ← link to ClassHeaderEnrollment record
description       ← "Tuition: {course_code} - {course_title}"
unit_price        ← course price from pricing tier
quantity          ← 1
line_total        ← unit_price * quantity
```

#### **2. LATE FEES**

```python
line_item_type = InvoiceLineItem.LineItemType.FEE
fee_pricing       ← link to FeePricing with fee_type="LATE"
description       ← "Late Payment Fee"
unit_price        ← late fee amount
quantity          ← 1
line_total        ← unit_price * quantity
```

#### **3. SCHOLARSHIPS/FINANCIAL AID**

```python
line_item_type = InvoiceLineItem.LineItemType.SCHOLARSHIP
description       ← "Scholarship: {scholarship_name}"
unit_price        ← scholarship amount (negative for discounts)
quantity          ← 1
line_total        ← unit_price * quantity (negative)
```

#### **4. LIBRARY FEES**

```python
line_item_type = InvoiceLineItem.LineItemType.FEE
fee_pricing       ← link to FeePricing with fee_type="LIBRARY"
description       ← "Library Fee"
unit_price        ← fee amount
quantity          ← 1
```

#### **5. REGISTRATION FEES**

```python
line_item_type = InvoiceLineItem.LineItemType.FEE
fee_pricing       ← link to FeePricing with fee_type="REGISTRATION"
description       ← "Registration Fee"
unit_price        ← registration amount
quantity          ← 1
```

#### **6. TECHNOLOGY FEES**

```python
line_item_type = InvoiceLineItem.LineItemType.FEE
fee_pricing       ← link to FeePricing with fee_type="TECHNOLOGY"
description       ← "Technology Fee"
unit_price        ← tech fee amount
quantity          ← 1
```

#### **7. PARKING FEES**

```python
line_item_type = InvoiceLineItem.LineItemType.FEE
fee_pricing       ← link to FeePricing with fee_type="PARKING"
description       ← "Parking Fee"
unit_price        ← parking amount
quantity          ← 1
```

#### **8. PAYMENT ADJUSTMENTS/CORRECTIONS**

```python
line_item_type = InvoiceLineItem.LineItemType.ADJUSTMENT
description       ← "Payment Adjustment - {reason}"
unit_price        ← adjustment amount (positive or negative)
quantity          ← 1
```

---

## 🔄 **Payment & Transaction Tracking**

Since receipts represent **completed payments**, you'll also need to create:

### **Payment Records:**

```python
payment_reference  ← generate new reference
invoice           ← link to created Invoice
amount            ← payment amount from receipt
currency          ← "USD"
payment_method    ← from legacy payment method
payment_date      ← receipt date
status            ← Payment.PaymentStatus.COMPLETED
payer_name        ← student name or payer info
external_reference ← legacy receipt number
processed_by      ← system user for import
```

### **Financial Transaction Records:**

```python
transaction_type  ← FinancialTransaction.TransactionType.PAYMENT
student          ← StudentProfile reference
amount           ← payment amount
currency         ← "USD"
description      ← "Legacy payment import"
invoice          ← Invoice reference
payment          ← Payment reference
processed_by     ← system user for import
```

---

## 📊 **Required Legacy Fields**

### **From `legacy_receipt_header`:**

- `receipt_number/id` (for invoice_number generation)
- `student_id` (to map to StudentProfile)
- `term_id/semester` (to map to Term)
- `receipt_date` (for issue_date)
- `due_date` (if available)
- `total_amount`
- `paid_amount`
- `payment_date`
- `payment_method`
- `status`
- `notes/comments`

### **From `legacy_receipt_lines`:**

- `charge_type/charge_code` (to determine line_item_type)
- `course_id` (for tuition charges)
- `fee_code` (for fee charges)
- `description`
- `unit_price`
- `quantity`
- `line_total`
- `discount_amount` (if applicable)

---

## ⚠️ **Data Integrity Considerations**

### **Pre-Import Validation:**

- ✅ Verify student exists: `legacy_student_id → StudentProfile`
- ✅ Verify term exists: `legacy_term → Term`
- ✅ Validate charge types can be mapped to known fee types
- ✅ Check for duplicate receipt numbers
- ✅ Ensure all course references are valid

### **Import Process Validation:**

- ✅ Total of line items must equal header total
- ✅ Paid amount cannot exceed total amount
- ✅ All required references must exist
- ✅ Handle orphaned records gracefully

---

## 🎯 **Import Process Flow**

### **1. Data Mapping & Validation**

- Map legacy student IDs to StudentProfile records
- Map legacy terms to Term records
- Validate all charge types and fee codes
- Check for data completeness

### **2. Invoice Creation** (from receipt header)

- Create Invoice record with mapped header data
- Generate appropriate invoice number
- Set correct status based on payment status

### **3. Line Item Creation** (from receipt lines)

- Create InvoiceLineItem records for each charge
- Map charge types to appropriate line_item_types
- Link to enrollment records for course charges
- Link to fee_pricing records for fee charges

### **4. Payment Record Creation** (since receipts = payments)

- Create Payment records for completed payments
- Link payments to their corresponding invoices
- Set appropriate payment status and dates

### **5. Financial Transaction Audit Trail**

- Create FinancialTransaction records for audit purposes
- Maintain complete transaction history
- Mark records as legacy imports

### **6. Status Updates & Reconciliation**

- Update invoice payment status
- Reconcile totals and balances
- Generate import summary reports

---

## 🛠️ **Technical Implementation Notes**

### **Service Layer Usage:**

- Use `InvoiceService.create_invoice()` with legacy data
- Use `PaymentService.record_payment()` for payment records
- Use `FinancialTransactionService.record_transaction()` for audit trail

### **Error Handling:**

- Implement comprehensive error handling using existing `FinancialError`
- Use transaction rollback for failed imports
- Log all import errors for review

### **Performance Considerations:**

- Use bulk operations where possible
- Implement batch processing for large datasets
- Monitor memory usage during import

---

## 📈 **Expected Outcomes**

After successful import, you'll have:

- ✅ Complete invoice records with detailed line items
- ✅ Proper payment tracking and reconciliation
- ✅ Full audit trail for all financial transactions
- ✅ Normalized data structure for future operations
- ✅ Seamless integration with existing SIS finance workflows

---

## 🔍 **Post-Import Validation**

### **Data Integrity Checks:**

- Verify invoice totals match payment amounts
- Confirm all line items sum to invoice subtotals
- Check for any orphaned records
- Validate foreign key relationships

### **Business Logic Validation:**

- Ensure student balances are correct
- Verify term-based charge calculations
- Check scholarship and discount applications
- Confirm payment method distributions

---

_This guide provides a comprehensive framework for importing legacy receipt data into the new SIS finance structure while maintaining data integrity and audit trails._
