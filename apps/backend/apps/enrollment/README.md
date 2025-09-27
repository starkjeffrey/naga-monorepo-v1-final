# Enrollment App

## Overview

The `enrollment` app manages student enrollment in degree programs, class registration, waitlist management, and academic progression tracking. This domain layer app serves as the bridge between students and their academic journey, handling the complex business rules around enrollment eligibility, capacity management, and academic requirements.

## Features

### Program Enrollment Management

- **Degree program enrollment** with major declaration tracking
- **Program change management** with academic credit transfer
- **Enrollment status tracking** with temporal validation
- **Academic progression** monitoring and validation

### Class Registration System

- **Class-level enrollment** with capacity management and waitlisting
- **Component-level enrollment** for language programs with flexible part selection
- **Prerequisites validation** with automated eligibility checking
- **Registration periods** with time-based access control

### Waitlist Management

- **Automated waitlist processing** with priority-based ordering
- **Seat release notifications** with time-limited offers
- **Waitlist analytics** with conversion tracking
- **Multiple waitlist support** for different enrollment types

### Academic Tracking

- **Credit accumulation** with degree progress tracking
- **GPA monitoring** with academic standing updates
- **Graduation requirements** progress tracking
- **Academic holds** management with enrollment restrictions

## Models

### Program Enrollment

#### ProgramEnrollment

Student enrollment in degree programs with academic tracking.

```python
# Enroll student in Bachelor's program
program_enrollment = ProgramEnrollment.objects.create(
    student=student_profile,
    major=business_administration,
    program_level=ProgramLevel.BACHELOR,
    entry_term=fall_2024,
    enrollment_status=EnrollmentStatus.ACTIVE,
    expected_graduation_term=spring_2028
)

# Track academic progress
program_enrollment.update_progress(
    credits_completed=45,
    gpa=Decimal("3.45"),
    requirements_completed=15
)
```

#### MajorDeclaration

Major selection and change tracking with effective dates.

```python
# Declare initial major
declaration = MajorDeclaration.objects.create(
    student=student_profile,
    major=undeclared_major,
    declaration_type=DeclarationType.INITIAL,
    effective_term=fall_2024,
    declared_by=student_user
)

# Change major with tracking
new_declaration = MajorDeclaration.objects.create(
    student=student_profile,
    major=business_administration,
    declaration_type=DeclarationType.CHANGE,
    effective_term=spring_2025,
    previous_declaration=declaration,
    reason="Career interest change"
)
```

### Class Enrollment

#### ClassHeaderEnrollment

Primary class enrollment with comprehensive tracking.

```python
# Enroll student in class
enrollment = ClassHeaderEnrollment.objects.create(
    student=student_profile,
    class_header=english_101_section_a,
    enrollment_type=EnrollmentType.REGULAR,
    status=EnrollmentStatus.ENROLLED,
    enrolled_at=timezone.now(),
    enrolled_by=student_user
)

# Handle enrollment with capacity checking
try:
    enrollment = EnrollmentService.enroll_student(
        student=student_profile,
        class_header=class_header,
        check_prerequisites=True,
        check_capacity=True
    )
except EnrollmentCapacityError:
    # Add to waitlist
    waitlist_entry = EnrollmentService.add_to_waitlist(
        student=student_profile,
        class_header=class_header
    )
```

#### ClassPartEnrollment

Component-level enrollment for language programs.

```python
# Enroll in specific class components (IEAP program)
speaking_enrollment = ClassPartEnrollment.objects.create(
    student=student_profile,
    class_part=speaking_component,
    enrollment_type=EnrollmentType.PART_TIME,
    status=EnrollmentStatus.ENROLLED
)

listening_enrollment = ClassPartEnrollment.objects.create(
    student=student_profile,
    class_part=listening_component,
    enrollment_type=EnrollmentType.PART_TIME,
    status=EnrollmentStatus.ENROLLED
)
```

### Waitlist Management

#### WaitlistEntry

Waitlist management with priority ordering and automated processing.

```python
# Add student to waitlist
waitlist_entry = WaitlistEntry.objects.create(
    student=student_profile,
    class_header=popular_class,
    position=5,  # Automatically calculated
    added_at=timezone.now(),
    priority_type=PriorityType.SENIOR,  # Senior students get priority
    notification_sent=False
)

# Process waitlist when seat becomes available
WaitlistService.process_waitlist(
    class_header=popular_class,
    available_seats=1
)
```

