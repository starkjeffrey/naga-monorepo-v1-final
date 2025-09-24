# Naga SIS - Systems Operations Manual

## Overview

This manual provides comprehensive operational guidance for the Naga Student Information System (SIS) monorepo. The system consists of a Django backend, Vue.js PWA frontend, comprehensive monitoring stack, and automated CI/CD pipeline.

## Architecture Overview

### System Components
- **Backend**: Django 5.2+ with django-ninja API
- **Frontend**: Vue 3 + Quasar PWA with Capacitor
- **Database**: PostgreSQL 16 with multi-environment support
- **Cache**: Redis 7 for sessions and background tasks
- **Task Queue**: Dramatiq for async processing
- **Monitoring**: Prometheus, Grafana, Alertmanager, Sentry
- **Build System**: Nx monorepo with affected builds
- **Infrastructure**: Docker containerization with multi-stage builds

### Environment Architecture
```
Production    → Blue-green deployment with health checks
Staging       → Pre-production testing environment
Evaluation     → Version of the system for end users so they can make comments (REAL DATA - CAUTION)
Local/Testing → Development and CI/CD testing (REAL DATA - CAUTION)
```

## 🤖🤖 Dual Claude Development Setup

### Overview: Two Claude Instances Working Together

This section provides step-by-step instructions for setting up and coordinating **two Claude instances** working simultaneously:
- **Backend Claude**: Django/API development
- **Frontend Claude**: Vue.js/PWA development

### Initial Workspace Setup

#### Step 1: Create Git Worktrees
```bash
# From your main repository directory
cd /Users/jeffreystark/PycharmProjects/naga-monorepo

# Create separate workspaces for each Claude
git worktree add ../naga-monorepo-backend main
git worktree add ../naga-monorepo-frontend main

# Create coordination directory
mkdir -p .claude-sessions
```

#### Step 2: Initialize Coordination System
```bash
# Create session coordination file
cat > .claude-sessions/active-sessions.json << 'EOF'
{
  "backend": {
    "claude_id": "",
    "workspace": "naga-monorepo-backend",
    "status": "inactive",
    "current_task": "",
    "last_activity": "",
    "files_locked": []
  },
  "frontend": {
    "claude_id": "",
    "workspace": "naga-monorepo-frontend",
    "status": "inactive",
    "current_task": "",
    "last_activity": "",
    "files_locked": []
  },
  "coordination": {
    "schema_update_available": false,
    "schema_integrated": true,
    "emergency_halt": false,
    "last_sync": ""
  }
}
EOF
```

### Starting Your Claude Instances

#### Backend Claude Initialization
**In Terminal 1** (Backend Claude workspace):
```bash
cd /Users/jeffreystark/PycharmProjects/naga-monorepo-backend
claude-code

# First message to Backend Claude:
"I am BACKEND-CLAUDE working on Django/API development. Please read CLAUDE.md for dual Claude coordination protocol and update the active-sessions.json file to mark yourself as active."
```

#### Frontend Claude Initialization
**In Terminal 2** (Frontend Claude workspace):
```bash
cd /Users/jeffreystark/PycharmProjects/naga-monorepo-frontend
claude-code

# First message to Frontend Claude:
"I am FRONTEND-CLAUDE working on Vue.js/PWA development. Please read CLAUDE.md for dual Claude coordination protocol and update the active-sessions.json file to mark yourself as active."
```

### Coordination Guidelines for You (The Human)

#### Task Assignment Strategy
- **Backend Claude**: Give tasks related to Django, API endpoints, database models, backend testing
- **Frontend Claude**: Give tasks related to Vue components, PWA features, UI/UX, frontend testing
- **Shared Tasks**: Coordinate these between both Claudes:
  - API schema changes (Backend starts, Frontend integrates)
  - Root-level configuration changes (package.json, nx.json)
  - Documentation updates affecting both sides

#### Communication Patterns

**For Backend Tasks:**
```
"Backend Claude: Please implement a new enrollment API endpoint with the following requirements..."
```

**For Frontend Tasks:**
```
"Frontend Claude: Please create a student enrollment component that consumes the enrollment API..."
```

