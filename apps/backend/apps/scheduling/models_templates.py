"""Class Part Template models for automatic class structure generation.

This module provides template-based class part generation for language programs,
enabling automatic creation of class structures when new classes are created or
students are promoted to new levels.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, ClassVar

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _

from apps.common.models import SoftDeleteModel, TimestampedModel
from apps.scheduling.class_part_types import ClassPartType

if TYPE_CHECKING:
    from django.db.models.fields import CharField, DateField, DecimalField, TextField
    from django.db.models.fields.related import ForeignKey, ManyToManyField

    from apps.scheduling.models import ClassPart, ClassSession


class ClassPartTemplateSet(TimestampedModel, SoftDeleteModel):
    """Groups related class part templates for a program and level.

    Represents the complete structure of a class at a specific level,
    including all its parts (e.g., Ventures, Reading, Computer Training).
    Supports versioning through effective dates.
    """

    # Program and level identification
    program_code: CharField = models.CharField(
        _("Program Code"),
        max_length=20,
        help_text=_("Program code (EHSS, GESL, IEAP, EXPRESS)"),
        db_index=True,
    )
    level_number: models.IntegerField = models.IntegerField(
        _("Level Number"),
        help_text=_("Level number within the program"),
        db_index=True,
    )

    # Versioning
    effective_date: DateField = models.DateField(
        _("Effective Date"),
        help_text=_("Date this template set becomes active"),
        db_index=True,
    )
    expiry_date: DateField = models.DateField(
        _("Expiry Date"),
        null=True,
        blank=True,
        help_text=_("Date this template set expires (null = no expiry)"),
    )
    version: models.IntegerField = models.IntegerField(
        _("Version"),
        default=1,
        help_text=_("Version number for this template set"),
    )

    # Metadata
    name: CharField = models.CharField(
        _("Template Set Name"),
        max_length=200,
        help_text=_("Descriptive name for this template set"),
    )
    description: TextField = models.TextField(
        _("Description"),
        blank=True,
        help_text=_("Description of this template structure"),
    )
    is_active: models.BooleanField = models.BooleanField(
        _("Is Active"),
        default=True,
        help_text=_("Whether this template set is currently active"),
        db_index=True,
    )

    # Configuration
    auto_apply_on_promotion: models.BooleanField = models.BooleanField(
        _("Auto Apply on Promotion"),
        default=True,
        help_text=_("Automatically apply this template when students are promoted to this level"),
    )
    preserve_section_cohort: models.BooleanField = models.BooleanField(
        _("Preserve Section Cohort"),
        default=True,
        help_text=_("Keep students in same section when promoted"),
    )

    class Meta:
        verbose_name = _("Class Part Template Set")
        verbose_name_plural = _("Class Part Template Sets")
        unique_together = [["program_code", "level_number", "version"]]
        ordering = ["-effective_date", "program_code", "level_number"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["program_code", "level_number", "-effective_date"]),
            models.Index(fields=["effective_date", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.program_code}-{self.level_number:02d} v{self.version} ({self.effective_date})"

    @property
    def level_code(self) -> str:
        """Generate level code (e.g., EHSS-07)."""
        return f"{self.program_code}-{self.level_number:02d}"

    def is_current(self) -> bool:
        """Check if this template set is currently active."""
        from django.utils import timezone

        today = timezone.now().date()

        if not self.is_active:
            return False
        if self.effective_date > today:
            return False
        if self.expiry_date and self.expiry_date < today:
            return False
        return True

    @classmethod
    def get_current_for_level(cls, program_code: str, level_number: int) -> ClassPartTemplateSet | None:
        """Get the current active template set for a program and level."""
        from django.utils import timezone

        today = timezone.now().date()

        return (
            cls.objects.filter(
                program_code=program_code,
                level_number=level_number,
                is_active=True,
                effective_date__lte=today,
                is_deleted=False,
            )
            .filter(models.Q(expiry_date__isnull=True) | models.Q(expiry_date__gte=today))
            .order_by("-effective_date")
            .first()
        )

    def apply_to_session(self, class_session: ClassSession) -> list[ClassPart]:
        """Apply this template set to create class parts for a session."""
        from apps.scheduling.models import ClassPart

        created_parts = []
        with transaction.atomic():
            for template in self.templates.filter(is_active=True).order_by("sequence_order"):
                part = ClassPart(
                    class_session=class_session,
                    class_part_type=template.class_part_type,
                    class_part_code=template.class_part_code,
                    name=template.name,
                    meeting_days=template.meeting_days_pattern,
                    grade_weight=template.grade_weight,
                    template_derived=True,
                    notes=f"Created from template: {self}",
                )
                part.save()

                # Add textbooks if specified
                if template.default_textbooks.exists():
                    part.textbooks.set(template.default_textbooks.all())

                created_parts.append(part)

        return created_parts

    def clean(self) -> None:
        """Validate template set data."""
        super().clean()

        # Validate date ordering
        if self.expiry_date and self.expiry_date <= self.effective_date:
            raise ValidationError({"expiry_date": _("Expiry date must be after effective date.")})

        # Check for overlapping active templates
        if self.is_active and not self.pk:  # Only for new templates
            overlapping = (
                ClassPartTemplateSet.objects.filter(
                    program_code=self.program_code,
                    level_number=self.level_number,
                    is_active=True,
                    is_deleted=False,
                )
                .filter(models.Q(expiry_date__isnull=True) | models.Q(expiry_date__gte=self.effective_date))
                .filter(effective_date__lte=self.expiry_date if self.expiry_date else models.F("effective_date"))
            )

            if overlapping.exists():
                raise ValidationError(_("Active template sets cannot have overlapping date ranges."))


class ClassPartTemplate(TimestampedModel, SoftDeleteModel):
    """Template for a single class part within a template set.

    Defines the structure and properties of one part of a class
    (e.g., the Reading component of EHSS-07).
    """

    # Link to template set
    template_set: ForeignKey[ClassPartTemplateSet] = models.ForeignKey(
        ClassPartTemplateSet,
        on_delete=models.CASCADE,
        related_name="templates",
        verbose_name=_("Template Set"),
    )

    # Part identification
    class_part_type: CharField = models.CharField(
        _("Class Part Type"),
        max_length=20,
        choices=ClassPartType.choices,
        default=ClassPartType.MAIN,
        help_text=_("Type of class component"),
    )
    class_part_code: models.PositiveSmallIntegerField = models.PositiveSmallIntegerField(
        _("Class Part Code"),
        default=1,
        help_text=_("Numeric identifier for this part (1, 2, 3, etc.)"),
    )
    name: CharField = models.CharField(
        _("Part Name"),
        max_length=100,
        help_text=_("Name for this part (e.g., 'Ventures Ventures', 'Reading')"),
    )

    # Scheduling pattern
    meeting_days_pattern: CharField = models.CharField(
        _("Meeting Days Pattern"),
        max_length=50,
        help_text=_("Days pattern (e.g., 'MON,WED' or 'TUE,THU' or 'FRI')"),
    )
    sequence_order: models.IntegerField = models.IntegerField(
        _("Sequence Order"),
        default=0,
        help_text=_("Order in which parts should be created"),
    )

    # Academic configuration
    grade_weight: DecimalField = models.DecimalField(
        _("Grade Weight"),
        max_digits=4,
        decimal_places=3,
        default=Decimal("1.000"),
        validators=[
            MinValueValidator(Decimal("0.000")),
            MaxValueValidator(Decimal("1.000")),
        ],
        help_text=_("Weight of this part in final grade (0.000-1.000)"),
    )

    # Default resources
    default_textbooks: ManyToManyField = models.ManyToManyField(
        "curriculum.Textbook",
        blank=True,
        related_name="template_parts",
        verbose_name=_("Default Textbooks"),
        help_text=_("Default textbooks for this part"),
    )

    # Configuration
    is_active: models.BooleanField = models.BooleanField(
        _("Is Active"),
        default=True,
        help_text=_("Whether this template is active"),
    )
    notes: TextField = models.TextField(
        _("Notes"),
        blank=True,
        help_text=_("Additional notes about this template"),
    )

    class Meta:
        verbose_name = _("Class Part Template")
        verbose_name_plural = _("Class Part Templates")
        unique_together = [["template_set", "class_part_code"]]
        ordering = ["template_set", "sequence_order", "class_part_code"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["template_set", "sequence_order"]),
        ]

    def __str__(self) -> str:
        return f"{self.template_set.level_code} - {self.name} ({self.class_part_code})"  # type: ignore[attr-defined]

    def clean(self) -> None:
        """Validate template data."""
        super().clean()

        # Validate meeting days pattern
        if self.meeting_days_pattern:
            valid_days = {"MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"}
            days = [day.strip().upper() for day in self.meeting_days_pattern.split(",")]
            invalid_days = [day for day in days if day not in valid_days]
            if invalid_days:
                raise ValidationError({"meeting_days_pattern": _(f"Invalid days: {', '.join(invalid_days)}")})


class ClassPromotionRule(TimestampedModel, SoftDeleteModel):
    """Rules for promoting students between levels.

    Defines how students move from one level to another,
    including cohort preservation and template application.
    """

    # Source and destination
    source_program: CharField = models.CharField(
        _("Source Program"),
        max_length=20,
        help_text=_("Program code students are promoted from"),
    )
    source_level: models.IntegerField = models.IntegerField(
        _("Source Level"),
        help_text=_("Level number students are promoted from"),
    )
    destination_program: CharField = models.CharField(
        _("Destination Program"),
        max_length=20,
        help_text=_("Program code students are promoted to"),
    )
    destination_level: models.IntegerField = models.IntegerField(
        _("Destination Level"),
        help_text=_("Level number students are promoted to"),
    )

    # Configuration
    preserve_cohort: models.BooleanField = models.BooleanField(
        _("Preserve Cohort"),
        default=True,
        help_text=_("Keep students together in same section"),
    )
    auto_create_classes: models.BooleanField = models.BooleanField(
        _("Auto Create Classes"),
        default=True,
        help_text=_("Automatically create new classes for promoted students"),
    )
    apply_template: models.BooleanField = models.BooleanField(
        _("Apply Template"),
        default=True,
        help_text=_("Apply class part templates to new classes"),
    )

    # Metadata
    is_active: models.BooleanField = models.BooleanField(
        _("Is Active"),
        default=True,
        help_text=_("Whether this rule is active"),
    )
    notes: TextField = models.TextField(
        _("Notes"),
        blank=True,
        help_text=_("Additional notes about this promotion rule"),
    )

    class Meta:
        verbose_name = _("Class Promotion Rule")
        verbose_name_plural = _("Class Promotion Rules")
        unique_together = [["source_program", "source_level", "destination_program", "destination_level"]]
        ordering = ["source_program", "source_level"]

    def __str__(self) -> str:
        return (
            f"{self.source_program}-{self.source_level:02d} → {self.destination_program}-{self.destination_level:02d}"
        )
