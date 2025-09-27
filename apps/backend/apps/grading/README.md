# Grading App

## Overview

The `grading` app manages comprehensive grade recording, GPA calculations, academic standing determination, and grade reporting for the Naga SIS. This business logic layer app provides secure grade management with audit trails, automated calculations, and integration with academic policies and external systems.

## Features

### Comprehensive Grade Management

- **Multi-component grading** with weighted class parts (exams, assignments, participation)
- **Flexible grading scales** supporting letter grades, percentage, and pass/fail systems
- **Grade validation** with range checking and policy enforcement
- **Grade history tracking** with complete audit trail of all changes

### Automated GPA Calculations

- **Real-time GPA computation** with term and cumulative calculations
- **Multiple GPA types** (institutional, transfer, major-specific)
- **Credit hour weighting** with accurate decimal precision
- **Academic standing determination** based on configurable thresholds

### Grade Security & Auditing

- **Role-based grade access** with teacher-specific authorization
- **Change tracking** with before/after values and justification requirements
- **Grade finalization** with lockdown periods and override capabilities
- **Comprehensive audit logs** for compliance and security

### Reporting & Analytics

- **Grade distribution analysis** with statistical reporting
- **Academic performance trends** across terms and programs
- **Early intervention alerts** for at-risk students
- **Institutional reporting** for accreditation and compliance

## Models

### Core Grading

#### GradingScale

Configurable grading scales with letter grade mappings.

```python
# Create standard grading scale
standard_scale = GradingScale.objects.create(
    name="Standard Letter Grade Scale",
    scale_type=ScaleType.LETTER_GRADE,
    description="Traditional A-F letter grading with plus/minus",
    is_default=True,
    is_active=True
)

# Define grade mappings
grade_mappings = [
    {"letter": "A+", "min_percentage": 97.0, "max_percentage": 100.0, "gpa_points": 4.0},
    {"letter": "A", "min_percentage": 93.0, "max_percentage": 96.9, "gpa_points": 4.0},
    {"letter": "A-", "min_percentage": 90.0, "max_percentage": 92.9, "gpa_points": 3.7},
    {"letter": "B+", "min_percentage": 87.0, "max_percentage": 89.9, "gpa_points": 3.3},
    {"letter": "B", "min_percentage": 83.0, "max_percentage": 86.9, "gpa_points": 3.0},
    {"letter": "B-", "min_percentage": 80.0, "max_percentage": 82.9, "gpa_points": 2.7},
    {"letter": "C+", "min_percentage": 77.0, "max_percentage": 79.9, "gpa_points": 2.3},
    {"letter": "C", "min_percentage": 73.0, "max_percentage": 76.9, "gpa_points": 2.0},
    {"letter": "C-", "min_percentage": 70.0, "max_percentage": 72.9, "gpa_points": 1.7},
    {"letter": "D", "min_percentage": 60.0, "max_percentage": 69.9, "gpa_points": 1.0},
    {"letter": "F", "min_percentage": 0.0, "max_percentage": 59.9, "gpa_points": 0.0}
]

for mapping in grade_mappings:
    GradeMapping.objects.create(
        grading_scale=standard_scale,
        **mapping
    )
```

#### ClassPartGrade

Individual grades for specific class components.

```python
# Record midterm exam grade
midterm_grade = ClassPartGrade.objects.create(
    enrollment=student_enrollment,
    class_part=midterm_exam_part,
    numeric_score=Decimal("87.5"),
    letter_grade="B+",
    gpa_points=Decimal("3.3"),
    grading_scale=standard_scale,
    recorded_date=date.today(),
    recorded_by=teacher_user,
    status=GradeStatus.RECORDED,
    comments="Strong performance on analytical questions"
)

# Handle late grade update
midterm_grade.update_grade(
    new_numeric_score=Decimal("89.0"),
    new_letter_grade="B+",
    updated_by=teacher_user,
    reason="Calculation error correction",
    change_type=GradeChangeType.CORRECTION
)
```

#### ClassSessionGrade

Composite grades for complete class sessions.

```python
# Calculate session grade from components
session_grade = ClassSessionGrade.objects.create(
    enrollment=student_enrollment,
    class_session=class_session,
    calculated_score=Decimal("85.3"),
    letter_grade="B",
    gpa_points=Decimal("3.0"),
    credits_earned=Decimal("3.0"),
    grade_status=GradeStatus.FINAL,
    calculation_method=CalculationMethod.WEIGHTED_AVERAGE,
    finalized_date=date.today(),
    finalized_by=teacher_user
)
```

