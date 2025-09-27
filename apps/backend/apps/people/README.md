# People App

## Overview

The `people` app manages person profiles for all individuals in the Naga SIS - students, teachers, staff, and their relationships. This domain layer app serves as the foundation for all person-related functionality across the system.

## Features

### Comprehensive Person Management

- **Unified person model** with role-specific profiles
- **Multi-language name support** (English/Khmer)
- **Flexible address management** with validation
- **Emergency contact relationships** with multiple contacts per person

### Student Lifecycle Management

- **Student profile creation** with academic tracking
- **Enrollment history** with program progression
- **Academic status tracking** with automated updates
- **ID generation** with institutional formatting

### Faculty & Staff Management

- **Teacher profiles** with qualifications and specializations
- **Staff profiles** with administrative responsibilities
- **Contact information** with verification status
- **Professional credentials** and certification tracking

### Contact & Communication

- **Phone number normalization** with international support
- **Email validation** with institutional domain checking
- **Address standardization** with geocoding integration
- **Emergency contact management** with relationship tracking

## Models

### Core Person Model

#### Person

Central person entity with comprehensive demographic information.

```python
# Create a person with bilingual names
person = Person.objects.create(
    first_name_eng="Sophea",
    last_name_eng="Chan",
    first_name_local="សុភា",
    last_name_local="ចាន់",
    date_of_birth=date(2000, 5, 15),
    gender=Gender.FEMALE,
    nationality="Cambodian",
    phone_primary="+855 12 345 678",
    email_primary="sophea.chan@example.com"
)
```

### Role-Specific Profiles

#### StudentProfile

Student-specific information and academic tracking.

```python
# Create student profile
student = StudentProfile.objects.create(
    person=person,
    student_id="SIS-12345",
    program_level=ProgramLevel.BACHELOR,
    entry_term=current_term,
    academic_status=AcademicStatus.ACTIVE,
    expected_graduation_term=graduation_term
)

# Access student information
print(f"Student: {student.full_name_eng}")
print(f"ID: {student.student_id}")
print(f"GPA: {student.current_gpa}")
```

#### TeacherProfile

Faculty member information and qualifications.

```python
# Create teacher profile
teacher = TeacherProfile.objects.create(
    person=person,
    employee_id="EMP-001",
    hire_date=date(2020, 8, 1),
    position_title="Senior English Instructor",
    specialization="Academic English",
    qualification_level=QualificationLevel.MASTERS
)

# Teaching load and courses
assigned_courses = teacher.current_teaching_assignments.all()
```

#### StaffProfile

Administrative staff information.

```python
# Create staff profile
staff = StaffProfile.objects.create(
    person=person,
    employee_id="STAFF-001",
    department="Academic Affairs",
    position_title="Registrar",
    responsibilities="Student records, enrollment, graduation"
)
```

### Contact Management

#### EmergencyContact

Emergency contact relationships with detailed information.

```python
# Add emergency contacts
emergency_contact = EmergencyContact.objects.create(
    person=student.person,
    contact_name_eng="Meng Chan",
    contact_name_local="ម៉េង ចាន់",
    relationship=RelationshipType.PARENT,
    phone_primary="+855 11 234 567",
    is_primary_contact=True,
    can_authorize_medical=True
)
```

## Services

### Person Service

Comprehensive person management with validation and business logic.

```python
from apps.people.services import PersonService

# Create person with validation
person_data = {
    'first_name_eng': 'Sophea',
    'last_name_eng': 'Chan',
    'date_of_birth': '2000-05-15',
    'phone_primary': '012 345 678',
    'email_primary': 'sophea@example.com'
}

person = PersonService.create_person(person_data)

# Search for people
results = PersonService.search_people(
    query="Sophea Chan",
    include_students=True,
    include_teachers=False
)
```

### Student Service

Student-specific operations with academic validation.

```python
from apps.people.services import StudentService

# Create student with automated ID generation
student = StudentService.create_student(
    person=person,
    program_level=ProgramLevel.BACHELOR,
    entry_term=current_term
)

# Update academic status
StudentService.update_academic_status(
    student=student,
    new_status=AcademicStatus.PROBATION,
    reason="GPA below threshold",
    effective_date=date.today()
)

# Generate student ID
new_id = StudentService.generate_student_id(
    program_level=ProgramLevel.BACHELOR,
    entry_year=2024
)
```

### Name Parsing Service

Advanced name parsing with cultural considerations.

