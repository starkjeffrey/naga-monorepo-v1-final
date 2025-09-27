#!/bin/bash
# Comprehensive Backup Script for Staff-Web V2 Production System
# Usage: ./backup-system.sh [--type full|database|files] [--compress] [--remote]

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
COMPOSE_FILE="docker-compose.staff-web-production.yml"

# Default values
BACKUP_TYPE="full"
COMPRESS=true
REMOTE_BACKUP=false
RETENTION_DAYS=30

# Backup locations
LOCAL_BACKUP_DIR="/backups/staff-web-v2"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="staff_web_v2_${BACKUP_TYPE}_${TIMESTAMP}"

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
Staff-Web V2 Production Backup Script

Usage: $0 [OPTIONS]

OPTIONS:
    --type TYPE      Backup type: full|database|files [default: full]
    --compress       Compress backup files (default: enabled)
    --no-compress    Disable compression
    --remote         Upload backup to remote storage
    --retention N    Retention period in days [default: 30]
    --help           Show this help message

BACKUP TYPES:
    full             Complete system backup (database + files)
    database         Database backup only
    files            Application files backup only

EXAMPLES:
    $0                           # Full compressed backup
    $0 --type database           # Database backup only
    $0 --type files --remote     # Files backup with remote upload
    $0 --no-compress --retention 7  # Uncompressed backup, 7-day retention

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --type)
            BACKUP_TYPE="$2"
            shift 2
            ;;
        --compress)
            COMPRESS=true
            shift
            ;;
        --no-compress)
            COMPRESS=false
            shift
            ;;
        --remote)
            REMOTE_BACKUP=true
            shift
            ;;
        --retention)
            RETENTION_DAYS="$2"
            shift 2
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

# Validate backup type
if [[ "$BACKUP_TYPE" != "full" && "$BACKUP_TYPE" != "database" && "$BACKUP_TYPE" != "files" ]]; then
    error "Invalid backup type: $BACKUP_TYPE. Must be 'full', 'database', or 'files'"
fi

# Create backup directory
create_backup_directory() {
    log "Creating backup directory..."

    mkdir -p "$LOCAL_BACKUP_DIR" || {
        error "Failed to create backup directory: $LOCAL_BACKUP_DIR"
    }

    success "Backup directory created: $LOCAL_BACKUP_DIR"
}

# Database backup
backup_database() {
    log "Creating database backup..."

    local db_backup_file="$LOCAL_BACKUP_DIR/${BACKUP_NAME}_database.sql"

    # Create database dump
    docker-compose -f "$COMPOSE_FILE" exec -T postgres pg_dump \
        -h localhost -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
        --clean --if-exists --create --verbose > "$db_backup_file" || {
        error "Database backup failed"
    }

    # Compress if requested
    if [[ "$COMPRESS" == "true" ]]; then
        log "Compressing database backup..."
        gzip "$db_backup_file" || {
            error "Database backup compression failed"
        }
        db_backup_file="${db_backup_file}.gz"
    fi

    # Verify backup
    if [[ -f "$db_backup_file" ]]; then
        local size=$(du -h "$db_backup_file" | cut -f1)
        success "Database backup created: $db_backup_file ($size)"
    else
        error "Database backup file not found"
    fi
}

# Files backup
backup_files() {
    log "Creating files backup..."

    local files_backup_file="$LOCAL_BACKUP_DIR/${BACKUP_NAME}_files.tar"

    # Create list of directories to backup
    local backup_dirs=(
        "backend/mediafiles"
        "backend/staticfiles"
        "staff-web/build"
        ".envs"
        "docker-compose*.yml"
        "monitoring"
        "scripts"
        "security"
    )

    # Create tar archive
    cd "$PROJECT_ROOT"
    tar -cf "$files_backup_file" "${backup_dirs[@]}" 2>/dev/null || {
        warn "Some files could not be backed up, continuing..."
    }

    # Compress if requested
    if [[ "$COMPRESS" == "true" ]]; then
        log "Compressing files backup..."
        gzip "$files_backup_file" || {
            error "Files backup compression failed"
        }
        files_backup_file="${files_backup_file}.gz"
    fi

    # Verify backup
    if [[ -f "$files_backup_file" ]]; then
        local size=$(du -h "$files_backup_file" | cut -f1)
        success "Files backup created: $files_backup_file ($size)"
    else
        error "Files backup file not found"
    fi
}

