#!/bin/bash

# scheduled-integrity-check.sh - Automated database integrity monitoring
# Can be run via cron, systemd timer, or CI/CD pipeline

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_DIR="$PROJECT_ROOT/logs/integrity"
REPORT_DIR="$PROJECT_ROOT/project-docs/integrity-reports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DATE=$(date +%Y-%m-%d)

# Create directories if they don't exist
mkdir -p "$LOG_DIR"
mkdir -p "$REPORT_DIR"

# Log file paths
DAILY_LOG="$LOG_DIR/daily-check-$DATE.log"
ALERT_LOG="$LOG_DIR/alerts-$DATE.log"
REPORT_FILE="$REPORT_DIR/integrity-report-$TIMESTAMP.json"

# Alert thresholds
CRITICAL_THRESHOLD=1
WARNING_THRESHOLD=5

# Slack webhook (set via environment variable)
SLACK_WEBHOOK="${SLACK_WEBHOOK_URL:-}"

# Email settings (set via environment variables)
ALERT_EMAIL="${INTEGRITY_ALERT_EMAIL:-}"
SMTP_SERVER="${SMTP_SERVER:-localhost}"

# Colors for terminal output (disabled in non-interactive mode)
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    NC=''
fi

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$DAILY_LOG"
}

# Function to send alerts
send_alert() {
    local severity="$1"
    local message="$2"
    local details="$3"

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$severity] $message" >> "$ALERT_LOG"

    # Send Slack alert if webhook configured
    if [ -n "$SLACK_WEBHOOK" ]; then
        send_slack_alert "$severity" "$message" "$details"
    fi

    # Send email alert if configured
    if [ -n "$ALERT_EMAIL" ]; then
        send_email_alert "$severity" "$message" "$details"
    fi
}

# Function to send Slack alert
send_slack_alert() {
    local severity="$1"
    local message="$2"
    local details="$3"

    local color="good"
    local emoji="✅"

    if [ "$severity" = "CRITICAL" ]; then
        color="danger"
        emoji="🚨"
    elif [ "$severity" = "WARNING" ]; then
        color="warning"
        emoji="⚠️"
    fi

    local payload=$(cat <<EOF
{
    "attachments": [{
        "color": "$color",
        "title": "$emoji Database Integrity Alert - $severity",
        "text": "$message",
        "fields": [{
            "title": "Environment",
            "value": "${ENVIRONMENT:-development}",
            "short": true
        }, {
            "title": "Timestamp",
            "value": "$(date '+%Y-%m-%d %H:%M:%S')",
            "short": true
        }, {
            "title": "Details",
            "value": "$details",
            "short": false
        }],
        "footer": "Naga SIS Integrity Monitor"
    }]
}
EOF
)

    curl -X POST -H 'Content-type: application/json' \
         --data "$payload" "$SLACK_WEBHOOK" 2>/dev/null || true
}

# Function to send email alert
send_email_alert() {
    local severity="$1"
    local message="$2"
    local details="$3"

    if command -v mail >/dev/null 2>&1; then
        echo -e "Severity: $severity\n\nMessage: $message\n\nDetails:\n$details\n\nTimestamp: $(date)" | \
            mail -s "[Naga SIS] Database Integrity Alert - $severity" "$ALERT_EMAIL"
    fi
}

# Main execution
log_message "Starting database integrity check"

# Step 1: Check if database is accessible
log_message "Checking database connectivity..."
if ! docker compose -f docker-compose.local.yml exec -T postgres pg_isready -U debug -d naga_local >/dev/null 2>&1; then
    send_alert "CRITICAL" "Database is not accessible" "PostgreSQL connection failed"
    exit 1
fi

# Step 2: Run Python integrity monitor
log_message "Running integrity monitor..."
MONITOR_OUTPUT=$(docker compose -f docker-compose.local.yml run --rm -T django \
    python scripts/ci-cd/integrity-monitor.py --format json 2>&1) || MONITOR_EXIT=$?

# Save monitor output
echo "$MONITOR_OUTPUT" > "$REPORT_FILE"