## Services

### Enrollment Service

Comprehensive enrollment management with business rule validation.

```python
from apps.enrollment.services import EnrollmentService

# Enroll student with full validation
enrollment_result = EnrollmentService.enroll_student_with_validation(
    student=student_profile,
    class_header=class_header,
    options={
        'check_prerequisites': True,
        'check_capacity': True,
        'check_time_conflicts': True,
        'check_academic_standing': True
    }
)

if enrollment_result.success:
    enrollment = enrollment_result.enrollment
    print(f"Successfully enrolled {student_profile.full_name}")
else:
    for error in enrollment_result.errors:
        print(f"Enrollment failed: {error}")
```

### Program Enrollment Service

Degree program enrollment with major management.

```python
from apps.enrollment.services import ProgramEnrollmentService

# Enroll student in degree program
program_enrollment = ProgramEnrollmentService.enroll_in_program(
    student=student_profile,
    program_data={
        'major': business_administration,
        'program_level': ProgramLevel.BACHELOR,
        'entry_term': fall_2024,
        'specialization': 'Marketing'
    }
)

# Change major with credit evaluation
change_result = ProgramEnrollmentService.change_major(
    student=student_profile,
    new_major=computer_science,
    effective_term=spring_2025,
    evaluate_credits=True
)
```

### Waitlist Service

Automated waitlist processing with notification management.

```python
from apps.enrollment.services import WaitlistService

# Process all waitlists for available seats
processed_count = WaitlistService.process_all_waitlists(
    term=current_term,
    send_notifications=True
)

# Get waitlist statistics
stats = WaitlistService.get_waitlist_statistics(
    class_header=popular_class
)
# Returns: {
#     'total_waitlisted': 15,
#     'average_wait_time': '3.2 days',
#     'conversion_rate': 0.85,
#     'current_position_range': (1, 15)
# }
```

## Management Commands

### Enrollment Operations

```bash
# Process registration for upcoming term
python manage.py process_registration --term=spring2025 --priority=seniors

# Import enrollments from legacy system
python manage.py import_legacy_enrollments --file=enrollments.csv --validate

# Generate program enrollments for current students
python manage.py generate_program_enrollments --academic-year=2024

# Fix enrollment statuses based on academic rules
python manage.py fix_enrollment_statuses --term=current
```

### Waitlist Management

```bash
# Process all waitlists
python manage.py process_waitlists --send-notifications

# Clean expired waitlist entries
python manage.py clean_expired_waitlists --days=30

# Generate waitlist reports
python manage.py generate_waitlist_reports --term=current --format=csv
```

### Academic Progression

```bash
# Update graduation timelines
python manage.py update_graduation_timelines --recalculate

# Generate academic standing reports
python manage.py generate_academic_standing --term=current

# Check graduation eligibility
python manage.py check_graduation_eligibility --term=spring2025
```

## API Endpoints

### Enrollment Management API

```python
# Enroll student in class
POST /api/enrollment/classes/{class_id}/enroll/
{
    "student_id": 123,
    "enrollment_type": "regular",
    "check_prerequisites": true
}

# Response
{
    "success": true,
    "enrollment": {
        "id": 456,
        "status": "enrolled",
        "enrolled_at": "2024-07-15T10:30:00Z",
        "waitlist_position": null
    }
}

# Or if class is full
{
    "success": false,
    "error": "class_full",
    "waitlist_entry": {
        "position": 5,
        "estimated_notification": "2024-07-20T00:00:00Z"
    }
}
```

### Program Enrollment API

```python
# Get student program enrollment
GET /api/enrollment/students/{student_id}/programs/

{
    "programs": [
        {
            "id": 123,
            "major": "Business Administration",
            "program_level": "bachelor",
            "entry_term": "Fall 2024",
            "status": "active",
            "progress": {
                "credits_completed": 45,
                "credits_required": 120,
                "gpa": "3.45",
                "expected_graduation": "Spring 2028"
            }
        }
    ]
}
```

### Waitlist API

```python
# Get waitlist status
GET /api/enrollment/students/{student_id}/waitlists/

{
    "waitlist_entries": [
        {
            "class": "ACCT-101 Section A",
            "position": 3,
            "added_at": "2024-07-10T14:20:00Z",
            "estimated_notification": "2024-07-18T00:00:00Z",
            "priority_type": "senior"
        }
    ]
}
```

