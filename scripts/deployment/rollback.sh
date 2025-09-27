#!/bin/bash
# Rollback Script for Staff-Web V2 Production System
# Usage: ./rollback.sh [--backup-name BACKUP_NAME] [--force]

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
COMPOSE_FILE="docker-compose.staff-web-production.yml"

# Default values
BACKUP_NAME=""
FORCE_ROLLBACK=false

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Help function
show_help() {
    cat << EOF
Staff-Web V2 Production Rollback Script

Usage: $0 [OPTIONS]

OPTIONS:
    --backup-name NAME   Specific backup to restore (if not provided, uses latest)
    --force              Force rollback without confirmation
    --help               Show this help message

EXAMPLES:
    $0                                           # Rollback to latest backup
    $0 --backup-name staff_web_v2_backup_20240327_143022  # Rollback to specific backup
    $0 --force                                   # Force rollback without prompts

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --backup-name)
            BACKUP_NAME="$2"
            shift 2
            ;;
        --force)
            FORCE_ROLLBACK=true
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            ;;
    esac
done

# Confirmation prompt
confirm_rollback() {
    if [[ "$FORCE_ROLLBACK" == "true" ]]; then
        return 0
    fi

    echo -e "${RED}WARNING: This will rollback the Staff-Web V2 system to a previous state.${NC}"
    echo "This action will:"
    echo "  - Stop current services"
    echo "  - Restore database from backup"
    echo "  - Restart services with previous configuration"
    echo ""
    read -p "Are you sure you want to proceed? (yes/no): " -r

    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        log "Rollback cancelled by user"
        exit 0
    fi
}

# List available backups
list_backups() {
    log "Available backups:"
    docker-compose -f "$COMPOSE_FILE" exec postgres-backup ls -la /backups/ || {
        error "Failed to list backups"
    }
}

# Find latest backup
find_latest_backup() {
    log "Finding latest backup..."

    BACKUP_NAME=$(docker-compose -f "$COMPOSE_FILE" exec -T postgres-backup \
        find /backups -name "*.sql.gz" -type f -printf '%T@ %p\n' | \
        sort -n | tail -1 | cut -d' ' -f2- | xargs basename) || {
        error "Failed to find latest backup"
    }

    if [[ -z "$BACKUP_NAME" ]]; then
        error "No backups found"
    fi

    log "Latest backup found: $BACKUP_NAME"
}

# Verify backup exists
verify_backup() {
    log "Verifying backup: $BACKUP_NAME"

    docker-compose -f "$COMPOSE_FILE" exec -T postgres-backup \
        test -f "/backups/$BACKUP_NAME" || {
        error "Backup file not found: $BACKUP_NAME"
    }

    success "Backup verified: $BACKUP_NAME"
}

# Stop services gracefully
stop_services() {
    log "Stopping current services..."

    # Stop application services first
    docker-compose -f "$COMPOSE_FILE" stop staff-web django celery-worker celery-beat || {
        warn "Failed to stop some application services"
    }

    # Stop supporting services
    docker-compose -f "$COMPOSE_FILE" stop redis || {
        warn "Failed to stop Redis"
    }

    success "Services stopped"
}

# Backup current state before rollback
backup_current_state() {
    log "Creating backup of current state before rollback..."

    local rollback_backup_name="pre_rollback_backup_$(date +%Y%m%d_%H%M%S)"

    docker-compose -f "$COMPOSE_FILE" exec -T postgres pg_dump \
        -h postgres -U "$POSTGRES_USER" -d "$POSTGRES_DB" | \
        gzip > "/tmp/$rollback_backup_name.sql.gz" || {
        warn "Failed to create pre-rollback backup"
    }

    success "Pre-rollback backup created: $rollback_backup_name"
}

# Restore database
restore_database() {
    log "Restoring database from backup: $BACKUP_NAME"

    # Stop PostgreSQL connections
    docker-compose -f "$COMPOSE_FILE" exec -T postgres psql \
        -h postgres -U "$POSTGRES_USER" -d postgres \
        -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$POSTGRES_DB' AND pid <> pg_backend_pid();" || {
        warn "Failed to terminate existing connections"
    }

    # Restore database
    docker-compose -f "$COMPOSE_FILE" exec -T postgres-backup \
        gunzip -c "/backups/$BACKUP_NAME" | \
        docker-compose -f "$COMPOSE_FILE" exec -T postgres psql \
        -h postgres -U "$POSTGRES_USER" -d "$POSTGRES_DB" || {
        error "Database restore failed"
    }

    success "Database restored successfully"
}

# Start services
start_services() {
    log "Starting services..."

    # Start core services first
    docker-compose -f "$COMPOSE_FILE" up -d postgres redis || {
        error "Failed to start core services"
    }

    # Wait for core services
    sleep 30

    # Start application services
    docker-compose -f "$COMPOSE_FILE" up -d django celery-worker celery-beat staff-web || {
        error "Failed to start application services"
    }

    success "Services started"
}

# Health checks
perform_health_checks() {
    log "Performing health checks..."

    local max_attempts=30
    local attempt=1

    # Check Django health
    while [[ $attempt -le $max_attempts ]]; do
        if docker-compose -f "$COMPOSE_FILE" exec -T django \
           wget --quiet --tries=1 --spider "http://localhost:8000/health-check/" 2>/dev/null; then
            success "Django health check passed"
            break
        fi

        if [[ $attempt -eq $max_attempts ]]; then
            error "Django health check failed after $max_attempts attempts"
        fi

        log "Health check attempt $attempt/$max_attempts failed, retrying in 10 seconds..."
        sleep 10
        ((attempt++))
    done

    # Check frontend health
    attempt=1
    while [[ $attempt -le $max_attempts ]]; do
        if docker-compose -f "$COMPOSE_FILE" exec -T staff-web \
           wget --quiet --tries=1 --spider "http://localhost:80/health" 2>/dev/null; then
            success "Frontend health check passed"
            break
        fi

        if [[ $attempt -eq $max_attempts ]]; then
            error "Frontend health check failed after $max_attempts attempts"
        fi

        log "Frontend health check attempt $attempt/$max_attempts failed, retrying in 10 seconds..."
        sleep 10
        ((attempt++))
    done

    success "All health checks passed"
}

# Main rollback function
main() {
    log "Starting Staff-Web V2 rollback process"

    cd "$PROJECT_ROOT"

    # Show confirmation
    confirm_rollback

    # Find backup if not specified
    if [[ -z "$BACKUP_NAME" ]]; then
        list_backups
        find_latest_backup
    fi

    # Verify backup exists
    verify_backup

    # Backup current state
    backup_current_state

    # Stop services
    stop_services

    # Restore database
    restore_database

    # Start services
    start_services

    # Health checks
    perform_health_checks

    success "Rollback completed successfully!"
    log "System has been rolled back to backup: $BACKUP_NAME"
    log "Services should be available at:"
    log "  - Frontend: https://staff.yourdomain.com"
    log "  - API: https://api.yourdomain.com"
}

# Trap errors
trap 'error "Rollback failed! System may be in inconsistent state."' ERR

# Run main function
main "$@"