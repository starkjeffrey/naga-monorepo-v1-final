#!/usr/bin/env bash

###
### AUTOMATED BACKUP PIPELINE
### Complete backup solution: Local backup + Google Drive sync + monitoring
###
### This script integrates:
### - Production database backup
### - Google Drive cloud storage
### - Integrity verification
### - Monitoring and alerting
###
### Usage:
###     ./scripts/automated-backup-pipeline.sh daily
###     ./scripts/automated-backup-pipeline.sh weekly
###     ./scripts/automated-backup-pipeline.sh manual [database]
###

set -o errexit
set -o pipefail
set -o nounset

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKUP_DIR="${PROJECT_ROOT}/backups"
LOG_FILE="${BACKUP_DIR}/automated-backup.log"

# Backup configuration
ENABLE_GDRIVE_SYNC=true
ENABLE_NOTIFICATIONS=false  # Set to true to enable notifications
NOTIFICATION_EMAIL="your-email@example.com"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Enhanced logging
log_pipeline() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[${timestamp}] [PIPELINE-${level}] ${message}" >> "${LOG_FILE}"
    
    case "${level}" in
        "INFO")  echo -e "${BLUE}[PIPELINE-INFO]${NC} ${message}" ;;
        "SUCCESS") echo -e "${GREEN}[PIPELINE-SUCCESS]${NC} ${message}" ;;
        "WARNING") echo -e "${YELLOW}[PIPELINE-WARNING]${NC} ${message}" ;;
        "ERROR") echo -e "${RED}[PIPELINE-ERROR]${NC} ${message}" ;;
        "CRITICAL") echo -e "${RED}[PIPELINE-CRITICAL]${NC} ${message}" ;;
    esac
}

# Send notification (optional)
send_notification() {
    local subject="$1"
    local message="$2"
    local level="${3:-INFO}"
    
    if [[ "${ENABLE_NOTIFICATIONS}" == true ]]; then
        # Email notification (requires mail command or sendmail)
        if command -v mail >/dev/null 2>&1; then
            echo "${message}" | mail -s "Naga SIS Backup: ${subject}" "${NOTIFICATION_EMAIL}"
            log_pipeline "INFO" "Notification sent: ${subject}"
        fi
        
        # macOS notification
        if command -v osascript >/dev/null 2>&1; then
            osascript -e "display notification \"${message}\" with title \"Naga SIS Backup\" subtitle \"${subject}\""
        fi
        
        # Linux desktop notification
        if command -v notify-send >/dev/null 2>&1; then
            notify-send "Naga SIS Backup" "${subject}: ${message}"
        fi
    fi
}

# Daily backup routine
daily_backup() {
    log_pipeline "INFO" "Starting daily backup routine..."
    
    local backup_success=true
    local backup_files=()
    
    # Backup local database
    log_pipeline "INFO" "Creating local database backup..."
    if "${SCRIPT_DIR}/production-backup-system.sh" backup naga_local sql; then
        log_pipeline "SUCCESS" "Local database backup completed"
        
        # Find the most recent backup
        local latest_backup
        latest_backup=$(find "${BACKUP_DIR}" -name "naga_local_*.sql.gz" -type f -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)
        
        if [[ -n "${latest_backup}" ]]; then
            backup_files+=("${latest_backup}")
            log_pipeline "SUCCESS" "Latest backup: $(basename ${latest_backup})"
        fi
    else
        log_pipeline "ERROR" "Local database backup failed"
        backup_success=false
    fi
    
    # Google Drive sync (if enabled)
    if [[ "${ENABLE_GDRIVE_SYNC}" == true ]] && [[ "${backup_success}" == true ]]; then
        log_pipeline "INFO" "Syncing to Google Drive..."
        
        for backup_file in "${backup_files[@]}"; do
            if "${SCRIPT_DIR}/backup-google-drive.sh" upload "${backup_file}"; then
                log_pipeline "SUCCESS" "Google Drive sync completed: $(basename ${backup_file})"
            else
                log_pipeline "WARNING" "Google Drive sync failed: $(basename ${backup_file})"
                backup_success=false
            fi
        done
    fi
    
    # Generate summary report
    local summary_message
    if [[ "${backup_success}" == true ]]; then
        summary_message="Daily backup completed successfully. ${#backup_files[@]} backup(s) created and synced."
        log_pipeline "SUCCESS" "Daily backup routine completed successfully"
        send_notification "Daily Backup Success" "${summary_message}" "SUCCESS"
    else
        summary_message="Daily backup completed with errors. Check logs for details."
        log_pipeline "ERROR" "Daily backup routine completed with errors"
        send_notification "Daily Backup Failed" "${summary_message}" "ERROR"
    fi
    
    return $([[ "${backup_success}" == true ]] && echo 0 || echo 1)
}

