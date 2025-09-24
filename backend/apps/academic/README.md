# Academic App

## Overview

The `academic` app manages degree requirements, course equivalencies, transfer credits, and graduation tracking for the Naga SIS. This business logic layer app enforces academic standards, tracks student progress toward degree completion, and provides the foundation for academic advising and graduation audits.

## Features

### Degree Requirements Management

- **Canonical requirement definitions** with flexible criteria
- **Program-specific requirements** by major and level
- **Credit and course-based requirements** with validation
- **Requirement fulfillment tracking** with automated evaluation

### Course Equivalencies & Transfer Credits

- **Course substitution management** with approval workflows
- **Transfer credit evaluation** from external institutions
- **Equivalency mapping** with validation and expiration
- **Credit conversion** between different grading systems

### Academic Progress Tracking

- **Degree progress monitoring** with completion percentages
- **Requirement gap analysis** for academic planning
- **Graduation eligibility determination** with requirement validation
- **Academic milestone tracking** throughout student journey

### Institutional Requirements

- **Core curriculum** requirements across all programs
- **Major-specific** requirements with specialization tracks
- **Elective requirements** with category constraints
- **Capstone/thesis** requirements for degree completion

## Models

### Requirement Framework

#### RequirementType

Categories of academic requirements with flexible validation rules.

```python
# Define requirement types
core_requirement = RequirementType.objects.create(
    name="Core Curriculum",
    description="Required courses for all students",
    code="CORE",
    validation_method=ValidationMethod.COURSE_LIST,
    is_required=True
)

major_requirement = RequirementType.objects.create(
    name="Major Requirements",
    description="Required courses for major completion",
    code="MAJOR",
    validation_method=ValidationMethod.CREDIT_HOURS,
    is_required=True
)
```

#### Requirement

Specific degree requirements with criteria and fulfillment rules.

```python
# Create degree requirement
english_composition = Requirement.objects.create(
    requirement_type=core_requirement,
    name="English Composition",
    description="Complete two semesters of English composition",
    major=business_admin,
    program_level=ProgramLevel.BACHELOR,
    credit_hours_required=6,
    courses_required=2,
    minimum_grade="C",
    is_active=True
)

# Add specific courses that fulfill requirement
english_composition.qualifying_courses.add(eng_comp_1, eng_comp_2)
```

#### StudentRequirementFulfillment

Tracks individual student progress on each requirement.

```python
# Track student fulfillment
fulfillment = StudentRequirementFulfillment.objects.create(
    student=student_profile,
    requirement=english_composition,
    status=FulfillmentStatus.IN_PROGRESS,
    credits_completed=3,  # One course completed
    courses_completed=1,
    last_evaluated=timezone.now()
)

# Update when student completes second course
fulfillment.update_progress(
    new_course=eng_comp_2,
    grade="B+",
    credits=3
)
```

### Course Equivalencies

#### CourseEquivalency

Manages course substitutions and equivalencies.

```python
# Create course equivalency
equivalency = CourseEquivalency.objects.create(
    original_course=statistics_101,
    equivalent_course=business_stats,
    equivalency_type=EquivalencyType.SUBSTITUTION,
    approved_by=academic_dean,
    effective_date=date(2024, 8, 1),
    expiration_date=date(2027, 8, 1),
    reason="Business Statistics covers same learning outcomes"
)

# Apply to student
StudentCourseEquivalency.objects.create(
    student=student_profile,
    equivalency=equivalency,
    applied_date=date(2024, 9, 15),
    applied_by=academic_advisor
)
```

#### TransferCredit

External credit recognition with detailed tracking.

```python
# Record transfer credit
transfer_credit = TransferCredit.objects.create(
    student=student_profile,
    external_course_name="Introduction to Psychology",
    external_institution="Royal University of Phnom Penh",
    external_credits=3,
    external_grade="A",
    naga_equivalent_course=psychology_101,
    credits_awarded=3,
    evaluation_date=date(2024, 7, 15),
    evaluated_by=registrar,
    transcript_verified=True
)
```

### Canonical Requirements

#### CanonicalRequirement

Template requirements for efficient program setup.

