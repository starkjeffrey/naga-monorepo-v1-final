#!/bin/bash
# Update API types from Django backend OpenAPI schema

set -e

echo "🔄 Updating API types from Django backend..."

# Ensure backend is running to generate schema
echo "📋 Generating OpenAPI schema from Django..."
npm run schema:generate

# Check if schema file exists
if [[ ! -f "backend/openapi-schema.json" ]]; then
    echo "❌ OpenAPI schema file not found at backend/openapi-schema.json"
    exit 1
fi

# Generate TypeScript types from OpenAPI schema
echo "🔧 Generating TypeScript types..."
npx openapi-typescript backend/openapi-schema.json -o libs/shared/api-types/src/lib/generated-types.ts

# Build the shared library
echo "🏗️  Building shared API types library..."
nx build api-types

# Notify completion
echo "✅ API types updated successfully!"
echo "📁 Generated types available at: libs/shared/api-types/src/lib/generated-types.ts"
echo "📦 Built library ready for import in frontend and other projects"

# Optional: Run tests to ensure types are valid
if command -v nx &> /dev/null; then
    echo "🧪 Running tests for API types library..."
    nx test api-types
    echo "✅ All tests passed!"
fi