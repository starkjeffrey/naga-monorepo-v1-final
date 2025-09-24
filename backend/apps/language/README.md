# Language App

## Overview

The `language` app manages language-specific course progression, automated student promotion between levels, and specialized language program administration for the Naga SIS. This business logic layer app handles the unique requirements of language education including level-based progression, placement testing integration, and flexible class structures.

## Features

### Language Level Management

- **Standardized level progression** with predefined advancement criteria
- **Flexible level skipping** with approval workflows and validation
- **Cross-program transfers** between language tracks (GESL, IEAP, etc.)
- **Competency-based advancement** beyond traditional semester progression

### Automated Student Promotion

- **Batch promotion processing** with comprehensive eligibility analysis
- **Template-based class creation** for consistent course structure
- **Error handling and reporting** with detailed failure analysis
- **Audit trail** for all promotion decisions and outcomes

### Specialized Course Management

- **Language-specific course templates** with component definitions
- **Level-appropriate content validation** ensuring proper sequencing
- **Multi-skill integration** (speaking, listening, reading, writing)
- **Assessment alignment** with language proficiency standards

### Skip Request Management

- **Student-initiated skip requests** with justification requirements
- **Administrative review workflow** with approval/denial tracking
- **Competency validation** through placement testing integration
- **Academic record maintenance** preserving progression history

## Models

### Core Language Management

#### LanguageLevel

Enumerated language proficiency levels with standardized progression.

```python
from apps.language.enums import LanguageLevel

# Language levels are predefined enum values
beginner_levels = [
    LanguageLevel.BEGINNER_1,      # GESL-01 equivalent
    LanguageLevel.BEGINNER_2,      # GESL-02 equivalent
    LanguageLevel.BEGINNER_3       # GESL-03 equivalent
]

intermediate_levels = [
    LanguageLevel.INTERMEDIATE_1,  # GESL-04 equivalent
    LanguageLevel.INTERMEDIATE_2,  # GESL-05 equivalent
    LanguageLevel.INTERMEDIATE_3   # GESL-06 equivalent
]

advanced_levels = [
    LanguageLevel.ADVANCED_1,      # GESL-07 equivalent
    LanguageLevel.ADVANCED_2,      # GESL-08 equivalent
    LanguageLevel.PROFICIENT       # Academic readiness
]

# Check level progression
def can_advance_to_level(current_level, target_level):
    current_order = current_level.value[1]  # Get numeric order
    target_order = target_level.value[1]
    return target_order == current_order + 1
```

#### StudentLanguageLevel

Tracks individual student progression through language levels.

```python
# Record student's current language level
student_level = StudentLanguageLevel.objects.create(
    student=student_profile,
    current_level=LanguageLevel.INTERMEDIATE_1,
    achieved_date=date(2024, 7, 15),
    achievement_method=AchievementMethod.COURSE_COMPLETION,
    previous_level=LanguageLevel.BEGINNER_3,
    program_type=ProgramType.GESL,
    assessment_score=Decimal("78.5"),
    notes="Successfully completed GESL-03 with strong performance"
)

# Update when student advances
student_level.advance_to_level(
    new_level=LanguageLevel.INTERMEDIATE_2,
    achievement_method=AchievementMethod.COURSE_COMPLETION,
    assessment_score=Decimal("82.0"),
    completion_date=date(2024, 12, 15)
)
```

#### LanguageSkipRequest

Manages requests to skip language levels with approval workflow.

```python
# Student requests to skip a level
skip_request = LanguageSkipRequest.objects.create(
    student=student_profile,
    current_level=LanguageLevel.BEGINNER_2,
    requested_level=LanguageLevel.INTERMEDIATE_1,
    reason="Studied English extensively abroad",
    supporting_evidence="TOEFL score: 85, Previous coursework transcript",
    submitted_date=date.today(),
    status=RequestStatus.PENDING,
    requested_by=student_user
)

# Administrative review
skip_request.process_request(
    reviewed_by=academic_coordinator,
    decision=RequestDecision.APPROVED,
    review_notes="Strong supporting evidence, placement test recommended",
    conditions=[
        "Must pass placement test with 80% minimum",
        "Conditional approval pending first month performance"
    ]
)
```

### Promotion Management

#### PromotionBatch

Batch processing records for student promotions.

