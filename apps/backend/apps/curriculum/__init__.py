"""Curriculum management application.

This application manages the academic curriculum structure, course catalog,
program definitions, and academic calendars for the Naga Student Information System.

Core Components:
- Academic Structure: Hierarchical organization (Division ' Cycle ' Major ' Course)
- Course Catalog: Comprehensive course definitions with metadata
- Academic Calendar: Term and session management
- Course Templates: Standardized course component structure
- Prerequisites: Course dependency tracking and validation
- Senior Projects: Capstone project management and group formation

Architecture:
- Clean hierarchy replacing old SchoolStructuralUnit MPTT system
- Unified course model serving both language and academic sections
- Template-driven course creation ensuring curriculum integrity
- Clean separation from operational concerns (enrollment, grading)
- Comprehensive validation and business rule enforcement

Key Models:
- Division: Top-level organizational units (Language, Academic divisions)
- Cycle: Program cycles within divisions (Foundation, Bachelor's, Master's)
- Major: Unified academic programs and language programs
- Course: All courses with comprehensive metadata and progression tracking
- Term: Academic terms with comprehensive date and cohort tracking
- CoursePartTemplate: Curriculum-defined course structure templates
- CoursePrerequisite: Course dependency relationships
- SeniorProjectGroup: Capstone project management with tiered pricing

Services:
- AcademicStructureService: Division/cycle/major management
- CourseService: Course creation, validation, and progression planning
- CourseTemplateService: Template management and validation
- TransferCreditService: Inter-major credit transfer evaluation
- SeniorProjectService: Project group formation and validation
- TermService: Academic calendar management
"""

default_app_config = "apps.curriculum.apps.CurriculumConfig"
