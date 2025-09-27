# Data Pipeline Quick Start Guide

## TL;DR - Run the Pipeline

```bash
# Basic usage - process all tables
docker compose -f docker-compose.local.yml run --rm django python manage.py run_pipeline --dry-run --verbose

# Process specific table
docker compose -f docker-compose.local.yml run --rm django python manage.py run_pipeline --tables students --dry-run

# Full processing (remove --dry-run when ready)
docker compose -f docker-compose.local.yml run --rm django python manage.py run_pipeline --tables terms
```

## Prerequisites

1. **Source Data**: CSV files in `data/legacy/data-pipeline/inputs/`
2. **Database**: PostgreSQL running via Docker Compose
3. **Configuration**: Table configs in `apps/data_pipeline/configs/`

## File Structure (What You Need to Know)

```
apps/data_pipeline/
├── management/commands/
│   └── run_pipeline.py          # Main command you'll use
├── configs/                     # Table configurations
│   ├── terms.py                 # Simplest example (15 columns)
│   ├── students.py              # Complex example (91 columns)
│   └── base.py                  # Configuration classes
├── validators/                  # Pydantic validation models
├── core/
│   ├── pipeline.py             # Main pipeline engine
│   └── registry.py             # Configuration management
└── models.py                   # Django models for tracking
```

## Quick Commands Reference

### Check What's Available

```bash
# List all configured tables
docker compose -f docker-compose.local.yml run --rm django python -c "
from apps.data_pipeline.core.registry import TableRegistry
print('Available tables:', TableRegistry.list_all_tables())
"

# Validate all configurations
docker compose -f docker-compose.local.yml run --rm django python manage.py validate_configs
```

### Test Configuration

```bash
# Dry run - safe to run, makes no changes
docker compose -f docker-compose.local.yml run --rm django python manage.py run_pipeline --dry-run --verbose

# Check specific table configuration
docker compose -f docker-compose.local.yml run --rm django python manage.py run_pipeline --tables students --dry-run
```

### Process Data

```bash
# Process single table (safest approach)
docker compose -f docker-compose.local.yml run --rm django python manage.py run_pipeline --tables terms

# Process multiple specific tables
docker compose -f docker-compose.local.yml run --rm django python manage.py run_pipeline --tables terms students

# Process all tables (use with caution)
docker compose -f docker-compose.local.yml run --rm django python manage.py run_pipeline
```

### Debug Issues

```bash
# Verbose output for debugging
docker compose -f docker-compose.local.yml run --rm django python manage.py run_pipeline --verbose --tables students

# Process only through specific stage
docker compose -f docker-compose.local.yml run --rm django python manage.py run_pipeline --stage 2 --tables students

# Continue processing even if some tables fail
docker compose -f docker-compose.local.yml run --rm django python manage.py run_pipeline --continue-on-error
```

## Understanding the Output

### Success Output
```
📋 Processing Plan:
   Source directory: data/legacy/data-pipeline/inputs
   Max stage: 4
   Tables (1):
     1. terms - 15 columns - ✅

🔄 Processing table: terms
🚀 Executing stages 1-4
✅ terms completed successfully

📊 Results for terms:
   Stage completed: 4/4
   Total records: 177
   Valid records: 170
   Invalid records: 7
   Success rate: 96.0%

🎉 All tables processed successfully!
```

### Error Output
```
❌ terms failed with error: Source file not found: data/legacy/data-pipeline/inputs/terms.csv
```

## Common Issues & Quick Fixes

### "Source directory does not exist"
```bash
# Create the directory and add your CSV files
mkdir -p data/legacy/data-pipeline/inputs
# Copy your CSV files there
```

### "No configuration found for table"
Available tables are defined in `configs/`. Check:
```bash
ls apps/data_pipeline/configs/*.py
```

### "Encoding errors in data"
The pipeline auto-detects encoding. If issues persist, check the CSV file:
```bash
file -bi your-file.csv  # Check encoding
```

### "Validation failures"
Check the generated audit report or use verbose mode:
```bash
# Check Django admin for ValidationError records
# Or check project-docs/migration-reports/
```

## Quick Config Template

Need to add a new table? Copy and modify this template:

```python
# In configs/my_table.py
from ..configs.base import TableConfig, ColumnMapping
from ..validators.my_table import MyTableValidator

MY_TABLE_CONFIG = TableConfig(
    table_name="my_table",
    source_file_pattern="my_table.csv",
    description="Description of what this table contains",
    
    column_mappings=[
        ColumnMapping(
            source_name="ID",           # Column name in CSV
            target_name="record_id",    # Column name in database
            data_type="nvarchar(10)",   # SQL Server data type
            nullable=False,             # Required field
            cleaning_rules=["trim", "uppercase"],
            description="Primary identifier"
        ),
        # Add more columns...
    ],
    
    validator_class=MyTableValidator  # Pydantic validator class
)
```

## Quick Validator Template

```python
# In validators/my_table.py
from typing import Optional
from pydantic import BaseModel, Field

class MyTableValidator(BaseModel):
    record_id: str = Field(..., min_length=1, max_length=10)
    name: Optional[str] = Field(None, max_length=100)
    
    class Config:
        str_strip_whitespace = True
        extra = "forbid"
```

## Performance Tips

- **Start small**: Test with one table first (`--tables terms`)
- **Use dry-run**: Always test configuration before real processing
- **Chunk size**: Reduce `--chunk-size` if you get memory errors
- **Stage by stage**: Use `--stage 1` to test import, then `--stage 2` for profiling, etc.
- **Continue on error**: Use `--continue-on-error` for batch processing

## Next Steps

1. **Read full README.md** for complete documentation
2. **Check Django admin** for pipeline run history and errors
3. **Review audit reports** in `project-docs/migration-reports/`
4. **Examine existing configs** in `configs/` for examples
5. **Test with small datasets** before processing full data

## Emergency Recovery

If something goes wrong:

```bash
# Pipeline creates these tables - you can drop them to start over
# Raw tables: raw_tablename
# Cleaned tables: cleaned_tablename  
# Validated tables: validated_tablename
# Invalid tables: tablename_invalid

# Check what tables were created
docker compose -f docker-compose.local.yml run --rm django python -c "
from django.db import connection
cursor = connection.cursor()
cursor.execute(\"SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND (tablename LIKE 'raw_%' OR tablename LIKE 'cleaned_%' OR tablename LIKE 'validated_%')\")
for table in cursor.fetchall():
    print(table[0])
"
```

Remember: **The original CSV files are never modified** - raw data is always preserved.