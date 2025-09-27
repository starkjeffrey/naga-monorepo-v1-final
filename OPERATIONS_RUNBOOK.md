# Staff-Web V2 Operations Runbook

Comprehensive operations guide for managing the Staff-Web V2 production system.

## Quick Reference

### Emergency Contacts
- **System Administrator**: admin@yourdomain.com
- **Development Team**: dev-team@yourdomain.com
- **Security Team**: security@yourdomain.com

### Critical Service URLs
- **Application**: https://staff.yourdomain.com
- **API**: https://api.yourdomain.com
- **Monitoring**: https://grafana.yourdomain.com
- **Uptime Status**: https://uptime.yourdomain.com

### Quick Commands
```bash
# Health check
./scripts/maintenance/health-check.sh

# View logs
docker-compose -f docker-compose.staff-web-production.yml logs -f

# Emergency rollback
./scripts/deployment/rollback.sh --force

# Create backup
./scripts/backup/backup-system.sh --type database
```

## Daily Operations

### Morning Checklist

**1. System Health Check (5 minutes)**
```bash
# Run comprehensive health check
./scripts/maintenance/health-check.sh --verbose

# Check system resources
df -h
free -h
docker system df
```

**2. Service Status Verification (3 minutes)**
```bash
# Check all services are running
docker-compose -f docker-compose.staff-web-production.yml ps

# Check recent logs for errors
docker-compose -f docker-compose.staff-web-production.yml logs --since="24h" | grep -i error
```

**3. Backup Verification (2 minutes)**
```bash
# Check if last night's backup completed
ls -la /backups/staff-web-v2/ | head -10

# Verify backup file integrity
./scripts/backup/verify-backup.sh --latest
```

### Evening Checklist

**1. Performance Review (5 minutes)**
```bash
# Check Grafana dashboards
# - System Performance
# - Application Metrics
# - Database Performance

# Review top processes
docker stats --no-stream
```

**2. Security Review (3 minutes)**
```bash
# Check fail2ban status
sudo fail2ban-client status

# Review authentication logs
docker-compose -f docker-compose.staff-web-production.yml logs django | grep -i auth | tail -20
```

**3. Prepare for Next Day (2 minutes)**
```bash
# Schedule any pending maintenance
# Update operational notes
# Alert team of any issues
```

## Weekly Operations

### Monday: Security Review

**1. Security Logs Analysis**
```bash
# Review fail2ban logs
sudo journalctl -u fail2ban --since="1 week ago" | grep -i ban

# Check for suspicious access patterns
docker-compose -f docker-compose.staff-web-production.yml logs traefik | grep -i "404\|401\|403" | tail -50

# Review SSL certificate status
echo | openssl s_client -servername yourdomain.com -connect yourdomain.com:443 2>/dev/null | openssl x509 -noout -dates
```

**2. Access Control Review**
```bash
# Review user access logs
docker-compose -f docker-compose.staff-web-production.yml exec django python manage.py shell -c "
from django.contrib.auth.models import User
from django.contrib.admin.models import LogEntry
print('Recent admin actions:')
for entry in LogEntry.objects.select_related('user').order_by('-action_time')[:20]:
    print(f'{entry.action_time}: {entry.user} - {entry.change_message}')
"
```

**3. Vulnerability Scanning**
```bash
# Update system packages
sudo apt update && sudo apt list --upgradable

# Check Docker image vulnerabilities (if tools available)
# docker scan django-image
# docker scan staff-web-image
```

### Tuesday: Performance Optimization

**1. Database Performance Review**
```bash
# Check slow queries
docker-compose -f docker-compose.staff-web-production.yml exec postgres psql -U postgres -d naga_production -c "
SELECT query, mean_time, calls, total_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
"

# Check database size and growth
docker-compose -f docker-compose.staff-web-production.yml exec postgres psql -U postgres -d naga_production -c "
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;
"
```

**2. Application Performance Analysis**
```bash
# Check Django performance metrics in Grafana
# Review response times, error rates, throughput

# Check memory usage patterns
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"
```

