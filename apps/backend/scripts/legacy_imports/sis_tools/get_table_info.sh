#!/bin/bash
# Get information about database tables
# Usage: ./get_table_info.sh [table_name]

TABLE_NAME="$1"

if [ -z "$TABLE_NAME" ]; then
    echo "Getting list of all tables..."
    echo -e "SELECT TABLE_NAME, TABLE_TYPE FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE' ORDER BY TABLE_NAME\ngo" | \
        tsql -S sqlserver2008 -U sa -P '123456' -D New_PUCDB -t , 2>/dev/null | \
        grep -v "locale\|charset\|Setting\|rows affected\|^[0-9]>\|^%\|^$"
else
    echo "Getting schema for table: $TABLE_NAME"
    echo -e "SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE, COLUMN_DEFAULT FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '$TABLE_NAME' ORDER BY ORDINAL_POSITION\ngo" | \
        tsql -S sqlserver2008 -U sa -P '123456' -D New_PUCDB -t , 2>/dev/null | \
        grep -v "locale\|charset\|Setting\|rows affected\|^[0-9]>\|^%\|^$"
    
    echo -e "\nRecord count:"
    echo -e "SELECT COUNT(*) as RecordCount FROM $TABLE_NAME\ngo" | \
        tsql -S sqlserver2008 -U sa -P '123456' -D New_PUCDB 2>/dev/null | \
        grep -v "locale\|charset\|Setting\|rows affected\|^[0-9]>\|^%\|^$"
fi
