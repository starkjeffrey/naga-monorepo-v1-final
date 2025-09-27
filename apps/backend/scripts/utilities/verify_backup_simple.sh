#!/bin/bash
# Simple backup verification script

echo "🔍 Verifying backup integrity..."
cd /Users/jeffreystark/PycharmProjects/naga-monorepo/backend

# Configuration
BACKUP_FILE="backup_2025_08_01T23_54_11.sql.gz"
TEMP_DB="naga_verify_temp"
ORIGINAL_DB="naga_local"

echo -e "\n1️⃣ Creating temporary database..."
docker compose -f docker-compose.local.yml exec postgres createdb -U debug $TEMP_DB

echo -e "\n2️⃣ Restoring backup to temporary database..."
docker compose -f docker-compose.local.yml exec postgres bash -c "gunzip -c /backups/$BACKUP_FILE | psql -U debug -d $TEMP_DB -q"

echo -e "\n3️⃣ Counting records in both databases..."
echo -e "\nTable Comparison:"
echo "================="

# Define key tables to check
TABLES=(
    "curriculum_term"
    "curriculum_course" 
    "curriculum_division"
    "curriculum_major"
    "people_person"
    "people_studentprofile"
    "finance_defaultpricing"
    "finance_discountrule"
    "common_holiday"
    "common_room"
)

for TABLE in "${TABLES[@]}"; do
    # Get counts
    ORIG_COUNT=$(docker compose -f docker-compose.local.yml exec -T postgres psql -U debug -d $ORIGINAL_DB -t -c "SELECT COUNT(*) FROM $TABLE 2>/dev/null;" 2>/dev/null | tr -d ' ' | head -1)
    TEMP_COUNT=$(docker compose -f docker-compose.local.yml exec -T postgres psql -U debug -d $TEMP_DB -t -c "SELECT COUNT(*) FROM $TABLE 2>/dev/null;" 2>/dev/null | tr -d ' ' | head -1)
    
    # Format output
    if [ -n "$ORIG_COUNT" ] && [ -n "$TEMP_COUNT" ]; then
        if [ "$ORIG_COUNT" = "$TEMP_COUNT" ]; then
            printf "%-30s Original: %6s | Backup: %6s | ✅\n" "$TABLE" "$ORIG_COUNT" "$TEMP_COUNT"
        else
            printf "%-30s Original: %6s | Backup: %6s | ❌ MISMATCH\n" "$TABLE" "$ORIG_COUNT" "$TEMP_COUNT"
        fi
    fi
done

echo -e "\n4️⃣ Checking database sizes..."
ORIG_SIZE=$(docker compose -f docker-compose.local.yml exec -T postgres psql -U debug -d naga_local -t -c "SELECT pg_size_pretty(pg_database_size('$ORIGINAL_DB'));" | tr -d ' ')
TEMP_SIZE=$(docker compose -f docker-compose.local.yml exec -T postgres psql -U debug -d naga_local -t -c "SELECT pg_size_pretty(pg_database_size('$TEMP_DB'));" | tr -d ' ')

echo "Original DB size: $ORIG_SIZE"
echo "Restored DB size: $TEMP_SIZE"

echo -e "\n5️⃣ Cleaning up..."
docker compose -f docker-compose.local.yml exec postgres dropdb -U debug $TEMP_DB

echo -e "\n✅ Verification complete!"