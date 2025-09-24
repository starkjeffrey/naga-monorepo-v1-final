#!/bin/bash

# Convenience script to start GitHub Self-Hosted Runner

cd "$(dirname "$0")"

echo "🚀 Starting GitHub Self-Hosted Runner..."
echo "=================================="

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ Configuration not found!"
    echo "Run ./setup-local-runner.sh first to configure the runner"
    exit 1
fi

# Check if already running
if docker compose ps 2>/dev/null | grep -q "naga-github-runner.*running"; then
    echo "✅ Runner is already running!"
    echo ""
    echo "To view logs: docker compose logs -f github-runner"
    exit 0
fi

# Start the runner
echo "Starting runner container..."
docker compose up -d

# Wait a moment for startup
echo "⏳ Waiting for runner to start..."
sleep 5

# Check status
if docker compose ps | grep -q "naga-github-runner.*running"; then
    echo ""
    echo "✅ Runner started successfully!"
    echo ""
    echo "📊 Runner Status:"
    docker compose ps
    echo ""
    echo "📝 Next steps:"
    echo "   View logs:    docker compose logs -f github-runner"
    echo "   Check health: ./check-runner-health.sh"
    echo "   Stop runner:  ./runner-stop.sh"
else
    echo ""
    echo "❌ Failed to start runner"
    echo "Check logs with: docker compose logs github-runner"
    exit 1
fi