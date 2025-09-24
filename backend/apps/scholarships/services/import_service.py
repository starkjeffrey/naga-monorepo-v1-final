"""Scholarship Import Service for converting receipt data into scholarship records.

This service processes legacy receipt data and creates Scholarship model records
with proper student mapping, cycle determination, and amount calculations.
Designed to maintain financial accuracy for receipt reconciliation.
"""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.curriculum.models import Cycle, Term
from apps.finance.management.commands.smart_batch_processor import Command as BatchProcessor
from apps.people.models import StudentProfile
from apps.scholarships.models import Scholarship

if TYPE_CHECKING:
    from datetime import date

logger = logging.getLogger(__name__)


@dataclass
class ImportResult:
    """Container for import operation results."""

    successful_imports: int = 0
    failed_imports: int = 0
    skipped_records: int = 0
    created_scholarships: list[Scholarship] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)
    warnings: list[dict] = field(default_factory=list)

    def add_success(self, scholarship: Scholarship | None = None):
        """Record successful scholarship creation."""
        self.successful_imports += 1
        if scholarship is not None:
            self.created_scholarships.append(scholarship)

    def add_error(self, receipt_data: dict, error_message: str, error_category: str = "GENERAL"):
        """Record import error."""
        self.failed_imports += 1
        self.errors.append(
            {
                "receipt_number": receipt_data.get("ReceiptNo", "N/A"),
                "student_id": receipt_data.get("IPK", "N/A"),
                "error_message": error_message,
                "error_category": error_category,
                "receipt_data": {
                    k: v for k, v in receipt_data.items() if k in ["ReceiptNo", "IPK", "Amount", "NetAmount", "Notes"]
                },
            }
        )

    def add_warning(self, receipt_data: dict, warning_message: str):
        """Record import warning."""
        self.warnings.append(
            {
                "receipt_number": receipt_data.get("ReceiptNo", "N/A"),
                "student_id": receipt_data.get("IPK", "N/A"),
                "warning_message": warning_message,
            }
        )

    def add_skip(self):
        """Record skipped record."""
        self.skipped_records += 1