## Policies & Business Rules

### Enrollment Policies

Configurable business rules for enrollment validation.

```python
from apps.enrollment.policies.enrollment_policies import EnrollmentPolicy

class StandardEnrollmentPolicy(EnrollmentPolicy):
    def can_enroll(self, student, class_header):
        """Comprehensive enrollment eligibility check."""
        checks = [
            self.check_academic_standing(student),
            self.check_prerequisites(student, class_header.course),
            self.check_time_conflicts(student, class_header),
            self.check_capacity(class_header),
            self.check_enrollment_period(class_header.term)
        ]

        return all(checks)

    def get_enrollment_restrictions(self, student):
        """Get any restrictions preventing enrollment."""
        restrictions = []

        if student.academic_standing == AcademicStanding.PROBATION:
            restrictions.append("Student on academic probation - limited enrollment")

        if student.has_financial_hold:
            restrictions.append("Financial hold prevents enrollment")

        return restrictions
```

### Capacity Policies

Smart capacity management with priority systems.

```python
class CapacityPolicy:
    def can_enroll_despite_capacity(self, student, class_header):
        """Check if student can enroll even if class appears full."""
        # Senior students get priority registration
        if student.classification == StudentClassification.SENIOR:
            return True

        # Program requirement courses get expanded capacity
        if self.is_required_course(student, class_header.course):
            return True

        # Honor students get priority
        if student.gpa >= Decimal("3.5"):
            return True

        return False
```

## Validation & Constraints

### Enrollment Validation

```python
def validate_enrollment_eligibility(student, class_header):
    """Comprehensive enrollment validation."""
    errors = []

    # Check academic standing
    if student.academic_standing in [AcademicStanding.SUSPENDED, AcademicStanding.DISMISSED]:
        errors.append("Student not in good academic standing")

    # Check prerequisites
    missing_prereqs = get_missing_prerequisites(student, class_header.course)
    if missing_prereqs:
        errors.append(f"Missing prerequisites: {missing_prereqs}")

    # Check time conflicts
    conflicts = check_schedule_conflicts(student, class_header)
    if conflicts:
        errors.append(f"Schedule conflicts: {conflicts}")

    # Check enrollment limits
    current_credits = get_enrolled_credits(student, class_header.term)
    if current_credits + class_header.course.credits > MAX_CREDITS_PER_TERM:
        errors.append("Exceeds maximum credits per term")

    return errors

def validate_program_enrollment(student, program_data):
    """Validate program enrollment requirements."""
    # Check admission requirements
    if not meets_admission_requirements(student, program_data['major']):
        raise ValidationError("Does not meet admission requirements")

    # Check if already enrolled in similar program
    existing_enrollment = ProgramEnrollment.objects.filter(
        student=student,
        program_level=program_data['program_level'],
        enrollment_status=EnrollmentStatus.ACTIVE
    ).exists()

    if existing_enrollment:
        raise ValidationError("Already enrolled in program at this level")
```

## Integration Examples

### With Academic App

```python
# Check degree progress when enrolling
def enroll_with_degree_progress_check(student, class_header):
    from apps.academic.services import AcademicService

    # Check if course fulfills degree requirements
    fulfillment_info = AcademicService.check_requirement_fulfillment(
        student=student,
        course=class_header.course
    )

    # Enroll with fulfillment tracking
    enrollment = EnrollmentService.enroll_student(student, class_header)

    if fulfillment_info.fulfills_requirement:
        AcademicService.mark_requirement_fulfilled(
            student=student,
            requirement=fulfillment_info.requirement,
            course=class_header.course
        )

    return enrollment
```

### With Finance App

```python
# Check financial eligibility before enrollment
def enroll_with_financial_check(student, class_header):
    from apps.finance.services import FinanceService

    # Check for financial holds
    financial_status = FinanceService.get_student_financial_status(student)

    if financial_status.has_holds:
        raise EnrollmentError("Student has financial holds preventing enrollment")

    # Calculate tuition for enrollment
    tuition_amount = FinanceService.calculate_course_tuition(
        student=student,
        course=class_header.course
    )

    # Create enrollment
    enrollment = EnrollmentService.enroll_student(student, class_header)

    # Generate tuition charge
    FinanceService.create_tuition_charge(
        student=student,
        enrollment=enrollment,
        amount=tuition_amount
    )

    return enrollment
```

