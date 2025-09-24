# GitHub Secrets Configuration for Linode VPS Deployment

This document outlines the required GitHub secrets and variables for deploying the Naga SIS monorepo to Linode VPS servers.

## 🔐 Required GitHub Secrets

### Docker Hub Configuration
```
DOCKER_USERNAME       # Your Docker Hub username
DOCKER_PASSWORD       # Your Docker Hub password or access token
```

### Linode Server Access
```
LINODE_SSH_PRIVATE_KEY    # Private SSH key for server access (PEM format)
```

### Application Configuration
```
DATABASE_PASSWORD      # PostgreSQL database password
DJANGO_SECRET_KEY     # Django secret key for production
```

### Optional Notification Secrets
```
DEPLOYMENT_WEBHOOK_URL     # Slack/Discord webhook for deployment notifications
CODECOV_TOKEN             # Codecov token for coverage reporting
```

## 📋 Required GitHub Variables

### Production Environment
```
PRODUCTION_SERVER_HOST    # e.g., "prod.naga-sis.com" or IP address
PRODUCTION_SERVER_USER    # e.g., "deploy" or "ubuntu"
```

### Staging Environment
```
STAGING_SERVER_HOST       # e.g., "staging.naga-sis.com" or IP address  
STAGING_SERVER_USER       # e.g., "deploy" or "ubuntu"
```

## 🚀 Setup Instructions

### 1. Docker Hub Setup
1. Create a Docker Hub account at https://hub.docker.com
2. Create access token: Account Settings → Security → New Access Token
3. Add `DOCKER_USERNAME` and `DOCKER_PASSWORD` to GitHub Secrets

### 2. Linode Server Setup
1. Create Linode VPS instances for staging and production
2. Set up SSH key authentication:
   ```bash
   # Generate SSH key pair
   ssh-keygen -t ed25519 -C "github-actions-deploy"
   
   # Copy public key to servers
   ssh-copy-id -i ~/.ssh/id_ed25519.pub deploy@your-server.com
   ```
3. Add private key content to `LINODE_SSH_PRIVATE_KEY` secret
4. Set server hostnames in GitHub Variables

### 3. Application Configuration
1. Generate Django secret key:
   ```python
   from django.core.management.utils import get_random_secret_key
   print(get_random_secret_key())
   ```
2. Create strong database password
3. Add both to GitHub Secrets

### 4. Server Prerequisites

#### Install Docker and Docker Compose
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### Create Application Directories
```bash
sudo mkdir -p /opt/naga-sis /var/www/naga-sis
sudo chown $USER:$USER /opt/naga-sis /var/www/naga-sis
```

#### Install Nginx (for frontend)
```bash
sudo apt-get update
sudo apt-get install -y nginx
sudo systemctl enable nginx
```

#### Configure Firewall
```bash
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw enable
```

## 🌐 Domain Configuration

### DNS Setup
Point your domains to your Linode server IP addresses:

**Production:**
- `naga-sis.com` → Production server IP
- `api.naga-sis.com` → Production server IP

**Staging:**
- `staging.naga-sis.com` → Staging server IP  
- `api-staging.naga-sis.com` → Staging server IP

### SSL Certificates (Optional)
The deployment configures basic HTTP. For HTTPS, consider:

1. **Let's Encrypt with Certbot:**
   ```bash
   sudo apt-get install certbot python3-certbot-nginx
   sudo certbot --nginx -d naga-sis.com -d api.naga-sis.com
   ```

2. **Cloudflare Proxy:** Enable Cloudflare for automatic SSL

## 🔍 Testing the Setup

### 1. Test SSH Connection
```bash
ssh -i ~/.ssh/id_ed25519 deploy@your-server.com "echo 'SSH connection successful'"
```

### 2. Validate Secrets
Go to your GitHub repository → Settings → Secrets and Variables → Actions
Verify all required secrets and variables are present.

### 3. Manual Workflow Test
1. Go to Actions tab in GitHub
2. Select "Deploy (VPS/Linode)" workflow
3. Click "Run workflow"
4. Choose "staging" environment
5. Monitor deployment logs

## 🚨 Security Best Practices

### SSH Key Management
- Use separate SSH keys for different environments
- Rotate SSH keys regularly
- Use key passphrases when possible
- Restrict SSH key permissions: `chmod 600 ~/.ssh/id_ed25519`

### Server Security
```bash
# Disable root login
sudo sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config

# Disable password authentication
sudo sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config

# Restart SSH
sudo systemctl restart sshd

# Enable automatic security updates
sudo apt-get install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

### Secret Rotation
- Rotate database passwords quarterly
- Update Django secret keys annually  
- Monitor Docker Hub access logs
- Review SSH access logs regularly

## 📞 Troubleshooting

### Common Issues

**SSH Connection Failed:**
- Verify SSH key format (PEM, no passphrase for GitHub Actions)
- Check server hostname/IP in variables
- Ensure SSH key is added to server's authorized_keys

**Docker Hub Login Failed:**
- Verify Docker Hub credentials
- Check if 2FA is enabled (use access token instead of password)
- Ensure Docker Hub repository exists

**Deployment Health Check Failed:**
- Check server firewall settings
- Verify application ports are exposed
- Review Docker container logs on server

**Database Connection Issues:**
- Ensure PostgreSQL container is running
- Verify database password matches secret
- Check network connectivity between containers

### Debug Commands
```bash
# Check deployment status on server
ssh deploy@your-server.com "cd /opt/naga-sis/staging && docker-compose ps"

# View application logs
ssh deploy@your-server.com "cd /opt/naga-sis/staging && docker-compose logs backend"

# Test health endpoint
curl -f https://api-staging.naga-sis.com/health/
```

## 📚 Additional Resources

- [Linode VPS Documentation](https://www.linode.com/docs/)
- [Docker Deployment Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [GitHub Actions Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [Nginx Configuration Guide](https://nginx.org/en/docs/)