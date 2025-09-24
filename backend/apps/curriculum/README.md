# Curriculum App

## Overview

The `curriculum` app manages the academic curriculum structure, course catalog, program definitions, and academic calendars for the Naga SIS. This domain layer app serves as the foundation for all academic planning and course management across the institution.

## Features

### Academic Structure Management

- **Hierarchical organization** with Divisions → Cycles → Majors → Courses
- **Flexible program definitions** supporting multiple degree types
- **Course catalog management** with versioning and prerequisites
- **Academic calendar** with term planning and scheduling

### Course Management

- **Comprehensive course definitions** with learning outcomes
- **Prerequisite chains** with validation and enforcement
- **Course templates** for consistent class structure
- **Language course specialization** with level progression

### Program & Major Management

- **Degree program definitions** with requirements
- **Major declarations** and change tracking
- **Cross-program course sharing** and transfer credit support
- **Academic progression** planning and validation

### Term & Calendar Management

- **Academic term planning** with overlapping term support
- **Holiday integration** with academic calendar
- **Session organization** for intensive programs
- **Timeline validation** and conflict prevention

## Models

### Academic Hierarchy

#### Division

Top-level academic organization.

```python
# Create academic divisions
undergraduate = Division.objects.create(
    name="Undergraduate Programs",
    description="Bachelor's degree programs",
    is_active=True
)

graduate = Division.objects.create(
    name="Graduate Programs",
    description="Master's and doctoral programs",
    is_active=True
)
```

#### Cycle

Learning cycles within divisions.

```python
# Create learning cycles
foundation = Cycle.objects.create(
    division=undergraduate,
    name="Foundation Cycle",
    description="Preparatory English and basic skills",
    duration_terms=2,
    order=1
)

bachelor_cycle = Cycle.objects.create(
    division=undergraduate,
    name="Bachelor Cycle",
    description="Degree program courses",
    duration_terms=6,
    order=2
)
```

#### Major

Academic majors and specializations.

```python
# Create academic major
business_admin = Major.objects.create(
    cycle=bachelor_cycle,
    name="Business Administration",
    code="BUSADMIN",
    description="Comprehensive business education with management focus",
    credit_requirements=120,
    is_active=True
)
```

### Course Catalog

#### Course

Comprehensive course definitions.

```python
# Create academic course
course = Course.objects.create(
    code="ACCT-101",
    name="Principles of Accounting",
    description="Introduction to financial and managerial accounting",
    credits=3,
    is_language=False,
    start_date=date(2024, 8, 1),
    learning_outcomes=[
        "Understand basic accounting principles",
        "Prepare financial statements",
        "Analyze business transactions"
    ]
)

# Add to majors
course.majors.add(business_admin)
```

#### CoursePrerequisite

Course prerequisite relationships.

```python
# Define prerequisites
prerequisite = CoursePrerequisite.objects.create(
    course=advanced_accounting,
    prerequisite=principles_accounting,
    is_required=True,
    minimum_grade="C"
)
```

#### CoursePartTemplate

Template for course component structure.

```python
# Define course structure template
template = CoursePartTemplate.objects.create(
    course=course,
    part_name="Midterm Exam",
    part_type=PartType.EXAM,
    weight=Decimal("0.30"),
    description="Comprehensive midterm examination",
    is_required=True
)
```

### Academic Calendar

#### Term

Academic term management.

```python
# Create academic term
term = Term.objects.create(
    name="Fall 2024",
    term_type=TermType.BACHELOR,
    start_date=date(2024, 8, 1),
    end_date=date(2024, 12, 15),
    registration_start=date(2024, 7, 1),
    registration_end=date(2024, 7, 31),
    is_active=True
)
```

### Language-Specific Models

#### LanguageLevel

Standardized language level definitions.

```python
from apps.curriculum.models import LanguageLevel

# Language levels are pre-defined enum values
beginner = LanguageLevel.BEGINNER_1
intermediate = LanguageLevel.INTERMEDIATE_3
advanced = LanguageLevel.ADVANCED_2
```

#### SeniorProject

Capstone project management.

```python
# Create senior project
project = SeniorProject.objects.create(
    title="Digital Marketing Strategy for SMEs",
    description="Analysis of digital marketing effectiveness for small businesses",
    major=business_admin,
    max_students=4,
    term=final_term
)

# Add student group
project.student_group.add(student1, student2, student3)
```

## Services

### Curriculum Service

Comprehensive curriculum management with validation.

