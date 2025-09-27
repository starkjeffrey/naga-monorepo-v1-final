# Scholarships App

## Overview

The `scholarships` app manages financial aid relationships, sponsorships, and scholarship programs for the Naga SIS. This business logic layer app handles sponsor management, student financial aid allocation, and the complex relationships between external sponsors, institutional scholarships, and student funding needs.

## Features

### Sponsor Management

- **Organizational sponsor tracking** with MOU management and relationship history
- **Contact management** with multiple points of contact per sponsor
- **Funding capacity tracking** with budget allocation and utilization
- **Relationship lifecycle** from initial contact through active sponsorship

### Student Sponsorship

- **Individual student sponsorships** with flexible funding arrangements
- **Group sponsorships** for cohort or program-level funding
- **Temporal sponsorship tracking** with start/end dates and renewal cycles
- **Sponsorship status management** with automated alerts and notifications

### Scholarship Programs

- **Merit-based scholarships** with GPA and achievement criteria
- **Need-based financial aid** with income verification and assessment
- **Institutional scholarships** with internal funding allocation
- **External scholarships** with third-party sponsor coordination

### Financial Integration

- **Seamless finance app integration** for billing adjustments and credits
- **Automated payment processing** for sponsor-funded student accounts
- **Financial reporting** for sponsors with detailed usage tracking
- **Compliance reporting** for institutional and sponsor requirements

## Models

### Sponsor Management

#### Sponsor

External organizations providing student financial support.

```python
# Create organizational sponsor
corporate_sponsor = Sponsor.objects.create(
    name="ABC Corporation Foundation",
    sponsor_type=SponsorType.CORPORATE,
    country="Cambodia",
    contact_email="foundation@abccorp.com.kh",
    phone="+855 23 456 789",
    address={
        "street": "123 Business District",
        "city": "Phnom Penh",
        "postal_code": "12345",
        "country": "Cambodia"
    },
    website="https://foundation.abccorp.com.kh",
    established_date=date(2020, 1, 15),
    status=SponsorStatus.ACTIVE
)

# Add sponsor details
corporate_sponsor.description = """
ABC Corporation Foundation provides educational opportunities
for underprivileged students in Cambodia, focusing on business
and technology education.
"""

corporate_sponsor.funding_focus = [
    "Business Administration",
    "Computer Science",
    "Information Technology"
]

corporate_sponsor.annual_budget = Decimal("50000.00")
corporate_sponsor.save()
```

#### SponsoredStudent

Individual student sponsorship relationships with funding details.

```python
# Create sponsored student relationship
sponsored_student = SponsoredStudent.objects.create(
    sponsor=corporate_sponsor,
    student=student_profile,
    sponsorship_type=SponsorshipType.FULL_TUITION,
    start_date=date(2024, 8, 1),
    end_date=date(2028, 5, 31),  # 4-year sponsorship
    annual_amount=Decimal("3000.00"),
    total_commitment=Decimal("12000.00"),
    payment_schedule=PaymentSchedule.SEMESTER,
    status=SponsorshipStatus.ACTIVE,
    selection_criteria={
        "academic_merit": True,
        "financial_need": True,
        "program_relevance": "Business Administration",
        "community_service": "Required"
    }
)

# Add sponsorship conditions
sponsored_student.conditions = {
    "minimum_gpa": "3.0",
    "community_service_hours": 40,
    "annual_report_required": True,
    "mentor_meetings": "Monthly",
    "graduation_requirement": "On-time completion"
}
sponsored_student.save()
```

### Scholarship Programs

#### Scholarship

Institutional and external scholarship programs.

