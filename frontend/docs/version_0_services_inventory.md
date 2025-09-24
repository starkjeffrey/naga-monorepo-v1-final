# Version 0 Services Inventory - Business Logic and Operational Functions

## Overview

This document provides a comprehensive inventory of all services, utilities, and business logic components from the original naga-backend (version 0) codebase. Each service is cataloged with its specific functions and business purpose to assist in planning the migration to the clean architecture version 1.0.

**Source Location**: `/Users/jeffreystark/PycharmProjects/naga-backend`  
**Analysis Date**: June 15, 2025  
**Purpose**: Migration planning and feature prioritization for Naga SIS v1.0

---

## Business Logic Categories

The services have been systematically categorized by their primary business purpose:

- **Academic Operations**: Curriculum, progress tracking, scheduling, transcripts
- **Financial Operations**: Billing, payments, pricing, fees, reporting
- **Grading and Assessment**: GPA calculation, grade processing
- **Student Services**: Support systems, check-ins, proactive interventions
- **Integration Services**: External system integration (Moodle, notifications)
- **Data Processing**: Utilities, internationalization, data conversion

---

## Academic Operations

### 1. Academic Progress Management Service
**File**: `apps/academic/services/academic_progress_service.py`

| Function | Purpose Category | Description |
|----------|-----------------|-------------|
| `get_requirements_for_student()` | Business Logic | Determines applicable curriculum requirements based on student enrollment date and major |
| `process_enrollment_grades()` | Business Logic | Processes completed course enrollments to update requirement fulfillment status |
| `process_transfer_credit()` | Business Logic | Handles approved transfer credits for requirement fulfillment |
| `evaluate_student_progress()` | Business Logic | Comprehensive re-evaluation of all student academic requirements |
| `get_unfulfilled_requirements()` | Business Logic | Identifies outstanding requirements preventing graduation |
| `handle_major_change()` | Business Logic | Manages requirement changes when students change academic majors |

**Business Value**: Tracks student progress toward degree completion, handles curriculum versioning, manages transfer credits with full audit trail.

### 2. Simplified Academic Progress Service
**File**: `apps/academic/services/simplified_academic_progress_service.py`

| Function | Purpose Category | Description |
|----------|-----------------|-------------|
| `get_student_curriculum_date()` | Business Logic | Determines which curriculum version applies to specific student |
| `get_applicable_requirements()` | Business Logic | Gets requirements based on student's curriculum effective date |
| `get_completed_courses()` | Business Logic | Retrieves courses with passing grades (grandfathered approach) |
| `check_requirement_fulfillment()` | Business Logic | Validates if specific academic requirements are met |
| `get_student_progress_summary()` | Business Logic | Creates progress summary for administrative review |
| `create_manual_override()` | Administrative Operations | Allows admin clerks to create requirement exceptions |
| `handle_major_change()` | Business Logic | Simplified major change processing workflow |

**Business Value**: Simplified academic tracking focused on practical business needs with administrative override capability for edge cases.

### 3. Course Progression and Scheduling Optimization Service
**File**: `apps/core/services/course_progression_service.py`

| Function | Purpose Category | Description |
|----------|-----------------|-------------|
| `calculate_student_eligibility()` | Business Logic | Determines course eligibility based on prerequisites and term progression |
| `generate_course_selection_options()` | Business Logic | Creates curated course recommendations prioritizing failed courses |
| `optimize_cohort_scheduling()` | Academic Operations | Optimizes course assignments to maximize class sizes and minimize conflicts |
| `_calculate_student_term_number()` | Business Logic | Tracks student progression through 14-term program structure |
| `_get_completed_courses()` | Data Processing | Academic history analysis for progression calculation |
| `_get_failed_courses()` | Data Processing | Identifies courses requiring retake with priority ranking |
| `_check_prerequisites()` | Business Logic | Validates prerequisite completion before course enrollment |
| `_calculate_retry_priority()` | Business Logic | Prioritizes failed course retakes based on program requirements |

**Business Value**: DAG-based course scheduling system with intelligent eligibility calculation and cohort optimization to minimize small classes and scheduling conflicts.

### 4. Transcript Generation Service
**File**: `apps/core/services/transcript_service.py`

| Function | Purpose Category | Description |
|----------|-----------------|-------------|
| `get_enrollment_display()` | Data Processing | Formats course enrollment information with equivalency details |
| `build_transcript()` | Academic Operations | Generates complete official transcript showing all completed courses |

