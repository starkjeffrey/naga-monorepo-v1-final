#!/bin/bash

# GitHub Actions Runner Startup Script

set -e

echo "Starting GitHub Actions Runner..."

# If runner is not configured, configure it first
if [ ! -f ".runner" ]; then
    echo "Runner not configured. Running configuration..."
    /home/runner/configure-runner.sh
fi

# Cleanup function
cleanup() {
    echo "Removing runner..."
    ./config.sh remove --unattended --token "$GITHUB_TOKEN" || true
    exit 0
}

# Set trap to cleanup on container stop
trap cleanup SIGTERM SIGINT

# Start the runner
echo "Starting runner service..."
./run.sh &

# Wait for the runner process
wait $!