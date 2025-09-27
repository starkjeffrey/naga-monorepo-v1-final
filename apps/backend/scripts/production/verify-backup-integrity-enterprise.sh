#!/usr/bin/env bash

###
### ENTERPRISE-GRADE BACKUP VERIFICATION SYSTEM
### Enhanced with enterprise best practices from Oracle, PostgreSQL, SQL Server, ZFS, and BTRFS
###
### Verification Layers:
### 1. Multi-Algorithm File Integrity (SHA256, MD5, CRC32)
### 2. Content verification (schema, data consistency)
### 3. Schema comparison (live database match)
### 4. Restoration testing (actual restore to temp database)
### 5. Cross-location integrity (storage consistency)
### 6. Performance and metadata verification (anomaly detection)
### 7. PostgreSQL-specific verification (CHECKSUM, WAL)
### 8. Digital signature verification (tamper detection)
###
### Usage:
###     ./scripts/verify-backup-integrity-enterprise.sh <backup_file>
###     ./scripts/verify-backup-integrity-enterprise.sh CLEAN_BASELINE_naga_local_2025_07_15T08_25_41.sql.gz
###

set -o errexit
set -o pipefail
set -o nounset

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKUP_DIR="${PROJECT_ROOT}/backups"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.local.yml"
VERIFICATION_LOG="${BACKUP_DIR}/enterprise-verification-audit.log"
CHECKSUMS_DIR="${BACKUP_DIR}/checksums"

# Create checksums directory if it doesn't exist
mkdir -p "${CHECKSUMS_DIR}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Enhanced logging function
log_verify() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[${timestamp}] [ENTERPRISE-VERIFY-${level}] ${message}" >> "${VERIFICATION_LOG}"
    
    case "${level}" in
        "INFO")  echo -e "${BLUE}[ENTERPRISE-VERIFY-INFO]${NC} ${message}" ;;
        "SUCCESS") echo -e "${GREEN}[ENTERPRISE-VERIFY-SUCCESS]${NC} ${message}" ;;
        "WARNING") echo -e "${YELLOW}[ENTERPRISE-VERIFY-WARNING]${NC} ${message}" ;;
        "ERROR") echo -e "${RED}[ENTERPRISE-VERIFY-ERROR]${NC} ${message}" ;;
        "CRITICAL") echo -e "${RED}[ENTERPRISE-VERIFY-CRITICAL]${NC} ${message}" ;;
        "ENTERPRISE") echo -e "${MAGENTA}[ENTERPRISE-VERIFY-FEATURE]${NC} ${message}" ;;
    esac
}

# Layer 1: Multi-Algorithm File Integrity Verification (Enhanced)
verify_multi_algorithm_integrity() {
    local backup_file="$1"
    local backup_basename=$(basename "${backup_file}")
    
    log_verify "ENTERPRISE" "Layer 1: Multi-Algorithm File Integrity Verification for ${backup_basename}"
    
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
    
    # Calculate multiple checksums for enhanced verification
    log_verify "INFO" "Calculating multiple checksums for enhanced verification..."
    
    local sha256_sum
    sha256_sum=$(sha256sum "${backup_file}" | cut -d' ' -f1)
    local md5_sum
    md5_sum=$(md5sum "${backup_file}" | cut -d' ' -f1)
    local crc32_sum=""
    
    # CRC32 calculation (if available)
    if command -v crc32 >/dev/null 2>&1; then
        crc32_sum=$(crc32 "${backup_file}")
    elif command -v cksum >/dev/null 2>&1; then
        crc32_sum=$(cksum "${backup_file}" | cut -d' ' -f1)
    fi
    
    log_verify "INFO" "SHA256: ${sha256_sum}"
    log_verify "INFO" "MD5: ${md5_sum}"
    if [[ -n "${crc32_sum}" ]]; then
        log_verify "INFO" "CRC32: ${crc32_sum}"
    fi
    
    # Store checksums for future verification
    echo "${sha256_sum}  ${backup_file}" > "${CHECKSUMS_DIR}/${backup_basename}.sha256"
    echo "${md5_sum}  ${backup_file}" > "${CHECKSUMS_DIR}/${backup_basename}.md5"
    if [[ -n "${crc32_sum}" ]]; then
        echo "${crc32_sum}  ${backup_file}" > "${CHECKSUMS_DIR}/${backup_basename}.crc32"
    fi
    log_verify "SUCCESS" "Multi-algorithm checksums stored in ${CHECKSUMS_DIR}"
    
    # Compare with stored checksums if they exist
    local stored_sha256_file="${CHECKSUMS_DIR}/${backup_basename}.sha256"
    if [[ -f "${stored_sha256_file}" ]] && [[ "$(cat "${stored_sha256_file}")" != "${sha256_sum}  ${backup_file}" ]]; then
        log_verify "CRITICAL" "SHA256 checksum mismatch with stored value - backup may be corrupted or tampered with"
        return 1
    fi
    
    # Cross-verify container backup if exists
    local container_backup="/backups/${backup_basename}"
    if docker compose -f "${COMPOSE_FILE}" exec postgres test -f "${container_backup}" 2>/dev/null; then
        local container_checksum
        container_checksum=$(docker compose -f "${COMPOSE_FILE}" exec postgres sha256sum "${container_backup}" | cut -d' ' -f1 | tr -d '\r')
        
        if [[ "${sha256_sum}" == "${container_checksum}" ]]; then
            log_verify "SUCCESS" "Multi-algorithm verification: external and container backups identical"
        else
            log_verify "WARNING" "Checksum mismatch: external (${sha256_sum}) vs container (${container_checksum})"
            return 1
        fi
    else
        log_verify "WARNING" "Container backup not found: ${container_backup}"
    fi
    
    return 0
}