### With Scheduling App

```python
# Enroll with automatic schedule optimization
def enroll_with_schedule_optimization(student, preferred_classes):
    from apps.scheduling.services import SchedulingService

    # Find optimal schedule avoiding conflicts
    optimal_schedule = SchedulingService.find_optimal_schedule(
        student=student,
        preferred_classes=preferred_classes,
        max_credits=18
    )

    enrollments = []
    for class_header in optimal_schedule.classes:
        enrollment = EnrollmentService.enroll_student(student, class_header)
        enrollments.append(enrollment)

    return enrollments
```

## Testing

### Test Coverage

```bash
# Run enrollment app tests
pytest apps/enrollment/

# Test specific functionality
pytest apps/enrollment/tests/test_enrollment_policies.py
pytest apps/enrollment/tests/test_waitlist_processing.py
pytest apps/enrollment/tests/test_capacity_management.py
```

### Test Factories

```python
from apps.enrollment.tests.factories import (
    ProgramEnrollmentFactory,
    ClassHeaderEnrollmentFactory,
    MajorDeclarationFactory,
    WaitlistEntryFactory
)

# Create test enrollment data
program_enrollment = ProgramEnrollmentFactory(
    student__person__first_name_eng="Test",
    major__name="Computer Science"
)

class_enrollment = ClassHeaderEnrollmentFactory(
    student=program_enrollment.student,
    status=EnrollmentStatus.ENROLLED
)
```

## Performance Optimization

### Query Optimization

```python
# Efficient enrollment queries with relationships
def get_student_enrollments(student, term):
    return ClassHeaderEnrollment.objects.filter(
        student=student,
        class_header__term=term
    ).select_related(
        'class_header__course',
        'class_header__term',
        'class_header__room'
    ).prefetch_related(
        'class_header__classheaderteacher_set__teacher'
    )
```

### Batch Operations

```python
def bulk_enroll_students(student_class_pairs):
    """Efficiently enroll multiple students in multiple classes."""
    enrollments = []

    for student, class_header in student_class_pairs:
        enrollment = ClassHeaderEnrollment(
            student=student,
            class_header=class_header,
            status=EnrollmentStatus.ENROLLED,
            enrolled_at=timezone.now()
        )
        enrollments.append(enrollment)

    # Bulk create for performance
    ClassHeaderEnrollment.objects.bulk_create(enrollments, batch_size=100)
```

## Configuration

### Settings

```python
# Enrollment configuration
NAGA_ENROLLMENT_CONFIG = {
    'MAX_CREDITS_PER_TERM': 18,
    'MAX_COURSES_PER_TERM': 6,
    'ALLOW_OVERLOAD_ENROLLMENT': True,
    'OVERLOAD_CREDIT_LIMIT': 21,
    'WAITLIST_EXPIRATION_HOURS': 72,
    'AUTOMATIC_WAITLIST_PROCESSING': True,
    'ENROLLMENT_NOTIFICATION_ENABLED': True
}

# Registration periods
NAGA_REGISTRATION_CONFIG = {
    'EARLY_REGISTRATION_DAYS': 7,  # Senior priority period
    'REGISTRATION_PERIOD_DAYS': 14,
    'LATE_REGISTRATION_DAYS': 5,
    'ADD_DROP_PERIOD_DAYS': 10
}
```

## Dependencies

### Internal Dependencies

- `people`: Student profiles and academic information
- `curriculum`: Course definitions and prerequisites
- `scheduling`: Class schedules and capacity information
- `academic`: Degree requirements and progress tracking

### External Dependencies

- No external dependencies required

## Architecture Notes

### Design Principles

- **Domain layer focus**: Core enrollment logic without UI concerns
- **Business rule driven**: Configurable policies for enrollment validation
- **Event-driven notifications**: Asynchronous processing for waitlists
- **Audit trail**: Complete enrollment history tracking

### Key Design Patterns

- **Strategy pattern**: Pluggable enrollment policies
- **Observer pattern**: Enrollment event notifications
- **Command pattern**: Enrollment operations with undo capability
- **State machine**: Enrollment status transitions

### Future Enhancements

- **Machine learning waitlist prediction**: AI-powered wait time estimation
- **Mobile registration**: Native mobile app for course registration
- **Real-time seat availability**: WebSocket-based live updates
- **Advanced scheduling**: AI-powered optimal schedule generation
