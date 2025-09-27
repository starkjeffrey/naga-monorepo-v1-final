#!/usr/bin/env bash
set -euo pipefail

# Generate a breakdown of mypy attr-defined errors by file for apps/ and api/

ROOT_DIR=$(git rev-parse --show-toplevel)
cd "$ROOT_DIR/backend"

OUT_DIR="scripts/utilities/reports"
mkdir -p "$OUT_DIR"
REPORT="$OUT_DIR/mypy_attr_defined_report.txt"

echo "Running mypy (attr-defined report) for apps/ and api/ ..." >&2

uv run mypy --hide-error-context --no-error-summary apps api 2>&1 \
  | rg ": error:" \
  | rg "\[attr-defined\]" \
  | tee >(wc -l | awk '{print "Total attr-defined errors: "$1}' > "$REPORT") \
  | awk -F":" '{print $1}' \
  | sort \
  | uniq -c \
  | sort -nr \
  | tee -a "$REPORT"

echo "\nReport written to: $REPORT" >&2

