# Finance App Discount System Guide

## Overview

The Finance app's discount system provides a flexible, rule-based approach to managing various types of discounts and fee adjustments in the Naga Student Information System. The core of this system is the `DiscountRule` model, which enables configurable discount rules that can be automatically applied during billing and reconciliation processes.

## Table of Contents

1. [DiscountRule Model](#discountrule-model)
2. [Discount Types](#discount-types)
3. [How Discounts Work](#how-discounts-work)
4. [Integration with Services](#integration-with-services)
5. [Usage Examples](#usage-examples)
6. [Best Practices](#best-practices)

## DiscountRule Model

The `DiscountRule` model (`apps.finance.models.ar_reconstruction.DiscountRule`) is the central component for managing discount configurations.

### Key Fields

```python
class DiscountRule(TimestampedModel, UserTrackingModel):
    """Configurable discount rules discovered during processing."""
    
    # Rule Identification
    rule_name = models.CharField(max_length=100, unique=True)
    rule_type = models.CharField(max_length=20, choices=RuleType.choices)
    
    # Rule Configuration
    pattern_text = models.CharField(max_length=200)  # Text pattern that triggers this rule
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    fixed_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    
    # Applicability
    applies_to_terms = models.JSONField(default=list)  # Empty = all terms
    applies_to_programs = models.JSONField(default=list)  # Empty = all programs
    
    # Status
    is_active = models.BooleanField(default=True)
    effective_date = models.DateField(default=date.today)
    
    # Usage Tracking
    times_applied = models.PositiveIntegerField(default=0)
    last_applied_date = models.DateTimeField(null=True, blank=True)
```

## Discount Types

The system supports several predefined discount types:

### 1. Early Bird Discount (`EARLY_BIRD`)
- Applied when students register/pay before a specific deadline
- Typically a percentage discount (e.g., 10%)
- Configured per term with different deadlines

### 2. Cash Payment Plan (`CASH_PLAN`)
- Applied when students pay in cash upfront
- Can be percentage or fixed amount
- Encourages immediate payment

### 3. Weekend Class Discount (`WEEKEND`)
- Applied to weekend class enrollments
- Recognizes different pricing for weekend programs
- Usually a percentage discount

### 4. Monk Pricing (`MONK`)
- Special pricing for monks
- Can be significant percentage discount or fixed pricing
- Respects cultural and religious considerations

### 5. Administrative Fee (`ADMIN_FEE`)
- Not a discount but a fee addition
- Can be fixed amount or percentage
- Applied for specific administrative services

### 6. Custom Rule (`CUSTOM`)
- Flexible type for any other discount scenarios
- Fully configurable based on pattern matching

## How Discounts Work

### 1. Pattern Matching

Discounts are triggered by matching text patterns in payment notes or through automatic eligibility checks:

```python
# Example pattern matching in notes
if "early bird" in payment_notes.lower():
    # Look for Early Bird discount rule
    rule = DiscountRule.objects.filter(
        rule_type=DiscountRule.RuleType.EARLY_BIRD,
        is_active=True,
        pattern_text__icontains="early bird"
    ).first()
```

### 2. Eligibility Checking

The `AutomaticDiscountService` checks student eligibility for various discounts:

```python
from apps.finance.services.automatic_discount_service import AutomaticDiscountService

service = AutomaticDiscountService()
result = service.check_early_bird_eligibility(
    student_id="ST001",
    term_code="2024-1",
    payment_date=date(2024, 1, 15)
)

if result.status == DiscountEligibilityStatus.ELIGIBLE:
    # Apply the discount
    discount_amount = result.discount_amount
```

### 3. Rule Application

Discount rules can be applied during:
- Invoice generation
- Payment processing
- Reconciliation
- Price calculation

## Integration with Services

### 1. Automatic Discount Service

Located at `apps.finance.services.automatic_discount_service.py`, this service:
- Loads active discount rules
- Checks student eligibility
- Calculates discount amounts
- Tracks rule usage

Key methods:
```python
def check_early_bird_eligibility(student_id, term_code, payment_date)
def check_cash_payment_plan_eligibility(student_id, term_code)
def check_weekend_class_discount(student_id, term_code)
def get_applicable_discounts(student_id, term_code, payment_date)
```

### 2. Comprehensive Reconciliation Service

The reconciliation service uses discount rules to:
- Verify historical discounts against current rules
- Flag discrepancies in discount applications
- Generate reconciliation reports

### 3. Term Discount Validation

Located at `apps.finance.services.term_discount_validation.py`, this service:
- Validates discount rates across terms
- Identifies missing discount configurations
- Suggests canonical rates based on historical data

## Usage Examples

### Creating a Discount Rule

```python
from apps.finance.models.ar_reconstruction import DiscountRule
from datetime import date

# Create Early Bird discount rule
early_bird = DiscountRule.objects.create(
    rule_name="Early Bird 2024-1",
    rule_type=DiscountRule.RuleType.EARLY_BIRD,
    pattern_text="early bird",
    discount_percentage=10.0,
    applies_to_terms=["2024-1"],
    is_active=True,
    effective_date=date(2024, 1, 1)
)

# Create Monk pricing rule
monk_discount = DiscountRule.objects.create(
    rule_name="Monk Special Pricing",
    rule_type=DiscountRule.RuleType.MONK_PRICING,
    pattern_text="monk",
    discount_percentage=50.0,
    is_active=True
)
```

### Checking Discount Eligibility

```python
from apps.finance.services.automatic_discount_service import AutomaticDiscountService

service = AutomaticDiscountService()

# Check all applicable discounts for a student
discounts = service.get_applicable_discounts(
    student_id="ST001",
    term_code="2024-1",
    payment_date=date(2024, 1, 15)
)

for discount_type, result in discounts.items():
    if result.status == DiscountEligibilityStatus.ELIGIBLE:
        print(f"{discount_type}: ${result.discount_amount}")
```

### Reconciliation with Discount Verification

```python
from apps.finance.services.comprehensive_reconciliation_service import (
    ComprehensiveReconciliationService
)

service = ComprehensiveReconciliationService()

# Process payment with discount verification
status = service.process_csv_payment({
    'student_id': 'John Doe',
    'term_code': '2024-1',
    'amount': 1000.00,
    'notes': '10% early bird discount applied'
})

# Check for discount discrepancies
if status.has_discount_discrepancy:
    print(f"Discount mismatch: {status.discount_error_details}")
```

## Best Practices

### 1. Rule Configuration

- **Be Specific with Patterns**: Use clear, unambiguous pattern text
- **Set Term Limits**: Specify `applies_to_terms` to prevent incorrect application
- **Track Usage**: Monitor `times_applied` to understand discount impact

### 2. Discount Hierarchy

When multiple discounts could apply:
1. Check eligibility for all applicable discounts
2. Apply business rules for combination (e.g., max one discount)
3. Document the selection logic

### 3. Audit Trail

Always maintain audit trails:
- Log when discounts are applied
- Track who approved special discounts
- Record the rule version used

### 4. Testing

Before deploying new discount rules:
1. Test pattern matching with sample data
2. Verify calculations with edge cases
3. Run reconciliation to check historical consistency

### 5. Monitoring

Regular monitoring tasks:
- Review discount usage reports
- Check for anomalous discount applications
- Validate discount percentages remain reasonable

## Integration with Other Systems

### Scholarships
- Discounts are separate from scholarships
- Scholarships typically cover tuition percentages
- Discounts apply to specific fees or situations

### General Ledger
- Discounts affect revenue recognition
- Each discount type may map to different GL accounts
- Proper categorization ensures accurate financial reporting

### Reporting
- Discount usage appears in financial reports
- Analytics can show discount effectiveness
- Reconciliation reports highlight discount discrepancies

## Troubleshooting

### Common Issues

1. **Discount Not Applied**
   - Check if rule is active
   - Verify pattern matching
   - Confirm term applicability

2. **Wrong Discount Amount**
   - Verify percentage vs fixed amount configuration
   - Check for multiple rules matching
   - Review calculation logic

3. **Historical Discrepancies**
   - Run term discount validation
   - Review pattern text changes
   - Check effective dates

## Future Enhancements

Planned improvements to the discount system:
1. Time-based discounts (specific hours/days)
2. Quantity-based discounts (multiple courses)
3. Loyalty discounts (returning students)
4. Automated discount approval workflows
5. Advanced pattern matching with regular expressions