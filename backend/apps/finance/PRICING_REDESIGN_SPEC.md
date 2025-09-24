# Pricing System Redesign Specification

## Overview

This specification outlines the complete redesign of the Naga SIS pricing system, splitting the current unified pricing model into four separate, domain-specific models that better represent the distinct pricing paradigms used by the institution.

## Business Requirements

### 1. Default Pricing
- **Purpose**: Set a standard price per credit for all regular courses in a cycle (BA/MA)
- **Current Price**: $75 per course
- **Scope**: Applies to all courses unless overridden by other pricing types
- **Users**: Registrar sets once per term/year

### 2. Fixed Course Pricing  
- **Purpose**: Override default pricing for specific courses
- **Example**: COMEX-488 costs $275 instead of default $75
- **Scope**: Specific course codes that have non-standard pricing
- **Users**: Department heads or registrar

### 3. Senior Project Pricing
- **Purpose**: Group-based pricing for senior project courses
- **Eligible Courses**: IR-489, FIN-489, BUS-489, THM-433
- **Pricing Tiers**:
  - 1-2 students (Individual/Pair)
  - 3-4 students (Small Group)  
  - 5 students (Full Group)
- **Special Features**: 
  - Total price is split among group members
  - Includes advisor payment amount
  - Includes committee member payment amount
- **Integration**: Must work with existing SeniorProjectGroup model

### 4. Reading/Request Class Pricing
- **Purpose**: Premium pricing for small enrollment classes
- **Pricing Tiers**:
  - 1-2 students (Tutorial)
  - 3-5 students (Small Class)
  - 6-15 students (Medium Class)
- **Features**:
  - Price per student
  - Minimum revenue guarantee
- **Integration**: Must work with existing "lock price" functionality
- **Scope**: Any course except fixed price and senior project courses

## Technical Requirements

### Database Schema

#### 1. Remove Existing Constraints
First, remove the constraints we added to CoursePricing that are no longer needed:

```python
# Migration to clean up CoursePricing
class Migration(migrations.Migration):
    operations = [
        migrations.RemoveConstraint(
            model_name='coursepricing',
            name='unique_course_pricing_no_tier',
        ),
        migrations.RemoveConstraint(
            model_name='coursepricing',
            name='unique_course_pricing_with_tier',
        ),
        # Restore original unique_together if needed
    ]
```

#### 2. Create Abstract Base Model

```python
# In apps/finance/models.py

class BasePricingModel(UserAuditModel):
    """Abstract base model for all pricing models."""
    
    effective_date = models.DateField(
        _("Effective Date"),
        default=date.today,
        help_text=_("Date this pricing becomes effective")
    )
    end_date = models.DateField(
        _("End Date"),
        null=True,
        blank=True,
        help_text=_("Date this pricing expires (null = indefinite)")
    )
    notes = models.TextField(
        _("Notes"),
        blank=True,
        help_text=_("Additional notes about this pricing")
    )
    
    class Meta:
        abstract = True
    
    @property
    def is_active(self) -> bool:
        """Check if this pricing is currently active."""
        today = timezone.now().date()
        return (self.effective_date <= today and 
                (self.end_date is None or self.end_date >= today))
```

#### 3. Model Definitions

##### DefaultPricing Model

```python
class DefaultPricing(BasePricingModel):
    """Default pricing for regular courses by cycle."""
    
    cycle = models.ForeignKey(
        "curriculum.Cycle",
        on_delete=models.PROTECT,
        related_name="default_pricing",
        verbose_name=_("Academic Cycle"),
        help_text=_("BA or MA cycle")
    )
    domestic_price = models.DecimalField(
        _("Domestic Price"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text=_("Price for Cambodian students")
    )
    foreign_price = models.DecimalField(
        _("Foreign Price"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text=_("Price for international students")
    )
    currency = models.CharField(
        _("Currency"),
        max_length=3,
        choices=Currency,
        default=Currency.USD,
        help_text=_("Currency for this price")
    )
    
    class Meta:
        verbose_name = _("Default Pricing")
        verbose_name_plural = _("Default Pricing")
        ordering = ["cycle", "-effective_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["cycle", "effective_date"],
                name="unique_default_per_cycle_date"
            )
        ]
        indexes = [
            models.Index(fields=["cycle", "effective_date"]),
            models.Index(fields=["effective_date", "end_date"]),
        ]
    
    def __str__(self) -> str:
        return f"{self.cycle} - ${self.domestic_price} (Effective: {self.effective_date})"
    
    def clean(self) -> None:
        """Validate pricing data."""
        super().clean()
        if self.end_date and self.end_date <= self.effective_date:
            raise ValidationError(
                {"end_date": _("End date must be after effective date.")}
            )
```

