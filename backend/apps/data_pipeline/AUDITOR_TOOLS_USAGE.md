# Auditor Tools Usage Examples

Complete examples of how to use the data pipeline auditing tools for quality assurance and business rule validation.

## Quick Start

### 1. Inspect Random Records
```bash
# Inspect 10 random student records through all pipeline stages
python manage.py inspect_pipeline_records students --sample-size 10

# Inspect 5 random academic class records  
python manage.py inspect_pipeline_records academicclasses --sample-size 5

# Show all columns instead of just key columns
python manage.py inspect_pipeline_records students --sample-size 5 --show-all-columns
```

### 2. Track Specific Records
```bash
# Follow specific record (source row 123) through all stages
python manage.py inspect_pipeline_records students --source-row 123

# Focus only on business rule validation fields
python manage.py inspect_pipeline_records students --source-row 123 --business-rules-only

# Include invalid records from Stage 4
python manage.py inspect_pipeline_records students --source-row 123 --include-invalid
```

### 3. Compare Specific Stages
```bash
# Compare raw data (Stage 1) vs cleaned data (Stage 3)
python manage.py inspect_pipeline_records students --stage-comparison "1,3" --sample-size 5

# Compare cleaned (Stage 3) vs validated (Stage 4)
python manage.py inspect_pipeline_records students --stage-comparison "3,4" --sample-size 10

# Three-way comparison: raw → cleaned → transformed
python manage.py inspect_pipeline_records students --stage-comparison "1,3,5" --sample-size 3
```

### 4. Export Audit Reports
```bash
# Export detailed audit trail to CSV
python manage.py inspect_pipeline_records students --sample-size 20 --export-csv student_audit.csv

# Export business rules validation data
python manage.py inspect_pipeline_records students --business-rules-only --export-csv business_rules_audit.csv --include-invalid
```

### 5. Business Rules Validation
```bash
# Validate all business rules for students table
python manage.py validate_business_rules students

# Validate with detailed error information
python manage.py validate_business_rules students --detailed

# Validate all tables
python manage.py validate_business_rules all

# Set custom success threshold (default is 95%)
python manage.py validate_business_rules students --threshold 98.0

# Validate specific pipeline stage
python manage.py validate_business_rules students --stage 3  # Stage 3: cleaned data
```

## Detailed Usage Scenarios

### Scenario 1: Name Parsing Quality Assurance

**Goal**: Verify that legacy student names with status indicators are parsed correctly.

```bash
# Step 1: Inspect random students to see name parsing results
python manage.py inspect_pipeline_records students --sample-size 10 --stage-comparison "1,3"

# Step 2: Focus on business rules (name parsing, status indicators)  
python manage.py inspect_pipeline_records students --sample-size 15 --business-rules-only

# Step 3: Validate name parsing business rules
python manage.py validate_business_rules students --detailed

# Step 4: Export detailed analysis for review
python manage.py inspect_pipeline_records students --sample-size 50 --business-rules-only --export-csv name_parsing_audit.csv
```

**Expected Output**:
```
🔍 Inspecting pipeline records for table: students
================================================================================

📊 Pipeline Stage Summary:
   Stage 1: students_stage1_raw (4,127 records)
   Stage 3: students_stage3_cleaned (4,127 records)  
   Stage 4:
     - valid: students_stage4_valid (4,089 records)
     - invalid: students_stage4_invalid (38 records)

🔀 Comparing stages: 1 → 3
================================================================================
📊 Record 1/10 - Source Row: 245
================================================================================
   Stage 1 (Raw Import) | Stage 3 (Data Cleaning)
   ──────────────────── | ─────────────────────
   Name: "$$JOHN SMITH<ABC FOUNDATION>$$" | clean_name: "John Smith"
   _source_row: 245 | is_frozen: true
   — | is_sponsored: true
   — | sponsor_name: "ABC FOUNDATION"
   — | has_admin_fees: false
```

### Scenario 2: Cross-Table Consistency Validation