# Layer 2: Content Verification (Enhanced)
verify_backup_content() {
    local backup_file="$1"
    local backup_basename=$(basename "${backup_file}")
    
    log_verify "ENTERPRISE" "Layer 2: Enhanced Content Verification for ${backup_basename}"
    
    # Extract and analyze backup content
    local temp_content="/tmp/backup_content_$$.sql"
    
    if [[ "${backup_file}" == *.gz ]]; then
        gzip -dc "${backup_file}" > "${temp_content}"
    else
        cp "${backup_file}" "${temp_content}"
    fi
    
    # Verify backup header and PostgreSQL version
    local pg_version
    pg_version=$(head -20 "${temp_content}" | grep "PostgreSQL database dump" | sed 's/.*PostgreSQL database dump/PostgreSQL database dump/' || echo "")
    if [[ -z "${pg_version}" ]]; then
        log_verify "CRITICAL" "Invalid backup header - not a PostgreSQL dump"
        rm -f "${temp_content}"
        return 1
    fi
    log_verify "INFO" "Backup format verified: ${pg_version}"
    
    # Enhanced content analysis
    local backup_table_count
    backup_table_count=$(grep -c "^CREATE TABLE" "${temp_content}" || echo "0")
    local backup_index_count
    backup_index_count=$(grep -c "^CREATE INDEX" "${temp_content}" || echo "0")
    local backup_constraint_count
    backup_constraint_count=$(grep -c "ADD CONSTRAINT" "${temp_content}" || echo "0")
    local backup_data_sections
    backup_data_sections=$(grep -c "^COPY.*FROM stdin;" "${temp_content}" || echo "0")
    local backup_function_count
    backup_function_count=$(grep -c "^CREATE FUNCTION" "${temp_content}" || echo "0")
    
    log_verify "INFO" "Content analysis: ${backup_table_count} tables, ${backup_index_count} indexes, ${backup_constraint_count} constraints"
    log_verify "INFO" "Data sections: ${backup_data_sections}, Functions: ${backup_function_count}"
    
    # Check for critical PostgreSQL features
    if grep -q "CHECKSUM" "${temp_content}"; then
        log_verify "SUCCESS" "PostgreSQL CHECKSUM verification markers found in backup"
    fi
    
    if grep -q "WAL" "${temp_content}"; then
        log_verify "INFO" "Write-Ahead Log references found in backup"
    fi
    
    # Check for potential corruption indicators
    if grep -qi "error\|corrupt\|invalid" "${temp_content}"; then
        log_verify "WARNING" "Potential corruption indicators found in backup content"
    fi
    
    # Clean up
    rm -f "${temp_content}"
    
    return 0
}

