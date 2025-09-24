# Naga SIS Evaluation Environment Deployment Plan

## Overview

This document provides a comprehensive plan for deploying the Naga SIS evaluation environment to `evaluation.pucsr.edu.kh` with a working database that staff can use for testing and evaluation.

## 🎯 Objective

Deploy a fully functional evaluation environment that allows PUCSR staff to:
- Test all SIS functionality with realistic data
- Evaluate system performance and usability
- Provide feedback before production deployment
- Train staff on the new system

## 📋 Prerequisites

### Server Requirements
- **Linux server** (Ubuntu 20.04+ recommended)
- **Minimum resources**: 4 GB RAM, 2 CPU cores, 50 GB storage
- **Recommended**: 8 GB RAM, 4 CPU cores, 100 GB storage
- **Domain**: `evaluation.pucsr.edu.kh` pointing to server IP
- **SSL certificate** (Let's Encrypt via Traefik)

### Software Requirements
- Docker Engine 20.10+
- Docker Compose 2.0+
- Git
- Basic firewall configuration (ports 80, 443, 22)

## 🚀 Deployment Steps

### Phase 1: Server Setup

1. **Server Preparation**
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
   
   # Reboot to apply group changes
   sudo reboot
   ```

2. **Firewall Configuration**
   ```bash
   sudo ufw allow 22    # SSH
   sudo ufw allow 80    # HTTP
   sudo ufw allow 443   # HTTPS
   sudo ufw enable
   ```

### Phase 2: Code Deployment

1. **Clone Repository**
   ```bash
   cd /opt
   sudo git clone https://github.com/jpucsr/naga-monorepo.git
   sudo chown -R $USER:$USER naga-monorepo
   cd naga-monorepo/backend
   ```

2. **Environment Configuration**
   ```bash
   # Copy and modify environment files
   cp .envs/.evaluation/.django.example .envs/.evaluation/.django
   cp .envs/.evaluation/.postgres.example .envs/.evaluation/.postgres
   
   # Generate secure secrets
   DJANGO_SECRET=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
   POSTGRES_PASSWORD=$(openssl rand -base64 32)
   
   # Update .envs/.evaluation/.django
   sed -i "s/CHANGE_ME_IN_PRODUCTION_EVALUATION_ENV/$DJANGO_SECRET/" .envs/.evaluation/.django
   
   # Update .envs/.evaluation/.postgres  
   sed -i "s/CHANGE_ME_POSTGRES_PASSWORD/$POSTGRES_PASSWORD/" .envs/.evaluation/.postgres
   sed -i "s/CHANGE_ME_POSTGRES_PASSWORD/$POSTGRES_PASSWORD/" .envs/.evaluation/.django
   ```

### Phase 3: Database Setup

1. **Start Database Services**
   ```bash
   # Start only database and redis initially
   docker compose -f docker-compose.evaluation.yml up -d postgres redis
   
   # Wait for database to be ready
   docker compose -f docker-compose.evaluation.yml logs postgres
   ```

2. **Database Migration and Setup**
   ```bash
   # Run migrations
   docker compose -f docker-compose.evaluation.yml run --rm django python manage.py migrate
   
   # Create superuser (interactive)
   docker compose -f docker-compose.evaluation.yml run --rm django python manage.py createsuperuser
   
   # Load initial data
   docker compose -f docker-compose.evaluation.yml run --rm django python manage.py loaddata \
       data/curriculum_foundation_fixtures.json \
       data/curriculum_terms_fixtures.json \
       data/curriculum_courses_fixtures.json \
       data/rooms_fixture.json \
       data/holidays_fixtures.json \
       data/scholarships_sponsors_fixtures.json
   ```

### Phase 4: Sample Data Population

1. **Academic Data Setup**
   ```bash
   # Load canonical requirements
   docker compose -f docker-compose.evaluation.yml run --rm django \
       python manage.py load_canonical_requirements data/academic_canonical_requirements_fixtures.json
   
   # Create sample students (run custom management command)
   docker compose -f docker-compose.evaluation.yml run --rm django \
       python manage.py create_sample_students --count=100
   
   # Create sample enrollments for current term
   docker compose -f docker-compose.evaluation.yml run --rm django \
       python manage.py create_sample_enrollments --term-code=current
   ```

2. **Staff and Faculty Setup**
   ```bash
   # Create sample staff accounts
   docker compose -f docker-compose.evaluation.yml run --rm django \
       python manage.py create_sample_staff
   
   # Create sample classes with schedules
   docker compose -f docker-compose.evaluation.yml run --rm django \
       python manage.py create_sample_classes --term-code=current
   ```

### Phase 5: Full System Deployment

1. **Deploy All Services**
   ```bash
   # Deploy complete stack
   docker compose -f docker-compose.evaluation.yml up -d
   
   # Monitor deployment
   docker compose -f docker-compose.evaluation.yml logs -f
   ```

2. **SSL Certificate Setup**
   ```bash
   # Traefik will automatically request Let's Encrypt certificates
   # Monitor certificate generation
   docker compose -f docker-compose.evaluation.yml logs traefik
   ```

### Phase 6: System Verification

1. **Health Checks**
   ```bash
   # Check all services
   docker compose -f docker-compose.evaluation.yml ps
   
   # Test database connectivity
   docker compose -f docker-compose.evaluation.yml exec django python manage.py dbshell
   
   # Test admin access
   curl -f https://evaluation.pucsr.edu.kh/admin-evaluation/
   ```

2. **Monitoring Setup**
   - Uptime Kuma: `https://uptime.evaluation.pucsr.edu.kh`
   - Netdata: `https://netdata.evaluation.pucsr.edu.kh`
   - Prometheus: `https://prometheus.evaluation.pucsr.edu.kh`

## 🗃️ Database Content Strategy

### Core Academic Data
- **Programs**: BA in Business Administration, BA in TESOL
- **Courses**: Complete course catalog with prerequisites
- **Terms**: Current and recent academic terms
- **Requirements**: Graduation requirements for all programs

### Sample Student Data (100+ students)
- **Demographics**: Realistic names, IDs, contact information
- **Enrollments**: Current and historical enrollments
- **Academic Progress**: Grades, GPA calculations
- **Financial Records**: Invoices, payments, scholarships

### Faculty and Staff Data
- **User Accounts**: Role-based access (Admin, Faculty, Staff, Student)
- **Class Schedules**: Complete schedules for current term
- **Room Assignments**: Realistic room usage

### Operational Data
- **Attendance Records**: Sample attendance data
- **Grade Records**: Realistic grade distributions
- **Financial Transactions**: Payment histories, scholarships
- **Academic Records**: Transcripts, degree progress tracking

## 🔧 Configuration Files

### Key Environment Variables
```bash
# Django
DJANGO_SETTINGS_MODULE=config.settings.evaluation
DJANGO_ALLOWED_HOSTS=evaluation.pucsr.edu.kh
DJANGO_ADMIN_URL=admin-evaluation/

# Database
POSTGRES_DB=naga_evaluation
POSTGRES_USER=naga_evaluation_user

# Security
DJANGO_SECURE_SSL_REDIRECT=True
DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=True

# Email
DJANGO_DEFAULT_FROM_EMAIL="Naga SIS Evaluation <noreply@evaluation.pucsr.edu.kh>"
```

### Docker Compose Configuration
- Uses production-ready Docker images
- Includes monitoring stack (Uptime Kuma, Netdata, Prometheus)
- SSL termination via Traefik
- Data persistence with named volumes

## 📊 Monitoring and Maintenance

### Automated Monitoring
- **Uptime monitoring** for all services
- **Performance metrics** via Netdata
- **Application metrics** via Prometheus
- **Error tracking** via Sentry (optional)

### Backup Strategy
```bash
# Database backup
docker compose -f docker-compose.evaluation.yml exec postgres backup

# Media files backup
docker cp naga_evaluation_django:/app/mediafiles ./mediafiles-backup/

# Environment backup
cp -r .envs/.evaluation/ ./env-backup/
```

### Log Management
```bash
# View application logs
docker compose -f docker-compose.evaluation.yml logs django

# Database logs
docker compose -f docker-compose.evaluation.yml logs postgres

# All services
docker compose -f docker-compose.evaluation.yml logs
```

## 👥 User Access and Training

### Admin Accounts
- **Superuser**: Full system access
- **Academic Admin**: Student records, grades, transcripts
- **Financial Admin**: Billing, payments, scholarships
- **Faculty**: Course management, grades, attendance

### Student Accounts
- **Sample logins** for different student types
- **Mobile-friendly interface** for attendance
- **Grade and schedule viewing**

### Training Materials
- **Admin documentation** for each module
- **User guides** for common tasks
- **Video tutorials** for key workflows
- **FAQ** for common issues

## 🔄 Update and Maintenance Procedures

### Regular Updates
```bash
# Pull latest code
git pull origin main

# Rebuild images
docker compose -f docker-compose.evaluation.yml build

# Deploy updates
docker compose -f docker-compose.evaluation.yml up -d

# Run migrations
docker compose -f docker-compose.evaluation.yml run --rm django python manage.py migrate
```

### Data Refresh
```bash
# Reset to clean state (careful!)
docker compose -f docker-compose.evaluation.yml down -v
docker compose -f docker-compose.evaluation.yml up -d postgres redis
# Re-run database setup steps
```

## 🚨 Troubleshooting

### Common Issues
1. **SSL Certificate Issues**: Check Traefik logs and DNS configuration
2. **Database Connection**: Verify PostgreSQL service health
3. **Memory Issues**: Monitor with Netdata, adjust container limits
4. **Performance**: Check Django logs and database queries

### Emergency Procedures
```bash
# Stop all services
docker compose -f docker-compose.evaluation.yml down

# Start in debug mode
docker compose -f docker-compose.evaluation.yml up

# Access Django shell
docker compose -f docker-compose.evaluation.yml run --rm django python manage.py shell
```

## ✅ Success Criteria

The evaluation environment is ready when:
- [ ] All services are running and healthy
- [ ] SSL certificates are active
- [ ] Admin interface is accessible
- [ ] Sample data is loaded and realistic
- [ ] All major SIS functions work correctly
- [ ] Monitoring dashboards are operational
- [ ] Staff can log in and perform typical tasks
- [ ] System performance meets expectations

## 📞 Support and Feedback

### Feedback Collection
- Document any issues or suggestions
- Monitor system usage and performance
- Collect user feedback on interface and functionality
- Track system reliability and uptime

### Next Steps
Based on evaluation feedback:
1. Address any critical issues
2. Implement requested features
3. Performance optimizations
4. Plan production deployment
5. Develop staff training program

## 🔗 Quick Links

- **Main Application**: https://evaluation.pucsr.edu.kh
- **Admin Interface**: https://evaluation.pucsr.edu.kh/admin-evaluation/
- **Uptime Monitoring**: https://uptime.evaluation.pucsr.edu.kh
- **System Metrics**: https://netdata.evaluation.pucsr.edu.kh
- **Application Metrics**: https://prometheus.evaluation.pucsr.edu.kh

---

This evaluation environment provides a comprehensive testing platform for PUCSR staff to evaluate the Naga SIS system before production deployment.