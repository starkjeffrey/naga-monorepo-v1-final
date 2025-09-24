#!/usr/bin/env bash

###
### SECURE GOOGLE DRIVE BACKUP INTEGRATION
### Safely uploads database backups to Google Drive with encryption and verification
###
### Prerequisites:
### 1. Install rclone: brew install rclone (macOS) or apt install rclone (Linux)
### 2. Configure Google Drive: rclone config (follow interactive setup)
### 3. Set up GPG encryption for sensitive data
###
### Usage:
###     ./scripts/backup-google-drive.sh upload [backup_file]
###     ./scripts/backup-google-drive.sh sync
###     ./scripts/backup-google-drive.sh setup
###

set -o errexit
set -o pipefail
set -o nounset

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKUP_DIR="${PROJECT_ROOT}/backups"
LOG_FILE="${BACKUP_DIR}/gdrive-sync.log"

# Google Drive configuration
GDRIVE_REMOTE="gdrive"  # rclone remote name
GDRIVE_FOLDER="naga-sis-backups"
ENCRYPTION_ENABLED=true
GPG_RECIPIENT="your-email@example.com"  # Replace with your GPG key email

# Retention settings
GDRIVE_RETENTION_DAYS=365  # Keep backups for 1 year in Google Drive
MAX_GDRIVE_BACKUPS=100

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging functions
log_gdrive() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[${timestamp}] [GDRIVE-${level}] ${message}" >> "${LOG_FILE}"
    
    case "${level}" in
        "INFO")  echo -e "${BLUE}[GDRIVE-INFO]${NC} ${message}" ;;
        "SUCCESS") echo -e "${GREEN}[GDRIVE-SUCCESS]${NC} ${message}" ;;
        "WARNING") echo -e "${YELLOW}[GDRIVE-WARNING]${NC} ${message}" ;;
        "ERROR") echo -e "${RED}[GDRIVE-ERROR]${NC} ${message}" ;;
        "CRITICAL") echo -e "${RED}[GDRIVE-CRITICAL]${NC} ${message}" ;;
    esac
}

# Check prerequisites
check_prerequisites() {
    log_gdrive "INFO" "Checking Google Drive backup prerequisites..."
    
    # Check rclone installation
    if ! command -v rclone >/dev/null 2>&1; then
        log_gdrive "CRITICAL" "rclone is not installed. Install with: brew install rclone (macOS) or apt install rclone (Linux)"
        exit 1
    fi
    
    # Check rclone configuration
    if ! rclone listremotes | grep -q "^${GDRIVE_REMOTE}:$"; then
        log_gdrive "CRITICAL" "Google Drive remote '${GDRIVE_REMOTE}' not configured. Run: rclone config"
        exit 1
    fi
    
    # Check GPG if encryption enabled
    if [[ "${ENCRYPTION_ENABLED}" == true ]]; then
        if ! command -v gpg >/dev/null 2>&1; then
            log_gdrive "WARNING" "GPG not found - encryption disabled"
            ENCRYPTION_ENABLED=false
        elif ! gpg --list-keys "${GPG_RECIPIENT}" >/dev/null 2>&1; then
            log_gdrive "WARNING" "GPG key for '${GPG_RECIPIENT}' not found - encryption disabled"
            ENCRYPTION_ENABLED=false
        fi
    fi
    
    # Test Google Drive connectivity
    if ! rclone lsd "${GDRIVE_REMOTE}:" >/dev/null 2>&1; then
        log_gdrive "CRITICAL" "Cannot connect to Google Drive. Check rclone configuration and internet connection"
        exit 1
    fi
    
    log_gdrive "SUCCESS" "Prerequisites check passed"
}

