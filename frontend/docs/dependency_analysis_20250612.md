# Django Model Dependencies Analysis - Naga Backend

**Analysis Date:** December 6, 2025 (Updated June 13, 2025)  
**Project:** Naga SIS (Student Information System)  
**Django Version:** 5.2+  

## Version 1.0 Updates (June 13, 2025)

**Architecture Changes Made:**
- ✅ **Facilities app eliminated** - Building/Room models moved to `apps/common/` 
- ✅ **Province model deprecated** - Replaced with ENUM choices in `apps/common/constants.py`
- ✅ **Geography app not needed** - Location handling simplified to enums
- ✅ **Clean dependency hierarchy established** - No circular dependencies in new structure
- ✅ **Scheduling app implemented** - With ClassSession support for IEAP programs

## Version 1.0 Updates (June 14, 2025)

**Critical Architectural Error Corrected:**
- 🚨 **Claude failed to consult dependency analysis** when asked about missing admin.py files
- ❌ **Facilities app was incorrectly created** despite being marked as eliminated in analysis
- ✅ **Facilities app removed from codebase** and settings after discovery
- 📝 **LESSON LEARNED:** Always reference dependency analysis before any architectural decisions
- 🔄 **Process improved:** Must check docs/dependency_analysis_20250612.md first  

## Executive Summary

This analysis reveals a complex web of interdependencies across Django apps in the Naga backend that requires immediate architectural refactoring. The current structure contains multiple circular dependencies, unclear app boundaries, and violations of Django's recommended layered architecture.

**Key Findings:**
- **12 circular dependency chains** identified across apps
- **Mixed responsibilities** in several apps violating single responsibility principle
- **Core models scattered** across multiple apps creating tight coupling
- **Inconsistent dependency direction** making the codebase difficult to maintain

**Priority:** **CRITICAL** - This technical debt impacts maintainability, testing, and future development velocity.

## 1. Complete Model Inventory

### 1.1 Core App (`apps/core/`)
**Purpose:** Central models for people, courses, facilities, and academic structure

| Model | Primary Dependencies | Description |
|-------|---------------------|-------------|
| **Person** | Province | Base person model for all humans |
| **StudentProfile** | Person, TeacherProfile (academic_advisor), Term | Student-specific data and status |
| **TeacherProfile** | Person, Course (areas_of_expertise) | Teacher profiles and qualifications |
| **StaffProfile** | Person | Staff member profiles |
| **EmergencyContact** | Person | Emergency contact information |
| **PhoneNumber** | Person | Multiple phone numbers per person |
| **PersonEventLog** | Person, CustomUser | Audit log for person events |
| **StudentAuditLog** | StudentProfile, CustomUser, ContentType | Student-specific audit trail |
| **ProgramEnrollment** | StudentProfile, SchoolStructuralUnit, Term | Program enrollment tracking |
| **Sponsor** | None | Organizations that sponsor students |
| **SponsorDiscount** | Sponsor | Sponsor-specific discounts |
| **SponsoredStudent** | Sponsor, StudentProfile, finance.Scholarship | Links sponsors to students |
| **FeedbackContact** | StudentProfile | Student feedback contacts |
| **SchoolStructuralUnit** | grading.GradingScale (self-reference) | Academic organizational hierarchy |
| **Term** | None | Academic terms/semesters |
| **Course** | SchoolStructuralUnit | Course definitions |
| **MajorRequirement** | SchoolStructuralUnit, Course | Program requirements |
| **CoursePrerequisite** | Course (self-reference) | Course prerequisite relationships |
| **CourseProgression** | SchoolStructuralUnit, Course | Course sequencing rules |
| **CourseProgressionPrerequisite** | CourseProgression, Course | Detailed prerequisite rules |
| **StudentCourseEligibility** | StudentProfile, Course, Term | Course eligibility tracking |
| **Textbook** | None | Course textbooks |
| **EquivalentCourse** | Course (self-reference), StudentProfile | Course equivalencies |
| **TransferCredit** | StudentProfile, Course | Transfer credit records |
| **Building** | None | Physical buildings |
| **Room** | Building | Rooms within buildings |
| **Holiday** | None | Holiday calendar |
| **University** | None | University information |
| **Province** | None | Geographic provinces |

