# Level Testing App

## Overview

The `level_testing` app manages language placement testing, test registration, fee processing, and results management for prospective students. This specialized service app provides a complete testing workflow from initial application through score reporting, with integrated payment processing and automated placement recommendations.

## Features

### Comprehensive Test Management

- **Multi-step application process** with form wizard interface
- **Test session scheduling** with capacity management and booking
- **Flexible test administration** supporting multiple assessment types
- **Automated scoring** with placement level recommendations

### Registration & Payment Processing

- **Self-service registration** with document upload capabilities
- **Integrated fee calculation** with student type differentiation
- **Multiple payment methods** (cash, bank transfer, mobile payment)
- **Payment verification** with receipt generation and tracking

### Student Management & Duplicate Detection

- **Potential student profiles** for non-enrolled test takers
- **Sophisticated duplicate detection** using name similarity algorithms
- **Student record merging** with data consolidation workflows
- **Contact information validation** and verification

### Results & Placement Management

- **Secure test result recording** with score validation
- **Automated placement recommendations** based on score ranges
- **Result notification** with score reports and next steps
- **Integration pathways** to enrollment and academic systems

## Models

### Test Administration

#### TestSession

Scheduled testing sessions with capacity and logistics management.

```python
# Create placement test session
test_session = TestSession.objects.create(
    session_name="English Placement Test - July 2024",
    test_type=TestType.ENGLISH_PLACEMENT,
    session_date=date(2024, 7, 20),
    start_time=time(9, 0),
    end_time=time(12, 0),
    capacity=30,
    location="Computer Lab A",
    proctor=test_administrator,
    registration_deadline=date(2024, 7, 18),
    fee_amount=Decimal("25.00"),
    instructions={
        "arrival_time": "8:45 AM",
        "required_documents": ["ID card or passport", "Registration receipt"],
        "prohibited_items": ["Mobile phones", "Dictionaries", "Electronic devices"],
        "test_format": "Computer-based assessment",
        "duration": "3 hours including breaks"
    },
    status=SessionStatus.OPEN
)
```

#### TestApplication

Individual test applications with comprehensive applicant information.

```python
# Create test application
test_application = TestApplication.objects.create(
    test_session=test_session,
    application_number="LT-2024-000789",
    potential_student=potential_student,
    application_status=ApplicationStatus.PENDING_PAYMENT,
    intended_program=IntendedProgram.BACHELOR_DEGREE,
    english_background={
        "years_studied": 8,
        "previous_courses": ["High school English", "Private tutoring"],
        "self_assessment": "Intermediate",
        "specific_needs": "Improvement in academic writing"
    },
    contact_preference=ContactMethod.EMAIL,
    emergency_contact={
        "name": "Meng Chan",
        "relationship": "Parent",
        "phone": "+855 11 234 567"
    },
    submitted_at=timezone.now()
)
```

### Student Management

#### PotentialStudent

Prospective student profiles for test applicants.

```python
# Create potential student profile
potential_student = PotentialStudent.objects.create(
    first_name_eng="Sophea",
    last_name_eng="Chan",
    first_name_local="សុភា",
    last_name_local="ចាន់",
    date_of_birth=date(2000, 5, 15),
    gender=Gender.FEMALE,
    nationality="Cambodian",
    phone_primary="+855 12 345 678",
    email_primary="sophea.chan@example.com",
    address_current={
        "street": "123 Main Street",
        "city": "Siem Reap",
        "province": "Siem Reap",
        "country": "Cambodia"
    },
    education_background={
        "highest_level": "High School",
        "institution": "Siem Reap High School",
        "graduation_year": 2018,
        "gpa": "3.8"
    },
    status=StudentStatus.APPLICANT
)
```

### Payment & Financial

#### TestPayment

Payment processing for test fees with verification workflow.

```python
# Record test payment
test_payment = TestPayment.objects.create(
    potential_student=potential_student,
    test_session=test_session,
    amount=Decimal("25.00"),
    payment_method=PaymentMethod.MOBILE_PAYMENT,
    payment_reference="ABA-PAY-789012345",
    payment_date=date.today(),
    payment_details={
        "provider": "ABA PayWay",
        "transaction_id": "TXN789012345",
        "phone_number": "+855 12 345 678",
        "receipt_number": "RCP-789012"
    },
    verification_status=VerificationStatus.PENDING,
    is_paid=True
)

# Verify payment
test_payment.verify_payment(
    verified_by=finance_staff,
    verification_notes="Payment confirmed via ABA PayWay transaction log",
    verification_date=timezone.now()
)
```

