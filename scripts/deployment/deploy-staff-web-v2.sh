#!/bin/bash
# Automated Deployment Script for Staff-Web V2 Production System
# Usage: ./deploy-staff-web-v2.sh [--environment prod|staging] [--skip-backup] [--quick]

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
COMPOSE_FILE="docker-compose.staff-web-production.yml"
ENV_FILE=".env.production"

# Default values
ENVIRONMENT="prod"
SKIP_BACKUP=false
QUICK_DEPLOY=false
FORCE_DEPLOY=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging
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
Staff-Web V2 Production Deployment Script

Usage: $0 [OPTIONS]

OPTIONS:
    --environment ENV    Deployment environment (prod|staging) [default: prod]
    --skip-backup       Skip database backup before deployment
    --quick             Quick deployment (skip tests and non-critical checks)
    --force             Force deployment even if health checks fail
    --help              Show this help message

EXAMPLES:
    $0                                    # Full production deployment
    $0 --environment staging             # Deploy to staging
    $0 --quick --skip-backup             # Quick deployment without backup
    $0 --force                           # Force deployment

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --skip-backup)
            SKIP_BACKUP=true
            shift
            ;;
        --quick)
            QUICK_DEPLOY=true
            shift
            ;;
        --force)
            FORCE_DEPLOY=true
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

# Validate environment
if [[ "$ENVIRONMENT" != "prod" && "$ENVIRONMENT" != "staging" ]]; then
    error "Environment must be 'prod' or 'staging'"
fi

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."

    # Check if running as root
    if [[ $EUID -eq 0 ]]; then
        error "This script should not be run as root"
    fi

    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed or not in PATH"
    fi

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed or not in PATH"
    fi

    # Check if we're in the right directory
    if [[ ! -f "$PROJECT_ROOT/$COMPOSE_FILE" ]]; then
        error "Docker Compose file not found: $PROJECT_ROOT/$COMPOSE_FILE"
    fi

    # Check environment file
    if [[ ! -f "$PROJECT_ROOT/$ENV_FILE" ]]; then
        error "Environment file not found: $PROJECT_ROOT/$ENV_FILE"
        log "Please copy $ENV_FILE.example to $ENV_FILE and configure it"
    fi

    success "Prerequisites check passed"
}

# Health check function
health_check() {
    local service=$1
    local endpoint=$2
    local max_attempts=30
    local attempt=1

    log "Performing health check for $service..."

    while [[ $attempt -le $max_attempts ]]; do
        if docker-compose -f "$COMPOSE_FILE" exec -T "$service" wget --quiet --tries=1 --spider "$endpoint" 2>/dev/null; then
            success "$service health check passed"
            return 0
        fi

        log "Health check attempt $attempt/$max_attempts failed, retrying in 10 seconds..."
        sleep 10
        ((attempt++))
    done

    error "$service health check failed after $max_attempts attempts"
}

# Backup database
backup_database() {
    if [[ "$SKIP_BACKUP" == "true" ]]; then
        warn "Skipping database backup as requested"
        return 0
    fi

    log "Creating database backup..."

    local backup_name="staff_web_v2_backup_$(date +%Y%m%d_%H%M%S)"

    # Create backup using postgres-backup service
    docker-compose -f "$COMPOSE_FILE" exec -T postgres-backup /usr/local/bin/backup-now.sh "$backup_name" || {
        error "Database backup failed"
    }

    success "Database backup created: $backup_name"
}

# Pull latest images
pull_images() {
    log "Pulling latest Docker images..."

    docker-compose -f "$COMPOSE_FILE" pull || {
        error "Failed to pull Docker images"
    }

    success "Docker images pulled successfully"
}

# Build custom images
build_images() {
    log "Building custom Docker images..."

    # Build Django backend
    docker-compose -f "$COMPOSE_FILE" build django || {
        error "Failed to build Django image"
    }

    # Build React frontend
    docker-compose -f "$COMPOSE_FILE" build staff-web || {
        error "Failed to build Staff-Web frontend image"
    }

    success "Custom images built successfully"
}

# Run database migrations
run_migrations() {
    log "Running database migrations..."

    docker-compose -f "$COMPOSE_FILE" exec -T django python manage.py migrate --no-input || {
        error "Database migrations failed"
    }

    success "Database migrations completed"
}

# Collect static files
collect_static() {
    log "Collecting static files..."

    docker-compose -f "$COMPOSE_FILE" exec -T django python manage.py collectstatic --no-input --clear || {
        error "Static file collection failed"
    }

    success "Static files collected"
}

# Deploy services
deploy_services() {
    log "Deploying services..."

    # Deploy with zero-downtime strategy
    docker-compose -f "$COMPOSE_FILE" up -d --remove-orphans || {
        error "Service deployment failed"
    }

    success "Services deployed successfully"
}

# Post-deployment tasks
post_deployment() {
    log "Running post-deployment tasks..."

    # Wait for services to be ready
    sleep 30

    # Health checks
    if [[ "$FORCE_DEPLOY" != "true" ]]; then
        health_check "django" "http://localhost:8000/health-check/"
        health_check "staff-web" "http://localhost:80/health"
    fi

    # Clear application caches
    docker-compose -f "$COMPOSE_FILE" exec -T django python manage.py clear_cache || {
        warn "Cache clearing failed, continuing..."
    }

    # Warm up application
    log "Warming up application..."
    docker-compose -f "$COMPOSE_FILE" exec -T django python manage.py warmup_cache || {
        warn "Cache warmup failed, continuing..."
    }

    success "Post-deployment tasks completed"
}

# Cleanup old images and containers
cleanup() {
    log "Cleaning up old Docker resources..."

    # Remove dangling images
    docker image prune -f || warn "Image cleanup failed"

    # Remove unused volumes (be careful with this)
    # docker volume prune -f || warn "Volume cleanup failed"

    success "Cleanup completed"
}

# Main deployment function
main() {
    log "Starting Staff-Web V2 deployment for environment: $ENVIRONMENT"
    log "Quick deploy: $QUICK_DEPLOY, Skip backup: $SKIP_BACKUP, Force: $FORCE_DEPLOY"

    cd "$PROJECT_ROOT"

    # Pre-deployment checks
    check_prerequisites

    # Backup (unless skipped)
    backup_database

    # Pull and build images
    pull_images
    build_images

    # Database operations
    run_migrations
    collect_static

    # Deploy services
    deploy_services

    # Post-deployment
    post_deployment

    # Cleanup
    cleanup

    success "Staff-Web V2 deployment completed successfully!"
    log "Services should be available at:"
    log "  - Frontend: https://staff.yourdomain.com"
    log "  - API: https://api.yourdomain.com"
    log "  - Monitoring: https://grafana.yourdomain.com"
}

# Trap errors and cleanup
trap 'error "Deployment failed! Check logs for details."' ERR

# Run main function
main "$@"