#!/usr/bin/env bash

# MyPy Baseline CI Check
# Only fail if NEW mypy errors are introduced compared to baseline

set -euo pipefail

BASELINE_FILE="mypy-baseline.txt"
CURRENT_OUTPUT="mypy-current.txt"

echo "🔍 Running mypy baseline check..."

# Run mypy and capture current errors
uv run mypy --hide-error-context --no-error-summary apps api > "$CURRENT_OUTPUT" 2>&1 || true

# Create baseline if it doesn't exist
if [[ ! -f "$BASELINE_FILE" ]]; then
    echo "📝 Creating initial mypy baseline..."
    cp "$CURRENT_OUTPUT" "$BASELINE_FILE"
    echo "✅ Baseline created with $(wc -l < "$BASELINE_FILE") errors"
    exit 0
fi

# Compare current errors with baseline
BASELINE_COUNT=$(wc -l < "$BASELINE_FILE" | xargs)
CURRENT_COUNT=$(wc -l < "$CURRENT_OUTPUT" | xargs)

echo "📊 Baseline errors: $BASELINE_COUNT"
echo "📊 Current errors:  $CURRENT_COUNT"

if [[ $CURRENT_COUNT -gt $BASELINE_COUNT ]]; then
    echo "❌ NEW mypy errors introduced!"
    echo "📈 Error count increased by: $((CURRENT_COUNT - BASELINE_COUNT))"
    echo ""
    echo "🆕 New errors (not in baseline):"
    comm -13 <(sort "$BASELINE_FILE") <(sort "$CURRENT_OUTPUT")
    exit 1
elif [[ $CURRENT_COUNT -lt $BASELINE_COUNT ]]; then
    echo "🎉 Great! You FIXED $((BASELINE_COUNT - CURRENT_COUNT)) mypy errors!"
    echo "💡 Consider updating the baseline: cp $CURRENT_OUTPUT $BASELINE_FILE"
    exit 0
else
    echo "✅ No new mypy errors introduced"
    exit 0
fi
