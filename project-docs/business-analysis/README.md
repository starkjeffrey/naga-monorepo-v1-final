# Business Analysis Documentation

## 📊 Business Requirements & Domain Analysis

This directory contains business analysis, requirements documentation, and domain-specific business logic for the Naga SIS system.

## 📁 Contents

### Academic Institution Analysis
- **school_structure_250621.md** - Academic institution structure and organizational hierarchy
- **program_enrollment_service_logic.md** - Program enrollment business rules and logic

### Domain-Specific Requirements
- **business-questions-level-testing-250629.md** - Level testing system business requirements
- **absence_penalty_reset_system.md** - Attendance penalty system design and rules

## 🏫 Academic Context

### Target Institution
**Pannasastra University of Cambodia, Siem Reap Campus (PUCSR)**

### Institutional Characteristics
- **Multi-language support**: English and Khmer
- **Academic programs**: Undergraduate and graduate degrees
- **Student population**: Mixed local and international students
- **Academic calendar**: Semester-based system
- **Financial aid**: Comprehensive scholarship programs

## 🎯 Core Business Domains

### Student Lifecycle Management
- **Admissions**: Application, testing, enrollment decisions
- **Registration**: Course enrollment, schedule management
- **Academic Progress**: Grade tracking, GPA calculation, graduation requirements
- **Financial Management**: Tuition, fees, scholarships, payment tracking

### Academic Operations
- **Course Management**: Course catalog, prerequisites, capacity planning
- **Scheduling**: Class times, room assignments, instructor scheduling
- **Attendance**: QR code tracking, penalty systems, reporting
- **Grading**: Grade entry, scale management, transcript generation

### Financial Operations
- **Billing**: Tuition calculation, fee assessment, payment processing
- **Scholarships**: Award management, disbursement, renewal criteria
- **Reporting**: Financial aid reporting, revenue tracking
- **Integration**: QuickBooks synchronization, GL account management

## 📋 Business Rules & Logic

### Enrollment Business Rules
- **Course Load Limits**: Minimum 12 credits, maximum 18 credits per semester
- **Prerequisites**: Automated prerequisite checking and enforcement
- **Capacity Management**: Waitlist system for oversubscribed courses
- **Late Enrollment**: 7-day deadline with penalty fees

### Financial Business Rules
- **Payment Deadlines**: Semester-based payment schedules
- **Late Fees**: 5% penalty for overdue payments
- **Scholarship Limits**: Maximum 100% tuition coverage
- **Currency**: USD as default with multi-currency support

### Attendance Business Rules
- **Grace Period**: 15-minute attendance grace period
- **Absence Limits**: Maximum 25% absence rate per course
- **QR Code Expiry**: 30-minute validity for attendance codes
- **Penalty System**: Automated warnings and academic probation

## 🔄 Business Process Workflows

### Student Enrollment Process
1. **Application Submission** → Level testing (if required)
2. **Academic Assessment** → Program admission decision
3. **Financial Planning** → Scholarship evaluation and award
4. **Course Selection** → Prerequisite validation and enrollment
5. **Payment Processing** → Registration confirmation

### Grade Management Process
1. **Course Delivery** → Attendance tracking and participation
2. **Assessment Entry** → Grade recording and validation
3. **GPA Calculation** → Academic standing evaluation
4. **Transcript Generation** → Official record creation
5. **Graduation Evaluation** → Degree requirement verification

### Financial Management Process
1. **Billing Generation** → Tuition and fee calculation
2. **Payment Processing** → Multiple payment method support
3. **Scholarship Application** → Award evaluation and disbursement
4. **Financial Reporting** → Compliance and audit reporting
5. **GL Integration** → QuickBooks synchronization

## 📈 Business Metrics & KPIs

### Academic Metrics
- **Enrollment rates** by program and semester
- **Course completion rates** and academic success
- **Attendance patterns** and engagement metrics
- **Graduation rates** and time-to-degree

### Financial Metrics
- **Revenue tracking** by program and payment method
- **Scholarship utilization** and effectiveness
- **Payment collection rates** and aging
- **Cost per student** and operational efficiency

### Operational Metrics
- **System usage patterns** by user role
- **Process automation** and efficiency gains
- **User satisfaction** and support metrics
- **Compliance reporting** and audit readiness

## 🎓 Academic Standards

### Grading System
- **4.0 GPA Scale** with letter grade conversion
- **Passing Grade**: D or higher (configurable)
- **GPA Precision**: 2 decimal places
- **Academic Standing**: Good standing, probation, suspension

### Language Requirements
- **English proficiency** for international students
- **Khmer language** support for local students
- **Level testing** for language placement
- **Progression requirements** through language levels

## 📚 Related Documentation
- [Architecture](../architecture/) - System design reflecting business requirements
- [Development](../development/) - Implementation of business logic
- [API](../api/) - Business domain API endpoints and integration