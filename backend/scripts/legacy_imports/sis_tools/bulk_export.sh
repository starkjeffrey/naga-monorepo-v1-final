#!/bin/bash
# Bulk export script for common SIS tables with CSV headers
# Usage: ./bulk_export.sh [output_directory]

# Default to the monorepo inputs directory, but allow override
OUTPUT_DIR="${1:-/Users/jeffreystark/NagaProjects/naga-monorepo/data/legacy/data_pipeline/inputs}"

# Clear existing data and create backup if needed
if [ -d "$OUTPUT_DIR" ] && [ "$(ls -A "$OUTPUT_DIR" 2>/dev/null)" ]; then
    BACKUP_DIR="/Users/jeffreystark/NagaProjects/naga-monorepo/data/legacy/data_pipeline/backup"
    mkdir -p "$BACKUP_DIR"
    echo "Backing up existing data to $BACKUP_DIR..."
    rm -rf "$BACKUP_DIR"/*  # Clear old backup
    mv "$OUTPUT_DIR"/* "$BACKUP_DIR"/ 2>/dev/null || true
fi

mkdir -p "$OUTPUT_DIR"

# Columns that should always be quoted (known to contain commas or problematic text)
# Format: "table_name:column_name" or just "column_name" for all tables
ALWAYS_QUOTE_COLUMNS=(
    "Students:Name"
    "Students:Address"
    "Students:Comments"
    "Students:Description"
    "Students:SelectedFaculty"
    "Students:BatchID"
    "Courses:Description"
    "Courses:Comments"
    "Users:Name"
    "Users:Address"
    "AcademicCourseTakers:ClassID"
    "AcademicClasses:ClassID"
)

# Columns to DROP from export (exclude completely)
# Format: "table_name:column_name" or just "column_name" for all tables
DROP_COLUMNS=(
    "UI"
    "PW"
    "Students:HomeAddress"
    "Students:HomePhone"
    "Students:EmploymentPlace"
    "Students:BatchIDForDoctor"
    "Color"
    "CreatedBy"            # Drop CreatedBy from all tables
    "ModifiedBy"           # Drop ModifiedBy from all tables
    "LastModified"         # Drop LastModified from all tables
    "Receipt_Headers:Description"
    "Receipt_Items:Description"
    "AcademicCourseTakers:RepeatNum"
    "AcademicCourseTakers:LScore"
    "AcademicCourseTakers:Comment"
    "AcademicCourseTakers:QuickNote"
    "AcademicCourseTakers:PreviousGrade"
    "NormalizedCourse"
    "NormalizedPart"
    "NormalizedSection"
    "NormalizedTOD"
    "AcademicCourseTakers:parsed_termid"
    "AcademicCourseTakers:parsed_coursecode"
    "AcademicCourseTakers:parsed_langcourse"
    "AcademicCourseTakers:section"
    "AcademicCourseTakers:UScore"
    "AcademicClasses:CourseTitle"
    "AcademicClasses:schooltime"
    "AcademicClasses:ExSubject"
    "AcademicClasses:StNumber"
    "AcademicClasses:Subject"
    "AcademicClasses:desGroupID"
    "AcademicClasses:GroupID"
    "AcademicClass:Major"
    "Receipt_Headers:TermName"
    "Receipt_Headers:name"
    "Receipt_Headers:Receiver"
    "Receipt_Headers:Gender"
    "Receipt_Header:TransType"
    "Receipt_Header:ReceiptType"
    "time_slot"
    "Pos"
    "GPos"
    "Adder"
    "gidPOS"
    "cidPOS"
    "proPOS"
    "ForeColor"
    "BackColor"
    "RegisterMode"
)

echo "Starting bulk export with CSV headers to: $OUTPUT_DIR"
echo "Note: Using enhanced CSV quoting to handle commas in data"
if [ ${#DROP_COLUMNS[@]} -gt 0 ]; then
    echo "Note: Some columns will be dropped per configuration"
fi
echo "================================================"

# Core SIS tables to export
TABLES=(
    "Students"
    "Courses"
    "AcademicClasses"
    "AcademicCourseTakers"
    "Terms"
    "Receipt_Headers"
    "Receipt_Items"
    "Moo"
    "DerivedData"
)

SUCCESS_COUNT=0
FAIL_COUNT=0

# Export each table
for table in "${TABLES[@]}"; do
    echo "Exporting $table with enhanced CSV formatting..."
    lowercase_table=$(echo "$table" | tr '[:upper:]' '[:lower:]')
    
    # Create a list of columns to always quote for this table
    quote_columns=""
    for col_spec in "${ALWAYS_QUOTE_COLUMNS[@]}"; do
        if [[ "$col_spec" == "$table:"* ]]; then
            # Table-specific column
            col_name="${col_spec#*:}"
            quote_columns="$quote_columns,$col_name"
        elif [[ "$col_spec" != *":"* ]]; then
            # Global column (applies to all tables)
            quote_columns="$quote_columns,$col_spec"
        fi
    done
    # Remove leading comma
    quote_columns="${quote_columns#,}"
    
    # Create a list of columns to drop for this table
    drop_columns=""
    for col_spec in "${DROP_COLUMNS[@]}"; do
        # Skip commented lines (starting with #)
        [[ "$col_spec" =~ ^[[:space:]]*# ]] && continue
        
        if [[ "$col_spec" == "$table:"* ]]; then
            # Table-specific column
            col_name="${col_spec#*:}"
            drop_columns="$drop_columns,$col_name"
        elif [[ "$col_spec" != *":"* ]]; then
            # Global column (applies to all tables)
            drop_columns="$drop_columns,$col_spec"
        fi
    done
    # Remove leading comma
    drop_columns="${drop_columns#,}"
    
    if "$(dirname "$0")/export_table.sh" "$table" "$OUTPUT_DIR/${lowercase_table}.csv" "" "$quote_columns" "$drop_columns"; then
        echo "✓ $table exported successfully with enhanced CSV formatting"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        echo "✗ Failed to export $table"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
    echo "---"
done

echo "Bulk export completed!"
echo "Success: $SUCCESS_COUNT tables | Failed: $FAIL_COUNT tables"
echo "Files created in: $OUTPUT_DIR"
echo ""
ls -la "$OUTPUT_DIR"
echo ""

# Create a summary report
echo "Export Summary with Headers - $(date)" > "$OUTPUT_DIR/export_summary.txt"
echo "=========================================" >> "$OUTPUT_DIR/export_summary.txt"
echo "Successful exports: $SUCCESS_COUNT" >> "$OUTPUT_DIR/export_summary.txt"
echo "Failed exports: $FAIL_COUNT" >> "$OUTPUT_DIR/export_summary.txt"
echo "" >> "$OUTPUT_DIR/export_summary.txt"
echo "File Details:" >> "$OUTPUT_DIR/export_summary.txt"
echo "-------------" >> "$OUTPUT_DIR/export_summary.txt"

for csv_file in "$OUTPUT_DIR"/*.csv; do
    if [ -f "$csv_file" ]; then
        filename=$(basename "$csv_file")
        line_count=$(wc -l < "$csv_file" 2>/dev/null || echo "0")
        file_size=$(ls -lh "$csv_file" | awk '{print $5}' 2>/dev/null || echo "0B")
        if [ "$line_count" -gt 0 ]; then
            data_records=$((line_count - 1))
            echo "$filename: $data_records records + 1 header row ($file_size)" >> "$OUTPUT_DIR/export_summary.txt"
        else
            echo "$filename: 0 records ($file_size)" >> "$OUTPUT_DIR/export_summary.txt"
        fi
    fi
done

echo "" >> "$OUTPUT_DIR/export_summary.txt"
echo "Note: All CSV files now include column headers in the first row." >> "$OUTPUT_DIR/export_summary.txt"

echo "Summary report created: $OUTPUT_DIR/export_summary.txt"
echo "" 
echo "=== EXPORT SUMMARY ==="
cat "$OUTPUT_DIR/export_summary.txt"

if [ "$SUCCESS_COUNT" -gt 0 ]; then
    echo ""
    echo "✓ Export completed successfully! All CSV files include headers."
else
    echo ""
    echo "✗ No tables were exported successfully."
    exit 1
fi
