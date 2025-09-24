# 🚀 CI/CD Pipeline Setup & Operations Guide

## 📋 **Overview**

The Naga SIS monorepo uses a comprehensive CI/CD pipeline built on GitHub Actions with Nx workspace optimization, multi-environment deployments, and enterprise-grade monitoring.

## 🏗️ **Architecture**

### **Pipeline Components**
- **Build System**: Nx monorepo with affected builds
- **Testing**: Parallel test execution for backend/frontend
- **Security**: Multi-layer scanning (SAST, DAST, container, dependencies)
- **Deployment**: Environment-specific with blue-green strategy
- **Monitoring**: Prometheus, Grafana, Alertmanager, Sentry

### **Workflow Structure**
```
.github/workflows/
├── ci.yml           # Main CI/CD pipeline
├── security.yml     # Security scanning
└── deploy.yml       # Environment deployments
```

## 🔄 **CI/CD Workflows**

### **Main CI Pipeline** (`ci.yml`)

**Triggers:**
- Push to `main`/`develop`
- Pull requests to `main`/`develop`
- Manual dispatch

**Stages:**
1. **Setup** → Nx affected analysis
2. **Lint & Format** → Code quality checks
3. **Test** → Parallel test execution
4. **Build** → Docker image creation
5. **Security Scan** → Vulnerability assessment
6. **Deploy** → Environment-specific deployment

**Key Features:**
- **Nx Affected Commands** → Only build/test changed projects
- **Parallel Execution** → Frontend/backend run concurrently
- **Caching Strategy** → Nx cache + Docker layer caching
- **Artifact Management** → Test reports, coverage, build outputs

### **Security Pipeline** (`security.yml`)

**Scans:**
- **CodeQL** → SAST for Python/JavaScript
- **Dependency Review** → Vulnerable dependencies
- **Container Scanning** → Trivy + Snyk
- **Secret Detection** → TruffleHog
- **License Compliance** → License compatibility

**Schedule:** Weekly + on-demand

### **Deployment Pipeline** (`deploy.yml`)

**Environments:**
- **Staging** → Auto-deploy from `develop`
- **Production** → Auto-deploy from `main` (with approval)

**Features:**
- **Infrastructure as Code** → Terraform
- **Health Checks** → Automated validation
- **Rollback Strategy** → Automatic on failure
- **Blue-Green Deployment** → Zero-downtime

## 🛠️ **Setup Instructions**

### **1. Repository Configuration**

#### **Required Secrets**
```bash
# Docker Registry
DOCKER_USERNAME
DOCKER_PASSWORD

# AWS Deployment
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY

# Database
DATABASE_URL
GRAFANA_DB_PASSWORD

# Notifications
SLACK_WEBHOOK_URL
SMTP_PASSWORD

# Security
SENTRY_DSN
SNYK_TOKEN
```

#### **Required Variables**
```bash
# Infrastructure
AWS_REGION=us-east-1
TERRAFORM_STATE_BUCKET=naga-terraform-state
DOMAIN_NAME=naga.pucsr.edu.kh
CERTIFICATE_ARN=arn:aws:acm:...

# Networking
PRIVATE_SUBNET_1=subnet-xxx
PRIVATE_SUBNET_2=subnet-yyy
BACKEND_SECURITY_GROUP=sg-xxx

# Storage
S3_BUCKET_NAME=naga-frontend-assets
CLOUDFRONT_DISTRIBUTION_ID=E1234567890

# Monitoring
SNS_ALERT_TOPIC=arn:aws:sns:...
ECR_REGISTRY=123456789.dkr.ecr.us-east-1.amazonaws.com
```

### **2. Environment Setup**

#### **GitHub Actions Environments**
1. **staging**
   - Auto-deployment enabled
   - Reviewers: Development team
   - Protection rules: None

2. **production**
   - Manual approval required
   - Reviewers: Senior developers, DevOps
   - Protection rules: Main branch only

#### **Branch Protection Rules**
```yaml
main:
  required_status_checks:
    - CI/CD Pipeline
    - Security Scanning
  required_pull_request_reviews: 2
  dismiss_stale_reviews: true
  require_code_owner_reviews: true

develop:
  required_status_checks:
    - CI/CD Pipeline
  required_pull_request_reviews: 1
```

### **3. Infrastructure Prerequisites**

#### **AWS Resources**
- **ECS Cluster** → Container orchestration
- **RDS PostgreSQL** → Database
- **ElastiCache Redis** → Caching
- **S3 Bucket** → Static assets
- **CloudFront** → CDN
- **ALB** → Load balancing
- **Route 53** → DNS management

#### **Monitoring Stack**
```bash
# Start monitoring services
docker-compose -f monitoring/docker-compose.monitoring.yml up -d

# Access dashboards
http://localhost:3000    # Grafana
http://localhost:9090    # Prometheus
http://localhost:3001    # Uptime Kuma
```

## 📊 **Monitoring & Observability**

### **Metrics Collection**
- **Application Metrics** → Django + Vue.js
- **Infrastructure Metrics** → Node Exporter, cAdvisor
- **Database Metrics** → PostgreSQL Exporter
- **Cache Metrics** → Redis Exporter

### **Logging Strategy**
- **Structured Logs** → JSON format
- **Log Aggregation** → Loki
- **Log Retention** → 30 days (configurable)
- **Sensitive Data Filtering** → Automatic PII removal