##### CourseFixedPricing Model

```python
class CourseFixedPricing(BasePricingModel):
    """Fixed pricing for specific courses that override defaults."""
    
    course = models.ForeignKey(
        "curriculum.Course",
        on_delete=models.CASCADE,
        related_name="fixed_pricing",
        verbose_name=_("Course"),
        help_text=_("Course with custom pricing")
    )
    domestic_price = models.DecimalField(
        _("Domestic Price"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text=_("Price for Cambodian students")
    )
    foreign_price = models.DecimalField(
        _("Foreign Price"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text=_("Price for international students")
    )
    currency = models.CharField(
        _("Currency"),
        max_length=3,
        choices=Currency,
        default=Currency.USD,
        help_text=_("Currency for this price")
    )
    override_reason = models.CharField(
        _("Override Reason"),
        max_length=200,
        blank=True,
        help_text=_("Why this course has special pricing")
    )
    
    class Meta:
        verbose_name = _("Course Fixed Pricing")
        verbose_name_plural = _("Course Fixed Pricing")
        ordering = ["course__code", "-effective_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["course", "effective_date"],
                name="unique_fixed_per_course_date"
            )
        ]
        indexes = [
            models.Index(fields=["course", "effective_date"]),
            models.Index(fields=["effective_date", "end_date"]),
        ]
    
    def __str__(self) -> str:
        return f"{self.course.code} - ${self.domestic_price}"
    
    def clean(self) -> None:
        """Validate pricing data."""
        super().clean()
        if self.end_date and self.end_date <= self.effective_date:
            raise ValidationError(
                {"end_date": _("End date must be after effective date.")}
            )
```

##### SeniorProjectPricing Model

```python
class SeniorProjectPricing(BasePricingModel):
    """Pricing for senior projects based on group size."""
    
    class GroupSizeTier(models.TextChoices):
        INDIVIDUAL = "1-2", _("1-2 Students")
        SMALL_GROUP = "3-4", _("3-4 Students")  
        FULL_GROUP = "5", _("5 Students")
    
    tier = models.CharField(
        _("Group Size Tier"),
        max_length=10,
        choices=GroupSizeTier.choices,
        help_text=_("Number of students in the project group")
    )
    total_price = models.DecimalField(
        _("Total Project Price"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text=_("Total price for the entire project (will be divided among students)")
    )
    advisor_payment = models.DecimalField(
        _("Advisor Payment"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)],
        help_text=_("Payment amount for project advisor")
    )
    committee_payment = models.DecimalField(
        _("Committee Member Payment"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)],
        help_text=_("Payment amount for each committee member")
    )
    currency = models.CharField(
        _("Currency"),
        max_length=3,
        choices=Currency,
        default=Currency.USD
    )
    
    class Meta:
        verbose_name = _("Senior Project Pricing")
        verbose_name_plural = _("Senior Project Pricing")
        ordering = ["tier", "-effective_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["tier", "effective_date"],
                name="unique_senior_project_tier_date"
            )
        ]
        indexes = [
            models.Index(fields=["tier", "effective_date"]),
            models.Index(fields=["effective_date", "end_date"]),
        ]
    
    def __str__(self) -> str:
        return f"Senior Project {self.tier}: ${self.total_price}"
    
    def clean(self) -> None:
        """Validate pricing data."""
        super().clean()
        if self.end_date and self.end_date <= self.effective_date:
            raise ValidationError(
                {"end_date": _("End date must be after effective date.")}
            )
    
    @property
    def price_per_student(self) -> Decimal:
        """Calculate price per student based on tier."""
        if self.tier == self.GroupSizeTier.INDIVIDUAL:
            # For 1-2 students, assume 2 for calculation
            return self.total_price / Decimal('2')
        elif self.tier == self.GroupSizeTier.SMALL_GROUP:
            # For 3-4 students, assume 4 for calculation
            return self.total_price / Decimal('4')
        else:  # FULL_GROUP
            return self.total_price / Decimal('5')
```

##### SeniorProjectCourse Model

```python
class SeniorProjectCourse(models.Model):
    """Configuration for courses that use senior project pricing."""
    
    course = models.OneToOneField(
        "curriculum.Course",
        on_delete=models.CASCADE,
        related_name="senior_project_config",
        verbose_name=_("Course"),
        help_text=_("Course that uses senior project pricing")
    )
    is_active = models.BooleanField(
        _("Is Active"),
        default=True,
        help_text=_("Whether this course currently uses senior project pricing")
    )
    requires_advisor = models.BooleanField(
        _("Requires Advisor"),
        default=True,
        help_text=_("Whether this project requires an advisor")
    )
    requires_committee = models.BooleanField(
        _("Requires Committee"),
        default=True,
        help_text=_("Whether this project requires committee members")
    )
    
    class Meta:
        verbose_name = _("Senior Project Course")
        verbose_name_plural = _("Senior Project Courses")
    
    def __str__(self) -> str:
        return f"{self.course.code} - Senior Project"
```

