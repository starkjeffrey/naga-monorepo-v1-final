#!/bin/bash

# MyPy Cleanup Progress Monitor
# Usage: ./monitor-mypy-cleanup.sh

LOGFILE="logs/mypy_aggressive_cleanup_20250813_170101.log"

echo "🔍 MYPY AGGRESSIVE CLEANUP - LIVE MONITOR"
echo "========================================"
echo "Log file: $LOGFILE"
echo ""

if [ ! -f "$LOGFILE" ]; then
    echo "❌ Log file not found. Task may not have started yet."
    exit 1
fi

echo "📊 Current Status:"
echo "Lines in log: $(wc -l < "$LOGFILE")"
echo "File size: $(ls -lh "$LOGFILE" | awk '{print $5}')"
echo ""

echo "🔥 Live Progress (press Ctrl+C to exit):"
echo "----------------------------------------"

# Follow the log file for live updates
tail -f "$LOGFILE"