**3. Cache Performance**
```bash
# Check Redis statistics
docker-compose -f docker-compose.staff-web-production.yml exec redis redis-cli info stats
docker-compose -f docker-compose.staff-web-production.yml exec redis redis-cli info memory
```

### Wednesday: Backup and Recovery Testing

**1. Backup Verification**
```bash
# Test backup creation
./scripts/backup/backup-system.sh --type database --compress

# Verify backup integrity
./scripts/backup/verify-backup.sh --all

# Test backup restoration (on staging if available)
# ./scripts/deployment/rollback.sh --backup-name test_backup
```

**2. Recovery Procedures Test**
```bash
# Document recovery time objectives (RTO)
# Document recovery point objectives (RPO)
# Test disaster recovery procedures
```

### Thursday: Capacity Planning

**1. Resource Usage Analysis**
```bash
# Analyze growth trends in Grafana
# - Database size growth
# - CPU usage trends
# - Memory usage trends
# - Network traffic patterns

# Check disk space projections
df -h
find /var/lib/docker -type f -size +100M -exec ls -lh {} \; | head -20
```

**2. Performance Baseline Updates**
```bash
# Update performance baselines
# Document any capacity concerns
# Plan for scaling if needed
```

### Friday: Maintenance and Updates

**1. System Updates**
```bash
# Check for available updates
sudo apt list --upgradable

# Update Docker images (if needed)
docker-compose -f docker-compose.staff-web-production.yml pull

# Plan maintenance windows for updates
```

**2. Documentation Updates**
```bash
# Update operational procedures
# Document any configuration changes
# Update runbook with lessons learned
```

## Monthly Operations

### First Monday: Security Audit

**1. Comprehensive Security Review**
```bash
# Review all user accounts
docker-compose -f docker-compose.staff-web-production.yml exec django python manage.py shell -c "
from django.contrib.auth.models import User
print('Active users:', User.objects.filter(is_active=True).count())
print('Admin users:', User.objects.filter(is_superuser=True).count())
print('Recent logins:', User.objects.filter(last_login__gte=timezone.now()-timedelta(days=30)).count())
"

# Review SSL certificates
for domain in yourdomain.com api.yourdomain.com staff.yourdomain.com; do
  echo "Checking $domain:"
  echo | openssl s_client -servername $domain -connect $domain:443 2>/dev/null | openssl x509 -noout -dates
done

# Security configuration audit
./scripts/security/security-audit.sh
```

**2. Dependency Security Review**
```bash
# Check for security updates
# Review dependency vulnerabilities
# Update security policies if needed
```

### Second Monday: Database Maintenance

**1. Database Optimization**
```bash
# Vacuum and analyze database
docker-compose -f docker-compose.staff-web-production.yml exec postgres psql -U postgres -d naga_production -c "VACUUM ANALYZE;"

# Update database statistics
docker-compose -f docker-compose.staff-web-production.yml exec postgres psql -U postgres -d naga_production -c "UPDATE pg_stat_user_tables SET n_tup_ins = 0, n_tup_upd = 0, n_tup_del = 0;"

# Check for unused indexes
docker-compose -f docker-compose.staff-web-production.yml exec postgres psql -U postgres -d naga_production -c "
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0
ORDER BY schemaname, tablename;
"
```

**2. Database Backup Strategy Review**
```bash
# Review backup retention policy
# Test backup restoration
# Update backup procedures if needed
```

### Third Monday: Infrastructure Review

**1. Server Health Assessment**
```bash
# Check server hardware health
# Review system logs for hardware issues
sudo dmesg | grep -i error
sudo journalctl --since="1 month ago" | grep -i error | tail -50

# Check disk health
sudo smartctl -a /dev/sda || echo "smartctl not available"
```

**2. Network and Connectivity**
```bash
# Test external connectivity
curl -I https://yourdomain.com
curl -I https://api.yourdomain.com

# Check DNS resolution
nslookup yourdomain.com
nslookup api.yourdomain.com
```

### Fourth Monday: Disaster Recovery Testing

**1. Full Backup and Recovery Test**
```bash
# Create full system backup
./scripts/backup/backup-system.sh --type full --compress

# Test restoration procedures
# Document recovery times
# Update disaster recovery plan
```