##### ReadingClassPricing Model

```python
class ReadingClassPricing(BasePricingModel):
    """Pricing for reading/request classes based on enrollment size."""
    
    class ClassSizeTier(models.TextChoices):
        TUTORIAL = "1-2", _("1-2 Students (Tutorial)")
        SMALL = "3-5", _("3-5 Students")
        MEDIUM = "6-15", _("6-15 Students")
    
    cycle = models.ForeignKey(
        "curriculum.Cycle",
        on_delete=models.PROTECT,
        related_name="reading_class_pricing",
        verbose_name=_("Academic Cycle"),
        help_text=_("BA or MA cycle")
    )
    tier = models.CharField(
        _("Class Size Tier"),
        max_length=10,
        choices=ClassSizeTier.choices,
        help_text=_("Number of students enrolled in the class")
    )
    price_per_student = models.DecimalField(
        _("Price Per Student"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text=_("Amount charged to each student")
    )
    minimum_revenue = models.DecimalField(
        _("Minimum Revenue"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text=_("Minimum total revenue for the class regardless of enrollment")
    )
    currency = models.CharField(
        _("Currency"),
        max_length=3,
        choices=Currency,
        default=Currency.USD
    )
    
    class Meta:
        verbose_name = _("Reading Class Pricing")
        verbose_name_plural = _("Reading Class Pricing")
        ordering = ["cycle", "tier", "-effective_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["cycle", "tier", "effective_date"],
                name="unique_reading_per_cycle_tier_date"
            )
        ]
        indexes = [
            models.Index(fields=["cycle", "tier", "effective_date"]),
            models.Index(fields=["effective_date", "end_date"]),
        ]
    
    def __str__(self) -> str:
        return f"{self.cycle} Reading Class {self.tier}: ${self.price_per_student}/student"
    
    def clean(self) -> None:
        """Validate pricing data."""
        super().clean()
        if self.end_date and self.end_date <= self.effective_date:
            raise ValidationError(
                {"end_date": _("End date must be after effective date.")}
            )
    
    def calculate_total(self, enrollment_count: int) -> Decimal:
        """Calculate total revenue for given enrollment."""
        student_total = self.price_per_student * Decimal(str(enrollment_count))
        return max(student_total, self.minimum_revenue)
```

### Service Layer Implementation

#### Master Pricing Service

```python
# In apps/finance/services/pricing_service.py

from decimal import Decimal
from typing import Optional, Tuple, Dict, Any
from django.db.models import Q
from django.utils import timezone

from apps.enrollment.models import ClassHeaderEnrollment, SeniorProjectGroup
from apps.curriculum.models import Course, ClassHeader
from apps.people.models import Student
from apps.finance.models import (
    DefaultPricing, CourseFixedPricing, SeniorProjectPricing,
    ReadingClassPricing, SeniorProjectCourse
)

class PricingService:
    """Master service that orchestrates all pricing calculations."""
    
    @classmethod
    def calculate_course_price(
        cls,
        course: Course,
        student: Student,
        term: 'Term',
        class_header: Optional[ClassHeader] = None,
        enrollment_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Calculate the price for a course enrollment.
        
        Args:
            course: The course to price
            student: The student enrolling
            term: The term of enrollment
            class_header: The specific class section (if known)
            enrollment_context: Additional context (e.g., is_reading_class)
            
        Returns:
            Dictionary containing:
                - price: Decimal amount
                - pricing_type: Description of pricing type used
                - currency: Currency code
                - details: Additional pricing details
        """
        # Determine if student is foreign
        is_foreign = cls._is_foreign_student(student)
        
        # 1. Check if it's a senior project course
        if cls._is_senior_project(course):
            return SeniorProjectPricingService.calculate_price(
                course, student, term, is_foreign
            )
        
        # 2. Check if it's a reading/request class
        if cls._is_reading_class(class_header, enrollment_context):
            return ReadingClassPricingService.calculate_price(
                class_header, course, student, is_foreign
            )
        
        # 3. Check for fixed course pricing
        fixed_result = CourseFixedPricingService.get_price(course, is_foreign)
        if fixed_result:
            return fixed_result
        
        # 4. Use default pricing
        return DefaultPricingService.get_price(course.cycle, is_foreign)
    
    @classmethod
    def _is_foreign_student(cls, student: Student) -> bool:
        """Determine if student should pay foreign rates."""
        # This method should check the student's nationality/residency
        # Implementation depends on your Student model
        return getattr(student, 'is_international', False)
    
    @classmethod
    def _is_senior_project(cls, course: Course) -> bool:
        """Check if course is configured for senior project pricing."""
        return SeniorProjectCourse.objects.filter(
            course=course,
            is_active=True
        ).exists()
    
    @classmethod
    def _is_reading_class(
        cls,
        class_header: Optional[ClassHeader],
        enrollment_context: Optional[Dict[str, Any]]
    ) -> bool:
        """Determine if this is a reading/request class."""
        if class_header and hasattr(class_header, 'is_reading_class'):
            return class_header.is_reading_class
        
        if enrollment_context:
            return enrollment_context.get('is_reading_class', False)
        
        return False
```

