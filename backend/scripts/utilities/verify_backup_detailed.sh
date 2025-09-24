#!/bin/bash
# Detailed backup verification with table counts

echo "🔍 Performing detailed backup verification..."
cd /Users/jeffreystark/PycharmProjects/naga-monorepo/backend

# Configuration
BACKUP_FILE="backup_2025_08_01T23_54_11.sql.gz"
TEMP_DB="naga_verify_temp"
ORIGINAL_DB="naga_local"

echo -e "\n📋 Backup file details:"
docker compose -f docker-compose.local.yml exec postgres ls -lh /backups/$BACKUP_FILE

echo -e "\n1️⃣ Creating temporary database..."
docker compose -f docker-compose.local.yml exec postgres createdb -U debug $TEMP_DB 2>/dev/null || echo "Database may already exist"

echo -e "\n2️⃣ Restoring backup to temporary database (this may take a moment)..."
docker compose -f docker-compose.local.yml exec postgres bash -c "gunzip -c /backups/$BACKUP_FILE | psql -U debug -d $TEMP_DB -q" 2>&1 | grep -v "already exists" | grep -v "setval"

echo -e "\n3️⃣ Comparing table record counts..."
echo -e "\nDetailed Table Comparison:"
echo "========================================="
printf "%-35s | %10s | %10s | Status\n" "Table Name" "Original" "Backup"
echo "========================================="

# Get all tables from the original database
TABLES=$(docker compose -f docker-compose.local.yml exec -T postgres psql -U debug -d $ORIGINAL_DB -t -c "
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_type = 'BASE TABLE'
    ORDER BY table_name;" | grep -v "^$")

TOTAL_TABLES=0
MATCHING_TABLES=0
MISMATCHED_TABLES=0

for TABLE in $TABLES; do
    # Skip django_migrations table
    if [[ "$TABLE" == "django_migrations" ]]; then
        continue
    fi
    
    # Get count from original database
    ORIG_COUNT=$(docker compose -f docker-compose.local.yml exec -T postgres psql -U debug -d $ORIGINAL_DB -t -c "SELECT COUNT(*) FROM $TABLE;" 2>/dev/null | tr -d ' ')
    
    # Get count from restored database
    TEMP_COUNT=$(docker compose -f docker-compose.local.yml exec -T postgres psql -U debug -d $TEMP_DB -t -c "SELECT COUNT(*) FROM $TABLE;" 2>/dev/null | tr -d ' ')
    
    # Only show non-empty tables
    if [[ -n "$ORIG_COUNT" && -n "$TEMP_COUNT" && ("$ORIG_COUNT" != "0" || "$TEMP_COUNT" != "0") ]]; then
        TOTAL_TABLES=$((TOTAL_TABLES + 1))
        
        if [[ "$ORIG_COUNT" == "$TEMP_COUNT" ]]; then
            printf "%-35s | %10s | %10s | ✅\n" "$TABLE" "$ORIG_COUNT" "$TEMP_COUNT"
            MATCHING_TABLES=$((MATCHING_TABLES + 1))
        else
            printf "%-35s | %10s | %10s | ❌ MISMATCH\n" "$TABLE" "$ORIG_COUNT" "$TEMP_COUNT"
            MISMATCHED_TABLES=$((MISMATCHED_TABLES + 1))
        fi
    fi
done

echo "========================================="

echo -e "\n📊 Summary:"
echo "Total tables with data: $TOTAL_TABLES"
echo "Matching tables: $MATCHING_TABLES"
echo "Mismatched tables: $MISMATCHED_TABLES"

# Database size comparison
echo -e "\n4️⃣ Comparing database sizes..."
ORIG_SIZE=$(docker compose -f docker-compose.local.yml exec -T postgres psql -U debug -d naga_local -t -c "SELECT pg_size_pretty(pg_database_size('$ORIGINAL_DB'));" | tr -d ' ')
TEMP_SIZE=$(docker compose -f docker-compose.local.yml exec -T postgres psql -U debug -d naga_local -t -c "SELECT pg_size_pretty(pg_database_size('$TEMP_DB'));" | tr -d ' ')

echo "Original database size: $ORIG_SIZE"
echo "Restored database size: $TEMP_SIZE"

# Check schema consistency
echo -e "\n5️⃣ Verifying schema consistency..."
ORIG_TABLE_COUNT=$(docker compose -f docker-compose.local.yml exec -T postgres psql -U debug -d $ORIGINAL_DB -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" | tr -d ' ')
TEMP_TABLE_COUNT=$(docker compose -f docker-compose.local.yml exec -T postgres psql -U debug -d $TEMP_DB -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" | tr -d ' ')

echo "Original database tables: $ORIG_TABLE_COUNT"
echo "Restored database tables: $TEMP_TABLE_COUNT"

echo -e "\n6️⃣ Cleaning up..."
docker compose -f docker-compose.local.yml exec postgres dropdb -U debug $TEMP_DB

echo -e "\n🎯 Verification Result:"
if [[ "$MISMATCHED_TABLES" -eq 0 && "$ORIG_TABLE_COUNT" == "$TEMP_TABLE_COUNT" ]]; then
    echo "✅ BACKUP VERIFIED SUCCESSFULLY!"
    echo "   All table counts match and schema is consistent."
    echo "   The backup process is working correctly."
else
    echo "⚠️  WARNING: Verification found issues:"
    if [[ "$MISMATCHED_TABLES" -gt 0 ]]; then
        echo "   - $MISMATCHED_TABLES tables have different record counts"
    fi
    if [[ "$ORIG_TABLE_COUNT" != "$TEMP_TABLE_COUNT" ]]; then
        echo "   - Schema differences detected"
    fi
fi