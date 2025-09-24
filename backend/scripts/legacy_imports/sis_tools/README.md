# SIS Tools - SQL Server 2008 Data Access Utilities

## Quick Start

### Test Connection
```bash
~/sis_tools/test_connection.sh
```

### Export Single Table (WITH CSV HEADERS)
```bash
# Export with automatic CSV headers
~/sis_tools/export_table.sh "Students" "students.csv"
~/sis_tools/export_table.sh "Students" "recent_students.csv" "WHERE AdmissionDate > '2020-01-01'"
```
**New Feature**: All CSV exports now automatically include column headers in the first row!

### Get Table Information
```bash
# List all tables
~/sis_tools/get_table_info.sh

# Get table schema and record count
~/sis_tools/get_table_info.sh "Students"
```

### Bulk Export All Key Tables (WITH HEADERS)
```bash
# Export all key tables with CSV headers
~/sis_tools/bulk_export.sh
~/sis_tools/bulk_export.sh "/path/to/custom/output/dir"
```
**All exported CSV files include proper column headers and detailed reporting.**

## CSV Header Features

- **Automatic Headers**: All exports now include column names in the first row
- **Proper CSV Format**: Headers are comma-separated and match the data columns
- **Improved Reporting**: Export scripts now report data records + header row counts
- **Backward Compatibility**: Works with older SQL Server 2008 versions
- **Enhanced Summary**: Bulk export creates detailed reports including file sizes

## File Locations
- **Main Documentation**: `~/SQL_SERVER_2008_ACCESS_GUIDE.md`
- **Tools Directory**: `~/sis_tools/`
- **FreeTDS Config**: `/etc/freetds/freetds.conf`
- **Backup Scripts**: `~/sis_tools/*.backup` (original versions without headers)

## Connection Details
- **Server**: 96.9.90.64:1500
- **Database**: New_PUCDB  
- **Alias**: sqlserver2008 (FreeTDS)

## Manual Commands

### Direct FreeTDS Connection
```bash
tsql -S sqlserver2008 -U sa -P '123456' -D New_PUCDB
```

### Manual Export (without headers)
```bash
echo -e "SELECT * FROM TableName\ngo" | tsql -S sqlserver2008 -U sa -P '123456' -D New_PUCDB -t , > output.csv
```

### Microsoft Tools (may have SSL issues with SQL Server 2008)
```bash
sqlcmd -S 96.9.90.64,1500 -d New_PUCDB -U sa -P '123456' -C -N -Q "SELECT @@VERSION"
bcp "SELECT * FROM TableName" queryout output.csv -c -t, -S 96.9.90.64,1500 -d New_PUCDB -U sa -P '123456'
```

## Recent Updates

### Version 2.0 - CSV Headers Added
- **Enhanced Export Scripts**: All table exports now include proper CSV headers
- **Improved Bulk Export**: Better reporting with file sizes and record counts
- **Backward Compatibility**: Original scripts backed up as `*.backup` files
- **Better Error Handling**: Enhanced validation and user feedback