**Goal**: Ensure ClassID consistency between academicclasses and academiccoursetakers.

```bash
# Step 1: Validate academicclasses business rules
python manage.py validate_business_rules academicclasses --detailed

# Step 2: Validate academiccoursetakers business rules (includes cross-references)
python manage.py validate_business_rules academiccoursetakers --detailed

# Step 3: Inspect specific records to verify ClassID consistency
python manage.py inspect_pipeline_records academicclasses --sample-size 5 --show-all-columns
python manage.py inspect_pipeline_records academiccoursetakers --sample-size 5 --show-all-columns

# Step 4: Export cross-reference analysis
python manage.py inspect_pipeline_records academiccoursetakers --sample-size 25 --export-csv classid_consistency.csv
```

### Scenario 3: Data Quality Regression Testing

**Goal**: Compare data quality before and after pipeline changes.

```bash
# Step 1: Baseline validation (run before changes)
python manage.py validate_business_rules all > baseline_validation.txt

# Step 2: Record inspection baseline (run before changes) 
python manage.py inspect_pipeline_records students --sample-size 20 --export-csv baseline_students.csv
python manage.py inspect_pipeline_records academicclasses --sample-size 10 --export-csv baseline_classes.csv

# Step 3: After changes - repeat validation
python manage.py validate_business_rules all > updated_validation.txt

# Step 4: After changes - repeat inspection with same sample
python manage.py inspect_pipeline_records students --sample-size 20 --export-csv updated_students.csv  
python manage.py inspect_pipeline_records academicclasses --sample-size 10 --export-csv updated_classes.csv

# Step 5: Compare results (manual diff or automated comparison)
diff baseline_validation.txt updated_validation.txt
```

### Scenario 4: Production Readiness Assessment

**Goal**: Comprehensive pre-deployment validation.

```bash
# Step 1: Full business rules validation
python manage.py validate_business_rules all --threshold 95.0 --detailed

# Step 2: Random sampling across all tables
python manage.py inspect_pipeline_records students --sample-size 25 --export-csv prod_students_sample.csv
python manage.py inspect_pipeline_records academicclasses --sample-size 15 --export-csv prod_classes_sample.csv  
python manage.py inspect_pipeline_records terms --sample-size 10 --export-csv prod_terms_sample.csv

# Step 3: Focus on critical business rules
python manage.py inspect_pipeline_records students --business-rules-only --sample-size 30 --include-invalid
python manage.py inspect_pipeline_records academiccoursetakers --business-rules-only --sample-size 20

# Step 4: Validate data transformation accuracy  
python manage.py inspect_pipeline_records students --stage-comparison "4,5" --sample-size 15
```

### Scenario 5: Troubleshooting Data Issues

**Goal**: Investigate specific data quality problems.

```bash
# Step 1: If you know specific problematic records
python manage.py inspect_pipeline_records students --source-row 1234 --show-all-columns --include-invalid
python manage.py inspect_pipeline_records students --source-row 5678 --show-all-columns --include-invalid

# Step 2: Focus on invalid records  
python manage.py inspect_pipeline_records students --sample-size 20 --include-invalid --business-rules-only

# Step 3: Export invalid records for detailed analysis
python manage.py inspect_pipeline_records students --sample-size 50 --include-invalid --export-csv invalid_records_analysis.csv

# Step 4: Validate specific stage where issues might occur
python manage.py validate_business_rules students --stage 3 --detailed  # Cleaning stage
python manage.py validate_business_rules students --stage 4 --detailed  # Validation stage
```

## Sample Output Examples

