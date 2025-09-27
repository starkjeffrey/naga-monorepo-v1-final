"""Common mixins for Django models.

This module contains reusable mixins that provide common functionality
across multiple Django apps following clean architecture principles.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

if TYPE_CHECKING:
    from datetime import date


class DateRangeValidationMixin(models.Model):
    """Mixin for validating non-overlapping date ranges.

    Provides validation to ensure that date ranges (effective_date to end_date)
    do not overlap for records with the same grouping fields.

    Usage:
        class CourseFixedPricing(DateRangeValidationMixin, BasePricingModel):
            # DateRangeValidationMixin configuration
            date_range_fields = ['effective_date', 'end_date']
            date_range_scope_fields = ['course']  # Fields that define the scope for overlap checking

            # ... model fields ...

            class Meta:
                # ... other meta options ...
    """

    class Meta:
        abstract = True

    def clean(self) -> None:
        """Validate that date ranges don't overlap within the same scope."""
        super().clean()

        # Get the date range field names from class attributes
        date_range_fields = getattr(self.__class__, "date_range_fields", None)
        date_range_scope_fields = getattr(self.__class__, "date_range_scope_fields", None)

        if not date_range_fields or not date_range_scope_fields:
            return

        if len(date_range_fields) != 2:
            raise ValueError("date_range_fields must contain exactly 2 fields: [start_field, end_field]")

        start_field, end_field = date_range_fields
        start_date = getattr(self, start_field, None)
        end_date = getattr(self, end_field, None)

        if not start_date:
            return  # Can't validate without start date

        # Build the scope filter to check overlaps within the same scope
        scope_filter = {}
        for field in date_range_scope_fields:
            value = getattr(self, field, None)
            if value is None:
                return  # Can't validate without scope values
            scope_filter[field] = value

        # Get queryset of other records in the same scope
        queryset = self.__class__.objects.filter(**scope_filter)

        # Exclude self if updating existing record
        if self.pk:
            queryset = queryset.exclude(pk=self.pk)

        # Check for overlaps
        for existing in queryset:
            existing_start = getattr(existing, start_field)
            existing_end = getattr(existing, end_field)

            if self._date_ranges_overlap(start_date, end_date, existing_start, existing_end):
                scope_description = ", ".join([f"{field}={getattr(self, field)}" for field in date_range_scope_fields])

                error_msg = _(
                    "Date range {start} to {end} overlaps with existing record "
                    "({existing_start} to {existing_end}) for {scope}."
                ).format(
                    start=start_date,
                    end=end_date or "∞",
                    existing_start=existing_start,
                    existing_end=existing_end or "∞",
                    scope=scope_description,
                )

                raise ValidationError({start_field: error_msg})

    def _date_ranges_overlap(self, start1: date, end1: date | None, start2: date, end2: date | None) -> bool:
        """Check if two date ranges overlap.

        Args:
            start1, end1: First date range (end1 can be None for open-ended)
            start2, end2: Second date range (end2 can be None for open-ended)

        Returns:
            bool: True if ranges overlap, False otherwise
        """
        # Convert None end dates to a far future date for comparison
        from datetime import date

        FAR_FUTURE = date(9999, 12, 31)

        effective_end1 = end1 or FAR_FUTURE
        effective_end2 = end2 or FAR_FUTURE

        # Two ranges overlap if:
        # start1 <= end2 AND start2 <= end1
        return start1 <= effective_end2 and start2 <= effective_end1


class SoftDeleteMixin(models.Model):
    """Mixin for soft delete functionality.

    Adds a deleted_at field and overrides delete() to perform soft deletes.
    Provides a custom manager that excludes soft-deleted records by default.
    """

    deleted_at: models.DateTimeField = models.DateTimeField(
        _("Deleted At"),
        null=True,
        blank=True,
        help_text=_("When this record was soft deleted"),
    )

    class Meta:
        abstract = True

    def delete(self, using: str | None = None, keep_parents: bool = False) -> None:
        """Perform soft delete by setting deleted_at timestamp."""
        if not self.deleted_at:
            from django.utils import timezone

            self.deleted_at = timezone.now()
            self.save(update_fields=["deleted_at"])

    def hard_delete(self, using: str | None = None, keep_parents: bool = False) -> None:
        """Perform actual database deletion."""
        super().delete(using=using, keep_parents=keep_parents)

    @property
    def is_deleted(self) -> bool:
        """Check if this record is soft deleted."""
        return self.deleted_at is not None


class ActiveManager(models.Manager):
    """Manager that excludes soft-deleted records by default."""

    def get_queryset(self) -> models.QuerySet:
        """Return queryset excluding soft-deleted records."""
        return super().get_queryset().filter(deleted_at__isnull=True)


class AuditableQuerySetMixin(models.QuerySet):
    """Mixin for querysets that provides audit-aware filtering methods."""

    def active(self) -> models.QuerySet:
        """Filter to only active (non-soft-deleted) records."""
        return self.filter(deleted_at__isnull=True)

    def deleted(self) -> models.QuerySet:
        """Filter to only soft-deleted records."""
        return self.filter(deleted_at__isnull=False)

    def current(self, as_of_date: date | None = None) -> models.QuerySet:
        """Filter to records that are current as of a specific date.

        Useful for models with effective_date/end_date fields.
        """
        if as_of_date is None:
            from django.utils import timezone

            as_of_date = timezone.now().date()

        return self.filter(effective_date__lte=as_of_date).filter(
            models.Q(end_date__isnull=True) | models.Q(end_date__gte=as_of_date)
        )
