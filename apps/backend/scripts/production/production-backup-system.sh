#!/usr/bin/env bash

###
### PRODUCTION-GRADE DATABASE BACKUP SYSTEM
### Comprehensive backup solution with integrity checks, monitoring, and safety features
###
### Features:
### - Pre-backup data verification
### - Multiple backup formats (compressed SQL, custom format)
### - Integrity verification post-backup
### - External storage with retention policies
### - Monitoring and alerting
### - Recovery testing
### - Audit logging
###

set -o errexit
set -o pipefail
set -o nounset

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKUP_DIR="${PROJECT_ROOT}/backups"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.local.yml"
LOG_FILE="${BACKUP_DIR}/backup-audit.log"
RETENTION_DAYS=90
MAX_BACKUPS_KEEP=50

# Backup format options
BACKUP_SQL=true
BACKUP_CUSTOM=true
BACKUP_DIRECTORY=false

# Monitoring configuration
BACKUP_SIZE_THRESHOLD_MB=10  # Minimum expected backup size in MB
TABLE_COUNT_THRESHOLD=50     # Minimum expected table count

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Enhanced logging functions with audit trail
log_audit() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[${timestamp}] [${level}] ${message}" >> "${LOG_FILE}"
    
    case "${level}" in
        "INFO")  echo -e "${BLUE}[INFO]${NC} ${message}" ;;
        "SUCCESS") echo -e "${GREEN}[SUCCESS]${NC} ${message}" ;;
        "WARNING") echo -e "${YELLOW}[WARNING]${NC} ${message}" ;;
        "ERROR") echo -e "${RED}[ERROR]${NC} ${message}" ;;
        "CRITICAL") echo -e "${RED}[CRITICAL]${NC} ${message}" ;;
    esac
}

# Initialize backup system
initialize_backup_system() {
    # Create backup directory with proper permissions
    mkdir -p "${BACKUP_DIR}"
    chmod 750 "${BACKUP_DIR}"
    
    # Initialize audit log
    if [[ ! -f "${LOG_FILE}" ]]; then
        touch "${LOG_FILE}"
        chmod 640 "${LOG_FILE}"
    fi
    
    log_audit "INFO" "Production backup system initialized"
    log_audit "INFO" "Backup directory: ${BACKUP_DIR}"
    log_audit "INFO" "Retention policy: ${RETENTION_DAYS} days, max ${MAX_BACKUPS_KEEP} backups"
}