### Record Inspection Output
```
🔍 Inspecting pipeline records for table: students
================================================================================

📊 Pipeline Stage Summary:
   Stage 1: students_stage1_raw (4,127 records)
   Stage 3: students_stage3_cleaned (4,127 records)
   Stage 4:
     - valid: students_stage4_valid (4,089 records)
     - invalid: students_stage4_invalid (38 records)

🎲 Inspecting 3 random records
────────────────────────────────────────────────────────────────────────────────
🔍 Record 1/3 - Source Row: 156
────────────────────────────────────────────────────────────────────────────────

   📋 Stage 1 - Raw Import
     📂 Stage 1 (students_stage1_raw):
        _source_row: 156
        _source_file: "data/legacy/data_pipeline/inputs/students.csv"
        id: "00156"
        name: "$$MARY JOHNSON<SCHOLARSHIP FOUNDATION>$$"
        birthdate: "Mar 15 1985 12:00AM"

   📋 Stage 3 - Data Cleaning  
     📂 Stage 3 (students_stage3_cleaned):
        _source_row: 156
        clean_name: "Mary Johnson"
        is_frozen: true
        is_sponsored: true
        sponsor_name: "SCHOLARSHIP FOUNDATION"
        has_admin_fees: false
        birth_date_normalized: "1985-03-15"

   📋 Stage 4 - Validation
     📂 Stage 4 (valid) (students_stage4_valid):
        _source_row: 156
        clean_name: "Mary Johnson"
        is_frozen: true
        is_sponsored: true
        sponsor_name: "SCHOLARSHIP FOUNDATION"
        _validation_score: 98.5
```

### Business Rules Validation Output
```
🔍 Business Rules Validation Report: students
================================================================================

📊 Validation Summary for students:
   Total Records: 4,127
   Overall Success Rate: 97.8%
   Status: ✅ PASS (>= 95.0%)

📋 Individual Business Rule Checks:

   ✅ Name Parsing Completeness:
      Description: All records should have clean_name populated
      Results: 4,127/4,127 (100.0%)

   ✅ Status Indicator Consistency:
      Description: Status indicators ($$, <sponsor>, {AF}) should match boolean flags
      Results: 12,263/12,381 (99.0%)
      Details: {'frozen_consistency': '4127/4127', 'sponsored_consistency': '4127/4127', 'admin_fees_consistency': '4009/4127'}

   ✅ Birth Date Validation:
      Description: Birth dates should be normalized and within reasonable range (1900-2010)
      Results: 3,985/4,089 (97.5%)
      Failed: 104

   ❌ Emergency Contact Parsing:
      Description: Emergency contacts should be parsed when present
      Results: 2,856/3,178 (89.9%)
      Failed: 322

🚨 Critical Failures (< 95.0%):
   • emergency_contact_parsing: 89.9% (322 failures)
```

## Integration with CI/CD Pipeline

### Automated Quality Gates
```bash
#!/bin/bash
# quality_gate.sh - Run in CI/CD pipeline

echo "🔍 Running Data Pipeline Quality Gates..."

# Set high threshold for production
THRESHOLD=98.0

# Run comprehensive business rules validation  
python manage.py validate_business_rules all --threshold $THRESHOLD

if [ $? -eq 0 ]; then
    echo "✅ Business rules validation passed"
else
    echo "❌ Business rules validation failed"
    exit 1
fi

# Sample data for regression testing
python manage.py inspect_pipeline_records students --sample-size 50 --export-csv ci_students_sample.csv
python manage.py inspect_pipeline_records academicclasses --sample-size 25 --export-csv ci_classes_sample.csv

echo "📊 Quality gate completed - artifacts exported for review"
```

### Manual Review Checklist

Before production deployment, verify:

1. **✅ Overall Success Rate**: `validate_business_rules all` shows >95% success
2. **✅ Name Parsing**: Student status indicators correctly parsed ($$, <sponsor>, {AF})
3. **✅ Cross-References**: ClassID consistency between academicclasses/academiccoursetakers  
4. **✅ Data Completeness**: All required fields populated after cleaning
5. **✅ Date Normalization**: Birth dates and term dates properly standardized
6. **✅ Business Logic**: No violations of core business rules
7. **✅ Error Tracking**: Invalid records properly segregated with error details

Use the inspection and validation tools to verify each checkpoint systematically.