# Payment Reconciliation System

## Overview

This reconciliation system matches student payments against their course enrollments using a sophisticated price determination engine. It replaces the previous `receipt_reconciliation` project with an integrated solution built directly into the Naga SIS.

## Quick Start

### 1. Launch the Gradio Review Panel

The easiest way to start is with the interactive web interface:

```bash
./run_reconciliation_panel.py
```

This launches a web interface at http://localhost:7860 where you can:
- Review payments case-by-case
- See detailed pricing breakdowns
- Make notes on specific cases
- Navigate through unreconciled payments
- Export results

### 2. Command Line Reconciliation

For batch processing:

```bash
# Reconcile all payments for a specific year
python manage.py run_reconciliation --year 2023 --export-csv results_2023.csv

# Reconcile a specific term
python manage.py run_reconciliation --term FALL2023

# Process only unmatched payments
python manage.py run_reconciliation --only-unmatched --verbose

# Dry run to see what would happen
python manage.py run_reconciliation --dry-run --year 2023
```

### 3. Direct Legacy CSV Reconciliation

For quick reconciliation without database loading:

```bash
# Process legacy CSV files directly
python manage.py reconcile_legacy_payments --year 2023 --output legacy_results.csv

# Process specific student
python manage.py reconcile_legacy_payments --student-id 12345
```

## Key Features

### Price Determination Engine

The system automatically determines prices based on:

1. **Default Pricing** - Standard per-cycle rates (BA/MA/LANG)
2. **Fixed Course Pricing** - Specific courses with override prices
3. **Senior Project Pricing** - Tiered based on group size (IR-489, BUS-489, etc.)
4. **Reading Class Pricing** - Small class pricing (detected by READ, REQ, SPECIAL keywords)

### Intelligent Matching

- **Exact Match** - Payment exactly matches calculated price
- **Dropped Course Detection** - Zero payment for all-dropped schedules
- **Combination Matching** - Tries different course combinations
- **Senior Project Tier Matching** - Determines group size from payment amount
- **Variance Tolerance** - Accepts small variances within thresholds

### Confidence Scoring

- **100%** - Exact match
- **95%** - Within 2% variance
- **85%** - Within 5% variance  
- **75%** - Within 10% variance
- **<75%** - Requires manual review

## Data Requirements

### Legacy CSV Files (250728 timestamp)

Place these files in `backend/data/legacy/`:

- `all_students_250728.csv` - Student data with citizenship
- `all_receipt_headers_250728.csv` - Payment records
- `all_academiccoursetakers_250728.csv` - Enrollment records
- `all_academicclasses_250728.csv` - Class information

### Data Preparation

```bash
# Verify data files exist
python manage.py prepare_reconciliation_data

# Load into database (optional)
python manage.py prepare_reconciliation_data --load-tables

# Dry run
python manage.py prepare_reconciliation_data --load-tables --dry-run
```

## Gradio Panel Features

The web interface provides:

### Payment Review Tab
- **Case-by-case navigation** - Review each payment individually
- **Student information** - Name, ID, citizenship, foreign/domestic status
- **Enrollment details** - All courses with status and attendance
- **Pricing breakdown** - Detailed price calculation by type
- **Reconciliation summary** - Expected vs actual with variance

### Actions
- **Auto-Reconcile** - Apply matching algorithm
- **Confidence Override** - Manually adjust confidence
- **Review Notes** - Add notes for manual review
- **Mark for Review** - Flag for human verification

### Filters
- **Status** - Unreconciled, Fully Reconciled, Pending Review, etc.
- **Confidence** - High/Medium/Low
- **Term** - Specific academic terms
- **Date Range** - Payment date filtering

## Configuration

### Materiality Thresholds

Set in Django admin under Finance > Materiality Thresholds:

- Individual Payment: $50 or 10%
- Student Account: $100
- Batch Total: $1,000

### Pricing Data

Managed in Django admin:
- Finance > Default Pricing
- Finance > Course Fixed Pricing  
- Finance > Senior Project Pricing
- Finance > Reading Class Pricing

## Troubleshooting

### Common Issues

1. **"No payments found"** - Check date filters and payment status
2. **Low confidence scores** - Review pricing configuration
3. **Missing enrollments** - Verify enrollment data is loaded
4. **Zero payments** - Check if all courses were dropped

### Debug Mode

Run with verbose output:

```bash
python manage.py run_reconciliation --verbose --student-id 12345
```

## Reporting

### Export Options

```bash
# CSV export with full details
python manage.py run_reconciliation --export-csv full_report.csv

# Summary statistics
python manage.py run_reconciliation --year 2023 > summary_2023.txt
```

### Key Metrics

- Success Rate - Percentage fully reconciled
- Confidence Distribution - High/Medium/Low breakdown
- Variance Analysis - Total and average variances
- Error Categories - Common failure patterns

## Notes for Manual Review

When using the Gradio panel for case-by-case review:

1. **Check enrollment status** - Dropped courses shouldn't be charged
2. **Verify citizenship** - Affects foreign/domestic pricing
3. **Look for reading classes** - Special pricing applies
4. **Senior projects** - May need manual group size determination
5. **Add detailed notes** - Help improve future matching

## Migration from receipt_reconciliation

This system replaces the standalone `receipt_reconciliation` project. Key improvements:

- Integrated with main SIS database
- Automatic price determination
- Better confidence scoring
- Comprehensive audit trail
- Web and CLI interfaces

To migrate:
1. Export any important notes from old system
2. Run reconciliation on same date ranges
3. Compare results
4. Adjust confidence thresholds as needed