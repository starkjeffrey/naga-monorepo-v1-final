#!/bin/bash
# Comprehensive Health Check Script for Staff-Web V2 Production System
# Usage: ./health-check.sh [--verbose] [--json] [--critical-only]

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
COMPOSE_FILE="docker-compose.staff-web-production.yml"

# Default values
VERBOSE=false
JSON_OUTPUT=false
CRITICAL_ONLY=false

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Health status tracking
OVERALL_STATUS="healthy"
HEALTH_RESULTS=()

# Logging functions
log() {
    if [[ "$JSON_OUTPUT" != "true" ]]; then
        echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
    fi
}

warn() {
    if [[ "$JSON_OUTPUT" != "true" ]]; then
        echo -e "${YELLOW}[WARNING]${NC} $1"
    fi
}

error() {
    if [[ "$JSON_OUTPUT" != "true" ]]; then
        echo -e "${RED}[ERROR]${NC} $1"
    fi
}

success() {
    if [[ "$JSON_OUTPUT" != "true" ]]; then
        echo -e "${GREEN}[SUCCESS]${NC} $1"
    fi
}

# Add health result
add_result() {
    local service=$1
    local status=$2
    local message=$3
    local critical=${4:-false}

    HEALTH_RESULTS+=("$service:$status:$message:$critical")

    if [[ "$status" != "healthy" ]]; then
        if [[ "$critical" == "true" ]]; then
            OVERALL_STATUS="critical"
        elif [[ "$OVERALL_STATUS" != "critical" ]]; then
            OVERALL_STATUS="warning"
        fi
    fi
}

# Help function
show_help() {
    cat << EOF
Staff-Web V2 Production Health Check Script

Usage: $0 [OPTIONS]

OPTIONS:
    --verbose         Enable verbose output
    --json           Output results in JSON format
    --critical-only  Check only critical services
    --help           Show this help message

EXAMPLES:
    $0                    # Standard health check
    $0 --verbose          # Detailed health check
    $0 --json             # JSON output for monitoring
    $0 --critical-only    # Quick critical services check

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --verbose)
            VERBOSE=true
            shift
            ;;
        --json)
            JSON_OUTPUT=true
            shift
            ;;
        --critical-only)
            CRITICAL_ONLY=true
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            shift
            ;;
    esac
done

# Check if service is running
check_service_running() {
    local service=$1
    local critical=${2:-false}

    if docker-compose -f "$COMPOSE_FILE" ps "$service" | grep -q "Up"; then
        add_result "$service" "healthy" "Service is running" "$critical"
        if [[ "$VERBOSE" == "true" ]]; then
            success "$service is running"
        fi
        return 0
    else
        add_result "$service" "unhealthy" "Service is not running" "$critical"
        error "$service is not running"
        return 1
    fi
}

# Check service health endpoint
check_health_endpoint() {
    local service=$1
    local endpoint=$2
    local critical=${3:-false}

    if docker-compose -f "$COMPOSE_FILE" exec -T "$service" \
       wget --quiet --tries=1 --spider "$endpoint" 2>/dev/null; then
        add_result "$service-health" "healthy" "Health endpoint responding" "$critical"
        if [[ "$VERBOSE" == "true" ]]; then
            success "$service health endpoint is responding"
        fi
        return 0
    else
        add_result "$service-health" "unhealthy" "Health endpoint not responding" "$critical"
        error "$service health endpoint is not responding"
        return 1
    fi
}

# Check database connectivity
check_database() {
    local critical=true

    log "Checking database connectivity..."

    if docker-compose -f "$COMPOSE_FILE" exec -T postgres \
       pg_isready -h localhost -p 5432 -U postgres 2>/dev/null; then
        add_result "database" "healthy" "Database is accepting connections" "$critical"
        if [[ "$VERBOSE" == "true" ]]; then
            success "Database is accepting connections"
        fi
    else
        add_result "database" "unhealthy" "Database is not accepting connections" "$critical"
        error "Database is not accepting connections"
        return 1
    fi

    # Check database queries
    if docker-compose -f "$COMPOSE_FILE" exec -T postgres \
       psql -h localhost -U postgres -d "$POSTGRES_DB" -c "SELECT 1;" >/dev/null 2>&1; then
        add_result "database-query" "healthy" "Database queries working" "$critical"
        if [[ "$VERBOSE" == "true" ]]; then
            success "Database queries are working"
        fi
    else
        add_result "database-query" "unhealthy" "Database queries failing" "$critical"
        error "Database queries are failing"
    fi
}

# Check Redis connectivity
check_redis() {
    local critical=true

    log "Checking Redis connectivity..."

    if docker-compose -f "$COMPOSE_FILE" exec -T redis redis-cli ping 2>/dev/null | grep -q "PONG"; then
        add_result "redis" "healthy" "Redis is responding" "$critical"
        if [[ "$VERBOSE" == "true" ]]; then
            success "Redis is responding"
        fi
    else
        add_result "redis" "unhealthy" "Redis is not responding" "$critical"
        error "Redis is not responding"
    fi
}

# Check disk space
check_disk_space() {
    local critical=false

    log "Checking disk space..."

    local disk_usage=$(df /var/lib/docker | awk 'NR==2 {print $5}' | sed 's/%//')

    if [[ $disk_usage -lt 80 ]]; then
        add_result "disk-space" "healthy" "Disk usage: ${disk_usage}%" "$critical"
        if [[ "$VERBOSE" == "true" ]]; then
            success "Disk usage is normal: ${disk_usage}%"
        fi
    elif [[ $disk_usage -lt 90 ]]; then
        add_result "disk-space" "warning" "Disk usage high: ${disk_usage}%" "$critical"
        warn "Disk usage is high: ${disk_usage}%"
    else
        add_result "disk-space" "critical" "Disk usage critical: ${disk_usage}%" "true"
        error "Disk usage is critical: ${disk_usage}%"
    fi
}

