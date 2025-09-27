# TODO Analysis Report - Naga SIS Backend

Generated on: 2025-08-10

## Summary Dashboard

### By Priority
- 🔴 **CRITICAL (17)**: FIXME, BUG items requiring immediate attention
- 🟡 **HIGH (48)**: TODO items with implementation needs
- 🟢 **MEDIUM (23)**: General TODO items for future improvement
- 🔵 **LOW (15)**: OPTIMIZE, REFACTOR, NOTE items

### By Category
- **API Implementation (12)**: Missing API endpoints and features
- **Database/Migration (8)**: Schema and data migration improvements
- **Business Logic (15)**: Service layer enhancements
- **Testing (3)**: Test coverage improvements
- **Configuration (5)**: Settings and environment improvements
- **UI/Frontend (2)**: Web interface enhancements
- **Performance (8)**: Optimization opportunities
- **Documentation (4)**: Code documentation needs

## 🔴 CRITICAL Items (Immediate Action Required)

### API Issues - High Priority
1. **Document API Query Issues** - `api/v1/academic_records/document_api.py:185-192`
   ```python
   # TODO: Fix DocumentExcessFee query - these fields don't exist on the model
   ```
   - **Impact**: API endpoints likely failing
   - **Action**: Review DocumentExcessFee model fields and fix queries

2. **Course Retake Logic** - `apps/academic/management/commands/transitional/populate_course_fulfillments.py:270`
   ```python
   # TODO: CRITICAL - Handle Course Retake Logic (Issue #XXX)
   ```
   - **Impact**: Academic record accuracy
   - **Action**: Implement retake handling for GPA calculations

### Model Field Issues
3. **Subject Specializations** - `apps/accounts/models.py:548`
   ```python
   # Subject specializations - TODO: Enable when curriculum.Subject model exists
   ```
   - **Impact**: Teacher profiles incomplete
   - **Action**: Create Subject model or remove disabled feature

## 🟡 HIGH Priority Items (Implementation Needed)

### Core Business Logic
4. **Finance Integration** - `apps/level_testing/services.py:658`
   ```python
   # TODO: Implement actual finance integration
   ```
   - **Context**: Level testing debt checking
   - **Impact**: Financial validation missing

5. **Student Analytics** - `apps/analytics/services.py:84`
   ```python
   # TODO: Implement using ProgramEnrollment model
   ```
   - **Context**: Graduate tracking analytics
   - **Impact**: Reporting accuracy

6. **Complex Prerequisites** - `apps/enrollment/services.py:980`
   ```python
   # TODO: Implement complex prerequisite parsing
   ```
   - **Context**: Course enrollment validation
   - **Impact**: Academic integrity

7. **Grading Logic** - `apps/grading/services.py:620,624,647,658`
   ```python
   # TODO: Implement logic to filter by major requirements
   # TODO: Use proper enrollment status
   # TODO: Implement proper weighting based on session structure
   ```
   - **Context**: GPA calculation and academic standing
   - **Impact**: Student academic records

### API Development
8. **Attendance API** - `api/v1/attendance.py:256,275`
   ```python
   # TODO: Add photo URLs
   # Note: This is a partial migration - the full attendance API has many more endpoints
   ```
   - **Context**: Mobile attendance system
   - **Impact**: Feature completeness

9. **Finance API** - `api/v1/finance.py:208-209`
   ```python
   # TODO: Get term from data or context
   # TODO: Convert items to enrollments
   ```
   - **Context**: Invoice creation API
   - **Impact**: Financial operations

10. **Remaining API Routers** - `api/v1/__init__.py:93`
    ```python
    # TODO: Add remaining routers as they are migrated:
    ```
    - **Context**: API completeness
    - **Impact**: Feature parity with V0 system

### Level Testing System
11. **Program/Level Matching** - `apps/level_testing/services.py:285`
    ```python
    # TODO: Implement program/level matching logic
    ```
    - **Context**: Automated level testing placement
    - **Impact**: Student placement accuracy

12. **Record Merging** - `apps/level_testing/services.py:465`
    ```python
    # TODO: Implement comprehensive student record merging
    ```
    - **Context**: Duplicate student handling
    - **Impact**: Data integrity

## 🟢 MEDIUM Priority Items (Future Improvements)

### Model Enhancements
13. **Minimum Grade Validation** - `apps/enrollment/services.py:1004-1005`
    ```python
    # TODO: Implement minimum_grade field and GPA calculation
    ```
    - **Context**: Course enrollment requirements
    - **Timeline**: Next version