### 1.2 Accounts App (`apps/accounts/`)
**Purpose:** User authentication, roles, and permissions

| Model | Primary Dependencies | Description |
|-------|---------------------|-------------|
| **CustomUser** | Department, UserRole | Main user model (email-based) |
| **Department** | None | Organizational departments |
| **UserRole** | Department, Permission | Role-based access control |
| **Permission** | ContentType | Custom permission system |
| **RolePermission** | UserRole, Permission, Department, ContentType | Role-permission assignments |
| **CustomGroup** | AuthGroup (proxy) | Extended group model |

### 1.3 Finance App (`apps/finance/`)
**Purpose:** Financial transactions, discounts, scholarships, and billing

| Model | Primary Dependencies | Description |
|-------|---------------------|-------------|
| **Discount** | None | Discount type definitions |
| **StudentDiscountEligibility** | StudentProfile, Discount, Scholarship, CustomUser | Student discount eligibility |
| **DiscountUsage** | Discount, StudentProfile, StudentDiscountEligibility, ScholarshipTransaction | Discount usage audit trail |
| **ScholarshipType** | None | Scholarship program templates |
| **Scholarship** | StudentProfile, ScholarshipType, Discount, Term, CustomUser | Individual scholarship awards |
| **ScholarshipTransaction** | Scholarship, Term, ContentType | Scholarship usage tracking |
| **TermDiscountValue** | Discount, Term | Term-specific discount values |
| **AdministrativePackageType** | None | Admin service package types |
| **DocumentTypeLimit** | AdministrativePackageType | Document limits per package |
| **StudentPackageAssignment** | StudentProfile, AdministrativePackageType, CustomUser | Student package assignments |
| **AdminDocumentOrder** | StudentProfile, DocumentTypeLimit, followup.FollowUp | Admin document orders |

### 1.4 Scheduling App (`apps/scheduling/`)
**Purpose:** Class scheduling, enrollments, and session management

| Model | Primary Dependencies | Description |
|-------|---------------------|-------------|
| **RoomSchedule** | Room, DayOfWeek | Room availability schedules |
| **ClassHeaderTemplate** | None | Class structure templates |
| **ClassPartTemplate** | ClassHeaderTemplate, ClassPartType, Textbook | Class component templates |
| **ClassHeader** | Course, Term, CombinedClassGroup, ClassHeaderTemplate | Class offerings |
| **ClassPart** | ClassHeader, TeacherProfile, Room, ClassPartTemplate, Textbook | Scheduled class components |
| **ClassPartEnrollment** | StudentProfile, ClassPart | Student enrollment in class parts |
| **CombinedClassGroup** | Term | Groups of combined classes |
| **StudentEnrollment** | StudentProfile, ClassHeader, CustomUser | Main enrollment records |
| **ReadingClass** | ClassHeader | Special reading class management |

### 1.5 Academic App (`apps/academic/`)
**Purpose:** Academic requirements, prerequisites, and degree tracking

| Model | Primary Dependencies | Description |
|-------|---------------------|-------------|
| **RequirementType** | None | Types of academic requirements |
| **Requirement** | SchoolStructuralUnit, RequirementType, Course, Term | Academic requirements |
| **RequirementCourse** | Requirement, Course | Requirement-course links |
| **CourseEquivalency** | Course (self-reference), Term | Course equivalency rules |
| **TransferCredit** | StudentProfile, Course, CustomUser | Transfer credit records |
| **StudentRequirementFulfillment** | StudentProfile, Requirement, Course, StudentEnrollment, TransferCredit, CustomUser | Requirement completion tracking |
| **CoursePrerequisite** | Course (self-reference), Term | Course prerequisites |
| **StudentCourseOverride** | StudentProfile, Course, CustomUser, Term | Individual course overrides |

### 1.6 Grading App (`apps/grading/`)
**Purpose:** Grade management, scales, and GPA calculation

