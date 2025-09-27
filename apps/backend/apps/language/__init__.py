"""Language program management application.

This application manages language-specific course progression, automated student
promotion between levels, and specialized language program administration for
the Naga Student Information System.

Core Components:
- Language Level Management: Standardized progression with flexible advancement
- Automated Student Promotion: Batch processing with eligibility analysis
- Level Skip Requests: Management-approved level advancement workflows
- Term Preparation: Automated class creation and student enrollment
- Promotion Audit: Comprehensive tracking of all advancement decisions

Architecture:
- Level-based progression with clear advancement criteria and validation
- Template-driven class creation ensuring curriculum integrity
- Audit-focused design with complete tracking of promotions and level changes
- Automation-friendly batch processing with comprehensive error handling
- Clean separation from operational concerns while maintaining integration

Key Models:
- LanguageProgramPromotion: Batch promotion events with comprehensive tracking
- LanguageStudentPromotion: Individual student advancement records
- LanguageLevelSkipRequest: Management-approved level skip workflows

Services:
- LanguagePromotionService: Automated promotion analysis and execution
- LanguageLevelSkipService: Level skip request processing and implementation

Business Rules:
- Eligibility validation based on grades, attendance, and completion
- Program-specific promotion policies and timeline requirements
- Template-based class creation (no legacy cloning allowed)
- Comprehensive audit trail for all advancement decisions
- Maximum level skip limits with management override capability

Integration:
- Level Testing: Placement test result processing for initial level assignment
- Enrollment: Automatic enrollment in promoted classes with validation
- Academic: Language requirement fulfillment for degree progress tracking
"""

default_app_config = "apps.language.apps.LanguageConfig"
