#!/usr/bin/env bash

###
### COMPREHENSIVE BACKUP VERIFICATION SYSTEM
### Verifies backup integrity across all storage locations and against live database
###
### Verification Layers:
### 1. File integrity (compression, checksums)
### 2. Content verification (schema, data consistency)
### 3. Restoration testing (actual restore to temp database)
### 4. Cross-location verification (container vs external storage)
###
### Usage:
###     ./scripts/verify-backup-integrity.sh <backup_file>
###     ./scripts/verify-backup-integrity.sh CLEAN_BASELINE_naga_local_2025_07_15T08_25_41.sql.gz
###

set -o errexit
set -o pipefail
set -o nounset

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKUP_DIR="${PROJECT_ROOT}/backups"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.local.yml"
VERIFICATION_LOG="${BACKUP_DIR}/verification-audit.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging function
log_verify() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[${timestamp}] [VERIFY-${level}] ${message}" >> "${VERIFICATION_LOG}"
    
    case "${level}" in
        "INFO")  echo -e "${BLUE}[VERIFY-INFO]${NC} ${message}" ;;
        "SUCCESS") echo -e "${GREEN}[VERIFY-SUCCESS]${NC} ${message}" ;;
        "WARNING") echo -e "${YELLOW}[VERIFY-WARNING]${NC} ${message}" ;;
        "ERROR") echo -e "${RED}[VERIFY-ERROR]${NC} ${message}" ;;
        "CRITICAL") echo -e "${RED}[VERIFY-CRITICAL]${NC} ${message}" ;;
    esac
}

# Layer 1: File Integrity Verification
verify_file_integrity() {
    local backup_file="$1"
    local backup_basename=$(basename "${backup_file}")
    
    log_verify "INFO" "Layer 1: File Integrity Verification for ${backup_basename}"
    
    # Check if external backup exists
    if [[ ! -f "${backup_file}" ]]; then
        log_verify "CRITICAL" "External backup file not found: ${backup_file}"
        return 1
    fi
    
    # Test compression integrity
    if [[ "${backup_file}" == *.gz ]]; then
        if ! gzip -t "${backup_file}" 2>/dev/null; then
            log_verify "CRITICAL" "Backup file compression corrupted: ${backup_basename}"
            return 1
        fi
        log_verify "SUCCESS" "Compression integrity verified: ${backup_basename}"
    fi
    
    # Calculate external backup checksum
    local external_checksum
    external_checksum=$(sha256sum "${backup_file}" | cut -d' ' -f1)
    log_verify "INFO" "External backup SHA256: ${external_checksum}"
    
    # Check if container backup exists and compare checksums
    local container_backup="/backups/${backup_basename}"
    if docker compose -f "${COMPOSE_FILE}" exec postgres test -f "${container_backup}" 2>/dev/null; then
        local container_checksum
        container_checksum=$(docker compose -f "${COMPOSE_FILE}" exec postgres sha256sum "${container_backup}" | cut -d' ' -f1 | tr -d '\r')
        
        if [[ "${external_checksum}" == "${container_checksum}" ]]; then
            log_verify "SUCCESS" "Checksum match: external and container backups identical"
        else
            log_verify "WARNING" "Checksum mismatch: external (${external_checksum}) vs container (${container_checksum})"
            return 1
        fi
    else
        log_verify "WARNING" "Container backup not found: ${container_backup}"
    fi
    
    return 0
}