**2. Business Continuity Review**
```bash
# Review recovery time objectives
# Test communication procedures
# Update contact information
```

## Incident Response Procedures

### Severity Levels

**Critical (Severity 1)**: System completely down or major data loss
**High (Severity 2)**: Significant functionality impaired
**Medium (Severity 3)**: Minor functionality issues
**Low (Severity 4)**: Cosmetic issues or enhancement requests

### Incident Response Steps

**1. Initial Response (0-15 minutes)**
```bash
# Acknowledge the incident
# Assess severity level
# Begin investigation

# Quick health check
./scripts/maintenance/health-check.sh --json

# Check system resources
top
df -h
free -h
```

**2. Investigation (15-30 minutes)**
```bash
# Check service logs
docker-compose -f docker-compose.staff-web-production.yml logs --since="1h" | grep -i error

# Check monitoring dashboards
# Review recent changes
# Identify root cause
```

**3. Resolution (30+ minutes)**
```bash
# Apply fix based on root cause
# Test resolution
# Monitor for regression

# If needed, rollback
./scripts/deployment/rollback.sh
```

**4. Post-Incident (After resolution)**
```bash
# Document incident
# Update procedures
# Conduct post-mortem
# Implement preventive measures
```

### Common Issues and Solutions

**Service Won't Start**
```bash
# Check Docker daemon
sudo systemctl status docker

# Check disk space
df -h

# Check memory
free -h

# Restart service
docker-compose -f docker-compose.staff-web-production.yml restart service-name
```

**Database Connection Issues**
```bash
# Check PostgreSQL status
docker-compose -f docker-compose.staff-web-production.yml exec postgres pg_isready

# Check connections
docker-compose -f docker-compose.staff-web-production.yml exec postgres psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"

# Restart PostgreSQL
docker-compose -f docker-compose.staff-web-production.yml restart postgres
```

**High Load/Performance Issues**
```bash
# Check CPU usage
top
htop

# Check I/O usage
iotop

# Check network usage
nethogs

# Scale services if possible
docker-compose -f docker-compose.staff-web-production.yml up -d --scale django=2
```

## Monitoring and Alerting

### Key Metrics to Monitor

**System Metrics:**
- CPU usage > 80%
- Memory usage > 85%
- Disk usage > 80%
- Network latency > 100ms

**Application Metrics:**
- Response time > 2 seconds
- Error rate > 1%
- Database connection pool exhaustion
- Queue length > 100

**Security Metrics:**
- Failed login attempts > 10/minute
- 404 errors > 50/minute
- SSL certificate expiry < 30 days

### Alert Configuration

**Critical Alerts (Immediate Response):**
- System down
- Database unavailable
- SSL certificate expired
- Security breach detected

**Warning Alerts (Response within 1 hour):**
- High resource usage
- Performance degradation
- Backup failures
- Certificate expiring soon

## Maintenance Windows

### Scheduled Maintenance

**Weekly Maintenance Window:**
- Time: Sunday 2:00 AM - 4:00 AM UTC
- Activities: System updates, minor deployments

**Monthly Maintenance Window:**
- Time: First Sunday 1:00 AM - 5:00 AM UTC
- Activities: Major updates, database maintenance

### Emergency Maintenance

**Criteria for Emergency Maintenance:**
- Critical security vulnerability
- Data integrity issues
- System stability problems

**Approval Process:**
1. Assess business impact
2. Get approval from stakeholders
3. Notify users (if possible)
4. Execute maintenance
5. Verify resolution

## Contact Information

### Escalation Matrix

**Level 1**: System Administrator
- Response time: 15 minutes
- Availability: 24/7

**Level 2**: Development Team Lead
- Response time: 30 minutes
- Availability: Business hours + on-call

**Level 3**: Architecture Team
- Response time: 1 hour
- Availability: Business hours

### External Vendors

**Hosting Provider**: [Contact Information]
**DNS Provider**: [Contact Information]
**Monitoring Service**: [Contact Information]

---

**Document Version**: 1.0.0
**Last Updated**: $(date +%Y-%m-%d)
**Next Review**: $(date -d "+3 months" +%Y-%m-%d)