# Parse results
CRITICAL_COUNT=$(echo "$MONITOR_OUTPUT" | grep -o '"severity": "CRITICAL"' | wc -l || echo 0)
WARNING_COUNT=$(echo "$MONITOR_OUTPUT" | grep -o '"severity": "WARNING"' | wc -l || echo 0)
EXIT_CODE=$(echo "$MONITOR_OUTPUT" | grep -o '"exit_code": [0-9]*' | grep -o '[0-9]*' || echo 0)

log_message "Check complete: $CRITICAL_COUNT critical issues, $WARNING_COUNT warnings"

# Step 3: Check migration status
log_message "Checking for unapplied migrations..."
UNAPPLIED=$(docker compose -f docker-compose.local.yml run --rm -T django \
    python manage.py showmigrations --plan 2>/dev/null | grep "\[ \]" | wc -l || echo 0)

if [ "$UNAPPLIED" -gt 0 ]; then
    send_alert "CRITICAL" "Unapplied migrations detected" "$UNAPPLIED migrations pending"
    CRITICAL_COUNT=$((CRITICAL_COUNT + 1))
fi

# Step 4: Check for model changes
log_message "Checking for unmigrated model changes..."
if ! docker compose -f docker-compose.local.yml run --rm -T django \
    python manage.py makemigrations --check --dry-run >/dev/null 2>&1; then
    send_alert "CRITICAL" "Model changes without migrations" "Run makemigrations to create migrations"
    CRITICAL_COUNT=$((CRITICAL_COUNT + 1))
fi

# Step 5: Quick NULL constraint check
log_message "Running quick constraint validation..."
CONSTRAINT_CHECK=$(docker compose -f docker-compose.local.yml exec -T postgres psql -U debug -d naga_local -t -c "
    SELECT COUNT(*)
    FROM information_schema.columns c
    JOIN information_schema.tables t ON c.table_name = t.table_name
    WHERE t.table_schema = 'public'
    AND t.table_type = 'BASE TABLE'
    AND c.column_name NOT IN ('id', 'created_at', 'updated_at')
    AND c.is_nullable = 'YES'
    AND c.table_name LIKE 'finance_%'
" 2>/dev/null | xargs)

if [ "$CONSTRAINT_CHECK" -gt 20 ]; then
    WARNING_COUNT=$((WARNING_COUNT + 1))
    log_message "Warning: High number of nullable columns in finance tables ($CONSTRAINT_CHECK)"
fi

# Step 6: Determine overall status and send alerts
if [ "$CRITICAL_COUNT" -gt 0 ]; then
    STATUS="CRITICAL"
    STATUS_COLOR="$RED"
    send_alert "CRITICAL" "Database integrity check failed" "$CRITICAL_COUNT critical issues found"
elif [ "$WARNING_COUNT" -gt "$WARNING_THRESHOLD" ]; then
    STATUS="WARNING"
    STATUS_COLOR="$YELLOW"
    send_alert "WARNING" "Database integrity warnings" "$WARNING_COUNT warnings found"
else
    STATUS="HEALTHY"
    STATUS_COLOR="$GREEN"
fi

# Step 7: Generate summary
log_message "Generating summary report..."
cat >> "$DAILY_LOG" <<EOF

================================================================================
                          INTEGRITY CHECK SUMMARY
================================================================================
Date:           $(date)
Status:         $STATUS
Critical:       $CRITICAL_COUNT
Warnings:       $WARNING_COUNT
Report:         $REPORT_FILE
================================================================================

EOF

# Step 8: Cleanup old logs (keep 30 days)
log_message "Cleaning up old logs..."
find "$LOG_DIR" -name "*.log" -mtime +30 -delete 2>/dev/null || true
find "$REPORT_DIR" -name "*.json" -mtime +90 -delete 2>/dev/null || true

# Step 9: Exit with appropriate code
echo -e "${STATUS_COLOR}Database Integrity Status: $STATUS${NC}"

if [ "$CRITICAL_COUNT" -gt 0 ]; then
    exit 2
elif [ "$WARNING_COUNT" -gt "$WARNING_THRESHOLD" ]; then
    exit 1
else
    exit 0
fi
