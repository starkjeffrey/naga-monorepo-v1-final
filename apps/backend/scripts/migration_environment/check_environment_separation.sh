#!/bin/bash
#
# MIGRATION ENVIRONMENT - Environment Separation Verification
# This script verifies that TEST and MIGRATION environments are properly separated
#

echo "🔍 Environment Separation Verification"
echo "======================================"

echo ""
echo "📊 TEST Environment (docker-compose.test.yml):"
echo "  Port: 8000"
echo "  Database: naga_test_v1"
echo "  Purpose: Clean development and testing"

if docker compose -f docker-compose.test.yml ps postgres | grep -q "healthy"; then
    echo "  Status: ✅ Running"

    LEGACY_COUNT=$(docker compose -f docker-compose.test.yml run --rm django python manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
cursor.execute(\"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE 'legacy_%';\")
print(cursor.fetchone()[0])
" 2>/dev/null | tail -1)

    if [ "$LEGACY_COUNT" = "0" ]; then
        echo "  Legacy Data: ✅ Clean (no legacy tables)"
    else
        echo "  Legacy Data: ❌ Contains $LEGACY_COUNT legacy tables (should be 0)"
    fi
else
    echo "  Status: ⏸️ Not running"
fi

echo ""
echo "📊 MIGRATION Environment (docker-compose.migration.yml):"
echo "  Port: 8001"
echo "  Database: naga_migration_v1"
echo "  Purpose: Legacy data import and processing"

if docker compose -f docker-compose.migration.yml ps postgres | grep -q "healthy"; then
    echo "  Status: ✅ Running"

    MIGRATION_SUMMARY=$(docker compose -f docker-compose.migration.yml run --rm django python manage.py shell -c "
from django.db import connection
cursor = connection.cursor()

# Get legacy table count and total rows
cursor.execute(\"\"\"
    SELECT COUNT(*)
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name LIKE 'legacy_%';
\"\"\")
table_count = cursor.fetchone()[0]

total_rows = 0
if table_count > 0:
    cursor.execute(\"\"\"
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name LIKE 'legacy_%';
    \"\"\")
    for (table_name,) in cursor.fetchall():
        cursor.execute(f'SELECT COUNT(*) FROM {table_name};')
        total_rows += cursor.fetchone()[0]

print(f'{table_count}:{total_rows}')
" 2>/dev/null | tail -1)

    MIGRATION_TABLES=$(echo "$MIGRATION_SUMMARY" | cut -d: -f1)
    MIGRATION_ROWS=$(echo "$MIGRATION_SUMMARY" | cut -d: -f2)

    if [ "$MIGRATION_TABLES" -gt 0 ]; then
        echo "  Legacy Data: ✅ Contains $MIGRATION_TABLES legacy tables with $MIGRATION_ROWS total records"
    else
        echo "  Legacy Data: ⚠️ No legacy data found"
    fi
else
    echo "  Status: ⏸️ Not running"
fi

echo ""
echo "🎯 Environment Summary:"
if [ "$LEGACY_COUNT" = "0" ] && [ "$MIGRATION_TABLES" -gt 0 ]; then
    echo "✅ Perfect separation:"
    echo "  - TEST environment is clean for development"
    echo "  - MIGRATION environment contains legacy data for processing"
    echo "  - No data contamination between environments"
else
    echo "⚠️ Issues detected:"
    if [ "$LEGACY_COUNT" != "0" ]; then
        echo "  - TEST environment contains legacy data (should be clean)"
    fi
    if [ "$MIGRATION_TABLES" = "0" ]; then
        echo "  - MIGRATION environment missing legacy data"
    fi
fi

echo ""
echo "🔧 Quick Commands:"
echo "  Start TEST:      docker compose -f docker-compose.test.yml up -d"
echo "  Start MIGRATION: docker compose -f docker-compose.migration.yml up -d"
echo "  Import Legacy:   ./scripts/migration_environment/import_legacy_data.sh"
