#!/bin/bash

# GitHub Runner Health Check Script
# Checks the status of the self-hosted runner and provides diagnostics

set -e

echo "🏥 GitHub Runner Health Check"
echo "============================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is running
echo -n "Docker Engine: "
if docker info > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Running${NC}"
else
    echo -e "${RED}❌ Not running${NC}"
    echo "Please start Docker Desktop"
    exit 1
fi

# Check if runner container exists
echo -n "Runner Container: "
if docker ps -a | grep -q "naga-github-runner"; then
    echo -e "${GREEN}✅ Exists${NC}"
else
    echo -e "${RED}❌ Not found${NC}"
    echo "Run ./setup-local-runner.sh to create the runner"
    exit 1
fi

# Check if runner is running
echo -n "Runner Status: "
RUNNER_STATUS=$(docker inspect -f '{{.State.Status}}' naga-github-runner 2>/dev/null || echo "unknown")
if [ "$RUNNER_STATUS" = "running" ]; then
    echo -e "${GREEN}✅ Running${NC}"
else
    echo -e "${RED}❌ $RUNNER_STATUS${NC}"
    echo "Start with: docker compose up -d"
fi

# Check runner uptime
if [ "$RUNNER_STATUS" = "running" ]; then
    echo -n "Uptime: "
    UPTIME=$(docker inspect -f '{{.State.StartedAt}}' naga-github-runner)
    echo "$UPTIME"
fi

# Check resource usage
echo ""
echo "📊 Resource Usage:"
if [ "$RUNNER_STATUS" = "running" ]; then
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" naga-github-runner
fi

# Check if .env file exists and has token
echo ""
echo "🔐 Configuration:"
if [ -f ".env" ]; then
    echo -e "Config file: ${GREEN}✅ Found${NC}"
    
    # Check if token is set (without revealing it)
    if grep -q "GITHUB_TOKEN=your_github_personal_access_token_here" .env; then
        echo -e "GitHub Token: ${RED}❌ Not configured${NC}"
        echo "Run ./setup-local-runner.sh to configure"
    else
        echo -e "GitHub Token: ${GREEN}✅ Configured${NC}"
    fi
    
    # Show repository
    REPO=$(grep "GITHUB_REPOSITORY=" .env | cut -d'=' -f2)
    echo "Repository: $REPO"
    
    # Show runner name
    RUNNER_NAME=$(grep "RUNNER_NAME=" .env | cut -d'=' -f2)
    echo "Runner Name: $RUNNER_NAME"
else
    echo -e "Config file: ${RED}❌ Not found${NC}"
    echo "Run ./setup-local-runner.sh to configure"
fi

# Check recent logs for errors
echo ""
echo "📜 Recent Activity:"
if [ "$RUNNER_STATUS" = "running" ]; then
    echo "Last 10 log entries:"
    docker logs --tail=10 naga-github-runner 2>&1 | grep -E "(Listening|Running|Error|Failed)" || echo "No significant events"
fi

# Check GitHub API connectivity
echo ""
echo "🌐 GitHub Connectivity:"
if [ -f ".env" ] && ! grep -q "GITHUB_TOKEN=your_github_personal_access_token_here" .env; then
    # Extract token safely
    source .env
    
    # Test GitHub API
    API_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "Authorization: Bearer $GITHUB_TOKEN" \
        -H "Accept: application/vnd.github.v3+json" \
        https://api.github.com/user)
    
    if [ "$API_RESPONSE" = "200" ]; then
        echo -e "GitHub API: ${GREEN}✅ Connected${NC}"
        
        # Check runner registration
        REPO=$(grep "GITHUB_REPOSITORY=" .env | cut -d'=' -f2)
        RUNNERS_RESPONSE=$(curl -s \
            -H "Authorization: Bearer $GITHUB_TOKEN" \
            -H "Accept: application/vnd.github.v3+json" \
            "https://api.github.com/repos/$REPO/actions/runners")
        
        RUNNER_COUNT=$(echo "$RUNNERS_RESPONSE" | grep -o '"id"' | wc -l)
        echo "Registered Runners: $RUNNER_COUNT"
    else
        echo -e "GitHub API: ${RED}❌ Failed (HTTP $API_RESPONSE)${NC}"
        echo "Check your GitHub token permissions"
    fi
else
    echo -e "GitHub API: ${YELLOW}⚠️  Not checked (no token)${NC}"
fi

# Summary
echo ""
echo "📋 Summary:"
if [ "$RUNNER_STATUS" = "running" ] && [ "$API_RESPONSE" = "200" ]; then
    echo -e "${GREEN}✅ Runner is healthy and ready!${NC}"
    echo ""
    echo "View in GitHub: https://github.com/$REPO/settings/actions/runners"
else
    echo -e "${YELLOW}⚠️  Runner needs attention${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "1. Check logs: docker compose logs -f github-runner"
    echo "2. Restart: docker compose restart"
    echo "3. Reconfigure: ./setup-local-runner.sh"
fi