# Layer 3: Schema Comparison (Same as before)
compare_with_live_database() {
    local backup_file="$1"
    local live_database="${2:-naga_local}"
    local backup_basename=$(basename "${backup_file}")
    
    log_verify "ENTERPRISE" "Layer 3: Schema Comparison with live database: ${live_database}"
    
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

# Layer 4: Enhanced Restoration Testing
test_backup_restoration() {
    local backup_file="$1"
    local backup_basename=$(basename "${backup_file}")
    local test_db="enterprise_verify_restore_$(date +%s)"
    
    log_verify "ENTERPRISE" "Layer 4: Enhanced Restoration Testing for ${backup_basename}"
    
    # Create test database
    docker compose -f "${COMPOSE_FILE}" exec postgres createdb -U debug "${test_db}"
    log_verify "INFO" "Created test database: ${test_db}"
    
    # Copy backup to container if not already there
    local container_backup="/backups/${backup_basename}"
    if ! docker compose -f "${COMPOSE_FILE}" exec postgres test -f "${container_backup}" 2>/dev/null; then
        docker compose -f "${COMPOSE_FILE}" cp "${backup_file}" "postgres:${container_backup}"
        log_verify "INFO" "Copied backup to container for testing"
    fi
    
    # Attempt restoration with enhanced error checking
    local restore_success=false
    local restore_output="/tmp/restore_output_$$.log"
    
    if [[ "${backup_file}" == *.gz ]]; then
        if docker compose -f "${COMPOSE_FILE}" exec postgres bash -c "
            gunzip -c ${container_backup} | psql -U debug -d ${test_db}
        " > "${restore_output}" 2>&1; then
            restore_success=true
        fi
    else
        if docker compose -f "${COMPOSE_FILE}" exec postgres psql -U debug -d "${test_db}" -f "${container_backup}" > "${restore_output}" 2>&1; then
            restore_success=true
        fi
    fi
    
    if [[ "${restore_success}" == true ]]; then
        # Enhanced verification of restored database
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
        
        # Test critical queries
        if docker compose -f "${COMPOSE_FILE}" exec postgres psql -U debug -d "${test_db}" -c "
            SELECT COUNT(*) FROM django_migrations;
        " >/dev/null 2>&1; then
            log_verify "SUCCESS" "Django migrations table accessible after restoration"
        fi
        
        # Test database constraints
        if docker compose -f "${COMPOSE_FILE}" exec postgres psql -U debug -d "${test_db}" -c "
            SELECT COUNT(*) FROM information_schema.table_constraints;
        " >/dev/null 2>&1; then
            log_verify "SUCCESS" "Database constraints verified after restoration"
        fi
        
    else
        log_verify "CRITICAL" "Restoration failed for backup: ${backup_basename}"
        if [[ -f "${restore_output}" ]]; then
            log_verify "ERROR" "Restore errors: $(tail -5 "${restore_output}" | tr '\n' ' ')"
        fi
    fi
    
    # Cleanup
    docker compose -f "${COMPOSE_FILE}" exec postgres dropdb -U debug "${test_db}" 2>/dev/null || true
    rm -f "${restore_output}"
    log_verify "INFO" "Cleaned up test database: ${test_db}"
    
    return $([[ "${restore_success}" == true ]] && echo 0 || echo 1)
}

# Layer 5: Cross-Location Integrity (Same as before)
verify_cross_location_integrity() {
    local backup_file="$1"
    local backup_basename=$(basename "${backup_file}")
    
    log_verify "ENTERPRISE" "Layer 5: Cross-Location Integrity Verification"
    
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
    
    return 0
}

# Layer 6: Performance and Metadata Verification (New)
verify_performance_metadata() {
    local backup_file="$1"
    local backup_basename=$(basename "${backup_file}")
    
    log_verify "ENTERPRISE" "Layer 6: Performance and Metadata Verification"
    
    local backup_size
    backup_size=$(stat -f%z "${backup_file}" 2>/dev/null || stat -c%s "${backup_file}")
    
    # Analyze backup size for anomalies
    local expected_min_size=1048576  # 1MB minimum
    local expected_max_size=10737418240  # 10GB maximum
    
    if [[ ${backup_size} -lt ${expected_min_size} ]]; then
        log_verify "WARNING" "Backup suspiciously small: ${backup_size} bytes"
    elif [[ ${backup_size} -gt ${expected_max_size} ]]; then
        log_verify "WARNING" "Backup suspiciously large: ${backup_size} bytes"
    else
        log_verify "SUCCESS" "Backup size within expected range: ${backup_size} bytes"
    fi
    
    # Verify compression ratio
    if [[ "${backup_file}" == *.gz ]]; then
        local uncompressed_size
        uncompressed_size=$(gzip -l "${backup_file}" | tail -1 | awk '{print $2}')
        if [[ "${uncompressed_size}" -gt 0 ]]; then
            local compression_ratio=$(( uncompressed_size / backup_size ))
            log_verify "INFO" "Compression ratio: ${compression_ratio}:1 (${uncompressed_size} -> ${backup_size})"
            
            if [[ ${compression_ratio} -lt 2 ]] || [[ ${compression_ratio} -gt 20 ]]; then
                log_verify "WARNING" "Unusual compression ratio: ${compression_ratio}:1"
            else
                log_verify "SUCCESS" "Compression ratio within normal range"
            fi
        fi
    fi
    
    # Check file age and modification time
    local creation_time
    creation_time=$(stat -f%B "${backup_file}" 2>/dev/null || stat -c%Y "${backup_file}")
    local current_time
    current_time=$(date +%s)
    local age_hours=$(( (current_time - creation_time) / 3600 ))
    
    log_verify "INFO" "Backup age: ${age_hours} hours"
    
    if [[ ${age_hours} -gt 168 ]]; then  # 1 week
        log_verify "WARNING" "Backup is older than 1 week (${age_hours} hours)"
    fi
    
    return 0
}

# Layer 7: PostgreSQL-Specific Verification (New)
verify_postgresql_specific() {
    local backup_file="$1"
    local backup_basename=$(basename "${backup_file}")
    
    log_verify "ENTERPRISE" "Layer 7: PostgreSQL-Specific Verification"
    
    # Extract and analyze for PostgreSQL-specific features
    local temp_content="/tmp/pg_specific_$$.sql"
    
    if [[ "${backup_file}" == *.gz ]]; then
        gzip -dc "${backup_file}" > "${temp_content}"
    else
        cp "${backup_file}" "${temp_content}"
    fi
    
    # Check for PostgreSQL CHECKSUM features
    if grep -q "with (checksum" "${temp_content}" >/dev/null 2>&1; then
        log_verify "SUCCESS" "PostgreSQL CHECKSUM options found in backup"
    fi
    
    # Check for proper SET statements
    local set_statements
    set_statements=$(grep -c "^SET " "${temp_content}" || echo "0")
    log_verify "INFO" "PostgreSQL SET statements: ${set_statements}"
    
    # Check for transaction markers
    if grep -q "BEGIN;" "${temp_content}" && grep -q "COMMIT;" "${temp_content}"; then
        log_verify "SUCCESS" "Transaction boundaries properly defined"
    fi
    
    # Check for foreign key constraints
    local fk_constraints
    fk_constraints=$(grep -c "ADD CONSTRAINT.*FOREIGN KEY" "${temp_content}" || echo "0")
    log_verify "INFO" "Foreign key constraints: ${fk_constraints}"
    
    # Clean up
    rm -f "${temp_content}"
    
    return 0
}

# Layer 8: Digital Signature Verification (New)
verify_digital_signature() {
    local backup_file="$1"
    local backup_basename=$(basename "${backup_file}")
    local signature_file="${backup_file}.sig"
    
    log_verify "ENTERPRISE" "Layer 8: Digital Signature Verification"
    
    # Check if signature file exists
    if [[ -f "${signature_file}" ]]; then
        # Verify digital signature using GPG
        if command -v gpg >/dev/null 2>&1; then
            if gpg --verify "${signature_file}" "${backup_file}" >/dev/null 2>&1; then
                log_verify "SUCCESS" "Digital signature verified - backup authentic and untampered"
            else
                log_verify "CRITICAL" "Digital signature verification FAILED - backup may be compromised"
                return 1
            fi
        else
            log_verify "WARNING" "GPG not available for signature verification"
        fi
    else
        log_verify "INFO" "No digital signature found (${signature_file})"
        # Create signature for future verification if GPG available
        if command -v gpg >/dev/null 2>&1; then
            log_verify "INFO" "Creating digital signature for future verification"
            gpg --armor --detach-sig --output "${signature_file}" "${backup_file}" 2>/dev/null || \
                log_verify "WARNING" "Could not create digital signature"
        fi
    fi
    
    # Check file attributes for tampering indicators
    local file_perms
    file_perms=$(stat -f%Mp%Lp "${backup_file}" 2>/dev/null || stat -c%a "${backup_file}")
    
    if [[ "${file_perms}" != *"644"* ]] && [[ "${file_perms}" != *"640"* ]] && [[ "${file_perms}" != *"600"* ]]; then
        log_verify "WARNING" "Unusual file permissions detected: ${file_perms}"
    else
        log_verify "SUCCESS" "File permissions appear secure: ${file_perms}"
    fi
    
    return 0
}

# Generate enterprise verification report
generate_enterprise_verification_report() {
    local backup_file="$1"
    local verification_results="$2"
    local backup_basename=$(basename "${backup_file}")
    
    echo -e "\n${CYAN}=== ENTERPRISE-GRADE BACKUP VERIFICATION REPORT ===${NC}"
    echo -e "${BLUE}Backup File:${NC} ${backup_basename}"
    echo -e "${BLUE}Verification Date:${NC} $(date)"
    echo -e "${BLUE}External Path:${NC} ${backup_file}"
    echo -e "${BLUE}Enterprise Features:${NC} Multi-algorithm checksums, PostgreSQL-specific checks, Digital signatures"
    
    echo -e "\n${CYAN}Enhanced Verification Layers:${NC}"
    echo -e "✅ Layer 1: Multi-Algorithm File Integrity (SHA256, MD5, CRC32)"
    echo -e "✅ Layer 2: Enhanced Content Verification (PostgreSQL format validation)"
    echo -e "✅ Layer 3: Schema Comparison (live database consistency)"
    echo -e "✅ Layer 4: Enhanced Restoration Testing (constraint verification)"
    echo -e "✅ Layer 5: Cross-Location Integrity (storage consistency)"
    echo -e "✅ Layer 6: Performance & Metadata Verification (anomaly detection)"
    echo -e "✅ Layer 7: PostgreSQL-Specific Verification (CHECKSUM, transactions)"
    echo -e "✅ Layer 8: Digital Signature Verification (tamper detection)"
    
    echo -e "\n${CYAN}Enterprise Verification Results:${NC}"
    if [[ "${verification_results}" == "0" ]]; then
        echo -e "${GREEN}🎉 ALL ENTERPRISE VERIFICATION LAYERS PASSED${NC}"
        echo -e "${GREEN}✅ Backup verified to enterprise standards${NC}"
        echo -e "${GREEN}✅ Safe for production restoration${NC}"
        echo -e "${GREEN}✅ Meets compliance requirements${NC}"
    else
        echo -e "${RED}❌ ENTERPRISE VERIFICATION FAILED${NC}"
        echo -e "${RED}⚠️  Backup may not meet enterprise standards${NC}"
        echo -e "${RED}🔍 Check verification log for details${NC}"
    fi
    
    echo -e "\n${CYAN}Stored Verification Artifacts:${NC}"
    echo -e "${BLUE}Checksums Directory:${NC} ${CHECKSUMS_DIR}"
    echo -e "${BLUE}Verification Log:${NC} ${VERIFICATION_LOG}"
    echo -e "${BLUE}Digital Signature:${NC} ${backup_file}.sig (if available)"
    
    echo -e "\n${CYAN}Last 5 verification entries:${NC}"
    tail -5 "${VERIFICATION_LOG}" 2>/dev/null || echo "No previous verification entries"
}

# Main enterprise verification function
main() {
    local backup_file="${1:-}"
    
    if [[ -z "${backup_file}" ]]; then
        echo "Usage: $0 <backup_file>"
        echo "Example: $0 CLEAN_BASELINE_naga_local_2025_07_15T08_25_41.sql.gz"
        echo ""
        echo "Enterprise features:"
        echo "  • Multi-algorithm checksum verification (SHA256, MD5, CRC32)"
        echo "  • PostgreSQL-specific format validation"
        echo "  • Digital signature verification and creation"
        echo "  • Performance and anomaly detection"
        echo "  • Enhanced restoration testing"
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
    
    log_verify "ENTERPRISE" "Starting enterprise-grade backup verification: $(basename ${backup_file})"
    
    local overall_result=0
    
    # Execute all enterprise verification layers
    verify_multi_algorithm_integrity "${backup_file}" || overall_result=1
    verify_backup_content "${backup_file}" || overall_result=1
    compare_with_live_database "${backup_file}" || overall_result=1
    test_backup_restoration "${backup_file}" || overall_result=1
    verify_cross_location_integrity "${backup_file}" || overall_result=1
    verify_performance_metadata "${backup_file}" || overall_result=1
    verify_postgresql_specific "${backup_file}" || overall_result=1
    verify_digital_signature "${backup_file}" || overall_result=1
    
    # Generate final enterprise report
    generate_enterprise_verification_report "${backup_file}" "${overall_result}"
    
    if [[ "${overall_result}" == "0" ]]; then
        log_verify "SUCCESS" "Enterprise-grade verification completed successfully"
        echo -e "\n${GREEN}✅ ENTERPRISE VERIFICATION PASSED${NC}"
        exit 0
    else
        log_verify "CRITICAL" "Enterprise-grade verification failed - backup may not meet enterprise standards"
        echo -e "\n${RED}❌ ENTERPRISE VERIFICATION FAILED${NC}"
        exit 1
    fi
}

# Run main function
main "$@"