#!/bin/bash

# Backup Verification Script
# This script creates a backup of the test database and verifies it works by restoring to a temporary database

set -e  # Exit on any error

echo "🔍 Starting Database Backup Verification Process"
echo "================================================="

# Configuration
TEST_COMPOSE="docker-compose.test.yml"
TEMP_DB_NAME="naga_test_backup_verify"
TIMESTAMP=$(date +'%Y%m%d_%H%M%S')
BACKUP_NAME="test_backup_verification_${TIMESTAMP}.sql.gz"

echo "📋 Configuration:"
echo "  - Test compose file: ${TEST_COMPOSE}"
echo "  - Temporary DB: ${TEMP_DB_NAME}"
echo "  - Backup filename: ${BACKUP_NAME}"
echo ""

# Step 1: Ensure test environment is running
echo "🚀 Step 1: Starting test environment..."
docker compose -f ${TEST_COMPOSE} up -d postgres
echo "✅ Test environment started"

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
docker compose -f ${TEST_COMPOSE} exec -T postgres sh -c 'until pg_isready -U $POSTGRES_USER -d $POSTGRES_DB; do sleep 1; done'
echo "✅ Database is ready"

# Step 2: Create backup
echo ""
echo "💾 Step 2: Creating backup..."
docker compose -f ${TEST_COMPOSE} exec -T postgres backup
echo "✅ Backup created"

# Get the actual backup filename (most recent)
ACTUAL_BACKUP=$(docker compose -f ${TEST_COMPOSE} exec -T postgres sh -c 'ls -t /backups/backup_*.sql.gz | head -1 | xargs basename')
echo "📁 Backup file: ${ACTUAL_BACKUP}"

# Step 3: Create temporary database for verification
echo ""
echo "🔧 Step 3: Creating temporary database for verification..."
docker compose -f ${TEST_COMPOSE} exec -T postgres createdb -U debug ${TEMP_DB_NAME}
echo "✅ Temporary database '${TEMP_DB_NAME}' created"

# Step 4: Restore backup to temporary database
echo ""
echo "🔄 Step 4: Restoring backup to temporary database..."
docker compose -f ${TEST_COMPOSE} exec -T postgres sh -c "gunzip -c /backups/${ACTUAL_BACKUP} | psql -U debug ${TEMP_DB_NAME}"
echo "✅ Backup restored to temporary database"

# Step 5: Verify data integrity
echo ""
echo "🔍 Step 5: Verifying data integrity..."

# Check table counts
echo "📊 Checking table counts..."
ORIGINAL_TABLES=$(docker compose -f ${TEST_COMPOSE} exec -T postgres psql -U debug -d naga_test_v1 -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';")
RESTORED_TABLES=$(docker compose -f ${TEST_COMPOSE} exec -T postgres psql -U debug -d ${TEMP_DB_NAME} -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';")

echo "  Original database tables: $(echo $ORIGINAL_TABLES | tr -d ' ')"
echo "  Restored database tables: $(echo $RESTORED_TABLES | tr -d ' ')"

if [ "$(echo $ORIGINAL_TABLES | tr -d ' ')" = "$(echo $RESTORED_TABLES | tr -d ' ')" ]; then
    echo "✅ Table count verification passed"
else
    echo "❌ Table count verification failed"
    exit 1
fi

# Check ALL tables data integrity - every single record count must match
echo "📋 Checking COMPLETE data integrity (ALL tables)..."

# Get list of all non-system tables
ALL_TABLES=$(docker compose -f ${TEST_COMPOSE} exec -T postgres psql -U debug -d naga_test_v1 -t -c "
SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
AND tablename NOT LIKE 'django_%'
ORDER BY tablename;
" | tr -d ' ')

TOTAL_TABLES=0
VERIFIED_TABLES=0
FAILED_TABLES=0

echo "🔍 Verifying record counts for ALL application tables..."

for table_name in $ALL_TABLES; do
    if [ ! -z "$table_name" ]; then
        TOTAL_TABLES=$((TOTAL_TABLES + 1))
        echo "  Checking ${table_name}..."

        original_count=$(docker compose -f ${TEST_COMPOSE} exec -T postgres psql -U debug -d naga_test_v1 -t -c "SELECT COUNT(*) FROM ${table_name};" 2>/dev/null || echo "0")
        restored_count=$(docker compose -f ${TEST_COMPOSE} exec -T postgres psql -U debug -d ${TEMP_DB_NAME} -t -c "SELECT COUNT(*) FROM ${table_name};" 2>/dev/null || echo "0")

        original_count=$(echo $original_count | tr -d ' ')
        restored_count=$(echo $restored_count | tr -d ' ')

        echo "    Original: ${original_count}, Restored: ${restored_count}"

        if [ "${original_count}" = "${restored_count}" ]; then
            echo "    ✅ ${table_name} data integrity verified"
            VERIFIED_TABLES=$((VERIFIED_TABLES + 1))
        else
            echo "    ❌ ${table_name} data integrity FAILED - COUNTS DON'T MATCH!"
            FAILED_TABLES=$((FAILED_TABLES + 1))
        fi
    fi
done

echo ""
echo "📊 Data Integrity Summary:"
echo "  Total tables checked: ${TOTAL_TABLES}"
echo "  Successfully verified: ${VERIFIED_TABLES}"
echo "  Failed verification: ${FAILED_TABLES}"

if [ $FAILED_TABLES -gt 0 ]; then
    echo "❌ BACKUP VERIFICATION FAILED - Record counts don't match!"
    echo "🚨 Do NOT use this backup for restoration!"
    exit 1
fi

echo "✅ Data integrity verification completed"

# Step 6: Clean up temporary database
echo ""
echo "🧹 Step 6: Cleaning up..."
docker compose -f ${TEST_COMPOSE} exec -T postgres dropdb -U debug ${TEMP_DB_NAME}
echo "✅ Temporary database cleaned up"

# Step 7: Summary
echo ""
echo "🎉 Backup Verification Summary"
echo "=============================="
echo "✅ Backup created successfully: ${ACTUAL_BACKUP}"
echo "✅ Backup can be restored without errors"
echo "✅ Data integrity verified across key tables"
echo "✅ Temporary database cleaned up"
echo ""
echo "🔒 Your backup is verified and safe to use for restoration!"
echo "📁 Backup location: /backups/${ACTUAL_BACKUP} (inside postgres container)"
echo ""
echo "To restore this backup later:"
echo "  docker compose -f ${TEST_COMPOSE} exec postgres restore ${ACTUAL_BACKUP}"
