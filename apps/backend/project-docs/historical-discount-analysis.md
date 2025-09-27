# Historical Discount Rate Analysis

## Overview

This tool analyzes legacy receipt data to extract historical early bird discount rates per term, including the date ranges when discounts were offered. It helps understand the evolution from COVID-era full-term discounts to refined early bird periods.

## Purpose

The analysis provides:
- **Discount percentages** offered per term
- **Active date ranges** when discounts were available
- **Offering patterns** (full-term vs. early-period vs. variable)
- **Evolution tracking** from COVID adjustments to refined early bird systems

## Usage

### Basic Analysis

```bash
# Analyze legacy receipt data
python manage.py analyze_historical_discount_rates data/legacy/all_receipt_headers.csv

# Save summary results to CSV
python manage.py analyze_historical_discount_rates data/legacy/all_receipt_headers.csv --output-csv historical_rates.csv

# Save detailed analysis with sample notes
python manage.py analyze_historical_discount_rates data/legacy/all_receipt_headers.csv --output-detailed detailed_analysis.csv

# Adjust minimum occurrence threshold
python manage.py analyze_historical_discount_rates data/legacy/all_receipt_headers.csv --min-occurrences 10
```

### Command Options

- `--output-csv`: Save summary results (TermID, percentage, date ranges, pattern type)
- `--output-detailed`: Save detailed analysis with sample notes for validation
- `--min-occurrences`: Minimum occurrences to consider a pattern significant (default: 5)

## Output Format

### Console Output
```
🎓 TERM: 201927E-T1
   Period: 2020-08-01 to 2020-11-30
   Pattern: FULL_TERM
   Receipts: 150 with discounts / 200 total
   📈 10% (COVID): 2020-08-01 to 2020-11-30 (150 receipts, $15,000.00)
      Sample: "10% all students COVID adjustment..."

🎓 TERM: 231027B-T3
   Period: 2023-08-15 to 2023-12-15
   Pattern: EARLY_PERIOD
   Receipts: 45 with discounts / 180 total
   📈 10% (EARLY_BIRD): 2023-08-15 to 2023-08-22 (45 receipts, $5,850.00)
      Sample: "10% pay by Aug 22 deadline..."

🎓 TERM: 241027C-T1
   Period: 2024-02-01 to 2024-06-01
   Pattern: EARLY_PERIOD
   ⚠️  Variable rates detected (time-based)
   📈 VARIABLE% (TIME_VARIABLE): 2024-02-01 to 2024-02-07 (35 receipts, $4,200.00)
      Sample: "10% morning payment discount..."
```

### CSV Output (Summary)
| TermID | TermStart | TermEnd | DiscountPercent | ActiveStart | ActiveEnd | OfferingPattern | ReceiptCount | TotalDiscountAmount | VariableRates |
|--------|-----------|---------|-----------------|-------------|-----------|-----------------|--------------|-------------------|---------------|
| 201927E-T1 | 2020-08-01 | 2020-11-30 | 10 | 2020-08-01 | 2020-11-30 | FULL_TERM | 150 | 15000.00 | NO |
| 231027B-T3 | 2023-08-15 | 2023-12-15 | 10 | 2023-08-15 | 2023-08-22 | EARLY_PERIOD | 45 | 5850.00 | NO |
| 241027C-T1 | 2024-02-01 | 2024-06-01 | VARIABLE | 2024-02-01 | 2024-02-07 | EARLY_PERIOD | 35 | 4200.00 | YES |

## Pattern Classification

### Offering Patterns

**FULL_TERM**
- Discount available throughout most of the term (≥80% coverage)
- Typical of COVID-era emergency adjustments
- Example: "10% all students COVID adjustment"

**EXTENDED_PERIOD** 
- Discount available for moderate period (30-80% of term)
- Transition era between full-term and refined early bird
- Example: Extended early bird periods

**EARLY_PERIOD**
- Discount available for short period (≤30% of term)
- Refined early bird system (typically 7-14 days)
- Example: "10% pay by deadline" with 7-day window

### Discount Type Classification

**COVID**
- Notes containing: "covid", "pandemic", "emergency"
- Usually full-term offerings

**EARLY_BIRD**
- Notes containing: "pay by", "early", "deadline", "before", "advance"
- Time-limited offerings

**TIME_VARIABLE**
- Notes containing: "morning", "afternoon", "evening", "am", "pm"
- Different rates based on time of payment

**SPECIAL**
- Notes containing: "monk", "staff", "employee", "sibling", "scholarship"
- Identity-based discounts (excluded from early bird analysis)

## Historical Evolution Patterns

### Era 1: COVID Emergency (2020-2021)
- **Pattern**: FULL_TERM
- **Rate**: Typically 10%
- **Duration**: Entire term
- **Purpose**: Financial relief during pandemic

### Era 2: Transition (2021-2022)
- **Pattern**: EXTENDED_PERIOD
- **Rate**: Varies (10-15%)
- **Duration**: First 2-4 weeks of term
- **Purpose**: Moving away from emergency measures

### Era 3: Refined Early Bird (2023+)
- **Pattern**: EARLY_PERIOD
- **Rate**: Typically 10%
- **Duration**: First 7 days of term
- **Purpose**: Optimized early payment incentive

### Era 4: Variable Rates (Late 2024+)
- **Pattern**: EARLY_PERIOD with VARIABLE rates
- **Rate**: VARIABLE (different rates by time)
- **Duration**: First 7 days with time-based tiers
- **Purpose**: Fine-tuned incentive structure

## Integration with Automatic Discount System

After analyzing historical patterns, create proper `DiscountRule` entries:

### Step 1: Review Analysis Results
```bash
python manage.py analyze_historical_discount_rates data/legacy/receipts.csv --output-csv analysis.csv
```

### Step 2: Create Term-Specific Rules
For each term period identified, create appropriate `DiscountRule` entries with:
- Correct percentage from analysis
- `applies_to_terms` set to specific term codes
- `effective_date` matching the active start date
- Proper rule naming convention

### Step 3: Set Term Discount Deadlines
Update `Term.discount_end_date` fields based on analysis results:
```python
# Example: Set discount deadline for refined early bird terms
Term.objects.filter(code__in=['231027B-T3', '241027C-T1']).update(
    discount_end_date=F('start_date') + timedelta(days=7)
)
```

### Step 4: Validate with Historical Data
Run AR reconstruction with the new rules to validate against historical patterns.

## Benefits

1. **Historical Accuracy**: Captures actual discount offering periods and rates
2. **Evolution Tracking**: Shows progression from COVID emergency to refined system
3. **Data-Driven Rules**: Creates evidence-based discount rules for automation
4. **Variable Rate Detection**: Identifies complex time-based discount schemes
5. **Audit Trail**: Provides documentation for historical financial practices

## Future Use

Once the new SIS is fully operational:
- This historical data helps establish baseline discount policies
- Pattern analysis can inform future early bird strategy
- Historical rates provide context for policy decisions
- Data can be used for financial planning and budgeting

## Notes

- Variable rate analysis marks complex schemes as "VARIABLE" for manual review
- Minimum occurrence thresholds filter out one-off special cases
- Sample notes provide context for validating pattern classification
- Date range analysis helps distinguish full-term vs. early bird offerings