# Finance App

## Overview

The `finance` app manages comprehensive financial operations including billing, payments, accounting integration, discount management, and financial reporting for the Naga SIS. This business logic layer app provides complete financial lifecycle management with QuickBooks integration, automated billing processes, reconciliation systems, and detailed financial analytics.

## Key Documentation

- [Discount System Guide](docs/DISCOUNT_SYSTEM_GUIDE.md) - Comprehensive guide to the discount rule system
- [Reconciliation Engine Design](docs/RECONCILIATION_ENGINE_DESIGN.md) - Technical design of the reconciliation system
- [Finance Developer Guide](FINANCE_DEVELOPER_GUIDE.md) - Developer reference for working with finance modules
- [Performance Optimization](PERFORMANCE_OPTIMIZATION.md) - Performance tuning and optimization strategies

## Features

### Comprehensive Billing System

- **Student billing management** with automated invoice generation
- **Course-specific pricing** with tiered fee structures
- **Flexible payment plans** with installment options
- **Late fee calculation** with automated penalty assessment

### Discount Management System

- **Rule-based discounts** with configurable discount rules
- **Pattern matching** from payment notes and automatic eligibility
- **Multiple discount types** including Early Bird, Cash Payment, Weekend Classes, etc.
- **Term and program-specific** discount applicability
- **Usage tracking** with analytics and reporting

### Payment Processing & Tracking

- **Multi-method payment support** (cash, bank transfer, mobile payment)
- **Payment verification** with receipt generation
- **Refund management** with approval workflows
- **Outstanding balance tracking** with aging reports

### Accounting Integration

- **QuickBooks synchronization** with chart of accounts mapping
- **General ledger integration** with automated journal entries
- **Financial reporting** with standard accounting reports
- **Audit trail** with complete transaction history

### Specialized Financial Services

- **Senior project fees** with group billing capabilities
- **International student fees** with currency conversion
- **Scholarship accounting** with sponsor billing integration
- **Service fees** for transcripts, documents, and administrative services

## Models

### Core Financial

#### PricingTier

Flexible pricing structure for different student categories.

```python
# Create pricing tiers
domestic_pricing = PricingTier.objects.create(
    name="Domestic Students",
    description="Pricing for Cambodian citizens",
    tier_type=TierType.DOMESTIC,
    base_tuition_per_credit=Decimal("75.00"),
    registration_fee=Decimal("100.00"),
    technology_fee=Decimal("50.00"),
    is_active=True
)

international_pricing = PricingTier.objects.create(
    name="International Students",
    description="Pricing for international students",
    tier_type=TierType.INTERNATIONAL,
    base_tuition_per_credit=Decimal("125.00"),
    registration_fee=Decimal("200.00"),
    technology_fee=Decimal("75.00"),
    is_active=True
)
```

#### CoursePricing

Course-specific pricing overrides and special rates.

```python
# Set special pricing for specific courses
senior_project_pricing = CoursePricing.objects.create(
    course=senior_project_course,
    pricing_tier=domestic_pricing,
    override_price=Decimal("500.00"),
    pricing_type=PricingType.FLAT_FEE,
    effective_date=date(2024, 8, 1),
    reason="Senior project comprehensive fee including advisor meetings"
)

lab_course_pricing = CoursePricing.objects.create(
    course=chemistry_lab,
    pricing_tier=domestic_pricing,
    additional_fee=Decimal("25.00"),
    pricing_type=PricingType.ADDITIONAL_FEE,
    fee_description="Laboratory materials and equipment fee"
)
```

#### Invoice

Student billing with detailed line items and payment tracking.

