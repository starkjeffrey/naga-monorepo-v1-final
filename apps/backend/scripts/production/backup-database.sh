#!/usr/bin/env bash

###
### Production-Quality Database Backup Script
### Creates backups of LOCAL and MIGRATION databases with external storage
###
### Usage:
###     ./scripts/backup-database.sh [local|migration|both]
###     ./scripts/backup-database.sh                    # defaults to both
###

set -o errexit
set -o pipefail
set -o nounset

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
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

# Ensure backup directory exists
ensure_backup_dir() {
    if [[ ! -d "${BACKUP_DIR}" ]]; then
        log_info "Creating backup directory: ${BACKUP_DIR}"
        mkdir -p "${BACKUP_DIR}"
    fi
}

# Check if docker compose is running
check_services() {
    if ! docker compose -f "${COMPOSE_FILE}" ps postgres | grep -q "Up"; then
        log_error "PostgreSQL container is not running. Please start it first:"
        log_error "  docker compose -f docker-compose.local.yml up postgres -d"
        exit 1
    fi
}

# Create backup in container
create_backup() {
    local backup_type="$1"
    local timestamp=$(date +'%Y_%m_%dT%H_%M_%S')
    
    log_info "Creating ${backup_type} database backup..."
    
    case "${backup_type}" in
        "local")
            docker compose -f "${COMPOSE_FILE}" exec postgres backup
            ;;
        "migration")
            docker compose -f "${COMPOSE_FILE}" exec postgres backup-dual migration
            ;;
        "both")
            docker compose -f "${COMPOSE_FILE}" exec postgres backup-dual both
            ;;
        *)
            log_error "Invalid backup type: ${backup_type}"
            exit 1
            ;;
    esac
}

# Copy backups to external storage
copy_backups_external() {
    log_info "Copying backups to external storage..."
    
    # Get list of backups in container
    local backup_files
    backup_files=$(docker compose -f "${COMPOSE_FILE}" exec postgres ls -t ${CONTAINER_BACKUP_DIR}/ | head -10)
    
    # Copy each backup file
    for backup_file in ${backup_files}; do
        # Skip if not a backup file
        if [[ ! "${backup_file}" =~ .*backup.*\.sql\.gz$ ]]; then
            continue
        fi
        
        local local_file="${BACKUP_DIR}/${backup_file}"
        
        # Skip if file already exists locally
        if [[ -f "${local_file}" ]]; then
            log_warning "Backup already exists locally: ${backup_file}"
            continue
        fi
        
        log_info "Copying ${backup_file} to external storage..."
        docker compose -f "${COMPOSE_FILE}" cp "postgres:${CONTAINER_BACKUP_DIR}/${backup_file}" "${BACKUP_DIR}/"
        
        if [[ -f "${local_file}" ]]; then
            log_success "Successfully copied: ${backup_file}"
            
            # Verify backup integrity
            if gzip -t "${local_file}" 2>/dev/null; then
                log_success "Backup integrity verified: ${backup_file}"
            else
                log_error "Backup file corrupted: ${backup_file}"
                rm -f "${local_file}"
            fi
        else
            log_error "Failed to copy: ${backup_file}"
        fi
    done
}

# Clean old backups (keep last 30 days)
cleanup_old_backups() {
    log_info "Cleaning up old backups (keeping last 30 days)..."
    
    # Clean local backups
    find "${BACKUP_DIR}" -name "*.sql.gz" -type f -mtime +30 -delete 2>/dev/null || true
    
    # Clean container backups (keep last 10)
    docker compose -f "${COMPOSE_FILE}" exec postgres bash -c "
        cd ${CONTAINER_BACKUP_DIR} && 
        ls -t *.sql.gz 2>/dev/null | tail -n +11 | xargs -r rm -f
    " 2>/dev/null || true
    
    log_success "Old backup cleanup completed"
}

# List available backups
list_backups() {
    log_info "Available backups:"
    
    echo -e "\n${BLUE}Container backups:${NC}"
    docker compose -f "${COMPOSE_FILE}" exec postgres backups
    
    echo -e "\n${BLUE}Local backups:${NC}"
    if [[ -d "${BACKUP_DIR}" ]] && [[ $(ls -1 "${BACKUP_DIR}"/*.sql.gz 2>/dev/null | wc -l) -gt 0 ]]; then
        ls -lht "${BACKUP_DIR}"/*.sql.gz
    else
        echo "No local backups found"
    fi
}

# Main backup function
main() {
    local backup_type="${1:-both}"
    
    log_info "Starting production database backup process..."
    log_info "Backup type: ${backup_type}"
    
    # Pre-flight checks
    ensure_backup_dir
    check_services
    
    # Create backups
    create_backup "${backup_type}"
    
    # Copy to external storage
    copy_backups_external
    
    # Cleanup old backups
    cleanup_old_backups
    
    # Show summary
    list_backups
    
    log_success "Database backup process completed successfully!"
    log_info "Backups are stored in: ${BACKUP_DIR}"
}

# Handle command line arguments
case "${1:-both}" in
    "local"|"migration"|"both")
        main "$1"
        ;;
    "list")
        list_backups
        ;;
    "help"|"-h"|"--help")
        echo "Usage: $0 [local|migration|both|list|help]"
        echo ""
        echo "  local      - Backup only the local development database"
        echo "  migration  - Backup only the migration database"
        echo "  both       - Backup both databases (default)"
        echo "  list       - List all available backups"
        echo "  help       - Show this help message"
        ;;
    *)
        log_error "Invalid argument: $1"
        log_error "Use '$0 help' for usage information"
        exit 1
        ;;
esac