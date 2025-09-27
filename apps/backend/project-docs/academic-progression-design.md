# Academic Progression Tracking System Design

## Executive Summary

This document proposes a new architecture for tracking student academic progression through PUCSR's programs, replacing the failed ProgramEnrollment approach with an event-driven, performance-optimized system.

## Core Design Principles

1. **Event-Driven**: Record academic events as they happen, not retrospectively
2. **Separation of Concerns**: Different models for different purposes
3. **Performance First**: Denormalized views for sub-second queries on 200k+ records
4. **Clear Milestones**: Explicit tracking of graduations, certificates, and transitions
5. **Audit Trail**: Complete history of all academic journey changes

## Model Architecture

### 1. AcademicJourney (Core Progression Tracker)

```python
class AcademicJourney(models.Model):
    """
    Tracks a student's complete academic journey at PUCSR.
    One record per student, updated as they progress.
    """
    # Core Fields
    student = models.OneToOneField('people.StudentProfile', on_delete=models.PROTECT)
    
    # Current Status
    current_program_type = models.CharField(max_length=20)  # LANGUAGE, BA, MA
    current_program = models.ForeignKey('curriculum.Major', null=True)
    current_level = models.CharField(max_length=10, blank=True)  # For language programs
    journey_status = models.CharField(max_length=20)  # ACTIVE, GRADUATED, DROPPED, etc.
    
    # Journey Dates
    first_enrollment_date = models.DateField()
    last_activity_date = models.DateField()
    expected_completion_date = models.DateField(null=True)
    
    # Summary Statistics (Denormalized for Performance)
    total_terms_enrolled = models.IntegerField(default=0)
    total_credits_earned = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    language_programs_completed = models.JSONField(default=list)  # ['IEAP-4', 'GESL-12']
    degrees_earned = models.JSONField(default=list)  # ['BA-IR-2018', 'MA-TESOL-2020']
    
    # Performance Indexes
    class Meta:
        indexes = [
            models.Index(fields=['journey_status', 'current_program_type']),
            models.Index(fields=['current_program', 'journey_status']),
        ]
```

### 2. ProgramMilestone (Event Records)

```python
class ProgramMilestone(models.Model):
    """
    Records key events in a student's academic journey.
    Multiple records per student, one for each significant event.
    """
    class MilestoneType(models.TextChoices):
        # Enrollments
        PROGRAM_START = 'PROG_START', 'Program Start'
        LEVEL_ADVANCE = 'LEVEL_ADV', 'Level Advancement'  # Language programs
        MAJOR_DECLARE = 'MAJOR_DEC', 'Major Declaration'
        MAJOR_CHANGE = 'MAJOR_CHG', 'Major Change'
        
        # Completions
        LEVEL_COMPLETE = 'LEVEL_COMP', 'Level Completion'
        PROGRAM_COMPLETE = 'PROG_COMP', 'Program Completion'
        DEGREE_EARNED = 'DEGREE', 'Degree Earned'
        CERTIFICATE_EARNED = 'CERT', 'Certificate Earned'
        
        # Exits
        WITHDRAWAL = 'WITHDRAW', 'Withdrawal'
        DISMISSAL = 'DISMISS', 'Academic Dismissal'
        LEAVE_OF_ABSENCE = 'LOA', 'Leave of Absence'
        TRANSFER = 'TRANSFER', 'Transfer'
    
    # Core Fields
    journey = models.ForeignKey(AcademicJourney, on_delete=models.CASCADE, related_name='milestones')
    milestone_type = models.CharField(max_length=20, choices=MilestoneType.choices)
    milestone_date = models.DateField(db_index=True)
    academic_term = models.ForeignKey('curriculum.Term', on_delete=models.PROTECT, null=True)
    
    # Context Fields
    program = models.ForeignKey('curriculum.Major', on_delete=models.PROTECT, null=True)
    from_program = models.ForeignKey('curriculum.Major', on_delete=models.PROTECT, null=True, related_name='+')
    level = models.CharField(max_length=10, blank=True)  # For language levels
    
    # Metadata
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    recorded_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    
    # Performance Indexes
    class Meta:
        indexes = [
            models.Index(fields=['journey', 'milestone_date']),
            models.Index(fields=['milestone_type', 'milestone_date']),
            models.Index(fields=['program', 'milestone_type']),
        ]
```

### 3. AcademicProgression (Denormalized Performance View)

