# Simplified Program Status Analysis

## Overview
**Current Dataset**: 4,224 students with 2024-2025 activity
**Approach**: Simplified program tracking focused on current status and recent graduates
**Future**: Version 2 will add change of major/program tracking

## Simplified Data Model

### Core Fields
| Field | Description | Logic |
|-------|-------------|--------|
| StudentID | Student identifier | Direct from sis_programdates |
| CurrentStatus | Program status | Active_Language, Active_BA, Active_MA, Graduated_BA, Graduated_MA |
| LastActiveTerm | Most recent term | From LastPaidTerm column |
| LastActiveDate | Date of last activity | From LastPaidStartDate (standardized) |
| GraduationDate | Graduation date if applicable | BA/MA graduation logic |
| RecentActivity | 2024-2025 flag | Boolean for system testing readiness |

### Status Logic (Simplified)

#### 1. Active Students
- **Active_Language**: LastPaidTerm in 2024-2025, no BA/MA graduation
- **Active_BA**: BAStartDate exists, no BAGraddate, no MAStartDate
- **Active_MA**: MAStartDate exists, no MAGraddate

#### 2. Graduated Students
- **Graduated_BA**: BAEndDate exists, no MAStartDate → Set BAGraddate = BAEndDate
- **Graduated_MA**: MAGraddate exists → Use existing MAGraddate

## Cross-Reference with Recent Terms

### Term Matching
Our processed recent terms:
- **241007E-T4AE** (2,694 students) ✅ Present in program dates
- **241125B-T4** (1,437 students) → Check for matches
- **240821B-T3** (1,392 students) → Check for matches

### Common Recent Terms in Program Dates
- **240520B-T2**: May 2024 (many MA graduates)
- **241007E-T4AE**: Oct 2024 ✅ MATCHES our enrollment data
- **241111E-T4BE**: Nov 2024
- **250602B-T2**: Jun 2025 (future/projected)
- **250916E-T4AE**: Sep 2025 (future/projected)

## Target Students for System Testing

### Criteria
1. **High Priority**: StudentID in both recent enrollment AND program dates
2. **Active Status**: Currently enrolled (2024-2025 activity)
3. **Clean Data**: Clear program status, no data conflicts
4. **Representative**: Mix of Language, BA, MA students

### Expected Categories
- **Language Students**: ~2,000-3,000 (largest group)
- **BA Students**: ~800-1,200 (intermediate group)
- **MA Students**: ~200-400 (graduate level)
- **Recent Graduates**: ~300-500 (for alumni features)

## Implementation Plan

### Phase 1: Data Extraction
1. Extract 4,224 students with 2024-2025 activity
2. Apply simplified status logic
3. Standardize date formats
4. Cross-reference with recent enrollment data

### Phase 2: Validation
1. Identify students in BOTH datasets (enrollment + program dates)
2. Verify status consistency
3. Flag any data conflicts for review

### Phase 3: Test Dataset Creation
1. Create focused dataset of validated active students
2. Categorize by program status
3. Prepare for system testing

## Data Quality Notes

### Strengths
- Large dataset (4,224 recent students)
- Clear activity patterns
- Graduation data available

### Simplifications Applied
- Focused on current status vs. full program history
- Applied BA graduation logic automatically
- Standardized complex date formats
- Removed historical program change tracking (for v2)

## Next Actions
1. Process 4,224 students through simplified logic
2. Cross-reference StudentIDs with our 5,537 recent enrollment records
3. Identify overlap for high-confidence test candidates
4. Create clean dataset for system testing readiness