#### Individual Pricing Services

```python
# In apps/finance/services/pricing_services.py

class DefaultPricingService:
    """Service for default cycle-based pricing."""
    
    @classmethod
    def get_price(cls, cycle: 'Cycle', is_foreign: bool) -> Dict[str, Any]:
        """Get current default price for a cycle."""
        today = timezone.now().date()
        
        pricing = DefaultPricing.objects.filter(
            cycle=cycle,
            effective_date__lte=today
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=today)
        ).order_by('-effective_date').first()
        
        if not pricing:
            raise ValueError(f"No default pricing found for {cycle}")
        
        price = pricing.foreign_price if is_foreign else pricing.domestic_price
        
        return {
            'price': price,
            'pricing_type': f"Default {cycle} Pricing",
            'currency': pricing.currency,
            'details': {
                'effective_date': pricing.effective_date,
                'is_foreign': is_foreign
            }
        }


class CourseFixedPricingService:
    """Service for course-specific fixed pricing."""
    
    @classmethod
    def get_price(cls, course: Course, is_foreign: bool) -> Optional[Dict[str, Any]]:
        """Get fixed price for a course if it exists."""
        today = timezone.now().date()
        
        pricing = CourseFixedPricing.objects.filter(
            course=course,
            effective_date__lte=today
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=today)
        ).order_by('-effective_date').first()
        
        if not pricing:
            return None
        
        price = pricing.foreign_price if is_foreign else pricing.domestic_price
        
        return {
            'price': price,
            'pricing_type': "Fixed Course Pricing",
            'currency': pricing.currency,
            'details': {
                'course_code': course.code,
                'override_reason': pricing.override_reason,
                'is_foreign': is_foreign
            }
        }


class SeniorProjectPricingService:
    """Service for senior project group-based pricing."""
    
    @classmethod
    def calculate_price(
        cls,
        course: Course,
        student: Student,
        term: 'Term',
        is_foreign: bool
    ) -> Dict[str, Any]:
        """Calculate senior project price based on group size."""
        # Get student's project group
        project_group = cls._get_student_project_group(student, course, term)
        
        if project_group:
            group_size = project_group.members.count()
            tier = cls._get_tier_for_size(group_size)
        else:
            # Student not yet in a group - show individual pricing
            group_size = 1
            tier = SeniorProjectPricing.GroupSizeTier.INDIVIDUAL
        
        # Get current pricing for tier
        pricing = cls._get_pricing_for_tier(tier)
        
        # Calculate per-student share
        if group_size > 0:
            price_per_student = pricing.total_price / Decimal(str(group_size))
        else:
            price_per_student = pricing.total_price
        
        return {
            'price': price_per_student,
            'pricing_type': f"Senior Project ({group_size} student{'s' if group_size != 1 else ''})",
            'currency': pricing.currency,
            'details': {
                'tier': tier,
                'group_size': group_size,
                'total_project_price': pricing.total_price,
                'advisor_payment': pricing.advisor_payment,
                'committee_payment': pricing.committee_payment,
                'project_group_id': project_group.id if project_group else None
            }
        }
    
    @classmethod
    def _get_student_project_group(
        cls,
        student: Student,
        course: Course,
        term: 'Term'
    ) -> Optional['SeniorProjectGroup']:
        """Get the student's senior project group."""
        try:
            from apps.enrollment.models import SeniorProjectGroup
            return SeniorProjectGroup.objects.filter(
                members=student,
                project_course=course,
                term=term
            ).first()
        except ImportError:
            # Handle case where SeniorProjectGroup doesn't exist yet
            return None
    
    @classmethod
    def _get_tier_for_size(cls, size: int) -> str:
        """Determine pricing tier from group size."""
        if size <= 2:
            return SeniorProjectPricing.GroupSizeTier.INDIVIDUAL
        elif size <= 4:
            return SeniorProjectPricing.GroupSizeTier.SMALL_GROUP
        else:
            return SeniorProjectPricing.GroupSizeTier.FULL_GROUP
    
    @classmethod
    def _get_pricing_for_tier(cls, tier: str) -> SeniorProjectPricing:
        """Get current pricing for a tier."""
        today = timezone.now().date()
        
        pricing = SeniorProjectPricing.objects.filter(
            tier=tier,
            effective_date__lte=today
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=today)
        ).order_by('-effective_date').first()
        
        if not pricing:
            raise ValueError(f"No senior project pricing found for tier {tier}")
        
        return pricing


class ReadingClassPricingService:
    """Service for reading/request class size-based pricing."""
    
    @classmethod
    def calculate_price(
        cls,
        class_header: Optional[ClassHeader],
        course: Course,
        student: Student,
        is_foreign: bool
    ) -> Dict[str, Any]:
        """Calculate reading class price based on enrollment."""
        # Get enrollment count
        if class_header:
            enrollment_count = cls._get_class_enrollment_count(class_header)
        else:
            # If no class header yet, assume minimum
            enrollment_count = 1
        
        # Determine tier
        tier = cls._get_tier_for_size(enrollment_count)
        
        # Get pricing
        pricing = cls._get_pricing_for_tier(course.cycle, tier)
        
        # Reading classes typically charge same price regardless of nationality
        price = pricing.price_per_student
        
        return {
            'price': price,
            'pricing_type': f"Reading Class ({enrollment_count} student{'s' if enrollment_count != 1 else ''})",
            'currency': pricing.currency,
            'details': {
                'tier': tier,
                'enrollment_count': enrollment_count,
                'price_per_student': pricing.price_per_student,
                'minimum_revenue': pricing.minimum_revenue,
                'total_class_revenue': pricing.calculate_total(enrollment_count)
            }
        }
    
    @classmethod
    def _get_class_enrollment_count(cls, class_header: ClassHeader) -> int:
        """Get current enrollment count for a class."""
        return class_header.enrollments.filter(
            status=ClassHeaderEnrollment.EnrollmentStatus.REGISTERED
        ).count()
    
    @classmethod
    def _get_tier_for_size(cls, size: int) -> str:
        """Determine tier from class size."""
        if size <= 2:
            return ReadingClassPricing.ClassSizeTier.TUTORIAL
        elif size <= 5:
            return ReadingClassPricing.ClassSizeTier.SMALL
        else:
            return ReadingClassPricing.ClassSizeTier.MEDIUM
    
    @classmethod
    def _get_pricing_for_tier(
        cls,
        cycle: 'Cycle',
        tier: str
    ) -> ReadingClassPricing:
        """Get current pricing for a cycle and tier."""
        today = timezone.now().date()
        
        pricing = ReadingClassPricing.objects.filter(
            cycle=cycle,
            tier=tier,
            effective_date__lte=today
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=today)
        ).order_by('-effective_date').first()
        
        if not pricing:
            raise ValueError(
                f"No reading class pricing found for {cycle} tier {tier}"
            )
        
        return pricing
    
    @classmethod
    def lock_pricing_for_class(
        cls,
        class_header: ClassHeader,
        locked_by: 'User'
    ) -> None:
        """
        Lock the pricing for a reading class.
        This creates a snapshot of the current pricing that won't change.
        """
        # This would integrate with your existing lock price functionality
        # Implementation depends on how you want to store locked prices
        pass
```