```python
# Create merit-based scholarship
academic_excellence = Scholarship.objects.create(
    name="Academic Excellence Scholarship",
    scholarship_type=ScholarshipType.MERIT_BASED,
    funding_source=FundingSource.INSTITUTIONAL,
    program_level=ProgramLevel.BACHELOR,
    amount_type=AmountType.FIXED,
    amount=Decimal("1500.00"),
    duration_terms=2,  # One academic year
    max_recipients=10,
    eligibility_criteria={
        "minimum_gpa": "3.7",
        "credit_hours_completed": 30,
        "academic_standing": "good",
        "citizenship": "any",
        "financial_need": False
    },
    application_deadline=date(2024, 6, 30),
    award_date=date(2024, 7, 15),
    renewable=True,
    renewal_criteria={
        "maintain_gpa": "3.5",
        "full_time_enrollment": True,
        "satisfactory_progress": True
    }
)

# Create need-based scholarship
financial_assistance = Scholarship.objects.create(
    name="Financial Assistance Program",
    scholarship_type=ScholarshipType.NEED_BASED,
    funding_source=FundingSource.INSTITUTIONAL,
    amount_type=AmountType.VARIABLE,
    minimum_amount=Decimal("500.00"),
    maximum_amount=Decimal("2500.00"),
    max_recipients=25,
    eligibility_criteria={
        "minimum_gpa": "2.5",
        "financial_need": True,
        "family_income_threshold": "25000.00",
        "enrollment_status": "full_time"
    },
    requires_fafsa=True,
    requires_essay=True
)
```

#### ScholarshipRecipient

Individual scholarship awards with tracking and reporting.

```python
# Award scholarship to student
scholarship_recipient = ScholarshipRecipient.objects.create(
    scholarship=academic_excellence,
    student=high_achieving_student,
    award_amount=Decimal("1500.00"),
    award_term=fall_2024,
    award_date=date(2024, 7, 15),
    status=RecipientStatus.ACTIVE,
    selection_score=Decimal("95.5"),
    application_data={
        "gpa": "3.85",
        "essay_score": "92",
        "recommendation_scores": [88, 91, 94],
        "extracurricular_score": "87"
    }
)

# Track scholarship utilization
scholarship_recipient.disbursements.create(
    amount=Decimal("750.00"),
    disbursement_date=date(2024, 8, 15),
    disbursement_method=DisbursementMethod.TUITION_CREDIT,
    term=fall_2024,
    processed_by=financial_aid_officer
)
```

## Services

### Scholarship Service

Comprehensive scholarship management with eligibility evaluation.

```python
from apps.scholarships.services import ScholarshipService

# Evaluate student eligibility for scholarships
eligibility_results = ScholarshipService.evaluate_student_eligibility(
    student=student_profile,
    term=fall_2024,
    include_need_based=True,
    include_merit_based=True
)

# Returns detailed eligibility analysis
{
    'eligible_scholarships': [
        {
            'scholarship': academic_excellence,
            'eligibility_score': 85.5,
            'meets_requirements': True,
            'missing_requirements': [],
            'estimated_award': Decimal('1500.00')
        }
    ],
    'ineligible_scholarships': [
        {
            'scholarship': graduate_fellowship,
            'reason': 'Undergraduate student not eligible',
            'missing_requirements': ['graduate_enrollment']
        }
    ],
    'conditional_eligibility': [
        {
            'scholarship': financial_assistance,
            'condition': 'Financial need assessment required',
            'next_steps': ['Submit FAFSA', 'Complete financial aid application']
        }
    ]
}
```

### Sponsor Service

Sponsor relationship management with financial tracking.

```python
from apps.scholarships.services import SponsorService

# Create comprehensive sponsor relationship
sponsor_relationship = SponsorService.establish_sponsorship(
    sponsor=corporate_sponsor,
    student=student_profile,
    sponsorship_data={
        'type': SponsorshipType.PARTIAL_TUITION,
        'annual_amount': Decimal('2000.00'),
        'duration_years': 4,
        'payment_schedule': PaymentSchedule.SEMESTER,
        'conditions': {
            'minimum_gpa': '3.0',
            'community_service': True,
            'annual_reporting': True
        }
    }
)

# Track sponsor financial contributions
financial_summary = SponsorService.get_sponsor_financial_summary(
    sponsor=corporate_sponsor,
    year=2024
)

# Returns comprehensive financial tracking
{
    'total_commitment': Decimal('50000.00'),
    'amount_disbursed': Decimal('32000.00'),
    'amount_pending': Decimal('8000.00'),
    'amount_remaining': Decimal('10000.00'),
    'students_supported': 15,
    'average_support_per_student': Decimal('2133.33'),
    'disbursement_schedule': [
        {
            'student': 'Sophea Chan',
            'amount': Decimal('1000.00'),
            'due_date': '2024-08-15',
            'status': 'pending'
        }
    ]
}
```

### Financial Integration Service

Seamless integration with finance app for billing and payments.