### Testing & Results

#### TestResult

Secure test result recording with score breakdown and placement recommendations.

```python
# Record test results
test_result = TestResult.objects.create(
    test_application=test_application,
    test_session=test_session,
    test_date=date(2024, 7, 20),
    raw_score=Decimal("78.5"),
    scaled_score=Decimal("82.0"),
    placement_level=PlacementLevel.INTERMEDIATE_1,
    score_breakdown={
        "listening": 75,
        "reading": 82,
        "grammar": 85,
        "vocabulary": 72,
        "writing": 80
    },
    test_duration_minutes=165,
    scored_by=test_administrator,
    scoring_date=date(2024, 7, 21),
    verified=True,
    placement_recommendation={
        "recommended_course": "GESL-04",
        "alternative_options": ["GESL-03 with support", "GESL-05 with placement"],
        "additional_notes": "Strong performance in grammar and reading"
    }
)
```

## Services

### Test Registration Service

Complete test registration workflow with validation and processing.

```python
from apps.level_testing.services import TestRegistrationService

# Process complete test registration
registration_result = TestRegistrationService.process_registration(
    registration_data={
        'personal_info': {
            'first_name_eng': 'Sophea',
            'last_name_eng': 'Chan',
            'date_of_birth': '2000-05-15',
            'phone': '+855 12 345 678',
            'email': 'sophea.chan@example.com'
        },
        'test_preferences': {
            'test_session_id': 123,
            'intended_program': 'bachelor_degree',
            'english_background': 'intermediate'
        },
        'payment_info': {
            'payment_method': 'mobile_payment',
            'payment_reference': 'ABA-PAY-789012345'
        }
    }
)

# Returns registration outcome
{
    'success': True,
    'application_number': 'LT-2024-000789',
    'potential_student_id': 456,
    'payment_status': 'pending_verification',
    'next_steps': [
        'Payment verification within 24 hours',
        'Confirmation email will be sent',
        'Arrive 15 minutes before test time'
    ],
    'test_details': {
        'date': '2024-07-20',
        'time': '09:00 AM',
        'location': 'Computer Lab A',
        'duration': '3 hours'
    }
}
```

### Duplicate Detection Service

Advanced duplicate detection with name similarity and data analysis.

```python
from apps.level_testing.services import DuplicateDetectionService

# Detect potential duplicate students
duplicate_analysis = DuplicateDetectionService.analyze_potential_duplicates(
    potential_student=new_applicant,
    similarity_threshold=0.8
)

# Returns comprehensive analysis
{
    'has_potential_duplicates': True,
    'matches': [
        {
            'existing_student': existing_student,
            'similarity_score': 0.92,
            'matching_factors': [
                'name_similarity: 0.95',
                'date_of_birth: exact_match',
                'phone_partial_match: 0.85'
            ],
            'recommendation': 'high_probability_duplicate',
            'suggested_action': 'manual_review_required'
        }
    ],
    'auto_merge_eligible': False,
    'manual_review_required': True,
    'confidence_level': 'high'
}

# Merge duplicate records if confirmed
if duplicate_confirmed:
    merge_result = DuplicateDetectionService.merge_student_records(
        primary_student=existing_student,
        duplicate_student=new_applicant,
        merge_strategy='preserve_latest_contact_info'
    )
```

### Fee Calculation Service

Dynamic fee calculation with student type and service differentiation.