### Admin Interface Implementation

```python
# In apps/finance/admin.py (add to existing file)

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import (
    DefaultPricing, CourseFixedPricing, SeniorProjectPricing,
    ReadingClassPricing, SeniorProjectCourse
)

@admin.register(DefaultPricing)
class DefaultPricingAdmin(admin.ModelAdmin):
    """Admin interface for default cycle-based pricing."""
    
    list_display = [
        'cycle', 'domestic_price_display', 'foreign_price_display',
        'effective_date', 'end_date', 'is_current', 'created_by'
    ]
    list_filter = ['cycle', 'effective_date', 'end_date']
    search_fields = ['cycle__name', 'notes']
    ordering = ['cycle', '-effective_date']
    date_hierarchy = 'effective_date'
    
    fieldsets = (
        (None, {
            'fields': ('cycle', 'effective_date', 'end_date'),
            'description': 'Set the default pricing for all regular courses in this cycle'
        }),
        (_('Pricing'), {
            'fields': ('domestic_price', 'foreign_price', 'currency'),
            'description': 'Prices will apply to all courses unless overridden'
        }),
        (_('Notes'), {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        (_('Audit'), {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',),
            'description': 'Automatically tracked'
        }),
    )
    
    readonly_fields = ['created_by', 'updated_by', 'created_at', 'updated_at']
    
    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
    
    @admin.display(description='Domestic')
    def domestic_price_display(self, obj):
        return format_html(
            '<strong>${}</strong>',
            obj.domestic_price
        )
    
    @admin.display(description='Foreign')
    def foreign_price_display(self, obj):
        return format_html(
            '<strong>${}</strong>',
            obj.foreign_price
        )
    
    @admin.display(boolean=True, description='Current')
    def is_current(self, obj):
        return obj.is_active


@admin.register(CourseFixedPricing)
class CourseFixedPricingAdmin(admin.ModelAdmin):
    """Admin interface for course-specific fixed pricing."""
    
    list_display = [
        'course_code', 'course_title_short', 'domestic_price_display',
        'foreign_price_display', 'effective_date', 'is_current'
    ]
    list_filter = [
        'course__cycle__division',
        'course__cycle',
        'effective_date',
        ('course__department', admin.RelatedOnlyFieldListFilter),
    ]
    search_fields = ['course__code', 'course__title', 'override_reason']
    raw_id_fields = ['course']
    ordering = ['course__code', '-effective_date']
    date_hierarchy = 'effective_date'
    
    fieldsets = (
        (_('Course Selection'), {
            'fields': ('course',),
            'description': 'Select the course that needs custom pricing'
        }),
        (_('Fixed Pricing'), {
            'fields': ('domestic_price', 'foreign_price', 'currency'),
            'description': 'This pricing overrides the default cycle pricing'
        }),
        (_('Validity Period'), {
            'fields': ('effective_date', 'end_date'),
        }),
        (_('Reason'), {
            'fields': ('override_reason',),
            'description': 'Document why this course has special pricing'
        }),
        (_('Notes'), {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
    
    @admin.display(description='Code', ordering='course__code')
    def course_code(self, obj):
        return obj.course.code
    
    @admin.display(description='Title')
    def course_title_short(self, obj):
        return obj.course.title[:40] + '...' if len(obj.course.title) > 40 else obj.course.title
    
    @admin.display(description='Domestic')
    def domestic_price_display(self, obj):
        return format_html('<strong>${}</strong>', obj.domestic_price)
    
    @admin.display(description='Foreign')
    def foreign_price_display(self, obj):
        return format_html('<strong>${}</strong>', obj.foreign_price)
    
    @admin.display(boolean=True, description='Current')
    def is_current(self, obj):
        return obj.is_active


@admin.register(SeniorProjectPricing)
class SeniorProjectPricingAdmin(admin.ModelAdmin):
    """Admin interface for senior project pricing."""
    
    list_display = [
        'tier', 'total_price_display', 'per_student_display',
        'advisor_payment', 'committee_payment',
        'effective_date', 'is_current'
    ]
    list_filter = ['tier', 'effective_date']
    ordering = ['tier', '-effective_date']
    date_hierarchy = 'effective_date'
    
    fieldsets = (
        (_('Group Size Configuration'), {
            'fields': ('tier',),
            'description': 'Select the student group size range'
        }),
        (_('Project Pricing'), {
            'fields': ('total_price', 'currency'),
            'description': 'Total project cost (automatically divided among group members)'
        }),
        (_('Faculty Compensation'), {
            'fields': ('advisor_payment', 'committee_payment'),
            'description': 'Payments to faculty for supervising the project'
        }),
        (_('Validity Period'), {
            'fields': ('effective_date', 'end_date'),
        }),
        (_('Notes'), {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
    
    @admin.display(description='Total Price')
    def total_price_display(self, obj):
        return format_html('<strong>${}</strong>', obj.total_price)
    
    @admin.display(description='Per Student (est.)')
    def per_student_display(self, obj):
        return format_html('~${}', obj.price_per_student)
    
    @admin.display(boolean=True, description='Current')
    def is_current(self, obj):
        return obj.is_active


@admin.register(SeniorProjectCourse)
class SeniorProjectCourseAdmin(admin.ModelAdmin):
    """Configure which courses use senior project pricing."""
    
    list_display = [
        'course_code', 'course_title', 'is_active',
        'requires_advisor', 'requires_committee'
    ]
    list_filter = ['is_active', 'requires_advisor', 'requires_committee']
    search_fields = ['course__code', 'course__title']
    raw_id_fields = ['course']
    
    fieldsets = (
        (_('Course Configuration'), {
            'fields': ('course', 'is_active'),
            'description': 'Senior project courses: IR-489, FIN-489, BUS-489, THM-433'
        }),
        (_('Requirements'), {
            'fields': ('requires_advisor', 'requires_committee'),
            'description': 'Faculty supervision requirements'
        }),
    )
    
    @admin.display(description='Code', ordering='course__code')
    def course_code(self, obj):
        return obj.course.code
    
    @admin.display(description='Title')
    def course_title(self, obj):
        return obj.course.title


@admin.register(ReadingClassPricing)
class ReadingClassPricingAdmin(admin.ModelAdmin):
    """Admin interface for reading/request class pricing."""
    
    list_display = [
        'cycle', 'tier', 'price_per_student_display',
        'minimum_revenue_display', 'effective_date', 'is_current'
    ]
    list_filter = ['cycle', 'tier', 'effective_date']
    ordering = ['cycle', 'tier', '-effective_date']
    date_hierarchy = 'effective_date'
    
    fieldsets = (
        (_('Academic Cycle'), {
            'fields': ('cycle',),
        }),
        (_('Class Size Configuration'), {
            'fields': ('tier',),
            'description': 'Number of students in the reading class'
        }),
        (_('Pricing Structure'), {
            'fields': ('price_per_student', 'minimum_revenue', 'currency'),
            'description': (
                'Students pay per-student price, but total revenue '
                'must meet minimum threshold'
            )
        }),
        (_('Validity Period'), {
            'fields': ('effective_date', 'end_date'),
        }),
        (_('Notes'), {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
    
    @admin.display(description='Per Student')
    def price_per_student_display(self, obj):
        return format_html('<strong>${}</strong>', obj.price_per_student)
    
    @admin.display(description='Min. Revenue')  
    def minimum_revenue_display(self, obj):
        return format_html('${}', obj.minimum_revenue)
    
    @admin.display(boolean=True, description='Current')
    def is_current(self, obj):
        return obj.is_active
    
    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj:  # Editing existing
            readonly.extend(['created_by', 'updated_by', 'created_at', 'updated_at'])
        return readonly
```

