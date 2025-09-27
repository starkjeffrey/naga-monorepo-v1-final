# Academic App Legacy Cleanup Documentation

This document tracks the removal of the old flexible requirement system in favor of the new canonical requirement system.

## Summary

The academic app has been refactored to remove the old flexible requirement system and replace it with a cleaner canonical requirement system. This follows the architectural principle: **"Canonical as default, exception as override"**.

## Removed Legacy Models

### From the Old Flexible System:

1. **RequirementType** - Part of the old flexible requirement categorization
2. **Requirement** - The old flexible requirement model with complex many-to-many relationships
3. **RequirementCourse** - The junction table for the old many-to-many relationship

## CORRECTION: StudentRequirementFulfillment Status

Initially, I mistakenly identified `StudentRequirementFulfillment` as a legacy model to be removed. However, after clarification from the user, I understand that:

- **StudentRequirementFulfillment** was intended as a NEW model to track when specific requirements are fulfilled
- It serves a critical function: comparing fulfilled requirements against canonical requirements to determine what courses students still need

### New Architecture Solution

Instead of using the old `StudentRequirementFulfillment` model, I've created a new `CanonicalRequirementFulfillment` model that better fits the canonical architecture:

```python
class CanonicalRequirementFulfillment(AuditModel):
    """Tracks how a student fulfills a specific canonical requirement."""
    student = models.ForeignKey("people.StudentProfile", ...)
    canonical_requirement = models.ForeignKey("academic.CanonicalRequirement", ...)
    fulfillment_method = models.CharField(...)  # COURSE, TRANSFER, SUBSTITUTION, WAIVER, EXAM
    fulfillment_date = models.DateField(...)

    # Links to fulfillment sources
    fulfilling_enrollment = models.ForeignKey("enrollment.ClassHeaderEnrollment", ...)
    fulfilling_transfer = models.ForeignKey("academic.TransferCredit", ...)
    fulfilling_exception = models.ForeignKey("academic.StudentRequirementException", ...)

    credits_earned = models.DecimalField(...)
    grade = models.CharField(...)
```

This new model:

- Directly links to canonical requirements (cleaner than the old system)
- Tracks multiple fulfillment methods
- Maintains referential integrity with proper foreign keys
- Supports the comparison logic needed to determine remaining requirements

## New Canonical Models

The new system uses these models:

1. **CanonicalRequirement** - Rigid 43-course BA degree requirements
2. **StudentDegreeProgress** - Streamlined progress tracking
3. **StudentRequirementException** - Handles all deviations from canonical
4. **StudentCourseOverride** - Course substitution approvals
5. **TransferCredit** - External credit recognition
6. **CourseEquivalency** - Course mapping for transfers

## Files Modified

### Core Application Files:

- ✅ `/apps/enrollment/services.py` - Updated all references from old models to new
  - Replaced `StudentRequirementFulfillment` with `TransferCredit` and `StudentCourseOverride`
  - Replaced `Requirement` with `CanonicalRequirement`

### Deprecated Files (To Be Removed):

- `models_old.py` - Contains old models
- `canonical_models_old.py` - Old canonical implementation
- `services_old.py` - Old service implementations
- `canonical_services_old.py` - Old canonical services
- `admin_old.py` - Old admin interfaces

### Deprecated Management Commands:

- ⚠️ `populate_student_requirements.py` - Uses StudentRequirementFulfillment
- ⚠️ `populate_course_fulfillments.py` - Uses StudentRequirementFulfillment

### Test Files Needing Updates:

- `test_simple.py` - Imports RequirementType, StudentRequirementFulfillment
- `tests.py` - References old models
- `factories.py` - Contains factories for old models
- `/apps/enrollment/test_services.py` - Imports Requirement, RequirementCourse, RequirementType

## Migration Strategy

### Phase 1: Code Updates ✅

- [x] Create new model structure
- [x] Create new service layer
- [x] Update all imports in active code
- [x] Mark deprecated commands

### Phase 2: Data Migration (Pending)

- [ ] Create migration to convert RequirementType data to CanonicalRequirement metadata
- [ ] Create migration to convert StudentRequirementFulfillment to StudentDegreeProgress
- [ ] Migrate existing transfer credits and overrides

### Phase 3: Cleanup (Pending)

- [ ] Remove old model files
- [ ] Remove deprecated management commands
- [ ] Update or remove old test files
- [ ] Clean up migration files

## API Changes

### Old Pattern:

```python
# Complex requirement checking with flexible types
requirement = Requirement.objects.filter(
    requirement_type__code='CORE',
    requirement_courses__course=course,
    major=major
)

# Progress tracking through fulfillment records
fulfillment = StudentRequirementFulfillment.objects.create(
    student=student,
    requirement=requirement,
    fulfilling_course=course,
    fulfillment_source='COURSE_COMPLETION'
)
```

### New Pattern:

```python
# Simple canonical requirement lookup
requirement = CanonicalRequirement.objects.filter(
    major=major,
    required_course=course,
    is_active=True
)

# Progress automatically tracked in StudentDegreeProgress
progress = CanonicalRequirementService.update_degree_progress(student, major)
```

## Benefits of the New System

1. **Simpler Data Model**: Direct relationships instead of many-to-many
2. **Better Performance**: Optimized queries with proper prefetching
3. **Clearer Business Logic**: "Canonical as default, exception as override"
4. **Mobile App Ready**: Clean API for degree audit generation
5. **Reduced Complexity**: No more flexible requirement types to manage

## Next Steps

1. Update remaining test files to use new models
2. Create data migration scripts for production
3. Remove deprecated files after successful migration
4. Update API documentation for mobile app integration