```python
class AcademicProgression(models.Model):
    """
    Denormalized view for high-performance queries and reporting.
    Updated via database triggers or periodic tasks.
    """
    # Student Reference
    student = models.OneToOneField('people.StudentProfile', on_delete=models.CASCADE)
    student_name = models.CharField(max_length=200)  # Denormalized
    student_id_number = models.CharField(max_length=20)  # Denormalized
    
    # Program Journey Summary
    entry_program = models.CharField(max_length=50)
    entry_date = models.DateField()
    entry_term = models.CharField(max_length=20)
    
    # Language Program Summary
    language_start_date = models.DateField(null=True)
    language_end_date = models.DateField(null=True)
    language_terms = models.IntegerField(default=0)
    language_final_level = models.CharField(max_length=20, blank=True)
    language_completion_status = models.CharField(max_length=20)  # COMPLETED, BYPASSED, DROPPED
    
    # BA Program Summary  
    ba_start_date = models.DateField(null=True)
    ba_major = models.CharField(max_length=100, blank=True)
    ba_major_changes = models.IntegerField(default=0)
    ba_terms = models.IntegerField(default=0)
    ba_credits = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    ba_gpa = models.DecimalField(max_digits=3, decimal_places=2, null=True)
    ba_completion_date = models.DateField(null=True)
    ba_completion_status = models.CharField(max_length=20)  # GRADUATED, DROPPED, ACTIVE
    
    # MA Program Summary
    ma_start_date = models.DateField(null=True)
    ma_program = models.CharField(max_length=100, blank=True)
    ma_terms = models.IntegerField(default=0)
    ma_credits = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    ma_gpa = models.DecimalField(max_digits=3, decimal_places=2, null=True)
    ma_completion_date = models.DateField(null=True)
    ma_completion_status = models.CharField(max_length=20)
    
    # Overall Journey Metrics
    total_terms = models.IntegerField(default=0)
    total_gap_terms = models.IntegerField(default=0)
    time_to_ba_days = models.IntegerField(null=True)  # From first enrollment
    time_to_ma_days = models.IntegerField(null=True)  # From BA graduation
    
    # Current Status
    current_status = models.CharField(max_length=50)
    last_enrollment_term = models.CharField(max_length=20)
    last_updated = models.DateTimeField(auto_now=True)
    
    # Optimized for Queries
    class Meta:
        indexes = [
            models.Index(fields=['current_status', 'entry_program']),
            models.Index(fields=['ba_major', 'ba_completion_status']),
            models.Index(fields=['ma_program', 'ma_completion_status']),
            models.Index(fields=['time_to_ba_days']),
            models.Index(fields=['time_to_ma_days']),
        ]
```

### 4. CertificateIssuance (Official Records)

```python
class CertificateIssuance(models.Model):
    """
    Official record of all certificates and degrees issued.
    """
    class CertificateType(models.TextChoices):
        # Language Certificates
        IEAP_CERT = 'IEAP', 'IEAP Completion Certificate'
        GESL_CERT = 'GESL', 'GESL Completion Certificate' 
        EHSS_CERT = 'EHSS', 'EHSS Completion Certificate'
        
        # Degrees
        BA_DEGREE = 'BA', 'Bachelor of Arts'
        MA_DEGREE = 'MA', 'Master of Arts'
        
        # Other
        TRANSCRIPT = 'TRANS', 'Official Transcript'
        LETTER = 'LETTER', 'Completion Letter'
    
    # Core Fields
    student = models.ForeignKey('people.StudentProfile', on_delete=models.PROTECT)
    certificate_type = models.CharField(max_length=20, choices=CertificateType.choices)
    issue_date = models.DateField(db_index=True)
    
    # Program Details
    program = models.ForeignKey('curriculum.Major', on_delete=models.PROTECT, null=True)
    completion_level = models.CharField(max_length=20, blank=True)  # For language programs
    gpa = models.DecimalField(max_digits=3, decimal_places=2, null=True)
    
    # Document Tracking
    certificate_number = models.CharField(max_length=50, unique=True)
    issued_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    printed_date = models.DateField(null=True)
    collected_date = models.DateField(null=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['student', 'certificate_type']),
            models.Index(fields=['issue_date', 'certificate_type']),
        ]
```

## Handling Unreliable Legacy Data

Since the legacy system lacks progression tracking and has data reliability issues, our design includes:

### Data Quality Indicators

Add to `AcademicJourney` model:
```python
# Data Quality Fields
data_source = models.CharField(max_length=20)  # LEGACY, MANUAL, SYSTEM
confidence_score = models.DecimalField(max_digits=3, decimal_places=2, default=1.0)  # 0.0-1.0
data_issues = models.JSONField(default=list)  # ['missing_terms', 'major_conflict', etc.]
requires_review = models.BooleanField(default=False)
last_manual_review = models.DateTimeField(null=True)
```

Add to `ProgramMilestone` model:
```python
# Data Quality Fields  
is_inferred = models.BooleanField(default=False)  # True if deduced from enrollments
confidence_score = models.DecimalField(max_digits=3, decimal_places=2, default=1.0)
inference_method = models.CharField(max_length=50, blank=True)  # 'course_pattern', 'timing', etc.
```