# Check memory usage
check_memory() {
    local critical=false

    log "Checking memory usage..."

    local memory_usage=$(free | awk 'NR==2{printf "%.2f", $3*100/$2}')
    local memory_int=${memory_usage%.*}

    if [[ $memory_int -lt 80 ]]; then
        add_result "memory" "healthy" "Memory usage: ${memory_usage}%" "$critical"
        if [[ "$VERBOSE" == "true" ]]; then
            success "Memory usage is normal: ${memory_usage}%"
        fi
    elif [[ $memory_int -lt 90 ]]; then
        add_result "memory" "warning" "Memory usage high: ${memory_usage}%" "$critical"
        warn "Memory usage is high: ${memory_usage}%"
    else
        add_result "memory" "critical" "Memory usage critical: ${memory_usage}%" "true"
        error "Memory usage is critical: ${memory_usage}%"
    fi
}

# Check SSL certificates
check_ssl_certificates() {
    local critical=false

    log "Checking SSL certificates..."

    # This would typically check certificate expiration
    # For now, we'll do a basic connectivity check
    if command -v openssl >/dev/null 2>&1; then
        local domain="${DOMAIN_NAME:-localhost}"
        local expiry_date=$(echo | openssl s_client -servername "$domain" -connect "$domain:443" 2>/dev/null | \
                           openssl x509 -noout -dates 2>/dev/null | grep notAfter | cut -d= -f2)

        if [[ -n "$expiry_date" ]]; then
            add_result "ssl-cert" "healthy" "SSL certificate valid until: $expiry_date" "$critical"
            if [[ "$VERBOSE" == "true" ]]; then
                success "SSL certificate is valid until: $expiry_date"
            fi
        else
            add_result "ssl-cert" "warning" "Could not verify SSL certificate" "$critical"
            warn "Could not verify SSL certificate"
        fi
    else
        add_result "ssl-cert" "skipped" "OpenSSL not available" "$critical"
        warn "OpenSSL not available for certificate check"
    fi
}

# Check backup status
check_backup_status() {
    local critical=false

    log "Checking backup status..."

    # Check if backup service is running
    if check_service_running "postgres-backup" "$critical"; then
        # Check for recent backups
        local latest_backup=$(docker-compose -f "$COMPOSE_FILE" exec -T postgres-backup \
                             find /backups -name "*.sql.gz" -type f -mtime -1 2>/dev/null | wc -l)

        if [[ $latest_backup -gt 0 ]]; then
            add_result "backup" "healthy" "Recent backup found ($latest_backup files)" "$critical"
            if [[ "$VERBOSE" == "true" ]]; then
                success "Recent backup found ($latest_backup files)"
            fi
        else
            add_result "backup" "warning" "No recent backups found" "$critical"
            warn "No recent backups found"
        fi
    else
        add_result "backup" "unhealthy" "Backup service not running" "$critical"
    fi
}

# Output results in JSON format
output_json() {
    local json_output="{"
    json_output+="\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
    json_output+="\"overall_status\":\"$OVERALL_STATUS\","
    json_output+="\"checks\":["

    local first=true
    for result in "${HEALTH_RESULTS[@]}"; do
        IFS=':' read -r service status message critical <<< "$result"

        if [[ "$first" != "true" ]]; then
            json_output+=","
        fi
        first=false

        json_output+="{"
        json_output+="\"service\":\"$service\","
        json_output+="\"status\":\"$status\","
        json_output+="\"message\":\"$message\","
        json_output+="\"critical\":$critical"
        json_output+="}"
    done

    json_output+="]}"
    echo "$json_output"
}

# Main health check function
main() {
    cd "$PROJECT_ROOT"

    if [[ "$JSON_OUTPUT" != "true" ]]; then
        log "Starting Staff-Web V2 health check..."
    fi

    # Critical services (always checked)
    check_service_running "postgres" true
    check_service_running "redis" true
    check_service_running "django" true
    check_service_running "staff-web" true

    check_database
    check_redis
    check_health_endpoint "django" "http://localhost:8000/health-check/" true
    check_health_endpoint "staff-web" "http://localhost:80/health" true

    # Non-critical checks (skipped if --critical-only)
    if [[ "$CRITICAL_ONLY" != "true" ]]; then
        check_service_running "celery-worker" false
        check_service_running "celery-beat" false
        check_service_running "traefik" false
        check_service_running "prometheus" false
        check_service_running "grafana" false

        check_disk_space
        check_memory
        check_ssl_certificates
        check_backup_status
    fi

    # Output results
    if [[ "$JSON_OUTPUT" == "true" ]]; then
        output_json
    else
        echo ""
        case $OVERALL_STATUS in
            "healthy")
                success "Overall system status: HEALTHY"
                ;;
            "warning")
                warn "Overall system status: WARNING - Some non-critical issues detected"
                ;;
            "critical")
                error "Overall system status: CRITICAL - Immediate attention required"
                ;;
        esac
    fi

    # Exit with appropriate code
    case $OVERALL_STATUS in
        "healthy") exit 0 ;;
        "warning") exit 1 ;;
        "critical") exit 2 ;;
    esac
}

# Run main function
main "$@"