| Model | Primary Dependencies | Description |
|-------|---------------------|-------------|
| **GradingScale** | None | Grading scale definitions |
| **GradeConversion** | GradingScale | Grade conversion rules |
| **Grade** | StudentEnrollment, GradingScale, CustomUser | Individual grades |
| **GradeChangeHistory** | Grade, CustomUser | Grade change audit trail |
| **GPARecord** | StudentProfile, Term | GPA calculations |
| **GradeSubmissionWindow** | Term, Course, SchoolStructuralUnit | Grade submission deadlines |
| **CurveControlPolicy** | Course | Grade curve policies |
| **GradeImportJob** | Term, CustomUser | Bulk grade import tracking |
| **LanguageProgramGradingConfig** | Term | Language program grade rules |
| **ClassHeaderFinalGrade** | ClassHeader, StudentProfile, CustomUser | Language program final grades |
| **GradeCalculationLog** | ClassHeader, StudentProfile, ClassHeaderFinalGrade, CustomUser | Grade calculation audit |

### 1.7 Attendance App (`apps/attendance/`)
**Purpose:** Mobile-based attendance tracking with geolocation

| Model | Primary Dependencies | Description |
|-------|---------------------|-------------|
| **ProgramAttendanceSettings** | None | Program-specific attendance rules |
| **AttendanceSession** | ClassPart, TeacherProfile | Individual class sessions |
| **AttendanceCode** | AttendanceSession | Teacher-generated attendance codes |
| **AttendanceRecord** | AttendanceSession, StudentProfile, AttendanceCode | Student attendance records |
| **PermissionRequest** | StudentProfile, AttendanceSession, ClassPart, CustomUser | Excused absence requests |
| **AttendanceSync** | AttendanceSession | Mobile sync status tracking |
| **AttendanceArchive** | ClassPart, StudentProfile, Term | Archived attendance data |

### 1.8 Student Documents App (`apps/student_documents/`)
**Purpose:** Document verification and ordering system

| Model | Primary Dependencies | Description |
|-------|---------------------|-------------|
| **DocumentTemplate** | CustomUser | Available document types |
| **DocumentOrder** | followup.FollowUp, StudentProfile, DocumentTemplate, CustomUser | Document order tracking |
| **IdentityVerificationSubmission** | followup.FollowUp, StudentProfile, CustomUser | Identity verification requests |
| **DocumentValidationRule** | DocumentTemplate | Document ordering validation |

### 1.9 FollowUp App (`apps/followup/`)
**Purpose:** Task and ticket management system

| Model | Primary Dependencies | Description |
|-------|---------------------|-------------|
| **FollowUpTicket** | StudentProfile, CustomUser | Support tickets |
| **FollowUpComment** | FollowUpTicket, CustomUser | Ticket comments |
| **FollowUpCategory** | None | Ticket categories |

### 1.10 Additional Apps

**Surveys App:** Survey management models  
**Outreach App:** Marketing and outreach tracking  
**Checkin App:** Student check-in system  
**Level Testing App:** Language level assessment  
**Dashboard App:** Dashboard widgets and analytics  

## 2. Circular Dependencies Analysis

### 2.1 Critical Circular Dependencies

#### **Circular Chain #1: Core ↔ Finance**
```
core.SponsoredStudent → finance.Scholarship
finance.Scholarship → core.StudentProfile  
finance.StudentDiscountEligibility → core.StudentProfile
```
**Impact:** High - Prevents independent deployment and testing

#### **Circular Chain #2: Core ↔ Scheduling**
```
core.StudentProfile → scheduling.StudentEnrollment (reverse FK)
core.TeacherProfile → scheduling.ClassPart
scheduling.ClassHeader → core.Course
scheduling.ClassPart → core.TeacherProfile
```
**Impact:** High - Core scheduling logic tightly coupled

#### **Circular Chain #3: Core ↔ Academic**
```
core.SchoolStructuralUnit → academic.Requirement
academic.Requirement → core.Course
academic.StudentRequirementFulfillment → core.StudentProfile
```
**Impact:** Medium - Academic tracking depends on core models

