# 🗂️ Naga SIS V1 - Scripts Organization

**Organized by Criticality and Retention Policy** - July 2025 Restructure

## 📋 Directory Structure

```
scripts/
├── production/           # 🔴 CRITICAL - Production operations (PRESERVE)
├── development/          # 🟡 USEFUL - Development tools (6-12 months retention)
├── maintenance/          # 🟠 IMPORTANT - Database maintenance (PRESERVE)
├── utilities/           # 🟢 HELPFUL - General purpose tools (12 months retention)
├── legacy_imports/      # 📦 ARCHIVE - Legacy data import scripts
├── migration_environment/ # 🔄 PRESERVE - Migration tools and verification
├── translation-tools/   # 🌐 PRESERVE - Translation workflow
├── test_setup/         # 🧪 USEFUL - Test environment setup
├── management_reports/  # 📊 TEMPORARY - Reporting scripts (6 months)
└── one-off/            # ⚡ EPHEMERAL - One-time scripts (3 months)
```

---

## 🔴 Production Scripts (`production/`)

**⚠️ CRITICAL - ZERO TOLERANCE FOR LOSS**

**Retention**: **PERMANENT** - Must be preserved at all costs
**Backup**: Included in comprehensive backup system

### Scripts:
- `production-backup-system.sh` - Enterprise backup orchestration
- `comprehensive-backup.sh` - Database + fixtures + verification
- `backup-database.sh` - PostgreSQL backup utility
- `restore-database.sh` - Database restoration utility
- `automated-backup-pipeline.sh` - Automated backup scheduling
- `backup-google-drive.sh` - Google Drive backup integration
- `backup_verification.sh` - Backup integrity verification
- `verify-backup-integrity.sh` - Standard integrity checks
- `verify-backup-integrity-enterprise.sh` - Enterprise-grade verification
- `merge_production_dotenvs_in_dotenv.py` - Production configuration

### Recovery Impact: 
**CRITICAL** - Loss would require complete rebuild of backup/restore infrastructure

---

## 🟡 Development Scripts (`development/`)

**Retention**: **6-12 months** - Useful during active development
**Recovery Impact**: Moderate - Development workflow disruption

### Scripts:
- `verify-migration-completion.sh` - Migration workflow status checker
- `gemini_code_review.py` - AI-assisted code review
- `detailed_debug.py` - Comprehensive debugging tool
- `debug_promotion.py` - Promotion process debugging
- `*lint_fixes*.py` - Code quality automation
- `simple_gemini_review.sh` - Quick AI review tool
- `test_*.py` - Development testing scripts
- `setup_gemini_auth.sh` - AI tool authentication

---

## 🟠 Maintenance Scripts (`maintenance/`)

**⚠️ IMPORTANT - Database Operations**

**Retention**: **PERMANENT** - Database operations are critical
**Recovery Impact**: High - Database maintenance and environment management

### Scripts:
- `migrate-both.sh` - Dual-environment migration
- `migration-env.sh` - Migration environment management
- `check-environment-status.sh` - Environment health monitoring
- `compare-environment-data.sh` - Environment synchronization
- `check_test_data.sh` - Test data validation
- `fix_duplicate_classheaders.py` - Data integrity fixes

---

## 🟢 Utilities Scripts (`utilities/`)

**Retention**: **12 months** - General purpose tools
**Recovery Impact**: Low-Medium - Convenience tools

### Scripts:
- `extract_app_code.py` - Code extraction utility
- `extract_student_records.py` - Data extraction tool
- `setup-context7-memory.sh` - MCP server setup
- `project-memory-fallback.sh` - Memory system backup
- `normalize_legacy_classes.py` - Data normalization

---

## 📦 Legacy Systems (`legacy_imports/`, `migration_environment/`)

**Retention**: **PERMANENT** - Historical data migration
**Recovery Impact**: High for future migrations

### Purpose:
- Historical data import from Version 0 system
- Migration verification and validation
- Legacy system integration tools

### Key Scripts:
- `migration_environment/production-ready/` - Production migration tools
- `legacy_imports/import_*.py` - Data import scripts
- Various date-stamped migration scripts (250626, 250708, etc.)

---

## 🌐 Translation Tools (`translation-tools/`)

**Retention**: **PERMANENT** - Bilingual system requirement
**Recovery Impact**: High - Critical for English/Khmer support

### Contents:
- Translation workflow automation
- PO file processing
- Continuous translation monitoring
- Requirements: Google Translate API integration

---

## ⚡ Temporary Categories

### `one-off/` - Ephemeral Scripts
**Retention**: **3 months**
**Impact**: Minimal - One-time use scripts

### `management_reports/` - Reporting Scripts  
**Retention**: **6 months**
**Impact**: Low - Analysis and reporting tools

---

## 🔄 Retention and Cleanup Policies

### Automatic Cleanup Schedule:
- **Monthly**: Review `one-off/` directory (3-month retention)
- **Quarterly**: Review `management_reports/` (6-month retention)  
- **Bi-annually**: Review `development/` (12-month retention)
- **Never**: Clean `production/`, `maintenance/`, `legacy_imports/`, `migration_environment/`, `translation-tools/`

### Manual Review Triggers:
- Before major version releases
- Storage space constraints
- Security audit requirements
- Backup system optimization

---

## 📊 Git Repository Impact

### Excluded from Git (`.gitignore`):
- `data/legacy/**` (270MB - regeneratable from SQL)
- `translation-tools/.venv/**` (14MB - virtual environment)
- Backup files (`*.sql.gz`, `backups/**`)

### Included in Git:
- All script directories and contents
- Documentation and README files
- Configuration and requirements files

### Repository Health:
- **Before Restructure**: 274MB (Git size limit violation)
- **After Cleanup**: ~76KB `data/migrate` (Git-compatible)
- **Script Organization**: Improved disaster recovery capability

---

## 🚨 Emergency Recovery Procedures

### Priority Recovery Order:
1. **CRITICAL**: `production/` scripts - Backup/restore capabilities
2. **HIGH**: `maintenance/` scripts - Database operations
3. **MEDIUM**: `migration_environment/` - Historical data access
4. **LOW**: Other directories based on immediate needs

### Recovery Sources:
- Git repository (primary)
- Comprehensive backup system
- External backup locations (Google Drive, etc.)
- Documentation and manual recreation

---

## 📝 Usage Examples

```bash
# Production backup
./scripts/production/comprehensive-backup.sh local

# Development workflow check
./scripts/development/verify-migration-completion.sh

# Database maintenance
./scripts/maintenance/migrate-both.sh

# Utility operations
./scripts/utilities/extract_student_records.py

# Legacy data import
./scripts/migration_environment/import_legacy_data.sh
```

---

## 📋 Change Log

### July 27, 2025 - Major Restructure
- **Organized by criticality and retention policy**
- **Implemented Git size optimization** (274MB → ~76KB)
- **Created retention and cleanup policies**
- **Established recovery priority framework**
- **Improved disaster recovery capabilities**

### Previous Structure Issues Resolved:
- ❌ Mixed criticality levels in root directory
- ❌ No retention policies or cleanup procedures  
- ❌ Git size limit violations (274MB data/)
- ❌ Unclear recovery priorities
- ✅ **All issues systematically addressed**

---

**🎯 Result**: Organized, maintainable script structure with clear retention policies and optimal backup/recovery strategy.