```python
from apps.scholarships.services import FinancialIntegrationService

# Apply scholarship credit to student billing
credit_result = FinancialIntegrationService.apply_scholarship_credit(
    student=student_profile,
    scholarship_recipient=scholarship_recipient,
    term=fall_2024,
    amount=Decimal('1500.00')
)

# Process sponsor payment for student
sponsor_payment = FinancialIntegrationService.process_sponsor_payment(
    sponsored_student=sponsored_student,
    payment_amount=Decimal('1000.00'),
    payment_reference='SPONSOR-ABC-2024-001',
    apply_to_term=fall_2024
)
```

## Management Commands

### Scholarship Administration

```bash
# Process scholarship renewals
python manage.py process_scholarship_renewals --term=fall2024

# Evaluate scholarship eligibility for all students
python manage.py evaluate_scholarship_eligibility --term=fall2024

# Generate scholarship award letters
python manage.py generate_award_letters --scholarship=academic-excellence

# Import scholarship data from legacy system
python manage.py import_legacy_scholarships --file=scholarships.csv
```

### Sponsor Management

```bash
# Load sponsors from legacy system
python manage.py load_sponsors_from_v0 --validate-data

# Generate sponsor reports
python manage.py generate_sponsor_reports --year=2024 --format=pdf

# Process sponsor payments
python manage.py process_sponsor_payments --due-date=2024-08-15

# Send sponsor updates
python manage.py send_sponsor_updates --quarterly-report
```

### Financial Operations

```bash
# Apply scholarship credits to student accounts
python manage.py apply_scholarship_credits --term=fall2024

# Generate scholarship disbursements
python manage.py generate_scholarship_disbursements --term=fall2024

# Reconcile sponsor payments
python manage.py reconcile_sponsor_payments --month=july

# Generate financial aid reports
python manage.py generate_aid_reports --type=federal-compliance
```

## API Endpoints

### Scholarship Information API

```python
# Get available scholarships
GET /api/scholarships/available/?student_id=123&term=fall2024

{
    "available_scholarships": [
        {
            "id": 1,
            "name": "Academic Excellence Scholarship",
            "type": "merit_based",
            "amount": "1500.00",
            "application_deadline": "2024-06-30",
            "eligibility_status": "eligible",
            "requirements": [
                "Minimum GPA 3.7",
                "30 completed credit hours",
                "Good academic standing"
            ],
            "application_url": "/scholarships/apply/1/"
        }
    ],
    "current_awards": [
        {
            "scholarship_name": "Financial Assistance Program",
            "award_amount": "1200.00",
            "award_term": "Fall 2024",
            "status": "active",
            "disbursement_date": "2024-08-15"
        }
    ]
}
```

### Sponsor Dashboard API

```python
# Get sponsor dashboard data
GET /api/scholarships/sponsors/{sponsor_id}/dashboard/

{
    "sponsor_info": {
        "name": "ABC Corporation Foundation",
        "status": "active",
        "relationship_since": "2020-01-15"
    },
    "financial_summary": {
        "annual_commitment": "50000.00",
        "year_to_date_disbursed": "32000.00",
        "remaining_budget": "18000.00",
        "students_supported": 15
    },
    "sponsored_students": [
        {
            "student_name": "Sophea Chan",
            "program": "Business Administration",
            "year": "Junior",
            "gpa": "3.65",
            "sponsorship_amount": "3000.00",
            "status": "active",
            "last_report_date": "2024-06-15"
        }
    ],
    "upcoming_payments": [
        {
            "student": "Sophea Chan",
            "amount": "1500.00",
            "due_date": "2024-08-15",
            "purpose": "Fall 2024 tuition"
        }
    ]
}
```

### Financial Integration API

```python
# Apply scholarship to student account
POST /api/scholarships/apply-credit/
{
    "student_id": 123,
    "scholarship_recipient_id": 456,
    "amount": "1500.00",
    "term": "fall2024",
    "credit_type": "tuition_reduction"
}

# Response
{
    "credit_applied": true,
    "credit_amount": "1500.00",
    "student_balance_after": "500.00",
    "transaction_id": "SC-2024-001234",
    "effective_date": "2024-08-15"
}
```

## Integration Examples

### With Finance App

