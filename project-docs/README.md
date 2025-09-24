# Naga SIS - Project Documentation

## 📖 Documentation Overview

This directory contains comprehensive project documentation for the Naga Student Information System monorepo. Documentation is organized by category for easy navigation and maintenance.

## 📁 Documentation Structure

### 🏗️ Architecture & Design
- **[Architecture Analysis](architecture/)**: System architecture decisions and analysis
  - `dependency_analysis_20250612.md` - Critical circular dependency analysis from v0
  - `model-diagrams/` - Comprehensive model relationship diagrams
  - `dynamic_sidebar_system.md` - Frontend navigation architecture
  - `moodle_integration_architecture.md` - External system integration

### 💻 Development Guides
- **[Development](development/)**: Development workflows and standards
  - `dual_database_development_guide.md` - Multi-environment development
  - `environment_usage.md` - Environment-specific development guidelines
  - `context7-setup-instructions.md` - MCP Context7 setup for Claude
  - `gl-integration-guide.md` - General Ledger integration patterns

### ⚙️ Operations & Maintenance
- **[Operations](operations/)**: System operations and maintenance
  - `database_maintenance_strategy.md` - Database maintenance procedures
  - `backup_verification_instructions.md` - Backup verification protocols
  - `dramatiq_migration_summary.md` - Task queue migration notes

### 🔄 Data Migration
- **[Migration](migration/)**: Legacy data migration documentation
  - `migration-reports/` - Detailed migration audit reports (JSON format)
  - `migration_environment_guide.md` - Migration environment setup
  - `student_migration_notes_250626.md` - Student data migration specifics
  - `v0_to_v1_field_mapping.md` - Field mapping from legacy system
  - `naga_import_procedures.md` - Import procedure documentation

### 🌐 API Documentation
- **[API](api/)**: API specifications and guides
  - `api_documentation.json` - OpenAPI specifications
  - `attendance_api_endpoints.md` - Attendance system API
  - `attendance_api_schemas.md` - Attendance data schemas
  - `mobile_api_guide.md` - Mobile app API integration
  - `necessary_mods_to_apis_250617.md` - API modification requirements

### 📊 Business Analysis
- **[Business Analysis](business-analysis/)**: Business requirements and analysis
  - `business-questions-level-testing-250629.md` - Level testing business requirements
  - `school_structure_250621.md` - Academic institution structure analysis
  - `program_enrollment_service_logic.md` - Program enrollment business logic
  - `absence_penalty_reset_system.md` - Attendance penalty system design

### 🔍 Code Reviews
- **[Code Reviews](code-reviews/)**: Comprehensive app-by-app code reviews
  - `apps-academic.md` - Academic domain code review
  - `apps-enrollment.md` - Enrollment system code review
  - `apps-finance.md` - Financial system code review
  - `apps-grading.md` - Grading system code review
  - `apps-people.md` - People management code review
  - `apps-scholarships.md` - Scholarship system code review
  - And more comprehensive reviews for each Django app

### 📝 Session Logs
- **[Session Logs](session-logs/)**: Development session documentation
  - `session-250626-student-migration.md` - Student migration session
  - `session-250627-sponsorship-verification.md` - Sponsorship verification session

## 🎯 Quick Navigation

### For New Developers
1. **Start with**: [Architecture Analysis](architecture/dependency_analysis_20250612.md)
2. **Then read**: [Development Environment Setup](development/dual_database_development_guide.md)
3. **Review**: [Code Review Summaries](code-reviews/)

### For System Administrators
1. **Operations**: [Database Maintenance](operations/database_maintenance_strategy.md)
2. **Backups**: [Backup Verification](operations/backup_verification_instructions.md)
3. **Migration**: [Migration Environment](migration/migration_environment_guide.md)

### For API Developers
1. **API Specs**: [API Documentation](api/api_documentation.json)
2. **Mobile APIs**: [Mobile Integration Guide](api/mobile_api_guide.md)
3. **System APIs**: [Attendance System](api/attendance_api_endpoints.md)

### For Business Stakeholders
1. **Requirements**: [Business Analysis](business-analysis/)
2. **System Structure**: [School Structure](business-analysis/school_structure_250621.md)
3. **Process Logic**: [Program Enrollment](business-analysis/program_enrollment_service_logic.md)

## 📋 Documentation Standards

### File Naming Convention
- Use descriptive, lowercase filenames with hyphens
- Include dates for time-sensitive documents (YYMMDD format)
- Use appropriate file extensions (.md for markdown, .json for data)

### Content Standards
- **Headers**: Use clear, hierarchical heading structure
- **Code blocks**: Include language specification for syntax highlighting
- **Links**: Use relative links for internal documentation
- **Images**: Store in appropriate subdirectories with descriptive names

### Review Process
- **Technical Documentation**: Review by technical lead before merging
- **Business Documentation**: Review by business stakeholders
- **Migration Documentation**: Review by data team and technical lead
- **API Documentation**: Auto-generated where possible, manual review for changes

## 🔍 Search and Discovery

### Finding Documentation
- Use descriptive filenames and clear headers for searchability
- Cross-reference related documents with links
- Maintain this README with current content overview
- Use consistent terminology across documents

### Maintenance Schedule
- **Monthly**: Review and update quick navigation links
- **Quarterly**: Archive outdated session logs and reports
- **Per Release**: Update API documentation and architecture diagrams
- **Annual**: Comprehensive documentation audit and reorganization

## 📚 Related Documentation

### External Documentation
- **[OPERATIONS.md](../OPERATIONS.md)**: Comprehensive systems operations manual
- **[README.md](../README.md)**: Project overview and quick start guide
- **[CLAUDE.md](../backend/CLAUDE.md)**: Development context for AI assistants
- **[Sphinx Docs](../backend/docs/)**: Technical API documentation

### Live Documentation
- **API Docs**: http://localhost:8000/api/docs (django-ninja auto-generated)
- **Admin Interface**: http://localhost:8000/admin/ (Django admin)
- **Monitoring**: http://localhost:3000 (Grafana dashboards)

## 🤝 Contributing to Documentation

### Adding New Documentation
1. **Determine category** from the structure above
2. **Create descriptive filename** following naming conventions
3. **Add entry** to this README in appropriate section
4. **Cross-reference** related documents with links
5. **Submit for review** according to content type

### Updating Existing Documentation
1. **Maintain backwards compatibility** for referenced procedures
2. **Update cross-references** when moving or renaming files
3. **Archive outdated versions** with clear naming
4. **Update this README** if structure changes

---

**Documentation Version**: 1.0  
**Last Updated**: 2025-01-01  
**Maintainer**: Naga SIS Development Team  
**Review Schedule**: Monthly structural review, quarterly content audit