**For Coordinated Tasks:**
```
"Backend Claude: Please update the student model and generate new API types. When complete, notify Frontend Claude via the session file."

"Frontend Claude: Check the session file for schema updates from Backend Claude. When available, integrate the new student types into the enrollment component."
```

### Monitoring Coordination

#### Checking Claude Status
```bash
# View current coordination status
cat .claude-sessions/active-sessions.json | jq '.'

# Check which files are currently locked
cat .claude-sessions/active-sessions.json | jq '.backend.files_locked, .frontend.files_locked'
```

#### Resolving Conflicts
If you notice conflicts or issues:

1. **Check session file** for emergency status
2. **Tell both Claudes to stop** work immediately
3. **Manually resolve** any file conflicts
4. **Reset coordination file** status
5. **Resume** with clear task assignments

### Environment and Port Management

#### Backend Claude Environment
- **Working Directory**: `/Users/jeffreystark/PycharmProjects/naga-monorepo-backend/`
- **Database Ports**: 5432, 5433, 5434 (depending on environment)
- **API Ports**: 8000-8999 range
- **Docker Commands**: Full docker-compose management
- **Testing**: Backend test suite, API integration tests

#### Frontend Claude Environment
- **Working Directory**: `/Users/jeffreystark/PycharmProjects/naga-monorepo-frontend/`
- **Dev Server Ports**: 3000-3999 range
- **Build Ports**: 4000-4999 range
- **Testing**: Frontend unit tests, component tests
- **Docker**: Frontend Dockerfile only (not full compose)

### Development Workflow

#### Typical Development Session
1. **Start both Claude instances** in separate terminals
2. **Assign complementary tasks** (e.g., Backend creates API, Frontend creates UI)
3. **Monitor session file** for coordination messages
4. **Handle schema changes** through Backend → Frontend notification
5. **Review integration** by running full builds occasionally
6. **End session** by having both Claudes mark themselves inactive

#### Schema Change Workflow
```bash
# 1. Backend Claude modifies Django models
# 2. Backend Claude runs: npm run generate-types
# 3. Backend Claude updates session file: schema_update_available: true
# 4. You tell Frontend Claude: "Check for schema updates and integrate"
# 5. Frontend Claude pulls changes and updates components
# 6. Frontend Claude updates session file: schema_integrated: true
```

### Best Practices

#### DO's
✅ **Assign clear, non-overlapping tasks** to each Claude
✅ **Use the session file** for coordination between Claudes
✅ **Check git history** regularly for both workspaces
✅ **Run integration tests** after major changes
✅ **Monitor resource usage** (both Claudes + development servers)

#### DON'Ts
❌ **Never assign the same file** to both Claudes simultaneously
❌ **Don't ignore coordination warnings** from either Claude
❌ **Don't run conflicting Docker commands** in both workspaces
❌ **Don't forget to sync schema changes** between frontend/backend

### Troubleshooting

#### Common Issues

**Git Conflicts:**
```bash
# Check worktree status
git worktree list

# Resolve conflicts in main repo
cd /Users/jeffreystark/PycharmProjects/naga-monorepo
git status
git merge --abort  # if needed
```

**Port Conflicts:**
```bash
# Check what's using ports
lsof -i :3000  # Frontend dev server
lsof -i :8000  # Backend dev server
```

**Session File Corruption:**
```bash
# Reset session file if corrupted
cp .claude-sessions/active-sessions.json .claude-sessions/backup.json
# Re-initialize with template above
```

### Success Indicators

Your dual Claude setup is working well when:
- ✅ Both Claudes maintain separate git branches without conflicts
- ✅ Schema changes flow smoothly from backend to frontend
- ✅ No file access conflicts or corruption
- ✅ Integration tests pass consistently
- ✅ Build times remain reasonable despite dual development

## Quick Start Operations

### Development Environment Setup
```bash
# Clone repository
git clone <repository-url>
cd naga-monorepo

# Start local development environment
docker compose -f backend/docker-compose.local.yml up

# Frontend development (separate terminal)
cd frontend
npm install
npm run dev

# Access services
# - Backend: http://localhost:8000
# - Frontend: http://localhost:3000
# - Mailpit: http://localhost:8025
```