class ScholarshipImportService:
    """Service for importing scholarship records from receipt data."""

    def __init__(self):
        self.batch_processor = BatchProcessor()
        self.student_cache = {}
        self.cycle_cache = {}

    def import_scholarships_from_receipts(
        self, csv_file_path: str, batch_id: str | None = None, dry_run: bool = False
    ) -> ImportResult:
        """Import scholarships from receipt CSV data.

        Args:
            csv_file_path: Path to the receipt CSV file
            batch_id: Optional batch identifier for tracking
            dry_run: If True, validate but don't create records

        Returns:
            ImportResult with success/failure statistics
        """

        if batch_id is None:
            batch_id = f"SCHOLARSHIP_IMPORT_{timezone.now().strftime('%Y%m%d_%H%M%S')}"

        logger.info(f"Starting scholarship import from {csv_file_path} (batch: {batch_id}, dry_run: {dry_run})")

        # Initialize result tracking
        result = ImportResult()

        try:
            # Load receipt data
            receipt_data = self._load_receipt_data(csv_file_path)
            logger.info(f"Loaded {len(receipt_data)} receipt records")

            # Filter scholarship-eligible records
            scholarship_receipts = self._filter_scholarship_receipts(receipt_data)
            logger.info(f"Found {len(scholarship_receipts)} potential scholarship records")

            # Process each scholarship record
            with transaction.atomic():
                for i, receipt in enumerate(scholarship_receipts, 1):
                    try:
                        if dry_run:
                            # Validate without creating
                            self._validate_scholarship_data(receipt)
                            result.add_success(None)  # Count validation success
                        else:
                            scholarship = self._create_scholarship_from_receipt(receipt, batch_id)
                            result.add_success(scholarship)

                        # Progress logging
                        if i % 100 == 0:
                            logger.info(f"Processed {i}/{len(scholarship_receipts)} records")

                    except Exception as e:
                        logger.error(f"Error processing receipt {receipt.get('ReceiptNo', 'N/A')}: {e!s}")
                        error_category = self._categorize_error(e)
                        result.add_error(receipt, str(e), error_category)

                if dry_run:
                    # Rollback transaction in dry run mode
                    transaction.set_rollback(True)
                    logger.info("Dry run completed - no changes committed")

        except Exception as e:
            logger.error(f"Critical error during import: {e!s}")
            result.add_error({}, f"Critical import error: {e!s}", "CRITICAL")

        logger.info(
            f"Import completed: {result.successful_imports} success, "
            f"{result.failed_imports} failed, {result.skipped_records} skipped"
        )

        return result

    def _load_receipt_data(self, csv_file_path: str) -> list[dict]:
        """Load receipt data from CSV file."""
        receipt_data = []

        csv_path = Path(csv_file_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"Receipt CSV file not found: {csv_file_path}")

        with open(csv_path, encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)

            for row_num, row in enumerate(reader, start=2):
                # Skip deleted records
                if row.get("Deleted") == "1":
                    continue

                # Skip empty rows
                if not any(row.values()) or not row.get("ID"):
                    continue

                # Clean data
                cleaned_row = {k: v.strip() if v else "" for k, v in row.items()}
                cleaned_row["_row_number"] = row_num
                receipt_data.append(cleaned_row)

        return receipt_data

    def _filter_scholarship_receipts(self, receipts: list[dict]) -> list[dict]:
        """Filter receipts that contain scholarship indicators."""
        scholarship_receipts = []

        for receipt in receipts:
            net_amount = self.batch_processor._safe_decimal(receipt.get("NetAmount", "0"))

            # Use existing scholarship detection logic
            if self.batch_processor._detect_scholarship_payment(receipt, net_amount):
                scholarship_receipts.append(receipt)

        return scholarship_receipts

    def _validate_scholarship_data(self, receipt: dict) -> None:
        """Validate scholarship data without creating record."""
        # Validate student mapping
        student = self._map_student(receipt["ID"])

        # Validate cycle determination
        cycle = self._determine_cycle(student, receipt)

        # Validate amount calculation
        award_data = self._calculate_award_amount(receipt)

        # Validate date range
        start_date, end_date = self._determine_date_range(receipt)

        # Check for duplicates
        self._check_duplicate_scholarship(student, cycle, start_date, award_data)

    def _create_scholarship_from_receipt(self, receipt: dict, batch_id: str) -> Scholarship:
        """Create Scholarship record from receipt data."""

        # Map student
        student = self._map_student(receipt["ID"])

        # Determine cycle
        cycle = self._determine_cycle(student, receipt)

        # Calculate scholarship amount/percentage
        award_data = self._calculate_award_amount(receipt)

        # Generate scholarship details
        name = self._generate_scholarship_name(receipt)
        start_date, end_date = self._determine_date_range(receipt)

        # Check for duplicates
        existing = self._check_duplicate_scholarship(student, cycle, start_date, award_data)
        if existing:
            raise ValidationError(f"Duplicate scholarship exists: {existing}")

        # Create scholarship record
        scholarship = Scholarship.objects.create(
            student=student,
            cycle=cycle,
            name=name,
            scholarship_type=Scholarship.ScholarshipType.SPONSORED,
            status=Scholarship.AwardStatus.ACTIVE,
            start_date=start_date,
            end_date=end_date,
            description=f"Imported from receipt {receipt.get('ReceiptNo', 'N/A')} (batch: {batch_id})",
            notes=receipt.get("Notes", "")[:500],  # Truncate if needed
            **award_data,  # award_percentage OR award_amount
        )

        logger.debug(f"Created scholarship: {scholarship} for student {student}")
        return scholarship

    def _map_student(self, student_id: str) -> StudentProfile:
        """Map legacy student ID to StudentProfile with caching.

        Legacy receipt data uses zero-padded strings (e.g., "00001")
        which need to be converted to integers for student_id lookup.
        """
        if student_id in self.student_cache:
            return self.student_cache[student_id]

        try:
            if student_id.isdigit():
                # Convert zero-padded string to integer: "00001" -> 1
                numeric_id = int(student_id)
                student = StudentProfile.objects.select_related("person").get(student_id=numeric_id)
            else:
                raise ObjectDoesNotExist(f"Non-numeric student ID not supported: {student_id}")

            self.student_cache[student_id] = student
            return student

        except ObjectDoesNotExist as err:
            raise ValidationError(
                f"Student not found for student_id: {int(student_id) if student_id.isdigit() else student_id}"
            ) from err

    def _determine_cycle(self, student: StudentProfile, receipt: dict) -> Cycle | None:
        """Determine appropriate cycle from receipt program field.

        Program field mapping:
        - Program 147 → Cycle 3 (Master's Program)
        - Program 87 → Cycle 2 (Bachelor's Program)

        TermID is used only for date determination, not cycle.
        """
        program = receipt.get("Program")

        if program:
            try:
                # Convert to string for comparison (may be stored as different types)
                program_str = str(program).strip()

                if program_str == "147":
                    cycle = Cycle.objects.get(id=3)  # Master's Program
                    logger.debug(f"Program {program_str} mapped to cycle {cycle.name}")
                    return cycle
                elif program_str == "87":
                    cycle = Cycle.objects.get(id=2)  # Bachelor's Program
                    logger.debug(f"Program {program_str} mapped to cycle {cycle.name}")
                    return cycle
                else:
                    # For other programs, we don't have a specific mapping
                    # Could potentially add more mappings if needed
                    logger.debug(f"No cycle mapping defined for program {program_str}")

            except Cycle.DoesNotExist:
                logger.warning("Cycle not found - check cycle IDs in database")
            except Exception as e:
                logger.warning(f"Error processing program field '{program}': {e}")

        # If no program or unrecognized program, return None
        logger.debug(f"Could not determine cycle for student {student} with program {program}")
        return None

    def _calculate_award_amount(self, receipt: dict) -> dict:
        """Calculate scholarship award amount or percentage from receipt data."""

        amount = self.batch_processor._safe_decimal(receipt.get("Amount", "0"))
        net_amount = self.batch_processor._safe_decimal(receipt.get("NetAmount", "0"))
        net_discount = self.batch_processor._safe_decimal(receipt.get("NetDiscount", "0"))

        # Calculate discount amount
        if net_discount > 0:
            discount_amount = net_discount
        else:
            discount_amount = amount - net_amount

        if discount_amount <= 0:
            raise ValidationError(f"Invalid discount amount calculated: {discount_amount}")

        # Determine if this should be percentage or fixed amount
        if amount > 0:
            percentage = (discount_amount / amount * 100).quantize(Decimal("0.01"))

            # Use percentage if it's a round number, otherwise use fixed amount
            if percentage in [Decimal("25"), Decimal("50"), Decimal("75"), Decimal("100")] or percentage % 5 == 0:
                return {"award_percentage": percentage}
            else:
                return {"award_amount": discount_amount}
        else:
            # If no original amount, use fixed amount
            return {"award_amount": discount_amount}

    def _generate_scholarship_name(self, receipt: dict) -> str:
        """Generate appropriate scholarship name from receipt context."""

        notes = receipt.get("Notes", "").lower()
        receipt_no = receipt.get("ReceiptNo", "N/A")

        # Extract scholarship context from notes
        if "foundation" in notes:
            return f"Foundation Scholarship (Receipt {receipt_no})"
        elif "ngo" in notes:
            return f"NGO Sponsored Scholarship (Receipt {receipt_no})"
        elif "sponsor" in notes:
            return f"Sponsored Student Scholarship (Receipt {receipt_no})"
        elif "grant" in notes:
            return f"Grant Award (Receipt {receipt_no})"
        elif any(word in notes for word in ["100%", "full"]):
            return f"Full Scholarship (Receipt {receipt_no})"
        else:
            return f"Legacy Scholarship (Receipt {receipt_no})"

    def _determine_date_range(self, receipt: dict) -> tuple[date, date | None]:
        """Determine scholarship start and end dates from receipt context."""

        # Try to get dates from term if available
        term_id = receipt.get("TermID")
        if term_id:
            try:
                # Legacy receipt data contains term codes (like "2009T3T3E"), not numeric IDs
                # Look up term by code, not by ID
                term = Term.objects.get(code=term_id)
                return term.start_date, term.end_date
            except ObjectDoesNotExist:
                pass

        # Fallback to receipt date if available
        receipt_date_str = receipt.get("Date")
        if receipt_date_str:
            try:
                # Parse receipt date (format may vary)
                from datetime import datetime

                receipt_date = datetime.strptime(receipt_date_str, "%Y-%m-%d").date()
                # Set end date to end of academic year (approximate)
                end_date = receipt_date.replace(month=12, day=31)
                return receipt_date, end_date
            except (ValueError, AttributeError):
                pass

        # Final fallback - use current date
        today = timezone.now().date()
        logger.warning(f"Using current date as scholarship start date for receipt {receipt.get('ReceiptNo', 'N/A')}")
        return today, None

    def _check_duplicate_scholarship(
        self, student: StudentProfile, cycle: Cycle | None, start_date: date, award_data: dict
    ) -> Scholarship | None:
        """Check for existing scholarship that might be a duplicate."""

        existing_scholarships = Scholarship.objects.filter(
            student=student,
            cycle=cycle,
            start_date=start_date,
            status__in=[Scholarship.AwardStatus.APPROVED, Scholarship.AwardStatus.ACTIVE],
        )

        # Check for exact matches
        for scholarship in existing_scholarships:
            if "award_percentage" in award_data and scholarship.award_percentage == award_data["award_percentage"]:
                return scholarship
            if "award_amount" in award_data and scholarship.award_amount == award_data["award_amount"]:
                return scholarship

        return None

    def _categorize_error(self, exception: Exception) -> str:
        """Categorize error for reporting purposes."""

        if isinstance(exception, ObjectDoesNotExist):
            return "STUDENT_NOT_FOUND"
        elif isinstance(exception, ValidationError):
            if "duplicate" in str(exception).lower():
                return "DUPLICATE_SCHOLARSHIP"
            elif "amount" in str(exception).lower():
                return "INVALID_AMOUNT"
            else:
                return "VALIDATION_ERROR"
        else:
            return "PROCESSING_ERROR"
