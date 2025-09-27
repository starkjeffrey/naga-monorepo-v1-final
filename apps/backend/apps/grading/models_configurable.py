"""Configurable grading scales and levels.

These models allow for custom grading scales beyond the standard institutional ones.
They were moved from apps.settings to maintain proper domain boundaries.
"""

from typing import ClassVar

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import UserAuditModel


class ConfigurableGradeScale(UserAuditModel):
    """Configurable grading scales for academic programs.

    This allows institutions to define custom grading scales beyond
    the standard LANGUAGE_STANDARD, LANGUAGE_IEAP, and ACADEMIC scales.
    """

    name: models.CharField = models.CharField(
        _("Scale Name"),
        max_length=100,
        unique=True,
        help_text=_("Name of this grading scale"),
    )
    description: models.TextField = models.TextField(
        _("Description"),
        blank=True,
        help_text=_("Description of when to use this scale"),
    )
    is_default: models.BooleanField = models.BooleanField(
        _("Is Default"), default=False, help_text=_("Whether this is the default grading scale")
    )
    is_active: models.BooleanField = models.BooleanField(
        _("Is Active"), default=True, help_text=_("Whether this scale is currently in use")
    )

    class Meta:
        verbose_name = _("Configurable Grade Scale")
        verbose_name_plural = _("Configurable Grade Scales")
        ordering = ["-is_default", "name"]

    def __str__(self):
        return self.name

    def clean(self):
        """Ensure only one default grade scale exists."""
        if self.is_default:
            existing_default = ConfigurableGradeScale.objects.filter(is_default=True)
            if self.pk:
                existing_default = existing_default.exclude(pk=self.pk)
            if existing_default.exists():
                raise ValidationError(_("Only one default grade scale is allowed"))


class ConfigurableGradeLevel(UserAuditModel):
    """Individual grade levels within a configurable grading scale."""

    grade_scale: models.ForeignKey = models.ForeignKey(
        ConfigurableGradeScale, on_delete=models.CASCADE, related_name="grade_levels", verbose_name=_("Grade Scale")
    )
    letter_grade: models.CharField = models.CharField(
        _("Letter Grade"),
        max_length=5,
        help_text=_("Letter grade (A+, A, A-, B+, etc.)"),
    )
    min_percentage: models.DecimalField = models.DecimalField(
        _("Minimum Percentage"),
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_("Minimum percentage for this grade"),
    )
    max_percentage: models.DecimalField = models.DecimalField(
        _("Maximum Percentage"),
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_("Maximum percentage for this grade"),
    )
    grade_points: models.DecimalField = models.DecimalField(
        _("Grade Points"),
        max_digits=4,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(4)],
        help_text=_("GPA points for this grade"),
    )
    display_order: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Display Order"), default=0, help_text=_("Order for displaying grades (0 = highest)")
    )

    class Meta:
        verbose_name = _("Configurable Grade Level")
        verbose_name_plural = _("Configurable Grade Levels")
        unique_together = [
            ["grade_scale", "letter_grade"],
            ["grade_scale", "min_percentage"],
            ["grade_scale", "max_percentage"],
        ]
        ordering = ["grade_scale", "display_order"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["grade_scale", "display_order"]),
        ]

    def __str__(self):
        return f"{self.grade_scale.name}: {self.letter_grade}"

    def clean(self):
        """Validate grade level data."""
        if self.min_percentage >= self.max_percentage:
            raise ValidationError(_("Maximum percentage must be greater than minimum percentage"))
