# Finance App Pricing Service Guide

## Overview

The Finance app's pricing services provide flexible and comprehensive pricing calculation for courses, fees, and special programs. The system uses the `SeparatedPricingService` as the primary pricing engine, supporting multiple pricing models and student categories.

## Table of Contents

1. [Separated Pricing Service](#separated-pricing-service)
2. [Pricing Models](#pricing-models)
3. [Pricing Calculation Logic](#pricing-calculation-logic)
4. [Usage Examples](#usage-examples)
5. [Integration Points](#integration-points)
6. [Best Practices](#best-practices)

## Separated Pricing Service

Located at `apps.finance.services.separated_pricing_service.py`, this is the main pricing engine for the SIS.

### Key Features

- **Multiple Pricing Models**: Supports fixed pricing, credit-based pricing, and special course pricing
- **Student Category Awareness**: Different pricing for local/foreign students
- **Course-Specific Overrides**: Individual course pricing configurations
- **Senior Project Pricing**: Special handling for capstone courses
- **Reading Class Support**: Specific pricing for reading/tutorial classes
- **Default Fallback**: Configurable default pricing when specific rules don't apply

### Service Methods

```python
class SeparatedPricingService:
    def calculate_course_price(
        self,
        course: Course,
        student: StudentProfile,
        term: Term,
        class_header: ClassHeader = None
    ) -> tuple[Decimal, str]:
        """
        Calculate the price for a course based on all applicable pricing rules.
        
        Returns:
            tuple: (price, pricing_description)
        """
```

## Pricing Models

### 1. DefaultPricing

The base pricing model for standard courses:

```python
class DefaultPricing(TimestampedModel):
    foreign_student_credit_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Price per credit for foreign students"
    )
    local_student_credit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2, 
        help_text="Price per credit for local students"
    )
    is_active = models.BooleanField(default=True)
    effective_date = models.DateField()
```

### 2. CourseFixedPricing

Fixed pricing for specific courses:

```python
class CourseFixedPricing(TimestampedModel):
    course_code = models.CharField(max_length=20)
    course_title = models.CharField(max_length=255)
    fixed_price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    
    # Optional student type specific pricing
    applies_to_foreign = models.BooleanField(default=True)
    applies_to_local = models.BooleanField(default=True)
```

### 3. SeniorProjectPricing

Specialized pricing for senior/capstone projects:

```python
class SeniorProjectPricing(TimestampedModel):
    course = models.ForeignKey(SeniorProjectCourse, on_delete=models.CASCADE)
    local_price = models.DecimalField(max_digits=10, decimal_places=2)
    foreign_price = models.DecimalField(max_digits=10, decimal_places=2)
    term = models.ForeignKey('curriculum.Term', on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
```

### 4. ReadingClassPricing

Pricing for reading/tutorial classes:

```python
class ReadingClassPricing(TimestampedModel):
    course_code = models.CharField(max_length=20)
    local_price = models.DecimalField(max_digits=10, decimal_places=2)
    foreign_price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
```

### 5. FeePricing

Non-tuition fee pricing:

```python
class FeePricing(TimestampedModel):
    fee_code = models.CharField(max_length=50, unique=True)
    fee_name = models.CharField(max_length=200)
    fee_type = models.CharField(max_length=20, choices=FeeType.choices)
    
    # Amount configuration
    base_amount = models.DecimalField(max_digits=10, decimal_places=2)
    local_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    foreign_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    
    # G/L integration
    gl_account = models.ForeignKey(GLAccount, on_delete=models.PROTECT)
```

## Pricing Calculation Logic

### Pricing Hierarchy

The pricing service follows this hierarchy when calculating prices:

1. **Senior Project Check**: If course is identified as senior project, use SeniorProjectPricing
2. **Fixed Course Pricing**: Check CourseFixedPricing for exact course match
3. **Reading Class Check**: If course code contains "READ", use ReadingClassPricing
4. **Default Pricing**: Use DefaultPricing based on credits and student type
5. **Fallback**: If no pricing found, use configurable fallback amount

### Student Type Determination

```python
def _determine_student_type(self, student: StudentProfile) -> str:
    """Determine if student is local or foreign."""
    if not student or not student.person:
        return "foreign"  # Default to foreign pricing
    
    nationality = student.person.nationality.lower() if student.person.nationality else ""
    
    # Local if Cambodian/Khmer
    if any(term in nationality for term in ["cambodia", "khmer", "kampuchea"]):
        return "local"
    
    return "foreign"
```

### Calculation Example

```python
# 1. Senior Project Pricing
if self._is_senior_project(course):
    price = self._calculate_senior_project_price(course, student_type, term)
    return price, "SENIOR_PROJECT_PRICING"

# 2. Fixed Course Pricing
fixed_pricing = CourseFixedPricing.objects.filter(
    course_code=course.code,
    is_active=True
).first()

if fixed_pricing:
    if student_type == "local" and fixed_pricing.applies_to_local:
        return fixed_pricing.fixed_price, "FIXED_COURSE_PRICING"
    elif student_type == "foreign" and fixed_pricing.applies_to_foreign:
        return fixed_pricing.fixed_price, "FIXED_COURSE_PRICING"

# 3. Reading Class Pricing
if "READ" in course.code.upper():
    reading_pricing = ReadingClassPricing.objects.filter(
        course_code=course.code,
        is_active=True
    ).first()
    
    if reading_pricing:
        price = reading_pricing.local_price if student_type == "local" else reading_pricing.foreign_price
        return price, "READING_CLASS_PRICING"

# 4. Default Credit-Based Pricing
default_pricing = DefaultPricing.objects.filter(
    is_active=True,
    effective_date__lte=term.start_date if term else timezone.now().date()
).order_by('-effective_date').first()

if default_pricing:
    credit_price = (
        default_pricing.local_student_credit_price 
        if student_type == "local" 
        else default_pricing.foreign_student_credit_price
    )
    total_price = credit_price * Decimal(str(course.credits))
    return total_price, f"DEFAULT_{student_type.upper()}_PRICING"
```

## Usage Examples

### Basic Course Pricing

```python
from apps.finance.services.separated_pricing_service import SeparatedPricingService
from apps.people.models import StudentProfile
from apps.curriculum.models import Course, Term

service = SeparatedPricingService()

# Get student and course
student = StudentProfile.objects.get(student_id="ST12345")
course = Course.objects.get(code="ACCT-101")
term = Term.objects.get(code="2024-1")

# Calculate price
price, method = service.calculate_course_price(
    course=course,
    student=student,
    term=term
)

print(f"Course: {course.code}")
print(f"Price: ${price}")
print(f"Method: {method}")
# Output:
# Course: ACCT-101
# Price: $225.00
# Method: DEFAULT_LOCAL_PRICING
```

### Batch Pricing Calculation

```python
# Calculate pricing for all student enrollments
def calculate_term_billing(student, term):
    service = SeparatedPricingService()
    enrollments = ClassHeaderEnrollment.objects.filter(
        student=student,
        class_header__term=term,
        status='ENROLLED'
    ).select_related('class_header__course')
    
    total_tuition = Decimal('0')
    billing_details = []
    
    for enrollment in enrollments:
        price, method = service.calculate_course_price(
            course=enrollment.class_header.course,
            student=student,
            term=term,
            class_header=enrollment.class_header
        )
        
        total_tuition += price
        billing_details.append({
            'course': enrollment.class_header.course.code,
            'price': price,
            'method': method,
            'credits': enrollment.class_header.course.credits
        })
    
    return total_tuition, billing_details
```

### Creating Pricing Rules

```python
# Set up default pricing
DefaultPricing.objects.create(
    foreign_student_credit_price=Decimal("125.00"),
    local_student_credit_price=Decimal("75.00"),
    is_active=True,
    effective_date=date(2024, 1, 1)
)

# Add fixed pricing for specific course
CourseFixedPricing.objects.create(
    course_code="THESIS-499",
    course_title="Senior Thesis",
    fixed_price=Decimal("500.00"),
    applies_to_foreign=True,
    applies_to_local=True,
    is_active=True
)

# Configure senior project pricing
senior_course = SeniorProjectCourse.objects.create(
    course_code="CAPSTONE-498",
    is_active=True
)

SeniorProjectPricing.objects.create(
    course=senior_course,
    local_price=Decimal("400.00"),
    foreign_price=Decimal("600.00"),
    term=term,
    is_active=True
)
```

## Integration Points

### Invoice Generation

The pricing service integrates with invoice generation:

```python
from apps.finance.services.billing_service import BillingService

# Generate invoice with calculated pricing
billing_service = BillingService()
invoice = billing_service.generate_term_invoice(
    student=student,
    term=term,
    include_fees=True
)

# Invoice line items use pricing service calculations
for line_item in invoice.line_items.all():
    if line_item.enrollment:
        # Price calculated via SeparatedPricingService
        print(f"{line_item.description}: ${line_item.total_amount}")
```

### Reconciliation Integration

Used in reconciliation to verify historical pricing:

```python
# In SIS Integration Test
sis_calculation = self._calculate_sis_pricing(
    student=student,
    term=term,
    enrollments=enrollments
)

# Compare to actual payment amounts
variance = sis_calculation.expected_net_amount - payment.amount
```

### Fee Calculation

Additional fees beyond tuition:

```python
# Calculate fees using FeePricing
def calculate_term_fees(student, term):
    fees = []
    
    # Registration fee
    reg_fee = FeePricing.objects.get(
        fee_code="REGISTRATION",
        is_active=True
    )
    
    fee_amount = (
        reg_fee.local_amount if student.is_local 
        else reg_fee.foreign_amount
    ) or reg_fee.base_amount
    
    fees.append({
        'type': 'Registration Fee',
        'amount': fee_amount,
        'gl_account': reg_fee.gl_account.account_code
    })
    
    return fees
```

## Best Practices

### 1. Pricing Configuration

- **Effective Dating**: Always set effective_date for pricing rules
- **Active Flags**: Use is_active to disable outdated pricing
- **Overlap Prevention**: Avoid overlapping date ranges for same pricing type
- **Audit Trail**: Use TimestampedModel fields to track changes

### 2. Performance Optimization

```python
# Prefetch related data for batch operations
enrollments = ClassHeaderEnrollment.objects.filter(
    class_header__term=term
).select_related(
    'student__person',
    'class_header__course'
).prefetch_related(
    'class_header__course__senior_project_courses'
)

# Cache pricing lookups
@lru_cache(maxsize=128)
def get_default_pricing(term_start_date):
    return DefaultPricing.objects.filter(
        is_active=True,
        effective_date__lte=term_start_date
    ).order_by('-effective_date').first()
```

### 3. Error Handling

```python
try:
    price, method = service.calculate_course_price(
        course=course,
        student=student,
        term=term
    )
except Exception as e:
    logger.error(f"Pricing calculation failed for {course.code}: {e}")
    # Use fallback pricing
    price = Decimal("500.00")
    method = "FALLBACK_ERROR_PRICING"
```

### 4. Testing Pricing Rules

```python
# Test different student types
def test_local_vs_foreign_pricing():
    service = SeparatedPricingService()
    course = Course.objects.get(code="MATH-101")
    
    # Test local student
    local_student = StudentProfile.objects.create(
        person__nationality="Cambodian"
    )
    local_price, _ = service.calculate_course_price(
        course=course,
        student=local_student
    )
    
    # Test foreign student
    foreign_student = StudentProfile.objects.create(
        person__nationality="American"
    )
    foreign_price, _ = service.calculate_course_price(
        course=course,
        student=foreign_student
    )
    
    assert foreign_price > local_price
```

## Troubleshooting

### Common Issues

1. **No Pricing Found**
   - Check if DefaultPricing exists and is active
   - Verify effective_date is not in future
   - Ensure fallback pricing is configured

2. **Wrong Student Type**
   - Verify person.nationality is set correctly
   - Check nationality matching logic
   - Consider edge cases (dual citizenship, etc.)

3. **Senior Project Not Recognized**
   - Ensure SeniorProjectCourse entry exists
   - Check course code matching
   - Verify term association

4. **Performance Issues**
   - Use select_related for student/course queries
   - Implement caching for frequently accessed pricing
   - Consider database indexes on pricing lookup fields

## Future Enhancements

1. **Dynamic Pricing Rules**
   - Time-based pricing (early registration discounts)
   - Volume discounts for multiple courses
   - Promotional pricing campaigns

2. **Advanced Student Categories**
   - Exchange student pricing
   - Alumni continuing education rates
   - Staff/faculty family discounts

3. **Pricing Analytics**
   - Revenue optimization suggestions
   - Pricing elasticity analysis
   - Competitive pricing comparisons