```python
# Automatic scholarship credit application
def apply_scholarship_to_billing(scholarship_recipient, term):
    from apps.finance.services import BillingService

    # Get student's billing for term
    student_billing = BillingService.get_student_billing(
        student=scholarship_recipient.student,
        term=term
    )

    # Apply scholarship as credit
    credit_amount = min(
        scholarship_recipient.award_amount,
        student_billing.outstanding_balance
    )

    credit_transaction = BillingService.apply_credit(
        student=scholarship_recipient.student,
        amount=credit_amount,
        description=f"Scholarship credit - {scholarship_recipient.scholarship.name}",
        reference_id=f"SCHOL-{scholarship_recipient.id}",
        term=term
    )

    # Record disbursement
    ScholarshipDisbursement.objects.create(
        scholarship_recipient=scholarship_recipient,
        amount=credit_amount,
        disbursement_date=date.today(),
        disbursement_method=DisbursementMethod.TUITION_CREDIT,
        finance_transaction=credit_transaction
    )

    return credit_transaction
```

### With People App

```python
# Enhanced student profile with scholarship information
def get_student_financial_aid_profile(student_id):
    from apps.people.services import PersonService

    student = PersonService.get_student_profile(student_id)

    # Add scholarship information
    scholarship_info = {
        'current_scholarships': ScholarshipRecipient.objects.filter(
            student=student,
            status=RecipientStatus.ACTIVE
        ),
        'sponsored_relationships': SponsoredStudent.objects.filter(
            student=student,
            status=SponsorshipStatus.ACTIVE
        ),
        'total_aid_received': calculate_total_aid_received(student),
        'aid_eligibility_status': evaluate_continued_eligibility(student)
    }

    return {
        'student_profile': student,
        'financial_aid': scholarship_info
    }
```

### With Academic App

```python
# Scholarship renewal based on academic progress
def evaluate_scholarship_renewal(scholarship_recipient, completed_term):
    from apps.academic.services import AcademicService

    # Get academic progress
    academic_progress = AcademicService.get_student_progress(
        student=scholarship_recipient.student,
        as_of_term=completed_term
    )

    # Check renewal criteria
    renewal_eligible = True
    renewal_issues = []

    if academic_progress.gpa < scholarship_recipient.scholarship.renewal_criteria.get('minimum_gpa', 0):
        renewal_eligible = False
        renewal_issues.append(f"GPA below required {scholarship_recipient.scholarship.renewal_criteria['minimum_gpa']}")

    if not academic_progress.satisfactory_academic_progress:
        renewal_eligible = False
        renewal_issues.append("Not meeting satisfactory academic progress")

    # Process renewal
    if renewal_eligible:
        ScholarshipService.renew_scholarship(
            scholarship_recipient=scholarship_recipient,
            renewal_term=get_next_term(completed_term)
        )
    else:
        ScholarshipService.suspend_scholarship(
            scholarship_recipient=scholarship_recipient,
            suspension_reason="; ".join(renewal_issues)
        )

    return renewal_eligible, renewal_issues
```

## Validation & Business Rules

### Scholarship Eligibility Validation

```python
def validate_scholarship_eligibility(student, scholarship):
    """Comprehensive scholarship eligibility validation."""
    errors = []
    criteria = scholarship.eligibility_criteria

    # GPA requirement
    if 'minimum_gpa' in criteria:
        if student.cumulative_gpa < Decimal(criteria['minimum_gpa']):
            errors.append(f"GPA {student.cumulative_gpa} below required {criteria['minimum_gpa']}")

    # Credit hours requirement
    if 'credit_hours_completed' in criteria:
        if student.total_credits < criteria['credit_hours_completed']:
            errors.append(f"Credit hours {student.total_credits} below required {criteria['credit_hours_completed']}")

    # Enrollment status
    if 'enrollment_status' in criteria:
        current_enrollment = student.get_current_enrollment_status()
        if current_enrollment != criteria['enrollment_status']:
            errors.append(f"Enrollment status {current_enrollment} does not match required {criteria['enrollment_status']}")

    # Financial need assessment
    if criteria.get('financial_need') and not student.has_completed_financial_aid_application():
        errors.append("Financial need assessment required but not completed")

    return len(errors) == 0, errors

def validate_sponsor_payment_capacity(sponsor, new_commitment_amount):
    """Validate sponsor can make additional financial commitments."""
    current_commitments = SponsoredStudent.objects.filter(
        sponsor=sponsor,
        status=SponsorshipStatus.ACTIVE
    ).aggregate(
        total=Sum('annual_amount')
    )['total'] or Decimal('0.00')

    total_commitment = current_commitments + new_commitment_amount

    if total_commitment > sponsor.annual_budget:
        raise ValidationError(
            f"Total commitment {total_commitment} exceeds sponsor budget {sponsor.annual_budget}"
        )

    return True
```