### **Error Reporting**
- **Sentry Integration** → Real-time error tracking
- **Performance Monitoring** → Transaction tracing
- **Business Context** → Academic operation tracking
- **Alert Routing** → Team-specific notifications

### **Alerting Rules**

#### **Critical Alerts**
- Service Down (30s threshold)
- High Error Rate (>5% for 2m)
- Database Connection Issues
- Security Incidents

#### **Warning Alerts**
- High CPU/Memory (>80% for 5m)
- Slow Response Times (>2s 95th percentile)
- Disk Space Low (<10%)
- High Connection Count

#### **Business Alerts**
- Enrollment Deadline Approaching
- Term Ending Soon
- Scheduled Maintenance Reminder

## 🔧 **Troubleshooting Guide**

### **Common Issues**

#### **Build Failures**

**Nx Affected Detection Issues**
```bash
# Problem: Nx not detecting changes correctly
# Solution: Check base SHA and head SHA
git log --oneline -10
npx nx show projects --affected --base=HEAD~1 --head=HEAD
```

**Docker Build Failures**
```bash
# Problem: Docker build context issues
# Solution: Check .dockerignore and build context
docker build --no-cache -t test-image .
docker system prune -f  # Clean build cache
```

**Dependency Installation Failures**
```bash
# Problem: Package installation issues
# Solution: Clear cache and reinstall
npm ci --cache /tmp/empty-cache
pip cache purge && pip install -r requirements.txt
```

#### **Test Failures**

**Database Connection Issues**
```bash
# Problem: PostgreSQL service not ready
# Solution: Add health checks and wait conditions
docker-compose up -d postgres
docker-compose exec postgres pg_isready -U postgres
```

**Frontend Test Environment**
```bash
# Problem: DOM not available in tests
# Solution: Check vitest.config.js setup
npm run test -- --reporter=verbose
```

**Backend Test Database**
```bash
# Problem: Test database conflicts
# Solution: Use separate test database
export DJANGO_SETTINGS_MODULE=config.settings.test
python manage.py migrate --run-syncdb
```

#### **Deployment Issues**

**ECS Task Failures**
```bash
# Check ECS service status
aws ecs describe-services --cluster naga-prod --services naga-backend

# View task logs
aws logs get-log-events --log-group-name /ecs/naga-backend
```

**CloudFront Cache Issues**
```bash
# Invalidate CloudFront cache
aws cloudfront create-invalidation \
  --distribution-id E1234567890 \
  --paths "/*"
```

**Database Migration Issues**
```bash
# Run migrations manually
aws ecs run-task \
  --cluster naga-prod \
  --task-definition naga-backend \
  --overrides file://migration-task-override.json
```

#### **Monitoring Issues**

**Prometheus Target Down**
```bash
# Check service discovery
curl http://prometheus:9090/api/v1/targets

# Verify network connectivity
docker exec prometheus wget -qO- backend:8000/metrics
```

**Grafana Dashboard Issues**
```bash
# Check datasource connectivity
curl http://grafana:3000/api/datasources/proxy/1/api/v1/query \
  -H "Authorization: Bearer ${GRAFANA_TOKEN}"
```

**Alert Manager Not Firing**
```bash
# Check alert rules
curl http://prometheus:9090/api/v1/rules

# Verify alertmanager config
curl http://alertmanager:9093/api/v1/status
```

### **Performance Optimization**

#### **Build Performance**
```bash
# Enable Nx Cloud for distributed caching
npx nx connect-to-nx-cloud

# Optimize Docker builds with BuildKit
export DOCKER_BUILDKIT=1
docker build --cache-from=type=gha --cache-to=type=gha .
```

#### **Test Performance**
```bash
# Parallel test execution
npm run test -- --parallel --max-workers=4

# Use test database optimizations
export TEST_DATABASE_URL=sqlite:///memory:
```

#### **Deployment Performance**
```bash
# Use blue-green deployments
aws ecs update-service --cluster naga-prod \
  --service naga-backend --desired-count 4

# Monitor deployment progress
aws ecs wait services-stable --cluster naga-prod \
  --services naga-backend
```

## 📈 **Performance Metrics**

### **Pipeline Performance Targets**
- **Build Time** → <10 minutes
- **Test Execution** → <5 minutes
- **Security Scan** → <15 minutes
- **Deployment Time** → <10 minutes
- **Total Pipeline** → <30 minutes

### **System Performance Targets**
- **Response Time** → <500ms (95th percentile)
- **Error Rate** → <1%
- **Uptime** → >99.9%
- **Database Connections** → <80% capacity

## 🔐 **Security Best Practices**

### **Pipeline Security**
- Secrets stored in GitHub Secrets
- OIDC authentication for AWS
- Least privilege access policies
- Audit logging enabled

### **Container Security**
- Non-root user containers
- Multi-stage builds
- Regular base image updates
- Vulnerability scanning

### **Network Security**
- VPC with private subnets
- Security groups with minimal access
- TLS encryption in transit
- WAF protection

## 📚 **Additional Resources**

### **Documentation**
- [Nx Workspace Guide](https://nx.dev/getting-started)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Prometheus Monitoring](https://prometheus.io/docs/)
- [Grafana Dashboards](https://grafana.com/docs/)

### **Support Channels**
- **DevOps Team** → devops@pucsr.edu.kh
- **Security Team** → security@pucsr.edu.kh
- **On-call Escalation** → +855-xxx-xxxx

---

*Last Updated: $(date '+%Y-%m-%d')*
*Version: 1.0.0*