# Staff-Web V2 Production Deployment Guide

Complete production deployment documentation for the Staff-Web V2 system with React frontend and Django backend.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Initial Setup](#initial-setup)
4. [Configuration](#configuration)
5. [Deployment Process](#deployment-process)
6. [Monitoring and Logging](#monitoring-and-logging)
7. [Security Configuration](#security-configuration)
8. [Backup and Recovery](#backup-and-recovery)
9. [Maintenance Procedures](#maintenance-procedures)
10. [Troubleshooting](#troubleshooting)

## Overview

The Staff-Web V2 system is a comprehensive production deployment that includes:

- **React Frontend**: Modern TypeScript-based web application
- **Django Backend**: Python-based API and administration
- **PostgreSQL**: Production database with optimization
- **Redis**: Caching and session storage
- **Celery**: Background task processing
- **Traefik**: Reverse proxy with SSL termination
- **Monitoring Stack**: Prometheus, Grafana, Loki, Uptime Kuma
- **Security**: Fail2ban, rate limiting, security headers

## Prerequisites

### System Requirements

**Minimum Server Specifications:**
- CPU: 4 cores
- RAM: 8GB
- Storage: 100GB SSD
- Network: 1Gbps connection

**Recommended Server Specifications:**
- CPU: 8 cores
- RAM: 16GB
- Storage: 200GB SSD with backup storage
- Network: 1Gbps connection with redundancy

### Software Requirements

```bash
# Required software
- Docker 24.0+
- Docker Compose 2.20+
- Git 2.30+
- OpenSSL 1.1.1+

# Optional but recommended
- fail2ban 0.11+
- htop
- iotop
- nethogs
```

### Network Requirements

- Domain name with DNS control
- SSL certificate (Let's Encrypt automated)
- Firewall configuration (ports 80, 443, 22)
- SMTP server for notifications (optional)

## Initial Setup

### 1. Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install additional tools
sudo apt install -y git htop iotop nethogs fail2ban ufw
```

### 2. Firewall Configuration

```bash
# Configure UFW firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

### 3. Clone Repository

```bash
# Clone the repository
git clone https://github.com/your-org/naga-monorepo-v1-final.git
cd naga-monorepo-v1-final

# Create necessary directories
sudo mkdir -p /backups/staff-web-v2
sudo chown $USER:$USER /backups/staff-web-v2
```

## Configuration

### 1. Environment Configuration

```bash
# Copy environment templates
cp .env.production.example .env.production
cp .envs/.production/.django.example .envs/.production/.django
cp .envs/.production/.postgres.example .envs/.production/.postgres
cp staff-web/.env.production.example staff-web/.env.production
```

### 2. Environment Variables

Edit `.env.production`:

```bash
# Domain Configuration
DOMAIN_NAME=yourdomain.com
ACME_EMAIL=admin@yourdomain.com

# Frontend Configuration
VITE_API_BASE_URL=https://api.yourdomain.com
VITE_WS_URL=wss://api.yourdomain.com

# Database Configuration
POSTGRES_DB=naga_production
POSTGRES_USER=naga_user
POSTGRES_PASSWORD=your-super-secure-postgres-password-here

# Django Configuration
DJANGO_SECRET_KEY=your-super-secret-django-key-here-make-it-long-and-random-50-chars-minimum
DJANGO_DEBUG=False

# Security Configuration
SECURITY_HEADERS_ENABLED=true
RATE_LIMITING_ENABLED=true

# Monitoring Configuration
GRAFANA_ADMIN_PASSWORD=your-secure-grafana-password
```

### 3. Django Configuration

Edit `.envs/.production/.django`:

```bash
# Django Core Settings
DJANGO_SECRET_KEY=your-super-secret-django-key-here
DJANGO_ALLOWED_HOSTS=yourdomain.com,api.yourdomain.com,staff.yourdomain.com

# Database Configuration
DATABASE_URL=postgres://naga_user:password@postgres:5432/naga_production

# Security Settings
DJANGO_SECURE_SSL_REDIRECT=True
DJANGO_SECURE_HSTS_SECONDS=31536000
DJANGO_SESSION_COOKIE_SECURE=True
DJANGO_CSRF_COOKIE_SECURE=True

# CORS Configuration
DJANGO_CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://staff.yourdomain.com
```

### 4. PostgreSQL Configuration

Edit `.envs/.production/.postgres`:

```bash
POSTGRES_HOST=postgres
POSTGRES_DB=naga_production
POSTGRES_USER=naga_user
POSTGRES_PASSWORD=your-super-secure-postgres-password-here
```

## Deployment Process

### 1. Automated Deployment

The recommended deployment method uses the automated script:

```bash
# Make deployment script executable
chmod +x scripts/deployment/deploy-staff-web-v2.sh

# Full production deployment
./scripts/deployment/deploy-staff-web-v2.sh --environment prod

# Quick deployment (development/testing)
./scripts/deployment/deploy-staff-web-v2.sh --quick --skip-backup
```

### 2. Manual Deployment Steps

If you need to deploy manually or understand the process:

```bash
# 1. Build and pull images
docker-compose -f docker-compose.staff-web-production.yml pull
docker-compose -f docker-compose.staff-web-production.yml build

# 2. Start core services first
docker-compose -f docker-compose.staff-web-production.yml up -d postgres redis

# 3. Wait for database to be ready
sleep 30

# 4. Run database migrations
docker-compose -f docker-compose.staff-web-production.yml exec django python manage.py migrate

# 5. Collect static files
docker-compose -f docker-compose.staff-web-production.yml exec django python manage.py collectstatic --no-input

# 6. Start all services
docker-compose -f docker-compose.staff-web-production.yml up -d

# 7. Verify deployment
./scripts/maintenance/health-check.sh
```

### 3. Zero-Downtime Deployment

For zero-downtime deployments:

```bash
# 1. Deploy new version alongside existing
docker-compose -f docker-compose.staff-web-production.yml up -d --scale django=2 --scale staff-web=2

# 2. Wait for health checks
./scripts/maintenance/health-check.sh --critical-only

# 3. Remove old instances
docker-compose -f docker-compose.staff-web-production.yml up -d --scale django=1 --scale staff-web=1
```

## Monitoring and Logging

### 1. Access Monitoring Services

- **Grafana**: https://grafana.yourdomain.com
- **Prometheus**: https://prometheus.yourdomain.com
- **Uptime Kuma**: https://uptime.yourdomain.com
- **Traefik Dashboard**: https://traefik.yourdomain.com (if enabled)

### 2. Default Grafana Dashboards

The system includes pre-configured dashboards for:
- System metrics (CPU, memory, disk)
- Application performance
- Database performance
- Security events
- Business metrics

### 3. Log Access

```bash
# View application logs
docker-compose -f docker-compose.staff-web-production.yml logs -f django
docker-compose -f docker-compose.staff-web-production.yml logs -f staff-web

# View all service logs
docker-compose -f docker-compose.staff-web-production.yml logs -f

# View specific timeframe
docker-compose -f docker-compose.staff-web-production.yml logs --since="2024-01-01T00:00:00" django
```

### 4. Health Monitoring

```bash
# Run comprehensive health check
./scripts/maintenance/health-check.sh --verbose

# JSON output for monitoring systems
./scripts/maintenance/health-check.sh --json

# Critical services only (fast check)
./scripts/maintenance/health-check.sh --critical-only
```

## Security Configuration

### 1. SSL/TLS Configuration

SSL certificates are automatically managed by Traefik and Let's Encrypt:

```yaml
# Automatic certificate generation for configured domains
- traefik.http.routers.service.tls.certresolver=letsencrypt
```

### 2. Security Headers

Security headers are automatically applied via Traefik and Nginx:

- Strict-Transport-Security
- Content-Security-Policy
- X-Frame-Options
- X-Content-Type-Options
- X-XSS-Protection

### 3. Rate Limiting

Rate limiting is configured at multiple levels:

```bash
# API endpoints: 10 requests/second
# Login endpoints: 5 requests/minute
# Static files: 50 requests/second
# General requests: 20 requests/second
```

### 4. Fail2ban Configuration

```bash
# Install and configure fail2ban
sudo cp security/fail2ban/jail.local /etc/fail2ban/jail.local
sudo cp security/fail2ban/filter.d/nginx-docker.conf /etc/fail2ban/filter.d/
sudo systemctl restart fail2ban

# Monitor fail2ban status
sudo fail2ban-client status
```

## Backup and Recovery

### 1. Automated Backups

```bash
# Full system backup
./scripts/backup/backup-system.sh --type full --compress --remote

# Database only backup
./scripts/backup/backup-system.sh --type database

# Files only backup
./scripts/backup/backup-system.sh --type files
```

### 2. Backup Schedule

Set up automated backups using cron:

```bash
# Edit crontab
crontab -e

# Add backup schedules
# Daily database backup at 2 AM
0 2 * * * /path/to/scripts/backup/backup-system.sh --type database --compress

# Weekly full backup on Sundays at 3 AM
0 3 * * 0 /path/to/scripts/backup/backup-system.sh --type full --compress --remote

# Monthly configuration backup
0 4 1 * * /path/to/scripts/backup/backup-system.sh --type files --compress --remote
```

### 3. Recovery Procedures

```bash
# Emergency rollback to previous version
./scripts/deployment/rollback.sh

# Rollback to specific backup
./scripts/deployment/rollback.sh --backup-name staff_web_v2_backup_20240327_143022

# Force rollback without confirmation
./scripts/deployment/rollback.sh --force
```

## Maintenance Procedures

### 1. Regular Maintenance Tasks

**Daily:**
- Monitor system health
- Check application logs
- Verify backup completion

**Weekly:**
- Review security logs
- Update system packages
- Check disk space usage
- Review performance metrics

**Monthly:**
- Security audit
- Dependency updates
- Certificate renewal check
- Backup recovery testing

### 2. System Updates

```bash
# Update Docker images
docker-compose -f docker-compose.staff-web-production.yml pull

# Update system packages
sudo apt update && sudo apt upgrade -y

# Restart services if needed
docker-compose -f docker-compose.staff-web-production.yml restart
```

### 3. Database Maintenance

```bash
# Database vacuum and analyze
docker-compose -f docker-compose.staff-web-production.yml exec postgres psql -U postgres -d naga_production -c "VACUUM ANALYZE;"

# Check database performance
docker-compose -f docker-compose.staff-web-production.yml exec postgres psql -U postgres -d naga_production -c "SELECT * FROM pg_stat_user_tables;"

# Reindex if needed
docker-compose -f docker-compose.staff-web-production.yml exec postgres psql -U postgres -d naga_production -c "REINDEX DATABASE naga_production;"
```

## Troubleshooting

### 1. Common Issues

**Service Won't Start:**
```bash
# Check service status
docker-compose -f docker-compose.staff-web-production.yml ps

# View service logs
docker-compose -f docker-compose.staff-web-production.yml logs service-name

# Restart specific service
docker-compose -f docker-compose.staff-web-production.yml restart service-name
```

**Database Connection Issues:**
```bash
# Check PostgreSQL status
docker-compose -f docker-compose.staff-web-production.yml exec postgres pg_isready

# Check database connections
docker-compose -f docker-compose.staff-web-production.yml exec postgres psql -U postgres -l

# Reset database connections
docker-compose -f docker-compose.staff-web-production.yml restart postgres
```

**SSL Certificate Issues:**
```bash
# Check certificate status
docker-compose -f docker-compose.staff-web-production.yml logs traefik | grep -i cert

# Force certificate renewal
docker-compose -f docker-compose.staff-web-production.yml restart traefik
```

### 2. Performance Issues

**High CPU Usage:**
```bash
# Check container resource usage
docker stats

# Check specific service performance
docker-compose -f docker-compose.staff-web-production.yml top django
```

**High Memory Usage:**
```bash
# Check memory usage
free -h

# Check Docker memory usage
docker system df

# Clean up unused resources
docker system prune -f
```

**Database Performance:**
```bash
# Check slow queries
docker-compose -f docker-compose.staff-web-production.yml exec postgres psql -U postgres -d naga_production -c "SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"

# Check database locks
docker-compose -f docker-compose.staff-web-production.yml exec postgres psql -U postgres -d naga_production -c "SELECT * FROM pg_locks WHERE NOT granted;"
```

### 3. Emergency Procedures

**Complete System Failure:**
```bash
# 1. Stop all services
docker-compose -f docker-compose.staff-web-production.yml down

# 2. Check system resources
df -h
free -h
top

# 3. Restart core services only
docker-compose -f docker-compose.staff-web-production.yml up -d postgres redis

# 4. Restore from backup if needed
./scripts/deployment/rollback.sh --force

# 5. Gradually restart other services
docker-compose -f docker-compose.staff-web-production.yml up -d django
docker-compose -f docker-compose.staff-web-production.yml up -d staff-web
```

**Data Corruption:**
```bash
# 1. Immediately stop application services
docker-compose -f docker-compose.staff-web-production.yml stop django staff-web celery-worker

# 2. Create emergency backup
./scripts/backup/backup-system.sh --type database --compress

# 3. Restore from last known good backup
./scripts/deployment/rollback.sh --backup-name last_known_good_backup

# 4. Verify data integrity
docker-compose -f docker-compose.staff-web-production.yml exec django python manage.py check
```

## Support and Contact

For technical support and questions:

- **Internal Documentation**: `/project-docs/`
- **Logs Location**: `/var/log/` and Docker container logs
- **Backup Location**: `/backups/staff-web-v2/`
- **Configuration**: `.envs/.production/`

## Version Information

- **Staff-Web V2**: Version 2.0.0
- **Django**: Version from requirements
- **React**: Version from package.json
- **PostgreSQL**: Version 16.0
- **Redis**: Version 7.2
- **Docker**: Required 24.0+
- **Docker Compose**: Required 2.20+

---

**Last Updated**: $(date +%Y-%m-%d)
**Document Version**: 1.0.0