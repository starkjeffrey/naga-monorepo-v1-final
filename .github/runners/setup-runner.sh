#!/bin/bash

# GitHub Actions Self-Hosted Runner Setup Script
# Quick setup for Naga monorepo self-hosted runners

set -e

echo "🚀 Setting up GitHub Actions Self-Hosted Runner for Naga Monorepo"
echo "==============================================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first:"
    echo "   https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first:"
    echo "   https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    
    echo ""
    echo "⚠️  Please edit .env file with your GitHub credentials:"
    echo "   1. Get GitHub token: https://github.com/settings/tokens"
    echo "   2. Edit .env file: nano .env"
    echo "   3. Set GITHUB_TOKEN and GITHUB_REPOSITORY"
    echo ""
    read -p "Press Enter after editing .env file..."
fi

# Validate environment
source .env

if [ -z "$GITHUB_TOKEN" ] || [ "$GITHUB_TOKEN" = "ghp_your_token_here" ]; then
    echo "❌ Please set GITHUB_TOKEN in .env file"
    exit 1
fi

if [ -z "$GITHUB_REPOSITORY" ]; then
    echo "❌ Please set GITHUB_REPOSITORY in .env file"
    exit 1
fi

echo "✅ Environment configuration validated"

# Test GitHub token
echo "🔐 Testing GitHub token..."
RESPONSE=$(curl -s -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user)
if echo "$RESPONSE" | grep -q '"login"'; then
    USERNAME=$(echo "$RESPONSE" | grep '"login"' | cut -d'"' -f4)
    echo "✅ GitHub token valid for user: $USERNAME"
else
    echo "❌ GitHub token is invalid or expired"
    exit 1
fi

# Build and start runner
echo "🏗️  Building runner Docker image..."
docker-compose build

echo "🚀 Starting GitHub Actions runner..."
docker-compose up -d

echo "📊 Checking runner status..."
sleep 10
docker-compose logs github-runner

echo ""
echo "✅ GitHub Actions Runner Setup Complete!"
echo ""
echo "📍 Next steps:"
echo "   1. Check runner status: docker-compose logs -f github-runner"
echo "   2. Verify in GitHub: https://github.com/$GITHUB_REPOSITORY/settings/actions/runners"
echo "   3. Monitor resource usage: docker stats naga-github-runner"
echo ""
echo "💰 Cost savings: You're now using self-hosted runners instead of paying for GitHub-hosted runners!"
echo ""
echo "🔧 Management commands:"
echo "   Start:   docker-compose up -d"
echo "   Stop:    docker-compose down"
echo "   Logs:    docker-compose logs -f github-runner"
echo "   Restart: docker-compose restart github-runner"