### GPA Management

#### GPARecord

Term and cumulative GPA tracking with detailed calculations.

```python
# Calculate term GPA
term_gpa = GPARecord.objects.create(
    student=student_profile,
    term=fall_2024,
    gpa_type=GPAType.TERM,
    gpa_value=Decimal("3.45"),
    total_credits=Decimal("15.0"),
    quality_points=Decimal("51.75"),
    courses_completed=5,
    calculation_date=date.today(),
    is_official=True
)

# Calculate cumulative GPA
cumulative_gpa = GPARecord.objects.create(
    student=student_profile,
    term=fall_2024,
    gpa_type=GPAType.CUMULATIVE,
    gpa_value=Decimal("3.23"),
    total_credits=Decimal("45.0"),
    quality_points=Decimal("145.35"),
    courses_completed=15,
    calculation_date=date.today(),
    is_official=True
)
```

#### AcademicStanding

Academic standing determination with policy enforcement.

```python
# Determine academic standing
academic_standing = AcademicStanding.objects.create(
    student=student_profile,
    term=fall_2024,
    standing=StandingType.GOOD_STANDING,
    cumulative_gpa=Decimal("3.23"),
    term_gpa=Decimal("3.45"),
    credits_completed=Decimal("45.0"),
    standing_date=date.today(),
    notes="Student maintaining satisfactory academic progress",
    next_review_date=date(2025, 1, 15)
)

# Handle probation case
probation_standing = AcademicStanding.objects.create(
    student=at_risk_student,
    term=fall_2024,
    standing=StandingType.PROBATION,
    cumulative_gpa=Decimal("1.85"),
    term_gpa=Decimal("2.1"),
    conditions=[
        "Must achieve 2.5 GPA in next term",
        "Required to meet with academic advisor monthly",
        "Limited to 12 credit hours maximum"
    ],
    probation_start_date=date.today(),
    review_date=date(2025, 1, 15)
)
```

### Audit & History

#### GradeChangeHistory

Complete audit trail of all grade modifications.

```python
# Automatic change tracking
change_record = GradeChangeHistory.objects.create(
    class_part_grade=midterm_grade,
    change_type=GradeChangeHistory.ChangeType.CORRECTION,
    previous_numeric_score=Decimal("87.5"),
    new_numeric_score=Decimal("89.0"),
    previous_letter_grade="B+",
    new_letter_grade="B+",
    changed_by=teacher_user,
    change_date=timezone.now(),
    reason="Calculation error correction",
    ip_address="192.168.1.100",
    additional_context={
        "original_calculation": "87.5",
        "corrected_calculation": "89.0",
        "error_type": "arithmetic_mistake"
    }
)
```

## Services

### Grading Service

Comprehensive grade management with validation and calculation.

```python
from apps.grading.services import GradingService

# Record class part grade with validation
grade_result = GradingService.record_class_part_grade(
    enrollment=student_enrollment,
    class_part=midterm_exam,
    grade_data={
        'numeric_score': Decimal('87.5'),
        'comments': 'Strong analytical skills demonstrated',
        'recorded_by': teacher_user
    },
    validation_options={
        'check_authorization': True,
        'validate_score_range': True,
        'require_finalization': False
    }
)

if grade_result.success:
    # Automatically trigger session grade calculation
    session_result = GradingService.calculate_session_grade(
        enrollment=student_enrollment,
        class_session=class_session
    )
```

### GPA Calculation Service

Accurate GPA calculations with multiple precision handling.

```python
from apps.grading.gpa import GPACalculationService

# Calculate comprehensive GPA report
gpa_report = GPACalculationService.calculate_comprehensive_gpa(
    student=student_profile,
    through_term=fall_2024,
    include_transfer_credits=True,
    include_repeated_courses=True
)

# Returns detailed GPA breakdown
{
    'term_gpa': {
        'value': Decimal('3.45'),
        'credits': Decimal('15.0'),
        'quality_points': Decimal('51.75')
    },
    'cumulative_gpa': {
        'value': Decimal('3.23'),
        'credits': Decimal('45.0'),
        'quality_points': Decimal('145.35')
    },
    'major_gpa': {
        'value': Decimal('3.67'),
        'credits': Decimal('24.0'),
        'quality_points': Decimal('88.08')
    },
    'academic_standing': 'good_standing',
    'credits_for_graduation': Decimal('75.0'),  # Remaining
    'projected_graduation_gpa': Decimal('3.35')
}
```