```python
from apps.curriculum.services import CurriculumService

# Create complete curriculum structure
division_data = {
    'name': 'Undergraduate Programs',
    'cycles': [
        {
            'name': 'Foundation Cycle',
            'majors': [
                {
                    'name': 'General Studies',
                    'code': 'GEN',
                    'courses': ['GESL-01', 'GESL-02', 'GESL-03']
                }
            ]
        }
    ]
}

division = CurriculumService.create_division_structure(division_data)
```

### Course Service

Course management with prerequisite validation.

```python
from apps.curriculum.services import CourseService

# Create course with prerequisites
course_data = {
    'code': 'ACCT-201',
    'name': 'Intermediate Accounting',
    'credits': 3,
    'prerequisites': ['ACCT-101'],
    'majors': ['BUSADMIN']
}

course = CourseService.create_course(course_data)

# Validate prerequisite chain
is_valid = CourseService.validate_prerequisite_chain('ACCT-201')
```

### Term Service

Academic calendar management with validation.

```python
from apps.curriculum.services import TermService

# Create academic year terms
academic_year = TermService.create_academic_year(
    year=2024,
    term_types=[TermType.BACHELOR, TermType.FOUNDATION],
    start_date=date(2024, 8, 1)
)

# Check term overlaps
overlaps = TermService.check_term_overlaps(new_term)
```

## Management Commands

### Curriculum Setup

```bash
# Load courses from legacy system
python manage.py load_courses_from_v0 --validate-only

# Import academic terms
python manage.py import_terms --file=terms.json

# Add missing language courses
python manage.py add_missing_language_courses --level=all

# Fix course cycle assignments
python manage.py fix_course_cycles --dry-run
```

### Data Validation

```bash
# Check division-cycle relationships
python manage.py check_division_cycle --fix-errors

# Validate course prerequisites
python manage.py validate_prerequisites --check-cycles

# Convert legacy cycle references
python manage.py convert_cycle_to_fk --batch-size=100
```

## API Endpoints

### Course Catalog API

```python
# Get course catalog with filtering
GET /api/curriculum/courses/?major=BUSADMIN&level=undergraduate

{
    "courses": [
        {
            "id": 123,
            "code": "ACCT-101",
            "name": "Principles of Accounting",
            "credits": 3,
            "majors": ["Business Administration"],
            "prerequisites": [],
            "learning_outcomes": [
                "Understand basic accounting principles",
                "Prepare financial statements"
            ],
            "is_active": true
        }
    ],
    "total": 1,
    "page": 1
}
```

### Program Structure API

```python
# Get complete program structure
GET /api/curriculum/programs/bachelor/

{
    "divisions": [
        {
            "id": 1,
            "name": "Undergraduate Programs",
            "cycles": [
                {
                    "id": 1,
                    "name": "Foundation Cycle",
                    "duration_terms": 2,
                    "majors": [
                        {
                            "id": 1,
                            "name": "General Studies",
                            "code": "GEN",
                            "course_count": 12
                        }
                    ]
                }
            ]
        }
    ]
}
```

### Academic Calendar API

```python
# Get academic calendar
GET /api/curriculum/terms/?academic_year=2024

{
    "terms": [
        {
            "id": 1,
            "name": "Fall 2024",
            "type": "bachelor",
            "start_date": "2024-08-01",
            "end_date": "2024-12-15",
            "registration_period": {
                "start": "2024-07-01",
                "end": "2024-07-31"
            },
            "is_current": true
        }
    ]
}
```

## Validation & Business Rules

### Course Validation

```python
from apps.curriculum.models import Course

class CourseValidation:
    @staticmethod
    def validate_prerequisite_chain(course):
        """Prevent circular prerequisites."""
        visited = set()

        def check_cycle(current_course, path):
            if current_course.id in path:
                raise ValidationError(f"Circular prerequisite detected: {path}")

            path.add(current_course.id)
            for prereq in current_course.prerequisites.all():
                check_cycle(prereq.prerequisite, path.copy())

        check_cycle(course, set())

    @staticmethod
    def validate_credit_range(credits):
        """Validate reasonable credit range."""
        if not 1 <= credits <= 6:
            raise ValidationError("Credits must be between 1 and 6")
```

### Term Validation

```python
def validate_term_dates(term):
    """Validate term date relationships."""
    if term.start_date >= term.end_date:
        raise ValidationError("Start date must be before end date")

    if term.registration_end > term.start_date:
        raise ValidationError("Registration must end before term starts")

    # Check for overlapping terms of same type
    overlapping = Term.objects.filter(
        term_type=term.term_type,
        start_date__lte=term.end_date,
        end_date__gte=term.start_date
    ).exclude(id=term.id)

    if overlapping.exists():
        raise ValidationError("Term dates overlap with existing term")
```

## Testing

