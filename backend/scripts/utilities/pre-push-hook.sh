#!/bin/bash

# Git pre-push hook - Runs CI checks before pushing to save CI/CD minutes
# Installation: cp scripts/utilities/pre-push-hook.sh .git/hooks/pre-push

echo "🔍 Running pre-push CI validation to save CI/CD minutes..."

# Get the directory where the hook is located
HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HOOK_DIR/../.." && pwd)"

# Run the validation script
if [ -f "$REPO_ROOT/backend/scripts/utilities/validate-ci-locally.sh" ]; then
    "$REPO_ROOT/backend/scripts/utilities/validate-ci-locally.sh"
    result=$?
else
    echo "⚠️  Validation script not found. Proceeding with push..."
    result=0
fi

if [ $result -ne 0 ]; then
    echo ""
    echo "❌ Pre-push validation failed!"
    echo ""
    echo "Options:"
    echo "  1. Fix the issues and try again (recommended)"
    echo "  2. Push anyway with: git push --no-verify"
    echo "  3. Run full GitLab CI locally: ./scripts/utilities/run-gitlab-ci-locally.sh"
    echo ""
    exit 1
fi

echo "✅ Pre-push validation passed!"
exit 0