#### **Circular Chain #4: Core ↔ Grading**
```
core.SchoolStructuralUnit → grading.GradingScale
grading.Grade → scheduling.StudentEnrollment
grading.ClassHeaderFinalGrade → scheduling.ClassHeader
```
**Impact:** Medium - Grade management tightly coupled

#### **Circular Chain #5: Scheduling ↔ Grading**
```
scheduling.StudentEnrollment → grading.Grade
grading.GradeCalculationLog → scheduling.ClassHeader
grading.ClassHeaderFinalGrade → scheduling.ClassHeader
```
**Impact:** High - Grade management cannot work without scheduling

#### **Circular Chain #6: Finance ↔ Scheduling**
```
finance.ScholarshipTransaction → scheduling.StudentEnrollment (via content type)
finance.DiscountUsage → scheduling.StudentEnrollment (via content type)
```
**Impact:** Medium - Financial tracking depends on enrollment

#### **Circular Chain #7: Core ↔ Attendance**
```
core.StudentProfile → attendance.AttendanceRecord
core.TeacherProfile → attendance.AttendanceSession
attendance.AttendanceSession → scheduling.ClassPart
```
**Impact:** Medium - Attendance tracking coupled to scheduling

#### **Circular Chain #8: Student Documents ↔ FollowUp**
```
student_documents.DocumentOrder → followup.FollowUp
student_documents.IdentityVerificationSubmission → followup.FollowUp
```
**Impact:** Low - Workflow dependency

#### **Circular Chain #9: Finance ↔ FollowUp**
```
finance.AdminDocumentOrder → followup.FollowUp
```
**Impact:** Low - Administrative workflow

#### **Circular Chain #10: Academic ↔ Scheduling**
```
academic.StudentRequirementFulfillment → scheduling.StudentEnrollment
academic.CoursePrerequisite → core.Course (shared dependency)
```
**Impact:** Medium - Academic tracking needs enrollment data

#### **Circular Chain #11: Core ↔ Accounts**
```
core.PersonEventLog → accounts.CustomUser
core.StudentAuditLog → accounts.CustomUser
accounts.UserRole → core models (via generic FKs)
```
**Impact:** Low - Audit trail dependencies

#### **Circular Chain #12: Multi-app Generic FK Dependencies**
```
finance.DiscountUsage → ContentType (any model)
finance.ScholarshipTransaction → ContentType (any model)
accounts.RolePermission → ContentType (any model)
```
**Impact:** Medium - Generic relationships create implicit coupling

### 2.2 Dependency Visualization

```
                    ┌─────────────┐
                    │   ACCOUNTS  │◄─────────┐
                    │   (Users)   │          │
                    └─────────────┘          │
                           │                 │
                           ▼                 │
    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
    │   FINANCE   │◄─┤    CORE     │─►│  SCHEDULING │
    │ (Discounts) │  │ (Students)  │  │  (Classes)  │
    └─────────────┘  └─────────────┘  └─────────────┘
           │              │ ▲                │ ▲
           │              ▼ │                ▼ │
           │         ┌─────────────┐  ┌─────────────┐
           │         │  ACADEMIC   │  │   GRADING   │
           │         │(Requirements)│  │  (Grades)   │
           │         └─────────────┘  └─────────────┘
           │              │                 │
           │              ▼                 │
           │         ┌─────────────┐        │
           │         │ ATTENDANCE  │        │
           │         │  (Records)  │        │
           │         └─────────────┘        │
           │                               │
           ▼                               │
    ┌─────────────┐                       │
    │  FOLLOWUP   │◄──────────────────────┘
    │ (Tickets)   │
    └─────────────┘
           ▲
           │
    ┌─────────────┐
    │ STUDENT_DOCS│
    │(Verification)│
    └─────────────┘
```

## 3. Current App Purposes and Responsibilities

### 3.1 Well-Defined Apps ✅

**Accounts (`apps/accounts/`)**
- **Purpose:** User authentication and authorization
- **Responsibility:** Clear and focused
- **Issues:** None significant

**Attendance (`apps/attendance/`)**
- **Purpose:** Mobile attendance tracking
- **Responsibility:** Well-defined domain
- **Issues:** Depends on scheduling models

