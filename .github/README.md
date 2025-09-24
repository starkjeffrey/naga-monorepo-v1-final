# GitHub Workflows Documentation

This directory contains the CI/CD workflows for the Naga SIS monorepo.

## 🔄 Workflows Overview

### 1. **CI/CD Pipeline** (`ci.yml`)
- **Triggers**: Push to main/develop, Pull Requests
- **Features**: 
  - Nx-powered affected project detection
  - Parallel testing (backend, frontend, shared)
  - Code coverage reporting
  - Docker image building
  - Automated deployment triggers

### 2. **Deployment** (`deploy.yml`)  
- **Triggers**: Successful CI completion, Manual dispatch
- **Features**:
  - VPS deployment to Linode servers
  - Docker Hub image registry
  - Health checks and automatic rollback
  - Multi-environment support (staging/production)
  - Nginx static file serving

### 3. **Security Scanning** (`security.yml`)
- **Triggers**: Push, Pull Requests, Weekly schedule
- **Features**:
  - Dependency vulnerability scanning
  - Secret detection (TruffleHog)
  - Static code analysis (CodeQL)
  - Container security scanning (Trivy, Snyk)
  - License compliance checking

## 🚀 Quick Start

### Prerequisites
1. Configure GitHub Secrets (see `SECRETS_SETUP.md`)
2. Set up Linode VPS servers for staging and production
3. Ensure Docker is running locally
4. Install dependencies: `npm ci`

### Local Testing
```bash
# Test workflows locally
./scripts/test-workflows-local.sh

# Test specific project
npx nx test backend
npx nx lint frontend
npx nx affected:build
```

### Manual Workflow Triggers
1. Go to **Actions** tab in GitHub
2. Select workflow to run
3. Click **Run workflow**
4. Choose branch and parameters

## 📊 Workflow Features

### Nx Monorepo Optimization
- **Affected Detection**: Only tests/builds changed projects
- **Parallel Execution**: Frontend and backend run simultaneously  
- **Dependency Caching**: Faster builds with intelligent caching
- **Shared Libraries**: Automated API type generation and validation

### Backend-Specific Features
- **Multi-Database Testing**: PostgreSQL + Redis services
- **Django Optimization**: Custom CI settings for faster tests
- **Docker Integration**: Production-ready container builds
- **Migration Testing**: Automated database migration validation

### Frontend-Specific Features
- **PWA Building**: Service worker and manifest validation
- **Mobile Testing**: Capacitor integration tests
- **Asset Optimization**: Automated image and bundle optimization
- **TypeScript Validation**: Strict type checking with shared API types

## 🔐 Security & Compliance

### Automated Security Checks
- **Secret Scanning**: Prevents credential leaks
- **Dependency Auditing**: CVE and license compliance
- **Code Quality**: ESLint, Prettier, Ruff integration
- **Container Scanning**: Multi-layer vulnerability detection

### Compliance Features
- **Audit Logging**: Full CI/CD activity tracking
- **Environment Separation**: Strict staging/production isolation
- **Access Controls**: Role-based deployment permissions
- **Rollback Procedures**: Automated failure recovery

## 🛠️ Troubleshooting

### Common Issues

**Tests Failing:**
```bash
# Check service health
docker compose -f backend/docker-compose.local.yml ps

# View logs
docker compose -f backend/docker-compose.local.yml logs
```

**Deployment Issues:**
- Verify Linode SSH keys in GitHub Secrets
- Check Docker Hub credentials and repository access
- Validate server connectivity and prerequisites
- Review deployment logs for specific error details

**Security Scan Failures:**
- Review Snyk/Trivy reports in Actions tab
- Update vulnerable dependencies
- Add security exceptions if needed

### Debug Commands
```bash
# Test affected detection
npx nx show projects --affected --base=main

# Validate Docker builds
docker build -f backend/compose/production/django/Dockerfile backend/

# Test database migrations
docker compose -f backend/docker-compose.local.yml run --rm django python manage.py migrate --check
```

## 📈 Monitoring & Metrics

### CI/CD Metrics
- **Build Times**: Track via Actions dashboard
- **Test Coverage**: Automated Codecov reporting  
- **Deployment Success**: Health check validation
- **Security Posture**: Weekly vulnerability reports

### Performance Optimization
- **Cache Hit Rates**: Nx and Docker layer caching
- **Parallel Execution**: Optimal job distribution
- **Resource Usage**: Memory and CPU monitoring
- **Artifact Management**: Automated cleanup policies

## 🔄 Workflow Updates

When modifying workflows:

1. **Test Locally**: Use `./scripts/test-workflows-local.sh`
2. **Staged Deployment**: Test in feature branch first
3. **Documentation**: Update this README
4. **Team Review**: PR review required for workflow changes

### Version Updates
- **Actions**: Use pinned versions (e.g., `@v4`)
- **Dependencies**: Regular security updates
- **Base Images**: Monthly base image updates
- **Tools**: Quarterly tool version reviews