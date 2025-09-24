#!/bin/bash

# Test GitHub Workflows Locally
# This script simulates the CI environment for testing

set -e

echo "🚀 Testing GitHub Workflows Locally"
echo "=================================="

# Check if we're in the right directory
if [[ ! -f "nx.json" ]]; then
    echo "❌ Error: Run this script from the repository root"
    exit 1
fi

# Test Nx workspace setup
echo "📦 Testing Nx workspace..."
npx nx show projects
echo "✅ Nx workspace OK"

# Test affected projects detection
echo "📊 Testing affected projects detection..."
AFFECTED=$(npx nx show projects --affected --base=HEAD~1 --head=HEAD --json | jq -r '.[]' | tr '\n' ',' | sed 's/,$//')
echo "Affected projects: $AFFECTED"

# Test frontend if affected
if echo "$AFFECTED" | grep -q "frontend"; then
    echo "🎨 Testing frontend..."
    npx nx lint frontend || echo "⚠️  Frontend linting issues (non-blocking)"
    npx nx test frontend || echo "⚠️  Frontend tests failed"
    echo "✅ Frontend tests completed"
fi

# Test backend if affected  
if echo "$AFFECTED" | grep -q "backend"; then
    echo "🐍 Testing backend..."
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        echo "❌ Docker is not running. Please start Docker Desktop."
        exit 1
    fi
    
    # Start services
    echo "🐳 Starting backend services..."
    cd backend
    docker compose -f docker-compose.local.yml up -d postgres redis
    
    # Wait for services
    echo "⏳ Waiting for services to be ready..."
    timeout 60 bash -c 'until docker compose -f docker-compose.local.yml exec postgres pg_isready; do sleep 1; done'
    timeout 60 bash -c 'until docker compose -f docker-compose.local.yml exec redis redis-cli ping; do sleep 1; done'
    
    # Run migrations
    echo "🗄️ Running migrations..."
    docker compose -f docker-compose.local.yml run --rm django python manage.py migrate
    
    # Run tests
    echo "🧪 Running backend tests..."
    docker compose -f docker-compose.local.yml run --rm \
        -e DJANGO_SETTINGS_MODULE=config.settings.ci \
        django pytest apps/ -v --tb=short --maxfail=5 || echo "⚠️  Some backend tests failed"
    
    # Cleanup
    echo "🧹 Cleaning up..."
    docker compose -f docker-compose.local.yml down
    cd ..
    
    echo "✅ Backend tests completed"
fi

# Test shared API types if affected
if echo "$AFFECTED" | grep -q "api-types"; then
    echo "🔄 Testing shared API types..."
    npx nx test api-types || echo "⚠️  API types tests failed"
    echo "✅ API types tests completed"
fi

echo ""
echo "🎉 Local workflow testing completed!"
echo "📝 Summary:"
echo "   - Affected projects: $AFFECTED"
echo "   - Check above for any ⚠️  warnings"
echo ""
echo "💡 To run the actual GitHub workflows:"
echo "   1. Push to main/develop branch"  
echo "   2. Create a pull request"
echo "   3. Or manually trigger via GitHub Actions tab"