# Setup Google Drive folder structure
setup_gdrive_folder() {
    log_gdrive "INFO" "Setting up Google Drive folder structure..."
    
    # Create main backup folder
    if ! rclone lsd "${GDRIVE_REMOTE}:" | grep -q "${GDRIVE_FOLDER}"; then
        rclone mkdir "${GDRIVE_REMOTE}:${GDRIVE_FOLDER}"
        log_gdrive "SUCCESS" "Created folder: ${GDRIVE_FOLDER}"
    fi
    
    # Create subfolders for organization
    rclone mkdir "${GDRIVE_REMOTE}:${GDRIVE_FOLDER}/local" 2>/dev/null || true
    rclone mkdir "${GDRIVE_REMOTE}:${GDRIVE_FOLDER}/migration" 2>/dev/null || true
    rclone mkdir "${GDRIVE_REMOTE}:${GDRIVE_FOLDER}/archives" 2>/dev/null || true
    
    log_gdrive "SUCCESS" "Google Drive folder structure ready"
}

# Encrypt backup file
encrypt_backup() {
    local backup_file="$1"
    local encrypted_file="${backup_file}.gpg"
    
    if [[ "${ENCRYPTION_ENABLED}" == true ]]; then
        log_gdrive "INFO" "Encrypting backup: $(basename ${backup_file})"
        
        if gpg --trust-model always --cipher-algo AES256 --compress-algo 1 --symmetric \
               --recipient "${GPG_RECIPIENT}" --armor \
               --output "${encrypted_file}" "${backup_file}"; then
            log_gdrive "SUCCESS" "Backup encrypted: $(basename ${encrypted_file})"
            echo "${encrypted_file}"
        else
            log_gdrive "ERROR" "Encryption failed for: $(basename ${backup_file})"
            echo "${backup_file}"  # Return original file if encryption fails
        fi
    else
        echo "${backup_file}"  # Return original file if encryption disabled
    fi
}

# Upload single backup file
upload_backup_file() {
    local backup_file="$1"
    local upload_file
    
    if [[ ! -f "${backup_file}" ]]; then
        log_gdrive "ERROR" "Backup file not found: ${backup_file}"
        return 1
    fi
    
    # Determine target folder based on filename
    local target_folder="${GDRIVE_FOLDER}"
    if [[ "$(basename ${backup_file})" == *"naga_local"* ]]; then
        target_folder="${GDRIVE_FOLDER}/local"
    elif [[ "$(basename ${backup_file})" == *"naga_migration"* ]]; then
        target_folder="${GDRIVE_FOLDER}/migration"
    fi
    
    # Encrypt if enabled
    upload_file=$(encrypt_backup "${backup_file}")
    
    # Verify file integrity before upload
    if [[ "${upload_file}" == *.gz ]]; then
        if ! gzip -t "${upload_file}" 2>/dev/null; then
            log_gdrive "ERROR" "Backup file corrupted before upload: $(basename ${upload_file})"
            return 1
        fi
    fi
    
    # Calculate checksums for verification
    local local_checksum
    local_checksum=$(sha256sum "${upload_file}" | cut -d' ' -f1)
    
    log_gdrive "INFO" "Uploading to Google Drive: $(basename ${upload_file})"
    
    # Upload with verification
    if rclone copy "${upload_file}" "${GDRIVE_REMOTE}:${target_folder}/" \
               --transfers 1 \
               --checkers 1 \
               --retries 3 \
               --low-level-retries 3 \
               --stats 30s \
               --progress; then
        
        # Verify upload integrity
        local remote_size
        remote_size=$(rclone size "${GDRIVE_REMOTE}:${target_folder}/$(basename ${upload_file})" --json | jq -r '.bytes')
        local local_size
        local_size=$(stat -f%z "${upload_file}" 2>/dev/null || stat -c%s "${upload_file}")
        
        if [[ "${remote_size}" == "${local_size}" ]]; then
            log_gdrive "SUCCESS" "Upload verified: $(basename ${upload_file}) (${local_size} bytes)"
            
            # Clean up encrypted file if it was created
            if [[ "${upload_file}" != "${backup_file}" ]] && [[ -f "${upload_file}" ]]; then
                rm -f "${upload_file}"
                log_gdrive "INFO" "Cleaned up temporary encrypted file"
            fi
            
            return 0
        else
            log_gdrive "ERROR" "Upload verification failed: size mismatch (local: ${local_size}, remote: ${remote_size})"
            return 1
        fi
    else
        log_gdrive "ERROR" "Upload failed: $(basename ${upload_file})"
        return 1
    fi
}

