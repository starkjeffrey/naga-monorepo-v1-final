#!/bin/bash
# Enhanced table export script for SIS project with CSV headers, proper quoting, and column dropping
# Usage: ./export_table.sh <table_name> <output_file> [where_clause] [always_quote_columns] [drop_columns]

TABLE_NAME="$1"
OUTPUT_FILE="$2"
WHERE_CLAUSE="$3"
ALWAYS_QUOTE_COLUMNS="$4"  # Comma-separated list of column names to always quote
DROP_COLUMNS="$5"          # Comma-separated list of column names to exclude

if [ -z "$TABLE_NAME" ] || [ -z "$OUTPUT_FILE" ]; then
    echo "Usage: $0 <table_name> <output_file> [where_clause] [always_quote_columns] [drop_columns]"
    echo "Example: $0 Students students.csv"
    echo "Example: $0 Students recent_students.csv \"WHERE AdmissionDate > '2020-01-01'\" \"Name,Address,Comments\" \"Password,SSN\""
    exit 1
fi

# Convert always-quote columns to array
IFS=',' read -ra ALWAYS_QUOTE_ARRAY <<< "$ALWAYS_QUOTE_COLUMNS"

# Convert drop columns to array
IFS=',' read -ra DROP_COLUMNS_ARRAY <<< "$DROP_COLUMNS"

# First, get column headers for the table
echo "Getting column headers for $TABLE_NAME..."
HEADER_QUERY="SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '$TABLE_NAME' ORDER BY ORDINAL_POSITION"

# Get all column names first
ALL_COLUMNS=()
while IFS= read -r column_name; do
    ALL_COLUMNS+=("$column_name")
done < <(echo -e "${HEADER_QUERY}\ngo" | tsql -S OLDSIS2 -U sa -P '123456' -D New_PUCDB 2>/dev/null | \
    grep -v "locale\|charset\|Setting\|rows affected" | \
    sed '/^$/d' | \
    sed '/^[0-9]>/d' | \
    grep -v '^%')

# Filter out dropped columns to create final column list
COLUMN_NAMES=()
for column in "${ALL_COLUMNS[@]}"; do
    should_drop=false
    for drop_col in "${DROP_COLUMNS_ARRAY[@]}"; do
        if [[ "$column" == "$drop_col" ]]; then
            should_drop=true
            echo "Dropping column: $column"
            break
        fi
    done
    
    if [[ "$should_drop" == "false" ]]; then
        COLUMN_NAMES+=("$column")
    fi
done

echo "Final column list (${#COLUMN_NAMES[@]} columns): ${COLUMN_NAMES[*]}"

# Generate CSV headers from filtered column list
{
    for i in "${!COLUMN_NAMES[@]}"; do
        if [ $i -eq 0 ]; then
            printf "%s" "${COLUMN_NAMES[i]}"
        else
            printf ",%s" "${COLUMN_NAMES[i]}"
        fi
    done
    echo ""
} > "$OUTPUT_FILE"

# Add newline after headers if file has content
if [ -s "$OUTPUT_FILE" ]; then
    echo "" >> "$OUTPUT_FILE"
    echo "✓ Headers added to $OUTPUT_FILE"
else
    echo "✗ Could not retrieve column headers for $TABLE_NAME"
    exit 1
fi

# Build SQL query for data with proper CSV formatting using filtered columns
# Use tab delimiter initially, then we'll convert to properly quoted CSV

# Build column list for SELECT statement
COLUMN_LIST=""
for i in "${!COLUMN_NAMES[@]}"; do
    if [ $i -eq 0 ]; then
        COLUMN_LIST="[${COLUMN_NAMES[i]}]"
    else
        COLUMN_LIST="$COLUMN_LIST, [${COLUMN_NAMES[i]}]"
    fi
done

# Handle special filtering for AcademicClasses to exclude shadow records
if [ "$TABLE_NAME" = "AcademicClasses" ]; then
    SHADOW_FILTER="WHERE is_shadow = 0"
    if [ -n "$WHERE_CLAUSE" ]; then
        # If there's already a WHERE clause, combine them with AND
        QUERY="SELECT $COLUMN_LIST FROM $TABLE_NAME $WHERE_CLAUSE AND is_shadow = 0"
    else
        # No existing WHERE clause, just add the shadow filter
        QUERY="SELECT $COLUMN_LIST FROM $TABLE_NAME $SHADOW_FILTER"
    fi
else
    # For all other tables, use the original logic
    if [ -n "$WHERE_CLAUSE" ]; then
        QUERY="SELECT $COLUMN_LIST FROM $TABLE_NAME $WHERE_CLAUSE"
    else
        QUERY="SELECT $COLUMN_LIST FROM $TABLE_NAME"
    fi
fi

echo "Executing: $QUERY"

# Create temporary file for tab-delimited data
TEMP_FILE="${OUTPUT_FILE}.tmp"

# Execute query with tab delimiter (safer for initial extraction)
echo -e "${QUERY}\ngo" | tsql -S OLDSIS2 -U sa -P '123456' -D New_PUCDB -t $'\t' 2>/dev/null | \
    grep -v "locale\|charset\|Setting\|rows affected" | \
    sed '/^$/d' | \
    sed '/^[0-9]>/d' | \
    grep -v '^%' > "$TEMP_FILE"

# Convert tab-delimited data to properly quoted CSV
echo "Converting to properly quoted CSV format..."
if [ -s "$TEMP_FILE" ]; then
    # Process each line to add proper CSV quoting
    while IFS=$'\t' read -r -a fields; do
        output_line=""
        for i in "${!fields[@]}"; do
            field="${fields[i]}"
            column_name="${COLUMN_NAMES[i]}"
            
            # Check if this column should always be quoted
            force_quote=false
            for quote_col in "${ALWAYS_QUOTE_ARRAY[@]}"; do
                if [[ "$column_name" == "$quote_col" ]]; then
                    force_quote=true
                    break
                fi
            done
            
            # Check if field contains comma, quote, newline, starts/ends with whitespace, or should be force-quoted
            if [[ "$force_quote" == "true" ]] || [[ "$field" == *,* ]] || [[ "$field" == *\"* ]] || [[ "$field" == *$'\n'* ]] || [[ "$field" =~ ^[[:space:]] ]] || [[ "$field" =~ [[:space:]]$ ]]; then
                # Escape any existing quotes by doubling them
                field="${field//\"/\"\"}"
                # Wrap in quotes
                field="\"$field\""
            fi
            
            if [ $i -eq 0 ]; then
                output_line="$field"
            else
                output_line="$output_line,$field"
            fi
        done
        echo "$output_line" >> "$OUTPUT_FILE"
    done < "$TEMP_FILE"
    
    # Clean up temp file
    rm -f "$TEMP_FILE"
else
    echo "✗ No data retrieved from query"
    rm -f "$TEMP_FILE"
    exit 1
fi

# Report results
if [ -s "$OUTPUT_FILE" ]; then
    LINE_COUNT=$(wc -l < "$OUTPUT_FILE")
    DATA_RECORDS=$((LINE_COUNT - 1))  # Subtract 1 for header row
    echo "✓ Successfully exported $TABLE_NAME to $OUTPUT_FILE"
    echo "✓ Total records: $DATA_RECORDS (plus 1 header row)"
    echo "✓ File size: $(ls -lh "$OUTPUT_FILE" | awk '{print $5}')"
    echo "✓ First few lines (including header):"
    head -4 "$OUTPUT_FILE"
    echo "..."
    echo "✓ Export completed successfully!"
else
    echo "✗ Export failed or no data found"
    exit 1
fi