```python
from apps.level_testing.fee_service import FeeCalculationService

# Calculate test fee based on student profile
fee_calculation = FeeCalculationService.calculate_test_fee(
    test_type=TestType.ENGLISH_PLACEMENT,
    student_type=StudentType.INTERNATIONAL,
    service_options={
        'rush_processing': False,
        'score_report_copies': 2,
        'result_certification': True
    }
)

# Returns detailed fee breakdown
{
    'base_fee': Decimal('25.00'),
    'international_surcharge': Decimal('10.00'),
    'additional_score_copies': Decimal('5.00'),  # $2.50 each
    'certification_fee': Decimal('5.00'),
    'total_fee': Decimal('45.00'),
    'fee_breakdown': [
        {'item': 'Placement test fee', 'amount': '25.00'},
        {'item': 'International student surcharge', 'amount': '10.00'},
        {'item': 'Additional score report copies (2)', 'amount': '5.00'},
        {'item': 'Result certification', 'amount': '5.00'}
    ],
    'payment_options': ['cash', 'bank_transfer', 'mobile_payment'],
    'due_date': '2024-07-18'
}
```

## Views & Forms

### Multi-Step Registration Wizard

Progressive form wizard with validation and session management.

```python
from apps.level_testing.views import TestRegistrationWizardView

class TestRegistrationWizard(TestRegistrationWizardView):
    template_name = 'level_testing/wizard_step.html'

    step_forms = [
        ('personal_info', PersonalInformationForm),
        ('test_preferences', TestPreferencesForm),
        ('payment', PaymentInformationForm),
        ('review', ApplicationReviewForm)
    ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add step-specific context
        if self.steps.current == 'payment':
            # Calculate fees for payment step
            fee_info = self.calculate_application_fees()
            context['fee_breakdown'] = fee_info

        elif self.steps.current == 'review':
            # Compile all form data for review
            context['application_summary'] = self.compile_application_data()

        return context

    def done(self, form_list, **kwargs):
        # Process completed application
        return self.process_complete_application(form_list)
```

### Staff Administration Interface

Comprehensive admin interface for test management and processing.

```python
class StaffTestDashboardView(StaffRequiredMixin, TemplateView):
    template_name = 'level_testing/staff/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update({
            'pending_applications': self.get_pending_applications(),
            'payment_processing': self.get_payments_needing_verification(),
            'upcoming_sessions': self.get_upcoming_test_sessions(),
            'duplicate_alerts': self.get_duplicate_detection_alerts(),
            'daily_statistics': self.get_daily_stats()
        })

        return context
```

## Management Commands

### Test Administration

```bash
# Generate test sessions for upcoming month
python manage.py generate_test_sessions --month=august --capacity=30

# Process pending payments
python manage.py process_pending_payments --verify-all

# Send test reminders
python manage.py send_test_reminders --days-before=2

# Generate test materials
python manage.py generate_test_materials --session-id=123
```

### Data Management

```bash
# Import legacy test data
python manage.py import_legacy_test_data --file=test_results.csv --validate

# Clean duplicate potential students
python manage.py clean_duplicate_students --similarity-threshold=0.9

# Generate fee reports
python manage.py generate_test_fee_report --month=july --format=excel

# Archive completed applications
python manage.py archive_completed_applications --older-than=180-days
```

### Reporting & Analytics

```bash
# Generate placement statistics
python manage.py generate_placement_statistics --year=2024

# Create test performance reports
python manage.py generate_performance_reports --session-id=123

# Export test results
python manage.py export_test_results --format=csv --date-range="2024-07-01,2024-07-31"
```

## API Endpoints

### Test Registration API

```python
# Check test session availability
GET /api/level-testing/sessions/available/

{
    "available_sessions": [
        {
            "id": 123,
            "session_name": "English Placement Test - July 2024",
            "date": "2024-07-20",
            "time": "09:00 AM",
            "duration": "3 hours",
            "capacity": 30,
            "registered": 18,
            "available_spots": 12,
            "fee": "25.00",
            "registration_deadline": "2024-07-18"
        }
    ]
}

# Submit test application
POST /api/level-testing/applications/
{
    "test_session_id": 123,
    "personal_info": {
        "first_name_eng": "Sophea",
        "last_name_eng": "Chan",
        "date_of_birth": "2000-05-15",
        "phone": "+855 12 345 678",
        "email": "sophea.chan@example.com"
    },
    "test_preferences": {
        "intended_program": "bachelor_degree",
        "english_background": "intermediate"
    }
}
```

### Payment Processing API

