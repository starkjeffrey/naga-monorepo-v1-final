# Academic App Cleanup Notes

This document tracks the cleanup and reorganization of the academic app.

## Completed Work

### 1. Created New Model Structure

- `models/canonical.py` - Canonical requirements and degree progress
- `models/transfer.py` - Transfer credits and course equivalencies
- `models/exceptions.py` - Student exceptions and overrides
- `models/__init__.py` - Exports all models

### 2. Created New Service Structure

- `services/canonical.py` - Canonical requirement services
- `services/transfer.py` - Transfer credit services
- `services/exceptions.py` - Exception management services
- `services/degree_audit.py` - Mobile app integration services
- `services/__init__.py` - Exports all services

### 3. Refactored Admin

- Removed code duplication with generic filter factory
- Updated to use service layer for approvals/rejections
- Removed references to deprecated models

### 4. Updated Constants

- Added BA/MA degree requirements
- Added completion percentage thresholds
- Moved hardcoded values from code

## Legacy Elements to Remove

### Models to Remove (from models_old.py)

- [x] RequirementType - Part of old flexible requirement system
- [x] Requirement - Old flexible requirement model
- [x] RequirementCourse - Old many-to-many junction table
- [x] StudentRequirementFulfillment - References removed Requirement model
- [x] Business logic in models (approve/reject methods)

### Code to Clean

- [x] Remove imports of deprecated models from enrollment/services.py
- [x] Mark deprecated management commands
- [ ] Update test files that import old models
- [ ] Clean up migration files

### Files to Remove After Migration

- models_old.py
- canonical_models_old.py
- services_old.py
- canonical_services_old.py
- admin_old.py

## Migration Plan

### Phase 1: Data Migration

1. Create migration to convert RequirementType data to CanonicalRequirement metadata
2. Create migration to convert StudentRequirementFulfillment to StudentDegreeProgress
3. Ensure all TransferCredit and StudentCourseOverride data is preserved

### Phase 2: Schema Changes

1. Drop RequirementType table
2. Drop StudentRequirementFulfillment table
3. Add any missing indexes for performance

### Phase 3: Code Cleanup

1. Remove old model files
2. Update all imports
3. Run tests to ensure everything works

## API Considerations for Mobile App

The new service layer provides clean APIs for the mobile app:

### DegreeAuditService.generate_mobile_audit()

- Returns comprehensive degree audit optimized for mobile
- Includes progress tracking, requirements, exceptions
- JSON-serializable output

### Key Mobile Endpoints Needed

1. GET /api/degree-audit/{student_id}/ - Get degree audit
2. GET /api/degree-progress/{student_id}/ - Get progress summary
3. GET /api/requirements/{major_id}/ - Get major requirements
4. GET /api/exceptions/{student_id}/ - Get student exceptions

## Testing Strategy

### Unit Tests Needed

1. Model validation tests
2. Service logic tests
3. Admin action tests

### Integration Tests Needed

1. Degree audit generation
2. Progress calculation
3. Exception approval workflow
4. Transfer credit workflow

### Performance Tests

1. Degree audit with many requirements
2. Bulk progress updates
3. Query optimization validation