```python
# Generate student invoice
invoice = Invoice.objects.create(
    student=student_profile,
    term=fall_2024,
    invoice_number="INV-2024-001234",
    issue_date=date.today(),
    due_date=date.today() + timedelta(days=30),
    status=InvoiceStatus.ISSUED,
    billing_address={
        "name": "Sophea Chan",
        "address": "123 Main St, Phnom Penh",
        "country": "Cambodia"
    }
)

# Add line items
InvoiceLineItem.objects.create(
    invoice=invoice,
    description="Tuition - ACCT-101 (3 credits)",
    quantity=3,
    unit_price=Decimal("75.00"),
    total_amount=Decimal("225.00"),
    gl_account=tuition_revenue_account
)

InvoiceLineItem.objects.create(
    invoice=invoice,
    description="Registration Fee - Fall 2024",
    quantity=1,
    unit_price=Decimal("100.00"),
    total_amount=Decimal("100.00"),
    gl_account=registration_fee_account
)
```

#### Payment

Payment processing with comprehensive tracking and verification.

```python
# Record student payment
payment = Payment.objects.create(
    student=student_profile,
    invoice=invoice,
    amount=Decimal("325.00"),
    payment_method=PaymentMethod.BANK_TRANSFER,
    payment_date=date.today(),
    reference_number="BT-2024-789012",
    payment_details={
        "bank_name": "ABA Bank",
        "account_number": "****1234",
        "transaction_id": "TXN789012"
    },
    verified_by=finance_staff,
    verified_at=timezone.now(),
    status=PaymentStatus.VERIFIED
)

# Apply payment to invoice
PaymentApplication.objects.create(
    payment=payment,
    invoice=invoice,
    amount_applied=Decimal("325.00"),
    applied_date=date.today()
)
```

### Accounting Integration

#### GLAccount

Chart of accounts with QuickBooks integration mapping.

```python
# Define general ledger accounts
tuition_revenue = GLAccount.objects.create(
    account_code="4100-01",
    account_name="Tuition Revenue - Undergraduate",
    account_type=AccountType.REVENUE,
    quickbooks_account_id="QB-REV-4100-01",
    is_active=True,
    description="Revenue from undergraduate tuition fees"
)

cash_account = GLAccount.objects.create(
    account_code="1100-01",
    account_name="Cash - Operating Account",
    account_type=AccountType.ASSET,
    quickbooks_account_id="QB-CASH-1100-01",
    is_active=True
)
```

#### JournalEntry

Double-entry bookkeeping with automated transaction recording.

```python
# Create journal entry for payment
journal_entry = JournalEntry.objects.create(
    entry_number="JE-2024-003456",
    entry_date=date.today(),
    description="Student payment - Invoice INV-2024-001234",
    total_debits=Decimal("325.00"),
    total_credits=Decimal("325.00"),
    created_by=finance_staff,
    status=EntryStatus.POSTED
)

# Debit cash account
JournalEntryLine.objects.create(
    journal_entry=journal_entry,
    gl_account=cash_account,
    debit_amount=Decimal("325.00"),
    credit_amount=Decimal("0.00"),
    description="Cash received from student payment"
)

# Credit accounts receivable
JournalEntryLine.objects.create(
    journal_entry=journal_entry,
    gl_account=accounts_receivable,
    debit_amount=Decimal("0.00"),
    credit_amount=Decimal("325.00"),
    description="Accounts receivable payment received"
)
```

### Specialized Financial Services

#### SeniorProjectFee

Group billing for senior project courses.

```python
# Create senior project group fee
senior_project_fee = SeniorProjectFee.objects.create(
    senior_project=capstone_project,
    total_fee=Decimal("2000.00"),
    fee_per_student=Decimal("500.00"),
    billing_term=spring_2024,
    fee_description="Senior project comprehensive fee including advisor, materials, and presentation costs",
    group_billing=True
)

# Assign students to group billing
for student in capstone_project.student_group.all():
    SeniorProjectStudentFee.objects.create(
        senior_project_fee=senior_project_fee,
        student=student,
        fee_amount=Decimal("500.00"),
        payment_status=PaymentStatus.PENDING
    )
```

## Services

### Billing Service

Comprehensive billing management with automated invoice generation.

