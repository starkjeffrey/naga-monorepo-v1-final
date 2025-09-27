"""Management command to warm up cache for better performance.

This command pre-loads commonly accessed data into Redis cache
to improve initial page load times.
"""

import logging

from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.db.models import Count, Q, Sum

from apps.curriculum.services import TermService
from apps.enrollment.models import ClassHeaderEnrollment, ProgramEnrollment
from apps.finance.models import Invoice
from apps.people.models import StudentProfile
from apps.web_interface.performance import CacheManager

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Warm up cache with commonly accessed data."""

    help = "Pre-load frequently accessed data into cache for better performance"

    def handle(self, *args, **options):
        """Execute cache warming operations."""
        self.stdout.write("Starting cache warmup...")

        # Warm up current term cache
        self.warm_current_term()

        # Warm up student statistics
        self.warm_student_stats()

        # Warm up enrollment statistics
        self.warm_enrollment_stats()

        # Warm up financial statistics
        self.warm_financial_stats()

        self.stdout.write(self.style.SUCCESS("Cache warmup completed successfully!"))

    def warm_current_term(self):
        """Cache all active terms (ENG_A, ENG_B, BA, MA)."""
        try:
            # Cache all active terms
            active_terms = TermService.get_all_active_terms()
            if active_terms:
                cache.set("active_terms_all", active_terms, 300)
                self.stdout.write(f"✓ Cached {len(active_terms)} active terms:")
                for term in active_terms:
                    self.stdout.write(f"  - {term.term_type}: {term.code}")
            else:
                self.stdout.write(self.style.WARNING("No active terms found"))

            # Cache active terms by type
            active_terms_by_type = TermService.get_active_terms_by_type()
            cache.set("active_terms_by_type", active_terms_by_type, 300)

            # Count non-null terms
            active_count = sum(1 for term in active_terms_by_type.values() if term is not None)
            self.stdout.write(f"✓ Cached active terms by type: {active_count} term types active")

            # Keep backward compatibility - cache first term as current_term
            if active_terms:
                cache.set("current_term", active_terms[0], 300)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error caching active terms: {e}"))

    def warm_student_stats(self):
        """Cache student statistics."""
        try:
            # Cache overall student counts
            student_stats = StudentProfile.objects.aggregate(
                total_active=Count("id", filter=Q(current_status__in=["ACTIVE", "ENROLLED"])),
                total_graduated=Count("id", filter=Q(current_status="GRADUATED")),
                total_inactive=Count("id", filter=Q(current_status="INACTIVE")),
            )

            cache.set("student_stats", student_stats, CacheManager.TIMEOUT_MEDIUM)
            self.stdout.write(f"✓ Cached student statistics: {student_stats['total_active']} active students")

            # Cache student counts by status
            status_counts = StudentProfile.objects.values("current_status").annotate(count=Count("id"))
            cache.set("student_status_counts", list(status_counts), CacheManager.TIMEOUT_MEDIUM)
            self.stdout.write("✓ Cached student status counts")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error caching student stats: {e}"))

    def warm_enrollment_stats(self):
        """Cache enrollment statistics."""
        try:
            # Cache active class count
            active_classes = (
                ClassHeaderEnrollment.objects.filter(status__in=["ENROLLED", "ACTIVE"])
                .values("class_header")
                .distinct()
                .count()
            )
            cache.set("active_classes_count", active_classes, CacheManager.TIMEOUT_SHORT)
            self.stdout.write(f"✓ Cached active classes: {active_classes}")

            # Cache total program enrollments
            total_enrollments = ProgramEnrollment.objects.count()
            cache.set("total_program_enrollments", total_enrollments, CacheManager.TIMEOUT_MEDIUM)
            self.stdout.write(f"✓ Cached program enrollments: {total_enrollments}")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error caching enrollment stats: {e}"))

    def warm_financial_stats(self):
        """Cache financial statistics."""
        try:
            # Cache pending invoices
            invoice_stats = Invoice.objects.filter(status__in=["SENT", "PARTIALLY_PAID", "OVERDUE"]).aggregate(
                pending_total=Sum("total_amount"), pending_count=Count("id")
            )

            cache.set("pending_invoice_stats", invoice_stats, CacheManager.TIMEOUT_SHORT)
            self.stdout.write(f"✓ Cached pending invoices: {invoice_stats['pending_count']} invoices")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error caching financial stats: {e}"))
