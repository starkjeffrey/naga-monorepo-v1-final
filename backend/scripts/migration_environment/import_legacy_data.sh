#!/bin/bash
#
# MIGRATION ENVIRONMENT - Import Legacy Data
# This script imports legacy data into the test environment for migration work
#
# WARNING: This clears existing data and imports legacy tables
#

set -e

echo "🔄 MIGRATION: Importing Legacy Data"
echo "===================================="
echo "⚠️  WARNING: This will clear existing data in TEST database"
echo "⚠️  This is for MIGRATION work only - not for regular testing"
echo ""

# Confirm action
read -p "Continue with legacy data import? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Import cancelled"
    exit 1
fi

# Check if migration environment is running
echo "🔍 Checking migration environment status..."
if ! docker compose -f docker-compose.migration.yml ps postgres | grep -q "healthy"; then
    echo "⚠️ Migration environment not running. Starting it first..."
    echo "Run: docker compose -f docker-compose.migration.yml up -d"
    exit 1
fi

# Check for legacy data files
echo "📂 Checking for legacy data files..."
if [ ! -d "data/legacy" ]; then
    echo "❌ Legacy data directory not found: data/legacy/"
    echo "Please ensure legacy CSV files are in data/legacy/ directory"
    exit 1
fi

LEGACY_FILES=$(find data/legacy -name "*.csv" 2>/dev/null | wc -l)
if [ "$LEGACY_FILES" -eq 0 ]; then
    echo "❌ No legacy CSV files found in data/legacy/"
    echo "Please place your legacy CSV files in the data/legacy/ directory"
    exit 1
fi

echo "✅ Found $LEGACY_FILES legacy CSV files"

# Clear existing data (except auth tables)
echo "🧹 Clearing existing migration data..."
docker compose -f docker-compose.migration.yml run --rm django python manage.py shell -c "
from django.db import connection
cursor = connection.cursor()

# Get list of tables to clear (exclude auth and migration tables)
cursor.execute(\"\"\"
    SELECT tablename
    FROM pg_tables
    WHERE schemaname = 'public'
    AND tablename NOT LIKE 'auth_%'
    AND tablename NOT LIKE 'django_%'
    AND tablename NOT LIKE 'account_%'
    AND tablename NOT LIKE 'socialaccount_%'
    ORDER BY tablename;
\"\"\")

tables = [row[0] for row in cursor.fetchall()]
print(f'Found {len(tables)} tables to clear')

# Disable foreign key checks and clear tables
cursor.execute('SET session_replication_role = replica;')
for table in tables:
    try:
        cursor.execute(f'TRUNCATE TABLE {table} CASCADE;')
        print(f'Cleared table: {table}')
    except Exception as e:
        print(f'Warning: Could not clear {table}: {e}')

cursor.execute('SET session_replication_role = DEFAULT;')
print('✅ Data clearing completed')
"

# Import legacy data files using Django command
echo "📥 Importing legacy CSV files..."
echo "  🔄 Running Django import_legacy_data command..."
docker compose -f docker-compose.migration.yml run --rm django python manage.py import_legacy_data --drop-tables
echo "  ✅ Legacy data import completed"

# Verify import
echo "📊 Verifying import..."
docker compose -f docker-compose.migration.yml run --rm django python manage.py shell -c "
from django.db import connection
cursor = connection.cursor()

# Get count of legacy tables
cursor.execute(\"\"\"
    SELECT COUNT(*)
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name LIKE 'legacy_%';
\"\"\")
legacy_count = cursor.fetchone()[0]

print(f'📋 Found {legacy_count} legacy tables imported')

# Show some table row counts
cursor.execute(\"\"\"
    SELECT table_name,
           (xpath('/row/c/text()', query_to_xml('SELECT COUNT(*) FROM ' || table_name, false, true, '')))[1]::text::int as row_count
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name LIKE 'legacy_%'
    ORDER BY table_name
    LIMIT 10;
\"\"\")

print('📊 Sample table row counts:')
for table_name, row_count in cursor.fetchall():
    print(f'  {table_name}: {row_count:,} rows')
"

echo ""
echo "✅ MIGRATION: Legacy data import completed!"
echo ""
echo "🗄️ Database: naga_migration_v1 (MIGRATION environment)"
echo "🌐 Django: http://localhost:8001"
echo "📋 Legacy tables imported with legacy_ prefix"
echo ""
echo "Next steps:"
echo "  1. Review imported data"
echo "  2. Run migration scripts to convert legacy data"
echo "  3. Test data integrity"
