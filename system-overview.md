# Naga Student Information System - Business Overview

## System Overview

The Naga SIS is a comprehensive Student Information System designed specifically for Pannasastra University of Cambodia (PUCSR), Siem Reap Campus. It manages the complete educational journey from English language learning through advanced degree programs, with specialized features supporting Cambodian educational culture and bilingual operations.

The system handles two primary educational tracks:
- **Language Division**: Non-degree English programs (IEAP, GESL, EHSS) for language learning
- **Academic Division**: Formal degree programs (Bachelor's, Master's, Doctoral) in various fields

## Core Entities

### **Person & Student Management**
- **Person**: Central profile containing both preferred and legal names, with full bilingual support (English/Khmer names)
- **Student Profile**: Comprehensive student data including status tracking (Active, Graduated, Dropped), monk status (important for scholarship eligibility in Cambodia), study time preferences, and transfer student management
- **Teacher Profile**: Faculty qualifications, employment history, and course assignments
- **Staff Profile**: Administrative positions and departmental assignments
- **Emergency Contacts**: Multiple contact persons with relationship tracking and phone number management

### **Academic Structure**
- **Division**: Top-level organization (Language Division, Academic Division)
- **Cycle**: Program levels within divisions (Foundation Year, Bachelor's Program, Master's Program)
- **Major**: Specific degree programs (BA Business Administration, MBA, MEd TESOL) and language programs (IEAP, GESL)
- **Course**: All courses with prerequisite tracking, progression planning, and support for both language and academic instruction
- **Term**: Academic periods with cohort tracking for degree programs and comprehensive deadline management

### **Enrollment & Registration**
- **Program Enrollment**: Student enrollment in academic programs with comprehensive lifecycle tracking (language → academic progression)
- **Class Enrollment**: Student registration in specific class offerings with status management and grade tracking
- **Course Eligibility**: Automated prerequisite checking and retake management with priority scoring
- **Program Transitions**: Tracking student movements between programs (common pathway: IEAP → BA → MBA)

### **Class Scheduling & Operations**
- **Class Header**: Main scheduled class instances (e.g., "GESL-01 Section A, Fall 2025")
- **Class Session**: Session organization within classes (1 session for regular classes, 2 sessions for IEAP programs)
- **Class Part**: Individual class components (Grammar MWF 9-10am, Computer Lab TTh 2-3pm) with teacher and room assignments
- **Reading Classes**: Specialized small-group offerings with tiered pricing based on enrollment (1-2 students, 3-5 students, 6-15 students)

### **Financial Management**
- **Invoice**: Student billing with comprehensive line item tracking and payment status management
- **Payment Processing**: Multiple payment methods with cashier session management and daily reconciliation
- **Pricing System**: Complex pricing structure including course fees, administrative fees, and tiered pricing for specialized offerings
- **Discount Management**: Automated discount rules with time-based and enrollment-based triggers
- **Scholarship Tracking**: Financial aid management with sponsor payment coordination

### **Academic Assessment**
- **Grading Scales**: Multiple grading systems:
  - Language Standard: A-F with F<50% (for EHSS, GESL, Weekend programs)
  - Language IEAP: A-F with F<60% and specialized breakpoints
  - Academic: A+ through F with F<60% for degree programs
- **Grade Management**: Hierarchical grade calculation from class parts → sessions → final grades
- **GPA Calculation**: Program-specific GPA tracking limited to current major requirements

## Main Workflows

### 1. **Student Lifecycle Management**
**Admission → Language Learning → Academic Progression → Graduation**
- Initial placement testing and level assessment for language programs
- Progressive enrollment through language levels (IEAP-01 through IEAP-05)
- Transition from language programs to academic degree programs
- Major declaration and academic planning within degree programs
- Senior project coordination (1-5 students per group with tiered pricing)
- Graduation tracking and transcript preparation

### 2. **Daily Academic Operations**
**Class Scheduling → Enrollment → Instruction → Assessment → Reporting**
- Complex class scheduling supporting multi-part language classes and single-part academic courses
- Student enrollment with prerequisite checking and capacity management
- Attendance tracking with mobile support for teachers
- Multi-level grading for complex language programs (part grades → session grades → final grades)
- Progress monitoring and early intervention for at-risk students

### 3. **Financial Operations**
**Pricing → Billing → Payment → Reconciliation → Reporting**
- Automated invoice generation based on enrollment with complex pricing rules
- Multiple payment processing (cash, credit card, bank transfer) with cashier session management
- Daily reconciliation with variance tracking and management approval workflows
- Integration with QuickBooks for general ledger posting and financial reporting
- Scholarship management with sponsor billing and payment coordination

### 4. **Administrative Functions**
**Planning → Scheduling → Monitoring → Reporting → Compliance**
- Term planning with cohort management for degree programs
- Resource allocation (teachers, rooms) with conflict detection
- Performance monitoring and analytics across all operations
- Comprehensive reporting for academic, financial, and operational metrics
- Audit trail maintenance for compliance and quality assurance

## Key Business Rules

### **Academic Progression Rules**
- Students must complete prerequisite courses before enrolling in advanced courses
- Language programs require level-appropriate placement and sequential completion
- Academic programs require minimum GPA maintenance and credit hour completion
- Senior projects require 1-5 students per group with faculty advisor assignment

### **Financial Business Rules**
- Tiered pricing for specialized courses based on enrollment numbers
- Automatic discount application based on enrollment timing and student status
- Monk students receive special scholarship consideration and pricing adjustments
- Payment deadlines are strictly enforced with automatic late fee assessment

### **Operational Business Rules**
- Class scheduling prevents double-booking of teachers and rooms
- IEAP programs require dual-session structure with weighted grade averaging
- Reading classes automatically convert to standard classes when enrollment exceeds 15 students
- Grade changes require approval workflow and audit trail maintenance

### **Cultural & Regional Considerations**
- Full bilingual support for English and Khmer languages throughout the system
- Monk status tracking affects scholarship eligibility and program participation
- Cambodian currency (KHR) support alongside US Dollar (USD) for payment processing
- Flexible family structure accommodation in emergency contact management

## User Roles & Permissions

### **Student Users**
- View academic records, schedules, and financial accounts
- Submit enrollment applications and course registration requests
- Access grade reports and transcript requests
- Make online payments and view payment history

### **Faculty Users**
- Manage class rosters and attendance tracking
- Enter and modify grades within approval workflows
- Access student academic information relevant to their courses
- Coordinate senior project supervision and grading

### **Academic Staff**
- Process student enrollment and program changes
- Generate academic reports and transcript requests
- Manage prerequisite overrides and special accommodations
- Monitor student progress and academic standing

### **Financial Staff**
- Process payments and manage cashier sessions
- Generate financial reports and reconciliation documents
- Manage scholarship awards and sponsor billing
- Handle billing inquiries and payment plan administration

### **Administrative Management**
- Configure system settings, pricing, and discount rules
- Generate comprehensive operational and compliance reports
- Manage user access and security permissions
- Oversee data integrity and system maintenance

---

*This system overview reflects the business functionality of a sophisticated bilingual Student Information System designed for the unique needs of a Cambodian international university, supporting both language learning and formal degree programs with comprehensive financial management and cultural considerations.*