```python
from apps.finance.services import BillingService

# Generate term billing for student
billing_result = BillingService.generate_term_billing(
    student=student_profile,
    term=fall_2024,
    include_courses=True,
    include_fees=True,
    apply_financial_aid=True
)

# Returns detailed billing information
{
    'invoice': invoice_object,
    'total_amount': Decimal('1250.00'),
    'line_items': [
        {
            'description': 'Tuition - 15 credits',
            'amount': Decimal('1125.00')
        },
        {
            'description': 'Registration Fee',
            'amount': Decimal('100.00')
        },
        {
            'description': 'Technology Fee',
            'amount': Decimal('25.00')
        }
    ],
    'due_date': date(2024, 8, 15),
    'payment_options': ['full_payment', 'installment_plan']
}
```

### Payment Service

Payment processing with verification and application.

```python
from apps.finance.services import PaymentService

# Process student payment
payment_result = PaymentService.process_payment(
    student=student_profile,
    amount=Decimal("500.00"),
    payment_method=PaymentMethod.MOBILE_PAYMENT,
    payment_details={
        'provider': 'ABA PayWay',
        'transaction_id': 'PW789012345',
        'phone_number': '+855 12 345 678'
    },
    apply_to_invoices='oldest_first'
)

if payment_result.success:
    receipt = PaymentService.generate_receipt(payment_result.payment)
    PaymentService.send_payment_confirmation(
        student=student_profile,
        payment=payment_result.payment,
        receipt=receipt
    )
```

### QuickBooks Integration Service

Automated synchronization with QuickBooks accounting system.

```python
from apps.finance.services import QuickBooksService

# Sync financial data with QuickBooks
sync_result = QuickBooksService.sync_daily_transactions(
    sync_date=date.today(),
    include_invoices=True,
    include_payments=True,
    include_journal_entries=True
)

# Generate QuickBooks reports
qb_report = QuickBooksService.generate_ar_aging_report(
    as_of_date=date.today(),
    customer_filter='active_students'
)
```

## Management Commands

### Billing Operations

```bash
# Generate monthly billing for all students
python manage.py generate_monthly_billing --term=fall2024

# Create default pricing tiers
python manage.py create_default_pricing --academic-year=2024

# Generate term invoices
python manage.py generate_term_invoices --term=fall2024 --student-type=all

# Process recurring charges
python manage.py process_recurring_charges --charge-date=2024-07-15
```

### Financial Reporting

```bash
# Generate monthly journal entries
python manage.py generate_monthly_journal_entries --month=july --year=2024

# Create QuickBooks reports
python manage.py generate_quickbooks_reports --report-type=ar_aging

# Generate financial summaries
python manage.py generate_financial_summaries --term=current --format=pdf

# Export data for external audit
python manage.py export_audit_data --year=2024 --format=excel
```

### Payment Processing

```bash
# Import bank statements for reconciliation
python manage.py import_bank_statements --file=bank_statement.csv

# Process pending payments
python manage.py process_pending_payments --verify-all

# Generate payment reminders
python manage.py generate_payment_reminders --days-overdue=30

# Apply late fees
python manage.py apply_late_fees --grace-period=7
```

## API Endpoints

### Student Financial API

```python
# Get student financial summary
GET /api/finance/students/{student_id}/summary/

{
    "student": {
        "id": 123,
        "name": "Sophea Chan",
        "program": "Bachelor of Business Administration"
    },
    "financial_summary": {
        "current_balance": "750.00",
        "total_charges": "1250.00",
        "total_payments": "500.00",
        "overdue_amount": "250.00",
        "next_payment_due": "2024-08-15"
    },
    "recent_transactions": [
        {
            "date": "2024-07-15",
            "type": "payment",
            "amount": "500.00",
            "description": "Mobile payment - ABA PayWay",
            "status": "verified"
        }
    ],
    "outstanding_invoices": [
        {
            "invoice_number": "INV-2024-001234",
            "amount": "750.00",
            "due_date": "2024-08-15",
            "status": "partial_payment"
        }
    ]
}
```

### Payment Processing API

```python
# Submit payment
POST /api/finance/payments/
{
    "student_id": 123,
    "amount": "500.00",
    "payment_method": "bank_transfer",
    "payment_details": {
        "bank_name": "ABA Bank",
        "reference_number": "BT789012345",
        "transaction_date": "2024-07-15"
    },
    "apply_to_invoice": "INV-2024-001234"
}

# Response
{
    "payment_id": 456,
    "status": "pending_verification",
    "receipt_number": "RCP-2024-000789",
    "verification_required": true,
    "estimated_processing_time": "1-2 business days"
}
```

