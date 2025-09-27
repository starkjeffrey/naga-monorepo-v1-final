#!/bin/bash
# Deploy evaluation stack on Ubuntu dev-01

set -e

echo "🚀 Deploying EVALUATION stack on Ubuntu dev-01..."

# Change to project directory
cd /home/ommae/Projects/naga-monorepo/backend

# Check for certificate
if [ ! -f "compose/traefik/certs/wildcard.pucsr.edu.kh.crt" ]; then
    echo "❌ Wildcard certificate not found!"
    echo "Add certificate to compose/traefik/certs/ first"
    exit 1
fi

# Load eval environment
if [ -f ".env.eval" ]; then
    export $(cat .env.eval | grep -v '^#' | xargs)
else
    echo "❌ .env.eval file not found!"
    echo "Copy .env.eval.example to .env.eval and configure it first"
    exit 1
fi

# Create network if it doesn't exist
docker network create web 2>/dev/null || true

# Stop existing services (if any)
docker compose -f docker-compose.eval.yml down --remove-orphans

# Build production image
echo "🔨 Building production Django image..."
docker compose -f docker-compose.eval.yml build

# Start services
echo "🚀 Starting evaluation services..."
docker compose -f docker-compose.eval.yml up -d

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
sleep 20

# Run migrations
echo "🗃️ Running database migrations..."
docker compose -f docker-compose.eval.yml exec -T django python manage.py migrate

# Collect static files
echo "📦 Collecting static files..."
docker compose -f docker-compose.eval.yml exec -T django python manage.py collectstatic --noinput

# Check deployment
echo "🔍 Checking deployment..."
docker compose -f docker-compose.eval.yml exec -T django python manage.py check --deploy

echo "✅ Evaluation stack deployed!"
echo ""
echo "🌐 URLs:"
echo "  - App: https://sis-eval.pucsr.edu.kh"
echo "  - Status: https://status.pucsr.edu.kh"
echo "  - Portainer: https://portainer.pucsr.edu.kh"
echo "  - Silk Profiler: https://sis-eval.pucsr.edu.kh/silk/"
echo ""
echo "👤 Create Django superuser:"
echo "  docker compose -f docker-compose.eval.yml exec django python manage.py createsuperuser"
echo ""
echo "📊 Check logs with:"
echo "  docker compose -f docker-compose.eval.yml logs -f"