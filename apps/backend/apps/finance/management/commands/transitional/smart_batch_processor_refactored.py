"""Enterprise-scale smart batch processor for 100K+ legacy receipt reconstruction.

This refactored version includes:
- Proper type annotations throughout
- Optimized data structures and algorithms
- Clear separation of concerns
- Enhanced error handling
- Performance improvements
"""

import csv
import re
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Optional

from django.db import transaction
from django.utils import timezone

from apps.common.management.base_migration import BaseMigrationCommand
from apps.curriculum.models import Term
from apps.finance.models import Invoice, Payment
from apps.finance.models.ar_reconstruction import (
    ARReconstructionBatch,
    LegacyReceiptMapping,
)
from apps.people.models import StudentProfile

from .process_receipt_notes import NotesProcessor


@dataclass
class ProcessingStats:
    """Statistics for batch processing."""

    total_processed: int = 0
    successful: int = 0
    failed: int = 0
    skipped: int = 0
    success_rate: float = 0.0
    start_time: datetime | None = None
    last_checkpoint: datetime | None = None
    errors_by_category: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def update_success_rate(self) -> None:
        """Update the success rate calculation."""
        if self.total_processed > 0:
            self.success_rate = (self.successful / self.total_processed) * 100


@dataclass
class ReceiptData:
    """Structured receipt data with proper typing."""

    receipt_id: str
    receipt_no: str
    student_id: str
    term_id: str | None
    amount: Decimal
    net_amount: Decimal
    discount: Decimal
    notes: str
    payment_date: datetime | None
    payment_type: str
    program: str
    deleted: bool = False

    @classmethod
    def from_csv_row(cls, row: dict[str, Any]) -> Optional["ReceiptData"]:
        """Create ReceiptData from CSV row with validation."""
        try:
            # Skip deleted records
            if row.get("Deleted", "0").strip() == "1":
                return None

            # Parse amounts safely
            amount = cls._parse_decimal(row.get("Amount", "0"))
            net_amount = cls._parse_decimal(row.get("NetAmount", "0"))
            discount = cls._parse_decimal(row.get("NetDiscount", "0"))

            return cls(
                receipt_id=row.get("ReceiptID", "").strip(),
                receipt_no=row.get("ReceiptNo", "").strip(),
                student_id=row.get("ID", "").strip().zfill(5),
                term_id=row.get("TermID", "").strip() or None,
                amount=amount,
                net_amount=net_amount,
                discount=discount,
                notes=row.get("Notes", "").strip(),
                payment_date=cls._parse_date(row.get("PmtDate")),
                payment_type=row.get("PmtType", "Cash").strip(),
                program=row.get("Program", "").strip(),
            )
        except (ValueError, KeyError):
            return None

    @staticmethod
    def _parse_decimal(value: Any) -> Decimal:
        """Parse decimal value safely."""
        if not value or str(value).upper() == "NULL":
            return Decimal("0")
        try:
            return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except (ValueError, TypeError, InvalidOperation):
            return Decimal("0")

    @staticmethod
    def _parse_date(value: Any) -> datetime | None:
        """Parse date safely."""
        if not value or str(value).upper() == "NULL":
            return None
        try:
            date_str = str(value)
            if "." in date_str:
                date_str = date_str.split(".")[0]
            return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        except (ValueError, AttributeError, TypeError):
            return None