### Production Deployment
```bash
# Build and deploy production images
docker compose -f backend/docker-compose.production.yml up -d

# Run database migrations
docker compose -f backend/docker-compose.production.yml run --rm django python manage.py migrate

# Collect static files
docker compose -f backend/docker-compose.production.yml run --rm django python manage.py collectstatic --noinput
```

## Environment Management

### Environment Configuration Matrix

| Environment | Purpose | Database | Port | Compose File |
|-------------|---------|----------|------|--------------|
| Local       | Development | `naga_local` | 8000 | `docker-compose.local.yml` |
| Migration   | Legacy data | `naga_migration` (REAL DATA) | 8001 | `docker-compose.migration.yml` |
| Staging     | Pre-production | `naga_staging` | 8002 | `docker-compose.staging.yml` |
| Production  | Live system | `naga_production` | 80/443 | `docker-compose.production.yml` |

### Critical Environment Protocols

#### ⚠️ MIGRATION ENVIRONMENT WARNING ⚠️
- **CONTAINS REAL LEGACY DATA** - Handle with extreme caution
- **Never run destructive operations** without explicit approval
- **No test data creation** - only process actual legacy records
- **Backup before any operations**

#### Environment Selection Commands
```bash
# Local development (safe)
docker compose -f backend/docker-compose.local.yml [command]

# Migration environment (CAUTION - REAL DATA)
docker compose -f backend/docker-compose.migration.yml [command]

# Staging environment
docker compose -f backend/docker-compose.staging.yml [command]

# Production environment
docker compose -f backend/docker-compose.production.yml [command]
```

## Database Operations

### Backup and Restore

#### Automated Backup Scripts
```bash
# Create backup (recommended)
./scripts/backup-database.sh

# Manual backup via container
docker compose -f backend/docker-compose.local.yml exec postgres backup

# List available backups
docker compose -f backend/docker-compose.local.yml exec postgres backups

# Restore from backup
docker compose -f backend/docker-compose.local.yml exec postgres restore backup_filename.sql.gz

# Remove backup file
docker compose -f backend/docker-compose.local.yml exec postgres rmbackup backup_filename.sql.gz
```

#### Database Migration Commands
```bash
# Run migrations
docker compose -f backend/docker-compose.local.yml run --rm django python manage.py migrate

# Create new migration
docker compose -f backend/docker-compose.local.yml run --rm django python manage.py makemigrations

# Check migration status
docker compose -f backend/docker-compose.local.yml run --rm django python manage.py showmigrations

# Reset migrations (DANGEROUS)
docker compose -f backend/docker-compose.local.yml run --rm django python manage.py migrate app_name zero
```

### Data Migration Standards

#### Critical Requirements for Data Migration Scripts
```python
# ALL migration scripts MUST use BaseMigrationCommand
from apps.common.management.base_migration import BaseMigrationCommand

class Command(BaseMigrationCommand):
    def get_rejection_categories(self):
        return ["missing_data", "duplicate_constraint", "validation_error"]

    def execute_migration(self, *args, **options):
        # Comprehensive audit reporting is automatic
        self.record_input_stats(total_records=count)
        self.record_success("records_created", count)
        self.record_rejection("missing_data", record_id, reason)
```

#### Migration Audit Reports
- **Location**: `project-docs/migration-reports/`
- **Format**: JSON with comprehensive statistics
- **Required**: Total processed/succeeded/failed with error categorization
- **Includes**: Performance metrics, data integrity validation, sample verification

## Nx Monorepo Operations

### Build System Commands
```bash
# Install Nx globally
npm install -g nx

# Build affected projects
nx affected:build

# Test affected projects
nx affected:test

# Lint affected projects
nx affected:lint

# Run specific project
nx run frontend:dev
nx run backend:test

# View dependency graph
nx graph

# Clear Nx cache
nx reset
```

### Build Optimization
- **Affected builds**: Only builds/tests changed projects
- **Distributed caching**: Shares build artifacts across environments
- **Parallel execution**: Runs tasks concurrently when possible

## CI/CD Pipeline Operations

### GitHub Actions Workflows

#### Main CI Pipeline (`.github/workflows/ci.yml`)
- **Triggers**: Push to main, pull requests
- **Jobs**: Frontend build/test, Backend test, Docker builds
- **Optimizations**: Nx affected builds, parallel execution
- **Outputs**: Docker images pushed to registry

