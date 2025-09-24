#!/bin/bash
# Photo download script using same tsql technique as bulk_export.sh
# Downloads photos from AcadStudentCards and EngStudentCards with admit dates
# Usage: ./download_student_photos.sh [output_directory]

OUTPUT_DIR="${1:-./student_photos_$(date +%Y%m%d_%H%M%S)}"
mkdir -p "$OUTPUT_DIR"

echo "Starting photo download to: $OUTPUT_DIR"
echo "Note: Student IDs will be formatted as left-zero-padded 5 digits"
echo "Note: Using same tsql connection as CSV export scripts"
echo "================================================"

# Photo tables to download from
TABLES=(
    "AcadStudentCards"
    "EngStudentCards"
)

SUCCESS_COUNT=0
FAIL_COUNT=0
TOTAL_PHOTOS=0

# Function to convert hex string to binary file using Python
convert_hex_to_jpg() {
    local student_id="$1"
    local admit_date="$2"
    local hex_data="$3"
    local output_path="$4"
    
    python3 -c "
import sys
import binascii

try:
    # Remove 0x prefix and whitespace
    hex_clean = '$hex_data'.replace('0x', '').replace(' ', '').replace('\\n', '').replace('\\r', '')
    
    # Skip if too short
    if len(hex_clean) < 20:
        print('  ✗ $student_id' + '_$admit_date - insufficient data')
        sys.exit(1)
    
    # Convert hex to binary
    binary_data = binascii.unhexlify(hex_clean)
    
    # Write to file
    with open('$output_path', 'wb') as f:
        f.write(binary_data)
    
    print('  ✓ $(basename $output_path) ({} bytes)'.format(len(binary_data)))
    
except Exception as e:
    print('  ✗ $student_id' + '_$admit_date - Error: {}'.format(str(e)))
    sys.exit(1)
"
}

# Process each table
for table in "${TABLES[@]}"; do
    echo "Processing $table..."
    
    # First get count of photos (same technique as bulk_export.sh)
    COUNT_QUERY="SELECT COUNT(*) FROM $table WHERE photo IS NOT NULL"
    PHOTO_COUNT=$(echo -e "${COUNT_QUERY}\ngo" | tsql -S OLDSIS2 -U sa -P '123456' -D PUCIDCardMaker 2>/dev/null | \
        grep -v "locale\|charset\|Setting\|rows affected" | \
        sed '/^$/d' | \
        sed '/^[0-9]>/d' | \
        grep -v '^%' | head -1 | tr -d '[:space:]')
    
    echo "✓ Found $PHOTO_COUNT photos in $table"
    
    if [ "$PHOTO_COUNT" -eq 0 ]; then
        echo "No photos found in $table, skipping..."
        continue
    fi
    
    # Get photo data using tsql (same technique as bulk_export.sh)
    PHOTO_QUERY="SELECT IDNo, CONVERT(varchar, AdmitDate, 112) as AdmitDate, CONVERT(varchar(max), CAST(photo as varbinary(max)), 2) as PhotoHex FROM $table WHERE photo IS NOT NULL ORDER BY IDNo"
    
    # Use tsql with same parameters as bulk_export.sh
    echo -e "${PHOTO_QUERY}\ngo" | tsql -S OLDSIS2 -U sa -P '123456' -D PUCIDCardMaker 2>/dev/null | \
        grep -v "locale\|charset\|Setting\|rows affected" | \
        sed '/^$/d' | \
        sed '/^[0-9]>/d' | \
        grep -v '^%' | \
        while IFS=$'\t' read -r STUDENT_ID ADMIT_DATE PHOTO_HEX; do
            # Skip empty lines
            if [ -z "$STUDENT_ID" ] || [ -z "$ADMIT_DATE" ] || [ -z "$PHOTO_HEX" ]; then
                continue
            fi
            
            # Format student ID as left-zero-padded 5 digits
            CLEAN_ID=$(echo "$STUDENT_ID" | sed 's/^0*//')
            if [[ "$CLEAN_ID" =~ ^[0-9]+$ ]] && [ -n "$CLEAN_ID" ]; then
                FORMATTED_ID=$(printf "%05d" "$CLEAN_ID")
            else
                FORMATTED_ID=$(echo "$STUDENT_ID" | tr -cd '[:alnum:]')
            fi
            
            # Create filename with admit date
            FILENAME="${FORMATTED_ID}_${ADMIT_DATE}.jpg"
            IMAGE_PATH="${OUTPUT_DIR}/${FILENAME}"
            
            # Handle duplicates
            COUNTER=1
            while [ -f "$IMAGE_PATH" ]; do
                FILENAME="${FORMATTED_ID}_${ADMIT_DATE}_$(printf "%02d" $COUNTER).jpg"
                IMAGE_PATH="${OUTPUT_DIR}/${FILENAME}"
                COUNTER=$((COUNTER + 1))
            done
            
            # Convert hex to binary JPEG
            if convert_hex_to_jpg "$FORMATTED_ID" "$ADMIT_DATE" "$PHOTO_HEX" "$IMAGE_PATH"; then
                SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
            else
                FAIL_COUNT=$((FAIL_COUNT + 1))
            fi
        done
    
    echo "✓ $table processing completed"
    echo "---"
done

# Final summary (same style as bulk_export.sh)
echo "Photo download completed!"
echo "Success: $SUCCESS_COUNT photos | Failed: $FAIL_COUNT photos"
echo "Photos saved to: $OUTPUT_DIR"
echo ""

if [ "$SUCCESS_COUNT" -gt 0 ]; then
    # Show directory listing
    ls -la "$OUTPUT_DIR" | head -10
    TOTAL_FILES=$(ls -1 "$OUTPUT_DIR" | wc -l)
    if [ "$TOTAL_FILES" -gt 10 ]; then
        echo "... and $((TOTAL_FILES - 10)) more photos"
    fi
    
    # Create summary report (same style as bulk_export.sh)
    SUMMARY_FILE="$OUTPUT_DIR/download_summary.txt"
    echo "Photo Download Summary - $(date)" > "$SUMMARY_FILE"
    echo "=========================================" >> "$SUMMARY_FILE"
    echo "Successfully downloaded: $SUCCESS_COUNT photos" >> "$SUMMARY_FILE"
    echo "Failed downloads: $FAIL_COUNT photos" >> "$SUMMARY_FILE"
    echo "Total photos: $((SUCCESS_COUNT + FAIL_COUNT))" >> "$SUMMARY_FILE"
    echo "" >> "$SUMMARY_FILE"
    echo "Directory Structure:" >> "$SUMMARY_FILE"
    echo "-------------------" >> "$SUMMARY_FILE"
    ls -la "$OUTPUT_DIR" >> "$SUMMARY_FILE"
    
    echo ""
    echo "Summary report created: $SUMMARY_FILE"
    echo "✓ Photo download completed successfully!"
    echo "All photos saved with format: StudentID_AdmitDate.jpg"
    
else
    echo "✗ No photos were downloaded successfully"
    exit 1
fi