```python
# Create promotion batch for term end
promotion_batch = PromotionBatch.objects.create(
    source_term=fall_2024,
    target_term=spring_2025,
    program_code="GESL",
    initiated_by=academic_admin,
    batch_date=date.today(),
    status=BatchStatus.IN_PROGRESS,
    eligibility_criteria={
        "minimum_grade": "C",
        "attendance_threshold": 80,
        "completion_requirement": "all_components"
    }
)

# Process the batch
from apps.language.services import LanguagePromotionService

promotion_result = LanguagePromotionService.execute_promotion(
    source_term=fall_2024,
    target_term=spring_2025,
    program="GESL",
    dry_run=False
)
```

#### PromotionRecord

Individual student promotion tracking with detailed outcomes.

```python
# Record successful promotion
promotion_record = PromotionRecord.objects.create(
    promotion_batch=promotion_batch,
    student=student_profile,
    source_level=LanguageLevel.BEGINNER_2,
    target_level=LanguageLevel.BEGINNER_3,
    source_class=gesl_02_section_a,
    target_class=gesl_03_section_b,
    promotion_status=PromotionStatus.PROMOTED,
    final_grade="B+",
    attendance_percentage=Decimal("92.5"),
    promotion_date=date.today(),
    notes="Strong performance across all components"
)

# Record promotion failure
failed_promotion = PromotionRecord.objects.create(
    promotion_batch=promotion_batch,
    student=struggling_student,
    source_level=LanguageLevel.BEGINNER_1,
    target_level=LanguageLevel.BEGINNER_2,
    source_class=gesl_01_section_c,
    target_class=None,  # No promotion
    promotion_status=PromotionStatus.REPEAT,
    final_grade="D+",
    attendance_percentage=Decimal("65.0"),
    failure_reasons=[
        "Grade below minimum threshold",
        "Attendance below required 80%",
        "Incomplete speaking assessment"
    ],
    notes="Recommend additional support and repeat current level"
)
```

## Services

### Language Promotion Service

Comprehensive promotion management with eligibility analysis and batch processing.

```python
from apps.language.services import LanguagePromotionService

# Analyze promotion eligibility for term
eligibility_analysis = LanguagePromotionService.analyze_promotion_eligibility(
    source_term=fall_2024,
    program="GESL"
)

# Returns detailed analysis
{
    'total_students': 85,
    'eligible_for_promotion': 72,
    'requires_repeat': 8,
    'incomplete_assessments': 5,
    'level_breakdown': {
        'BEGINNER_1_to_BEGINNER_2': {
            'eligible': 18,
            'repeat': 3,
            'incomplete': 1
        },
        'BEGINNER_2_to_BEGINNER_3': {
            'eligible': 15,
            'repeat': 2,
            'incomplete': 1
        }
        # ... additional levels
    },
    'risk_factors': [
        {
            'student': 'John Doe',
            'issue': 'Borderline grade',
            'recommendation': 'Manual review required'
        }
    ]
}

# Execute promotion with comprehensive reporting
promotion_result = LanguagePromotionService.execute_promotion(
    source_term=fall_2024,
    target_term=spring_2025,
    program="GESL",
    create_missing_classes=True,
    dry_run=False
)
```

### Level Management Service

Student level tracking and progression validation.

```python
from apps.language.services import LevelManagementService

# Update student level after course completion
level_update = LevelManagementService.update_student_level(
    student=student_profile,
    completed_course=gesl_02,
    final_grade="B+",
    completion_date=date(2024, 12, 15),
    assessment_data={
        'speaking_score': 82,
        'listening_score': 85,
        'reading_score': 79,
        'writing_score': 81
    }
)

# Validate level skip request
skip_validation = LevelManagementService.validate_skip_request(
    student=student_profile,
    current_level=LanguageLevel.BEGINNER_2,
    target_level=LanguageLevel.INTERMEDIATE_1,
    supporting_evidence="TOEFL score: 85"
)

if skip_validation.is_valid:
    # Process the skip
    skip_result = LevelManagementService.process_level_skip(
        student=student_profile,
        skip_request=skip_request,
        approved_by=academic_coordinator
    )
```

### Template Management Service

Course template management for consistent class structure.

