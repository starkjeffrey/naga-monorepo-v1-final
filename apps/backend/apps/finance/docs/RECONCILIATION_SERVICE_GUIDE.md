# Finance App Reconciliation Service Guide

## Overview

The Finance app's reconciliation services provide comprehensive tools for matching payments to invoices, verifying financial transactions, and ensuring data integrity across the Student Information System. The reconciliation system handles both automated matching and manual review workflows.

## Table of Contents

1. [Core Reconciliation Services](#core-reconciliation-services)
2. [SIS Integration Test Service](#sis-integration-test-service)
3. [Reconciliation Models](#reconciliation-models)
4. [Reconciliation Workflow](#reconciliation-workflow)
5. [Usage Examples](#usage-examples)
6. [Best Practices](#best-practices)

## Core Reconciliation Services

### Comprehensive Reconciliation Service

Located at `apps.finance.services.comprehensive_reconciliation_service.py`, this service handles:
- CSV payment data processing
- Automatic discount verification
- Scholarship validation
- Exception handling and error categorization

Key features:
- Pattern matching for discount identification
- Integration with DiscountRule table
- Automated confidence scoring
- Detailed error tracking

### SIS Integration Test Service

The `SISIntegrationTestService` (in `apps.finance.management.commands.run_sis_integration_test.py`) provides comprehensive validation by:

1. **Using SeparatedPricingService** to calculate actual course prices
2. **Looking up scholarships** in the Scholarship table to verify percentages
3. **Using DiscountRule table** to match Early Bird and other discounts from notes
4. **Comparing SIS calculated values** to clerk's notes and flagging differences
5. **Creating detailed error tracking** for all discrepancies

This service acts as a comprehensive integration test comparing the entire SIS against historical payment data and flagging any clerk errors or system discrepancies.

## Reconciliation Models

### ReconciliationBatch

Tracks batch processing of reconciliation runs:

```python
class ReconciliationBatch(TimestampedModel, UserTrackingModel):
    batch_id = models.CharField(max_length=100, unique=True)
    batch_type = models.CharField(max_length=20, choices=BatchType.choices)
    status = models.CharField(max_length=20, choices=BatchStatus.choices)
    
    # Statistics
    total_payments = models.PositiveIntegerField(default=0)
    processed_payments = models.PositiveIntegerField(default=0)
    successful_matches = models.PositiveIntegerField(default=0)
    failed_matches = models.PositiveIntegerField(default=0)
    
    # Results
    results_summary = models.JSONField(default=dict)
    error_log = models.TextField(blank=True)
```

### ReconciliationStatus

Tracks individual payment reconciliation status:

```python
class ReconciliationStatus(TimestampedModel, UserTrackingModel):
    payment = models.ForeignKey('finance.Payment', on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=Status.choices)
    confidence_level = models.CharField(max_length=10, choices=ConfidenceLevel.choices)
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2)
    
    # Variance tracking
    variance_amount = models.DecimalField(max_digits=10, decimal_places=2)
    pricing_method_applied = models.CharField(max_length=50)
    
    # Error details
    error_category = models.CharField(max_length=50, blank=True)
    error_details = models.JSONField(default=dict)
```

## Reconciliation Workflow

### 1. Data Import and Parsing

```python
# Parse CSV payment data
csv_data = CSVPaymentData(
    student_id=row['name'],
    term_code=row['TermID'],
    amount=Decimal(row['Amount']),
    net_amount=Decimal(row['NetAmount']),
    net_discount=Decimal(row['NetDiscount']),
    notes=row['Notes'],
    payment_type=row['PmtType'],
    payment_date=row['PmtDate'],
    receipt_number=row['ReceiptNo']
)
```

### 2. SIS Calculation

```python
# Calculate pricing using actual SIS pricing service
sis_calculation = service._calculate_sis_pricing(
    student=student,
    term=term,
    enrollments=enrollments
)

# Returns SISCalculation object with:
# - base_price: Total tuition before discounts
# - scholarship_discount: Amount from scholarships
# - discount_amount: Other discounts (Early Bird, etc.)
# - expected_net_amount: Final calculated amount
```

### 3. Clerk Entry Parsing

```python
# Parse clerk's notes to extract recorded values
clerk_entry = service._parse_clerk_notes(csv_data)

# Extracts:
# - recorded_discount_percentage
# - recorded_discount_amount  
# - scholarship_mentioned
# - discount_type_mentioned
```

### 4. Discrepancy Identification

The service identifies several types of discrepancies:

- **MISSING_SCHOLARSHIP_RECORD**: Clerk mentioned scholarship but none found in SIS
- **UNREPORTED_SCHOLARSHIP**: SIS shows scholarship but clerk didn't record it
- **SCHOLARSHIP_PERCENTAGE_MISMATCH**: Different percentages between SIS and clerk
- **EARLY_BIRD_PERCENTAGE_MISMATCH**: Discount percentage doesn't match rule
- **NET_AMOUNT_MISMATCH**: Final amounts don't match

### 5. Confidence Scoring

```python
# Determine confidence based on discrepancies
if not discrepancies:
    confidence_level = HIGH
    confidence_score = 95%
elif any(d.severity in ['HIGH', 'CRITICAL'] for d in discrepancies):
    confidence_level = NONE
    confidence_score = 20%
elif any(d.severity == 'MEDIUM' for d in discrepancies):
    confidence_level = LOW
    confidence_score = 60%
else:
    confidence_level = MEDIUM
    confidence_score = 80%
```

## Usage Examples

### Running SIS Integration Test

```bash
# Run comprehensive integration test
python manage.py run_sis_integration_test /path/to/payments.csv \
    --batch-name "SPRING-2024-TEST" \
    --limit 1000 \
    --verbose

# Output shows:
# 🚀 Starting SIS Integration Test Reconciliation
# 📄 CSV File: /path/to/payments.csv
# 📊 Limit: 1000 records
# 
# 🚨 HIGH: CLERK ERROR: Scholarship percentage mismatch - SIS calculated 50% but clerk recorded 40%
# 📊 Processed 50 payments...
# 
# 🎉 SIS Integration Test Complete!
# 📊 Total Processed: 1000
# ✅ Successful: 950
# ❌ Errors: 50
# ⚠️ Payments with Discrepancies: 75
```

### Processing Individual Payment

```python
from apps.finance.services.sis_integration_test_service import (
    SISIntegrationTestService,
    CSVPaymentData
)

service = SISIntegrationTestService(user=request.user)

# Process single payment
csv_data = CSVPaymentData(
    student_id="John Doe",
    term_code="2024-1",
    amount=Decimal("1500.00"),
    net_amount=Decimal("1350.00"),
    net_discount=Decimal("150.00"),
    notes="10% early bird discount applied",
    payment_type="CASH",
    payment_date="2024-01-15",
    receipt_number="RCP-2024-001"
)

status, discrepancies = service.process_payment_integration_test(csv_data)

# Review discrepancies
for disc in discrepancies:
    print(f"{disc.severity}: {disc.description}")
    print(f"SIS Value: {disc.sis_value}, Clerk Value: {disc.clerk_value}")
```

### Batch Reconciliation Review

```python
# Review batch results
batch = ReconciliationBatch.objects.get(batch_id="SPRING-2024-TEST")

# Check summary
print(f"Success Rate: {batch.results_summary['success_rate']}%")
print(f"Discrepancy Count: {batch.results_summary['discrepancy_count']}")

# Review discrepancy breakdown
for disc_type, count in batch.results_summary['discrepancies_by_type'].items():
    print(f"{disc_type}: {count} occurrences")

# Find high-severity issues
critical_issues = ReconciliationStatus.objects.filter(
    reconciliation_batch=batch,
    confidence_level=ReconciliationStatus.ConfidenceLevel.NONE
)
```

## Best Practices

### 1. Data Preparation

- **Clean CSV Data**: Ensure consistent formatting and encoding
- **Validate Required Fields**: Check for NULL values and empty strings
- **Standardize Dates**: Use consistent date formats
- **Normalize Names**: Handle name variations and duplicates

### 2. Reconciliation Configuration

- **Set Appropriate Thresholds**: Configure variance tolerances
- **Define Severity Levels**: Establish clear criteria for HIGH/MEDIUM/LOW
- **Enable Verbose Logging**: Use --verbose flag for troubleshooting
- **Process in Batches**: Use reasonable limits to avoid timeouts

### 3. Error Handling

- **Review Exception Categories**: 
  - MISSING_STUDENT_OR_TERM
  - NO_ENROLLMENTS
  - PROCESSING_ERROR
- **Track Error Patterns**: Monitor recurring issues
- **Document Resolutions**: Record how discrepancies were resolved

### 4. Performance Optimization

```python
# Use select_related for efficient queries
enrollments = ClassHeaderEnrollment.objects.filter(
    student=student,
    class_header__term=term
).select_related(
    'class_header__course',
    'class_header'
)

# Process in chunks for large datasets
for chunk in chunk_list(payments, size=100):
    process_chunk(chunk)
```

### 5. Audit Trail

- **Maintain Complete History**: Keep all reconciliation runs
- **Document Manual Adjustments**: Record why changes were made
- **Track User Actions**: Use UserTrackingModel fields
- **Generate Reports**: Create summaries for management review

## Integration with Other Services

### Pricing Service Integration

The reconciliation service uses `SeparatedPricingService` for accurate pricing:

```python
course_price, pricing_description = self.pricing_service.calculate_course_price(
    course=enrollment.class_header.course,
    student=student,
    term=term,
    class_header=enrollment.class_header
)
```

### Scholarship Service Integration

Validates scholarships against actual records:

```python
active_scholarships = Scholarship.objects.filter(
    student=student,
    status__in=[Scholarship.AwardStatus.APPROVED, Scholarship.AwardStatus.ACTIVE],
    start_date__lte=term.end_date
)
```

### Discount Rule Integration

Matches clerk notes against configured discount rules:

```python
for pattern, rule in self.discount_rules_cache.items():
    if pattern in notes.lower():
        expected_percentage = rule.discount_percentage
        # Verify against clerk's recorded percentage
```

## Troubleshooting

### Common Issues

1. **Student Not Found**
   - Check name variations and spelling
   - Verify student exists in the system
   - Consider fuzzy matching for names

2. **Missing Enrollments**
   - Verify term dates are correct
   - Check enrollment status filters
   - Ensure course associations exist

3. **Pricing Mismatches**
   - Review pricing tier assignments
   - Check for special course pricing
   - Verify scholarship applications

4. **Performance Issues**
   - Reduce batch size with --limit flag
   - Add database indexes on frequently queried fields
   - Use select_related() and prefetch_related()

## Future Enhancements

1. **Machine Learning Integration**
   - Automatic pattern recognition for discount types
   - Anomaly detection for unusual transactions
   - Predictive confidence scoring

2. **Real-time Reconciliation**
   - Webhook integration for immediate processing
   - Live dashboard for monitoring
   - Automatic alert generation

3. **Enhanced Reporting**
   - Customizable reconciliation reports
   - Trend analysis over time
   - Comparative analytics between terms

4. **API Integration**
   - RESTful API for external reconciliation
   - Bulk import endpoints
   - Real-time status updates