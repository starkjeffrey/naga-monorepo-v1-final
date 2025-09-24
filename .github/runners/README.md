# Self-Hosted GitHub Actions Runners

This directory contains configuration for setting up self-hosted GitHub Actions runners to eliminate GitHub-hosted runner charges.

## 🚀 Quick Start with Docker

### Prerequisites
- Docker and Docker Compose installed
- GitHub Personal Access Token with `repo` permissions

### Setup Steps

1. **Create GitHub Personal Access Token**
   ```bash
   # Go to: https://github.com/settings/tokens
   # Create token with 'repo' scope (or 'public_repo' for public repos)
   ```

2. **Configure Environment**
   ```bash
   cd .github/runners
   cp .env.example .env
   # Edit .env with your GitHub token and repository
   ```

3. **Start the Runner**
   ```bash
   docker-compose up -d
   ```

4. **Verify Runner Registration**
   ```bash
   # Check runner logs
   docker-compose logs -f github-runner
   
   # Verify in GitHub: Settings → Actions → Runners
   ```

## 🔧 Configuration Options

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GITHUB_TOKEN` | ✅ | - | GitHub Personal Access Token |
| `GITHUB_REPOSITORY` | ✅ | `starkjeffrey/naga-monorepo` | Repository name |
| `RUNNER_NAME` | ❌ | `naga-monorepo-runner` | Custom runner name |
| `RUNNER_LABELS` | ❌ | `self-hosted,linux,x64,naga-monorepo,docker` | Runner labels |
| `RUNNER_GROUP` | ❌ | `default` | Runner group |

### Runner Labels for Targeting

Update your workflow files to target specific runners:

```yaml
jobs:
  test:
    runs-on: [self-hosted, naga-monorepo]  # Target by labels
    # or
    runs-on: self-hosted  # Any self-hosted runner
```

## 📦 What's Included

The Docker runner includes:
- ✅ **Ubuntu 22.04** base system
- ✅ **Node.js 20.15.0** for frontend builds
- ✅ **Python 3.13.7 + UV** for backend development
- ✅ **Docker-in-Docker** for container builds
- ✅ **PostgreSQL & Redis clients** for testing
- ✅ **GitHub CLI** for advanced GitHub integration
- ✅ **Build tools** and system dependencies

## 🏗️ Alternative: Native Installation

If you prefer not to use Docker:

### Install on Ubuntu/Debian Server

```bash
# 1. Install system dependencies
sudo apt update
sudo apt install -y curl wget git build-essential python3 python3-pip nodejs npm postgresql-client redis-tools

# 2. Install UV for Python
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Install Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# 4. Download GitHub Actions runner
mkdir actions-runner && cd actions-runner
curl -o actions-runner-linux-x64-2.321.0.tar.gz -L https://github.com/actions/runner/releases/download/v2.321.0/actions-runner-linux-x64-2.321.0.tar.gz
tar xzf ./actions-runner-linux-x64-2.321.0.tar.gz

# 5. Configure runner
./config.sh --url https://github.com/starkjeffrey/naga-monorepo --token YOUR_TOKEN

# 6. Install as service (optional)
sudo ./svc.sh install
sudo ./svc.sh start
```

## 🔒 Security Considerations

### Token Permissions
- Use **Personal Access Token** (classic) with minimal required permissions
- For private repos: `repo` scope
- For public repos: `public_repo` scope
- Consider using **GitHub App** for enhanced security

### Runner Security
- ✅ Runs in isolated Docker container
- ✅ Non-root user execution
- ✅ Resource limits configured
- ⚠️ Has Docker socket access (required for builds)
- ⚠️ Can access your repository code

### Network Security
```yaml
# In docker-compose.yml - restrict network access
networks:
  runner-net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

## 📊 Cost Savings

### GitHub-Hosted vs Self-Hosted

| Runner Type | Cost | Specs | Notes |
|-------------|------|-------|--------|
| GitHub-Hosted | $0.008/min | 2 CPU, 7GB RAM | Charges per minute |
| Self-Hosted | $0 | Your hardware | One-time setup |

**Example Monthly Savings:**
- 100 workflow runs/month × 10 minutes average = 1,000 minutes
- GitHub cost: 1,000 × $0.008 = **$8/month**
- Self-hosted cost: **$0/month** (after setup)

## 🚨 Troubleshooting

### Runner Not Appearing
```bash
# Check logs
docker-compose logs github-runner

# Verify token permissions
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/user

# Re-register runner
docker-compose down
docker-compose up -d
```

### Build Failures
```bash
# Check runner system resources
docker stats naga-github-runner

# Increase memory/CPU limits in docker-compose.yml
# Check for conflicting ports (PostgreSQL: 5433, Redis: 6380)
```

### Docker Issues
```bash
# Verify Docker socket mount
docker exec naga-github-runner docker ps

# Check Docker daemon access
docker exec naga-github-runner docker info
```

## 🔄 Management Commands

```bash
# Start runner
docker-compose up -d

# Stop runner
docker-compose down

# View logs
docker-compose logs -f github-runner

# Restart runner
docker-compose restart github-runner

# Update runner
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Remove runner (unregisters from GitHub)
docker-compose down -v
```

## 📈 Monitoring

### Resource Usage
```bash
# Monitor resource usage
docker stats naga-github-runner

# Check disk usage
docker system df
```

### Logs
```bash
# Runner logs
docker-compose logs -f github-runner

# System logs
sudo journalctl -u docker -f
```

## 🎯 Multiple Runners

For better performance, run multiple runners:

```bash
# Scale to 3 runners
docker-compose up -d --scale github-runner=3

# Or create separate compose files for different runner types
docker-compose -f docker-compose.build.yml up -d  # For builds
docker-compose -f docker-compose.test.yml up -d   # For tests
```