#### Security Pipeline (`.github/workflows/security.yml`)
- **Tools**: CodeQL, Trivy, Snyk, TruffleHog
- **Coverage**: Code analysis, dependency scanning, container security, secret detection
- **Schedule**: Weekly scans + PR triggers

#### Deployment Pipeline (`.github/workflows/deploy.yml`)
- **Strategy**: Blue-green deployment with health checks
- **Environments**: Staging (auto) → Production (manual approval)
- **Rollback**: Automatic on health check failures

### Pipeline Troubleshooting
```bash
# Check workflow status
gh workflow list
gh run list --workflow=ci.yml

# View specific run
gh run view <run-id>

# Re-run failed jobs
gh run rerun <run-id>

# Cancel running workflow
gh run cancel <run-id>
```

## Monitoring and Observability

### Monitoring Stack Services

#### Prometheus (Port 9090)
```yaml
# Configuration: monitoring/prometheus/prometheus.yml
# Targets: Django metrics, system metrics, custom business metrics
# Retention: 30 days default

# Query examples:
# - Request rate: rate(django_http_requests_total[5m])
# - Error rate: rate(django_http_requests_total{status=~"5.."}[5m])
# - Database connections: django_db_connections_active
```

#### Grafana (Port 3000)
```yaml
# Dashboards: monitoring/grafana/dashboards/
# - system-overview.json: System health and performance
# - django-application.json: Application-specific metrics
# - academic-business.json: Academic domain metrics
# - infrastructure.json: Database, Redis, container metrics

# Access: admin/admin (change in production)
```

#### Alertmanager (Port 9093)
```yaml
# Configuration: monitoring/alertmanager/alertmanager.yml
# Rules: monitoring/prometheus/rules/
# Channels: Email, Slack, PagerDuty integration

# Alert categories:
# - Critical: System down, data corruption
# - High: Performance degradation, error rate spikes
# - Medium: Resource utilization, disk space
# - Low: Informational, maintenance reminders
```

#### Sentry Error Tracking
```yaml
# Configuration via environment variables
# SENTRY_DSN: Project-specific DSN
# SENTRY_ENVIRONMENT: Environment tag
# SENTRY_TRACES_SAMPLE_RATE: Performance monitoring

# Integration: Automatic Django error capture
# Features: Error grouping, performance monitoring, release tracking
```

### Monitoring Commands
```bash
# Start monitoring stack
docker compose -f monitoring/docker-compose.yml up -d

# View monitoring logs
docker compose -f monitoring/docker-compose.yml logs -f prometheus
docker compose -f monitoring/docker-compose.yml logs -f grafana

# Backup Grafana dashboards
./scripts/backup-grafana-dashboards.sh

# Import custom dashboard
curl -X POST http://admin:admin@localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @monitoring/grafana/dashboards/custom-dashboard.json
```

### Academic Business Metrics
```yaml
# Student enrollment metrics
student_enrollment_total{status="active"}
student_enrollment_by_program{program="computer_science"}

# Course metrics
course_capacity_utilization{course_code="CS101"}
course_completion_rate{semester="2024-1"}

# Financial metrics
tuition_revenue_total{payment_status="paid"}
scholarship_utilization{scholarship_type="merit"}

# Attendance metrics
attendance_rate_by_course{course_code="CS101"}
absence_rate_trend{time_period="weekly"}
```

## Security Operations

### Security Scanning
```bash
# Run security scans locally
docker run --rm -v $(pwd):/src aquasec/trivy fs /src
bandit -r backend/ -f json -o security-report.json

# Dependency vulnerability check
pip-audit --format=json --output=audit-report.json

# Secret scanning
trufflehog git file://. --json > secrets-report.json
```

### Security Hardening Checklist
- [ ] Container images run as non-root users
- [ ] Secrets stored in environment variables, not code
- [ ] TLS enabled for all production traffic
- [ ] Database connections encrypted
- [ ] Regular security updates applied
- [ ] Security headers configured (HSTS, CSP, etc.)
- [ ] Authentication via Keycloak with strong policies
- [ ] API rate limiting enabled
- [ ] Input validation on all endpoints
- [ ] Audit logging enabled for sensitive operations