```python
# Submit payment information
POST /api/level-testing/payments/
{
    "application_id": 456,
    "payment_method": "mobile_payment",
    "payment_reference": "ABA-PAY-789012345",
    "amount": "25.00",
    "payment_details": {
        "provider": "ABA PayWay",
        "transaction_id": "TXN789012345"
    }
}

# Check payment status
GET /api/level-testing/payments/{payment_id}/status/

{
    "payment_id": 789,
    "status": "verified",
    "amount": "25.00",
    "payment_date": "2024-07-15",
    "verification_date": "2024-07-15",
    "receipt_available": true,
    "application_status": "confirmed"
}
```

### Test Results API

```python
# Submit test results (staff only)
POST /api/level-testing/results/
{
    "application_id": 456,
    "test_session_id": 123,
    "raw_score": "78.5",
    "score_breakdown": {
        "listening": 75,
        "reading": 82,
        "grammar": 85,
        "vocabulary": 72,
        "writing": 80
    },
    "placement_recommendation": "INTERMEDIATE_1"
}

# Get test results
GET /api/level-testing/results/{application_id}/

{
    "application_number": "LT-2024-000789",
    "student_name": "Sophea Chan",
    "test_date": "2024-07-20",
    "overall_score": "78.5",
    "placement_level": "INTERMEDIATE_1",
    "recommended_course": "GESL-04",
    "score_breakdown": {
        "listening": 75,
        "reading": 82,
        "grammar": 85,
        "vocabulary": 72,
        "writing": 80
    },
    "next_steps": [
        "Register for GESL-04 course",
        "Contact academic advisor",
        "Complete enrollment application"
    ]
}
```

## Integration Examples

### With Finance App

```python
# Create test fee charge in finance system
def create_test_fee_transaction(test_payment):
    from apps.finance.services import FinanceService

    # Create service charge in finance system
    finance_transaction = FinanceService.create_service_charge(
        customer_type='potential_student',
        customer_id=test_payment.potential_student.id,
        service_type='placement_test',
        amount=test_payment.amount,
        description=f"Placement test fee - {test_payment.test_session.session_name}",
        due_date=test_payment.test_session.registration_deadline,
        payment_reference=test_payment.payment_reference
    )

    # Link to test payment
    test_payment.finance_transaction_id = finance_transaction.id
    test_payment.save()

    return finance_transaction
```

### With Language App

```python
# Set initial language level based on placement test
def apply_placement_test_results(test_result):
    from apps.language.services import LevelManagementService

    # Convert potential student to enrolled student if needed
    if test_result.test_application.potential_student.status == StudentStatus.ENROLLED:
        student = convert_potential_to_enrolled_student(
            test_result.test_application.potential_student
        )

        # Set initial language level
        LevelManagementService.set_initial_level(
            student=student,
            level=test_result.placement_level,
            achievement_method=AchievementMethod.PLACEMENT_TEST,
            assessment_score=test_result.scaled_score,
            notes=f"Placed via placement test. Raw score: {test_result.raw_score}"
        )

        return student
```

### With Enrollment App

```python
# Facilitate enrollment pathway from test results
def create_enrollment_pathway(test_result):
    from apps.enrollment.services import EnrollmentService

    if test_result.placement_level and test_result.placement_recommendation.get('recommended_course'):
        # Find available classes for recommended course
        recommended_course_code = test_result.placement_recommendation['recommended_course']
        available_classes = EnrollmentService.find_available_classes(
            course_code=recommended_course_code,
            term=get_next_registration_term()
        )

        if available_classes:
            # Create enrollment application
            enrollment_application = EnrollmentService.create_enrollment_application(
                potential_student=test_result.test_application.potential_student,
                recommended_classes=available_classes,
                placement_test_result=test_result,
                application_type='placement_based'
            )

            return enrollment_application
```

## Security & Validation

### Data Security

```python
class TestResultSecurity:
    @staticmethod
    def validate_result_modification(user, test_result, proposed_changes):
        """Validate authorization for test result modifications."""
        # Only test administrators can modify results
        if not user.has_permission('level_testing.modify_test_results'):
            raise PermissionDenied("Insufficient permissions to modify test results")

        # Results can only be modified within 48 hours of test date
        if (timezone.now().date() - test_result.test_date).days > 2:
            raise ValidationError("Test results cannot be modified after 48 hours")

        # Score changes require supervisor approval
        if 'raw_score' in proposed_changes or 'scaled_score' in proposed_changes:
            if not user.has_permission('level_testing.approve_score_changes'):
                raise ValidationError("Score changes require supervisor approval")

    @staticmethod
    def audit_test_access(user, test_application, access_type):
        """Log all test-related data access for security auditing."""
        TestAccessLog.objects.create(
            user=user,
            test_application=test_application,
            access_type=access_type,
            ip_address=get_client_ip(),
            timestamp=timezone.now(),
            user_agent=get_user_agent()
        )
```