## Testing

### Test Coverage

```bash
# Run scholarships app tests
pytest apps/scholarships/

# Test specific functionality
pytest apps/scholarships/tests/test_eligibility_evaluation.py
pytest apps/scholarships/tests/test_sponsor_management.py
pytest apps/scholarships/tests/test_financial_integration.py
```

### Test Factories

```python
from apps.scholarships.tests.factories import (
    SponsorFactory,
    ScholarshipFactory,
    SponsoredStudentFactory,
    ScholarshipRecipientFactory
)

# Create test scholarship data
sponsor = SponsorFactory(
    name="Test Foundation",
    annual_budget=Decimal("25000.00")
)

scholarship = ScholarshipFactory(
    name="Test Merit Scholarship",
    amount=Decimal("1500.00")
)

sponsored_student = SponsoredStudentFactory(
    sponsor=sponsor,
    annual_amount=Decimal("2000.00")
)
```

## Performance Optimization

### Scholarship Eligibility Evaluation

```python
# Efficient batch eligibility evaluation
def evaluate_batch_scholarship_eligibility(students, scholarships):
    """Evaluate multiple students for multiple scholarships efficiently."""

    # Pre-fetch student academic data
    students_with_data = students.select_related(
        'person', 'program_enrollment'
    ).prefetch_related(
        'grades', 'current_enrollments'
    )

    # Pre-calculate academic metrics
    student_metrics = {}
    for student in students_with_data:
        student_metrics[student.id] = {
            'gpa': calculate_gpa(student),
            'credits_completed': calculate_credits(student),
            'enrollment_status': get_enrollment_status(student)
        }

    # Batch evaluate eligibility
    eligibility_results = {}
    for scholarship in scholarships:
        eligible_students = []
        for student in students_with_data:
            if meets_eligibility_criteria(student_metrics[student.id], scholarship):
                eligible_students.append(student)
        eligibility_results[scholarship.id] = eligible_students

    return eligibility_results
```

## Configuration

### Settings

```python
# Scholarships configuration
NAGA_SCHOLARSHIPS_CONFIG = {
    'AUTOMATIC_ELIGIBILITY_EVALUATION': True,
    'SCHOLARSHIP_APPLICATION_DEADLINE_DAYS': 30,
    'FINANCIAL_NEED_ASSESSMENT_REQUIRED': True,
    'MAXIMUM_AWARDS_PER_STUDENT': 3,
    'MINIMUM_SCHOLARSHIP_AMOUNT': Decimal('100.00'),
    'SPONSOR_REPORTING_FREQUENCY': 'quarterly'
}

# Financial integration
NAGA_SCHOLARSHIP_FINANCE_CONFIG = {
    'AUTO_APPLY_CREDITS': True,
    'DISBURSEMENT_SCHEDULE_DAYS': [15, 45],  # Days after term start
    'REQUIRE_ENROLLMENT_VERIFICATION': True,
    'SCHOLARSHIP_GL_ACCOUNT': '4200-01'  # Scholarship revenue account
}
```

## Dependencies

### Internal Dependencies

- `people`: Student profiles and academic information
- `finance`: Billing integration and financial transactions
- `academic`: Academic progress and GPA calculations
- `enrollment`: Student enrollment verification

### External Dependencies

- No external dependencies required

## Architecture Notes

### Design Principles

- **Relationship-focused**: Manages complex sponsor-student-scholarship relationships
- **Financial integration**: Seamless connection with billing and accounting
- **Compliance-ready**: Supports institutional and sponsor reporting requirements
- **Flexible criteria**: Configurable eligibility and renewal requirements

### Key Relationships

- **Sponsors** can support multiple students
- **Students** can have multiple scholarships and sponsorships
- **Scholarships** can have multiple recipients across terms
- **Financial integration** ensures accurate billing and payments

### Future Enhancements

- **AI-powered matching**: Automated student-scholarship matching
- **Blockchain verification**: Immutable scholarship award tracking
- **Mobile scholarship portal**: Student mobile app for scholarship management
- **Predictive analytics**: Early identification of at-risk scholarship recipients