## Performance Operations

### Performance Monitoring
```bash
# Django performance profiling
docker compose -f backend/docker-compose.local.yml run --rm django python manage.py shell
# Use django-debug-toolbar for request profiling

# Database query analysis
docker compose -f backend/docker-compose.local.yml exec postgres psql -U postgres -d naga
# Use EXPLAIN ANALYZE for slow queries

# Redis performance monitoring
docker compose -f backend/docker-compose.local.yml exec redis redis-cli --latency-history
```

### Performance Optimization Guidelines
- **Database**: Index frequently queried fields, use select_related/prefetch_related
- **Caching**: Implement Redis caching for expensive queries
- **Static Files**: Use CDN for production static/media files
- **Background Tasks**: Use Dramatiq for time-consuming operations
- **Frontend**: Implement code splitting and lazy loading
- **Images**: Optimize and compress images, use WebP format

## Maintenance Operations

### Regular Maintenance Tasks

#### Daily
- [ ] Check application health endpoints
- [ ] Review error logs and alerts
- [ ] Monitor disk space and resource usage
- [ ] Verify backup completion

#### Weekly
- [ ] Security scan results review
- [ ] Performance metrics analysis
- [ ] Database maintenance (VACUUM, REINDEX)
- [ ] Log rotation and cleanup

#### Monthly
- [ ] Dependency updates (security patches)
- [ ] SSL certificate renewal check
- [ ] Disaster recovery testing
- [ ] Capacity planning review

### Maintenance Commands
```bash
# Database maintenance
docker compose -f backend/docker-compose.production.yml exec postgres psql -U postgres -d naga -c "VACUUM ANALYZE;"

# Log cleanup
docker system prune -f
docker volume prune -f

# Certificate renewal (Let's Encrypt)
docker compose -f backend/docker-compose.production.yml exec nginx certbot renew

# Dependency updates
cd backend && uv sync --upgrade
cd frontend && npm update

# Clear application caches
docker compose -f backend/docker-compose.production.yml run --rm django python manage.py clear_cache
```

## Troubleshooting Guide

### Common Issues and Solutions

#### Application Won't Start
```bash
# Check logs
docker compose -f backend/docker-compose.local.yml logs django

# Common causes:
# - Database connection issues: Check DATABASE_URL
# - Missing migrations: Run python manage.py migrate
# - Port conflicts: Check if port 8000 is in use
# - Permission issues: Check file permissions and Docker user
```

#### Database Connection Issues
```bash
# Check database status
docker compose -f backend/docker-compose.local.yml exec postgres pg_isready

# Reset database connection
docker compose -f backend/docker-compose.local.yml restart postgres django

# Check connection settings
docker compose -f backend/docker-compose.local.yml run --rm django python manage.py shell
>>> from django.db import connection
>>> connection.ensure_connection()
```

#### Performance Issues
```bash
# Check resource usage
docker stats

# Analyze slow queries
docker compose -f backend/docker-compose.local.yml exec postgres psql -U postgres -d naga
# Enable slow query logging and analyze patterns

# Check Redis memory usage
docker compose -f backend/docker-compose.local.yml exec redis redis-cli info memory
```

#### Build Issues
```bash
# Clear build cache
docker builder prune -f

# Rebuild from scratch
docker compose -f backend/docker-compose.local.yml build --no-cache

# Check Nx cache
nx reset
```

### Emergency Procedures

#### System Down
1. **Check health endpoints**: Verify which services are affected
2. **Review recent changes**: Check last deployments via git log
3. **Check monitoring alerts**: Grafana/Prometheus for root cause
4. **Rollback if needed**: Use previous working Docker images
5. **Document incident**: Create incident report in project-docs/

#### Data Corruption
1. **STOP all write operations immediately**
2. **Create emergency backup** of current state
3. **Assess corruption scope** via database queries
4. **Restore from last good backup** if necessary
5. **Investigate root cause** before resuming operations
6. **Test data integrity** thoroughly before going live

#### Security Breach
1. **Isolate affected systems** immediately
2. **Change all credentials** (database, API keys, etc.)
3. **Review access logs** for breach extent
4. **Patch vulnerabilities** that enabled breach
5. **Monitor for continued attacks**
6. **Report incident** according to compliance requirements

