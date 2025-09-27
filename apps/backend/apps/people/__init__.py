"""People management application.

This application manages person profiles for all individuals in the Naga SIS -
students, teachers, staff, and their relationships. This domain layer app serves
as the foundation for all person-related functionality across the system.

Core Components:
- Comprehensive Person Management: Unified person model with role-specific profiles
- Multi-Language Support: Bilingual name handling (English/Khmer) with cultural sensitivity
- Student Lifecycle: Complete student journey from application to graduation
- Faculty & Staff: Professional profiles with qualifications and credentials
- Contact Management: Emergency contacts with relationship tracking and validation
- ID Generation: Institutional student ID format with sequence management

Architecture:
- Domain layer focus providing core person management without business logic
- Profile pattern with role-specific profiles extending base person entity
- Flexible relationship support for complex family and professional structures
- Cultural sensitivity with comprehensive multi-language name support
- Clean separation from operational concerns while enabling system integration

Key Models:
- Person: Central person entity with comprehensive demographic information
- StudentProfile: Student-specific academic tracking and status management
- TeacherProfile: Faculty qualifications, specializations, and credentials
- StaffProfile: Administrative responsibilities and professional information
- EmergencyContact: Contact relationships with authorization and medical permissions
- PhoneNumber: Multiple validated phone numbers per person with normalization
- PersonEventLog: Comprehensive audit trail for all person-related changes

Services:
- StudentNumberService: Atomic student ID generation using PostgreSQL sequences
- PersonService: Person creation, validation, and comprehensive search functionality
- DuplicateDetectionService: Advanced duplicate person identification and merging
- NameParsingService: Cultural name parsing with Western and Khmer support

Validation & Security:
- Comprehensive validation for names, contact information, and demographic data
- PII encryption for sensitive personal information with access controls
- GDPR compliance with data retention policies and audit requirements
- Phone number normalization with international format support

Integration:
- Enrollment: Student profile integration with academic program management
- Academic: Student academic progress and requirement fulfillment tracking
- Authentication: User account linkage for students, teachers, and staff
- Level Testing: Conversion of test applicants to enrolled students
"""

default_app_config = "apps.people.apps.PeopleConfig"