```python
from apps.language.services import TemplateManagementService

# Create class from course template
class_creation_result = TemplateManagementService.create_class_from_template(
    course=gesl_03,
    term=spring_2025,
    section="A",
    teacher=assigned_teacher,
    room=classroom_101
)

if class_creation_result.success:
    new_class = class_creation_result.class_header

    # Validate all required components are created
    required_components = [
        'Speaking Assessment',
        'Listening Assessment',
        'Reading Assessment',
        'Writing Assessment',
        'Participation'
    ]

    created_components = [
        part.name for part in new_class.class_parts.all()
    ]

    missing_components = set(required_components) - set(created_components)
    if missing_components:
        raise ValidationError(f"Missing required components: {missing_components}")
```

## Management Commands

### Promotion Operations

```bash
# Analyze promotion eligibility for term
python manage.py analyze_promotion_eligibility --term=fall2024 --program=GESL

# Execute student promotions
python manage.py execute_promotions --source-term=fall2024 --target-term=spring2025 --program=GESL

# Generate promotion reports
python manage.py generate_promotion_reports --batch-id=123 --format=pdf

# Rollback promotion batch (if needed)
python manage.py rollback_promotion_batch --batch-id=123 --confirm
```

### Level Management

```bash
# Update student levels based on completed courses
python manage.py update_student_levels --term=fall2024

# Process pending skip requests
python manage.py process_skip_requests --review-pending

# Validate level progressions
python manage.py validate_level_progressions --fix-errors

# Generate level distribution reports
python manage.py generate_level_reports --program=GESL --term=current
```

### Template Management

```bash
# Validate course templates
python manage.py validate_course_templates --program=GESL

# Create missing templates
python manage.py create_missing_templates --course-level=all

# Update template structures
python manage.py update_template_structures --version=2024.1
```

## API Endpoints

### Promotion Management API

```python
# Analyze promotion eligibility
GET /api/language/promotion/analyze/?term=fall2024&program=GESL

{
    "analysis_date": "2024-12-20",
    "source_term": "Fall 2024",
    "program": "GESL",
    "summary": {
        "total_students": 85,
        "eligible_for_promotion": 72,
        "requires_repeat": 8,
        "incomplete_assessments": 5,
        "promotion_rate": 84.7
    },
    "level_breakdown": [
        {
            "current_level": "BEGINNER_1",
            "target_level": "BEGINNER_2",
            "eligible_count": 18,
            "repeat_count": 3,
            "promotion_rate": 85.7
        }
    ],
    "at_risk_students": [
        {
            "student_name": "John Doe",
            "current_grade": "C-",
            "attendance": "78%",
            "recommendation": "Manual review required"
        }
    ]
}

# Execute promotion batch
POST /api/language/promotion/execute/
{
    "source_term": "fall2024",
    "target_term": "spring2025",
    "program": "GESL",
    "create_missing_classes": true,
    "dry_run": false
}
```

### Skip Request API

```python
# Submit skip request
POST /api/language/skip-requests/
{
    "student_id": 123,
    "current_level": "BEGINNER_2",
    "requested_level": "INTERMEDIATE_1",
    "reason": "Studied English extensively abroad",
    "supporting_evidence": "TOEFL score: 85, Previous coursework"
}

# Response
{
    "request_id": 456,
    "status": "pending",
    "submitted_date": "2024-07-15",
    "review_timeline": "5-7 business days",
    "required_assessments": [
        "Placement test required",
        "Speaking assessment recommended"
    ]
}

# Get skip request status
GET /api/language/skip-requests/{request_id}/

{
    "request_id": 456,
    "status": "approved",
    "submitted_date": "2024-07-15",
    "reviewed_date": "2024-07-18",
    "reviewed_by": "Academic Coordinator",
    "decision": "approved",
    "conditions": [
        "Must pass placement test with 80% minimum",
        "Conditional approval pending first month performance"
    ],
    "next_steps": [
        "Schedule placement test",
        "Register for INTERMEDIATE_1 course"
    ]
}
```

### Student Level API

```python
# Get student language progression
GET /api/language/students/{student_id}/progression/

{
    "student": {
        "id": 123,
        "name": "Sophea Chan",
        "program": "GESL"
    },
    "current_level": {
        "level": "INTERMEDIATE_1",
        "achieved_date": "2024-07-15",
        "achievement_method": "course_completion",
        "assessment_score": "78.5"
    },
    "progression_history": [
        {
            "level": "BEGINNER_1",
            "start_date": "2024-01-15",
            "completion_date": "2024-05-15",
            "final_grade": "B",
            "duration_days": 120
        },
        {
            "level": "BEGINNER_2",
            "start_date": "2024-06-01",
            "completion_date": "2024-07-15",
            "final_grade": "B+",
            "duration_days": 45
        }
    ],
    "next_level": {
        "target_level": "INTERMEDIATE_2",
        "estimated_completion": "2024-12-15",
        "prerequisites": ["Complete INTERMEDIATE_1 with C or better"]
    }
}
```