```python
from apps.people.utils.name_parser import NameParser

# Parse complex names
parser = NameParser()

# Handle Western names
parsed = parser.parse_western_name("Mary Jane Smith-Wilson")
# Returns: {
#     'first_name': 'Mary Jane',
#     'last_name': 'Smith-Wilson',
#     'middle_name': None
# }

# Handle Khmer names with titles
parsed = parser.parse_khmer_name("លោក ចាន់ សុភា")
# Returns: {
#     'title': 'លោក',
#     'first_name': 'សុភា',
#     'last_name': 'ចាន់'
# }
```

## Views & Forms

### Student Profile CRUD

Comprehensive student management interface.

```python
from apps.people.views.student_profile_crud import StudentProfileCrudView

# Advanced CRUD with academic context
class StudentManagementView(StudentProfileCrudView):
    template_name = 'people/student_management.html'

    def get_queryset(self):
        return StudentProfile.objects.select_related(
            'person', 'entry_term'
        ).filter(
            academic_status__in=[
                AcademicStatus.ACTIVE,
                AcademicStatus.PROBATION
            ]
        )
```

### Person Forms

Sophisticated forms with validation and user experience enhancements.

```python
from apps.people.forms import PersonForm, StudentProfileForm

# Multi-step person creation
person_form = PersonForm(data=request.POST)
if person_form.is_valid():
    person = person_form.save()

    # Create student profile
    student_form = StudentProfileForm(
        data=request.POST,
        person=person
    )
    if student_form.is_valid():
        student = student_form.save()
```

## Management Commands

### Data Import & Migration

```bash
# Import students from legacy system
python manage.py import_students --file=legacy_students.csv --validate-only

# Import staff data
python manage.py import_staff_data --department="Academic Affairs"

# Fix student names with improved parser
python manage.py fix_student_names --dry-run

# Migrate corrected student data
python manage.py migrate_students_corrected --batch-size=100
```

### Data Validation

```bash
# Validate all person data
python manage.py validate_people_data --fix-errors

# Check for duplicate persons
python manage.py find_duplicate_people --similarity-threshold=0.8

# Validate contact information
python manage.py validate_contact_info --update-status
```

## API Integration

### Person Search API

```python
# Search for people with advanced filtering
GET /api/people/search/?q=sophea&role=student&status=active

{
    "results": [
        {
            "id": 123,
            "full_name_eng": "Sophea Chan",
            "full_name_local": "សុភា ចាន់",
            "role": "student",
            "student_id": "SIS-12345",
            "academic_status": "active",
            "program": "Bachelor of Arts"
        }
    ],
    "total": 1,
    "page": 1
}
```

### Student Profile API

```python
# Get comprehensive student information
GET /api/people/students/{student_id}/

{
    "personal_info": {
        "full_name_eng": "Sophea Chan",
        "date_of_birth": "2000-05-15",
        "nationality": "Cambodian"
    },
    "academic_info": {
        "student_id": "SIS-12345",
        "program_level": "bachelor",
        "current_gpa": "3.45",
        "academic_status": "active",
        "credits_completed": 45
    },
    "contact_info": {
        "phone_primary": "+855012345678",
        "email_primary": "sophea.chan@student.pucsr.edu.kh",
        "address": "Phnom Penh, Cambodia"
    },
    "emergency_contacts": [
        {
            "name": "Meng Chan",
            "relationship": "parent",
            "phone": "+855011234567",
            "is_primary": true
        }
    ]
}
```

## Validation & Business Rules

### Person Validation

```python
from apps.people.models import Person

class PersonValidation:
    @staticmethod
    def validate_names(first_name_eng, last_name_eng):
        """Validate English names for completeness and format."""
        if not first_name_eng or not last_name_eng:
            raise ValidationError("English names are required")

        # Check for appropriate length and characters
        if len(first_name_eng) < 2:
            raise ValidationError("First name too short")

    @staticmethod
    def validate_contact_info(phone, email):
        """Validate contact information for reachability."""
        from apps.common.utils import normalize_phone_number

        if phone:
            normalized = normalize_phone_number(phone)
            if not normalized:
                raise ValidationError("Invalid phone number format")

        if email and "@" not in email:
            raise ValidationError("Invalid email format")
```

### Student ID Generation

```python
def generate_student_id(program_level, entry_year):
    """Generate unique student ID following institutional format."""
    prefix = "SIS"
    year_suffix = str(entry_year)[-2:]  # Last 2 digits of year

    # Get next sequence number for the year
    last_student = StudentProfile.objects.filter(
        student_id__startswith=f"{prefix}-{year_suffix}"
    ).order_by('-student_id').first()

    if last_student:
        last_sequence = int(last_student.student_id.split('-')[-1])
        next_sequence = last_sequence + 1
    else:
        next_sequence = 1

    return f"{prefix}-{year_suffix}{next_sequence:04d}"
```

