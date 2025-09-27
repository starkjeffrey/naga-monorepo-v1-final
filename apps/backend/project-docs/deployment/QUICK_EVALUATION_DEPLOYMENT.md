# Quick Evaluation Deployment Guide

## 🎯 Goal: Get evaluation.pucsr.edu.kh running ASAP with minimal maintenance

### Prerequisites
- Server with Docker installed
- Your existing `*.pucsr.edu.kh` SSL certificate
- Reverse proxy (nginx/Apache) already configured

## 🚀 Super Quick Deployment (10 minutes)

### 1. **Deploy Code**
```bash
# From your local machine
./deploy-evaluation.sh your-server-ip

# OR manually:
rsync -avz --exclude='__pycache__' --exclude '*.pyc' --exclude 'data/legacy' \
    ./ user@server:/opt/naga-evaluation/
```

### 2. **Database Strategy** (Choose one)

**Option A: Use Your Clean Backup** (Recommended - 2 minutes)
```bash
# Copy your existing clean backup to server
scp backups/CLEAN_BASELINE_naga_local_2025_07_15T08_25_41.sql.gz \
    user@server:/opt/naga-evaluation/

# On server:
cd /opt/naga-evaluation
docker compose -f docker-compose.evaluation.yml up -d postgres redis
sleep 30
gunzip -c CLEAN_BASELINE_naga_local_2025_07_15T08_25_41.sql.gz | \
    docker compose -f docker-compose.evaluation.yml exec -T postgres \
    psql -U postgres -d naga_evaluation
```

**Option B: Fresh Database** (5 minutes)
```bash
cd /opt/naga-evaluation
docker compose -f docker-compose.evaluation.yml up -d postgres redis
sleep 30
docker compose -f docker-compose.evaluation.yml run --rm django python manage.py migrate
docker compose -f docker-compose.evaluation.yml run --rm django python manage.py createsuperuser
```

### 3. **Start Services**
```bash
cd /opt/naga-evaluation
docker compose -f docker-compose.evaluation.yml up -d
```

### 4. **Configure Your Reverse Proxy**
Add to your existing nginx/Apache config:

**Nginx Example:**
```nginx
server {
    listen 443 ssl;
    server_name evaluation.pucsr.edu.kh;
    
    ssl_certificate /path/to/your/pucsr.edu.kh.crt;
    ssl_certificate_key /path/to/your/pucsr.edu.kh.key;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /static/ {
        proxy_pass http://localhost:8000/static/;
    }
    
    location /media/ {
        proxy_pass http://localhost:8000/media/;
    }
}
```

## 🎛️ Performance Optimizations (Already Included)

✅ **PostgreSQL**: Optimized for 1-4GB RAM servers  
✅ **Redis Caching**: 5-minute cache with connection pooling  
✅ **Django**: Longer connection pooling, session caching  
✅ **Container Limits**: Right-sized for evaluation workload  

## 🔧 Minimal Maintenance Commands

**Check Status:**
```bash
docker compose -f docker-compose.evaluation.yml ps
```

**View Logs:**
```bash
docker compose -f docker-compose.evaluation.yml logs -f django
```

**Restart if Needed:**
```bash
docker compose -f docker-compose.evaluation.yml restart django
```

**Quick Update (when you push changes):**
```bash
git pull
docker compose -f docker-compose.evaluation.yml build django
docker compose -f docker-compose.evaluation.yml up -d django
```

## 🎯 What Staff Can Test

With your clean database, they can immediately test:
- **Login/Authentication** - All existing accounts work
- **Student Records** - Browse/search existing students  
- **Academic Management** - Classes, enrollments, grades
- **Financial System** - Invoices, payments, scholarships
- **Reporting** - All existing reports work
- **Admin Interface** - Full admin functionality

## 💡 Pro Tips for Low Maintenance

1. **Use Your Clean Backup**: Contains realistic data, saves setup time
2. **Point-in-Time Restore**: If anything breaks, just restore backup again
3. **Monitor with Existing Tools**: Your server monitoring should catch issues
4. **Staff Feedback**: Ask them to focus on critical workflows only
5. **Don't Over-Engineer**: This is temporary evaluation, not production

## 🆘 Troubleshooting (2-minute fixes)

**Service Won't Start:**
```bash
docker compose -f docker-compose.evaluation.yml logs [service-name]
```

**Database Issues:**
```bash
# Restore from backup again
docker compose -f docker-compose.evaluation.yml down postgres
docker volume rm naga_evaluation_postgres_data
docker compose -f docker-compose.evaluation.yml up -d postgres
# Re-restore backup
```

**Performance Issues:**
```bash
# Check resource usage
docker stats
# If needed, restart services
docker compose -f docker-compose.evaluation.yml restart
```

## 🎉 Success Metrics

**Ready for Staff Testing When:**
- [ ] https://evaluation.pucsr.edu.kh loads
- [ ] Admin login works: https://evaluation.pucsr.edu.kh/admin-evaluation/
- [ ] Can browse students, courses, enrollments
- [ ] Page load times < 3 seconds
- [ ] No obvious errors in logs

**Expected Performance:**
- **Page loads**: 1-3 seconds (good enough for evaluation)
- **Database queries**: < 500ms typical
- **Admin operations**: Responsive enough for staff testing
- **Concurrent users**: 5-10 staff members simultaneously

This setup gives you a **functional evaluation environment** with **minimal ongoing maintenance** - perfect for letting staff "kick the tires" without major time investment!