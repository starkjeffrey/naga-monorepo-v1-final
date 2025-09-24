# Naga SIS Deployment Guide

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Environment Setup](#environment-setup)
4. [Deployment Strategies](#deployment-strategies)
5. [Docker Deployment](#docker-deployment)
6. [Kubernetes Deployment](#kubernetes-deployment)
7. [Database Management](#database-management)
8. [Security Configuration](#security-configuration)
9. [Monitoring Setup](#monitoring-setup)
10. [Backup and Recovery](#backup-and-recovery)
11. [Troubleshooting](#troubleshooting)
12. [Maintenance](#maintenance)

## Overview

This guide provides comprehensive instructions for deploying the Naga Student Information System in various environments. The system supports multiple deployment strategies from simple Docker Compose to full Kubernetes orchestration.

## Prerequisites

### System Requirements

**Minimum Production Requirements:**
- CPU: 4 cores (8 recommended)
- RAM: 8GB (16GB recommended)
- Storage: 50GB SSD (100GB recommended)
- OS: Ubuntu 22.04 LTS or similar

**Software Requirements:**
- Docker 24.0+
- Docker Compose 2.20+
- Python 3.13.7+ (for management scripts)
- Node.js 18+ (for frontend builds)
- PostgreSQL client tools
- Git 2.40+

### Network Requirements

**Required Ports:**
- 80/443: HTTP/HTTPS traffic
- 5432: PostgreSQL (internal)
- 6379: Redis (internal)
- 9090: Prometheus (monitoring)
- 3000: Grafana (monitoring)

## Environment Setup

### 1. Clone Repository

```bash
# Clone the repository
git clone https://github.com/naga-sis/naga-monorepo.git
cd naga-monorepo

# Create required directories
mkdir -p data/{postgres,redis,media,static,backups}
mkdir -p logs/{nginx,django,postgres}
```

### 2. Environment Configuration

Create environment files for each deployment:

**Production (.env.production)**
```bash
# Django Settings
DJANGO_SETTINGS_MODULE=config.settings.production
SECRET_KEY=your-very-secure-secret-key-here
DEBUG=False
ALLOWED_HOSTS=naga-sis.edu.kh,www.naga-sis.edu.kh

# Database
DATABASE_URL=postgresql://naga_user:secure_password@postgres:5432/naga_production
POSTGRES_DB=naga_production
POSTGRES_USER=naga_user
POSTGRES_PASSWORD=secure_password

# Redis
REDIS_URL=redis://redis:6379/0

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=noreply@naga-sis.edu.kh
EMAIL_HOST_PASSWORD=email_password

# External Services
KEYCLOAK_URL=https://auth.naga-sis.edu.kh
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id

# Storage
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_STORAGE_BUCKET_NAME=naga-sis-media
```

**Staging (.env.staging)**
```bash
# Similar to production but with staging-specific values
DJANGO_SETTINGS_MODULE=config.settings.staging
ALLOWED_HOSTS=staging.naga-sis.edu.kh
DATABASE_URL=postgresql://naga_user:password@postgres:5432/naga_staging
```

### 3. SSL Certificates

```bash
# Using Let's Encrypt with Certbot
sudo apt-get update
sudo apt-get install certbot python3-certbot-nginx

# Generate certificates
sudo certbot certonly --standalone -d naga-sis.edu.kh -d www.naga-sis.edu.kh

# Copy certificates to project
sudo cp /etc/letsencrypt/live/naga-sis.edu.kh/fullchain.pem ./nginx/certs/
sudo cp /etc/letsencrypt/live/naga-sis.edu.kh/privkey.pem ./nginx/certs/
```

## Deployment Strategies

### Strategy Comparison

| Strategy | Use Case | Complexity | Scalability | Cost |
|----------|----------|------------|-------------|------|
| Docker Compose | Small institutions, POC | Low | Limited | Low |
| Docker Swarm | Medium institutions | Medium | Good | Medium |
| Kubernetes | Large institutions, multi-campus | High | Excellent | High |
| Managed Cloud | Any size, low maintenance | Low | Excellent | Variable |

## Docker Deployment

### 1. Production Docker Compose

```yaml
# docker-compose.production.yml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/certs:/etc/nginx/certs
      - static_volume:/app/staticfiles
      - media_volume:/app/mediafiles
    depends_on:
      - django

  django:
    build:
      context: ./backend
      dockerfile: Dockerfile.production
    command: gunicorn config.wsgi:application --bind 0.0.0.0:8000
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/mediafiles
    env_file:
      - .env.production
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:16-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/postgres/backup.sh:/usr/local/bin/backup
    env_file:
      - .env.production
    command: >
      postgres
      -c max_connections=200
      -c shared_buffers=256MB
      -c effective_cache_size=1GB

  redis:
    image: redis:8.2-alpine
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

  dramatiq:
    build:
      context: ./backend
      dockerfile: Dockerfile.production
    command: python manage.py rundramatiq
    env_file:
      - .env.production
    depends_on:
      - postgres
      - redis

volumes:
  postgres_data:
  redis_data:
  static_volume:
  media_volume:
```

### 2. Deploy with Docker Compose

```bash
# Build images
docker compose -f docker-compose.production.yml build

# Start services
docker compose -f docker-compose.production.yml up -d

# Run migrations
docker compose -f docker-compose.production.yml exec django python manage.py migrate

# Collect static files
docker compose -f docker-compose.production.yml exec django python manage.py collectstatic --noinput

# Create superuser
docker compose -f docker-compose.production.yml exec django python manage.py createsuperuser

# Check status
docker compose -f docker-compose.production.yml ps
```

### 3. Update Deployment

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker compose -f docker-compose.production.yml build django
docker compose -f docker-compose.production.yml up -d --no-deps django dramatiq

# Run migrations if needed
docker compose -f docker-compose.production.yml exec django python manage.py migrate
```

## Kubernetes Deployment

### 1. Kubernetes Manifests

**namespace.yaml**
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: naga-sis
```

**django-deployment.yaml**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: django
  namespace: naga-sis
spec:
  replicas: 3
  selector:
    matchLabels:
      app: django
  template:
    metadata:
      labels:
        app: django
    spec:
      containers:
      - name: django
        image: naga-sis/django:latest
        ports:
        - containerPort: 8000
        env:
        - name: DJANGO_SETTINGS_MODULE
          value: "config.settings.production"
        envFrom:
        - secretRef:
            name: django-secrets
        volumeMounts:
        - name: media
          mountPath: /app/media
        livenessProbe:
          httpGet:
            path: /api/health/
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/health/
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: media
        persistentVolumeClaim:
          claimName: media-pvc
```

**postgres-statefulset.yaml**
```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: naga-sis
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:16-alpine
        ports:
        - containerPort: 5432
        env:
        - name: POSTGRES_DB
          valueFrom:
            secretKeyRef:
              name: postgres-secrets
              key: database
        - name: POSTGRES_USER
          valueFrom:
            secretKeyRef:
              name: postgres-secrets
              key: username
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-secrets
              key: password
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 50Gi
```

### 2. Deploy to Kubernetes

```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Create secrets
kubectl create secret generic django-secrets \
  --from-env-file=.env.production \
  -n naga-sis

# Deploy database
kubectl apply -f k8s/postgres-statefulset.yaml
kubectl apply -f k8s/postgres-service.yaml

# Deploy Redis
kubectl apply -f k8s/redis-deployment.yaml
kubectl apply -f k8s/redis-service.yaml

# Deploy Django
kubectl apply -f k8s/django-deployment.yaml
kubectl apply -f k8s/django-service.yaml

# Deploy Ingress
kubectl apply -f k8s/ingress.yaml

# Check status
kubectl get pods -n naga-sis
```

### 3. Scaling

```bash
# Scale Django pods
kubectl scale deployment django --replicas=5 -n naga-sis

# Autoscaling
kubectl autoscale deployment django \
  --min=3 --max=10 \
  --cpu-percent=80 \
  -n naga-sis
```

## Database Management

### 1. Initial Setup

```bash
# Create database and user
docker compose exec postgres psql -U postgres <<EOF
CREATE USER naga_user WITH PASSWORD 'secure_password';
CREATE DATABASE naga_production OWNER naga_user;
GRANT ALL PRIVILEGES ON DATABASE naga_production TO naga_user;
EOF

# Run migrations
docker compose exec django python manage.py migrate

# Load initial data
docker compose exec django python manage.py loaddata initial_data.json
```

### 2. Database Optimization

```sql
-- Performance tuning
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
ALTER SYSTEM SET random_page_cost = 1.1;

-- Create indexes for common queries
CREATE INDEX idx_student_status ON people_person(is_student, status);
CREATE INDEX idx_enrollment_term ON enrollment_enrollment(term_id, student_id);
CREATE INDEX idx_payment_date ON finance_payment(payment_date, status);

-- Vacuum and analyze
VACUUM ANALYZE;
```

### 3. Connection Pooling

```python
# settings/production.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'naga_production',
        'USER': 'naga_user',
        'PASSWORD': 'secure_password',
        'HOST': 'postgres',
        'PORT': '5432',
        'CONN_MAX_AGE': 600,  # Connection pooling
        'OPTIONS': {
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000'  # 30 seconds
        }
    }
}
```

## Security Configuration

### 1. Django Security Settings

```python
# settings/production.py
# Security settings
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True

# Content Security Policy
CSP_DEFAULT_SRC = ("'self'",)
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'", 'https://fonts.googleapis.com')
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'", 'https://www.google-analytics.com')
CSP_FONT_SRC = ("'self'", 'https://fonts.gstatic.com')
CSP_IMG_SRC = ("'self'", 'data:', 'https:')
```

### 2. Nginx Security Headers

```nginx
# nginx.conf
server {
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';" always;
    
    # Hide nginx version
    server_tokens off;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;
}
```

### 3. Firewall Configuration

```bash
# UFW firewall setup
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# Fail2ban for brute force protection
sudo apt-get install fail2ban
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

## Monitoring Setup

### 1. Deploy Monitoring Stack

```bash
# Deploy monitoring stack
docker compose -f docker-compose.monitoring.yml up -d

# Services available at:
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3000 (admin/admin)
# - Alertmanager: http://localhost:9093
```

### 2. Configure Prometheus

```yaml
# prometheus/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'django'
    static_configs:
      - targets: ['django:8000']
    metrics_path: '/metrics/'

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']

  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']
```

### 3. Setup Alerts

```yaml
# prometheus/alerts.yml
groups:
  - name: django
    rules:
      - alert: HighErrorRate
        expr: rate(django_http_responses_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: High error rate detected
          
      - alert: SlowResponseTime
        expr: django_http_response_time_seconds{quantile="0.95"} > 2
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: Slow response times detected
          
      - alert: DatabaseConnectionFailure
        expr: django_db_connections_active == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: Database connection failure
```

## Backup and Recovery

### 1. Automated Backups

```bash
#!/bin/bash
# scripts/backup.sh

# Configuration
BACKUP_DIR="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
S3_BUCKET="naga-sis-backups"

# Database backup
docker compose exec -T postgres pg_dump -U naga_user naga_production | \
  gzip > "$BACKUP_DIR/db_backup_$TIMESTAMP.sql.gz"

# Media files backup
tar -czf "$BACKUP_DIR/media_backup_$TIMESTAMP.tar.gz" -C /app/media .

# Upload to S3
aws s3 cp "$BACKUP_DIR/db_backup_$TIMESTAMP.sql.gz" "s3://$S3_BUCKET/database/"
aws s3 cp "$BACKUP_DIR/media_backup_$TIMESTAMP.tar.gz" "s3://$S3_BUCKET/media/"

# Clean old local backups (keep 7 days)
find $BACKUP_DIR -name "*.gz" -mtime +7 -delete
```

### 2. Backup Schedule

```bash
# Add to crontab
# Daily database backup at 2 AM
0 2 * * * /path/to/scripts/backup.sh

# Weekly full backup on Sunday at 3 AM
0 3 * * 0 /path/to/scripts/full-backup.sh

# Hourly transaction log backup
0 * * * * /path/to/scripts/transaction-backup.sh
```

### 3. Recovery Procedures

```bash
# Restore database from backup
gunzip < db_backup_20240115_020000.sql.gz | \
  docker compose exec -T postgres psql -U naga_user naga_production

# Restore media files
tar -xzf media_backup_20240115_020000.tar.gz -C /app/media

# Point-in-time recovery
docker compose exec postgres pg_restore \
  --dbname=naga_production \
  --verbose \
  --clean \
  --no-owner \
  backup_file.dump
```

## Troubleshooting

### Common Issues

#### 1. Database Connection Errors

```bash
# Check PostgreSQL status
docker compose exec postgres pg_isready

# Check connections
docker compose exec postgres psql -U naga_user -c "SELECT count(*) FROM pg_stat_activity;"

# Reset connections
docker compose restart django dramatiq
```

#### 2. Memory Issues

```bash
# Check memory usage
docker stats

# Increase memory limits
docker compose down
# Edit docker-compose.yml to add memory limits
# mem_limit: 2g
docker compose up -d
```

#### 3. Slow Performance

```bash
# Check slow queries
docker compose exec postgres psql -U naga_user -c "
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;"

# Vacuum database
docker compose exec postgres vacuumdb -U naga_user -d naga_production -z

# Reindex
docker compose exec postgres reindexdb -U naga_user -d naga_production
```

### Debug Mode

```bash
# Enable debug logging
docker compose exec django python manage.py shell
>>> import logging
>>> logging.basicConfig(level=logging.DEBUG)

# Check Django debug toolbar
# Add to INTERNAL_IPS in settings
INTERNAL_IPS = ['127.0.0.1', '10.0.0.0/8']
```

## Maintenance

### 1. Regular Maintenance Tasks

```bash
# Weekly maintenance script
#!/bin/bash

# Update packages
docker compose exec django pip install --upgrade -r requirements.txt

# Clean old sessions
docker compose exec django python manage.py clearsessions

# Clean old logs
find /logs -name "*.log" -mtime +30 -delete

# Optimize database
docker compose exec postgres vacuumdb -U naga_user -d naga_production -z

# Check disk space
df -h
```

### 2. Updates and Patches

```bash
# System updates
sudo apt-get update
sudo apt-get upgrade

# Docker updates
docker compose pull
docker compose up -d

# Django security updates
docker compose exec django pip install --upgrade django
docker compose exec django python manage.py check --deploy
```

### 3. Performance Monitoring

```bash
# Monitor resource usage
htop
iotop
nethogs

# Check application metrics
curl http://localhost:8000/metrics/

# Database performance
docker compose exec postgres psql -U naga_user -c "\
  SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
  FROM pg_tables 
  ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC 
  LIMIT 10;"
```

## Production Checklist

Before going live, ensure:

- [ ] SSL certificates installed and auto-renewal configured
- [ ] Environment variables properly set
- [ ] Database backed up and recovery tested
- [ ] Monitoring and alerting configured
- [ ] Security headers configured
- [ ] Rate limiting enabled
- [ ] Error tracking (Sentry) configured
- [ ] Log rotation configured
- [ ] Firewall rules configured
- [ ] Automated backups scheduled
- [ ] Health checks passing
- [ ] Load testing completed
- [ ] Disaster recovery plan documented
- [ ] Team trained on deployment procedures
- [ ] Documentation up to date