@dataclass
class DiscountInfo:
    """Structured discount information."""

    gl_type: str
    amount: Decimal | None = None
    percentage: Decimal | None = None
    applied_amount: Decimal = Decimal("0")
    text_matched: str = ""

    def calculate_amount(self, base_amount: Decimal) -> Decimal:
        """Calculate the actual discount amount."""
        if self.amount:
            return self.amount
        elif self.percentage:
            return (base_amount * self.percentage / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return self.applied_amount


@dataclass
class NotesAnalysis:
    """Result of analyzing receipt notes."""

    discounts: list[DiscountInfo] = field(default_factory=list)
    fees: list[dict[str, Any]] = field(default_factory=list)
    final_amount: Decimal | None = None
    calculation_steps: list[str] = field(default_factory=list)
    gl_discount_type: str | None = None
    total_discount: Decimal = Decimal("0")
    total_fees: Decimal = Decimal("0")


class OptimizedBatchProcessor(BaseMigrationCommand):
    """Optimized batch processor with proper typing and error handling."""

    help = "Enterprise batch processor for legacy receipts with enhanced typing"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.stats = ProcessingStats()
        self.notes_processor = NotesProcessor()
        self.batch: ARReconstructionBatch | None = None
        self.student_cache: dict[str, StudentProfile | None] = {}
        self.term_cache: dict[str, Term | None] = {}
        self.rejection_categories = self._initialize_rejection_categories()

    def _initialize_rejection_categories(self) -> dict[str, str]:
        """Initialize rejection categories."""
        return {
            "STUDENT_NOT_FOUND": "Student record not found",
            "TERM_NOT_FOUND": "Term record not found",
            "NULL_TERM_DROPPED": "NULL TermID",
            "MISSING_DATA": "Critical fields missing",
            "INVALID_FINANCIAL_DATA": "Invalid financial amounts",
            "PROCESSING_ERROR": "Unexpected error",
            "DUPLICATE_RECEIPT": "Duplicate receipt detected",
        }

    def get_rejection_categories(self) -> list[str]:
        """Return rejection category keys for base class."""
        return list(self.rejection_categories.keys())

    def add_arguments(self, parser: Any) -> None:
        """Add command arguments."""
        parser.add_argument(
            "--batch-size",
            type=int,
            default=1000,
            help="Records per batch (default: 1000)",
        )
        parser.add_argument(
            "--start-from",
            type=int,
            default=0,
            help="Start from record number",
        )
        parser.add_argument(
            "--max-records",
            type=int,
            help="Maximum records to process",
        )
        parser.add_argument(
            "--receipt-file",
            type=str,
            default="data/legacy/all_receipt_headers_250728.csv",
            help="Receipt CSV file path",
        )
        parser.add_argument(
            "--success-threshold",
            type=float,
            default=0.80,
            help="Minimum success rate (default: 80%)",
        )
        parser.add_argument(
            "--auto-resume",
            action="store_true",
            help="Auto-resume from last batch",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Dry run without database changes",
        )

    def execute_migration(self, *args: Any, **options: Any) -> None:
        """Execute the batch processing."""
        self.stats.start_time = timezone.now()

        try:
            # Initialize batch
            self._initialize_batch(options)

            # Load and process receipts
            receipts = self._load_receipts(options["receipt_file"])
            self._process_receipts(receipts, options)

            # Finalize
            self._finalize_batch()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Fatal error: {e}"))
            if self.batch:
                self.batch.status = ARReconstructionBatch.BatchStatus.FAILED
                self.batch.save()
            raise

    def _initialize_batch(self, options: dict[str, Any]) -> None:
        """Initialize processing batch."""
        batch_id = f"BATCH-{timezone.now().strftime('%Y%m%d-%H%M%S')}"

        self.batch = ARReconstructionBatch.objects.create(
            batch_id=batch_id,
            status=ARReconstructionBatch.BatchStatus.PROCESSING,
            processing_mode="SMART",
            processing_parameters={
                "batch_size": options["batch_size"],
                "success_threshold": options["success_threshold"],
                "dry_run": options.get("dry_run", False),
            },
        )

        self.stdout.write(f"Initialized batch: {batch_id}")

    def _load_receipts(self, file_path: str) -> Iterator[ReceiptData]:
        """Load receipts from CSV file."""
        csv_path = Path(file_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"Receipt file not found: {file_path}")

        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                receipt = ReceiptData.from_csv_row(row)
                if receipt:
                    yield receipt

    def _process_receipts(self, receipts: Iterator[ReceiptData], options: dict[str, Any]) -> None:
        """Process receipts in batches."""
        batch_size = options["batch_size"]
        start_from = options.get("start_from", 0)
        max_records = options.get("max_records")
        dry_run = options.get("dry_run", False)

        current_batch: list[ReceiptData] = []

        for i, receipt in enumerate(receipts):
            # Skip if before start position
            if i < start_from:
                continue

            # Stop if max records reached
            if max_records and self.stats.total_processed >= max_records:
                break

            current_batch.append(receipt)

            # Process batch when full
            if len(current_batch) >= batch_size:
                self._process_batch(current_batch, dry_run)
                current_batch = []

                # Check success threshold
                if not self._check_quality_gate(options["success_threshold"]):
                    self.stdout.write(self.style.WARNING("Quality gate failed, stopping"))
                    break

        # Process remaining receipts
        if current_batch:
            self._process_batch(current_batch, dry_run)

    def _process_batch(self, receipts: list[ReceiptData], dry_run: bool = False) -> None:
        """Process a batch of receipts."""
        batch_start = time.time()

        for receipt in receipts:
            try:
                if dry_run:
                    self._validate_receipt(receipt)
                else:
                    with transaction.atomic():
                        self._process_single_receipt(receipt)

                self.stats.successful += 1

            except Exception as e:
                self.stats.failed += 1
                error_category = self._categorize_error(e)
                self.stats.errors_by_category[error_category] = (
                    self.stats.errors_by_category.get(error_category, 0) + 1
                )

                self.record_rejection(
                    category=error_category,
                    record_id=receipt.receipt_no,
                    reason=str(e),
                    raw_data=receipt.__dict__,
                )

            finally:
                self.stats.total_processed += 1

        # Update statistics
        self.stats.update_success_rate()
        batch_time = time.time() - batch_start

        # Report progress
        self._report_progress(batch_time, len(receipts))

    def _process_single_receipt(self, receipt: ReceiptData) -> None:
        """Process a single receipt."""
        # Find student
        student = self._find_student(receipt.student_id)
        if not student:
            raise ValueError(f"Student not found: {receipt.student_id}")

        # Find term
        term = self._find_term(receipt.term_id)
        if not term:
            raise ValueError(f"Term not found: {receipt.term_id}")

        # Analyze notes
        notes_analysis = self._analyze_notes(receipt.notes, receipt.amount)

        # Create invoice
        invoice = self._create_invoice(
            student=student,
            term=term,
            receipt=receipt,
            notes_analysis=notes_analysis,
        )

        # Create payment
        payment = self._create_payment(
            invoice=invoice,
            receipt=receipt,
        )

        # Create mapping
        self._create_mapping(
            receipt=receipt,
            invoice=invoice,
            payment=payment,
            notes_analysis=notes_analysis,
        )

    def _validate_receipt(self, receipt: ReceiptData) -> None:
        """Validate receipt data without processing."""
        if not receipt.student_id:
            raise ValueError("Missing student ID")
        if not receipt.term_id:
            raise ValueError("Missing term ID")
        if receipt.amount <= 0:
            raise ValueError("Invalid amount")

    def _find_student(self, student_id: str) -> StudentProfile | None:
        """Find student with caching."""
        if student_id not in self.student_cache:
            try:
                self.student_cache[student_id] = StudentProfile.objects.get(student_id=student_id)
            except StudentProfile.DoesNotExist:
                self.student_cache[student_id] = None

        return self.student_cache[student_id]

    def _find_term(self, term_id: str | None) -> Term | None:
        """Find term with caching."""
        if not term_id:
            return None

        if term_id not in self.term_cache:
            try:
                self.term_cache[term_id] = Term.objects.get(code=term_id)
            except Term.DoesNotExist:
                self.term_cache[term_id] = None

        return self.term_cache[term_id]

    def _analyze_notes(self, notes: str, base_amount: Decimal) -> NotesAnalysis:
        """Analyze receipt notes for discounts and fees."""
        analysis = NotesAnalysis()

        if not notes or notes.strip().lower() in ["null", "none", ""]:
            return analysis

        notes_lower = notes.lower()

        # Check for final amount patterns
        final_patterns = [
            (r"pay\s*only\s*\$?(\d+(?:\.\d+)?)", "pay_only"),
            (r"final\s*amount\s*\$?(\d+(?:\.\d+)?)", "final_amount"),
        ]

        for pattern, gl_type in final_patterns:
            match = re.search(pattern, notes_lower)
            if match:
                try:
                    final_amount = Decimal(match.group(1))
                    if final_amount <= base_amount:
                        analysis.final_amount = final_amount
                        analysis.total_discount = base_amount - final_amount
                        analysis.gl_discount_type = gl_type
                        return analysis
                except (ValueError, TypeError):
                    pass

        # Check for discount patterns
        discount_patterns = [
            (r"(\d+(?:\.\d+)?)%\s*(?:early\s*bird)", "early_bird_discount"),
            (r"(\d+(?:\.\d+)?)%?\s*(?:staff|employee)", "staff_discount"),
            (r"(\d+(?:\.\d+)?)%?\s*(?:monk|religious)", "monk_discount"),
            (r"(\d+(?:\.\d+)?)%?\s*(?:sibling|family)", "family_discount"),
            (r"scholarship\s*\$?(\d+(?:\.\d+)?)", "scholarship"),
            (r"(\d+(?:\.\d+)?)%\s*discount", "general_discount"),
        ]

        for pattern, gl_type in discount_patterns:
            matches = re.finditer(pattern, notes_lower)
            for match in matches:
                try:
                    value = Decimal(match.group(1))

                    if "%" in match.group(0):
                        discount = DiscountInfo(
                            gl_type=gl_type,
                            percentage=value,
                            text_matched=match.group(0),
                        )
                    else:
                        discount = DiscountInfo(
                            gl_type=gl_type,
                            amount=value,
                            text_matched=match.group(0),
                        )

                    analysis.discounts.append(discount)

                except (ValueError, TypeError):
                    pass

        # Calculate total discount
        for discount in analysis.discounts:
            analysis.total_discount += discount.calculate_amount(base_amount)

        return analysis

    def _create_invoice(
        self,
        student: StudentProfile,
        term: Term,
        receipt: ReceiptData,
        notes_analysis: NotesAnalysis,
    ) -> Invoice:
        """Create invoice from receipt data."""
        invoice = Invoice(
            student=student,
            term=term,
            invoice_number=f"LEGACY-{receipt.receipt_no}",
            invoice_date=receipt.payment_date or timezone.now(),
            due_date=receipt.payment_date or timezone.now(),
            subtotal=receipt.amount,
            discount_applied=notes_analysis.total_discount,
            total_amount=receipt.net_amount,
            status=Invoice.InvoiceStatus.PAID,
            is_historical=True,
            legacy_receipt_number=receipt.receipt_no,
            notes=f"Reconstructed from legacy receipt: {receipt.notes}",
        )

        if not self.options.get("dry_run"):
            invoice.save()

        return invoice

    def _create_payment(
        self,
        invoice: Invoice,
        receipt: ReceiptData,
    ) -> Payment:
        """Create payment from receipt data."""
        payment = Payment(
            invoice=invoice,
            amount=receipt.net_amount,
            payment_date=receipt.payment_date or timezone.now(),
            payment_method=receipt.payment_type.upper()[:20],
            payment_reference=f"LEGACY-{receipt.receipt_no}",
            external_reference=receipt.receipt_id,
            is_historical_payment=True,
            legacy_receipt_reference=receipt.receipt_no,
            notes=f"Legacy payment: {receipt.notes}",
        )

        if not self.options.get("dry_run"):
            payment.save()

        return payment

    def _create_mapping(
        self,
        receipt: ReceiptData,
        invoice: Invoice,
        payment: Payment,
        notes_analysis: NotesAnalysis,
    ) -> None:
        """Create legacy receipt mapping."""
        if self.options.get("dry_run"):
            return

        LegacyReceiptMapping.objects.create(
            legacy_receipt_number=receipt.receipt_no,
            legacy_receipt_id=receipt.receipt_id,
            legacy_student_id=receipt.student_id,
            legacy_term_id=receipt.term_id,
            legacy_amount=receipt.amount,
            legacy_net_amount=receipt.net_amount,
            legacy_discount=receipt.discount,
            reconstructed_total=invoice.total_amount,
            variance_amount=receipt.net_amount - invoice.total_amount,
            legacy_notes=receipt.notes,
            generated_invoice=invoice,
            generated_payment=payment,
            reconstruction_batch=self.batch,
            validation_status="VALIDATED",
        )

    def _categorize_error(self, error: Exception) -> str:
        """Categorize error for reporting."""
        error_str = str(error).lower()

        if "student not found" in error_str:
            return "STUDENT_NOT_FOUND"
        elif "term not found" in error_str:
            return "TERM_NOT_FOUND"
        elif "invalid amount" in error_str:
            return "INVALID_FINANCIAL_DATA"
        elif "missing" in error_str:
            return "MISSING_DATA"
        else:
            return "PROCESSING_ERROR"

    def _check_quality_gate(self, threshold: float) -> bool:
        """Check if processing meets quality threshold."""
        if self.stats.total_processed < 10:
            return True  # Not enough data

        return self.stats.success_rate >= (threshold * 100)

    def _report_progress(self, batch_time: float, batch_size: int) -> None:
        """Report processing progress."""
        rate = batch_size / batch_time if batch_time > 0 else 0

        self.stdout.write(
            f"Processed: {self.stats.total_processed:,} | "
            f"Success: {self.stats.success_rate:.1f}% | "
            f"Rate: {rate:.1f} records/sec"
        )

        # Update batch if exists
        if self.batch:
            self.batch.processed_receipts = self.stats.total_processed
            self.batch.successful_reconstructions = self.stats.successful
            self.batch.failed_reconstructions = self.stats.failed
            self.batch.save()

    def _finalize_batch(self) -> None:
        """Finalize batch processing."""
        if not self.batch:
            return

        self.batch.status = ARReconstructionBatch.BatchStatus.COMPLETED
        self.batch.completed_at = timezone.now()
        self.batch.variance_summary = {
            "total_processed": self.stats.total_processed,
            "successful": self.stats.successful,
            "failed": self.stats.failed,
            "success_rate": self.stats.success_rate,
            "errors_by_category": self.stats.errors_by_category,
        }
        self.batch.save()

        # Generate final report
        self._generate_report()

    def _generate_report(self) -> None:
        """Generate final processing report."""
        duration = timezone.now() - self.stats.start_time if self.stats.start_time else timedelta()

        report = f"""
================================================================================
BATCH PROCESSING COMPLETE
================================================================================

Batch ID: {self.batch.batch_id if self.batch else "N/A"}
Duration: {duration}

STATISTICS:
-----------
Total Processed: {self.stats.total_processed:,}
Successful: {self.stats.successful:,}
Failed: {self.stats.failed:,}
Success Rate: {self.stats.success_rate:.2f}%

ERROR BREAKDOWN:
----------------"""

        for category, count in sorted(self.stats.errors_by_category.items()):
            report += f"\n{category}: {count:,}"

        report += "\n\n" + "=" * 80

        self.stdout.write(report)

        # Save report to file
        report_path = Path("project-docs/migration-reports")
        report_path.mkdir(parents=True, exist_ok=True)

        report_file = report_path / f"batch-{self.batch.batch_id if self.batch else 'unknown'}.txt"
        report_file.write_text(report)

        self.stdout.write(f"Report saved to: {report_file}")


# Create alias for backwards compatibility
Command = OptimizedBatchProcessor
