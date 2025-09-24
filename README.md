# Naga Student Information System - Monorepo

[![CI](https://github.com/starkjeffrey/naga-monorepo/workflows/CI/badge.svg)](https://github.com/starkjeffrey/naga-monorepo/actions)
[![Security](https://github.com/starkjeffrey/naga-monorepo/workflows/Security/badge.svg)](https://github.com/starkjeffrey/naga-monorepo/actions)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

> **Modern Student Information System for Educational Institutions**  
> Built with Django 5.2+, Vue 3, and clean architecture principles

## 🌟 Project Overview

Naga SIS is a comprehensive Student Information System designed for educational institutions, featuring a modern monorepo architecture with Django backend, Vue.js PWA frontend, and enterprise-grade monitoring and CI/CD capabilities.

### 🏗️ Architecture Highlights

- **🔧 Monorepo Structure**: Nx-powered workspace with affected builds and caching
- **⚡ Backend**: Django 5.2+ with django-ninja API and clean architecture
- **🏛️ Policy Engine**: Centralized business rules for audit compliance and governance
- **🎨 Frontend**: Vue 3 + Quasar PWA with Capacitor for mobile deployment
- **📊 Monitoring**: Comprehensive observability with Prometheus, Grafana, Sentry
- **🚀 CI/CD**: Automated testing, security scanning, and blue-green deployments
- **🐳 Infrastructure**: Multi-stage Docker builds with production optimization

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 18+ (for frontend development)
- Python 3.13.7+ (for local backend development)

### Development Setup
```bash
# Clone the repository
git clone https://github.com/starkjeffrey/naga-monorepo.git
cd naga-monorepo

# Start backend services
cd backend
docker compose -f docker-compose.local.yml up

# Start frontend development (separate terminal)
cd frontend  
npm install
npm run dev

# Access the application
# Backend: http://localhost:8000
# Frontend: http://localhost:3000
# API Docs: http://localhost:8000/api/docs
```

### Production Deployment
```bash
# Build and deploy production environment
docker compose -f backend/docker-compose.production.yml up -d

# Run database migrations
docker compose -f backend/docker-compose.production.yml run --rm django python manage.py migrate

# Start monitoring stack
docker compose -f monitoring/docker-compose.yml up -d
```

## 📁 Project Structure

```
naga-monorepo/
├── backend/                    # Django backend application
│   ├── apps/                   # Django apps (clean architecture)
│   ├── api/                    # django-ninja API endpoints
│   ├── config/                 # Django settings and configuration
│   └── docker-compose.*.yml    # Environment-specific Docker configs
├── frontend/                   # Vue.js PWA frontend
│   ├── src/                    # Vue application source
│   ├── src-capacitor/          # Capacitor mobile app config
│   └── dist/                   # Built frontend assets
├── libs/                       # Nx shared libraries
│   └── shared/api-types/       # TypeScript API types and validation
├── monitoring/                 # Monitoring stack configuration
│   ├── prometheus/             # Metrics collection
│   ├── grafana/                # Dashboards and visualization
│   └── alertmanager/           # Alert routing and notification
├── .github/workflows/          # CI/CD pipeline definitions
├── project-docs/               # Project documentation and analysis
└── scripts/                    # Utility and maintenance scripts
```

## 🛠️ Development Workflow

### Nx Monorepo Commands
```bash
# Install Nx globally
npm install -g nx

# Build affected projects only
nx affected:build

# Test affected projects
nx affected:test

# Run specific project
nx run frontend:dev
nx run backend:test

# View project dependency graph
nx graph
```

### Backend Development
```bash
# Django commands via Docker
docker compose -f backend/docker-compose.local.yml run --rm django python manage.py [command]

# Examples:
# Create migrations
docker compose -f backend/docker-compose.local.yml run --rm django python manage.py makemigrations

# Run tests with coverage
docker compose -f backend/docker-compose.local.yml run --rm -e DJANGO_SETTINGS_MODULE=config.settings.test django pytest --cov

# Code quality checks
docker compose -f backend/docker-compose.local.yml run --rm django ruff check
docker compose -f backend/docker-compose.local.yml run --rm django mypy naga
```

### Local Testing (Without Docker)

For faster test iterations and development, you can run the test suite locally using SQLite without requiring Docker or PostgreSQL.

#### Setup Local Testing Environment
```bash
cd backend

# Install dependencies with uv (recommended) or pip
uv sync --extra dev
# OR: pip install -e ".[dev]"

# Verify Python version
python --version  # Should be Python 3.13.7+
```

#### Running Tests Locally
```bash
# Run all tests using SQLite (fast)
uv run python manage.py test --settings=config.settings.local_test

# Run specific test modules
uv run python manage.py test apps.curriculum --settings=config.settings.local_test
uv run python manage.py test apps.people.tests --settings=config.settings.local_test

# Run with verbose output
uv run python manage.py test apps.curriculum --settings=config.settings.local_test -v 2

# Run single test class or method
uv run python manage.py test apps.curriculum.tests.CycleModelTest --settings=config.settings.local_test
uv run python manage.py test apps.curriculum.tests.CycleModelTest.test_cycle_creation --settings=config.settings.local_test
```

#### Local Test Configuration
The local test environment uses these optimizations:
- **SQLite in-memory database** for fast test execution
- **Simplified password hashing** (MD5) for speed
- **Disabled middleware** that requires external services
- **Local email backend** for email testing

#### Environment Setup for Local Testing
```bash
# Option 1: Create minimal .env for local testing
cd backend
cat > .env.local_test << EOF
DEBUG=1
SECRET_KEY=test-secret-key-for-local-development
DATABASE_URL=sqlite:///test_naga.db
ALLOWED_HOSTS=localhost,127.0.0.1
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EOF

# Option 2: Use environment variables directly
export DATABASE_URL="sqlite:///test_naga.db"
export DEBUG=1
export SECRET_KEY="test-secret-key"
```

#### Code Quality Checks (Local)
```bash
cd backend

# Format code
uv run ruff format .

# Check code style and quality
uv run ruff check .

# Type checking
uv run mypy .

# Run all quality checks
uv run ruff check . && uv run ruff format --check . && uv run mypy .
```

#### Benefits of Local Testing
- **⚡ Faster execution**: No Docker overhead, SQLite in-memory
- **🔧 Quick iteration**: Instant test feedback during development  
- **💻 Offline development**: No external service dependencies
- **🧪 Isolated testing**: Each test run uses fresh database
- **🔍 Better debugging**: Direct Python debugging without containers

#### Quick Setup Verification
```bash
cd backend

# Run setup verification script
python scripts/verify_local_testing.py

# If successful, you can now run tests locally:
uv run python manage.py test --settings=config.settings.local_test
```

#### When to Use Local vs Docker Testing
- **Local Testing**: Unit tests, model tests, quick validation during development
- **Docker Testing**: Integration tests, deployment validation, CI/CD pipeline testing
- **Both**: Run locally for speed, then validate with Docker before committing

### Frontend Development
```bash
cd frontend

# Development server
npm run dev

# Build for production
npm run build

# Mobile app development
npm run capacitor:dev

# Type checking
npm run type-check

# Linting and formatting
npm run lint
npm run format
```

## 🏛️ Clean Architecture

The project follows strict clean architecture principles to avoid the circular dependency issues documented in `project-docs/dependency_analysis_20250612.md`.

### Django Apps Structure
```
Foundation Layer:
├── accounts/     # Authentication & authorization
├── common/       # Shared utilities & base models
├── geography/    # Locations & provinces
└── facilities/   # Buildings & rooms

Domain Layer:
├── people/       # Person profiles & contacts
├── academic/     # Courses, programs, terms
├── enrollment/   # Student registration
└── scheduling/   # Class scheduling

Business Logic Layer:
├── scholarships/ # Financial aid management
├── finance/      # Billing & payments
├── grading/      # Grade & GPA management
└── attendance/   # Attendance tracking

Service Layer:
├── documents/    # Document services
└── workflow/     # Task management
```

### API Schema Sharing
- **Django Models** → **OpenAPI Schema** → **TypeScript Types** → **Zod Validation**
- Automated type generation ensures frontend/backend consistency
- Runtime validation with comprehensive error handling

## 📊 Monitoring & Observability

### Monitoring Stack
- **Prometheus** (`:9090`): Metrics collection and time-series database
- **Grafana** (`:3000`): Dashboards and visualization (admin/admin)
- **Alertmanager** (`:9093`): Alert routing and notifications
- **Sentry**: Error tracking and performance monitoring

### Key Metrics
```yaml
# Academic Business Metrics
student_enrollment_total{status="active"}
course_capacity_utilization{course_code="CS101"}
tuition_revenue_total{payment_status="paid"}
attendance_rate_by_course{course_code="CS101"}

# System Performance Metrics  
django_http_requests_total
django_db_connections_active
redis_memory_usage_bytes
container_cpu_usage_percent
```

### Monitoring Setup
```bash
# Start monitoring stack
docker compose -f monitoring/docker-compose.yml up -d

# Access services
# Grafana: http://localhost:3000 (admin/admin)
# Prometheus: http://localhost:9090
# Alertmanager: http://localhost:9093
```

## 🔒 Security & Compliance

### Security Features
- **Multi-layer scanning**: CodeQL, Trivy, Snyk, TruffleHog
- **Container security**: Non-root users, minimal attack surface
- **Authentication**: Keycloak integration with role-based access
- **API security**: Rate limiting, input validation, CORS configuration
- **Data protection**: Encrypted connections, secure session handling

### Security Scanning
```bash
# Run security scans locally
docker run --rm -v $(pwd):/src aquasec/trivy fs /src
bandit -r backend/ -f json -o security-report.json
trufflehog git file://. --json > secrets-report.json
```

## 🚀 CI/CD Pipeline

### Automated Workflows
- **🔄 Continuous Integration**: Nx affected builds, parallel testing, Docker builds
- **🔍 Security Scanning**: Weekly vulnerability scans, dependency analysis
- **🚢 Deployment**: Blue-green deployment with health checks and rollback

### Pipeline Features
- **Affected Builds**: Only builds/tests changed projects (Nx optimization)
- **Parallel Execution**: Frontend and backend jobs run concurrently
- **Environment Promotion**: Staging → Production with manual approval gates
- **Health Monitoring**: Automated rollback on deployment failures

## 🗄️ Database Management

### Multi-Environment Database Support
| Environment | Purpose | Database | Port | Notes |
|-------------|---------|----------|------|-------|
| Local | Development | `naga_local` | 5432 | Safe for testing |
| Evaluation | Demo/Testing | `naga_evaluation` | 5432 | Remote demo environment |
| Staging | Pre-production | `naga_staging` | 5434 | Production mirror |
| Production | Live system | `naga_production` | 5432 | Live data |

### Database Operations
```bash
# Backup database
./scripts/backup-database.sh

# Restore from backup  
docker compose -f backend/docker-compose.local.yml exec postgres restore backup_filename.sql.gz

# Run migrations
docker compose -f backend/docker-compose.local.yml run --rm django python manage.py migrate
```

## 🚀 Deployment Options

### Evaluation Environment
The evaluation environment allows remote users to test and evaluate the system:

```bash
# Deploy evaluation environment on remote server
docker compose -f backend/docker-compose.evaluation.yml up -d

# Monitor logs
docker compose -f backend/docker-compose.evaluation.yml logs -f

# Stop evaluation environment
docker compose -f backend/docker-compose.evaluation.yml down
```

**Features:**
- Pre-configured demo data for testing
- Secure remote access configuration
- Resource limits for shared hosting
- Automatic SSL/TLS setup (when configured)
- Includes monitoring stack

### Production Deployment
See [OPERATIONS.md](OPERATIONS.md) for complete production deployment guide.

## 📚 Documentation

### Available Documentation
- **[OPERATIONS.md](OPERATIONS.md)**: Comprehensive systems operations manual
- **[CLAUDE.md](backend/CLAUDE.md)**: Development context and architectural guidelines
- **[project-docs/](project-docs/)**: Technical analysis and migration reports
- **API Documentation**: Auto-generated at `/api/docs` (django-ninja)

### Documentation Structure
```
project-docs/           # Project-specific documentation
├── dependency_analysis_20250612.md  # Architectural analysis
├── migration-reports/  # Data migration audit trails
└── technical-specs/    # Feature specifications

docs/                   # Sphinx technical documentation
├── api/               # API reference documentation  
└── deployment/        # Deployment and infrastructure guides
```

## 🤝 Contributing

### Development Standards
- **Code Style**: Python (PEP 8, Ruff), TypeScript (ESLint, Prettier)
- **Testing**: Comprehensive test coverage with pytest and Vitest
- **Git**: Conventional commits with descriptive messages
- **Architecture**: Follow clean architecture principles (see CLAUDE.md)
- **Security**: Never commit secrets, always validate inputs

### Development Process
1. **Create feature branch** from `main`
2. **Follow TDD practices** for complex functionality  
3. **Run quality checks** (lint, type-check, test)
4. **Create pull request** with comprehensive description
5. **Automated CI/CD** runs affected builds and security scans
6. **Code review** and approval required
7. **Automated deployment** to staging, manual promotion to production

## 🌐 Academic Context

### Target Institution
**Pannasastra University of Cambodia, Siem Reap Campus (PUCSR)**
- Multi-language support (English, Khmer)
- Academic calendar and semester management
- Student lifecycle from enrollment to graduation
- Financial aid and scholarship management
- Mobile-first design for student and faculty access

### Core Features
- **👥 Student Management**: Enrollment, profiles, academic records
- **📚 Academic Management**: Courses, programs, scheduling, grading
- **💰 Financial Management**: Tuition, payments, scholarships, billing
- **📋 Attendance Tracking**: QR code check-in, automated reporting
- **📱 Mobile PWA**: Native app experience with offline capabilities
- **🔐 Role-based Access**: Students, faculty, staff, administrators

## 📞 Support & Contact

### Getting Help
- **Issues**: [GitHub Issues](https://github.com/starkjeffrey/naga-monorepo/issues)
- **Discussions**: [GitHub Discussions](https://github.com/starkjeffrey/naga-monorepo/discussions)  
- **Documentation**: Check `OPERATIONS.md` for detailed operational guidance
- **Security**: Report security issues via private GitHub security advisories

### Project Maintainers
- **Technical Lead**: Jeffrey Stark
- **Institution**: PUCSR Development Team
- **License**: MIT License

---

> **Built with ❤️ for educational excellence**  
> *Empowering institutions through modern technology*