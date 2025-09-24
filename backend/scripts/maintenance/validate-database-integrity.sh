#!/bin/bash

# validate-database-integrity.sh - Comprehensive database/model validation
# This script systematically checks for database/model mismatches and fixes them

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="$PROJECT_ROOT/project-docs/database-integrity-report-$TIMESTAMP.md"

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}       Database Integrity Validation - Naga SIS${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Initialize report
cat > "$REPORT_FILE" << EOF
# Database Integrity Report
Generated: $(date)

## Summary
This report validates database schema against Django models.

EOF

# Function to log to both console and report
log_both() {
    echo -e "$1"
    echo "$2" >> "$REPORT_FILE"
}

# Track issues
ISSUES_FOUND=0
CRITICAL_ISSUES=()

echo -e "${CYAN}Step 1: Checking for unapplied migrations...${NC}"
echo "## Migration Status" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Check for unapplied migrations
UNAPPLIED=$(docker compose -f docker-compose.local.yml run --rm django python manage.py showmigrations --plan | grep "\[ \]" || true)
if [ -n "$UNAPPLIED" ]; then
    log_both "${RED}❌ Found unapplied migrations:${NC}" "### ❌ Unapplied Migrations Found"
    echo "\`\`\`" >> "$REPORT_FILE"
    echo "$UNAPPLIED" | tee -a "$REPORT_FILE"
    echo "\`\`\`" >> "$REPORT_FILE"
    CRITICAL_ISSUES+=("Unapplied migrations")
    ((ISSUES_FOUND++))
else
    log_both "${GREEN}✓ All migrations applied${NC}" "### ✓ All migrations applied"
fi

echo ""
echo -e "${CYAN}Step 2: Checking for model changes without migrations...${NC}"
echo "" >> "$REPORT_FILE"
echo "## Model Changes" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Check for unmigrated model changes
CHANGES=$(docker compose -f docker-compose.local.yml run --rm django python manage.py makemigrations --dry-run 2>&1 | grep -v "No changes detected" || true)
if [ -n "$CHANGES" ] && [[ ! "$CHANGES" =~ "No changes detected" ]]; then
    log_both "${RED}❌ Found model changes without migrations:${NC}" "### ❌ Model Changes Without Migrations"
    echo "\`\`\`" >> "$REPORT_FILE"
    echo "$CHANGES" | tee -a "$REPORT_FILE"
    echo "\`\`\`" >> "$REPORT_FILE"
    CRITICAL_ISSUES+=("Model changes without migrations")
    ((ISSUES_FOUND++))
else
    log_both "${GREEN}✓ No unmigrated model changes${NC}" "### ✓ No unmigrated model changes"
fi

echo ""
echo -e "${CYAN}Step 3: Validating database schema against models...${NC}"
echo "" >> "$REPORT_FILE"
echo "## Schema Validation" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Create Python script for detailed validation
cat > "$PROJECT_ROOT/scratchpad/validate_db_schema.py" << 'PYTHON_SCRIPT'
"""Validate database schema against Django models."""
import os
import sys
import django
from django.apps import apps
from django.db import connection

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

def get_db_columns(table_name):
    """Get actual database columns."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = %s
            ORDER BY ordinal_position
        """, [table_name])
        return {row[0]: {'type': row[1], 'nullable': row[2]} for row in cursor.fetchall()}

def validate_models():
    """Validate all models against database."""
    issues = []
    warnings = []

    for model in apps.get_models():
        if model._meta.abstract or model._meta.proxy:
            continue

        table_name = model._meta.db_table
        model_fields = {}

        # Get model fields
        for field in model._meta.get_fields():
            if hasattr(field, 'column'):
                model_fields[field.column] = {
                    'field_name': field.name,
                    'field_type': field.__class__.__name__,
                    'nullable': field.null
                }

        # Get database columns
        try:
            db_columns = get_db_columns(table_name)
        except Exception as e:
            issues.append(f"ERROR: Table '{table_name}' for model {model.__name__} - {str(e)}")
            continue

        # Check for missing columns in database
        for column_name, field_info in model_fields.items():
            if column_name not in db_columns:
                issues.append(f"MISSING COLUMN: {table_name}.{column_name} (field: {field_info['field_name']})")

        # Check for extra columns in database
        for column_name in db_columns:
            if column_name not in model_fields and column_name not in ['id', 'created_at', 'updated_at']:
                warnings.append(f"EXTRA COLUMN: {table_name}.{column_name} not in model")

    return issues, warnings

# Run validation
print("Validating database schema...")
issues, warnings = validate_models()

if issues:
    print("\n🔴 CRITICAL ISSUES FOUND:")
    for issue in issues:
        print(f"  - {issue}")

if warnings:
    print("\n⚠️  WARNINGS:")
    for warning in warnings[:10]:  # Limit to first 10
        print(f"  - {warning}")
    if len(warnings) > 10:
        print(f"  ... and {len(warnings) - 10} more warnings")