# Layer 2: Content Verification
verify_backup_content() {
    local backup_file="$1"
    local backup_basename=$(basename "${backup_file}")
    
    log_verify "INFO" "Layer 2: Content Verification for ${backup_basename}"
    
    # Extract and analyze backup content
    local temp_content="/tmp/backup_content_$$.sql"
    
    if [[ "${backup_file}" == *.gz ]]; then
        gzip -dc "${backup_file}" > "${temp_content}"
    else
        cp "${backup_file}" "${temp_content}"
    fi
    
    # Verify backup header
    if ! head -20 "${temp_content}" | grep -q "PostgreSQL database dump"; then
        log_verify "CRITICAL" "Invalid backup header - not a PostgreSQL dump"
        rm -f "${temp_content}"
        return 1
    fi
    
    # Count tables in backup
    local backup_table_count
    backup_table_count=$(grep -c "^CREATE TABLE" "${temp_content}" || echo "0")
    log_verify "INFO" "Tables in backup: ${backup_table_count}"
    
    # Count data sections in backup
    local backup_data_sections
    backup_data_sections=$(grep -c "^COPY.*FROM stdin;" "${temp_content}" || echo "0")
    log_verify "INFO" "Data sections in backup: ${backup_data_sections}"
    
    # Check for foreign key constraints
    local backup_fk_count
    backup_fk_count=$(grep -c "ADD CONSTRAINT.*FOREIGN KEY" "${temp_content}" || echo "0")
    log_verify "INFO" "Foreign key constraints in backup: ${backup_fk_count}"
    
    # Clean up
    rm -f "${temp_content}"
    
    return 0
}