### Financial Reports API

```python
# Get accounts receivable aging
GET /api/finance/reports/ar-aging/?as_of_date=2024-07-15

{
    "report_date": "2024-07-15",
    "total_outstanding": "125000.00",
    "aging_buckets": {
        "current": {
            "amount": "75000.00",
            "percentage": 60.0
        },
        "30_days": {
            "amount": "30000.00",
            "percentage": 24.0
        },
        "60_days": {
            "amount": "15000.00",
            "percentage": 12.0
        },
        "90_plus_days": {
            "amount": "5000.00",
            "percentage": 4.0
        }
    },
    "student_details": [
        {
            "student_name": "Sophea Chan",
            "current": "750.00",
            "30_days": "0.00",
            "60_days": "0.00",
            "90_plus": "0.00",
            "total": "750.00"
        }
    ]
}
```

## Integration Examples

### With Enrollment App

```python
# Generate billing when student enrolls
def create_enrollment_billing(enrollment):
    from apps.finance.services import BillingService

    # Calculate course tuition
    tuition_amount = BillingService.calculate_course_tuition(
        student=enrollment.student,
        course=enrollment.class_header.course,
        term=enrollment.class_header.term
    )

    # Create or update invoice
    invoice = BillingService.add_enrollment_to_invoice(
        student=enrollment.student,
        enrollment=enrollment,
        tuition_amount=tuition_amount
    )

    return invoice
```

### With Scholarships App

```python
# Apply scholarship to student billing
def apply_scholarship_to_billing(student, scholarship, term):
    from apps.scholarships.services import ScholarshipService

    # Calculate scholarship amount
    scholarship_amount = ScholarshipService.calculate_scholarship_amount(
        student=student,
        scholarship=scholarship,
        term=term
    )

    # Apply as credit to student account
    BillingService.apply_scholarship_credit(
        student=student,
        scholarship=scholarship,
        amount=scholarship_amount,
        term=term,
        description=f"Scholarship credit - {scholarship.name}"
    )
```

### With Level Testing App

```python
# Create test fee charge
def create_test_fee_charge(test_application):
    from apps.level_testing.services import TestFeeService

    # Calculate test fee
    fee_amount = TestFeeService.calculate_test_fee(
        test_type=test_application.test_type,
        student_type=test_application.student_type
    )

    # Create service charge
    service_charge = BillingService.create_service_charge(
        student=test_application.potential_student,
        service_type='placement_test',
        amount=fee_amount,
        description=f"Placement test fee - {test_application.test_type}",
        due_date=date.today() + timedelta(days=7)
    )

    return service_charge
```

## Validation & Business Rules

### Financial Validation

```python
def validate_payment_amount(payment, invoice):
    """Validate payment amount against invoice balance."""
    if payment.amount <= 0:
        raise ValidationError("Payment amount must be positive")

    remaining_balance = invoice.get_remaining_balance()
    if payment.amount > remaining_balance:
        raise ValidationError(
            f"Payment amount ${payment.amount} exceeds remaining balance ${remaining_balance}"
        )

def validate_journal_entry_balance(journal_entry):
    """Ensure journal entry debits equal credits."""
    total_debits = journal_entry.lines.aggregate(
        total=Sum('debit_amount')
    )['total'] or Decimal('0.00')

    total_credits = journal_entry.lines.aggregate(
        total=Sum('credit_amount')
    )['total'] or Decimal('0.00')

    if total_debits != total_credits:
        raise ValidationError(
            f"Journal entry out of balance: debits ${total_debits}, credits ${total_credits}"
        )

def validate_pricing_tier_eligibility(student, pricing_tier):
    """Validate student eligibility for pricing tier."""
    if pricing_tier.tier_type == TierType.DOMESTIC:
        if student.person.nationality != "Cambodian":
            raise ValidationError("Student not eligible for domestic pricing")

    if pricing_tier.requires_documentation:
        if not student.has_required_documentation(pricing_tier.required_docs):
            raise ValidationError("Missing required documentation for pricing tier")
```

