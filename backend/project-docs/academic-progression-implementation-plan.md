# Academic Progression Implementation Plan

## 🎯 Objective
Replace the failed ProgramEnrollment system with a robust, performant academic progression tracking system that handles unreliable legacy data while providing fast queries on 200k+ enrollment records.

## 📋 Pre-Implementation Checklist

- [ ] Review existing ClassHeaderEnrollment data structure
- [ ] Analyze enrollment patterns in the database
- [ ] Identify signature courses for each major
- [ ] Document known data quality issues
- [ ] Get stakeholder approval on confidence thresholds

## 🚀 Implementation Steps

### Step 1: Create Core Models (2-3 hours)

Create file: `apps/enrollment/models_progression.py`

```python
# Key implementation notes:
# 1. Start with AcademicJourney model
# 2. Add all indexes for performance
# 3. Include data quality fields from the start
# 4. Use proper Django conventions
```

**Specific Tasks:**
1. Create AcademicJourney model with all fields
2. Create ProgramMilestone model with proper relationships
3. Create AcademicProgression denormalized model
4. Create CertificateIssuance model
5. Generate and run migrations

**Validation:** 
- Models created successfully
- Migrations run without errors
- Admin can create test records

### Step 2: Create Detection Services (4-5 hours)

Create file: `apps/enrollment/services/progression_builder.py`

```python
class ProgressionBuilder:
    """Service for building academic progression from enrollment data."""
    
    # Signature courses for major detection (customize for your school)
    MAJOR_SIGNATURES = {
        'International Relations': ['IR-480', 'POL-405', 'IR-485'],
        'Business Administration': ['BUS-464', 'BUS-465', 'BUS-460'],
        'TESOL': ['ENGL-200A', 'EDUC-400', 'ENGL-302A'],
        # Add more majors...
    }
    
    def detect_program_phases(self, student_id):
        """Main entry point for progression detection."""
        # Implementation here
```

**Key Methods to Implement:**
1. `detect_language_phase()` - Find IEAP/GESL/EHSS enrollments
2. `detect_ba_phase()` - Find BA program enrollments  
3. `detect_major_from_courses()` - Use signature courses
4. `calculate_confidence_score()` - Rate data quality
5. `handle_enrollment_gaps()` - Deal with missing terms

### Step 3: Create Batch Population Command (3-4 hours)

Create file: `apps/enrollment/management/commands/populate_academic_progression.py`

```python
class Command(BaseMigrationCommand):
    """Populate AcademicJourney from historical enrollment data."""
    
    def add_arguments(self, parser):
        parser.add_argument('--batch-size', type=int, default=100)
        parser.add_argument('--start-student', type=int, default=0)
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--confidence-threshold', type=float, default=0.7)
```

**Implementation Strategy:**
1. Process students in batches of 100
2. Show progress every 10 batches
3. Log low-confidence records to CSV
4. Generate summary report
5. Allow re-running for specific students

### Step 4: Performance Optimization (2-3 hours)

Create file: `apps/enrollment/services/progression_cache.py`

```python
class ProgressionCacheManager:
    """Manages denormalized AcademicProgression records."""
    
    def rebuild_progression_cache(self, student_id):
        """Rebuild denormalized record from source data."""
        journey = AcademicJourney.objects.get(student_id=student_id)
        milestones = journey.milestones.all().order_by('milestone_date')
        
        # Calculate summary statistics
        progression = self.calculate_progression_summary(journey, milestones)
        
        # Update or create denormalized record
        AcademicProgression.objects.update_or_create(
            student_id=student_id,
            defaults=progression
        )
```

**Optimization Tasks:**
1. Add database indexes (see model definitions)
2. Create composite indexes for common queries
3. Implement Redis caching for frequently accessed data
4. Add database triggers for auto-updates
5. Create periodic task to refresh cache

### Step 5: Create Admin Review Interface (2 hours)

Enhance: `apps/enrollment/admin.py`