## API Operations

### API Management
```bash
# View API documentation
# Django-ninja auto-generates OpenAPI docs at /api/docs

# Test API endpoints
curl -X GET http://localhost:8000/api/students/
curl -X POST http://localhost:8000/api/students/ -H "Content-Type: application/json" -d '{"name": "Test Student"}'

# API rate limiting (configured in settings)
# Monitor API usage via Prometheus metrics
```

### API Schema Management
```bash
# Generate TypeScript types from Django models
cd backend && python manage.py generate_api_types

# Validate API schema
cd backend && python manage.py validate_api_schema

# Update frontend types
cd frontend && npm run update-types
```

## Deployment Operations

### Blue-Green Deployment Process
1. **Pre-deployment validation**: Run tests and security scans
2. **Deploy to staging**: Validate in staging environment
3. **Deploy green environment**: New version parallel to blue
4. **Health check validation**: Automated tests on green environment
5. **Traffic switch**: Route traffic from blue to green
6. **Monitor metrics**: Watch for errors/performance issues
7. **Rollback capability**: Keep blue environment ready for 24 hours

### Deployment Commands
```bash
# Deploy to staging
gh workflow run deploy.yml --ref staging

# Deploy to production (requires approval)
gh workflow run deploy.yml --ref main

# Manual deployment
docker compose -f backend/docker-compose.production.yml up -d --build

# Health check
curl -f http://localhost:8000/health/
```

## 📚 Historical Repository Access

### Git Repository References

The monorepo includes read-only references to historical Git repositories that were consolidated during the monorepo creation. These provide access to pre-consolidation history without cluttering the main repository.

#### Available Historical Repositories
- **Frontend Repository**: Vue.js PWA frontend before monorepo consolidation
- **Backend Repository**: Django backend before monorepo consolidation
- **Version 0 Repository**: Legacy architecture (reference for dependency analysis)

#### Quick Access Commands
```bash
# View commit history
./scripts/git-history-tools.sh log frontend
./scripts/git-history-tools.sh log backend
./scripts/git-history-tools.sh log version-0

# Repository statistics
./scripts/git-history-tools.sh stats frontend

# Extract historical file
./scripts/git-history-tools.sh extract version-0 apps/core/models.py

# Compare with current
./scripts/git-history-tools.sh diff backend apps/people/models.py
```

#### Manual Git Commands
```bash
# Direct git access to historical repositories
git --git-dir=.git-references/frontend.git log --oneline
git --git-dir=.git-references/backend.git show HEAD:apps/people/models.py
git --git-dir=.git-references/version-0.git log --graph --oneline
```

#### Use Cases
- **Architectural Analysis**: Compare current clean architecture with problematic version-0
- **Migration Verification**: Ensure all functionality was preserved during consolidation
- **Historical Research**: Investigate how specific features evolved
- **Debugging**: Reference previous implementations when troubleshooting
- **Documentation**: Extract historical documentation or comments

#### Notes
- Historical repositories are **read-only** - no modifications possible
- Stored in `.git-references/` directory (gitignored, local only)
- Version-0 repository is particularly valuable for understanding circular dependency issues
- Use `./scripts/git-history-tools.sh help` for complete usage guide

## Contact and Escalation

### Support Contacts
- **System Administrator**: [admin@pucsr.edu.kh]
- **Development Team**: [dev@pucsr.edu.kh]
- **Security Team**: [security@pucsr.edu.kh]
- **Database Administrator**: [dba@pucsr.edu.kh]

### Escalation Matrix
- **P1 (Critical)**: System down, data loss, security breach
- **P2 (High)**: Major functionality broken, performance severely degraded
- **P3 (Medium)**: Minor functionality issues, performance concerns
- **P4 (Low)**: Enhancement requests, minor bugs

### Emergency Contacts
- **On-call Engineer**: [Available 24/7]
- **System Admin**: [Business hours + emergency escalation]
- **Security Team**: [Immediate response for security incidents]

---

**Document Version**: 1.0
**Last Updated**: 2025-01-01
**Next Review**: 2025-04-01
**Owner**: Naga SIS Operations Team
