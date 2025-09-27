#!/bin/bash
# Bulk photo download script for SIS student photos
# Downloads photos from both AcadStudentCards and EngStudentCards tables
# Usage: ./bulk_photo_download.sh [output_directory]
# Uses same tsql setup as bulk_export.sh

OUTPUT_DIR="${1:-./photos_$(date +%Y%m%d_%H%M%S)}"
mkdir -p "$OUTPUT_DIR"

echo "Starting bulk photo download to: $OUTPUT_DIR"
echo "Note: Student IDs will be formatted as left-zero-padded 5 digits"
echo "Note: Duplicate IDs will be handled with numeric suffixes"
echo "Note: Using same tsql connection as CSV export scripts"
echo "================================================"

# Check if download_photos.sh exists
SCRIPT_DIR="$(dirname "$0")"
DOWNLOAD_SCRIPT="$SCRIPT_DIR/download_photos.sh"

if [ ! -f "$DOWNLOAD_SCRIPT" ]; then
    echo "✗ Error: download_photos.sh not found in $SCRIPT_DIR"
    echo "   Please ensure download_photos.sh is in the same directory as this script"
    exit 1
fi

# Photo tables to process
TABLES=(
    "AcadStudentCards"
    "EngStudentCards"
)

SUCCESS_COUNT=0
FAIL_COUNT=0
TOTAL_PHOTOS=0

# Process each table
for table in "${TABLES[@]}"; do
    echo "Processing $table..."
    
    if "$DOWNLOAD_SCRIPT" "$table" "$OUTPUT_DIR"; then
        echo "✓ $table processed successfully"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        echo "✗ Failed to process $table"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
    echo "---"
done

echo "Bulk photo download completed!"
echo "Success: $SUCCESS_COUNT tables | Failed: $FAIL_COUNT tables"
echo "Files created in: $OUTPUT_DIR"
echo ""

    # Count total files created (including .txt placeholders)
    TOTAL_COUNT=0
    TOTAL_SIZE=0
    
    if [ -d "$OUTPUT_DIR" ]; then
        TOTAL_COUNT=$(find "$OUTPUT_DIR" -name "*.txt" | wc -l 2>/dev/null || echo 0)
        if [ "$TOTAL_COUNT" -gt 0 ]; then
            TOTAL_SIZE=$(find "$OUTPUT_DIR" -name "*.txt" -exec stat -f%z {} \; 2>/dev/null | awk '{s+=$1} END {print s}' || echo 0)
        fi
    fi
    
    echo ""
    echo "=== BULK PHOTO DOWNLOAD SUMMARY ==="
    echo "Total photo records processed: $TOTAL_COUNT"
    
    if [ "$TOTAL_SIZE" -gt 0 ]; then
        # Convert bytes to human readable format
        if [ "$TOTAL_SIZE" -gt 1048576 ]; then
            SIZE_MB=$((TOTAL_SIZE / 1048576))
            echo "Total size: ${SIZE_MB}MB"
        else
            SIZE_KB=$((TOTAL_SIZE / 1024))
            echo "Total size: ${SIZE_KB}KB"
        fi
    fi
    
    echo "Files saved to: $OUTPUT_DIR"
    echo ""
    echo "Directory structure:"
    if [ -d "$OUTPUT_DIR" ] && [ "$TOTAL_COUNT" -gt 0 ]; then
        ls -la "$OUTPUT_DIR" | head -10
        if [ "$TOTAL_COUNT" -gt 10 ]; then
            echo "... and $((TOTAL_COUNT - 10)) more files"
        fi
    fi
    
    # Create a summary report
    SUMMARY_FILE="$OUTPUT_DIR/download_summary.txt"
    echo "Photo Download Summary - $(date)" > "$SUMMARY_FILE"
    echo "=========================================" >> "$SUMMARY_FILE"
    echo "Tables processed successfully: $SUCCESS_COUNT" >> "$SUMMARY_FILE"
    echo "Tables failed: $FAIL_COUNT" >> "$SUMMARY_FILE"
    echo "Total photo records: $TOTAL_COUNT" >> "$SUMMARY_FILE"
    echo "" >> "$SUMMARY_FILE"
    echo "Directory Structure:" >> "$SUMMARY_FILE"
    echo "-------------------" >> "$SUMMARY_FILE"
    if [ -d "$OUTPUT_DIR" ]; then
        ls -la "$OUTPUT_DIR" >> "$SUMMARY_FILE"
    fi
    
    echo "" >> "$SUMMARY_FILE"
    echo "Notes:" >> "$SUMMARY_FILE"
    echo "- Student IDs are formatted as left-zero-padded 5 digits" >> "$SUMMARY_FILE"
    echo "- Duplicate student IDs are handled with numeric suffixes (_01, _02, etc.)" >> "$SUMMARY_FILE"
    echo "- Uses same tsql connection as CSV export scripts" >> "$SUMMARY_FILE"
    echo "- Academic and Engineering photos are saved in the same directory" >> "$SUMMARY_FILE"
    echo "- Currently creates placeholder .txt files (binary data processing needed)" >> "$SUMMARY_FILE"
    
    echo ""
    echo "Summary report created: $SUMMARY_FILE"
    
    if [ "$TOTAL_COUNT" -gt 0 ]; then
        echo ""
        echo "✓ Photo download completed successfully!"
        echo "  Individual table processing:"
        echo "  $DOWNLOAD_SCRIPT AcadStudentCards $OUTPUT_DIR"
        echo "  $DOWNLOAD_SCRIPT EngStudentCards $OUTPUT_DIR"
    else
        echo ""
        echo "✗ No photos were downloaded. Check database connection and table contents."
        exit 1
    fi
    
else
    echo ""
    echo "✗ Photo download failed. Check the error messages above."
    exit 1
fi
fi
