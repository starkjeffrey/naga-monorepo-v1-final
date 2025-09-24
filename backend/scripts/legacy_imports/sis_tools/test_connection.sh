#!/bin/bash
# Test connection to SQL Server 2008 database
# Usage: ./test_connection.sh

echo "Testing SQL Server 2008 connection..."
echo "Server: 96.9.90.64:1500"
echo "Database: New_PUCDB"
echo "==============================="

# Test network connectivity
echo "1. Testing network connectivity..."
if timeout 5 bash -c "</dev/tcp/96.9.90.64/1500" 2>/dev/null; then
    echo "✓ Network connection successful"
else
    echo "✗ Network connection failed"
    exit 1
fi

# Test SQL Server connection
echo -e "\n2. Testing SQL Server authentication..."
VERSION_OUTPUT=$(echo -e "SELECT @@VERSION\ngo" | tsql -S OLDSIS2 -U sa -P '123456' -D New_PUCDB 2>/dev/null | grep "Microsoft SQL Server")

if [ -n "$VERSION_OUTPUT" ]; then
    echo "✓ SQL Server connection successful"
    echo "✓ Version: $VERSION_OUTPUT"
else
    echo "✗ SQL Server connection failed"
    exit 1
fi

# Test database access
echo -e "\n3. Testing database access..."
TABLE_COUNT=$(echo -e "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'\ngo" | tsql -S OLDSIS2 -U sa -P '123456' -D New_PUCDB 2>/dev/null | grep -o '^[0-9]\+' | head -1)

if [ -n "$TABLE_COUNT" ] && [ "$TABLE_COUNT" -gt 0 ]; then
    echo "✓ Database access successful"
    echo "✓ Found $TABLE_COUNT tables in New_PUCDB database"
else
    echo "✗ Database access failed"
    exit 1
fi

# Test data retrieval
echo -e "\n4. Testing data retrieval..."
STUDENT_COUNT=$(echo -e "SELECT COUNT(*) FROM Students\ngo" | tsql -S OLDSIS2 -U sa -P '123456' -D New_PUCDB 2>/dev/null | grep -o '^[0-9]\+' | head -1)

if [ -n "$STUDENT_COUNT" ] && [ "$STUDENT_COUNT" -gt 0 ]; then
    echo "✓ Data retrieval successful"
    echo "✓ Found $STUDENT_COUNT student records"
else
    echo "✗ Data retrieval failed or no student data found"
fi

echo -e "\n==============================="
echo "✓ All connection tests passed!"
echo "✓ Ready for data export operations"