### Intelligent Retrospective Population Algorithm

```python
class ProgressionBuilder:
    """
    Builds academic progression from unreliable enrollment data.
    Handles gaps, conflicts, and missing data gracefully.
    """
    
    def build_student_journey(self, student_id):
        enrollments = self.get_enrollments_chronologically(student_id)
        
        # Detect program phases with confidence scoring
        phases = []
        confidence_issues = []
        
        # Phase 1: Language Program Detection
        language_phase = self.detect_language_phase(enrollments)
        if language_phase:
            phases.append(language_phase)
            if language_phase.confidence < 0.8:
                confidence_issues.append('uncertain_language_progression')
        
        # Phase 2: BA Program Detection  
        ba_phase = self.detect_ba_phase(enrollments)
        if ba_phase:
            # Handle major detection with fallback strategies
            major = self.detect_major_smart(ba_phase.enrollments)
            if not major.is_certain:
                confidence_issues.append('uncertain_major')
                
        # Create journey with appropriate confidence
        journey = AcademicJourney.objects.create(
            student=student,
            data_source='LEGACY',
            confidence_score=self.calculate_overall_confidence(phases),
            data_issues=confidence_issues,
            requires_review=len(confidence_issues) > 0
        )
        
        return journey
    
    def detect_major_smart(self, enrollments):
        """
        Multi-strategy major detection with confidence scoring.
        """
        strategies = [
            self.detect_by_signature_courses,  # Most reliable
            self.detect_by_course_frequency,   # Good indicator
            self.detect_by_advisor_notes,      # If available
            self.detect_by_legacy_codes,       # Last resort
        ]
        
        results = []
        for strategy in strategies:
            result = strategy(enrollments)
            if result:
                results.append(result)
        
        # Combine results with weighted confidence
        return self.combine_detection_results(results)
```

### Conflict Resolution System

```python
class ConflictResolver:
    """
    Handles data conflicts and ambiguities in legacy data.
    """
    
    def resolve_major_conflicts(self, student_id):
        # Get all possible major indicators
        indicators = {
            'course_patterns': self.analyze_course_patterns(student_id),
            'advisor_records': self.check_advisor_records(student_id),
            'legacy_fields': self.check_legacy_program_fields(student_id),
            'graduation_records': self.check_graduation_major(student_id)
        }
        
        # Apply resolution rules
        if self.all_indicators_agree(indicators):
            return indicators['course_patterns'], confidence=0.95
        elif self.majority_agrees(indicators):
            return self.get_majority_choice(indicators), confidence=0.75
        else:
            # Flag for manual review
            return self.make_best_guess(indicators), confidence=0.40
```

## Implementation Strategy (Revised)

### Phase 1: Core Models with Data Quality Support (Week 1)
1. Create models with data quality fields
2. Add confidence scoring throughout
3. Create admin interfaces with review workflows

### Phase 2: Retrospective Population System (Week 2-3)
1. Build intelligent detection algorithms
2. Create conflict resolution system
3. Implement batch processing with progress tracking
4. Generate quality reports for manual review

### Phase 3: Manual Review Tools (Week 3)
1. Create review dashboard for low-confidence records
2. Build correction tools with audit trail
3. Add bulk correction capabilities

### Phase 4: Performance & Forward-Looking System (Week 4)
1. Optimize queries with proper indexing
2. Create triggers for new enrollments
3. Build real-time progression tracking
4. Transition to forward-looking for new data

## Key Benefits

1. **Performance**: Denormalized AcademicProgression enables sub-second queries
2. **Clarity**: Clear separation between journey tracking and milestone events
3. **Flexibility**: Easy to add new milestone types without schema changes
4. **Auditability**: Complete history in ProgramMilestone table
5. **Reliability**: Forward-looking design, not retrospective guessing

## Migration Path

1. Keep existing ClassHeaderEnrollment and related models
2. Build new system in parallel
3. Populate historical data via management command
4. Gradually transition reporting to new models
5. Deprecate ProgramEnrollment once stable

## Query Examples

```python
# Get all students who dropped out at IEAP Level 3
dropouts = AcademicProgression.objects.filter(
    language_completion_status='DROPPED',
    language_final_level='3',
    entry_program='IEAP'
)

# Average time to BA graduation by major
from django.db.models import Avg
ba_times = AcademicProgression.objects.filter(
    ba_completion_status='GRADUATED'
).values('ba_major').annotate(
    avg_days=Avg('time_to_ba_days')
)

# Students with major changes
major_changers = AcademicProgression.objects.filter(
    ba_major_changes__gt=0
).select_related('student')
```

## Success Metrics

- Query performance: <100ms for summary statistics
- Data accuracy: 100% milestone recording
- User satisfaction: Clear at-a-glance views
- Maintenance: Easy to extend and modify