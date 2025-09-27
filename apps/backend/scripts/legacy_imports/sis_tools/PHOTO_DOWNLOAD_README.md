# SIS Photo Download Scripts

Companion scripts to download student photos from the PUCIDCardMaker database on the same MSSQL 2008 server as the CSV export tools.

## Quick Start

1. **Test the connection first:**
   ```bash
   ./test_photo_connection.py
   ```

2. **Download all photos (recommended):**
   ```bash
   ./bulk_photo_download.sh
   ```

3. **Or specify output directory:**
   ```bash
   ./bulk_photo_download.sh /Users/jeffreystark/Photos/sis_photos
   ```

## Scripts Overview

### 1. `bulk_photo_download.sh` (Main Script)
- **Purpose**: Downloads photos from both Academic and Engineering student tables
- **Usage**: `./bulk_photo_download.sh [output_directory]`
- **Features**:
  - Downloads from both `AcadStudentCards` and `EngStudentCards` tables
  - Creates separate subdirectories (`acad/` and `eng/`)
  - Handles duplicates automatically
  - Generates summary reports
  - Follows same pattern as `bulk_export.sh`

### 2. `download_photos.py` (Core Python Script)
- **Purpose**: Core photo download functionality with advanced options
- **Usage**: `python3 download_photos.py [options]`
- **Options**:
  - `--table {AcadStudentCards,EngStudentCards,both}` - Which table(s) to download from
  - `--output DIR` - Output directory for photos
  - `--check-duplicates` - Show duplicate student IDs before downloading
  - `--dry-run` - Preview what would be downloaded without actually downloading

### 3. `test_photo_connection.py` (Connection Test)
- **Purpose**: Test database connectivity and show photo statistics
- **Usage**: `./test_photo_connection.py`
- **Shows**:
  - Database connection status
  - Photo counts per table
  - Sample photo sizes
  - Duplicate ID warnings

## File Naming Convention

Photos are saved with the following naming pattern:
- **Standard**: `{student_id_padded}_{admit_date}.jpg` (e.g., `01234_20180314.jpg`)
- **Duplicates**: `{student_id_padded}_{admit_date}_{sequence}.jpg` (e.g., `01234_20180314_01.jpg`)

Student IDs are **left-zero-padded to 5 digits** and admit dates are in **YYYYMMDD format**.

## Examples

### Basic Usage
```bash
# Download all photos to timestamped directory
./bulk_photo_download.sh

# Download to specific directory
./bulk_photo_download.sh /Users/jeffreystark/Photos/student_photos

# Test connection first
./test_photo_connection.py
```

### Advanced Usage
```bash
# Download only Academic photos
python3 download_photos.py --table AcadStudentCards --output ./acad_photos

# Download only Engineering photos  
python3 download_photos.py --table EngStudentCards --output ./eng_photos

# Check for duplicates before downloading
python3 download_photos.py --check-duplicates --dry-run

# Download with duplicate checking
python3 download_photos.py --table both --check-duplicates --output ./all_photos
```

## Output Structure

When using `bulk_photo_download.sh`, the output structure will be:
```
photos_20240106_143052/
├── download_summary.txt
├── 00001_20110314.jpg
├── 00002_20150319.jpg
├── 00131_20180525.jpg
└── ...
```

Note: Photos from both Academic and Engineering tables are now saved in the same directory with filenames that include the admit date.

## Database Connection

The scripts connect to:
- **Server**: `192.168.36.250`
- **Database**: `PUCIDCardMaker`
- **Tables**: `AcadStudentCards`, `EngStudentCards`
- **Credentials**: Same as CSV export scripts

## Requirements

- Python 3.x
- `pymssql` package: `pip3 install pymssql`
- Network access to database server
- Database credentials (hardcoded same as CSV scripts)

## Duplicate Handling

The system automatically handles multiple photos for the same student ID and date:
- First occurrence: `12345_20180314.jpg`
- Second occurrence with same date: `12345_20180314_01.jpg`
- Third occurrence with same date: `12345_20180314_02.jpg`
- Different admit date: `12345_20190525.jpg`

Use `--check-duplicates` to see which student IDs have multiple photos before downloading.

## Error Handling

The scripts include comprehensive error handling for:
- Database connection failures
- Missing or corrupted image data
- File write permissions
- Duplicate student IDs
- Network connectivity issues

## Integration with Existing Tools

These photo download scripts follow the same patterns as the existing CSV export tools:
- Similar command-line interface
- Consistent error handling and reporting
- Compatible directory structures
- Same database connection parameters

## Troubleshooting

1. **Connection issues**: Run `./test_photo_connection.py` first
2. **Permission errors**: Check write permissions on output directory
3. **Missing photos**: Some student records may not have photo data
4. **Large downloads**: Photos are downloaded sequentially to avoid overwhelming the database

## Summary Reports

Both the shell script and Python script generate summary reports showing:
- Number of photos downloaded per table
- File sizes and locations
- Any errors or warnings encountered
- Duplicate handling statistics