```python
# Define canonical BA Business Admin requirements
ba_busadmin_reqs = CanonicalRequirement.objects.create(
    program_level=ProgramLevel.BACHELOR,
    major_code="BUSADMIN",
    requirement_data={
        "core_courses": [
            {"course_code": "ACCT-101", "required": True},
            {"course_code": "ECON-101", "required": True},
            {"course_code": "MGMT-101", "required": True}
        ],
        "electives": {
            "business_electives": {"credits_required": 15, "category": "BUSINESS"},
            "general_electives": {"credits_required": 12, "category": "GENERAL"}
        },
        "capstone": {
            "course_code": "BUSN-490",
            "required": True,
            "prerequisite_credits": 90
        }
    },
    created_by=academic_dean
)
```

## Services

### Academic Service

Comprehensive academic evaluation and requirement management.

```python
from apps.academic.services import AcademicService

# Evaluate student degree progress
progress = AcademicService.evaluate_degree_progress(
    student=student_profile,
    program_enrollment=program_enrollment
)

# Returns comprehensive progress report
{
    "overall_completion": 75.5,
    "credits_completed": 90,
    "credits_required": 120,
    "requirements": [
        {
            "name": "Core Curriculum",
            "status": "completed",
            "completion_percentage": 100
        },
        {
            "name": "Major Requirements",
            "status": "in_progress",
            "completion_percentage": 80,
            "remaining_courses": ["ACCT-301", "MGMT-401"]
        }
    ],
    "graduation_eligible": False,
    "estimated_graduation": "Spring 2025"
}
```

### Equivalency Service

Course equivalency and transfer credit management.

```python
from apps.academic.services import EquivalencyService

# Evaluate transfer credit
evaluation = EquivalencyService.evaluate_transfer_credit(
    student=student_profile,
    external_course_data={
        "course_name": "Business Mathematics",
        "institution": "IIC University",
        "credits": 3,
        "grade": "B+",
        "syllabus": course_syllabus_text
    }
)

if evaluation.approved:
    transfer_credit = EquivalencyService.create_transfer_credit(
        student=student_profile,
        evaluation=evaluation,
        approved_by=registrar
    )
```

### Requirement Service

Requirement management and fulfillment tracking.

```python
from apps.academic.services import RequirementService

# Check requirement fulfillment for specific course
fulfillment_check = RequirementService.check_course_fulfillment(
    student=student_profile,
    course=completed_course,
    grade="B+"
)

# Apply course to fulfill requirements
for requirement in fulfillment_check.fulfills:
    RequirementService.apply_course_to_requirement(
        student=student_profile,
        requirement=requirement,
        course=completed_course,
        grade="B+"
    )
```

## Management Commands

### Requirement Management

```bash
# Create canonical requirements for programs
python manage.py create_ba_busadmin_canonical_requirements
python manage.py create_ba_tesol_canonical_requirements

# Populate requirements from canonical templates
python manage.py populate_canonical_requirements --program=all

# Populate course fulfillments for existing students
python manage.py populate_course_fulfillments --recalculate
```

### Academic Evaluation

```bash
# Evaluate all students' degree progress
python manage.py evaluate_degree_progress --term=current

# Check graduation eligibility
python manage.py check_graduation_eligibility --term=spring2025

# Generate academic standing reports
python manage.py generate_academic_standing --term=current
```

### Data Migration

```bash
# Import legacy academic data
python manage.py import_legacy_requirements --file=requirements.json

# Migrate course equivalencies
python manage.py migrate_course_equivalencies --validate

# Update requirement fulfillments
python manage.py update_requirement_fulfillments --batch-size=100
```

## API Endpoints

### Degree Progress API

```python
# Get student degree progress
GET /api/academic/students/{student_id}/degree-progress/

{
    "student": {
        "id": 123,
        "name": "Sophea Chan",
        "program": "Bachelor of Business Administration"
    },
    "progress": {
        "overall_completion": 75.5,
        "credits_completed": 90,
        "credits_required": 120,
        "gpa": "3.45"
    },
    "requirements": [
        {
            "id": 1,
            "name": "Core Curriculum",
            "type": "core",
            "status": "completed",
            "completion_percentage": 100,
            "credits_required": 30,
            "credits_completed": 30
        },
        {
            "id": 2,
            "name": "Major Requirements",
            "type": "major",
            "status": "in_progress",
            "completion_percentage": 80,
            "credits_required": 60,
            "credits_completed": 48,
            "remaining_courses": ["ACCT-301", "MGMT-401"]
        }
    ],
    "graduation_status": {
        "eligible": false,
        "estimated_completion": "Spring 2025",
        "remaining_requirements": 2
    }
}
```

### Transfer Credit API