### Data Migration Strategy

```python
# In apps/finance/migrations/00XX_migrate_to_separated_pricing.py

from django.db import migrations
from decimal import Decimal

def migrate_pricing_data(apps, schema_editor):
    """Migrate existing pricing data to new models."""
    
    # Get models
    PricingTier = apps.get_model('finance', 'PricingTier')
    CoursePricing = apps.get_model('finance', 'CoursePricing')
    DefaultPricing = apps.get_model('finance', 'DefaultPricing')
    CourseFixedPricing = apps.get_model('finance', 'CourseFixedPricing')
    SeniorProjectPricing = apps.get_model('finance', 'SeniorProjectPricing')
    SeniorProjectCourse = apps.get_model('finance', 'SeniorProjectCourse')
    ReadingClassPricing = apps.get_model('finance', 'ReadingClassPricing')
    Course = apps.get_model('curriculum', 'Course')
    
    # 1. Migrate DEFAULT pricing tiers
    for tier in PricingTier.objects.filter(pricing_type='DEFAULT'):
        DefaultPricing.objects.create(
            cycle=tier.cycle,
            domestic_price=tier.local_price,
            foreign_price=tier.foreign_price,
            effective_date=tier.effective_date,
            end_date=None,  # You may need to determine this
            notes=f"Migrated from PricingTier: {tier.tier_name}",
            created_by=tier.created_by,
            updated_by=tier.updated_by,
            created_at=tier.created_at,
            updated_at=tier.updated_at
        )
    
    # 2. Migrate fixed course pricing
    # This depends on how you currently identify fixed pricing
    # Example: courses with specific pricing that don't follow tiers
    
    # 3. Migrate senior project pricing
    for tier in PricingTier.objects.filter(pricing_type='SENIOR_PROJECT'):
        # Map old tier names to new tier structure
        if '1' in tier.tier_name or '2' in tier.tier_name:
            new_tier = '1-2'
        elif '3' in tier.tier_name or '4' in tier.tier_name:
            new_tier = '3-4'
        else:
            new_tier = '5'
        
        SeniorProjectPricing.objects.create(
            tier=new_tier,
            total_price=tier.local_price,  # Adjust as needed
            advisor_payment=tier.advisor_payment or Decimal('0'),
            committee_payment=tier.committee_payment or Decimal('0'),
            effective_date=tier.effective_date,
            notes=f"Migrated from PricingTier: {tier.tier_name}",
            created_by=tier.created_by,
            updated_by=tier.updated_by
        )
    
    # 4. Configure senior project courses
    senior_project_codes = ['IR-489', 'FIN-489', 'BUS-489', 'THM-433']
    for code in senior_project_codes:
        course = Course.objects.filter(code=code).first()
        if course:
            SeniorProjectCourse.objects.create(
                course=course,
                is_active=True,
                requires_advisor=True,
                requires_committee=True
            )
    
    # 5. Migrate reading class pricing
    # This depends on your current structure
    
def reverse_migration(apps, schema_editor):
    """Remove migrated data if needed."""
    # Implement reverse migration
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('finance', '00XX_create_separated_pricing_models'),
        ('curriculum', '0001_initial'),
    ]
    
    operations = [
        migrations.RunPython(migrate_pricing_data, reverse_migration),
    ]
```