## Integration Examples

### With Level Testing App

```python
# Process placement test results for level determination
def process_placement_results(test_application, test_scores):
    from apps.level_testing.services import PlacementService

    # Get placement recommendation
    placement_result = PlacementService.determine_placement_level(
        test_scores=test_scores,
        program_type=ProgramType.GESL
    )

    # Update student language level
    if placement_result.recommended_level:
        LevelManagementService.set_initial_level(
            student=test_application.potential_student,
            level=placement_result.recommended_level,
            achievement_method=AchievementMethod.PLACEMENT_TEST,
            assessment_score=test_scores.overall_score,
            notes=f"Placed via placement test. Score: {test_scores.overall_score}"
        )

    return placement_result
```

### With Enrollment App

```python
# Automatic enrollment in promoted level
def enroll_promoted_students(promotion_batch):
    from apps.enrollment.services import EnrollmentService

    promoted_students = PromotionRecord.objects.filter(
        promotion_batch=promotion_batch,
        promotion_status=PromotionStatus.PROMOTED,
        target_class__isnull=False
    )

    enrollment_results = []
    for promotion in promoted_students:
        try:
            enrollment = EnrollmentService.enroll_student(
                student=promotion.student,
                class_header=promotion.target_class,
                enrollment_type=EnrollmentType.PROMOTED,
                check_prerequisites=False  # Already validated in promotion
            )
            enrollment_results.append({
                'student': promotion.student,
                'enrollment': enrollment,
                'success': True
            })
        except Exception as e:
            enrollment_results.append({
                'student': promotion.student,
                'enrollment': None,
                'success': False,
                'error': str(e)
            })

    return enrollment_results
```

### With Academic App

```python
# Update degree progress for language course completions
def update_language_degree_progress(student, completed_level, final_grade):
    from apps.academic.services import AcademicService

    # Check if completion fulfills language requirements
    if completed_level in [LanguageLevel.ADVANCED_2, LanguageLevel.PROFICIENT]:
        # Student has met English proficiency requirements
        language_requirement = AcademicService.get_language_requirement(
            student=student
        )

        if language_requirement:
            AcademicService.mark_requirement_fulfilled(
                student=student,
                requirement=language_requirement,
                fulfillment_method="language_course_completion",
                evidence=f"Completed {completed_level.name} with grade {final_grade}"
            )

    # Update overall academic progress
    progress_update = AcademicService.update_degree_progress(
        student=student,
        include_language_progress=True
    )

    return progress_update
```

## Validation & Business Rules

### Promotion Validation

```python
def validate_promotion_eligibility(student, source_class, target_level):
    """Validate student eligibility for level promotion."""
    errors = []

    # Check minimum grade requirement
    final_grade = get_final_grade(student, source_class)
    if not final_grade or get_grade_points(final_grade) < 2.0:  # Below C
        errors.append(f"Final grade {final_grade} below minimum C requirement")

    # Check attendance requirement
    attendance_percentage = get_attendance_percentage(student, source_class)
    if attendance_percentage < 80:
        errors.append(f"Attendance {attendance_percentage}% below required 80%")

    # Check component completion
    incomplete_components = get_incomplete_components(student, source_class)
    if incomplete_components:
        errors.append(f"Incomplete components: {', '.join(incomplete_components)}")

    # Validate level progression sequence
    current_level = get_current_level(student)
    if not can_advance_to_level(current_level, target_level):
        errors.append(f"Cannot advance from {current_level} to {target_level}")

    return len(errors) == 0, errors

def validate_skip_request(student, current_level, target_level, evidence):
    """Validate level skip request."""
    # Check maximum skip limit
    level_difference = target_level.value[1] - current_level.value[1]
    if level_difference > MAX_LEVEL_SKIP:
        raise ValidationError(f"Cannot skip more than {MAX_LEVEL_SKIP} levels")

    # Validate supporting evidence
    if not evidence or len(evidence.strip()) < 50:
        raise ValidationError("Detailed supporting evidence required (minimum 50 characters)")

    # Check for recent skip requests
    recent_requests = LanguageSkipRequest.objects.filter(
        student=student,
        submitted_date__gte=date.today() - timedelta(days=90)
    )

    if recent_requests.count() >= 2:
        raise ValidationError("Maximum 2 skip requests per 90-day period")

    return True
```