## Testing

### Test Coverage

```bash
# Run people app tests
pytest apps/people/

# Test specific functionality
pytest apps/people/tests/test_name_parser.py
pytest apps/people/tests/test_student_services.py
pytest apps/people/tests/test_duplicate_detection.py
```

### Test Factories

```python
from apps.people.tests.factories import (
    PersonFactory,
    StudentProfileFactory,
    TeacherProfileFactory,
    EmergencyContactFactory
)

# Create test data
person = PersonFactory(
    first_name_eng="Test",
    last_name_eng="Student"
)

student = StudentProfileFactory(
    person=person,
    program_level=ProgramLevel.BACHELOR
)

emergency_contact = EmergencyContactFactory(
    person=person,
    relationship=RelationshipType.PARENT
)
```

## Performance Optimization

### Database Queries

```python
# Optimized person queries with relationships
def get_students_with_contacts():
    return StudentProfile.objects.select_related(
        'person'
    ).prefetch_related(
        'person__emergency_contacts',
        'program_enrollments__major'
    ).filter(
        academic_status=AcademicStatus.ACTIVE
    )
```

### Indexing Strategy

- **Composite indexes** on name fields for search performance
- **Phone number indexing** for contact lookup
- **Student ID indexing** for rapid student identification
- **Date of birth indexing** for age-based queries

## Security & Privacy

### Data Protection

- **PII encryption** for sensitive personal information
- **Contact information masking** for unauthorized users
- **GDPR compliance** with data retention policies
- **Audit trail** for all person data modifications

### Access Control

```python
from apps.accounts.decorators import require_permission

@require_permission('people.view_student_details')
def view_student_profile(request, student_id):
    """View detailed student information."""
    student = get_object_or_404(StudentProfile, id=student_id)

    # Additional authorization for sensitive data
    if not request.user.can_view_sensitive_data:
        # Mask sensitive information
        student.person.phone_primary = "***-***-" + student.person.phone_primary[-4:]

    return render(request, 'people/student_detail.html', {
        'student': student
    })
```

## Integration Examples

### With Enrollment App

```python
# Create student and immediately enroll in program
def create_and_enroll_student(person_data, program_data):
    from apps.enrollment.services import EnrollmentService

    # Create person and student profile
    person = PersonService.create_person(person_data)
    student = StudentService.create_student(
        person=person,
        program_level=program_data['level']
    )

    # Enroll in program
    enrollment = EnrollmentService.enroll_student_in_program(
        student=student,
        program=program_data['program'],
        term=program_data['term']
    )

    return student, enrollment
```

### With Academic App

```python
# Get student academic progress
def get_student_academic_summary(student_id):
    from apps.academic.services import AcademicService

    student = StudentProfile.objects.get(id=student_id)

    return {
        'personal': student.person.basic_info,
        'academic_status': student.academic_status,
        'requirements': AcademicService.get_degree_progress(student),
        'gpa': student.current_gpa,
        'expected_graduation': student.expected_graduation_term
    }
```

## Configuration

### Settings

```python
# Student ID configuration
NAGA_STUDENT_ID_CONFIG = {
    'PREFIX': 'SIS',
    'YEAR_DIGITS': 2,
    'SEQUENCE_DIGITS': 4,
    'SEPARATOR': '-'
}

# Name validation
NAGA_NAME_VALIDATION = {
    'MIN_LENGTH': 2,
    'MAX_LENGTH': 50,
    'ALLOW_NUMBERS': False,
    'REQUIRE_ENGLISH_NAMES': True
}

# Contact validation
NAGA_CONTACT_CONFIG = {
    'DEFAULT_COUNTRY_CODE': '+855',
    'REQUIRE_VERIFIED_EMAIL': False,
    'MAX_EMERGENCY_CONTACTS': 3
}
```

## Dependencies

### Internal Dependencies

- `common`: Base models, phone normalization, audit framework
- `accounts`: User model integration for profiles

### External Dependencies

- `phonenumbers`: International phone number validation
- `django-countries`: Country field support
- `unicodedata`: Name normalization utilities

## Architecture Notes

### Design Principles

- **Domain layer focus**: Core person management without business logic
- **Profile pattern**: Role-specific profiles extending base person
- **Flexible relationships**: Support for complex family/contact structures
- **Cultural sensitivity**: Multi-language name support

### Future Enhancements

- **Photo management**: Profile pictures with privacy controls
- **Document storage**: ID documents and certificates
- **Relationship mapping**: Extended family/professional relationships
- **Integration APIs**: External HR/SIS system synchronization