**Student Documents (`apps/student_documents/`)**
- **Purpose:** Document ordering and verification
- **Responsibility:** Clear workflow management
- **Issues:** Depends on followup for tickets

### 3.2 Problematic Apps ⚠️

**Core (`apps/core/`)**
- **Purpose:** ❌ **UNCLEAR** - Contains everything from people to courses to facilities
- **Issues:**
  - **Mixed responsibilities:** People, academics, facilities, geography
  - **Too large:** 25+ models with different concerns
  - **Central dependency:** Every other app depends on it
  - **Circular dependencies** with most other apps

**Finance (`apps/finance/`)**
- **Purpose:** ⚠️ **MIXED** - Financial transactions, discounts, AND administrative packages
- **Issues:**
  - **Administrative packages** should be separate concern
  - **Tight coupling** to core student models
  - **Generic foreign keys** create hidden dependencies

**Scheduling (`apps/scheduling/`)**
- **Purpose:** ⚠️ **MIXED** - Class scheduling AND enrollment management
- **Issues:**
  - **Enrollment management** could be separate from scheduling
  - **Reading class logic** adds complexity
  - **Tight coupling** to core and grading apps

**Academic (`apps/academic/`)**
- **Purpose:** ⚠️ **OVERLAPPING** - Requirements tracking duplicates some core functionality
- **Issues:**
  - **Duplicate models:** TransferCredit exists in both core and academic
  - **CoursePrerequisite** duplicated across apps
  - **Unclear boundary** with core app

**Grading (`apps/grading/`)**
- **Purpose:** ⚠️ **MIXED** - Grade management AND language program specific logic
- **Issues:**
  - **Language-specific models** should be in separate app
  - **Tight coupling** to scheduling models
  - **Complex dependencies** on multiple apps

### 3.3 Responsibility Matrix

| App | People | Courses | Scheduling | Grades | Finance | Admin |
|-----|--------|---------|------------|--------|---------|-------|
| **core** | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **academic** | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **scheduling** | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **grading** | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| **finance** | ❌ | ❌ | ❌ | ❌ | ✅ | ⚠️ |
| **accounts** | ⚠️ | ❌ | ❌ | ❌ | ❌ | ✅ |

**Legend:** ✅ Appropriate, ⚠️ Partial/Unclear, ❌ Inappropriate

## 4. Clean Architecture Design

### 4.1 Proposed App Structure

```
├── people/           # Person, profiles, contacts
├── academic/         # Courses, programs, terms, requirements  
├── enrollment/       # Student enrollments and registration
├── scheduling/       # Class scheduling and room management
├── grading/          # Grade management and GPA calculation
├── finance/          # Financial transactions and billing
├── scholarships/     # Scholarship and discount management
├── attendance/       # Attendance tracking (keep current)
├── documents/        # Document services (rename from student_documents)
├── workflow/         # Task management (rename from followup)
├── facilities/       # Buildings, rooms, equipment
├── geography/        # Provinces, locations
├── accounts/         # Users and permissions (keep current)
├── common/           # Shared utilities and base models
```

### 4.2 Dependency Hierarchy

```
Level 1 (Foundation):
├── common/          # Base models, utilities
├── accounts/        # Users, permissions
├── geography/       # Locations, provinces
└── facilities/      # Buildings, rooms

Level 2 (Core Domain):
├── people/          # Person, contacts (depends on geography)
└── academic/        # Courses, terms, requirements

Level 3 (Business Logic):
├── enrollment/      # Student enrollment (depends on people, academic)
├── scheduling/      # Class scheduling (depends on people, academic, facilities)
├── scholarships/    # Scholarships and discounts (depends on people)
└── finance/         # Financial transactions (depends on people, scholarships)

Level 4 (Operational):
├── grading/         # Grades (depends on enrollment, scheduling)
├── attendance/      # Attendance (depends on scheduling, people)
├── documents/       # Document services (depends on people, workflow)
└── workflow/        # Task management (depends on people, accounts)
```

### 4.3 Model Migration Plan

