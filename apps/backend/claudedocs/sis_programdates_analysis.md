# SIS Program Dates Analysis

**File**: sis_programdates.csv
**Records**: 18,157 + 1 header row (2.9MB)
**Discovery Date**: 2025-09-25

## Data Structure

| Column | Description | Sample Values |
|--------|-------------|---------------|
| StudentID | Student identifier | 00005, 17281, MS2010001 |
| FirstPaidTerm | First term with payment | 2009T1E, 241111E-T4BE |
| FirstPaidStartDate | Start date of first paid term | Apr 27 2009, Nov 11 2024 |
| LanguageStartDate | Language program start | Apr 27 2009, Nov 11 2024 |
| LanguageEndDate | Language program end | Aug 13 2009, May 6 2025 |
| BAStartDate | BA program start date | NULL, Dec 9 2010 |
| BAEndDate | BA program end date | NULL, Aug 11 2014 |
| MAStartDate | MA program start date | NULL, Feb 1 2017 |
| MAEndDate | MA program end date | NULL, Aug 16 2025 |
| LastPaidTerm | Most recent paid term | 250916E-T4AE, 240520B-T2 |
| LastPaidStartDate | Last paid term start | Sep 16 2025, May 20 2024 |
| BAGraddate | BA graduation date | NULL, Oct 28 2017 |
| MAGraddate | MA graduation date | NULL, Jul 20 2024 |

## Key Observations

### Date Format Issues
- **Format**: `MMM dd yyyy hh:mm:ss:fffAM` (e.g., "Nov 11 2024 12:00:00:000AM")
- **User Note**: "we will have to adjust the treatment if we don't like the date format"
- **Recommendation**: Parse with proper datetime handling, consider standardizing

### Current Activity (2024-2025)

#### Recent Last Paid Terms
- **240520B-T2**: May 20, 2024 (many students)
- **240708E-T3AE**: Jul 8, 2024
- **241007E-T4AE**: Oct 7, 2024 (matches our recent terms!)
- **241111E-T4BE**: Nov 11, 2024
- **250602B-T2**: Jun 2, 2025 (future)
- **250916E-T4AE**: Sep 16, 2025 (future)

#### Graduation Patterns
- **MA Graduations 2024**: Many "Jul 20 2024" entries
- **User Note**: "If someone finished a BA program and didn't start an MA we can mark their BA grad status as graduated"

### Cross-Reference with Recent Terms
Our successfully processed recent terms:
- **241007E-T4AE** (2,694 students) - MATCHES program dates!
- **241125B-T4** (1,437 students)
- **240821B-T3** (1,392 students)

## Student Categories

### 1. Currently Active Students
- LastPaidTerm in 2024-2025
- No graduation dates OR future end dates
- Target for system testing

### 2. Recent MA Graduates
- MAGraddate = Jul 20 2024 (common pattern)
- Completed programs, valuable for alumni testing

### 3. BA-Only Completed Students
- BAEndDate present, MAStartDate = NULL
- Should have BAGraddate populated per user logic

### 4. Long-term Continuing Students
- Language programs spanning multiple years
- Mix of program types (Language → BA → MA progression)

## Data Quality Insights

### Strengths
- Comprehensive program timeline tracking
- Clear progression paths (Language → BA → MA)
- Recent activity well-represented

### Areas for Attention
- Date format standardization needed
- BA graduation logic implementation required
- Many future dates suggest projections/planning data

## Next Steps

1. **Parse and standardize dates** to handle MSSQL datetime format
2. **Cross-reference StudentIDs** with recent enrollment data
3. **Implement BA graduation logic** for completed BA-only students
4. **Identify active test candidates** with 2024-2025 activity
5. **Create focused dataset** for system testing readiness