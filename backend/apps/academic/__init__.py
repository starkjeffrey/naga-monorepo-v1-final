"""Academic requirements management application.

This application handles degree requirements, course equivalencies, transfer credits,
and graduation tracking for the Naga Student Information System.

Core Components:
- Canonical Requirements: Rigid degree requirements (exactly 43 courses for BA)
- Requirement Fulfillment: Tracking how students satisfy requirements
- Transfer Credits: External course credit recognition
- Student Exceptions: Approved deviations from standard requirements
- Degree Progress: Overall graduation tracking and audit functionality

Architecture:
- Uses "Canonical as default, exception as override" pattern
- Course.credits is the single source of truth for credit values
- Clean separation from operational concerns (enrollment, scheduling)
- Comprehensive audit trail for all academic decisions

Key Models:
- CanonicalRequirement: Template requirements for each major
- StudentDegreeProgress: Individual requirement completion tracking (renamed for human-friendliness)
- TransferCredit: External course credit management
- StudentRequirementException: Approved academic exceptions

Services:
- CanonicalRequirementService: Core academic requirement management
- Degree progress calculation and audit generation
- Exception processing and approval workflows
"""

default_app_config = "apps.academic.apps.AcademicConfig"