#### **4.3.1 New `people/` App**
**Move from `core/`:**
- Person
- StudentProfile  
- TeacherProfile
- StaffProfile
- EmergencyContact
- PhoneNumber
- PersonEventLog
- StudentAuditLog
- FeedbackContact

#### **4.3.2 Enhanced `academic/` App**
**Move from `core/`:**
- SchoolStructuralUnit
- Term
- Course
- MajorRequirement
- CoursePrerequisite
- CourseProgression
- CourseProgressionPrerequisite
- EquivalentCourse
- Textbook

**Keep existing:**
- All current academic models

#### **4.3.3 New `enrollment/` App**
**Move from `core/`:**
- ProgramEnrollment
- StudentCourseEligibility
- TransferCredit

**Move from `scheduling/`:**
- StudentEnrollment
- ClassPartEnrollment

#### **4.3.4 New `scholarships/` App**
**Move from `finance/`:**
- Discount
- StudentDiscountEligibility  
- DiscountUsage
- ScholarshipType
- Scholarship
- ScholarshipTransaction
- TermDiscountValue

**Move from `core/`:**
- Sponsor
- SponsorDiscount
- SponsoredStudent

#### **4.3.5 Refined `finance/` App**
**Keep:**
- Payment processing models
- Billing and invoicing
- Fee management

**Move out:**
- All scholarship/discount models → `scholarships/`
- Administrative packages → `documents/`

#### **4.3.6 New `facilities/` App**
**Move from `core/`:**
- Building
- Room

#### **4.3.7 New `geography/` App**
**DEPRECATED - Province model has been replaced with ENUM in apps/common/constants.py**
**Move from `core/`:**
- ~~Province~~ (deprecated, now using ProvinceChoices enum)
- University (if location-related)

#### **4.3.8 Refined `scheduling/` App**
**Keep:**
- ClassHeader
- ClassPart
- ClassHeaderTemplate
- ClassPartTemplate
- CombinedClassGroup
- ReadingClass
- RoomSchedule

**Move out:**
- StudentEnrollment → `enrollment/`
- ClassPartEnrollment → `enrollment/`

#### **4.3.9 Enhanced `documents/` App**
**Rename from:** `student_documents/`
**Move from `finance/`:**
- AdministrativePackageType
- DocumentTypeLimit
- StudentPackageAssignment
- AdminDocumentOrder

#### **4.3.10 New `workflow/` App**
**Rename from:** `followup/`
**Keep all current models**

### 4.4 Breaking Circular Dependencies

#### **Strategy 1: Reverse Foreign Keys**
Replace direct FKs with reverse lookups where appropriate:

```python
# Instead of:
class StudentProfile(models.Model):
    enrollments = models.ForeignKey(StudentEnrollment)

# Use:
class StudentEnrollment(models.Model):
    student = models.ForeignKey(StudentProfile, related_name='enrollments')

# Access via: student.enrollments.all()
```

#### **Strategy 2: Generic Foreign Keys → Specific FKs**
Replace generic relationships with explicit ones:

```python
# Instead of:
class DiscountUsage(models.Model):
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey()

# Use:
class DiscountUsage(models.Model):
    enrollment = models.ForeignKey(StudentEnrollment, null=True)
    invoice = models.ForeignKey(Invoice, null=True)
    # Other specific relationships
```

#### **Strategy 3: Interface/Protocol Pattern**
Define interfaces for cross-app communication:

```python
# In common/interfaces/
class Enrollable(Protocol):
    def get_student(self) -> StudentProfile: ...
    def get_amount_due(self) -> Decimal: ...

# Use in apps that need to work with enrollable objects
```

#### **Strategy 4: Event-Driven Communication**
Use Django signals for cross-app communication:

```python
# enrollment/signals.py
from django.dispatch import Signal

student_enrolled = Signal(providing_args=["student", "enrollment"])

# grading/receivers.py
@receiver(student_enrolled)
def create_grade_record(sender, student, enrollment, **kwargs):
    # Create grade record when student enrolls
```

## 5. Detailed Refactoring Plan

### 5.1 Phase 1: Foundation Apps (Weeks 1-2)

