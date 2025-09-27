#!/usr/bin/env bash

# MyPy CI Check - New/Modified Files Only
# Only check files that have been changed in this PR/branch

set -euo pipefail

echo "🔍 Checking mypy on new/modified files only..."

# Get the main branch name (usually 'main' or 'master')
MAIN_BRANCH="${MAIN_BRANCH:-main}"

# Check if we're in a git repo and have the main branch
if ! git rev-parse --verify "$MAIN_BRANCH" >/dev/null 2>&1; then
    echo "⚠️ Cannot find main branch '$MAIN_BRANCH', checking all staged files instead"
    FILES=$(git diff --staged --name-only --diff-filter=ACMR | grep '\.py$' || true)
else
    # Get files changed compared to main branch
    FILES=$(git diff "$MAIN_BRANCH"...HEAD --name-only --diff-filter=ACMR | grep '\.py$' || true)
fi

# If no files found, check unstaged changes
if [[ -z "$FILES" ]]; then
    FILES=$(git diff --name-only --diff-filter=ACMR | grep '\.py$' || true)
fi

# If still no files, nothing to check
if [[ -z "$FILES" ]]; then
    echo "✅ No Python files changed - skipping mypy check"
    exit 0
fi

echo "📝 Files to check:"
echo "$FILES" | sed 's/^/  /'
echo ""

# Convert to array
FILE_ARRAY=()
while IFS= read -r file; do
    if [[ -f "$file" && "$file" == *.py ]]; then
        FILE_ARRAY+=("$file")
    fi
done <<< "$FILES"

if [[ ${#FILE_ARRAY[@]} -eq 0 ]]; then
    echo "✅ No valid Python files to check"
    exit 0
fi

echo "🔍 Running mypy on ${#FILE_ARRAY[@]} file(s)..."

# Run mypy only on changed files
if uv run mypy --follow-imports=silent --show-error-codes "${FILE_ARRAY[@]}"; then
    echo "✅ No mypy errors in changed files!"
else
    echo "❌ Found mypy errors in changed files"
    echo "💡 Fix these errors or run: mypy-new-code locally to check"
    exit 1
fi