# Weekly backup routine
weekly_backup() {
    log_pipeline "INFO" "Starting weekly backup routine..."
    
    local backup_success=true
    local backup_files=()
    
    # Backup both databases with custom format for faster restores
    for database in "naga_local" "naga_migration"; do
        log_pipeline "INFO" "Creating weekly backup for: ${database}"
        
        if "${SCRIPT_DIR}/production-backup-system.sh" backup "${database}" both; then
            log_pipeline "SUCCESS" "Weekly backup completed: ${database}"
            
            # Find the most recent backups
            local latest_sql
            latest_sql=$(find "${BACKUP_DIR}" -name "${database}_*.sql.gz" -type f -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)
            local latest_dump
            latest_dump=$(find "${BACKUP_DIR}" -name "${database}_*.dump" -type f -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)
            
            [[ -n "${latest_sql}" ]] && backup_files+=("${latest_sql}")
            [[ -n "${latest_dump}" ]] && backup_files+=("${latest_dump}")
        else
            log_pipeline "ERROR" "Weekly backup failed: ${database}"
            backup_success=false
        fi
    done
    
    # Google Drive sync
    if [[ "${ENABLE_GDRIVE_SYNC}" == true ]] && [[ "${backup_success}" == true ]]; then
        log_pipeline "INFO" "Syncing weekly backups to Google Drive..."
        
        for backup_file in "${backup_files[@]}"; do
            if "${SCRIPT_DIR}/backup-google-drive.sh" upload "${backup_file}"; then
                log_pipeline "SUCCESS" "Google Drive sync completed: $(basename ${backup_file})"
            else
                log_pipeline "WARNING" "Google Drive sync failed: $(basename ${backup_file})"
            fi
        done
        
        # Clean up old Google Drive backups
        "${SCRIPT_DIR}/backup-google-drive.sh" cleanup
    fi
    
    # Clean up local backups
    "${SCRIPT_DIR}/production-backup-system.sh" cleanup
    
    # Generate comprehensive report
    "${SCRIPT_DIR}/production-backup-system.sh" report naga_local
    
    # Summary notification
    local summary_message
    if [[ "${backup_success}" == true ]]; then
        summary_message="Weekly backup completed successfully. ${#backup_files[@]} backup(s) created and synced."
        log_pipeline "SUCCESS" "Weekly backup routine completed successfully"
        send_notification "Weekly Backup Success" "${summary_message}" "SUCCESS"
    else
        summary_message="Weekly backup completed with errors. Check logs for details."
        log_pipeline "ERROR" "Weekly backup routine completed with errors"
        send_notification "Weekly Backup Failed" "${summary_message}" "ERROR"
    fi
    
    return $([[ "${backup_success}" == true ]] && echo 0 || echo 1)
}

# Manual backup with options
manual_backup() {
    local database="${1:-naga_local}"
    local backup_type="${2:-both}"
    
    log_pipeline "INFO" "Starting manual backup: ${database} (${backup_type})"
    
    # Create backup
    if "${SCRIPT_DIR}/production-backup-system.sh" backup "${database}" "${backup_type}"; then
        log_pipeline "SUCCESS" "Manual backup completed: ${database}"
        
        # Optional Google Drive sync
        if [[ "${ENABLE_GDRIVE_SYNC}" == true ]]; then
            read -p "Upload to Google Drive? (y/n): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                # Find the most recent backup
                local latest_backup
                latest_backup=$(find "${BACKUP_DIR}" -name "${database}_*.sql.gz" -o -name "${database}_*.dump" -type f -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)
                
                if [[ -n "${latest_backup}" ]]; then
                    "${SCRIPT_DIR}/backup-google-drive.sh" upload "${latest_backup}"
                fi
            fi
        fi
        
        # Generate report
        "${SCRIPT_DIR}/production-backup-system.sh" report "${database}"
        
        return 0
    else
        log_pipeline "ERROR" "Manual backup failed: ${database}"
        return 1
    fi
}