# Return exit code
sys.exit(1 if issues else 0)
PYTHON_SCRIPT

# Run the validation
echo "### Detailed Schema Validation" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "\`\`\`" >> "$REPORT_FILE"
if docker compose -f docker-compose.local.yml run --rm django python scratchpad/validate_db_schema.py 2>&1 | tee -a "$REPORT_FILE"; then
    log_both "${GREEN}✓ Schema validation passed${NC}" ""
else
    log_both "${RED}❌ Schema validation failed${NC}" ""
    CRITICAL_ISSUES+=("Schema mismatches")
    ((ISSUES_FOUND++))
fi
echo "\`\`\`" >> "$REPORT_FILE"

echo ""
echo -e "${CYAN}Step 4: Checking database constraints...${NC}"
echo "" >> "$REPORT_FILE"
echo "## Constraint Validation" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Check foreign key constraints
docker compose -f docker-compose.local.yml exec postgres psql -U debug -d naga_local -c "
SELECT
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM
    information_schema.table_constraints AS tc
    JOIN information_schema.key_column_usage AS kcu
      ON tc.constraint_name = kcu.constraint_name
    JOIN information_schema.constraint_column_usage AS ccu
      ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
ORDER BY tc.table_name
LIMIT 5;" >> "$REPORT_FILE" 2>&1

echo ""
echo -e "${CYAN}Step 5: Generating fixes...${NC}"
echo "" >> "$REPORT_FILE"
echo "## Recommended Fixes" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

if [ $ISSUES_FOUND -gt 0 ]; then
    echo "### Automatic Fix Commands" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"

    echo "1. **Generate missing migrations:**" >> "$REPORT_FILE"
    echo "\`\`\`bash" >> "$REPORT_FILE"
    echo "docker compose -f docker-compose.local.yml run --rm django python manage.py makemigrations" >> "$REPORT_FILE"
    echo "\`\`\`" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"

    echo "2. **Apply migrations:**" >> "$REPORT_FILE"
    echo "\`\`\`bash" >> "$REPORT_FILE"
    echo "docker compose -f docker-compose.local.yml run --rm django python manage.py migrate" >> "$REPORT_FILE"
    echo "\`\`\`" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"

    echo "3. **Force schema rebuild (DANGEROUS - backup first!):**" >> "$REPORT_FILE"
    echo "\`\`\`bash" >> "$REPORT_FILE"
    echo "# Backup database first!" >> "$REPORT_FILE"
    echo "./scripts/production/backup-database.sh" >> "$REPORT_FILE"
    echo "# Then recreate schema" >> "$REPORT_FILE"
    echo "docker compose -f docker-compose.local.yml run --rm django python manage.py migrate --fake-initial" >> "$REPORT_FILE"
    echo "\`\`\`" >> "$REPORT_FILE"
fi

# Create fix script for specific issues
if [[ " ${CRITICAL_ISSUES[@]} " =~ "Schema mismatches" ]]; then
    cat > "$PROJECT_ROOT/scratchpad/fix_cashier_session.py" << 'FIX_SCRIPT'
"""Fix missing session_number column in CashierSession."""
from django.db import connection

def add_missing_column():
    with connection.cursor() as cursor:
        # Check if column exists
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'finance_cashier_session'
            AND column_name = 'session_number'
        """)

        if not cursor.fetchone():
            print("Adding missing session_number column...")
            cursor.execute("""
                ALTER TABLE finance_cashier_session
                ADD COLUMN session_number VARCHAR(50) DEFAULT 'DEFAULT-001'
            """)
            cursor.execute("""
                ALTER TABLE finance_cashier_session
                ADD CONSTRAINT finance_cashier_session_session_number_unique
                UNIQUE (session_number)
            """)
            print("✓ Column added successfully")
        else:
            print("Column already exists")

if __name__ == "__main__":
    add_missing_column()
FIX_SCRIPT

    echo "" >> "$REPORT_FILE"
    echo "### Specific Fix for CashierSession" >> "$REPORT_FILE"
    echo "\`\`\`bash" >> "$REPORT_FILE"
    echo "docker compose -f docker-compose.local.yml run --rm django python scratchpad/fix_cashier_session.py" >> "$REPORT_FILE"
    echo "\`\`\`" >> "$REPORT_FILE"
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                        Summary${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

if [ $ISSUES_FOUND -eq 0 ]; then
    echo -e "${GREEN}✅ Database integrity check passed!${NC}"
else
    echo -e "${RED}❌ Found $ISSUES_FOUND issue(s):${NC}"
    for issue in "${CRITICAL_ISSUES[@]}"; do
        echo -e "   ${RED}• $issue${NC}"
    done
    echo ""
    echo -e "${YELLOW}📋 Full report saved to: $REPORT_FILE${NC}"
    echo -e "${YELLOW}🔧 Fix commands available in report${NC}"
fi

echo ""
echo "## Summary" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "Total issues found: $ISSUES_FOUND" >> "$REPORT_FILE"

exit $ISSUES_FOUND
