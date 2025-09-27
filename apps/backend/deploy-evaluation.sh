#!/bin/bash
#
# NAGA SIS Evaluation Environment Deployment Script
# Enhanced deployment for evaluation.pucsr.edu.kh with debugging capabilities
# 
# Usage: ./deploy-evaluation.sh [--local|--remote] [server-ip-or-domain] [remote-user]
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.evaluation.yml"
ENV_DIR=".envs/.evaluation"

# Default values
MODE="remote"
SERVER="evaluation.pucsr.edu.kh"
REMOTE_USER="ubuntu"
REMOTE_PATH="/opt/naga-evaluation"

# Functions
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

generate_secret() {
    if command -v openssl &> /dev/null; then
        openssl rand -hex 32
    else
        python3 -c 'import secrets; print(secrets.token_urlsafe(50))'
    fi
}

check_prerequisites() {
    log "Checking prerequisites..."
    
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed"
        exit 1
    fi

    if ! command -v docker compose &> /dev/null; then
        error "Docker Compose is not installed"
        exit 1
    fi

    if [ ! -f "$COMPOSE_FILE" ]; then
        error "Docker compose file not found: $COMPOSE_FILE"
        exit 1
    fi

    log "Prerequisites check passed ✓"
}

setup_local_environment() {
    log "Setting up local evaluation environment..."
    
    # Create directories
    mkdir -p "$ENV_DIR" logs monitoring/prometheus monitoring/grafana/datasources monitoring/grafana/dashboards monitoring/pgadmin
    
    # Generate secrets if needed
    if [ -f "$ENV_DIR/.django" ] && grep -q "!!!SET DJANGO_SECRET_KEY!!!" "$ENV_DIR/.django"; then
        warn "Generating Django secret key..."
        DJANGO_SECRET=$(generate_secret)
        sed -i.bak "s/DJANGO_SECRET_KEY=!!!SET DJANGO_SECRET_KEY!!!/DJANGO_SECRET_KEY=$DJANGO_SECRET/" "$ENV_DIR/.django"
        rm "$ENV_DIR/.django.bak" 2>/dev/null || true
    fi
    
    if [ -f "$ENV_DIR/.postgres" ] && grep -q "!!!SET SECURE POSTGRES PASSWORD!!!" "$ENV_DIR/.postgres"; then
        warn "Generating PostgreSQL password..."
        POSTGRES_PASSWORD=$(generate_secret | cut -c1-16)
        sed -i.bak "s/POSTGRES_PASSWORD=!!!SET SECURE POSTGRES PASSWORD!!!/POSTGRES_PASSWORD=$POSTGRES_PASSWORD/" "$ENV_DIR/.postgres"
        sed -i.bak "s/DATABASE_URL=postgres:\/\/!!!DB_USER!!!:!!!DB_PASS!!!@postgres:5432\/!!!DB_NAME!!!/DATABASE_URL=postgres:\/\/naga_evaluation_user:$POSTGRES_PASSWORD@postgres:5432\/naga_evaluation/" "$ENV_DIR/.django"
        rm "$ENV_DIR/.postgres.bak" "$ENV_DIR/.django.bak" 2>/dev/null || true
        
        # Update monitoring configurations
        if [ -f "monitoring/grafana/datasources/datasources.yml" ]; then
            sed -i.bak "s/password: \"!!!SET SECURE POSTGRES PASSWORD!!!\"/password: \"$POSTGRES_PASSWORD\"/" "monitoring/grafana/datasources/datasources.yml"
            rm "monitoring/grafana/datasources/datasources.yml.bak" 2>/dev/null || true
        fi
    fi
    
    log "Local environment setup completed ✓"
}

deploy_local() {
    log "🚀 Starting local evaluation environment..."
    
    check_prerequisites
    setup_local_environment
    
    # Pull base images first
    log "📦 Pulling base Docker images..."
    docker pull postgres:15-alpine
    docker pull redis:8.2-alpine  
    docker pull nginx:1.25-alpine
    docker pull louislam/uptime-kuma:1
    docker pull netdata/netdata:latest
    docker pull prom/prometheus:latest
    docker pull grafana/grafana:latest
    docker pull dpage/pgadmin4:latest
    docker pull axllent/mailpit:latest
    
    # Build custom images
    log "🔨 Building evaluation images..."
    docker compose -f "$COMPOSE_FILE" build --no-cache django nginx
    
    # Start core services first
    log "🐳 Starting core services..."
    docker compose -f "$COMPOSE_FILE" up -d postgres redis
    sleep 20
    
    # Start application
    log "🚀 Starting Django application..."
    docker compose -f "$COMPOSE_FILE" up -d django dramatiq nginx
    sleep 30
    
    # Start monitoring and debugging tools
    log "📊 Starting monitoring services..."
    docker compose -f "$COMPOSE_FILE" up -d uptime-kuma netdata prometheus grafana pgadmin mailpit healthcheck
    
    # Show status
    show_local_status
    
    log "✅ Local evaluation environment started successfully!"
}