**Business Value**: Official transcript generation with proper course equivalency handling for transfer students and curriculum changes.

---

## Financial Operations

### 5. Core Financial Services
**File**: `apps/finance/services/financial_service.py`

| Function | Purpose Category | Description |
|----------|-----------------|-------------|
| `create_invoice()` | Financial Operations | Creates invoices for course registration with comprehensive audit trails |
| `process_payment()` | Financial Operations | Handles payment processing, balance updates, and transaction records |
| `validate_payment_terms()` | Business Logic | Validates payment plans against business rules (minimum down payment, installment limits) |
| `_update_student_balance()` | Financial Operations | Updates student financial standing and manages registration holds |

**Business Value**: Core billing and payment processing system with comprehensive audit trails and automated hold management.

### 6. Late Fee Management Service
**File**: `apps/finance/services/financial_service.py` (LateFeeService class)

| Function | Purpose Category | Description |
|----------|-----------------|-------------|
| `calculate_late_fees()` | Financial Operations | Calculates progressive late fees based on days overdue |
| `apply_late_fees()` | Financial Operations | Automatically applies late fees to overdue invoices |
| `is_invoice_overdue()` | Business Logic | Determines if invoice is past due date based on terms |

**Business Value**: Automated late fee assessment and application with progressive penalties to encourage timely payment.

### 7. Credit Note Management Service
**File**: `apps/finance/services/financial_service.py` (CreditNoteService class)

| Function | Purpose Category | Description |
|----------|-----------------|-------------|
| `issue_credit_note()` | Financial Operations | Creates credit notes for refunds and account adjustments |
| `get_valid_credit_notes()` | Financial Operations | Retrieves applicable credit notes for students with expiration handling |
| `apply_credit_note()` | Financial Operations | Uses credit notes for transaction payments and balance adjustments |

**Business Value**: Student credit and refund management system with proper expiration handling and audit trails.

### 8. Pricing and Fee Calculation Service
**File**: `apps/finance/services/pricing_service.py`

| Function | Purpose Category | Description |
|----------|-----------------|-------------|
| `get_price_for_course()` | Business Logic | Determines course pricing based on enrollment count, course type, and special cases |
| `calculate_package_discount()` | Business Logic | Applies multi-course package discounts based on enrollment combinations |
| `_get_special_case_price()` | Business Logic | Handles special pricing rules (senior projects, reading courses, etc.) |
| `_get_matching_tier()` | Business Logic | Matches enrollment counts to dynamic pricing tiers |

**Business Value**: Sophisticated dynamic pricing system based on class size, course type, and package deals to optimize revenue and encourage enrollment.

### 9. Document Ordering and Fee Service
**File**: `apps/finance/services/document_ordering_service.py`

| Function | Purpose Category | Description |
|----------|-----------------|-------------|
| `calculate_order_fee()` | Financial Operations | Calculates fees for official document requests (transcripts, certificates) |
| `estimate_completion_time()` | Business Logic | Estimates document preparation time based on type and workload |
| `calculate_delivery_date()` | Business Logic | Calculates business-day delivery dates excluding institutional holidays |
| `create_order()` | Administrative Operations | Creates document orders with validation and workflow initiation |
| `cancel_order()` | Administrative Operations | Handles order cancellations with proper status validation |
| `update_order_status()` | Administrative Operations | Manages order workflow transitions through processing stages |

**Business Value**: Complete student document services system (transcripts, certificates, etc.) with proper workflow management and fee collection.

### 10. Financial Reporting Service
**File**: `apps/finance/services/financial_service.py` (ReportingService class)

| Function | Purpose Category | Description |
|----------|-----------------|-------------|
| `generate_aging_report()` | Reporting/Analytics | Creates accounts receivable aging analysis for management oversight |

**Business Value**: Financial reporting capabilities for administrative oversight and collection management.

---

## Grading and Assessment

### 11. GPA Calculation Service
**File**: `apps/grading/services/grade_services.py`

| Function | Purpose Category | Description |
|----------|-----------------|-------------|
| `calculate_student_gpa()` | Business Logic | Calculates term and cumulative GPA for major-specific courses |
| `update_student_gpa_record()` | Academic Operations | Updates official GPA records with comprehensive audit trails |