# Docker volumes backup
backup_docker_volumes() {
    log "Creating Docker volumes backup..."

    local volumes_backup_file="$LOCAL_BACKUP_DIR/${BACKUP_NAME}_volumes.tar"

    # Get list of project volumes
    local volumes=$(docker-compose -f "$COMPOSE_FILE" config --volumes 2>/dev/null | grep "naga_" || true)

    if [[ -n "$volumes" ]]; then
        # Create temporary container to backup volumes
        for volume in $volumes; do
            log "Backing up volume: $volume"
            docker run --rm \
                -v "$volume:/volume:ro" \
                -v "$LOCAL_BACKUP_DIR:/backup" \
                alpine tar -czf "/backup/${volume}_${TIMESTAMP}.tar.gz" -C /volume . || {
                warn "Failed to backup volume: $volume"
            }
        done

        success "Docker volumes backup completed"
    else
        warn "No project volumes found to backup"
    fi
}

# Configuration backup
backup_configuration() {
    log "Creating configuration backup..."

    local config_backup_file="$LOCAL_BACKUP_DIR/${BACKUP_NAME}_config.tar"

    # Configuration files to backup
    local config_files=(
        ".env*"
        "docker-compose*.yml"
        "nginx.conf"
        "prometheus.yml"
        "grafana"
        "monitoring"
        "security"
    )

    cd "$PROJECT_ROOT"
    tar -cf "$config_backup_file" "${config_files[@]}" 2>/dev/null || {
        warn "Some configuration files could not be backed up"
    }

    if [[ "$COMPRESS" == "true" ]]; then
        gzip "$config_backup_file"
        config_backup_file="${config_backup_file}.gz"
    fi

    if [[ -f "$config_backup_file" ]]; then
        local size=$(du -h "$config_backup_file" | cut -f1)
        success "Configuration backup created: $config_backup_file ($size)"
    fi
}

# Upload to remote storage
upload_to_remote() {
    if [[ "$REMOTE_BACKUP" != "true" ]]; then
        return 0
    fi

    log "Uploading backup to remote storage..."

    # This is a template - implement based on your remote storage solution
    # Examples:

    # AWS S3
    # aws s3 sync "$LOCAL_BACKUP_DIR" s3://your-backup-bucket/staff-web-v2/ --delete

    # rsync to remote server
    # rsync -avz --delete "$LOCAL_BACKUP_DIR/" user@backup-server:/backups/staff-web-v2/

    # Google Cloud Storage
    # gsutil -m rsync -r -d "$LOCAL_BACKUP_DIR" gs://your-backup-bucket/staff-web-v2/

    warn "Remote backup not configured - implement based on your storage solution"
}

# Cleanup old backups
cleanup_old_backups() {
    log "Cleaning up old backups (retention: $RETENTION_DAYS days)..."

    # Remove local backups older than retention period
    find "$LOCAL_BACKUP_DIR" -type f -mtime "+$RETENTION_DAYS" -delete 2>/dev/null || {
        warn "Failed to cleanup some old backup files"
    }

    # Count remaining backups
    local remaining_backups=$(find "$LOCAL_BACKUP_DIR" -type f | wc -l)
    success "Cleanup completed. Remaining backups: $remaining_backups"
}

# Generate backup manifest
generate_manifest() {
    log "Generating backup manifest..."

    local manifest_file="$LOCAL_BACKUP_DIR/${BACKUP_NAME}_manifest.txt"

    cat > "$manifest_file" << EOF
Staff-Web V2 Backup Manifest
============================

Backup Type: $BACKUP_TYPE
Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)
Compressed: $COMPRESS
Remote Upload: $REMOTE_BACKUP

System Information:
- Hostname: $(hostname)
- OS: $(uname -a)
- Docker Version: $(docker --version 2>/dev/null || echo "N/A")
- Docker Compose Version: $(docker-compose --version 2>/dev/null || echo "N/A")

Files in this backup:
EOF

    # List backup files
    find "$LOCAL_BACKUP_DIR" -name "${BACKUP_NAME}*" -type f -exec ls -lh {} \; >> "$manifest_file"

    success "Backup manifest created: $manifest_file"
}

# Main backup function
main() {
    log "Starting Staff-Web V2 backup (type: $BACKUP_TYPE, compress: $COMPRESS, remote: $REMOTE_BACKUP)"

    cd "$PROJECT_ROOT"

    # Create backup directory
    create_backup_directory

    # Perform backup based on type
    case $BACKUP_TYPE in
        "database")
            backup_database
            ;;
        "files")
            backup_files
            backup_configuration
            ;;
        "full")
            backup_database
            backup_files
            backup_docker_volumes
            backup_configuration
            ;;
    esac

    # Generate manifest
    generate_manifest

    # Upload to remote storage
    upload_to_remote

    # Cleanup old backups
    cleanup_old_backups

    success "Backup completed successfully!"
    log "Backup location: $LOCAL_BACKUP_DIR"
    log "Backup name pattern: ${BACKUP_NAME}*"
}

# Trap errors
trap 'error "Backup failed! Check logs for details."' ERR

# Run main function
main "$@"