# Data Pipeline Auditor's Guide

Complete guide to auditing the 6-stage data pipeline process for legacy data migration.

## Table of Contents
1. [Pipeline Overview](#pipeline-overview)
2. [Stage-by-Stage Data Storage](#stage-by-stage-data-storage)
3. [Data Lineage Tracking](#data-lineage-tracking)
4. [Business Rules Validation](#business-rules-validation)
5. [Quality Control Checkpoints](#quality-control-checkpoints)
6. [Audit Tools & Commands](#audit-tools--commands)

## Pipeline Overview

The data pipeline transforms legacy CSV files through 6 distinct stages, with each stage storing its results in PostgreSQL tables for full audit trail capability.

### Supported Tables
- `students` - Student records with embedded status indicators
- `academicclasses` - Class headers with course information
- `academiccoursetakers` - Student enrollment details
- `terms` - Academic term definitions
- `receipt_headers` - Payment transaction headers
- `receipt_items` - Payment transaction line items

## Stage-by-Stage Data Storage

### Stage 1: Raw Import
**Purpose**: Import CSV data preserving all original values
**Storage Pattern**: `{table_name}_stage1_raw`

| Table | Storage Location | Contents |
|-------|------------------|----------|
| students | `students_stage1_raw` | Exact CSV data + audit columns |
| academicclasses | `academicclasses_stage1_raw` | Raw class data |
| academiccoursetakers | `academiccoursetakers_stage1_raw` | Raw enrollment data |
| terms | `terms_stage1_raw` | Raw term data |
| receipt_headers | `receipt_headers_stage1_raw` | Raw payment headers |
| receipt_items | `receipt_items_stage1_raw` | Raw payment items |

**Audit Columns Added**:
```sql
_source_file VARCHAR(500)     -- Original CSV file path
_source_row INTEGER           -- Original CSV row number
_import_timestamp TIMESTAMP   -- When imported
_import_batch_id VARCHAR(100) -- Batch identifier
```

### Stage 2: Data Profiling
**Purpose**: Analyze data quality and generate recommendations
**Storage Pattern**: Same as Stage 1 + `DataProfile` model records

| Analysis Type | Storage |
|---------------|---------|
| Column statistics | `data_profile` table |
| Quality metrics | JSON in profile records |
| Recommendations | `_recommendations` field |
| Pattern detection | `_pattern_analysis` field |

**Quality Metrics Tracked**:
- Completeness percentage per column
- Data type consistency
- Encoding issues
- NULL pattern variations
- Outlier detection
- Format validation

### Stage 3: Data Cleaning
**Purpose**: Clean, normalize, and parse complex fields
**Storage Pattern**: `{table_name}_stage3_cleaned`

| Table | Storage Location | Key Transformations |
|-------|------------------|-------------------|
| students | `students_stage3_cleaned` | Name parsing, status extraction, date normalization |
| academicclasses | `academicclasses_stage3_cleaned` | ClassID normalization, cross-table optimization |
| academiccoursetakers | `academiccoursetakers_stage3_cleaned` | Reuses cleaned ClassIDs from headers |
| terms | `terms_stage3_cleaned` | Date parsing, term validation |
| receipt_headers | `receipt_headers_stage3_cleaned` | Amount formatting, date parsing |
| receipt_items | `receipt_items_stage3_cleaned` | Currency normalization |

**Virtual Columns Added (students example)**:
```sql
clean_name VARCHAR(200)           -- Parsed clean name
is_frozen BOOLEAN                 -- $$ indicator
is_sponsored BOOLEAN              -- <sponsor> indicator  
sponsor_name VARCHAR(100)         -- Extracted sponsor name
has_admin_fees BOOLEAN            -- {AF} indicator
emergency_contact_name VARCHAR(200) -- Parsed emergency contact
birth_date_normalized DATE        -- Standardized birth date
```

### Stage 4: Data Validation
**Purpose**: Validate business rules and separate valid/invalid records
**Storage Pattern**: 
- Valid: `{table_name}_stage4_valid`
- Invalid: `{table_name}_stage4_invalid`

| Table | Valid Records Table | Invalid Records Table | Validation Rules |
|-------|-------------------|---------------------|-----------------|
| students | `students_stage4_valid` | `students_stage4_invalid` | Required fields, date ranges, email formats |
| academicclasses | `academicclasses_stage4_valid` | `academicclasses_stage4_invalid` | ClassID format, term references |
| academiccoursetakers | `academiccoursetakers_stage4_valid` | `academiccoursetakers_stage4_invalid` | Student/class references |
| terms | `terms_stage4_valid` | `terms_stage4_invalid` | Date sequences, term overlaps |
| receipt_headers | `receipt_headers_stage4_valid` | `receipt_headers_stage4_invalid` | Amount validation, date checks |
| receipt_items | `receipt_items_stage4_valid` | `receipt_items_stage4_invalid` | Line item consistency |

**Validation Error Tracking**:
```sql
_validation_errors JSONB         -- Array of error details
_validation_score DECIMAL(5,2)   -- Quality score 0-100
_business_rule_failures TEXT[]   -- Failed business rule names
```

### Stage 5: Data Transformation
**Purpose**: Transform to target Django model structure
**Storage Pattern**: `{table_name}_stage5_transformed`

| Table | Storage Location | Django Model Mapping |
|-------|------------------|-------------------|
| students | `students_stage5_transformed` | `Person` + `Student` models |
| academicclasses | `academicclasses_stage5_transformed` | `ClassHeader` model |
| academiccoursetakers | `academiccoursetakers_stage5_transformed` | `Enrollment` model |
| terms | `terms_stage5_transformed` | `AcademicTerm` model |
| receipt_headers | `receipt_headers_stage5_transformed` | `Invoice` model |
| receipt_items | `receipt_items_stage5_transformed` | `InvoiceItem` model |

### Stage 6: Record Splitting (Optional)
**Purpose**: Split complex records into header/line relationships
**Storage Pattern**: 
- Headers: `{table_name}_headers`
- Lines: `{table_name}_lines`

**Applicable to**:
- `receipt_headers` → Multiple `receipt_items`
- `academicclasses` → Multiple `academiccoursetakers`

## Data Lineage Tracking

Every record maintains full lineage through all stages:

```sql
-- Example lineage chain for student ID 00001
students_stage1_raw._source_row = 2
students_stage3_cleaned._source_row = 2  
students_stage4_valid._source_row = 2
students_stage5_transformed._source_row = 2
```

**Lineage Queries**:
```sql
-- Track specific record through all stages
SELECT 
  'Stage 1' as stage, _source_row, name 
FROM students_stage1_raw WHERE _source_row = 2
UNION ALL
SELECT 
  'Stage 3' as stage, _source_row, clean_name 
FROM students_stage3_cleaned WHERE _source_row = 2
UNION ALL
SELECT 
  'Stage 4' as stage, _source_row, clean_name 
FROM students_stage4_valid WHERE _source_row = 2;
```

## Business Rules Validation

### Students Table Rules
1. **Name Parsing**: Legacy names with `$$`, `<sponsor>`, `{AF}` indicators parsed correctly
2. **Status Indicators**: 
   - `$$` = Frozen accounts (not sponsored!)
   - `<sponsor_name>` = Sponsored students requiring SIS lookup
   - `{AF}` = Subject to admin fees
3. **Date Validation**: Birth dates within reasonable ranges (1900-2010)
4. **Contact Information**: Emergency contacts parsed and validated

### Academic Tables Rules
1. **ClassID Consistency**: Same ClassID values across `academicclasses` and `academiccoursetakers`
2. **Term References**: All term references exist in `terms` table
3. **Enrollment Logic**: Students can't be enrolled before admission date
4. **Credit Hours**: Valid credit hour ranges (0.5-6.0)

### Financial Tables Rules
1. **Amount Validation**: Positive amounts, reasonable ranges
2. **Currency Consistency**: All amounts in USD
3. **Transaction Integrity**: Receipt items sum to header total
4. **Date Logic**: Payment dates within term periods

## Quality Control Checkpoints

### Stage 1 → Stage 2 Checkpoint
```sql
-- Verify no data loss during import
SELECT COUNT(*) FROM students_stage1_raw;  -- Should equal CSV row count
SELECT COUNT(*) FROM data_profile WHERE table_name = 'students';  -- Should have profile
```

### Stage 2 → Stage 3 Checkpoint  
```sql
-- Verify cleaning rules applied
SELECT COUNT(*) FROM students_stage3_cleaned WHERE clean_name IS NOT NULL;
SELECT COUNT(*) FROM students_stage3_cleaned WHERE is_frozen = true;  -- Should match $$ count
```

### Stage 3 → Stage 4 Checkpoint
```sql
-- Verify validation logic
SELECT COUNT(*) FROM students_stage4_valid;
SELECT COUNT(*) FROM students_stage4_invalid;
-- Total should equal stage3 count
```

### Stage 4 → Stage 5 Checkpoint
```sql
-- Verify transformation completeness
SELECT COUNT(*) FROM students_stage5_transformed;
-- Should equal valid records count
```

## Audit Tools & Commands

### Built-in Inspection Command
```bash
# Inspect 10 random records through all stages
python manage.py inspect_pipeline_records students --sample-size 10

# Inspect specific record by source row
python manage.py inspect_pipeline_records students --source-row 45

# Compare before/after for specific stage
python manage.py inspect_pipeline_records students --stage-comparison 3,4

# Export audit report
python manage.py inspect_pipeline_records students --export-csv audit_report.csv
```

### Manual SQL Queries

**Record Count Validation**:
```sql
-- Verify record counts through pipeline
SELECT 
  'Stage 1' as stage, COUNT(*) as record_count 
FROM students_stage1_raw
UNION ALL
SELECT 
  'Stage 3' as stage, COUNT(*) as record_count 
FROM students_stage3_cleaned
UNION ALL  
SELECT 
  'Stage 4 Valid' as stage, COUNT(*) as record_count 
FROM students_stage4_valid
UNION ALL
SELECT 
  'Stage 4 Invalid' as stage, COUNT(*) as record_count 
FROM students_stage4_invalid;
```

**Data Quality Metrics**:
```sql
-- Check name parsing success rate
SELECT 
  COUNT(*) as total_records,
  SUM(CASE WHEN clean_name IS NOT NULL THEN 1 ELSE 0 END) as parsed_names,
  SUM(CASE WHEN is_frozen = true THEN 1 ELSE 0 END) as frozen_accounts,
  SUM(CASE WHEN is_sponsored = true THEN 1 ELSE 0 END) as sponsored_students,
  SUM(CASE WHEN has_admin_fees = true THEN 1 ELSE 0 END) as admin_fee_students
FROM students_stage3_cleaned;
```

**Cross-Table Consistency**:
```sql
-- Verify ClassID consistency between tables
SELECT 
  ac.classid, 
  COUNT(act.classid) as enrollment_count
FROM academicclasses_stage4_valid ac
LEFT JOIN academiccoursetakers_stage4_valid act ON ac.classid = act.classid
GROUP BY ac.classid
HAVING COUNT(act.classid) = 0;  -- Classes with no enrollments
```

### Performance Monitoring
```sql
-- Pipeline execution performance
SELECT 
  table_name,
  stage,
  execution_time_seconds,
  records_processed,
  records_processed / execution_time_seconds as records_per_second
FROM pipeline_run_log
ORDER BY execution_time_seconds DESC;
```

## Common Issues & Troubleshooting

### Issue: Record Count Mismatches
```sql
-- Diagnose where records are lost
WITH stage_counts AS (
  SELECT 'Stage 1' as stage, COUNT(*) as count FROM students_stage1_raw
  UNION ALL
  SELECT 'Stage 3' as stage, COUNT(*) as count FROM students_stage3_cleaned  
  UNION ALL
  SELECT 'Stage 4V' as stage, COUNT(*) as count FROM students_stage4_valid
  UNION ALL  
  SELECT 'Stage 4I' as stage, COUNT(*) as count FROM students_stage4_invalid
)
SELECT stage, count, LAG(count) OVER (ORDER BY stage) as prev_count,
       count - LAG(count) OVER (ORDER BY stage) as diff
FROM stage_counts;
```

### Issue: Data Quality Problems
```sql
-- Find records with parsing issues
SELECT _source_row, name, clean_name, _validation_errors
FROM students_stage4_invalid
WHERE _validation_errors ? 'name_parsing_error'
LIMIT 10;
```

### Issue: Cross-Table Inconsistencies
```sql
-- Find orphaned records
SELECT 'Missing ClassID in academiccoursetakers' as issue, COUNT(*) as count
FROM academiccoursetakers_stage4_valid act
LEFT JOIN academicclasses_stage4_valid ac ON act.classid = ac.classid
WHERE ac.classid IS NULL;
```

## Compliance & Regulatory Notes

1. **Data Retention**: All stage tables retained for minimum 7 years per policy
2. **PII Handling**: Personal information encrypted at rest in all stage tables
3. **Audit Trail**: Complete lineage maintained for regulatory compliance
4. **Data Quality**: Minimum 95% success rate required for production deployment
5. **Business Rule Compliance**: All validation rules documented and version controlled

---

**Version**: 1.0  
**Last Updated**: 2025-01-22  
**Maintained by**: Data Pipeline Team