## Testing

### Test Coverage

```bash
# Run language app tests
pytest apps/language/

# Test specific functionality
pytest apps/language/tests/test_promotion_service.py
pytest apps/language/tests/test_level_management.py
pytest apps/language/tests/test_template_creation.py
```

### Test Factories

```python
from apps.language.tests.factories import (
    StudentLanguageLevelFactory,
    LanguageSkipRequestFactory,
    PromotionBatchFactory,
    PromotionRecordFactory
)

# Create test language data
student_level = StudentLanguageLevelFactory(
    current_level=LanguageLevel.INTERMEDIATE_1,
    assessment_score=Decimal("78.5")
)

skip_request = LanguageSkipRequestFactory(
    current_level=LanguageLevel.BEGINNER_2,
    requested_level=LanguageLevel.INTERMEDIATE_1
)
```

## Performance Optimization

### Batch Processing Optimization

```python
# Efficient promotion processing
def process_promotions_optimized(source_term, target_term, program):
    """Optimized batch promotion processing."""

    # Pre-fetch all required data
    eligible_students = get_eligible_students_with_data(source_term, program)

    # Batch create target classes if needed
    target_classes = create_target_classes_batch(eligible_students, target_term)

    # Process promotions in batches
    promotion_records = []
    for batch in chunk_list(eligible_students, 50):
        batch_records = process_student_batch(batch, target_classes)
        promotion_records.extend(batch_records)

    # Bulk create promotion records
    PromotionRecord.objects.bulk_create(promotion_records)

    return promotion_records

def get_eligible_students_with_data(source_term, program):
    """Efficiently fetch students with all required data."""
    return Student.objects.filter(
        enrollments__class_header__term=source_term,
        enrollments__class_header__course__code__startswith=program
    ).select_related(
        'person', 'program_enrollment'
    ).prefetch_related(
        'enrollments__grades',
        'enrollments__attendance_records',
        'language_levels'
    ).distinct()
```

## Configuration

### Settings

```python
# Language app configuration
NAGA_LANGUAGE_CONFIG = {
    'MAX_LEVEL_SKIP': 3,
    'PROMOTION_MINIMUM_GRADE': 'C',
    'PROMOTION_ATTENDANCE_THRESHOLD': 80,  # Percentage
    'SKIP_REQUEST_REVIEW_DAYS': 7,
    'AUTO_CREATE_TARGET_CLASSES': True,
    'REQUIRE_TEMPLATE_VALIDATION': True
}

# Level progression
NAGA_LEVEL_PROGRESSION = {
    'STANDARD_PROGRESSION_MONTHS': 4,
    'ACCELERATED_PROGRESSION_MONTHS': 2,
    'REMEDIAL_PROGRESSION_MONTHS': 6,
    'ASSESSMENT_SCORE_WEIGHT': 0.4,
    'GRADE_WEIGHT': 0.4,
    'ATTENDANCE_WEIGHT': 0.2
}
```

## Dependencies

### Internal Dependencies

- `curriculum`: Course definitions and templates
- `scheduling`: Class creation and management
- `enrollment`: Student enrollment and progression
- `grading`: Grade validation and calculation

### External Dependencies

- No external dependencies required

## Architecture Notes

### Design Principles

- **Level-based progression**: Clear advancement criteria and validation
- **Template-driven**: Consistent course structure through templates
- **Audit-focused**: Complete tracking of promotions and level changes
- **Automation-friendly**: Batch processing with error handling

### Key Workflows

1. **Level Assessment** → Student completes language course
2. **Eligibility Check** → Automated promotion criteria validation
3. **Batch Processing** → Group promotion with class creation
4. **Enrollment** → Automatic enrollment in next level
5. **Audit Trail** → Complete record of promotion decisions

### Future Enhancements

- **AI-powered placement**: Machine learning for level determination
- **Adaptive learning paths**: Personalized progression recommendations
- **Mobile assessment**: In-app language proficiency testing
- **Real-time analytics**: Live tracking of student progress patterns