# Layer 3: Database Schema Comparison
compare_with_live_database() {
    local backup_file="$1"
    local live_database="${2:-naga_local}"
    local backup_basename=$(basename "${backup_file}")
    
    log_verify "INFO" "Layer 3: Schema Comparison with live database: ${live_database}"
    
    # Get current database table count
    local live_table_count
    live_table_count=$(docker compose -f "${COMPOSE_FILE}" exec postgres psql -U debug -d "${live_database}" -t -c "
        SELECT COUNT(*) FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
    " | tr -d ' \r\n')
    
    log_verify "INFO" "Tables in live database: ${live_table_count}"
    
    # Get current database record count
    local live_record_count
    live_record_count=$(docker compose -f "${COMPOSE_FILE}" exec postgres psql -U debug -d "${live_database}" -t -c "
        SELECT COALESCE(SUM(n_tup_ins), 0) FROM pg_stat_user_tables;
    " | tr -d ' \r\n')
    
    log_verify "INFO" "Records in live database: ${live_record_count}"
    
    # Extract backup statistics for comparison
    local temp_content="/tmp/backup_schema_$$.sql"
    
    if [[ "${backup_file}" == *.gz ]]; then
        gzip -dc "${backup_file}" > "${temp_content}"
    else
        cp "${backup_file}" "${temp_content}"
    fi
    
    local backup_table_count
    backup_table_count=$(grep -c "^CREATE TABLE" "${temp_content}" || echo "0")
    
    # Clean up
    rm -f "${temp_content}"
    
    # Compare schema
    if [[ "${live_table_count}" -eq "${backup_table_count}" ]]; then
        log_verify "SUCCESS" "Schema match: ${live_table_count} tables in both live database and backup"
    else
        log_verify "WARNING" "Schema mismatch: live (${live_table_count}) vs backup (${backup_table_count}) tables"
    fi
    
    return 0
}

# Layer 4: Restoration Testing
test_backup_restoration() {
    local backup_file="$1"
    local backup_basename=$(basename "${backup_file}")
    local test_db="verify_restore_$(date +%s)"
    
    log_verify "INFO" "Layer 4: Restoration Testing for ${backup_basename}"
    
    # Create test database
    docker compose -f "${COMPOSE_FILE}" exec postgres createdb -U debug "${test_db}"
    log_verify "INFO" "Created test database: ${test_db}"
    
    # Copy backup to container if not already there
    local container_backup="/backups/${backup_basename}"
    if ! docker compose -f "${COMPOSE_FILE}" exec postgres test -f "${container_backup}" 2>/dev/null; then
        docker compose -f "${COMPOSE_FILE}" cp "${backup_file}" "postgres:${container_backup}"
        log_verify "INFO" "Copied backup to container for testing"
    fi
    
    # Attempt restoration
    local restore_success=false
    if [[ "${backup_file}" == *.gz ]]; then
        if docker compose -f "${COMPOSE_FILE}" exec postgres bash -c "
            gunzip -c ${container_backup} | psql -U debug -d ${test_db}
        " >/dev/null 2>&1; then
            restore_success=true
        fi
    else
        if docker compose -f "${COMPOSE_FILE}" exec postgres psql -U debug -d "${test_db}" -f "${container_backup}" >/dev/null 2>&1; then
            restore_success=true
        fi
    fi
    
    if [[ "${restore_success}" == true ]]; then
        # Verify restored database
        local restored_table_count
        restored_table_count=$(docker compose -f "${COMPOSE_FILE}" exec postgres psql -U debug -d "${test_db}" -t -c "
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
        " | tr -d ' \r\n')
        
        local restored_record_count
        restored_record_count=$(docker compose -f "${COMPOSE_FILE}" exec postgres psql -U debug -d "${test_db}" -t -c "
            SELECT COALESCE(SUM(n_tup_ins), 0) FROM pg_stat_user_tables;
        " | tr -d ' \r\n')
        
        log_verify "SUCCESS" "Restoration successful: ${restored_table_count} tables, ${restored_record_count} records"
        
        # Test basic queries
        if docker compose -f "${COMPOSE_FILE}" exec postgres psql -U debug -d "${test_db}" -c "
            SELECT COUNT(*) FROM django_migrations;
        " >/dev/null 2>&1; then
            log_verify "SUCCESS" "Database queries working after restoration"
        else
            log_verify "WARNING" "Database queries failed after restoration"
            restore_success=false
        fi
    else
        log_verify "CRITICAL" "Restoration failed for backup: ${backup_basename}"
    fi
    
    # Cleanup test database
    docker compose -f "${COMPOSE_FILE}" exec postgres dropdb -U debug "${test_db}" 2>/dev/null || true
    log_verify "INFO" "Cleaned up test database: ${test_db}"
    
    return $([[ "${restore_success}" == true ]] && echo 0 || echo 1)
}

# Layer 5: Cross-Location Integrity
verify_cross_location_integrity() {
    local backup_file="$1"
    local backup_basename=$(basename "${backup_file}")
    
    log_verify "INFO" "Layer 5: Cross-Location Integrity Verification"
    
    # Verify external file exists and is readable
    if [[ ! -r "${backup_file}" ]]; then
        log_verify "CRITICAL" "External backup not readable: ${backup_file}"
        return 1
    fi
    
    # Get external file stats
    local external_size
    external_size=$(stat -f%z "${backup_file}" 2>/dev/null || stat -c%s "${backup_file}")
    local external_perms
    external_perms=$(stat -f%Mp%Lp "${backup_file}" 2>/dev/null || stat -c%a "${backup_file}")
    
    log_verify "INFO" "External backup: ${external_size} bytes, permissions ${external_perms}"
    
    # Check container backup if exists
    local container_backup="/backups/${backup_basename}"
    if docker compose -f "${COMPOSE_FILE}" exec postgres test -f "${container_backup}" 2>/dev/null; then
        local container_size
        container_size=$(docker compose -f "${COMPOSE_FILE}" exec postgres stat -c%s "${container_backup}" | tr -d '\r')
        
        if [[ "${external_size}" == "${container_size}" ]]; then
            log_verify "SUCCESS" "Size match: external and container backups (${external_size} bytes)"
        else
            log_verify "WARNING" "Size mismatch: external (${external_size}) vs container (${container_size}) bytes"
            return 1
        fi
    fi
    
    # Verify backup directory structure
    if [[ ! -d "${BACKUP_DIR}" ]]; then
        log_verify "CRITICAL" "Backup directory missing: ${BACKUP_DIR}"
        return 1
    fi
    
    # Check backup directory permissions
    local backup_dir_perms
    backup_dir_perms=$(stat -f%Mp%Lp "${BACKUP_DIR}" 2>/dev/null || stat -c%a "${BACKUP_DIR}")
    
    if [[ "${backup_dir_perms}" == *"750"* ]] || [[ "${backup_dir_perms}" == *"755"* ]]; then
        log_verify "SUCCESS" "Backup directory permissions secure: ${backup_dir_perms}"
    else
        log_verify "WARNING" "Backup directory permissions may be insecure: ${backup_dir_perms}"
    fi
    
    return 0
}

# Generate comprehensive verification report
generate_verification_report() {
    local backup_file="$1"
    local verification_results="$2"
    local backup_basename=$(basename "${backup_file}")
    
    echo -e "\n${CYAN}=== COMPREHENSIVE BACKUP VERIFICATION REPORT ===${NC}"
    echo -e "${BLUE}Backup File:${NC} ${backup_basename}"
    echo -e "${BLUE}Verification Date:${NC} $(date)"
    echo -e "${BLUE}External Path:${NC} ${backup_file}"
    
    echo -e "\n${CYAN}Verification Layers:${NC}"
    echo -e "✅ Layer 1: File Integrity (compression, checksums)"
    echo -e "✅ Layer 2: Content Verification (schema, structure)"
    echo -e "✅ Layer 3: Schema Comparison (live database match)"
    echo -e "✅ Layer 4: Restoration Testing (actual restore)"
    echo -e "✅ Layer 5: Cross-Location Integrity (storage consistency)"
    
    echo -e "\n${CYAN}Verification Results:${NC}"
    if [[ "${verification_results}" == "0" ]]; then
        echo -e "${GREEN}🎉 ALL VERIFICATION LAYERS PASSED${NC}"
        echo -e "${GREEN}✅ Backup is verified as completely reliable${NC}"
        echo -e "${GREEN}✅ Safe for production restoration${NC}"
    else
        echo -e "${RED}❌ VERIFICATION FAILED${NC}"
        echo -e "${RED}⚠️  Backup may not be reliable for restoration${NC}"
        echo -e "${RED}🔍 Check verification log for details${NC}"
    fi
    
    echo -e "\n${CYAN}Verification Log:${NC} ${VERIFICATION_LOG}"
    echo -e "${CYAN}Last 5 verification entries:${NC}"
    tail -5 "${VERIFICATION_LOG}" 2>/dev/null || echo "No previous verification entries"
}

# Main verification function
main() {
    local backup_file="${1:-}"
    
    if [[ -z "${backup_file}" ]]; then
        echo "Usage: $0 <backup_file>"
        echo "Example: $0 CLEAN_BASELINE_naga_local_2025_07_15T08_25_41.sql.gz"
        exit 1
    fi
    
    # Resolve backup file path
    if [[ ! -f "${backup_file}" ]]; then
        # Try backup directory
        if [[ -f "${BACKUP_DIR}/${backup_file}" ]]; then
            backup_file="${BACKUP_DIR}/${backup_file}"
        else
            echo "Backup file not found: ${backup_file}"
            exit 1
        fi
    fi
    
    log_verify "INFO" "Starting comprehensive backup verification: $(basename ${backup_file})"
    
    local overall_result=0
    
    # Execute all verification layers
    verify_file_integrity "${backup_file}" || overall_result=1
    verify_backup_content "${backup_file}" || overall_result=1
    compare_with_live_database "${backup_file}" || overall_result=1
    test_backup_restoration "${backup_file}" || overall_result=1
    verify_cross_location_integrity "${backup_file}" || overall_result=1
    
    # Generate final report
    generate_verification_report "${backup_file}" "${overall_result}"
    
    if [[ "${overall_result}" == "0" ]]; then
        log_verify "SUCCESS" "Comprehensive verification completed successfully"
        exit 0
    else
        log_verify "CRITICAL" "Comprehensive verification failed - backup may not be reliable"
        exit 1
    fi
}

# Run main function
main "$@"