### Integration Points

#### Invoice Generation

```python
# Update apps/finance/services/invoice_service.py

def generate_invoice_line_items(enrollment, invoice):
    """Generate line items for an enrollment."""
    
    # Get pricing for the course
    pricing_result = PricingService.calculate_course_price(
        course=enrollment.class_header.course,
        student=enrollment.student,
        term=enrollment.class_header.term,
        class_header=enrollment.class_header,
        enrollment_context={
            'is_reading_class': enrollment.class_header.is_reading_class
        }
    )
    
    # Create line item
    InvoiceLineItem.objects.create(
        invoice=invoice,
        line_item_type=InvoiceLineItem.LineItemType.COURSE,
        description=f"{enrollment.class_header.course.code} - {pricing_result['pricing_type']}",
        enrollment=enrollment,
        unit_price=pricing_result['price'],
        quantity=Decimal('1.00'),
        line_total=pricing_result['price']
    )
```

#### API Endpoints

```python
# In apps/api/finance.py

from django_ninja import Router
from apps.finance.services import PricingService

router = Router()

@router.get("/pricing/calculate")
def calculate_pricing(
    request,
    course_id: int,
    student_id: int,
    term_id: int,
    class_header_id: Optional[int] = None
):
    """Calculate pricing for a course enrollment."""
    
    # Load objects
    course = get_object_or_404(Course, id=course_id)
    student = get_object_or_404(Student, id=student_id)
    term = get_object_or_404(Term, id=term_id)
    
    class_header = None
    if class_header_id:
        class_header = get_object_or_404(ClassHeader, id=class_header_id)
    
    # Calculate pricing
    result = PricingService.calculate_course_price(
        course=course,
        student=student,
        term=term,
        class_header=class_header
    )
    
    return result
```