```python
# Submit transfer credit evaluation
POST /api/academic/transfer-credits/evaluate/
{
    "student_id": 123,
    "external_course": {
        "name": "Introduction to Marketing",
        "institution": "Royal University of Phnom Penh",
        "credits": 3,
        "grade": "A",
        "completion_date": "2023-12-15"
    },
    "documentation": "base64_encoded_transcript"
}

# Response
{
    "evaluation_id": 456,
    "status": "approved",
    "naga_equivalent": {
        "course_code": "MKTG-101",
        "course_name": "Principles of Marketing",
        "credits_awarded": 3
    },
    "evaluator": "Dr. Academic Dean",
    "evaluation_date": "2024-07-15",
    "notes": "Course content aligns with MKTG-101 learning outcomes"
}
```

### Requirements API

```python
# Get program requirements
GET /api/academic/programs/{program_id}/requirements/

{
    "program": {
        "name": "Bachelor of Business Administration",
        "level": "bachelor",
        "total_credits": 120
    },
    "requirements": [
        {
            "type": "core",
            "name": "Core Curriculum",
            "credits_required": 30,
            "courses": [
                {
                    "code": "ACCT-101",
                    "name": "Principles of Accounting",
                    "credits": 3,
                    "required": true
                }
            ]
        },
        {
            "type": "major",
            "name": "Major Requirements",
            "credits_required": 60,
            "courses": [
                {
                    "code": "MGMT-101",
                    "name": "Principles of Management",
                    "credits": 3,
                    "required": true
                }
            ]
        }
    ]
}
```

## Validation & Business Rules

### Requirement Validation

```python
def validate_requirement_fulfillment(student, requirement, proposed_course):
    """Validate if course can fulfill requirement."""
    errors = []

    # Check if course is in qualifying list
    if not requirement.qualifying_courses.filter(id=proposed_course.id).exists():
        errors.append(f"Course {proposed_course.code} does not fulfill {requirement.name}")

    # Check minimum grade requirement
    if hasattr(proposed_course, 'grade'):
        if not meets_grade_requirement(proposed_course.grade, requirement.minimum_grade):
            errors.append(f"Grade {proposed_course.grade} below required {requirement.minimum_grade}")

    # Check prerequisite completion
    unmet_prereqs = check_unmet_prerequisites(student, proposed_course)
    if unmet_prereqs:
        errors.append(f"Unmet prerequisites: {unmet_prereqs}")

    return errors

def validate_graduation_eligibility(student, program_enrollment):
    """Comprehensive graduation eligibility check."""
    issues = []

    # Check all requirements completion
    unfulfilled_requirements = get_unfulfilled_requirements(student, program_enrollment)
    if unfulfilled_requirements:
        issues.extend([f"Incomplete: {req.name}" for req in unfulfilled_requirements])

    # Check minimum credit hours
    if student.total_credits < program_enrollment.major.credit_requirements:
        issues.append(f"Insufficient credits: {student.total_credits}/{program_enrollment.major.credit_requirements}")

    # Check minimum GPA
    if student.cumulative_gpa < program_enrollment.major.minimum_gpa:
        issues.append(f"GPA below minimum: {student.cumulative_gpa}/{program_enrollment.major.minimum_gpa}")

    # Check residency requirement (minimum credits at institution)
    if student.naga_credits < program_enrollment.major.residency_requirement:
        issues.append(f"Residency requirement not met: {student.naga_credits}/{program_enrollment.major.residency_requirement}")

    return len(issues) == 0, issues
```

### Transfer Credit Validation

```python
def validate_transfer_credit(transfer_credit_data):
    """Validate transfer credit application."""
    # Check institution accreditation
    if not is_accredited_institution(transfer_credit_data['institution']):
        raise ValidationError("Institution not accredited")

    # Check grade conversion
    converted_grade = convert_external_grade(
        transfer_credit_data['grade'],
        transfer_credit_data['grading_system']
    )

    if converted_grade < MINIMUM_TRANSFER_GRADE:
        raise ValidationError("Grade too low for transfer credit")

    # Check currency (course not too old)
    completion_date = transfer_credit_data['completion_date']
    if (date.today() - completion_date).days > TRANSFER_CREDIT_EXPIRATION_DAYS:
        raise ValidationError("Course too old for transfer credit")
```

## Integration Examples

### With Enrollment App

