# Database Integrity Maintenance Guide

## Overview

This guide provides comprehensive procedures for maintaining database integrity and preventing model/database divergence in the Naga SIS system.

## 🚨 Current Issues Summary

As of the latest scan, the following integrity issues have been identified:

### Critical Issues
- **26 NULL constraint mismatches** - Model and database disagree on nullable fields
- **Missing columns** - Model fields not present in database

### High Priority Issues
- **34 Extra columns** - Database columns not in models (especially finance app)
- **Orphaned ManyToMany tables** - Junction tables left behind from removed relationships

### Medium Priority Issues
- **18 Extra tables** - Mix of legacy tables and orphaned structures

## 🛠️ Restoration Process

### Phase 1: Immediate Fixes (Day 1)

1. **Backup Database**
```bash
./scripts/production/comprehensive-backup.sh local
```

2. **Run Analysis**
```bash
docker compose -f docker-compose.local.yml run --rm django \
  python scripts/maintenance/restore-database-integrity.py --analyze
```

3. **Apply Safe Fixes**
```bash
# Dry run first
docker compose -f docker-compose.local.yml run --rm django \
  python scripts/maintenance/restore-database-integrity.py --fix --dry-run

# Apply if safe
docker compose -f docker-compose.local.yml run --rm django \
  python scripts/maintenance/restore-database-integrity.py --fix
```

### Phase 2: NULL Constraint Alignment (Day 2)

1. **Generate Constraint Fix Migrations**
```bash
# For each app with issues
docker compose -f docker-compose.local.yml run --rm django \
  python manage.py makemigrations finance --name fix_null_constraints

docker compose -f docker-compose.local.yml run --rm django \
  python manage.py makemigrations enrollment --name fix_null_constraints
```

2. **Review Generated Migrations**
- Check `apps/*/migrations/*_fix_null_constraints.py`
- Ensure no data loss operations

3. **Apply Migrations**
```bash
docker compose -f docker-compose.local.yml run --rm django \
  python manage.py migrate
```

### Phase 3: Column Cleanup (Day 3-4)

1. **Finance App Columns**
```python
# Review orphaned CashierSession columns
# Options:
# A) Restore to model if needed
# B) Create data migration to preserve then remove

# If restoring to model:
class CashierSession(models.Model):
    # Add back missing fields
    date = models.DateField(null=True, blank=True)
    opening_time = models.TimeField(null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=20, null=True, blank=True)
    opening_cash = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    closing_cash = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    expected_cash = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    variance = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
```

2. **Generate Column Cleanup Migrations**
```bash
docker compose -f docker-compose.local.yml run --rm django \
  python manage.py makemigrations --name cleanup_orphaned_columns
```

### Phase 4: Table Cleanup (Day 5)

1. **Backup Orphaned Tables**
```sql
-- Via PostgreSQL MCP or psql
-- Backup each orphaned M2M table
CREATE TABLE backup_people_teacherleaverequest_affected_class_parts AS
SELECT * FROM people_teacherleaverequest_affected_class_parts;

-- Repeat for each orphaned table
```

2. **Drop Orphaned Tables** (After verification)
```bash
docker compose -f docker-compose.local.yml run --rm django \
  python scripts/maintenance/restore-database-integrity.py --fix --force
```

### Phase 5: Documentation (Day 6)

1. **Document Legacy Tables**
```markdown
# Create legacy_tables.md
## Preserved Legacy Tables
- legacy_students - Historical student import data
- legacy_academic_classes - Historical class data
- legacy_course_takers - Historical enrollment data
- legacy_receipt_headers - Historical finance data
```

## 📅 Maintenance Schedule

### Daily Checks (CI/CD Pipeline)
```yaml
# .github/workflows/integrity-check.yml
name: Database Integrity Check
on:
  schedule:
    - cron: '0 6 * * *'  # 6 AM UTC daily
  push:
    branches: [main, develop]

jobs:
  integrity-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Integrity Monitor
        run: |
          docker compose -f docker-compose.test.yml run --rm django \
            python scripts/ci-cd/integrity-monitor.py --format github
```

### Weekly Deep Scan
```bash
# Run every Monday
0 2 * * 1 cd /app && python scripts/maintenance/restore-database-integrity.py --analyze > /logs/weekly-integrity.log
```

