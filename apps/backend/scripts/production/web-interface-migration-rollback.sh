#!/bin/bash
# Web Interface Migration - Emergency Rollback Script
# Usage: ./web-interface-migration-rollback.sh [reason]

set -e  # Exit on any error

ROLLBACK_REASON=${1:-"Emergency rollback requested"}
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="/tmp/web_interface_rollback_$TIMESTAMP"

echo "🚨 EMERGENCY ROLLBACK: Web Interface Migration"
echo "============================================"
echo "Timestamp: $(date)"
echo "Reason: $ROLLBACK_REASON"
echo ""

# Step 1: Create backup of current state
echo "📦 Step 1: Backing up current state..."
mkdir -p "$BACKUP_DIR"
cp config/urls.py "$BACKUP_DIR/urls_current.py"
git log --oneline -5 > "$BACKUP_DIR/recent_commits.log"

# Step 2: Revert to previous configuration
echo "⏪ Step 2: Reverting URL configuration..."
git checkout HEAD~1 -- config/urls.py
echo "   ✅ URL configuration reverted"

# Step 3: Test basic functionality
echo "🔍 Step 3: Testing rollback..."
python manage.py check --deploy > "$BACKUP_DIR/rollback_check.log" 2>&1
if [ $? -eq 0 ]; then
    echo "   ✅ Django configuration check passed"
else
    echo "   ❌ Django check failed - see $BACKUP_DIR/rollback_check.log"
    exit 1
fi

# Step 4: Restart services (Docker)
echo "🔄 Step 4: Restarting services..."
if command -v docker-compose >/dev/null; then
    docker-compose -f docker-compose.local.yml restart django
    echo "   ✅ Django service restarted"
else
    echo "   ⚠️  Manual service restart required"
fi

# Step 5: Verify rollback success
echo "✅ Step 5: Verifying rollback..."
sleep 5
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ > "$BACKUP_DIR/rollback_test.log" 2>&1
if [ $(cat "$BACKUP_DIR/rollback_test.log") -eq 200 ]; then
    echo "   ✅ Root URL responding correctly"
else
    echo "   ❌ Root URL check failed - HTTP $(cat $BACKUP_DIR/rollback_test.log)"
fi

# Step 6: Log rollback
echo "📝 Step 6: Logging rollback..."
echo "ROLLBACK COMPLETED: $TIMESTAMP" >> logs/web_interface_migration.log
echo "Reason: $ROLLBACK_REASON" >> logs/web_interface_migration.log
echo "Backup location: $BACKUP_DIR" >> logs/web_interface_migration.log

echo ""
echo "🎉 ROLLBACK COMPLETED"
echo "===================="
echo "System has been reverted to previous state"
echo "Backup files stored in: $BACKUP_DIR"
echo "Log file: logs/web_interface_migration.log"
echo ""
echo "⚠️  NEXT STEPS:"
echo "1. Verify all functionality works correctly"
echo "2. Investigate root cause of issue"
echo "3. Update migration plan before retry"
echo "4. Notify team of rollback completion"