**Business Value**: Official GPA calculation system following institutional policies with proper major-specific course filtering.

### 12. Language Grade Calculator Service
**File**: `apps/grading/services/language_grade_calculator.py`

| Function | Purpose Category | Description |
|----------|-----------------|-------------|
| Language-specific grade calculations | Business Logic | Specialized grading rules for language proficiency courses |

**Business Value**: Specialized grading system for language programs with different assessment criteria.

### 13. Passing Grade Service
**File**: `apps/grading/services/passing_grade_service.py`

| Function | Purpose Category | Description |
|----------|-----------------|-------------|
| Passing grade determinations | Business Logic | Determines passing thresholds for different course types and programs |

**Business Value**: Flexible passing grade system accommodating different academic programs and course types.

---

## Student Services and Support

### 14. Check-in and Student Support Service
**File**: `apps/checkin/services.py`

| Function | Purpose Category | Description |
|----------|-----------------|-------------|
| `get_students_ready_for_checkin()` | Student Support | Identifies students needing staff attention based on system-defined rules |
| `create_system_recommendations()` | Student Support | Generates automated check-in recommendations for staff |
| `create_checkin()` | Student Support | Records student check-ins with proper follow-up scheduling |
| `_get_payment_overdue_students()` | Student Support | Flags students with payment issues requiring intervention |
| `_get_status_risk_students()` | Student Support | Identifies students with concerning academic status changes |
| `get_dashboard_stats()` | Reporting/Analytics | Provides staff dashboard metrics for student support overview |

**Business Value**: Proactive student support system that prevents academic and financial issues through early intervention and systematic follow-up.

---

## Scheduling and Class Management

### 15. Scheduling Service
**File**: `apps/scheduling/services/scheduling_service.py`

| Function | Purpose Category | Description |
|----------|-----------------|-------------|
| `create_class_section()` | Academic Operations | Creates new class sections with proper scheduling and resource allocation |
| `get_next_section()` | Academic Operations | Generates sequential section IDs for class organization |
| `_create_line()` | Academic Operations | Creates individual class meeting times with room and instructor assignment |

**Business Value**: Academic scheduling system with comprehensive section management and resource allocation.

### 16. Schedule Conflict Detection Service
**File**: `apps/core/services/conflict_checker.py`

| Function | Purpose Category | Description |
|----------|-----------------|-------------|
| `bulk_check_conflicts()` | Business Logic | Validates schedules for time conflicts across multiple students |
| `courses_conflict()` | Business Logic | Checks individual course time conflicts for enrollment validation |
| `get_conflicting_courses()` | Business Logic | Identifies conflicts for proposed course additions |

**Business Value**: Prevents scheduling conflicts and double-bookings to ensure students can attend all enrolled courses.

---

## Integration and External Services

### 17. Moodle LMS Integration Service
**File**: `apps/common/tasks/moodle_tasks.py`

| Function | Purpose Category | Description |
|----------|-----------------|-------------|
| `sync_student_to_moodle()` | Integration Services | Creates and updates student accounts in Moodle LMS |
| `sync_teacher_to_moodle()` | Integration Services | Manages teacher accounts and permissions in Moodle |
| `sync_class_enrollments()` | Integration Services | Synchronizes class rosters between SIS and LMS |
| `create_moodle_course_for_term()` | Integration Services | Creates course structures and categories in Moodle |
| `send_moodle_credentials()` | Notification/Communication | Emails login credentials and instructions to users |

**Business Value**: Seamless integration between SIS and LMS ensuring consistent enrollment data and user access across platforms.

### 18. Follow-up Notification Service
**File**: `apps/followup/tasks.py`

| Function | Purpose Category | Description |
|----------|-----------------|-------------|
| `echo_followup_to_telegram()` | Notification/Communication | Sends follow-up notifications via Telegram for staff coordination |

**Business Value**: Multi-channel communication system for student follow-up and staff coordination.

---

## Data Processing and Utilities

### 19. Internationalization Utilities
**File**: `apps/common/utils/name_converter.py`

| Function | Purpose Category | Description |
|----------|-----------------|-------------|
| `convert_khmer_name()` | Data Processing | Converts Limon-encoded Khmer text to proper Unicode |
| `process_csv_khmer_name()` | Data Processing | Batch processes CSV data with Khmer names for data migration |