# Sync all local backups to Google Drive
sync_all_backups() {
    log_gdrive "INFO" "Starting full backup sync to Google Drive..."
    
    local uploaded=0
    local failed=0
    
    # Upload all backup files
    for backup_file in "${BACKUP_DIR}"/*.sql.gz "${BACKUP_DIR}"/*.dump; do
        if [[ -f "${backup_file}" ]]; then
            if upload_backup_file "${backup_file}"; then
                uploaded=$((uploaded + 1))
            else
                failed=$((failed + 1))
            fi
        fi
    done
    
    log_gdrive "SUCCESS" "Sync completed: ${uploaded} uploaded, ${failed} failed"
    
    # Cleanup old backups in Google Drive
    cleanup_gdrive_backups
}

# Cleanup old backups in Google Drive
cleanup_gdrive_backups() {
    log_gdrive "INFO" "Cleaning up old Google Drive backups..."
    
    # Get list of files older than retention period
    local cutoff_date
    cutoff_date=$(date -d "${GDRIVE_RETENTION_DAYS} days ago" '+%Y-%m-%d' 2>/dev/null || \
                  date -v-${GDRIVE_RETENTION_DAYS}d '+%Y-%m-%d')
    
    # Cleanup each subfolder
    for subfolder in "local" "migration"; do
        local folder_path="${GDRIVE_REMOTE}:${GDRIVE_FOLDER}/${subfolder}"
        
        # List files and move old ones to archives
        rclone lsf "${folder_path}" --format "pt" | while read -r line; do
            local filename=$(echo "${line}" | cut -d';' -f2)
            local file_date=$(echo "${line}" | cut -d';' -f1)
            
            if [[ "${file_date}" < "${cutoff_date}" ]]; then
                log_gdrive "INFO" "Archiving old backup: ${filename}"
                rclone move "${folder_path}/${filename}" "${GDRIVE_REMOTE}:${GDRIVE_FOLDER}/archives/"
            fi
        done
    done
    
    log_gdrive "SUCCESS" "Google Drive cleanup completed"
}

# Download and decrypt backup from Google Drive
download_backup() {
    local backup_filename="$1"
    local download_dir="${BACKUP_DIR}/downloads"
    
    mkdir -p "${download_dir}"
    
    log_gdrive "INFO" "Downloading backup from Google Drive: ${backup_filename}"
    
    # Search for file in all folders
    local found_file=""
    for subfolder in "local" "migration" "archives"; do
        local folder_path="${GDRIVE_REMOTE}:${GDRIVE_FOLDER}/${subfolder}"
        if rclone lsf "${folder_path}" | grep -q "^${backup_filename}"; then
            found_file="${folder_path}/${backup_filename}"
            break
        fi
    done
    
    if [[ -z "${found_file}" ]]; then
        log_gdrive "ERROR" "Backup file not found in Google Drive: ${backup_filename}"
        return 1
    fi
    
    # Download file
    if rclone copy "${found_file}" "${download_dir}/"; then
        local downloaded_file="${download_dir}/${backup_filename}"
        
        # Decrypt if needed
        if [[ "${backup_filename}" == *.gpg ]] && [[ "${ENCRYPTION_ENABLED}" == true ]]; then
            local decrypted_file="${downloaded_file%.gpg}"
            if gpg --decrypt "${downloaded_file}" > "${decrypted_file}"; then
                rm -f "${downloaded_file}"
                log_gdrive "SUCCESS" "Downloaded and decrypted: $(basename ${decrypted_file})"
                echo "${decrypted_file}"
            else
                log_gdrive "ERROR" "Decryption failed: ${backup_filename}"
                return 1
            fi
        else
            log_gdrive "SUCCESS" "Downloaded: $(basename ${downloaded_file})"
            echo "${downloaded_file}"
        fi
    else
        log_gdrive "ERROR" "Download failed: ${backup_filename}"
        return 1
    fi
}

# List backups in Google Drive
list_gdrive_backups() {
    log_gdrive "INFO" "Listing Google Drive backups..."
    
    echo -e "\n${CYAN}=== GOOGLE DRIVE BACKUPS ===${NC}"
    
    for subfolder in "local" "migration" "archives"; do
        echo -e "\n${BLUE}${subfolder} backups:${NC}"
        rclone ls "${GDRIVE_REMOTE}:${GDRIVE_FOLDER}/${subfolder}" 2>/dev/null | sort -k2 || echo "No backups found"
    done
    
    echo -e "\n${CYAN}Storage usage:${NC}"
    rclone size "${GDRIVE_REMOTE}:${GDRIVE_FOLDER}" --json | jq -r '"Total: \(.bytes | tonumber / 1024 / 1024 | floor)MB in \(.count) files"'
}

# Interactive setup
interactive_setup() {
    echo -e "${CYAN}=== GOOGLE DRIVE BACKUP SETUP ===${NC}"
    echo
    echo "This will guide you through setting up secure Google Drive backups."
    echo
    
    # Check rclone
    if ! command -v rclone >/dev/null 2>&1; then
        echo -e "${RED}Error: rclone not installed${NC}"
        echo "Install with:"
        echo "  macOS: brew install rclone"
        echo "  Linux: apt install rclone"
        exit 1
    fi
    
    # Check configuration
    if ! rclone listremotes | grep -q "^${GDRIVE_REMOTE}:$"; then
        echo -e "${YELLOW}Google Drive not configured.${NC}"
        echo "Run: rclone config"
        echo "Then create a Google Drive remote named '${GDRIVE_REMOTE}'"
        exit 1
    fi
    
    # Setup encryption
    if [[ "${ENCRYPTION_ENABLED}" == true ]]; then
        echo -e "${YELLOW}GPG encryption is enabled.${NC}"
        echo "Make sure you have a GPG key configured for: ${GPG_RECIPIENT}"
        echo "Generate one with: gpg --generate-key"
    fi
    
    # Test and setup
    check_prerequisites
    setup_gdrive_folder
    
    echo -e "${GREEN}Setup completed successfully!${NC}"
    echo
    echo "Usage:"
    echo "  Upload single backup:  $0 upload backup_file.sql.gz"
    echo "  Sync all backups:      $0 sync"
    echo "  List remote backups:   $0 list"
    echo "  Download backup:       $0 download backup_file.sql.gz"
}

# Main function
main() {
    local command="${1:-help}"
    
    case "${command}" in
        "upload")
            if [[ -z "${2:-}" ]]; then
                echo "Usage: $0 upload <backup_file>"
                exit 1
            fi
            
            check_prerequisites
            setup_gdrive_folder
            upload_backup_file "${2}"
            ;;
            
        "sync")
            check_prerequisites
            setup_gdrive_folder
            sync_all_backups
            ;;
            
        "download")
            if [[ -z "${2:-}" ]]; then
                echo "Usage: $0 download <backup_filename>"
                exit 1
            fi
            
            check_prerequisites
            download_backup "${2}"
            ;;
            
        "list")
            check_prerequisites
            list_gdrive_backups
            ;;
            
        "cleanup")
            check_prerequisites
            cleanup_gdrive_backups
            ;;
            
        "setup")
            interactive_setup
            ;;
            
        "help"|"-h"|"--help")
            echo "Google Drive Backup Integration"
            echo ""
            echo "Usage: $0 [command] [options]"
            echo ""
            echo "Commands:"
            echo "  setup                    - Interactive setup guide"
            echo "  upload <backup_file>     - Upload single backup to Google Drive"
            echo "  sync                     - Sync all local backups to Google Drive"
            echo "  download <filename>      - Download backup from Google Drive"
            echo "  list                     - List all backups in Google Drive"
            echo "  cleanup                  - Clean up old backups in Google Drive"
            echo "  help                     - Show this help message"
            echo ""
            echo "Prerequisites:"
            echo "  1. Install rclone: brew install rclone"
            echo "  2. Configure Google Drive: rclone config"
            echo "  3. (Optional) Set up GPG for encryption"
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