### Grade Validation Service

Comprehensive grade validation with policy enforcement.

```python
from apps.grading.services import GradeValidationService

# Validate grade entry
validation_result = GradeValidationService.validate_grade_entry(
    teacher=teacher_user,
    enrollment=student_enrollment,
    class_part=assignment_part,
    proposed_grade={
        'numeric_score': Decimal('95.0'),
        'letter_grade': 'A'
    }
)

# Returns validation details
{
    'is_valid': True,
    'authorization_passed': True,
    'score_in_range': True,
    'grading_period_open': True,
    'validation_errors': [],
    'warnings': [],
    'grade_policy_compliance': True
}
```

## Management Commands

### Grade Processing

```bash
# Calculate GPA for all students for a term
python manage.py calculate_term_gpa --term=fall2024

# Update academic standing
python manage.py update_academic_standing --term=fall2024

# Finalize grades for term
python manage.py finalize_term_grades --term=fall2024 --confirm

# Import grades from external system
python manage.py import_grades --file=grades.csv --term=fall2024
```

### Grade Administration

```bash
# Setup grading scales
python manage.py setup_grading_scales

# Load grading scales from legacy system
python manage.py load_v0_grading_scales --validate

# Generate grade reports
python manage.py generate_grade_reports --term=fall2024 --format=pdf

# Audit grade changes
python manage.py audit_grade_changes --term=fall2024 --suspicious-only
```

### Academic Standing

```bash
# Calculate academic standing for all students
python manage.py calculate_academic_standing --term=fall2024

# Generate probation letters
python manage.py generate_probation_letters --term=fall2024

# Update dean's list
python manage.py update_deans_list --term=fall2024 --gpa-threshold=3.5
```

## API Endpoints

### Grade Management API

```python
# Record class part grade
POST /api/grading/class-parts/{class_part_id}/grades/
{
    "enrollment_id": 123,
    "numeric_score": "87.5",
    "comments": "Strong performance on analytical questions",
    "grade_date": "2024-07-15"
}

# Response
{
    "grade_id": 456,
    "status": "recorded",
    "calculated_letter_grade": "B+",
    "gpa_points": "3.3",
    "session_grade_updated": true,
    "gpa_recalculated": true
}

# Update existing grade
PUT /api/grading/grades/{grade_id}/
{
    "numeric_score": "89.0",
    "reason": "Calculation error correction",
    "change_type": "correction"
}
```

### GPA Information API

```python
# Get student GPA summary
GET /api/grading/students/{student_id}/gpa/

{
    "student": {
        "id": 123,
        "name": "Sophea Chan",
        "program": "Bachelor of Business Administration"
    },
    "current_gpa": {
        "term_gpa": "3.45",
        "cumulative_gpa": "3.23",
        "major_gpa": "3.67",
        "credits_completed": "45.0",
        "quality_points": "145.35"
    },
    "academic_standing": {
        "status": "good_standing",
        "effective_date": "2024-07-15",
        "next_review_date": "2025-01-15"
    },
    "gpa_history": [
        {
            "term": "Fall 2024",
            "term_gpa": "3.45",
            "cumulative_gpa": "3.23",
            "credits": "15.0"
        }
    ]
}
```

### Grade Reports API

```python
# Get class grade distribution
GET /api/grading/classes/{class_id}/grade-distribution/

{
    "class_info": {
        "course": "ACCT-101",
        "section": "A",
        "term": "Fall 2024",
        "instructor": "Dr. Smith"
    },
    "grade_distribution": {
        "A": {"count": 5, "percentage": 20.0},
        "B": {"count": 12, "percentage": 48.0},
        "C": {"count": 6, "percentage": 24.0},
        "D": {"count": 2, "percentage": 8.0},
        "F": {"count": 0, "percentage": 0.0}
    },
    "statistics": {
        "class_average": "83.2",
        "median_score": "84.0",
        "standard_deviation": "8.7",
        "highest_score": "97.0",
        "lowest_score": "62.0"
    }
}
```

## Integration Examples

### With Attendance App