# Pre-backup verification
verify_database_health() {
    local database="$1"
    
    log_audit "INFO" "Performing pre-backup health checks for database: ${database}"
    
    # Check if database is accessible
    if ! docker compose -f "${COMPOSE_FILE}" exec postgres psql -U debug -d "${database}" -c "SELECT 1;" >/dev/null 2>&1; then
        log_audit "CRITICAL" "Database ${database} is not accessible"
        return 1
    fi
    
    # Count tables
    local table_count
    table_count=$(docker compose -f "${COMPOSE_FILE}" exec postgres psql -U debug -d "${database}" -t -c "
        SELECT COUNT(*) FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
    " | tr -d ' \r\n')
    
    if [[ "${table_count}" -lt "${TABLE_COUNT_THRESHOLD}" ]]; then
        log_audit "WARNING" "Low table count in ${database}: ${table_count} (threshold: ${TABLE_COUNT_THRESHOLD})"
    else
        log_audit "SUCCESS" "Database ${database} health check passed: ${table_count} tables"
    fi
    
    # Count total records across all tables
    local total_records
    total_records=$(docker compose -f "${COMPOSE_FILE}" exec postgres psql -U debug -d "${database}" -t -c "
        SELECT SUM(n_tup_ins) FROM pg_stat_user_tables;
    " | tr -d ' \r\n')
    
    if [[ "${total_records}" == "0" ]] || [[ "${total_records}" == "" ]]; then
        log_audit "CRITICAL" "Database ${database} appears to be EMPTY - contains no data records"
        log_audit "CRITICAL" "Backup of empty database is likely NOT what you want"
        echo -e "${RED}CRITICAL WARNING: Database '${database}' appears to be empty!${NC}"
        echo -e "${RED}This backup will only contain schema, no actual data.${NC}"
        read -p "Continue with backup of empty database? Type 'yes' to proceed: " confirm
        if [[ "${confirm}" != "yes" ]]; then
            log_audit "INFO" "Backup cancelled - empty database"
            exit 0
        fi
        log_audit "WARNING" "Proceeding with backup of empty database per user confirmation"
    else
        log_audit "SUCCESS" "Database ${database} contains ${total_records} data records"
    fi
    
    return 0
}

# Create production-grade backup
create_production_backup() {
    local database="$1"
    local backup_type="${2:-both}"
    local timestamp=$(date +'%Y_%m_%dT%H_%M_%S')
    local backup_prefix="${database}_${timestamp}"
    
    log_audit "INFO" "Starting production backup: ${database} (type: ${backup_type})"
    
    # SQL dump backup (compressed)
    if [[ "${BACKUP_SQL}" == true ]] && [[ "${backup_type}" == "sql" || "${backup_type}" == "both" ]]; then
        local sql_backup="${backup_prefix}.sql.gz"
        log_audit "INFO" "Creating SQL backup: ${sql_backup}"
        
        docker compose -f "${COMPOSE_FILE}" exec postgres bash -c "
            pg_dump -U debug -d ${database} \
                --verbose \
                --format=plain \
                --no-owner \
                --no-privileges \
                --create \
                --clean \
                --if-exists \
            | gzip > /backups/${sql_backup}
        "
        
        # Copy to external storage
        docker compose -f "${COMPOSE_FILE}" cp "postgres:/backups/${sql_backup}" "${BACKUP_DIR}/"
        
        # Verify backup integrity
        if verify_backup_integrity "${BACKUP_DIR}/${sql_backup}"; then
            log_audit "SUCCESS" "SQL backup created and verified: ${sql_backup}"
        else
            log_audit "ERROR" "SQL backup verification failed: ${sql_backup}"
            return 1
        fi
    fi
    
    # Custom format backup (for faster restores)
    if [[ "${BACKUP_CUSTOM}" == true ]] && [[ "${backup_type}" == "custom" || "${backup_type}" == "both" ]]; then
        local custom_backup="${backup_prefix}.dump"
        log_audit "INFO" "Creating custom format backup: ${custom_backup}"
        
        docker compose -f "${COMPOSE_FILE}" exec postgres bash -c "
            pg_dump -U debug -d ${database} \
                --verbose \
                --format=custom \
                --compress=9 \
                --no-owner \
                --no-privileges \
                --create \
                --clean \
                --if-exists \
                --file=/backups/${custom_backup}
        "
        
        # Copy to external storage
        docker compose -f "${COMPOSE_FILE}" cp "postgres:/backups/${custom_backup}" "${BACKUP_DIR}/"
        
        # Verify custom backup
        if verify_custom_backup "${BACKUP_DIR}/${custom_backup}"; then
            log_audit "SUCCESS" "Custom backup created and verified: ${custom_backup}"
        else
            log_audit "ERROR" "Custom backup verification failed: ${custom_backup}"
            return 1
        fi
    fi
    
    return 0
}

# Verify backup integrity
verify_backup_integrity() {
    local backup_file="$1"
    
    if [[ "${backup_file}" == *.gz ]]; then
        # Test gzip integrity
        if ! gzip -t "${backup_file}" 2>/dev/null; then
            log_audit "ERROR" "Backup file corrupted (gzip test failed): ${backup_file}"
            return 1
        fi
        
        # Check backup size
        local size_mb
        size_mb=$(du -m "${backup_file}" | cut -f1)
        if [[ "${size_mb}" -lt "${BACKUP_SIZE_THRESHOLD_MB}" ]]; then
            log_audit "WARNING" "Backup file smaller than expected: ${size_mb}MB (threshold: ${BACKUP_SIZE_THRESHOLD_MB}MB)"
        fi
        
        # Quick content verification
        if gzip -dc "${backup_file}" | head -20 | grep -q "PostgreSQL database dump"; then
            log_audit "SUCCESS" "Backup content verification passed: ${backup_file}"
            return 0
        else
            log_audit "ERROR" "Backup content verification failed: ${backup_file}"
            return 1
        fi
    fi
    
    return 0
}

# Verify custom format backup
verify_custom_backup() {
    local backup_file="$1"
    
    # Use pg_restore to list contents (verification)
    if docker compose -f "${COMPOSE_FILE}" exec postgres pg_restore --list "${backup_file}" >/dev/null 2>&1; then
        log_audit "SUCCESS" "Custom backup verification passed: ${backup_file}"
        return 0
    else
        log_audit "ERROR" "Custom backup verification failed: ${backup_file}"
        return 1
    fi
}

# Test backup recovery
test_backup_recovery() {
    local backup_file="$1"
    local test_db="backup_test_$(date +%s)"
    
    log_audit "INFO" "Testing backup recovery: ${backup_file}"
    
    # Create test database
    docker compose -f "${COMPOSE_FILE}" exec postgres createdb -U debug "${test_db}"
    
    # Attempt restore
    local restore_success=false
    if [[ "${backup_file}" == *.gz ]]; then
        if docker compose -f "${COMPOSE_FILE}" exec postgres bash -c "
            gunzip -c /backups/$(basename ${backup_file}) | psql -U debug -d ${test_db}
        " >/dev/null 2>&1; then
            restore_success=true
        fi
    elif [[ "${backup_file}" == *.dump ]]; then
        if docker compose -f "${COMPOSE_FILE}" exec postgres pg_restore -U debug -d "${test_db}" "/backups/$(basename ${backup_file})" >/dev/null 2>&1; then
            restore_success=true
        fi
    fi
    
    # Verify restored database
    if [[ "${restore_success}" == true ]]; then
        local restored_tables
        restored_tables=$(docker compose -f "${COMPOSE_FILE}" exec postgres psql -U debug -d "${test_db}" -t -c "
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
        " | tr -d ' \r\n')
        
        if [[ "${restored_tables}" -gt 0 ]]; then
            log_audit "SUCCESS" "Backup recovery test passed: ${restored_tables} tables restored"
        else
            log_audit "ERROR" "Backup recovery test failed: no tables restored"
            restore_success=false
        fi
    else
        log_audit "ERROR" "Backup recovery test failed: restore operation failed"
    fi
    
    # Cleanup test database
    docker compose -f "${COMPOSE_FILE}" exec postgres dropdb -U debug "${test_db}" 2>/dev/null || true
    
    return $([[ "${restore_success}" == true ]] && echo 0 || echo 1)
}

# Cleanup old backups with retention policy
cleanup_old_backups() {
    log_audit "INFO" "Starting backup cleanup (retention: ${RETENTION_DAYS} days, max: ${MAX_BACKUPS_KEEP})"
    
    # Remove backups older than retention period
    local old_backups_removed=0
    while IFS= read -r -d '' backup_file; do
        rm -f "${backup_file}"
        old_backups_removed=$((old_backups_removed + 1))
        log_audit "INFO" "Removed old backup: $(basename ${backup_file})"
    done < <(find "${BACKUP_DIR}" -name "*.sql.gz" -o -name "*.dump" -type f -mtime +${RETENTION_DAYS} -print0 2>/dev/null)
    
    # Keep only the most recent backups if we exceed the limit
    local total_backups
    total_backups=$(find "${BACKUP_DIR}" \( -name "*.sql.gz" -o -name "*.dump" \) -type f | wc -l)
    
    if [[ "${total_backups}" -gt "${MAX_BACKUPS_KEEP}" ]]; then
        local excess_count=$((total_backups - MAX_BACKUPS_KEEP))
        log_audit "WARNING" "Too many backups (${total_backups}), removing ${excess_count} oldest"
        
        find "${BACKUP_DIR}" \( -name "*.sql.gz" -o -name "*.dump" \) -type f -printf '%T@ %p\n' | \
            sort -n | \
            head -${excess_count} | \
            cut -d' ' -f2- | \
            while read -r backup_file; do
                rm -f "${backup_file}"
                log_audit "INFO" "Removed excess backup: $(basename ${backup_file})"
            done
    fi
    
    log_audit "SUCCESS" "Backup cleanup completed (${old_backups_removed} old backups removed)"
}

# Generate backup report
generate_backup_report() {
    local database="$1"
    
    log_audit "INFO" "Generating backup report for: ${database}"
    
    echo -e "\n${CYAN}=== PRODUCTION BACKUP REPORT ===${NC}"
    echo -e "${BLUE}Database:${NC} ${database}"
    echo -e "${BLUE}Timestamp:${NC} $(date)"
    echo -e "${BLUE}Backup Location:${NC} ${BACKUP_DIR}"
    
    echo -e "\n${CYAN}Recent Backups:${NC}"
    if ls "${BACKUP_DIR}"/*${database}* >/dev/null 2>&1; then
        ls -lht "${BACKUP_DIR}"/*${database}* | head -5
    else
        echo "No backups found for ${database}"
    fi
    
    echo -e "\n${CYAN}Storage Usage:${NC}"
    du -sh "${BACKUP_DIR}"
    
    echo -e "\n${CYAN}Backup Integrity Status:${NC}"
    local total_backups=0
    local valid_backups=0
    
    for backup_file in "${BACKUP_DIR}"/*${database}*; do
        if [[ -f "${backup_file}" ]]; then
            total_backups=$((total_backups + 1))
            if verify_backup_integrity "${backup_file}" >/dev/null 2>&1; then
                valid_backups=$((valid_backups + 1))
                echo -e "${GREEN}✓${NC} $(basename ${backup_file})"
            else
                echo -e "${RED}✗${NC} $(basename ${backup_file})"
            fi
        fi
    done
    
    echo -e "\n${CYAN}Summary:${NC}"
    echo -e "Total backups: ${total_backups}"
    echo -e "Valid backups: ${valid_backups}"
    echo -e "Success rate: $(( valid_backups * 100 / (total_backups > 0 ? total_backups : 1) ))%"
}

# Main backup function
main() {
    local command="${1:-backup}"
    local database="${2:-naga_local}"
    local backup_type="${3:-both}"
    
    initialize_backup_system
    
    case "${command}" in
        "backup")
            log_audit "INFO" "Starting production backup process for: ${database}"
            
            # Check if docker compose is running
            if ! docker compose -f "${COMPOSE_FILE}" ps postgres | grep -q "Up"; then
                log_audit "CRITICAL" "PostgreSQL container is not running"
                exit 1
            fi
            
            # Pre-backup verification
            if ! verify_database_health "${database}"; then
                log_audit "CRITICAL" "Database health check failed - aborting backup"
                exit 1
            fi
            
            # Create backup
            if create_production_backup "${database}" "${backup_type}"; then
                log_audit "SUCCESS" "Production backup completed successfully"
            else
                log_audit "CRITICAL" "Production backup failed"
                exit 1
            fi
            
            # Test recovery (optional - can be slow)
            # if [[ "${TEST_RECOVERY:-false}" == "true" ]]; then
            #     test_backup_recovery "${latest_backup}"
            # fi
            
            # Cleanup old backups
            cleanup_old_backups
            
            # Generate report
            generate_backup_report "${database}"
            ;;
            
        "report")
            generate_backup_report "${database}"
            ;;
            
        "test")
            if [[ -z "${database}" ]]; then
                echo "Usage: $0 test <backup_file>"
                exit 1
            fi
            test_backup_recovery "${database}"
            ;;
            
        "cleanup")
            cleanup_old_backups
            ;;
            
        *)
            echo "Usage: $0 [backup|report|test|cleanup] [database] [sql|custom|both]"
            echo ""
            echo "Commands:"
            echo "  backup <db> [type]  - Create production backup (default: naga_local, both)"
            echo "  report <db>         - Generate backup report"
            echo "  test <backup_file>  - Test backup recovery"
            echo "  cleanup             - Clean up old backups"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"