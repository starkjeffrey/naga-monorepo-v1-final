#!/bin/bash
#
# MIGRATION ENVIRONMENT - Verification Script
# This script verifies the current state of the migration environment
#

set -e

echo "🔍 MIGRATION Environment Verification"
echo "====================================="

# Check test environment status (used for migration)
echo "📦 Checking environment status..."
if ! docker compose -f docker-compose.test.yml ps postgres | grep -q "healthy"; then
    echo "❌ TEST environment (used for migration) is not running"
    echo "Run: ./scripts/test_environment/start_test_env.sh"
    exit 1
fi

echo "✅ TEST environment is running (used for migration work)"

# Check database connectivity
echo "🗄️ Checking database connectivity..."
docker compose -f docker-compose.test.yml run --rm django python manage.py check --database=default >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Database connection successful"
else
    echo "❌ Database connection failed"
    exit 1
fi

# Check legacy data
echo "📊 Checking legacy data..."
LEGACY_SUMMARY=$(docker compose -f docker-compose.test.yml run --rm django python manage.py shell -c "
from django.db import connection
cursor = connection.cursor()

# Get all legacy tables
cursor.execute(\"\"\"
    SELECT table_name,
           (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name),
           (SELECT pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
            FROM pg_tables WHERE tablename = t.table_name)
    FROM information_schema.tables t
    WHERE table_schema = 'public'
    AND table_name LIKE 'legacy_%'
    ORDER BY table_name;
\"\"\")

legacy_tables = cursor.fetchall()
print(f'LEGACY_TABLES:{len(legacy_tables)}')

total_rows = 0
for table_name, column_count, size in legacy_tables:
    cursor.execute(f'SELECT COUNT(*) FROM {table_name};')
    row_count = cursor.fetchone()[0]
    total_rows += row_count
    print(f'{table_name}:{row_count}:{column_count}:{size}')

print(f'TOTAL_ROWS:{total_rows}')
" 2>/dev/null | grep -E '^(LEGACY_TABLES|legacy_|TOTAL_ROWS):')

# Parse the output
LEGACY_COUNT=$(echo "$LEGACY_SUMMARY" | grep "LEGACY_TABLES:" | cut -d: -f2)
TOTAL_ROWS=$(echo "$LEGACY_SUMMARY" | grep "TOTAL_ROWS:" | cut -d: -f2)

if [ "$LEGACY_COUNT" -gt 0 ]; then
    echo "✅ Legacy data found: $LEGACY_COUNT tables with $TOTAL_ROWS total records"
    echo ""
    echo "📋 Legacy Tables:"
    echo "$LEGACY_SUMMARY" | grep "^legacy_" | while IFS=: read -r table rows cols size; do
        printf "  %-30s %10s rows  %2s cols  %8s\n" "$table" "$rows" "$cols" "$size"
    done
else
    echo "⚠️ No legacy data found"
    echo "Run: ./scripts/migration_environment/import_legacy_data.sh"
fi

echo ""
echo "🌐 Services Available:"
echo "  - Django: http://localhost:8000"
echo "  - Mailpit: http://localhost:8025"
echo ""
echo "🗄️ Database: naga_test_v1 (TEST environment used for MIGRATION)"
echo "🔧 Settings: config.settings.test_env"

# Check available migration commands
echo ""
echo "🛠️ Available Migration Commands:"
docker compose -f docker-compose.test.yml run --rm django python manage.py help | grep -E "migrate_legacy|import_legacy|setup_" | sed 's/^/  - /'

echo ""
if [ "$LEGACY_COUNT" -gt 0 ]; then
    echo "✅ Migration environment is ready for data processing"
else
    echo "⚠️ Import legacy data first before proceeding"
fi