```python
# Apply attendance penalties to grades
def apply_attendance_penalty(student, class_part, penalty_percentage):
    from apps.grading.services import GradingService

    # Get current grade
    current_grade = ClassPartGrade.objects.get(
        enrollment__student=student,
        class_part=class_part
    )

    # Calculate penalty
    penalty_amount = current_grade.numeric_score * (penalty_percentage / 100)
    new_score = current_grade.numeric_score - penalty_amount

    # Apply penalty with audit trail
    penalty_result = GradingService.apply_attendance_penalty(
        grade=current_grade,
        penalty_amount=penalty_amount,
        new_score=new_score,
        reason=f"Attendance penalty: {penalty_percentage}% reduction",
        applied_by=system_user
    )

    return penalty_result
```

### With Academic App

```python
# Update degree progress when grades are finalized
def update_degree_progress_on_grade_finalization(student, term):
    from apps.academic.services import AcademicService

    # Get finalized grades for term
    finalized_grades = ClassSessionGrade.objects.filter(
        enrollment__student=student,
        class_session__term=term,
        grade_status=GradeStatus.FINAL
    )

    # Update requirement fulfillments
    for grade in finalized_grades:
        if grade.is_passing_grade():
            AcademicService.mark_course_completed(
                student=student,
                course=grade.class_session.course,
                grade=grade.letter_grade,
                credits_earned=grade.credits_earned,
                completion_term=term
            )

    # Recalculate degree progress
    progress_update = AcademicService.update_degree_progress(
        student=student,
        through_term=term
    )

    return progress_update
```

### With Finance App

```python
# Apply grade-based financial aid adjustments
def apply_grade_based_aid_adjustments(student, term):
    from apps.finance.services import FinanceService
    from apps.scholarships.services import ScholarshipService

    # Check GPA-based scholarship renewals
    current_gpa = GPACalculationService.calculate_term_gpa(student, term)

    if current_gpa.gpa_value < Decimal('3.0'):
        # Suspend merit-based scholarships
        merit_scholarships = ScholarshipService.get_merit_scholarships(student)
        for scholarship in merit_scholarships:
            ScholarshipService.suspend_scholarship(
                scholarship=scholarship,
                reason=f"GPA {current_gpa.gpa_value} below required 3.0",
                effective_term=get_next_term(term)
            )

    # Apply academic standing financial penalties
    standing = AcademicStanding.objects.get(student=student, term=term)
    if standing.standing == StandingType.PROBATION:
        FinanceService.apply_academic_standing_hold(
            student=student,
            hold_type='probation_registration_hold',
            reason='Academic probation - advising required'
        )
```

## Validation & Business Rules

### Grade Validation

```python
def validate_grade_entry(teacher, enrollment, class_part, grade_data):
    """Comprehensive grade entry validation."""
    errors = []

    # Check teacher authorization
    if not can_teacher_grade_class(teacher, enrollment.class_header):
        errors.append("Teacher not authorized to grade this class")

    # Validate grading period
    if not is_grading_period_open(enrollment.class_header.term, class_part):
        errors.append("Grading period is closed for this assignment")

    # Validate score range
    numeric_score = grade_data.get('numeric_score')
    if numeric_score is not None:
        if not (0 <= numeric_score <= 100):
            errors.append("Numeric score must be between 0 and 100")

    # Check for duplicate grade entry
    existing_grade = ClassPartGrade.objects.filter(
        enrollment=enrollment,
        class_part=class_part
    ).first()

    if existing_grade and existing_grade.status == GradeStatus.FINAL:
        errors.append("Grade already finalized for this component")

    return errors

def validate_gpa_calculation(student, term):
    """Validate GPA calculation inputs and business rules."""
    # Check for incomplete grades
    incomplete_grades = ClassSessionGrade.objects.filter(
        enrollment__student=student,
        class_session__term=term,
        grade_status=GradeStatus.INCOMPLETE
    )

    if incomplete_grades.exists():
        raise ValidationError("Cannot calculate GPA with incomplete grades")

    # Validate credit hours
    total_credits = ClassSessionGrade.objects.filter(
        enrollment__student=student,
        class_session__term=term,
        grade_status=GradeStatus.FINAL
    ).aggregate(total=Sum('credits_earned'))['total']

    if total_credits is None or total_credits <= 0:
        raise ValidationError("No completed credits found for GPA calculation")

    return True
```

## Testing

### Test Coverage

