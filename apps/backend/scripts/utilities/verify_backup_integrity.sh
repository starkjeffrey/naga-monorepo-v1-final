#!/bin/bash
# Script to verify backup integrity by restoring to a temporary database and comparing record counts

echo "🔍 Starting backup integrity verification..."
echo "📅 Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"

# Change to backend directory
cd /Users/jeffreystark/PycharmProjects/naga-monorepo/backend

# Configuration
BACKUP_FILE="backup_2025_08_01T23_54_11.sql.gz"
TEMP_DB="naga_local_verify"
ORIGINAL_DB="naga_local"

# Step 1: Create temporary database
echo -e "\n📦 Creating temporary database: $TEMP_DB"
docker compose -f docker-compose.local.yml exec -T postgres psql -U debug -d naga_local -c "DROP DATABASE IF EXISTS $TEMP_DB;"
docker compose -f docker-compose.local.yml exec -T postgres psql -U debug -d naga_local -c "CREATE DATABASE $TEMP_DB;"

# Step 2: Restore backup to temporary database
echo -e "\n🔄 Restoring backup to temporary database..."
docker compose -f docker-compose.local.yml exec -T postgres bash -c "gunzip -c /backups/$BACKUP_FILE | psql -U debug -d $TEMP_DB" > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "✅ Backup restored successfully to $TEMP_DB"
else
    echo "❌ Failed to restore backup"
    exit 1
fi

# Step 3: Compare record counts
echo -e "\n📊 Comparing record counts between databases..."
echo -e "\nTable Name | Original DB | Restored DB | Difference"
echo "-----------|-------------|-------------|------------"

# Get list of tables from original database
TABLES=$(docker compose -f docker-compose.local.yml exec -T postgres psql -U debug -d naga_local -d $ORIGINAL_DB -t -c "
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_type = 'BASE TABLE'
    AND table_name NOT LIKE '%django_migrations%'
    ORDER BY table_name;
")

TOTAL_DIFF=0
TABLES_WITH_DIFF=0

for TABLE in $TABLES; do
    # Get count from original database
    ORIGINAL_COUNT=$(docker compose -f docker-compose.local.yml exec -T postgres psql -U debug -d naga_local -d $ORIGINAL_DB -t -c "SELECT COUNT(*) FROM $TABLE;" | tr -d ' ')
    
    # Get count from restored database
    RESTORED_COUNT=$(docker compose -f docker-compose.local.yml exec -T postgres psql -U debug -d naga_local -d $TEMP_DB -t -c "SELECT COUNT(*) FROM $TABLE;" | tr -d ' ')
    
    # Calculate difference
    DIFF=$((ORIGINAL_COUNT - RESTORED_COUNT))
    
    # Only show tables with data or differences
    if [ "$ORIGINAL_COUNT" -gt 0 ] || [ "$RESTORED_COUNT" -gt 0 ] || [ "$DIFF" -ne 0 ]; then
        if [ "$DIFF" -eq 0 ]; then
            echo "$TABLE | $ORIGINAL_COUNT | $RESTORED_COUNT | ✅ 0"
        else
            echo "$TABLE | $ORIGINAL_COUNT | $RESTORED_COUNT | ⚠️  $DIFF"
            TABLES_WITH_DIFF=$((TABLES_WITH_DIFF + 1))
            TOTAL_DIFF=$((TOTAL_DIFF + DIFF))
        fi
    fi
done

echo -e "\n📈 Summary:"
echo "Total tables checked: $(echo "$TABLES" | wc -w)"
echo "Tables with differences: $TABLES_WITH_DIFF"
echo "Total record difference: $TOTAL_DIFF"

# Step 4: Check backup file details
echo -e "\n📁 Backup file details:"
docker compose -f docker-compose.local.yml exec -T postgres ls -lh /backups/$BACKUP_FILE

# Step 5: Cleanup - drop temporary database
echo -e "\n🧹 Cleaning up temporary database..."
docker compose -f docker-compose.local.yml exec -T postgres psql -U debug -d naga_local -c "DROP DATABASE IF EXISTS $TEMP_DB;"
echo "✅ Temporary database removed"

# Final verdict
echo -e "\n🎯 Verification Result:"
if [ "$TABLES_WITH_DIFF" -eq 0 ] && [ "$TOTAL_DIFF" -eq 0 ]; then
    echo "✅ BACKUP VERIFIED: All record counts match perfectly!"
    echo "   The backup process is working correctly."
else
    echo "⚠️  WARNING: Found differences in $TABLES_WITH_DIFF tables"
    echo "   Total record difference: $TOTAL_DIFF"
    echo "   Please investigate the discrepancies."
fi