### Test Coverage

```bash
# Run curriculum app tests
pytest apps/curriculum/

# Test specific functionality
pytest apps/curriculum/tests/test_course_part_template.py
pytest apps/curriculum/tests/test_prerequisite_validation.py
pytest apps/curriculum/tests/test_term_overlaps.py
```

### Test Factories

```python
from apps.curriculum.tests.factories import (
    DivisionFactory,
    CycleFactory,
    MajorFactory,
    CourseFactory,
    TermFactory
)

# Create test curriculum structure
division = DivisionFactory(name="Test Division")
cycle = CycleFactory(division=division)
major = MajorFactory(cycle=cycle)
course = CourseFactory(majors=[major])
```

## Performance Optimization

### Database Queries

```python
# Optimized course queries with relationships
def get_courses_with_prerequisites():
    return Course.objects.select_related(
        'cycle', 'major'
    ).prefetch_related(
        'prerequisites__prerequisite',
        'course_part_templates',
        'majors'
    ).filter(is_active=True)
```

### Caching Strategy

```python
from django.core.cache import cache

def get_curriculum_structure(division_id):
    """Cached curriculum structure for performance."""
    cache_key = f"curriculum_structure_{division_id}"
    structure = cache.get(cache_key)

    if not structure:
        structure = CurriculumService.build_structure(division_id)
        cache.set(cache_key, structure, 3600)  # 1 hour

    return structure
```

## Integration Examples

### With Scheduling App

```python
# Create class from course template
def create_class_from_course(course, term, section="A"):
    from apps.scheduling.services import SchedulingService

    class_header = SchedulingService.create_class_header(
        course=course,
        term=term,
        section=section
    )

    # Create class parts from course template
    for template in course.course_part_templates.all():
        SchedulingService.create_class_part(
            class_header=class_header,
            template=template
        )

    return class_header
```

### With Academic App

```python
# Get degree requirements for major
def get_degree_requirements(major):
    from apps.academic.services import AcademicService

    core_courses = Course.objects.filter(
        majors=major,
        is_required=True
    )

    elective_courses = Course.objects.filter(
        majors=major,
        is_required=False
    )

    return AcademicService.build_requirement_structure(
        major=major,
        core_courses=core_courses,
        elective_courses=elective_courses
    )
```

## Security & Access Control

### Course Management Authorization

```python
from apps.accounts.decorators import require_permission

@require_permission('curriculum.manage_courses')
def create_course(request):
    """Create new course - requires curriculum management permission."""
    # Course creation logic
    pass

@require_permission('curriculum.manage_programs')
def modify_major_requirements(request, major_id):
    """Modify major requirements - requires program management permission."""
    # Major modification logic
    pass
```

## Configuration

### Settings

```python
# Curriculum configuration
NAGA_CURRICULUM_CONFIG = {
    'MAX_PREREQUISITE_DEPTH': 5,
    'DEFAULT_CREDIT_RANGE': (1, 6),
    'REQUIRE_LEARNING_OUTCOMES': True,
    'COURSE_CODE_PATTERN': r'^[A-Z]{2,4}-\d{2,3}[A-Z]?$',
    'LANGUAGE_LEVEL_PROGRESSION': True
}

# Academic calendar
NAGA_ACADEMIC_CALENDAR = {
    'TERMS_PER_YEAR': 2,
    'DEFAULT_TERM_LENGTH_WEEKS': 16,
    'REGISTRATION_PERIOD_WEEKS': 4,
    'ALLOW_OVERLAPPING_TERMS': False
}
```

## Dependencies

### Internal Dependencies

- `common`: Base models, audit framework, room management
- No circular dependencies with other domain apps

### External Dependencies

- `django-mptt`: Hierarchical data structures (future enhancement)
- `django-treebeard`: Alternative tree structure support

## Architecture Notes

### Design Principles

- **Domain layer focus**: Pure curriculum management without operational concerns
- **Hierarchical organization**: Clear academic structure with Division → Cycle → Major → Course
- **Template-driven**: Course templates enable consistent class creation
- **Prerequisite integrity**: Validation prevents circular dependencies

### Business Rules

- **Prerequisite chains**: Maximum depth limit to prevent complexity
- **Credit validation**: Reasonable credit ranges for institutional standards
- **Term overlaps**: Controlled overlapping for intensive programs
- **Course versioning**: Support for curriculum changes over time

### Future Enhancements

- **Curriculum versioning**: Track changes over academic years
- **Learning outcome mapping**: Detailed outcome tracking and assessment
- **Transfer credit automation**: Automated course equivalency checking
- **Recommendation engine**: Course suggestion based on student progress