### Testing Requirements

```python
# In apps/finance/tests/test_pricing_models.py

import pytest
from decimal import Decimal
from django.utils import timezone
from apps.finance.models import (
    DefaultPricing, CourseFixedPricing,
    SeniorProjectPricing, ReadingClassPricing
)

@pytest.mark.django_db
class TestPricingModels:
    """Test the new pricing models."""
    
    def test_default_pricing_active_check(self):
        """Test is_active property for default pricing."""
        pricing = DefaultPricing.objects.create(
            cycle=self.ba_cycle,
            domestic_price=Decimal('75.00'),
            foreign_price=Decimal('75.00'),
            effective_date=timezone.now().date()
        )
        assert pricing.is_active is True
    
    def test_senior_project_price_calculation(self):
        """Test price per student calculation."""
        pricing = SeniorProjectPricing.objects.create(
            tier=SeniorProjectPricing.GroupSizeTier.FULL_GROUP,
            total_price=Decimal('1000.00'),
            effective_date=timezone.now().date()
        )
        assert pricing.price_per_student == Decimal('200.00')
    
    # Add more tests...
```

### Rollback Plan

If issues arise:

1. Keep old models active with feature flag
2. Dual-write to both old and new models during transition
3. Monitor for discrepancies
4. Have SQL scripts ready to revert data migration

### Documentation Updates

Update the following documentation:
- Finance module README
- API documentation for pricing endpoints
- Admin user guide for pricing management
- Developer guide for pricing calculations

## Implementation Checklist

- [ ] Create new model files
- [ ] Create migrations for new models
- [ ] Implement service layer
- [ ] Create admin interfaces
- [ ] Write data migration scripts
- [ ] Update invoice generation
- [ ] Create API endpoints
- [ ] Write comprehensive tests
- [ ] Update documentation
- [ ] Train staff on new system
- [ ] Deploy with feature flags
- [ ] Monitor and validate
- [ ] Remove old models (after validation period)

## Notes for Implementation

1. Start with models and migrations
2. Build services with comprehensive tests
3. Create admin interfaces with good UX
4. Carefully migrate existing data
5. Use feature flags for safe rollout
6. Keep old system running in parallel initially
7. Monitor closely during transition
8. Document everything thoroughly