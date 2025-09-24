
#!/bin/bash

# GitHub Runner Setup Script for Naga Monorepo
# This script helps set up a self-hosted GitHub Actions runner

set -e

echo "🚀 GitHub Actions Self-Hosted Runner Setup"
echo "=========================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker Desktop first."
    echo "   Visit: https://www.docker.com/products/docker-desktop"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker compose &> /dev/null && ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose."
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"
echo ""

# Check if .env file exists
if [ -f ".env" ]; then
    echo "📋 Found existing .env file"
    read -p "Do you want to reconfigure? (y/N): " reconfigure
    if [[ ! "$reconfigure" =~ ^[Yy]$ ]]; then
        echo "Using existing configuration..."
    else
        mv .env .env.backup-$(date +%Y%m%d-%H%M%S)
        echo "Backed up existing .env file"
    fi
fi

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Setting up GitHub Runner configuration..."
    echo ""
    
    # Copy from example
    cp .env.example .env
    
    echo "To set up your GitHub Personal Access Token:"
    echo "1. Go to: https://github.com/settings/tokens"
    echo "2. Click 'Generate new token (classic)'"
    echo "3. Give it a descriptive name (e.g., 'Naga Runner Token')"
    echo "4. Select scopes:"
    echo "   - For private repos: Select 'repo' (full control)"
    echo "   - For public repos: Select 'public_repo' only"
    echo "5. Click 'Generate token' and copy it"
    echo ""
    
    read -p "Enter your GitHub Personal Access Token: " github_token
    
    # Validate token is not empty
    if [ -z "$github_token" ]; then
        echo "❌ Token cannot be empty"
        exit 1
    fi
    
    # Update .env file with token
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/your_github_personal_access_token_here/$github_token/" .env
    else
        # Linux
        sed -i "s/your_github_personal_access_token_here/$github_token/" .env
    fi
    
    echo ""
    read -p "Enter repository (default: starkjeffrey/naga-monorepo): " repo
    if [ ! -z "$repo" ]; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s|starkjeffrey/naga-monorepo|$repo|" .env
        else
            sed -i "s|starkjeffrey/naga-monorepo|$repo|" .env
        fi
    fi
    
    echo ""
    read -p "Enter runner name (default: naga-monorepo-runner): " runner_name
    if [ ! -z "$runner_name" ]; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s/naga-monorepo-runner/$runner_name/" .env
        else
            sed -i "s/naga-monorepo-runner/$runner_name/" .env
        fi
    fi
    
    echo ""
    echo "✅ Configuration saved to .env file"
fi

echo ""
echo "🔨 Building Docker image..."
docker compose build

echo ""
echo "🚀 Starting GitHub Runner..."
docker compose up -d

echo ""
echo "⏳ Waiting for runner to start..."
sleep 5

# Check if runner is running
if docker compose ps | grep -q "running"; then
    echo "✅ Runner is starting up!"
    echo ""
    echo "📊 Checking runner logs..."
    docker compose logs --tail=20 github-runner
    echo ""
    echo "🎯 Next steps:"
    echo "1. Check runner status: docker compose logs -f github-runner"
    echo "2. Verify in GitHub: Settings → Actions → Runners"
    echo "3. Your runner should appear as '$runner_name' (or naga-monorepo-runner)"
    echo ""
    echo "📝 Useful commands:"
    echo "   View logs:  docker compose logs -f github-runner"
    echo "   Stop:       docker compose down"
    echo "   Restart:    docker compose restart"
    echo "   Status:     docker compose ps"
else
    echo "❌ Runner failed to start. Check logs with:"
    echo "   docker compose logs github-runner"
    exit 1
fi

echo ""
echo "✨ Setup complete!"