**Business Value**: Proper handling of Cambodian student names and cultural data ensuring accurate record keeping.

### 20. Date and Time Utilities
**File**: `apps/common/utils/datetime_utils.py`

| Function | Purpose Category | Description |
|----------|-----------------|-------------|
| `get_current_date()` | Data Processing | Timezone-aware current date for consistent date handling |
| `get_current_datetime()` | Data Processing | Timezone-aware current datetime for audit trails |

**Business Value**: Consistent timezone handling across the entire system preventing date-related errors.

### 21. Term and Calendar Management Utilities
**Referenced across multiple services**

| Function | Purpose Category | Description |
|----------|-----------------|-------------|
| Academic calendar management | Academic Operations | Term dates, enrollment periods, academic year structure |
| Business day calculations | Business Logic | Working day calculations excluding holidays |
| Term progression tracking | Academic Operations | Student advancement through academic terms |

**Business Value**: Academic calendar operations with proper holiday handling and term progression tracking.

---

## Summary Statistics

### Service Distribution by Category

| Category | Number of Services | Key Focus Areas |
|----------|-------------------|-----------------|
| **Academic Operations** | 9 services | Curriculum management, progress tracking, scheduling, transcripts |
| **Financial Operations** | 7 services | Billing, payments, pricing, fees, reporting, collections |
| **Grading and Assessment** | 3 services | GPA calculation, specialized grading, passing standards |
| **Student Services** | 2 services | Proactive support, check-in systems, intervention |
| **Integration Services** | 2 services | LMS integration, multi-channel communication |
| **Data Processing** | 3 services | Internationalization, utilities, data conversion |

### Business Logic Complexity

| Complexity Level | Services | Examples |
|------------------|----------|----------|
| **High Complexity** | 8 services | Academic progress tracking, course progression optimization, dynamic pricing |
| **Medium Complexity** | 10 services | Financial processing, GPA calculation, scheduling conflict detection |
| **Low Complexity** | 8 services | Utilities, basic data processing, simple calculations |

### Integration Points

| External System | Integration Type | Business Impact |
|-----------------|------------------|-----------------|
| **Moodle LMS** | Full bi-directional sync | Critical for course delivery |
| **Telegram** | Notification delivery | Staff communication enhancement |
| **Email System** | Credential delivery | User onboarding automation |

---

## Migration Recommendations

### High Priority for Version 1.0 (Essential Business Functions)
1. **Core Financial Services** - Billing, payments, invoicing (Services #5, #6, #7)
2. **Academic Progress Tracking** - Student progress and requirements (Services #1, #2)
3. **GPA Calculation** - Official grade processing (Service #11)
4. **Scheduling Services** - Class creation and conflict detection (Services #15, #16)

### Medium Priority for Version 1.0 (Important Operational Functions)
1. **Course Progression Optimization** - Smart scheduling and eligibility (Service #3)
2. **Dynamic Pricing System** - Revenue optimization (Service #8)
3. **Student Support Services** - Proactive intervention (Service #14)
4. **Document Ordering** - Administrative services (Service #9)

### Lower Priority or Deferrable (Nice-to-Have Functions)
1. **Moodle Integration** - Can be implemented later (Service #17)
2. **Specialized Grading** - Language-specific calculations (Services #12, #13)
3. **Advanced Reporting** - Beyond basic financial reports (Service #10)
4. **Multi-channel Notifications** - Telegram integration (Service #18)

### Utility Services (Required Infrastructure)
1. **Date/Time Utilities** - Essential for all operations (Service #20)
2. **Internationalization** - Critical for Cambodian institution (Service #19)
3. **Calendar Management** - Academic operations foundation (Service #21)

---

## Decision Framework

For each service, consider:

1. **Business Criticality**: Can the institution operate without this function?
2. **User Impact**: How many users depend on this functionality daily?
3. **Revenue Impact**: Does this service directly affect financial operations?
4. **Compliance Requirements**: Is this required for accreditation or legal compliance?
5. **Implementation Complexity**: How difficult is it to rebuild in clean architecture?
6. **Dependencies**: What other services depend on this functionality?

---

*This inventory represents the comprehensive business logic and operational capabilities developed in version 0, providing a foundation for strategic migration planning to the clean architecture version 1.0.*

**Next Steps**: Review each service for migration priority, identify any missing business functions, and plan the implementation sequence for version 1.0 development.