```python
@admin.register(AcademicJourney)
class AcademicJourneyAdmin(admin.ModelAdmin):
    list_display = ['student', 'current_program', 'journey_status', 'confidence_score', 'requires_review']
    list_filter = ['journey_status', 'requires_review', 'data_source', 'current_program_type']
    search_fields = ['student__person__personal_name', 'student__student_id']
    
    # Add custom actions
    actions = ['mark_reviewed', 'recalculate_confidence']
    
    # Inline for milestones
    inlines = [ProgramMilestoneInline]
```

### Step 6: Create Query APIs (2 hours)

Create file: `apps/enrollment/api/progression_endpoints.py`

```python
@router.get("/progression/summary", response=ProgressionSummarySchema)
def get_progression_summary(request, program: str = None, status: str = None):
    """Get summary statistics for academic progression."""
    
    queryset = AcademicProgression.objects.all()
    
    if program:
        queryset = queryset.filter(current_program__name=program)
    if status:
        queryset = queryset.filter(current_status=status)
    
    return {
        'total_students': queryset.count(),
        'avg_time_to_ba': queryset.aggregate(Avg('time_to_ba_days')),
        'dropout_points': self.analyze_dropout_points(queryset),
        # More statistics...
    }
```

## 🧪 Testing Strategy

### Unit Tests
```python
# tests/test_progression_builder.py
class TestProgressionBuilder(TestCase):
    def test_detect_major_from_signature_courses(self):
        # Create test enrollments with IR courses
        # Assert correct major detected with high confidence
    
    def test_handle_missing_enrollment_data(self):
        # Create sparse enrollment data
        # Assert graceful handling and appropriate confidence
```

### Integration Tests
- Test full student journey creation
- Test batch processing performance
- Test data conflict resolution
- Test cache updates

### Performance Tests
- Query 10,000 student summaries < 100ms
- Generate school-wide statistics < 500ms
- Individual student lookup < 10ms

## 📊 Success Metrics

1. **Data Quality**
   - 80%+ records with confidence > 0.8
   - <5% require manual review
   - 100% students have journey records

2. **Performance**
   - Summary queries < 100ms
   - Batch processing: 1000 students/minute
   - Real-time updates < 50ms

3. **Accuracy**
   - Validated against known graduates
   - Major detection accuracy > 90%
   - Certificate issuance 100% accurate

## ⚠️ Implementation Warnings

### For Claude/Sonnet:
1. **DO NOT** modify existing ClassHeaderEnrollment model
2. **DO NOT** delete any existing data
3. **ALWAYS** use BaseMigrationCommand for data migrations
4. **ALWAYS** include confidence scoring
5. **NEVER** assume data quality - always validate

### Common Pitfalls to Avoid:
1. Don't try to be too precise with major detection
2. Don't ignore enrollment gaps - they're common
3. Don't trust legacy SelProgram/SelMajor fields blindly
4. Don't forget to handle students who never graduated
5. Don't assume linear progression (students go backwards)

## 🔄 Rollback Plan

If issues arise:
1. Keep existing ProgramEnrollment model untouched
2. New models are additional, not replacements
3. Can disable new system via feature flag
4. All changes are reversible via migrations

## 📝 Post-Implementation Tasks

1. **Data Validation**
   - Compare results with known cases
   - Review low-confidence records
   - Get user feedback on accuracy

2. **Performance Tuning**
   - Monitor query performance
   - Adjust indexes based on usage
   - Optimize cache refresh timing

3. **User Training**
   - Document query examples
   - Create report templates
   - Train staff on review process

## 💡 Quick Implementation Commands

```bash
# 1. Create models
python manage.py makemigrations enrollment
python manage.py migrate

# 2. Run initial population (dry run)
python manage.py populate_academic_progression --dry-run

# 3. Run actual population
python manage.py populate_academic_progression --batch-size=100

# 4. Review low confidence records
python manage.py export_low_confidence_journeys --threshold=0.7

# 5. Refresh progression cache
python manage.py refresh_progression_cache
```