```python
# Check academic requirements before enrollment
def enroll_with_academic_check(student, class_header):
    from apps.enrollment.services import EnrollmentService

    # Check if course fulfills degree requirements
    fulfillment_analysis = AcademicService.analyze_course_fulfillment(
        student=student,
        course=class_header.course
    )

    # Enroll student
    enrollment = EnrollmentService.enroll_student(student, class_header)

    # Track requirement progress
    if fulfillment_analysis.fulfills_requirements:
        for requirement in fulfillment_analysis.requirements:
            RequirementService.mark_requirement_progress(
                student=student,
                requirement=requirement,
                course=class_header.course
            )

    return enrollment
```

### With Grading App

```python
# Update requirement fulfillment when grades are posted
def update_requirements_on_grade_change(student, course, new_grade):
    from apps.academic.services import RequirementService

    # Find requirements this course could fulfill
    potential_requirements = RequirementService.get_requirements_for_course(
        student=student,
        course=course
    )

    for requirement in potential_requirements:
        # Check if grade meets requirement
        if meets_grade_requirement(new_grade, requirement.minimum_grade):
            RequirementService.mark_requirement_fulfilled(
                student=student,
                requirement=requirement,
                course=course,
                grade=new_grade
            )
        else:
            # Remove fulfillment if grade dropped below minimum
            RequirementService.remove_requirement_fulfillment(
                student=student,
                requirement=requirement,
                course=course
            )
```

## Testing

### Test Coverage

```bash
# Run academic app tests
pytest apps/academic/

# Test specific functionality
pytest apps/academic/test_canonical.py
pytest apps/academic/test_core_business_logic.py
pytest apps/academic/test_services.py
```

### Test Factories

```python
from apps.academic.tests.factories import (
    RequirementTypeFactory,
    RequirementFactory,
    CourseEquivalencyFactory,
    TransferCreditFactory
)

# Create test academic data
requirement_type = RequirementTypeFactory(name="Test Requirements")
requirement = RequirementFactory(
    requirement_type=requirement_type,
    credit_hours_required=6
)
```

## Performance Optimization

### Query Optimization

```python
# Efficient degree progress queries
def get_student_progress_optimized(student):
    return StudentRequirementFulfillment.objects.filter(
        student=student
    ).select_related(
        'requirement__requirement_type',
        'requirement__major'
    ).prefetch_related(
        'requirement__qualifying_courses',
        'completed_courses'
    )
```

### Caching Strategy

```python
from django.core.cache import cache

def get_degree_requirements(major, program_level):
    """Cached degree requirements for performance."""
    cache_key = f"degree_requirements_{major.id}_{program_level}"
    requirements = cache.get(cache_key)

    if not requirements:
        requirements = Requirement.objects.filter(
            major=major,
            program_level=program_level,
            is_active=True
        ).select_related('requirement_type')
        cache.set(cache_key, requirements, 3600)  # 1 hour

    return requirements
```

## Configuration

### Settings

```python
# Academic configuration
NAGA_ACADEMIC_CONFIG = {
    'MINIMUM_TRANSFER_GRADE': 'C',
    'TRANSFER_CREDIT_EXPIRATION_YEARS': 7,
    'MAXIMUM_TRANSFER_CREDITS': 60,
    'RESIDENCY_REQUIREMENT_PERCENTAGE': 0.5,  # 50% of credits must be from Naga
    'GRADUATION_AUDIT_REQUIRED': True,
    'ACADEMIC_FORGIVENESS_ALLOWED': True
}

# Requirement validation
NAGA_REQUIREMENT_CONFIG = {
    'ALLOW_COURSE_SUBSTITUTIONS': True,
    'REQUIRE_ADVISOR_APPROVAL': True,
    'AUTOMATIC_FULFILLMENT_TRACKING': True,
    'GRADE_REPLACEMENT_POLICY': 'latest_attempt'
}
```

## Dependencies

### Internal Dependencies

- `curriculum`: Course definitions and prerequisites
- `people`: Student profiles and academic records
- `enrollment`: Student course enrollment history

### External Dependencies

- No external dependencies required

## Architecture Notes

### Design Principles

- **Business logic layer**: Encapsulates complex academic rules
- **Requirement-driven**: Flexible requirement framework for various programs
- **Audit trail**: Complete tracking of academic decisions and changes
- **Data integrity**: Strong validation for academic standards

### Key Relationships

- **Requirements** define what students must complete
- **Fulfillments** track individual student progress
- **Equivalencies** handle course substitutions and transfers
- **Canonical requirements** provide templates for program setup

### Future Enhancements

- **AI-powered degree planning**: Automated course recommendations
- **Blockchain transcripts**: Immutable academic record verification
- **Real-time progress tracking**: Live updates as grades are posted
- **Predictive analytics**: Early warning for at-risk students