### Payment Validation

```python
def validate_payment_integrity(test_payment):
    """Comprehensive payment validation."""
    # Validate payment amount matches session fee
    if test_payment.amount != test_payment.test_session.fee_amount:
        raise ValidationError("Payment amount does not match session fee")

    # Check for duplicate payments
    duplicate_payments = TestPayment.objects.filter(
        potential_student=test_payment.potential_student,
        test_session=test_payment.test_session
    ).exclude(id=test_payment.id)

    if duplicate_payments.exists():
        raise ValidationError("Duplicate payment detected for this test session")

    # Validate payment reference format
    if not validate_payment_reference_format(
        test_payment.payment_reference,
        test_payment.payment_method
    ):
        raise ValidationError("Invalid payment reference format")
```

## Performance Optimization

### Duplicate Detection Optimization

```python
# Efficient duplicate detection with database-level operations
def optimized_duplicate_detection(potential_student):
    """Optimized duplicate detection using database filtering."""

    # Use database functions for name similarity
    from django.contrib.postgres.search import TrigramSimilarity

    similar_students = PotentialStudent.objects.annotate(
        name_similarity=TrigramSimilarity('first_name_eng', potential_student.first_name_eng) +
                       TrigramSimilarity('last_name_eng', potential_student.last_name_eng)
    ).filter(
        name_similarity__gt=0.7,  # 70% similarity threshold
        date_of_birth=potential_student.date_of_birth  # Exact DOB match
    ).exclude(
        id=potential_student.id
    )

    return similar_students
```

## Configuration

### Settings

```python
# Level testing configuration
NAGA_LEVEL_TESTING_CONFIG = {
    'DEFAULT_TEST_FEE': Decimal('25.00'),
    'INTERNATIONAL_SURCHARGE': Decimal('10.00'),
    'PAYMENT_VERIFICATION_TIMEOUT_HOURS': 24,
    'TEST_RESULT_MODIFICATION_WINDOW_HOURS': 48,
    'DUPLICATE_DETECTION_THRESHOLD': 0.8,
    'MAX_APPLICATIONS_PER_SESSION': 30
}

# Fee structure
NAGA_TEST_FEES = {
    'ENGLISH_PLACEMENT': {
        'DOMESTIC': Decimal('25.00'),
        'INTERNATIONAL': Decimal('35.00')
    },
    'MATHEMATICS_PLACEMENT': {
        'DOMESTIC': Decimal('20.00'),
        'INTERNATIONAL': Decimal('30.00')
    },
    'RUSH_PROCESSING_FEE': Decimal('15.00'),
    'ADDITIONAL_SCORE_COPY_FEE': Decimal('2.50')
}
```

## Dependencies

### Internal Dependencies

- `people`: Student profile creation and management
- `finance`: Payment processing and fee integration
- `language`: Placement level determination and progression
- `common`: Base models and audit framework

### External Dependencies

- `python-Levenshtein`: Name similarity calculations
- `reportlab`: Test result report generation
- `celery`: Background payment processing

## Architecture Notes

### Design Principles

- **Self-contained workflow**: Complete testing process from registration to results
- **Security-focused**: Comprehensive audit trails and access controls
- **Integration-ready**: Smooth pathways to enrollment and academic systems
- **User-friendly**: Progressive web interface optimized for mobile devices

### Testing Workflow

1. **Registration** → Potential student applies for placement test
2. **Payment** → Fee payment and verification process
3. **Testing** → Test administration and score recording
4. **Results** → Score calculation and placement recommendation
5. **Pathway** → Integration with enrollment and language level systems

### Future Enhancements

- **Computer adaptive testing**: Dynamic test difficulty adjustment
- **Automated scoring**: AI-powered essay and speaking assessment
- **Mobile testing app**: Native mobile application for test taking
- **Blockchain verification**: Immutable test result certification