## Testing

### Test Coverage

```bash
# Run finance app tests
pytest apps/finance/

# Test specific areas
pytest apps/finance/tests/test_billing.py
pytest apps/finance/tests/test_quickbooks_integration.py
pytest apps/finance/tests/test_payment_processing.py
```

### Test Factories

```python
from apps.finance.tests.factories import (
    PricingTierFactory,
    InvoiceFactory,
    PaymentFactory,
    GLAccountFactory
)

# Create test financial data
pricing_tier = PricingTierFactory(
    name="Test Domestic",
    base_tuition_per_credit=Decimal("75.00")
)

invoice = InvoiceFactory(
    student__person__first_name_eng="Test Student",
    total_amount=Decimal("500.00")
)
```

## Performance Optimization

### Financial Calculations

```python
# Efficient student balance calculation
def calculate_student_balance_optimized(student):
    """Optimized student balance calculation."""
    return Invoice.objects.filter(
        student=student
    ).aggregate(
        total_charges=Sum('total_amount'),
        total_payments=Sum(
            'paymentapplication__amount_applied',
            filter=Q(paymentapplication__payment__status=PaymentStatus.VERIFIED)
        )
    )

# Batch billing generation
def generate_batch_billing(students, term, batch_size=50):
    """Efficiently generate billing for multiple students."""
    for student_batch in chunk_list(students, batch_size):
        invoices = []
        for student in student_batch:
            invoice_data = calculate_student_billing(student, term)
            invoices.append(Invoice(**invoice_data))

        # Bulk create invoices
        Invoice.objects.bulk_create(invoices)

        # Generate line items separately for performance
        generate_batch_line_items(invoices)
```

## Configuration

### Settings

```python
# Finance configuration
NAGA_FINANCE_CONFIG = {
    'DEFAULT_PAYMENT_TERMS_DAYS': 30,
    'LATE_FEE_PERCENTAGE': Decimal('1.5'),  # Monthly
    'LATE_FEE_GRACE_PERIOD_DAYS': 7,
    'MAXIMUM_PAYMENT_AMOUNT': Decimal('50000.00'),
    'REQUIRE_PAYMENT_VERIFICATION': True,
    'AUTO_APPLY_PAYMENTS': True
}

# QuickBooks integration
NAGA_QUICKBOOKS_CONFIG = {
    'COMPANY_ID': 'QB_COMPANY_123',
    'SYNC_FREQUENCY_HOURS': 24,
    'AUTO_SYNC_ENABLED': True,
    'SANDBOX_MODE': False,  # Set to True for testing
    'API_VERSION': '3.0'
}
```

## Dependencies

### Internal Dependencies

- `people`: Student profile and contact information
- `enrollment`: Course enrollment for billing calculation
- `curriculum`: Course information for pricing
- `scholarships`: Financial aid and scholarship integration

### External Dependencies

- `python-quickbooks`: QuickBooks API integration
- `stripe`: Payment processing (optional)
- `reportlab`: PDF generation for invoices and receipts
- `celery`: Background task processing for billing

## Architecture Notes

### Design Principles

- **Double-entry accounting**: Proper accounting principles with balanced entries
- **Audit trail**: Complete tracking of all financial transactions
- **Flexible pricing**: Configurable pricing structures for different student types
- **Integration-ready**: External accounting system integration capabilities

### Financial Workflow

1. **Enrollment** → Automatic billing generation
2. **Invoice** → Student notification and payment processing
3. **Payment** → Verification and application to outstanding balances
4. **Accounting** → Journal entry creation and QuickBooks sync
5. **Reporting** → Financial analytics and compliance reports

### Future Enhancements

- **Online payment portal**: Integrated payment gateway
- **Cryptocurrency payments**: Bitcoin and stablecoin support
- **AI-powered collections**: Automated payment reminder optimization
- **Blockchain audit trail**: Immutable financial transaction records