deploy_remote() {
    log "🚀 Deploying Naga SIS Evaluation Environment to $SERVER"

    # Step 1: Rsync code to server
    log "📦 Syncing code to server..."
    rsync -avz --delete \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='data/legacy/' \
        --exclude='media/photos/' \
        --exclude='.git/' \
        --exclude='node_modules/' \
        --exclude='htmlcov/' \
        --exclude='*.log' \
        --exclude='test.db' \
        --exclude='logs/' \
        --exclude='dist/' \
        ./ $REMOTE_USER@$SERVER:$REMOTE_PATH/

    # Step 2: Setup environment on server
    log "⚙️ Setting up environment on server..."
    ssh $REMOTE_USER@$SERVER bash << ENDSSH
set -e
cd $REMOTE_PATH

# Generate secrets if they don't exist
if [ -f "$ENV_DIR/.django" ] && grep -q "!!!SET DJANGO_SECRET_KEY!!!" "$ENV_DIR/.django"; then
    echo "Generating Django secret key..."
    DJANGO_SECRET=\$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')
    sed -i "s/DJANGO_SECRET_KEY=!!!SET DJANGO_SECRET_KEY!!!/DJANGO_SECRET_KEY=\$DJANGO_SECRET/" "$ENV_DIR/.django"
fi

if [ -f "$ENV_DIR/.postgres" ] && grep -q "!!!SET SECURE POSTGRES PASSWORD!!!" "$ENV_DIR/.postgres"; then
    echo "Generating PostgreSQL password..."
    POSTGRES_PASSWORD=\$(openssl rand -base64 16 | tr -d '=+/')
    sed -i "s/POSTGRES_PASSWORD=!!!SET SECURE POSTGRES PASSWORD!!!/POSTGRES_PASSWORD=\$POSTGRES_PASSWORD/" "$ENV_DIR/.postgres"
    sed -i "s/DATABASE_URL=postgres:\/\/!!!DB_USER!!!:!!!DB_PASS!!!@postgres:5432\/!!!DB_NAME!!!/DATABASE_URL=postgres:\/\/naga_evaluation_user:\$POSTGRES_PASSWORD@postgres:5432\/naga_evaluation/" "$ENV_DIR/.django"
    
    # Update monitoring configs
    if [ -f "monitoring/grafana/datasources/datasources.yml" ]; then
        sed -i "s/password: \"!!!SET SECURE POSTGRES PASSWORD!!!\"/password: \"\$POSTGRES_PASSWORD\"/" "monitoring/grafana/datasources/datasources.yml"
    fi
fi

# Ensure docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

# Pull base images to speed up build
echo "📦 Pulling base images..."
docker pull postgres:15-alpine
docker pull redis:8.2-alpine
docker pull nginx:1.25-alpine
docker pull python:3.13.7-slim-trixie

echo "✅ Environment setup complete"
ENDSSH

    # Step 3: Deploy services
    log "🐳 Building and starting Docker services..."
    ssh $REMOTE_USER@$SERVER bash << ENDSSH
set -e
cd $REMOTE_PATH

# Build images
echo "🔨 Building evaluation images..."
docker compose -f $COMPOSE_FILE build --no-cache

# Start database and cache first
echo "🗄️ Starting database and cache..."
docker compose -f $COMPOSE_FILE up -d postgres redis

# Wait for database
echo "⏳ Waiting for database to be ready..."
sleep 30

# Check if database needs initial setup
DB_EXISTS=\$(docker compose -f $COMPOSE_FILE exec -T postgres psql -U naga_evaluation_user -d naga_evaluation -c "SELECT 1;" 2>/dev/null | wc -l)
if [ "\$DB_EXISTS" -lt 3 ]; then
    echo "📊 Running initial database migrations..."
    docker compose -f $COMPOSE_FILE run --rm django python manage.py migrate
    
    echo "👤 Creating evaluation superuser..."
    docker compose -f $COMPOSE_FILE run --rm django python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@evaluation.pucsr.edu.kh', 'evaluation2024')
    print('Superuser created successfully')
else:
    print('Superuser already exists')
"
else
    echo "📊 Database already initialized"
fi

# Start all services
echo "🚀 Starting all services..."
docker compose -f $COMPOSE_FILE up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 60

# Show status
docker compose -f $COMPOSE_FILE ps

echo "✅ Remote deployment complete!"
ENDSSH

    show_remote_status
}

