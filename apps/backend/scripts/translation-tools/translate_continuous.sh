#!/bin/bash
# Continuous translation script
# Runs translation in batches until complete

echo "Starting continuous translation..."
echo "Press Ctrl+C to stop"

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Activate the virtual environment
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    echo "Virtual environment activated"
else
    echo "ERROR: Virtual environment not found at $SCRIPT_DIR/.venv"
    echo "Please run: python -m venv .venv && .venv/bin/pip install -r requirements.txt"
    exit 1
fi

# Track batches completed
batch_count=0
batch_size=500  # Increased batch size for faster completion

while true; do
    batch_count=$((batch_count + 1))
    
    # Run translation batch and capture output
    echo ""
    echo "=========================================="
    echo "Running batch #$batch_count (size: $batch_size)..."
    echo "=========================================="
    output=$(python translate_po_batch.py --batch-size $batch_size 2>&1)
    echo "$output"
    
    # Check if complete by looking for the completion message
    if echo "$output" | grep -q "Translation COMPLETE!"; then
        echo ""
        echo "✅ Translation complete!"
        break
    fi
    
    # Check if no entries left to translate
    if echo "$output" | grep -q "No entries left to translate!"; then
        echo ""
        echo "✅ Translation complete!"
        break
    fi
    
    # Check for errors that might cause infinite loop
    if echo "$output" | grep -q "Remaining to translate: 0 entries"; then
        echo ""
        echo "✅ Translation complete (0 remaining)!"
        break
    fi
    
    # Extract remaining count for progress tracking
    remaining=$(echo "$output" | grep "Remaining to translate:" | sed 's/[^0-9]//g')
    if [ -n "$remaining" ]; then
        echo ""
        echo "📊 Progress: $remaining entries remaining"
        echo "⏱️  Estimated batches left: $((($remaining + $batch_size - 1) / $batch_size))"
    fi
    
    # Short pause between batches
    echo "⏳ Waiting 3 seconds before next batch..."
    sleep 3
done

echo ""
echo "🎉 Translation process finished after $batch_count batches!"
echo "📁 Final file location: ../../locale/km/LC_MESSAGES/django_translated.po"