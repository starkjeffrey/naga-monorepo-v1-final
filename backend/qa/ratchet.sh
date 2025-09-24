#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

apps_paths="apps api tests"

# --- Run checks and capture metrics ---

# Ruff: count findings by matching "file:line:col:" lines
ruff_out="$(uv run ruff check $apps_paths || true)"
ruff_count="$(printf '%s\n' "$ruff_out" | grep -E '^[^:]+:[0-9]+:[0-9]+:' | wc -l | tr -d ' ')"

# Mypy: count "error:" lines
mypy_out="$(uv run mypy apps api || true)"
mypy_count="$(printf '%s\n' "$mypy_out" | grep -c 'error:' || true)"

# Coverage: run a quick-but-reasonable suite with coverage enabled
# Adjust the command if you prefer a different target (e.g., your full suite)
uv run pytest -q --cov=apps --cov=api --cov-report=term --cov-report=xml || true

# Parse TOTAL % from 'coverage report' (requires coverage to have run)
cov_line="$(uv run coverage report --fail-under=0 | tail -n 1)"
# LAST column is percent like '87%'
coverage_pct="$(printf '%s\n' "$cov_line" | awk '{print $NF}' | tr -d '%')"
coverage_pct="${coverage_pct:-0}"

# --- Compare against baselines ---
base_dir="qa/baselines"
mkdir -p "$base_dir"

read_baseline() {
  local file="$1" default="$2"
  if [ -s "$file" ]; then cat "$file"; else echo "$default"; fi
}

b_ruff="$(read_baseline "$base_dir/ruff.txt" 999999)"
b_mypy="$(read_baseline "$base_dir/mypy.txt" 999999)"
b_cov="$(read_baseline "$base_dir/coverage.txt" 0)"

status=0

echo "Ruff: current=$ruff_count, baseline=$b_ruff (must be <=)"
if [ "$ruff_count" -gt "$b_ruff" ]; then
  echo "❌ Ruff violations increased."
  status=1
fi

echo "Mypy: current=$mypy_count, baseline=$b_mypy (must be <=)"
if [ "$mypy_count" -gt "$b_mypy" ]; then
  echo "❌ Mypy errors increased."
  status=1
fi

echo "Coverage: current=${coverage_pct}%, baseline=${b_cov}% (must be >=)"
if [ "$coverage_pct" -lt "$b_cov" ]; then
  echo "❌ Coverage decreased."
  status=1
fi

# Summary and exit
if [ "$status" -eq 0 ]; then
  echo "✅ Ratchet checks passed (no regressions)."
else
  echo "⚠️  Ratchet failed. Fix issues or update baselines if you intentionally improved/remodeled."
fi

exit "$status"