#### **Step 1.1: Create Foundation Apps**
```bash
python manage.py startapp geography
python manage.py startapp facilities  
python manage.py startapp people
```

#### **Step 1.2: Move Geography Models**
1. Move `Province` from `core/` to `geography/`
2. Update all imports across codebase
3. Create migration to preserve data
4. Test all related functionality

#### **Step 1.3: Move Facilities Models**
1. Move `Building`, `Room` from `core/` to `facilities/`
2. Update scheduling app dependencies
3. Test room scheduling functionality

#### **Step 1.4: Move People Models**
1. Move person-related models from `core/` to `people/`
2. This is the most complex migration due to extensive dependencies
3. Update imports in all dependent apps
4. Extensive testing required

**Migration Strategy:**
```python
# Migration approach for moving models between apps
# 1. Create new model in target app
# 2. Create data migration to copy data
# 3. Update foreign key references
# 4. Remove old model
# 5. Clean up migrations

# Example migration for Province model
class Migration(migrations.Migration):
    operations = [
        # Step 1: Create in geography app
        migrations.CreateModel(
            name='Province',
            fields=[...],
            options={'db_table': 'core_province'},  # Keep same table
        ),
        # Step 2: Update foreign keys
        migrations.AlterField(
            model_name='person',
            name='birth_province',
            field=models.ForeignKey('geography.Province', ...),
        ),
    ]
```

### 5.2 Phase 2: Academic Restructure (Weeks 3-4)

#### **Step 2.1: Enhance Academic App**
1. Move course-related models from `core/` to `academic/`
2. Resolve duplicate models (merge academic.TransferCredit with core.TransferCredit)
3. Consolidate course prerequisite logic

#### **Step 2.2: Create Enrollment App**
1. Create new `enrollment/` app
2. Move enrollment-related models from `core/` and `scheduling/`
3. Update dependencies in grading and attendance apps

### 5.3 Phase 3: Business Logic Apps (Weeks 5-7)

#### **Step 3.1: Create Scholarships App**
1. Extract scholarship/discount logic from `finance/`
2. Move sponsor models from `core/`
3. Update finance app to depend on scholarships

#### **Step 3.2: Refactor Finance App**
1. Remove scholarship models (moved to scholarships app)
2. Move administrative package models to documents app
3. Focus purely on billing, invoicing, and payments

#### **Step 3.3: Refactor Scheduling App**
1. Remove enrollment models (moved to enrollment app)
2. Focus on class scheduling, room management, templates
3. Update grading dependencies

### 5.4 Phase 4: Operational Apps (Weeks 8-9)

#### **Step 4.1: Update Grading App**
1. Remove language-specific grading logic to separate app
2. Update dependencies to use enrollment app
3. Simplify grade management

#### **Step 4.2: Enhance Documents App**
1. Rename from student_documents
2. Move administrative package models from finance
3. Update workflow dependencies

#### **Step 4.3: Rename FollowUp to Workflow**
1. Rename app for clarity
2. No model changes needed

### 5.5 Phase 5: Testing and Validation (Week 10)

#### **Step 5.1: Comprehensive Testing**
1. Run full test suite
2. Test all major workflows
3. Performance testing
4. Database integrity checks

#### **Step 5.2: Documentation Updates**
1. Update architectural documentation
2. Update API documentation
3. Update development guidelines

## 6. Migration Strategy

### 6.1 Database Migration Approach

#### **Option A: In-Place Migration (Recommended)**
- Keep existing database tables
- Use `db_table` meta option to maintain table names
- Gradually update foreign key references
- Minimal downtime

#### **Option B: Fresh Migration**
- Create new database schema
- Data migration scripts
- Higher risk but cleaner result

### 6.2 Code Migration Steps

1. **Create new apps** with proper structure
2. **Copy models** to new locations with `db_table` meta
3. **Update imports** gradually across codebase
4. **Create data migrations** where necessary
5. **Remove old models** after verification
6. **Clean up migrations** and optimize

### 6.3 Testing Strategy