```bash
# Run grading app tests
pytest apps/grading/

# Test specific functionality
pytest apps/grading/tests/test_gpa_calculations.py
pytest apps/grading/tests/test_grade_validation.py
pytest apps/grading/tests/test_academic_standing.py
```

### Test Factories

```python
from apps.grading.tests.factories import (
    GradingScaleFactory,
    ClassPartGradeFactory,
    GPARecordFactory,
    AcademicStandingFactory
)

# Create test grading data
grading_scale = GradingScaleFactory(name="Test Scale")
grade = ClassPartGradeFactory(
    numeric_score=Decimal("87.5"),
    letter_grade="B+"
)
gpa_record = GPARecordFactory(
    gpa_value=Decimal("3.45"),
    total_credits=Decimal("15.0")
)
```

## Performance Optimization

### GPA Calculation Optimization

```python
# Efficient batch GPA calculation
def calculate_batch_gpa(students, term):
    """Calculate GPA for multiple students efficiently."""

    # Pre-fetch all required data
    grade_data = ClassSessionGrade.objects.filter(
        enrollment__student__in=students,
        class_session__term=term,
        grade_status=GradeStatus.FINAL
    ).select_related(
        'enrollment__student',
        'class_session__course'
    ).values(
        'enrollment__student_id',
        'gpa_points',
        'credits_earned'
    )

    # Group by student for efficient calculation
    student_grades = {}
    for grade in grade_data:
        student_id = grade['enrollment__student_id']
        if student_id not in student_grades:
            student_grades[student_id] = []
        student_grades[student_id].append(grade)

    # Calculate GPA for each student
    gpa_records = []
    for student_id, grades in student_grades.items():
        total_points = sum(g['gpa_points'] * g['credits_earned'] for g in grades)
        total_credits = sum(g['credits_earned'] for g in grades)
        gpa_value = total_points / total_credits if total_credits > 0 else Decimal('0.00')

        gpa_records.append(GPARecord(
            student_id=student_id,
            term=term,
            gpa_type=GPAType.TERM,
            gpa_value=gpa_value,
            total_credits=total_credits,
            quality_points=total_points
        ))

    # Bulk create GPA records
    GPARecord.objects.bulk_create(gpa_records)
```

## Configuration

### Settings

```python
# Grading configuration
NAGA_GRADING_CONFIG = {
    'DEFAULT_GRADING_SCALE': 'standard_letter_grade',
    'GPA_DECIMAL_PLACES': 2,
    'ALLOW_GRADE_REPLACEMENT': True,
    'GRADE_REPLACEMENT_POLICY': 'latest_attempt',
    'ACADEMIC_STANDING_THRESHOLDS': {
        'GOOD_STANDING': Decimal('2.0'),
        'PROBATION': Decimal('1.5'),
        'SUSPENSION': Decimal('1.0')
    },
    'GRADING_PERIOD_BUFFER_DAYS': 7  # Days after term end for grade entry
}

# Grade security
NAGA_GRADE_SECURITY = {
    'REQUIRE_GRADE_JUSTIFICATION': True,
    'AUDIT_ALL_GRADE_CHANGES': True,
    'ALLOW_GRADE_CORRECTIONS_DAYS': 30,
    'REQUIRE_SUPERVISOR_APPROVAL_FOR_CHANGES': True,
    'LOG_GRADE_ACCESS': True
}
```

## Dependencies

### Internal Dependencies

- `scheduling`: Class part and session information
- `enrollment`: Student enrollment validation
- `people`: Student and teacher profiles
- `curriculum`: Course credit information

### External Dependencies

- No external dependencies required

## Architecture Notes

### Design Principles

- **Precision-focused**: Accurate decimal calculations for GPA and grades
- **Security-first**: Comprehensive audit trails and authorization checks
- **Policy-driven**: Configurable grading scales and academic standing rules
- **Integration-ready**: Seamless connection with academic and financial systems

### Grade Calculation Flow

1. **Component grades** → Individual assignment/exam scores
2. **Session grades** → Weighted combination of component grades
3. **Term GPA** → Credit-weighted average of session grades
4. **Cumulative GPA** → Overall academic performance tracking
5. **Academic standing** → Policy-based status determination

### Future Enhancements

- **Machine learning grade prediction**: Early intervention for at-risk students
- **Blockchain grade verification**: Immutable academic record keeping
- **Advanced analytics**: Grade distribution analysis and trends
- **Mobile grading**: Native mobile app for teachers
