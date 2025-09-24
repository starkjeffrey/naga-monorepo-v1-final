#!/bin/bash

# GitHub Actions Runner Configuration Script
# This script configures the runner with your repository

set -e

# Check required environment variables
if [ -z "$GITHUB_TOKEN" ]; then
    echo "Error: GITHUB_TOKEN environment variable is required"
    exit 1
fi

if [ -z "$GITHUB_REPOSITORY" ]; then
    echo "Error: GITHUB_REPOSITORY environment variable is required (format: owner/repo)"
    exit 1
fi

# Default values
RUNNER_NAME=${RUNNER_NAME:-"self-hosted-runner-$(hostname)-$(date +%s)"}
RUNNER_LABELS=${RUNNER_LABELS:-"self-hosted,linux,x64,naga-monorepo"}
RUNNER_GROUP=${RUNNER_GROUP:-"default"}

echo "Configuring GitHub Actions Runner..."
echo "Repository: $GITHUB_REPOSITORY"
echo "Runner Name: $RUNNER_NAME"
echo "Labels: $RUNNER_LABELS"

# Get registration token
echo "Getting registration token from GitHub..."
REGISTRATION_TOKEN=$(curl -s -X POST \
    -H "Authorization: token $GITHUB_TOKEN" \
    -H "Accept: application/vnd.github.v3+json" \
    "https://api.github.com/repos/$GITHUB_REPOSITORY/actions/runners/registration-token" | jq -r .token)

if [ "$REGISTRATION_TOKEN" = "null" ] || [ -z "$REGISTRATION_TOKEN" ]; then
    echo "Error: Failed to get registration token. Check your GITHUB_TOKEN permissions."
    exit 1
fi

echo "Registration token obtained successfully"

# Configure the runner
echo "Configuring runner..."
./config.sh \
    --url "https://github.com/$GITHUB_REPOSITORY" \
    --token "$REGISTRATION_TOKEN" \
    --name "$RUNNER_NAME" \
    --labels "$RUNNER_LABELS" \
    --runnergroup "$RUNNER_GROUP" \
    --work "_work" \
    --unattended \
    --replace

echo "Runner configured successfully!"