```python
# Example test structure for migration validation
class ModelMigrationTests(TestCase):
    def test_person_model_moved_correctly(self):
        # Test that Person model works in new location
        person = people.models.Person.objects.create(...)
        self.assertIsNotNone(person.id)
    
    def test_foreign_key_references_updated(self):
        # Test that FK references still work
        student = people.models.StudentProfile.objects.create(...)
        enrollment = enrollment.models.StudentEnrollment.objects.create(
            student=student
        )
        self.assertEqual(enrollment.student, student)
    
    def test_reverse_relationships_work(self):
        # Test reverse FK relationships
        student = people.models.StudentProfile.objects.create(...)
        enrollments = student.enrollments.all()
        self.assertIsNotNone(enrollments)
```

## 7. Risk Assessment

### 7.1 High Risk Areas

#### **Person/Student Model Migration** 
- **Risk:** Critical models used throughout system
- **Mitigation:** Extensive testing, staged rollout, rollback plan

#### **Foreign Key Updates**
- **Risk:** Broken relationships, data loss
- **Mitigation:** Backup database, FK validation scripts, phased migration

#### **Import Statement Updates**
- **Risk:** Runtime errors from missing imports
- **Mitigation:** Search and replace scripts, comprehensive test coverage

### 7.2 Medium Risk Areas

#### **Generic Foreign Key Replacement**
- **Risk:** Complex logic changes required
- **Mitigation:** Gradual replacement, maintain backward compatibility

#### **Signal/Event System Implementation**
- **Risk:** New architecture complexity
- **Mitigation:** Start with simple signals, comprehensive documentation

### 7.3 Low Risk Areas

#### **App Renaming**
- **Risk:** Minimal technical risk
- **Mitigation:** Update configuration and imports

#### **Documentation Updates**
- **Risk:** No technical risk
- **Mitigation:** Update in parallel with code changes

## 8. Rollback Considerations

### 8.1 Rollback Strategy

1. **Database Backups** before each phase
2. **Migration Reversibility** for all database changes
3. **Code Branch Strategy** with ability to revert
4. **Feature Flags** for new architecture components

### 8.2 Rollback Triggers

- **Performance degradation** > 20%
- **Test failures** > 5% of test suite
- **Production errors** related to migration
- **Data integrity issues**

## 9. Implementation Timeline

### 9.1 Estimated Timeline: 10 Weeks

| Phase | Duration | Risk Level | Dependencies |
|-------|----------|------------|--------------|
| Phase 1: Foundation | 2 weeks | Medium | None |
| Phase 2: Academic | 2 weeks | Medium | Phase 1 |
| Phase 3: Business Logic | 3 weeks | High | Phase 1, 2 |
| Phase 4: Operational | 2 weeks | Medium | Phase 3 |
| Phase 5: Testing | 1 week | Low | All phases |

### 9.2 Resource Requirements

- **2 Senior Django Developers** (full-time)
- **1 Database Administrator** (part-time)
- **1 QA Engineer** (part-time phases 3-5)
- **1 DevOps Engineer** (part-time for deployment)

### 9.3 Success Metrics

- **Zero data loss** during migration
- **No increase** in test suite runtime
- **No performance degradation** > 5%
- **All existing functionality** preserved
- **Reduced circular dependencies** to zero
- **Improved code maintainability** scores

## 10. Conclusion

The current Django model architecture in Naga backend requires significant refactoring to address critical circular dependencies and unclear app boundaries. The proposed clean architecture will:

✅ **Eliminate all circular dependencies**  
✅ **Improve code maintainability and testability**  
✅ **Enable independent app development and deployment**  
✅ **Provide clear separation of concerns**  
✅ **Support future scaling and feature development**  

**Recommendation:** Proceed with the proposed refactoring plan with careful attention to risk mitigation and comprehensive testing at each phase.

**Next Steps:**
1. **Stakeholder approval** for 10-week timeline and resource allocation
2. **Detailed technical planning** for Phase 1 implementation
3. **Team assignment** and responsibility matrix
4. **Development environment** setup for parallel architecture work

---

**Prepared by:** Claude Code Analysis  
**Review Required:** Senior Architecture Team  
**Priority:** Critical - Technical Debt Resolution