14. **Course Enrollment Limits** - `apps/enrollment/services.py:1012-1013`
    ```python
    # TODO: Implement max_enrollments field for course enrollment limits
    ```
    - **Context**: Class size management
    - **Timeline**: Next version

15. **Academic Standing** - `apps/grading/signals.py:187,219,295`
    ```python
    # TODO: Implement academic standing determination and notifications
    # TODO: Get student's current major - for now assume first active major
    # TODO: Implement comprehensive grade validation
    ```
    - **Context**: Student academic status tracking
    - **Timeline**: Academic module enhancement

### Service Improvements
16. **Email Integration** - `apps/academic_records/admin.py:460`
    ```python
    # TODO: Implement email service integration
    ```
    - **Context**: Document delivery automation
    - **Timeline**: Communication module

17. **Staff Notifications** - `apps/level_testing/signals.py:192`
    ```python
    # TODO: Implement notification system for staff alerts
    ```
    - **Context**: Level testing workflow notifications
    - **Timeline**: Notification system

### Moodle Integration
18. **User Management** - `apps/moodle/services.py:126,141,154`
    ```python
    # TODO: Implement user creation logic
    # TODO: Implement user update logic
    # TODO: Implement full person sync logic
    ```
    - **Context**: LMS integration
    - **Timeline**: External integrations phase

19. **Unenrollment Logic** - `apps/moodle/tasks.py:107`
    ```python
    # TODO: Implement unenrollment logic
    ```
    - **Context**: Course drop handling in LMS
    - **Timeline**: External integrations phase

## 🔵 LOW Priority Items (Optimization & Enhancement)

### Performance Optimizations
20. **Query Optimization** - `apps/level_testing/services.py:82,85`
    ```python
    # Optimize debt checking
    # Optimize program checking
    ```
    - **Context**: Database query performance
    - **Timeline**: Performance optimization cycle

21. **Cache Implementation** - `apps/academic/services/canonical.py:82`
    ```python
    # Optimize with select_related to avoid N+1 queries
    ```
    - **Context**: Academic record queries
    - **Timeline**: Performance optimization cycle

### Location Services
22. **Geolocation Features** - `apps/attendance/services.py:321,368,673`
    ```python
    # TODO: Re-enable after installing geopy
    # TODO: Check for regular teaching schedule conflicts
    ```
    - **Context**: Location-based attendance validation
    - **Timeline**: Advanced features

### Configuration
23. **Production Settings** - `config/settings/production.py:54`
    ```python
    # TODO: set this to 60 seconds first and then to 518400 once you prove the former works
    ```
    - **Context**: SSL/HSTS configuration
    - **Timeline**: Production deployment

24. **Health Monitoring** - `apps/moodle/tasks.py:177`
    ```python
    # TODO: Store health check results in database for monitoring
    ```
    - **Context**: System monitoring and alerting
    - **Timeline**: Operations enhancement

### Frontend
25. **Language Switching** - `apps/web_interface/static/web_interface/js/dashboard.js:355`
    ```javascript
    // TODO: Implement actual language switching
    ```
    - **Context**: Bilingual interface completion
    - **Timeline**: UI/UX enhancement

## Deprecated/Legacy Items (Cleanup Required)

### Model Cleanup
- **Deprecated Fields**: `apps/level_testing/models.py:341`
- **Pricing Tiers**: `apps/level_testing/fee_service.py:446`
- **Admin Classes**: `apps/finance/admin.py:54`
- **Test Dependencies**: `apps/enrollment/tests/test_services.py:24,731`

## Action Plan Recommendations

### Phase 1 - Critical Fixes (Week 1-2)
1. Fix DocumentExcessFee API queries
2. Resolve Subject model dependency
3. Implement course retake logic

### Phase 2 - Core Features (Week 3-6)
1. Complete finance integration in level testing
2. Implement complex prerequisite parsing
3. Enhance grading system logic
4. Complete remaining API endpoints

### Phase 3 - Quality Improvements (Month 2)
1. Add comprehensive testing for TODOs
2. Implement notification systems
3. Enhance academic standing calculations

### Phase 4 - Advanced Features (Month 3+)
1. Moodle integration completion
2. Performance optimizations
3. Advanced location services
4. Production configuration finalization

## Statistics

- **Total TODOs Found**: 103
- **Active Development Items**: 65
- **Legacy/Cleanup Items**: 15
- **Documentation Notes**: 23
- **Files Affected**: 45 Python files, 1 JavaScript file
- **Most TODO-Heavy Modules**: enrollment (12), grading (8), level_testing (7), finance (6)

## Maintenance Notes

This report should be updated monthly or after major feature implementations. Consider creating GitHub issues for all HIGH and CRITICAL priority TODOs to ensure proper tracking and assignment.