### Monthly Cleanup
```bash
# First Sunday of month
0 3 1-7 * 0 cd /app && ./scripts/maintenance/monthly-integrity-cleanup.sh
```

## 🔍 Monitoring Integration

### GitHub Actions Setup
```yaml
# .github/workflows/integrity-monitor.yml
- name: Database Integrity Check
  run: |
    python scripts/ci-cd/integrity-monitor.py \
      --format github \
      --fail-on-warning
  env:
    DJANGO_SETTINGS_MODULE: config.settings.test
```

### GitLab CI Setup
```yaml
# .gitlab-ci.yml
integrity-check:
  stage: test
  script:
    - python scripts/ci-cd/integrity-monitor.py --format gitlab
  only:
    - merge_requests
    - main
```

### Slack Alerts
```bash
# Set webhook in environment
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."

# Run with alerts
python scripts/ci-cd/integrity-monitor.py \
  --slack-webhook $SLACK_WEBHOOK_URL
```

## 🚦 Prevention Strategies

### Pre-Migration Hooks

1. **Create Migration Wrapper**
```bash
#!/bin/bash
# scripts/maintenance/safe-migrate.sh

# Snapshot before migration
python scripts/maintenance/restore-database-integrity.py --analyze > pre-migration.json

# Run migrations
python manage.py migrate

# Verify after migration
python scripts/maintenance/restore-database-integrity.py --analyze > post-migration.json

# Compare and alert on new issues
python scripts/ci-cd/compare-integrity-reports.py pre-migration.json post-migration.json
```

### Development Practices

1. **Always use Django migrations** - Never manual SQL DDL
2. **Test migrations on staging** - Before production
3. **Review generated migrations** - Check for data loss
4. **Use atomic migrations** - Rollback capability
5. **Document model changes** - In PR descriptions

### Code Review Checklist

- [ ] No direct database SQL commands
- [ ] Migrations included for model changes
- [ ] Migration is reversible
- [ ] NULL constraints match intended behavior
- [ ] Foreign keys properly defined
- [ ] Indexes for frequently queried fields
- [ ] No circular dependencies

## 🔧 Troubleshooting

### Common Issues

#### 1. Migration Fails Partially
```bash
# Rollback to previous migration
python manage.py migrate app_name previous_migration_number

# Fix issue and retry
python manage.py migrate
```

#### 2. Column Type Mismatch
```python
# Create manual migration
from django.db import migrations

def fix_column_type(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("ALTER TABLE table_name ALTER COLUMN column_name TYPE new_type USING column_name::new_type")

class Migration(migrations.Migration):
    operations = [
        migrations.RunPython(fix_column_type),
    ]
```

#### 3. Orphaned Foreign Keys
```sql
-- Find orphaned records
SELECT t1.* FROM child_table t1
LEFT JOIN parent_table t2 ON t1.parent_id = t2.id
WHERE t1.parent_id IS NOT NULL AND t2.id IS NULL;

-- Clean orphaned records
DELETE FROM child_table
WHERE parent_id NOT IN (SELECT id FROM parent_table);
```

## 📊 Metrics and KPIs

### Integrity Health Score
- **Green (95-100%)**: No critical issues, <5 warnings
- **Yellow (80-94%)**: No critical issues, 5-20 warnings
- **Red (<80%)**: Critical issues present

### Key Metrics to Track
1. **Migration Success Rate**: Target >99%
2. **Schema Sync Score**: Target 100%
3. **Constraint Violations**: Target 0
4. **Orphaned Records**: Target <0.1%
5. **Response Time Impact**: Target <5ms

## 🎯 Long-term Goals

1. **Q1 2025**: Achieve 100% schema synchronization
2. **Q2 2025**: Implement automated rollback on integrity failure
3. **Q3 2025**: Add predictive integrity analysis
4. **Q4 2025**: Full integration with monitoring stack

## 📝 Change Log

| Date | Action | Result |
|------|--------|--------|
| 2025-01-08 | Initial integrity scan | 60 issues found |
| 2025-01-08 | Created restoration tools | Scripts deployed |
| TBD | Apply fixes | Pending |

## 🆘 Emergency Contacts

- **Database Admin**: Contact via Slack #database-emergency
- **DevOps Lead**: Contact via PagerDuty
- **Backup Location**: `/backups/postgres/` and S3

---

**Last Updated**: January 8, 2025
**Next Review**: February 1, 2025
**Document Owner**: Backend Team