show_local_status() {
    log "Service Status:"
    docker compose -f "$COMPOSE_FILE" ps
    
    echo ""
    info "Local Access URLs:"
    info "  Main Application: http://localhost/"
    info "  Django Admin: http://localhost/admin-evaluation/"
    info "  Uptime Monitoring: http://localhost:3001/"
    info "  System Metrics: http://localhost:19999/"
    info "  Prometheus: http://localhost:9090/"
    info "  Grafana: http://localhost:3000/ (admin/evaluation2024)"
    info "  Database Admin: http://localhost:8080/ (admin@evaluation.pucsr.edu.kh/evaluation2024)"
    info "  Email Testing: http://localhost:8025/"
}

show_remote_status() {
    log "🎉 Evaluation environment deployed successfully to $SERVER!"
    echo ""
    info "🌐 Production URLs:"
    info "  Main Application: https://evaluation.pucsr.edu.kh/"
    info "  Django Admin: https://evaluation.pucsr.edu.kh/admin-evaluation/"
    info "  Uptime Monitoring: https://uptime.evaluation.pucsr.edu.kh/"
    info "  System Metrics: https://netdata.evaluation.pucsr.edu.kh/"
    info "  Prometheus: https://prometheus.evaluation.pucsr.edu.kh/"
    info "  Grafana: https://grafana.evaluation.pucsr.edu.kh/ (admin/evaluation2024)"
    info "  Database Admin: https://pgadmin.evaluation.pucsr.edu.kh/ (admin@evaluation.pucsr.edu.kh/evaluation2024)"
    info "  Email Testing: https://mailpit.evaluation.pucsr.edu.kh/"
    echo ""
    info "📋 Quick remote commands:"
    info "  Check status: ssh $REMOTE_USER@$SERVER 'cd $REMOTE_PATH && docker compose -f $COMPOSE_FILE ps'"
    info "  View logs:    ssh $REMOTE_USER@$SERVER 'cd $REMOTE_PATH && docker compose -f $COMPOSE_FILE logs -f django'"
    info "  Restart:      ssh $REMOTE_USER@$SERVER 'cd $REMOTE_PATH && docker compose -f $COMPOSE_FILE restart'"
}

show_help() {
    echo "NAGA SIS Evaluation Environment Deployment Script"
    echo ""
    echo "Usage: $0 [MODE] [SERVER] [USER]"
    echo ""
    echo "Modes:"
    echo "  --local       Deploy locally for testing (default if no server specified)"
    echo "  --remote      Deploy to remote server (default if server specified)"
    echo ""
    echo "Examples:"
    echo "  $0 --local                                    # Local deployment"
    echo "  $0 --remote evaluation.pucsr.edu.kh ubuntu   # Remote deployment"
    echo "  $0 evaluation.pucsr.edu.kh                   # Remote deployment (user defaults to ubuntu)"
    echo ""
    echo "Remote deployment requires SSH access to the target server."
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --local)
            MODE="local"
            shift
            ;;
        --remote)
            MODE="remote"
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            if [[ "$1" != --* ]]; then
                SERVER="$1"
                MODE="remote"
                shift
                if [[ $# -gt 0 && "$1" != --* ]]; then
                    REMOTE_USER="$1"
                    shift
                fi
            else
                error "Unknown option: $1"
                show_help
                exit 1
            fi
            ;;
    esac
done

# If no server specified but mode is remote, show help
if [[ "$MODE" == "remote" && "$SERVER" == "evaluation.pucsr.edu.kh" ]] && [[ $# -eq 0 ]]; then
    MODE="local"
fi

# Main execution
case "$MODE" in
    local)
        deploy_local
        ;;
    remote)
        deploy_remote
        ;;
    *)
        error "Invalid mode: $MODE"
        show_help
        exit 1
        ;;
esac