# System health check
health_check() {
    log_pipeline "INFO" "Performing backup system health check..."
    
    local issues=0
    
    # Check disk space
    local backup_dir_usage
    backup_dir_usage=$(du -sh "${BACKUP_DIR}" | cut -f1)
    local available_space
    available_space=$(df -h "${BACKUP_DIR}" | awk 'NR==2{print $4}')
    
    log_pipeline "INFO" "Backup directory usage: ${backup_dir_usage}"
    log_pipeline "INFO" "Available space: ${available_space}"
    
    # Check backup file count
    local backup_count
    backup_count=$(find "${BACKUP_DIR}" -name "*.sql.gz" -o -name "*.dump" | wc -l)
    
    if [[ "${backup_count}" -eq 0 ]]; then
        log_pipeline "WARNING" "No backup files found"
        issues=$((issues + 1))
    else
        log_pipeline "SUCCESS" "Found ${backup_count} backup files"
    fi
    
    # Check Google Drive connectivity (if enabled)
    if [[ "${ENABLE_GDRIVE_SYNC}" == true ]]; then
        if command -v rclone >/dev/null 2>&1; then
            if rclone lsd gdrive: >/dev/null 2>&1; then
                log_pipeline "SUCCESS" "Google Drive connectivity OK"
            else
                log_pipeline "WARNING" "Google Drive connectivity failed"
                issues=$((issues + 1))
            fi
        else
            log_pipeline "WARNING" "rclone not installed - Google Drive sync disabled"
            issues=$((issues + 1))
        fi
    fi
    
    # Check log file size
    if [[ -f "${LOG_FILE}" ]]; then
        local log_size
        log_size=$(du -sh "${LOG_FILE}" | cut -f1)
        log_pipeline "INFO" "Log file size: ${log_size}"
    fi
    
    if [[ "${issues}" -eq 0 ]]; then
        log_pipeline "SUCCESS" "Backup system health check passed"
        return 0
    else
        log_pipeline "WARNING" "Backup system health check found ${issues} issue(s)"
        return 1
    fi
}

# Setup cron jobs
setup_cron() {
    log_pipeline "INFO" "Setting up automated backup cron jobs..."
    
    local script_path="${SCRIPT_DIR}/automated-backup-pipeline.sh"
    local cron_file="/tmp/naga_backup_cron"
    
    # Get current crontab
    crontab -l > "${cron_file}" 2>/dev/null || true
    
    # Remove existing naga backup entries
    grep -v "naga.*backup" "${cron_file}" > "${cron_file}.tmp" || true
    mv "${cron_file}.tmp" "${cron_file}"
    
    # Add new cron jobs
    echo "# Naga SIS Automated Backups" >> "${cron_file}"
    echo "0 2 * * * ${script_path} daily" >> "${cron_file}"
    echo "0 3 * * 0 ${script_path} weekly" >> "${cron_file}"
    echo "0 4 * * 0 ${script_path} health" >> "${cron_file}"
    echo "" >> "${cron_file}"
    
    # Install new crontab
    crontab "${cron_file}"
    rm -f "${cron_file}"
    
    log_pipeline "SUCCESS" "Cron jobs installed:"
    log_pipeline "INFO" "  Daily backup: 2:00 AM every day"
    log_pipeline "INFO" "  Weekly backup: 3:00 AM every Sunday"
    log_pipeline "INFO" "  Health check: 4:00 AM every Sunday"
}

# Main function
main() {
    local command="${1:-help}"
    
    # Ensure backup directory and log file exist
    mkdir -p "${BACKUP_DIR}"
    touch "${LOG_FILE}"
    
    case "${command}" in
        "daily")
            daily_backup
            ;;
            
        "weekly")
            weekly_backup
            ;;
            
        "manual")
            manual_backup "${2:-naga_local}" "${3:-both}"
            ;;
            
        "health")
            health_check
            ;;
            
        "setup-cron")
            setup_cron
            ;;
            
        "status")
            echo -e "${CYAN}=== BACKUP SYSTEM STATUS ===${NC}"
            health_check
            echo
            "${SCRIPT_DIR}/production-backup-system.sh" report naga_local
            if [[ "${ENABLE_GDRIVE_SYNC}" == true ]]; then
                echo
                "${SCRIPT_DIR}/backup-google-drive.sh" list
            fi
            ;;
            
        "help"|"-h"|"--help")
            echo "Automated Backup Pipeline"
            echo ""
            echo "Usage: $0 [command] [options]"
            echo ""
            echo "Commands:"
            echo "  daily                    - Run daily backup routine"
            echo "  weekly                   - Run weekly backup routine"
            echo "  manual [db] [type]       - Manual backup (default: naga_local, both)"
            echo "  health                   - System health check"
            echo "  status                   - Show backup system status"
            echo "  setup-cron               - Install automated cron jobs"
            echo "  help                     - Show this help message"
            echo ""
            echo "Automation:"
            echo "  Add to crontab for automated backups:"
            echo "    0 2 * * * $0 daily     # Daily at 2 AM"
            echo "    0 3 * * 0 $0 weekly    # Weekly on Sunday at 3 AM"
            ;;
            
        *)
            echo "Unknown command: ${command}"
            echo "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"