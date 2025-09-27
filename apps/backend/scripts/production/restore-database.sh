#!/usr/bin/env bash

###
### Production-Quality Database Restore Script
### Restores databases from backup files with safety checks
###
### Usage:
###     ./scripts/restore-database.sh <backup_filename> [target_db]
###     ./scripts/restore-database.sh backup_2025_07_15T00_40_16.sql.gz
###     ./scripts/restore-database.sh backup_2025_07_15T00_40_16.sql.gz naga_local
###

set -o errexit
set -o pipefail
set -o nounset

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BACKUP_DIR="${PROJECT_ROOT}/backups"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.local.yml"
CONTAINER_BACKUP_DIR="/backups"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if docker compose is running
check_services() {
    if ! docker compose -f "${COMPOSE_FILE}" ps postgres | grep -q "Up"; then
        log_error "PostgreSQL container is not running. Please start it first:"
        log_error "  docker compose -f docker-compose.local.yml up postgres -d"
        exit 1
    fi
}

# Verify backup file exists and is valid
verify_backup_file() {
    local backup_file="$1"
    local backup_path
    
    # Check if file exists in backup directory
    if [[ -f "${BACKUP_DIR}/${backup_file}" ]]; then
        backup_path="${BACKUP_DIR}/${backup_file}"
    elif [[ -f "${backup_file}" ]]; then
        backup_path="${backup_file}"
    else
        log_error "Backup file not found: ${backup_file}"
        log_error "Available backups:"
        ls -la "${BACKUP_DIR}"/*.sql.gz 2>/dev/null || echo "No backups found"
        exit 1
    fi
    
    # Verify file integrity
    if ! gzip -t "${backup_path}" 2>/dev/null; then
        log_error "Backup file is corrupted: ${backup_file}"
        exit 1
    fi
    
    log_success "Backup file verified: ${backup_path}"
    echo "${backup_path}"
}

# Create safety backup before restore
create_safety_backup() {
    local target_db="$1"
    local safety_backup_name="safety_backup_before_restore_$(date +'%Y_%m_%dT%H_%M_%S').sql.gz"
    
    log_warning "Creating safety backup of current database before restore..."
    
    # Create backup using container script
    docker compose -f "${COMPOSE_FILE}" exec postgres backup
    
    # Get the most recent backup (just created)
    local recent_backup
    recent_backup=$(docker compose -f "${COMPOSE_FILE}" exec postgres ls -t ${CONTAINER_BACKUP_DIR}/ | head -1 | tr -d '\r')
    
    # Copy to local storage with safety name
    docker compose -f "${COMPOSE_FILE}" cp "postgres:${CONTAINER_BACKUP_DIR}/${recent_backup}" "${BACKUP_DIR}/${safety_backup_name}"
    
    log_success "Safety backup created: ${safety_backup_name}"
    echo "${safety_backup_name}"
}

# Restore database from backup
restore_database() {
    local backup_file="$1"
    local target_db="${2:-naga_local}"
    local backup_path
    
    backup_path=$(verify_backup_file "${backup_file}")
    
    log_info "Restore configuration:"
    log_info "  Source backup: ${backup_file}"
    log_info "  Target database: ${target_db}"
    log_info "  Backup path: ${backup_path}"
    
    # Confirm with user
    read -p "Are you sure you want to restore? This will DESTROY all data in '${target_db}'. Type 'yes' to continue: " confirm
    if [[ "${confirm}" != "yes" ]]; then
        log_info "Restore cancelled by user"
        exit 0
    fi
    
    # Create safety backup
    local safety_backup
    safety_backup=$(create_safety_backup "${target_db}")
    
    # Copy backup file to container if not already there
    local container_backup_file
    container_backup_file=$(basename "${backup_path}")
    
    log_info "Copying backup file to container..."
    docker compose -f "${COMPOSE_FILE}" cp "${backup_path}" "postgres:${CONTAINER_BACKUP_DIR}/${container_backup_file}"
    
    # Drop and recreate database
    log_warning "Dropping and recreating database: ${target_db}"
    docker compose -f "${COMPOSE_FILE}" exec postgres psql -U debug -d postgres -c "DROP DATABASE IF EXISTS ${target_db};"
    docker compose -f "${COMPOSE_FILE}" exec postgres psql -U debug -d postgres -c "CREATE DATABASE ${target_db};"
    
    # Restore from backup
    log_info "Restoring database from backup..."
    docker compose -f "${COMPOSE_FILE}" exec postgres bash -c "
        gunzip -c ${CONTAINER_BACKUP_DIR}/${container_backup_file} | psql -U debug -d ${target_db}
    "
    
    # Verify restore
    local table_count
    table_count=$(docker compose -f "${COMPOSE_FILE}" exec postgres psql -U debug -d "${target_db}" -t -c "
        SELECT COUNT(*) FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
    " | tr -d ' \r\n')
    
    if [[ "${table_count}" -gt 0 ]]; then
        log_success "Database restore completed successfully!"
        log_success "Restored ${table_count} tables to database '${target_db}'"
        log_info "Safety backup available: ${safety_backup}"
    else
        log_error "Database restore may have failed - no tables found"
        log_warning "Safety backup available for recovery: ${safety_backup}"
        exit 1
    fi
}

# List available backups
list_backups() {
    log_info "Available backup files:"
    
    if [[ -d "${BACKUP_DIR}" ]] && [[ $(ls -1 "${BACKUP_DIR}"/*.sql.gz 2>/dev/null | wc -l) -gt 0 ]]; then
        ls -lht "${BACKUP_DIR}"/*.sql.gz
    else
        log_warning "No backup files found in ${BACKUP_DIR}"
    fi
}

# Show usage
show_usage() {
    echo "Usage: $0 <backup_filename> [target_database]"
    echo ""
    echo "Examples:"
    echo "  $0 backup_2025_07_15T00_40_16.sql.gz"
    echo "  $0 backup_2025_07_15T00_40_16.sql.gz naga_local"
    echo "  $0 list    # List available backups"
    echo ""
    echo "Target database defaults to 'naga_local' if not specified"
}

# Main function
main() {
    if [[ $# -eq 0 ]]; then
        show_usage
        exit 1
    fi
    
    case "$1" in
        "list")
            list_backups
            ;;
        "help"|"-h"|"--help")
            show_usage
            ;;
        *)
            local backup_file="$1"
            local target_db="${2:-naga_local}"
            
            log_info "Starting database restore process..."
            
            # Pre-flight checks
            check_services
            
            # Perform restore
            restore_database "${backup_file}" "${target_db}"
            ;;
    esac
}

# Run main function
main "$@"