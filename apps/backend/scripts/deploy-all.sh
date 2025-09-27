#!/bin/bash
# Deploy complete infrastructure on Ubuntu dev-01

set -e

echo "🚀 Deploying complete infrastructure on Ubuntu dev-01..."

# Change to project directory
cd /home/ommae/Projects/naga-monorepo/backend

# Start shared Traefik first
echo "🌐 Starting Traefik router..."
docker network create web 2>/dev/null || true
docker compose -f docker-compose.shared.yml up -d

# Wait for Traefik to be ready
echo "⏳ Waiting for Traefik to initialize..."
sleep 10

# Deploy evaluation (now the main environment)
echo ""
echo "🏭 Starting evaluation stack..."
./scripts/deploy-eval.sh

echo ""
echo "✅ Stack deployed successfully!"
echo ""
echo "🌐 URL List:"
echo "  Evaluation (Main System):"
echo "    - App: https://sis-eval.pucsr.edu.kh"
echo "    - Status: https://status.pucsr.edu.kh"
echo "    - Portainer: https://portainer.pucsr.edu.kh"
echo ""
echo "  System:"
echo "    - Traefik: https://traefik.pucsr.edu.kh"
echo ""
echo "📊 Monitor all services:"
echo "  docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"