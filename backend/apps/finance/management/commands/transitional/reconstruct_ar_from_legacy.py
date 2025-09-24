"""A/R Reconstruction management command for legacy financial data processing."""

import csv
import re
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.common.management.base_migration import BaseMigrationCommand
from apps.curriculum.models import Term
from apps.enrollment.models import ClassHeaderEnrollment
from apps.finance.models import (
    ARReconstructionBatch,
    ClerkIdentification,
    DiscountRule,
    Invoice,
    InvoiceLineItem,
    LegacyReceiptMapping,
    Payment,
)
from apps.people.models import StudentProfile

from .process_receipt_notes import NotesProcessor


class Command(BaseMigrationCommand):
    """Reconstruct A/R records from legacy receipt_headers data."""

    help = "Reconstruct A/R records from legacy receipt_headers with comprehensive audit trail"

    def execute_migration(self, *args: Any, **options: Any) -> Any:
        """Execute the actual migration work."""
        return self.handle(*args, **options)

    def get_rejection_categories(self) -> dict[str, str]:
        """Return rejection categories for failed reconstructions."""
        return {
            "STUDENT_NOT_FOUND": "Student record not found in current system",
            "TERM_NOT_FOUND": "Term record not found in current system",
            "INVALID_RECEIPT_DATA": "Receipt data validation failed",
            "ENROLLMENT_MISMATCH": "Could not match receipt to enrollments",
            "HIGH_VARIANCE": "Theoretical vs actual amount variance too high",
            "PROCESSING_ERROR": "Generic processing error occurred",
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.batch: ARReconstructionBatch  # Will be initialized in _initialize_processing
        self.discount_rules: dict[str, DiscountRule] = {}
        self.clerk_cache: dict[str, ClerkIdentification] = {}
        self.student_cache: dict[str, StudentProfile] = {}
        self.term_cache: dict[str, Term] = {}
        self.notes_processor = NotesProcessor()

    def add_arguments(self, parser: Any) -> None:
        """Add command line arguments."""
        super().add_arguments(parser)

        # Processing control
        parser.add_argument("--term", type=str, help="Process specific term (e.g., 251027E-T3BE)")

        parser.add_argument(
            "--mode",
            choices=["supervised", "automated", "reprocessing"],
            default="supervised",
            help="Processing mode (default: supervised)",
        )

        parser.add_argument(
            "--batch-id",
            type=str,
            help="Custom batch ID (auto-generated if not provided)",
        )

        # Data source
        parser.add_argument(
            "--receipt-file",
            type=str,
            default="data/legacy/all_receipt_headers_250723.csv",
            help="Path to receipt_headers CSV file",
        )

        # Processing limits
        parser.add_argument(
            "--limit",
            type=int,
            help="Limit number of receipts to process (for testing)",
        )

        parser.add_argument("--offset", type=int, default=0, help="Skip first N receipts (for resuming)")

        # Quality control
        parser.add_argument(
            "--confidence-threshold",
            type=float,
            default=80.0,
            help="Minimum confidence threshold for automatic processing",
        )

        parser.add_argument(
            "--max-variance",
            type=float,
            default=5.0,
            help="Maximum allowed variance percentage",
        )

        # Output control
        parser.add_argument(
            "--pause-on-variance",
            action="store_true",
            help="Pause processing when variance exceeds threshold",
        )

        parser.add_argument(
            "--report-interval",
            type=int,
            default=100,
            help="Report progress every N records",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Main command handler."""
        try:
            # Initialize processing
            self._initialize_processing(options)

            # Load receipt data
            receipt_data = self._load_receipt_data(options["receipt_file"])

            # Filter by term if specified
            if options["term"]:
                receipt_data = [r for r in receipt_data if r["TermID"] == options["term"]]
                self.batch.term_id = options["term"]
                self.batch.save()

            # Apply offset and limit
            if options["offset"]:
                receipt_data = receipt_data[options["offset"] :]
            if options["limit"]:
                receipt_data = receipt_data[: options["limit"]]

            # Update batch totals
            self.batch.total_receipts = len(receipt_data)
            self.batch.started_at = timezone.now()
            self.batch.status = ARReconstructionBatch.BatchStatus.PROCESSING
            self.batch.save()

            self.stdout.write(f"Processing {len(receipt_data)} receipts in {self.batch.processing_mode} mode")

            # Process receipts
            self._process_receipts(receipt_data, options)

            # Finalize batch
            self._finalize_batch()

            # Generate final report
            self._generate_final_report()

        except Exception as e:
            if self.batch:
                self.batch.status = ARReconstructionBatch.BatchStatus.FAILED
                self.batch.processing_log += f"\nFATAL ERROR: {e!s}"
                self.batch.save()
            self.stdout.write(self.style.ERROR(f"A/R reconstruction failed: {e!s}"))
            raise

    def _initialize_processing(self, options: dict[str, Any]) -> None:
        """Initialize processing batch and load rules."""
        # Create batch
        batch_id = options["batch_id"] or f"AR-{timezone.now().strftime('%Y%m%d-%H%M%S')}"

        self.batch = ARReconstructionBatch.objects.create(
            batch_id=batch_id,
            term_id=options.get("term", "MULTI"),
            processing_mode=options["mode"].upper(),
            processing_parameters={
                "confidence_threshold": options["confidence_threshold"],
                "max_variance": options["max_variance"],
                "pause_on_variance": options["pause_on_variance"],
                "report_interval": options["report_interval"],
            },
        )

        # Pre-load students and terms into memory for fast lookups
        self.stdout.write("Caching students and terms for performance...")

        # Load all students with their person data in a single query
        self.student_cache = {}
        for student in StudentProfile.objects.select_related("person").all():
            # Store by both string and int versions of the ID for flexibility
            self.student_cache[str(student.student_id)] = student
            self.student_cache[str(student.student_id).zfill(5)] = student

        # Load all terms into memory
        self.term_cache = {term.code: term for term in Term.objects.all()}

        self.stdout.write(f"Cached {len(StudentProfile.objects.all())} students and {len(self.term_cache)} terms.")

        self.stdout.write(f"Created reconstruction batch: {batch_id}")

        # Load existing discount rules
        self._load_discount_rules()

        # Load clerk identification cache
        self._load_clerk_cache()

    def _load_receipt_data(self, file_path: str) -> list[dict[str, Any]]:
        """Load receipt_headers CSV data, excluding deleted records."""
        receipts = []
        deleted_count = 0
        csv_path = Path(file_path)

        if not csv_path.exists():
            raise FileNotFoundError(f"Receipt file not found: {file_path}")

        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Skip deleted records (Deleted=1)
                if row.get("Deleted", "0").strip() == "1":
                    deleted_count += 1
                    continue

                # Skip invalid rows
                if not row.get("ID") or not row.get("ReceiptNo"):
                    continue
                receipts.append(row)

        self.stdout.write(f"Loaded {len(receipts)} valid receipt records from {file_path}")
        self.stdout.write(f"Excluded {deleted_count} deleted records (Deleted=1)")
        return receipts

    def _load_discount_rules(self) -> None:
        """Load existing discount rules into cache."""
        rules = DiscountRule.objects.filter(is_active=True)
        for rule in rules:
            self.discount_rules[rule.pattern_text.lower()] = rule
        self.stdout.write(f"Loaded {len(self.discount_rules)} discount rules")

    def _load_clerk_cache(self) -> None:
        """Load clerk identification cache."""
        clerks = ClerkIdentification.objects.all()
        for clerk in clerks:
            self.clerk_cache[clerk.receipt_id_pattern] = clerk
        self.stdout.write(f"Loaded {len(self.clerk_cache)} clerk identifications")

    def _process_receipts(self, receipt_data: list[dict[str, Any]], options: dict[str, Any]) -> None:
        """Process all receipts in the batch."""
        for i, receipt_row in enumerate(receipt_data, 1):
            try:
                with transaction.atomic():
                    # Process single receipt
                    result = self._process_single_receipt(receipt_row, options)

                    # Update batch statistics
                    self.batch.processed_receipts += 1
                    if result["success"]:
                        self.batch.successful_reconstructions += 1
                    else:
                        self.batch.failed_reconstructions += 1

                    if result.get("needs_review"):
                        self.batch.pending_review_count += 1

                    # Report progress
                    if i % options["report_interval"] == 0:
                        self._report_progress(i, len(receipt_data))

                    # Pause on variance if requested
                    if options["pause_on_variance"] and result.get("high_variance"):
                        self._pause_for_review(receipt_row, result)

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Failed to process receipt {receipt_row.get('ReceiptNo', 'UNKNOWN')}: {e!s}")
                )
                self.batch.failed_reconstructions += 1
                continue

            # Save batch progress periodically
            if i % (options["report_interval"] * 5) == 0:
                self.batch.save()

    def _process_single_receipt(self, receipt_row: dict[str, Any], options: dict[str, Any]) -> dict[str, Any]:
        """Process a single receipt record."""
        result = {
            "success": False,
            "needs_review": False,
            "high_variance": False,
            "variance_amount": Decimal("0"),
        }

        try:
            # Extract receipt data
            receipt_data = self._extract_receipt_data(receipt_row)

            # Find or create student
            student = self._find_student(receipt_data["student_id"])
            if not student:
                result["error"] = f"Student not found: {receipt_data['student_id']}"
                return result

            # Find term
            term = self._find_term(receipt_data["term_id"])
            if not term:
                result["error"] = f"Term not found: {receipt_data['term_id']}"
                return result

            # Find enrollments for this student/term
            enrollments = self._find_enrollments(student, term, receipt_data)

            # Calculate theoretical invoice
            theoretical_invoice = self._calculate_theoretical_invoice(student, term, enrollments, receipt_data)

            # Analyze variance
            variance = self._analyze_variance(theoretical_invoice, receipt_data)
            result.update(variance)

            # Apply discount rules
            discount_analysis = self._analyze_discounts(receipt_data, theoretical_invoice)

            # Create invoice and payment records
            invoice = self._create_invoice(student, term, receipt_data, theoretical_invoice, discount_analysis)

            payment = self._create_payment(invoice, receipt_data, discount_analysis)

            # Create line items
            self._create_line_items(
                invoice,
                enrollments,
                receipt_data,
                theoretical_invoice,
                discount_analysis,
            )

            # Create mapping record
            self._create_mapping_record(receipt_data, invoice, payment, variance)

            # Extract and store clerk information
            self._process_clerk_information(receipt_data)

            result["success"] = True
            result["invoice_id"] = getattr(invoice, "pk", None)
            result["payment_id"] = getattr(payment, "pk", None)

        except Exception as e:
            result["error"] = str(e)
            self.stdout.write(self.style.ERROR(f"Receipt processing error: {e!s}"))

        return result

    def _extract_receipt_data(self, row: dict[str, Any]) -> dict[str, Any]:
        """Extract and clean receipt data from CSV row."""
        return {
            "student_id": row["ID"].strip().zfill(5),
            "term_id": row["TermID"].strip() if row["TermID"] else None,
            "program_code": row["Program"].strip() if row["Program"] else None,
            "receipt_number": row["ReceiptNo"].strip() if row["ReceiptNo"] else None,
            "receipt_id": row["ReceiptID"].strip() if row["ReceiptID"] else None,
            "payment_date": self._parse_date(row["PmtDate"]),
            "amount": self._parse_decimal(row["Amount"]),
            "net_amount": self._parse_decimal(row["NetAmount"]),
            "net_discount": self._parse_decimal(row["NetDiscount"]),
            "scholar_grant": self._parse_decimal(row["ScholarGrant"]),
            "late_fee": self._parse_decimal(row["LateFee"]),
            "prepaid_fee": self._parse_decimal(row["PrepaidFee"]),
            "notes": row["Notes"].strip() if row.get("Notes") else "",
            "student_name": row["name"].strip() if row.get("name") else "",
            "payment_type": row["PmtType"].strip() if row.get("PmtType") else "Cash",
            "gender": row["Gender"].strip() if row.get("Gender") else "",
            "current_level": row["CurLevel"].strip() if row.get("CurLevel") else "",
        }

    def _parse_date(self, date_str: str) -> datetime | None:
        """Parse date string from receipt data."""
        if not date_str or date_str == "NULL":
            return None
        try:
            return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S.%f")
        except (ValueError, TypeError):
            return None

    def _parse_decimal(self, value_str: str) -> Decimal:
        """Parse decimal value from string."""
        if not value_str or value_str == "NULL":
            return Decimal("0")
        try:
            return Decimal(str(value_str))
        except (ValueError, TypeError):
            return Decimal("0")

    def _find_student(self, student_id: str) -> StudentProfile | None:
        """Find student by legacy ID (5-digit student number) from cache."""
        # Clean the student ID
        student_id_clean = student_id.strip()

        # Try both the raw ID and zero-padded version
        student = self.student_cache.get(student_id_clean)
        if not student:
            student = self.student_cache.get(student_id_clean.zfill(5))

        if not student:
            self.stdout.write(self.style.WARNING(f"Student not found for ID: {student_id}"))

        return student

    def _find_term(self, term_id: str) -> Term | None:
        """Find term by legacy term ID from cache."""
        if not term_id:
            return None

        # Clean the term ID and look up in cache
        term_code = term_id.strip()
        term = self.term_cache.get(term_code)

        if not term:
            self.stdout.write(self.style.WARNING(f"Term not found for ID: {term_id}"))

        return term

    def _find_enrollments(
        self, student: StudentProfile, term: Term, receipt_data: dict[str, Any]
    ) -> list[ClassHeaderEnrollment]:
        """Find enrollments for student/term combination."""
        if not student or not term:
            return []

        # Query ClassHeaderEnrollment for this student and term
        enrollments = ClassHeaderEnrollment.objects.select_related(
            "class_header__course", "class_header__term"
        ).filter(student=student, class_header__term=term)

        return list(enrollments)

    def _calculate_theoretical_invoice(
        self,
        student: StudentProfile,
        term: Term,
        enrollments: list[ClassHeaderEnrollment],
        receipt_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Calculate what the invoice should theoretically be based on program code and cycle pricing."""

        # Map legacy program codes to current cycle IDs
        program_code_to_cycle = {
            "87": 2,  # BA → Cycle 2 (Bachelor's level, current pricing $75/$130)
            "147": 3,  # MA → Cycle 3 (Master's level, current pricing $185/$400)
            "582": 1,  # Language → Language Program (ID: 1)
            "632": 1,  # Language → Language Program (ID: 1)
            "688": 1,  # Language → Language Program (ID: 1)
            # Add other mappings as needed
        }

        program_code = str(receipt_data.get("program_code", "")).strip()
        cycle_id = program_code_to_cycle.get(program_code)

        if cycle_id:
            # Use actual pricing from our clean data
            confidence = "HIGH"
            if cycle_id == 2:  # BA pricing (Cycle 2)
                expected_base_amount = Decimal("75.00")  # Current BA pricing from fixtures
            elif cycle_id == 3:  # MA pricing (Cycle 3)
                expected_base_amount = Decimal("185.00")  # Current MA pricing from fixtures
            else:
                expected_base_amount = receipt_data["amount"]
                confidence = "MEDIUM"
        else:
            # Unknown program code, use receipt amount
            expected_base_amount = receipt_data["amount"]
            confidence = "LOW"

        # Calculate expected discount
        net_amount = receipt_data["net_amount"]
        discount_amount = expected_base_amount - net_amount

        return {
            "subtotal": expected_base_amount,
            "discount": discount_amount,
            "total": net_amount,
            "line_items": [],
            "confidence": confidence,
            "program_code": program_code,
            "cycle_id": cycle_id,
        }

    def _analyze_variance(self, theoretical: dict[str, Any], receipt_data: dict[str, Any]) -> dict[str, Any]:
        """Analyze variance between theoretical and actual amounts."""
        variance_amount = theoretical["total"] - receipt_data["net_amount"]
        variance_percentage = (
            abs(variance_amount) / receipt_data["net_amount"] * 100 if receipt_data["net_amount"] > 0 else 0
        )

        return {
            "variance_amount": variance_amount,
            "variance_percentage": variance_percentage,
            "high_variance": variance_percentage > 10.0,
            "needs_review": variance_percentage > 5.0,
        }

    def _analyze_discounts(self, receipt_data: dict[str, Any], theoretical: dict[str, Any]) -> dict[str, Any]:
        """Analyze discount patterns from notes field."""
        notes = receipt_data["notes"].lower()
        matched_rules = []

        for pattern, rule in self.discount_rules.items():
            if pattern in notes:
                matched_rules.append(rule)

        return {
            "matched_rules": matched_rules,
            "notes_analysis": notes,
            "discount_applied": receipt_data["net_discount"],
        }

    def _create_invoice(self, student, term, receipt_data, theoretical, discount_analysis) -> Invoice:
        """Create invoice record with legacy data preservation."""
        import hashlib
        from datetime import datetime

        from django.db import IntegrityError

        # Generate base invoice number from receipt
        base_invoice_number = f"AR-{receipt_data['receipt_number']}"
        invoice_number = base_invoice_number

        # Handle duplicate invoice numbers by adding hash suffix
        attempt = 0
        while True:
            try:
                # Create the invoice
                invoice = Invoice.objects.create(
                    student=student,
                    term=term,
                    invoice_number=invoice_number,
                    issue_date=(
                        receipt_data["payment_date"].date() if receipt_data["payment_date"] else datetime.now().date()
                    ),
                    due_date=(
                        receipt_data["payment_date"].date() if receipt_data["payment_date"] else datetime.now().date()
                    )
                    + timedelta(days=1),
                    subtotal=receipt_data["amount"],
                    tax_amount=Decimal("0"),  # No tax in legacy data
                    total_amount=receipt_data["net_amount"],
                    paid_amount=Decimal("0.00"),  # Will be updated by payment signal
                    currency="USD",
                    status="SENT",  # Will be updated to PAID by payment signal
                    version=1,  # Set version field for new invoices
                    # Legacy data preservation
                    is_historical=True,
                    legacy_receipt_number=receipt_data["receipt_number"],
                    legacy_receipt_id=receipt_data["receipt_id"],
                    legacy_notes=receipt_data["notes"],
                    legacy_processing_clerk=self._extract_clerk_name(receipt_data["receipt_id"]),
                    original_amount=receipt_data["amount"],
                    discount_applied=receipt_data["net_discount"],
                    reconstruction_status="RECONSTRUCTED",
                    needs_reprocessing=False,  # Set default value for needs_reprocessing
                    reprocessing_reason="",  # Set default value for reprocessing_reason
                    reconstruction_batch=self.batch,
                )
                break  # Success, exit the loop
            except IntegrityError as e:
                if "invoice_number" in str(e):
                    attempt += 1
                    # Create hash from receipt ID to ensure uniqueness
                    hash_suffix = hashlib.sha256(f"{receipt_data['receipt_id']}-{attempt}".encode()).hexdigest()[:6]
                    invoice_number = f"{base_invoice_number}-{hash_suffix}"
                else:
                    raise

        return invoice

    def _create_payment(self, invoice, receipt_data, discount_analysis) -> Payment:
        """Create payment record with legacy data preservation."""
        import hashlib
        from datetime import datetime

        # Get or create a system user for processed_by (required field)
        from django.contrib.auth import get_user_model
        from django.db import IntegrityError

        User = get_user_model()

        try:
            # Try to get the first staff user or create a system user
            system_user = User.objects.filter(is_staff=True).first()
            if not system_user:
                # Create a system user for historical payments
                from typing import Any
                system_user = (User.objects if hasattr(User, "objects") else User._default_manager)
                system_user = getattr(system_user, "create_user")(
                    username="ar_reconstruction_system",
                    email="system@ar-reconstruction.local",
                    first_name="A/R",
                    last_name="Reconstruction System",
                    is_staff=True,
                )
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Could not create system user: {e}"))
            system_user = None

        # Generate base payment reference
        base_payment_reference = receipt_data["receipt_number"]
        payment_reference = base_payment_reference

        # Handle duplicate payment references by adding hash suffix
        attempt = 0
        while True:
            try:
                # Create the payment record
                payment = Payment.objects.create(
                    invoice=invoice,
                    payment_reference=payment_reference,
                    amount=receipt_data["net_amount"],
                    payment_date=(
                        receipt_data["payment_date"].date() if receipt_data["payment_date"] else datetime.now().date()
                    ),
                    processed_date=(receipt_data["payment_date"] if receipt_data["payment_date"] else datetime.now()),
                    payment_method=receipt_data.get("payment_type", "CASH").upper()[:20],
                    status="COMPLETED",  # Historical payments are completed
                    currency="USD",
                    payer_name=receipt_data.get("student_name", invoice.student.person.full_name),
                    external_reference=receipt_data["receipt_id"],
                    processed_by=system_user,
                    # Legacy data preservation
                    is_historical_payment=True,
                    legacy_receipt_reference=receipt_data["receipt_number"],
                    legacy_processing_clerk=self._extract_clerk_name(receipt_data["receipt_id"]),
                    legacy_business_notes=receipt_data["notes"],
                    legacy_receipt_full_id=receipt_data["receipt_id"],
                    legacy_program_code=receipt_data["program_code"],
                )
                break  # Success, exit the loop
            except IntegrityError as e:
                if "payment_reference" in str(e) or "external_reference" in str(e):
                    attempt += 1
                    # Create hash from receipt ID to ensure uniqueness
                    hash_suffix = hashlib.sha256(f"{receipt_data['receipt_id']}-{attempt}".encode()).hexdigest()[:6]
                    payment_reference = f"{base_payment_reference}-{hash_suffix}"
                else:
                    raise

        return payment

    def _create_line_items(self, invoice, enrollments, receipt_data, theoretical, discount_analysis):
        """Create invoice line items."""

        # If we have enrollment data, create line items for each enrollment
        if enrollments:
            for enrollment in enrollments:
                # Calculate per-course amount (distribute total across enrollments)
                line_amount = receipt_data["amount"] / len(enrollments)
                line_discount = (
                    receipt_data["net_discount"] / len(enrollments)
                    if receipt_data["net_discount"] > 0
                    else Decimal("0")
                )

                InvoiceLineItem.objects.create(
                    invoice=invoice,
                    description=(
                        f"Course: {enrollment.class_header.course.code} - {enrollment.class_header.course.title}"
                    ),
                    quantity=1,
                    unit_price=line_amount,
                    line_total=line_amount - line_discount,
                    # Legacy data preservation
                    legacy_program_code=receipt_data["program_code"],
                    legacy_course_level=receipt_data["current_level"],
                    pricing_method_used="UNKNOWN_LEGACY",
                    pricing_confidence="MEDIUM",
                    base_amount=line_amount,
                    discount_amount=line_discount,
                    discount_reason=(receipt_data["notes"] if receipt_data["notes"] else ""),
                )
        else:
            # Create a single line item for the total amount if no enrollments found
            InvoiceLineItem.objects.create(
                invoice=invoice,
                description=f"Legacy Payment - Program: {receipt_data['program_code']}",
                quantity=1,
                unit_price=receipt_data["amount"],
                line_total=receipt_data["net_amount"],
                # Legacy data preservation
                legacy_program_code=receipt_data["program_code"],
                legacy_course_level=receipt_data["current_level"],
                pricing_method_used="UNKNOWN_LEGACY",
                pricing_confidence="LOW",
                base_amount=receipt_data["amount"],
                discount_amount=receipt_data["net_discount"],
                discount_reason=receipt_data["notes"] if receipt_data["notes"] else "",
            )

    def _create_mapping_record(self, receipt_data, invoice, payment, variance):
        """Create legacy receipt mapping record with notes processing."""

        # Process the notes
        original_notes = receipt_data.get("notes", "")
        processed_note = self.notes_processor.process_note(original_notes)

        # Determine validation status based on variance
        if variance["high_variance"]:
            validation_status = "PENDING"
        elif variance["needs_review"]:
            validation_status = "PENDING"
        else:
            validation_status = "VALIDATED"

        # Create the mapping record for audit trail
        LegacyReceiptMapping.objects.create(
            legacy_receipt_number=receipt_data["receipt_number"],
            legacy_receipt_id=receipt_data["receipt_id"],
            legacy_student_id=receipt_data["student_id"],
            legacy_term_id=receipt_data["term_id"],
            # Financial amounts
            legacy_amount=receipt_data["amount"],
            legacy_net_amount=receipt_data["net_amount"],
            legacy_discount=receipt_data["net_discount"],
            reconstructed_total=invoice.total_amount,
            variance_amount=variance["variance_amount"],
            # Original and processed notes
            legacy_notes=original_notes,
            parsed_note_type=processed_note.note_type.value,
            parsed_amount_adjustment=processed_note.amount_adjustment,
            parsed_percentage_adjustment=processed_note.percentage_adjustment,
            parsed_authority=processed_note.authority,
            parsed_reason=processed_note.reason,
            notes_processing_confidence=processed_note.confidence,
            ar_transaction_mapping=processed_note.ar_transaction_mapping,
            normalized_note=self.notes_processor.create_normalized_note(processed_note),
            # Links to reconstructed records
            generated_invoice=invoice,
            generated_payment=payment,
            reconstruction_batch=self.batch,
            # Validation status
            validation_status=validation_status,
            validation_notes=(
                f"Variance: {variance['variance_percentage']:.2f}%" if variance["variance_percentage"] > 0 else ""
            ),
        )

    def _process_clerk_information(self, receipt_data):
        """Extract and process clerk information from ReceiptID."""
        receipt_id = receipt_data["receipt_id"]
        if not receipt_id:
            return

        # Extract clerk name from ReceiptID pattern
        clerk_info = self._extract_clerk_from_receipt_id(receipt_id)
        if clerk_info:
            # Store or update clerk identification
            self._store_clerk_identification(clerk_info, receipt_data)

    def _extract_clerk_from_receipt_id(self, receipt_id: str) -> dict | None:
        """Extract clerk information from ReceiptID pattern."""
        # Pattern: DESKTOP-GGBG2OR-DELL-SEREIROTH-29681-7192025-9341
        # Or: SRENROLLMENT1-ENROLLMENT1-ROATH-[numbers]-[date]-[time]

        patterns = [
            # Modern pattern: DESKTOP-[computer]-[program]-[clerk]-[numbers]-[date]-[time]
            r"DESKTOP-([^-]+)-([^-]+)-([^-]+)-",
            # Legacy pattern: SRENROLLMENT1-ENROLLMENT1-[clerk]-
            r"SRENROLLMENT1-ENROLLMENT1-([^-]+)-",
        ]

        for pattern in patterns:
            match = re.search(pattern, receipt_id)
            if match:
                groups = match.groups()
                if len(groups) >= 3:  # Modern pattern
                    return {
                        "computer_identifier": groups[0],
                        "program": groups[1],
                        "clerk_name": groups[2],
                        "pattern": receipt_id,
                        "confidence": "HIGH",
                    }
                elif len(groups) == 1:  # Legacy pattern
                    return {
                        "computer_identifier": "",
                        "program": "",
                        "clerk_name": groups[0],
                        "pattern": receipt_id,
                        "confidence": "MEDIUM",
                    }

        return None

    def _extract_clerk_name(self, receipt_id: str) -> str:
        """Extract clerk name from receipt ID for legacy data preservation."""
        if not receipt_id:
            return ""

        clerk_info = self._extract_clerk_from_receipt_id(receipt_id)
        if clerk_info:
            return clerk_info.get("clerk_name", "")
        return ""

    def _store_clerk_identification(self, clerk_info: dict, receipt_data: dict):
        """Store or update clerk identification."""
        # This would create/update ClerkIdentification record
        pass

    def _report_progress(self, current: int, total: int):
        """Report processing progress."""
        progress = (current / total) * 100
        success_rate = (self.batch.successful_reconstructions / max(current, 1)) * 100

        self.stdout.write(
            f"Progress: {current}/{total} ({progress:.1f}%) | "
            f"Success: {success_rate:.1f}% | "
            f"Pending Review: {self.batch.pending_review_count}"
        )

    def _pause_for_review(self, receipt_row: dict, result: dict):
        """Pause processing for manual review."""
        self.batch.status = ARReconstructionBatch.BatchStatus.PAUSED
        self.batch.save()

        self.stdout.write(
            self.style.WARNING(
                f"PAUSED: High variance detected in receipt {receipt_row.get('ReceiptNo')} "
                f"(${result['variance_amount']}, {result['variance_percentage']:.1f}%)"
            )
        )

        # In a real implementation, this would trigger notification
        # and wait for manual approval to continue

    def _finalize_batch(self):
        """Finalize the processing batch."""
        self.batch.completed_at = timezone.now()
        self.batch.status = ARReconstructionBatch.BatchStatus.COMPLETED

        # Calculate final statistics
        self.batch.variance_summary = {
            "success_rate": float(self.batch.success_rate),
            "total_processed": self.batch.processed_receipts,
            "successful": self.batch.successful_reconstructions,
            "failed": self.batch.failed_reconstructions,
            "pending_review": self.batch.pending_review_count,
        }

        self.batch.save()

        self.stdout.write(f"Batch {self.batch.batch_id} completed successfully")

    def _generate_final_report(self):
        """Generate comprehensive reconciliation report with detailed audit trail."""
        from pathlib import Path

        # Ensure reports directory exists
        reports_dir = Path("project-docs/migration-reports")
        reports_dir.mkdir(parents=True, exist_ok=True)

        report_path = reports_dir / f"ar-reconstruction-{self.batch.batch_id}.md"

        # Generate comprehensive report
        report_content = self._build_reconciliation_report()

        # Write report to file
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)

        # Also generate CSV summary for easy analysis
        csv_path = reports_dir / f"ar-reconstruction-{self.batch.batch_id}-summary.csv"
        self._generate_csv_summary(csv_path)

        self.stdout.write(f"📊 Comprehensive report generated: {report_path}")
        self.stdout.write(f"📈 CSV summary generated: {csv_path}")
        self.stdout.write(f"✅ Success rate: {self.batch.success_rate:.1f}%")
        self.stdout.write(f"⚠️  Records requiring review: {self.batch.pending_review_count}")

    def _build_reconciliation_report(self) -> str:
        """Build detailed reconciliation report content."""

        from apps.finance.models import Invoice, LegacyReceiptMapping, Payment
        from apps.people.models import StudentProfile

        # Collect comprehensive statistics
        successful_mappings = LegacyReceiptMapping.objects.filter(reconstruction_batch=self.batch)
        Invoice.objects.filter(reconstruction_batch=self.batch)
        Payment.objects.filter(invoice__reconstruction_batch=self.batch)

        # Financial totals
        total_legacy_amount = sum(m.legacy_amount for m in successful_mappings)
        total_reconstructed_amount = sum(m.reconstructed_total for m in successful_mappings)
        total_variance = total_legacy_amount - total_reconstructed_amount

        # Student analysis
        processed_students = set()
        missing_students = []

        # Analyze all receipts in this batch to identify missing students
        receipt_data = self._load_receipt_data("data/legacy/all_receipt_headers_250723.csv")
        if hasattr(self, "batch") and self.batch.term_id:
            receipt_data = [r for r in receipt_data if r["TermID"] == self.batch.term_id]

        for receipt in receipt_data[: self.batch.total_receipts]:
            student_id = receipt["ID"].strip().zfill(5)
            try:
                student = StudentProfile.objects.get(student_id=int(student_id))
                processed_students.add(student.student_id)
            except (ValueError, StudentProfile.DoesNotExist):
                missing_students.append(
                    {
                        "student_id": student_id,
                        "student_name": receipt.get("name", "Unknown"),
                        "receipt_number": receipt.get("ReceiptNo", "Unknown"),
                        "amount": receipt.get("NetAmount", "0"),
                        "term": receipt.get("TermID", "Unknown"),
                    }
                )

        # Build report content
        report = f"""# A/R Reconstruction Report
**Batch ID**: {self.batch.batch_id}
**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Processing Mode**: {self.batch.processing_mode}
**Term**: {self.batch.term_id or "Multiple Terms"}

## Executive Summary

| Metric | Count | Percentage |
|--------|-------|------------|
| **Total Receipts Processed** | {self.batch.processed_receipts:,} | 100.0% |
| **Successful Reconstructions** | {self.batch.successful_reconstructions:,} | {self.batch.success_rate:.1f}% |
| **Failed Reconstructions** | {self.batch.failed_reconstructions:,} | {100 - self.batch.success_rate:.1f}% |
| **Records Requiring Review** | {self.batch.pending_review_count:,} | {
            (self.batch.pending_review_count / max(self.batch.processed_receipts, 1) * 100):.1f
}% |

## Financial Reconciliation

| Financial Metric | Amount (USD) |
|------------------|--------------|
| **Total Legacy Amount** | ${total_legacy_amount:,.2f} |
| **Total Reconstructed Amount** | ${total_reconstructed_amount:,.2f} |
| **Net Variance** | ${total_variance:,.2f} |
| **Variance Percentage** | {(abs(total_variance) / max(total_legacy_amount, 1) * 100):.2f}% |

## Data Quality Analysis

### Students Analysis
- **Students Successfully Processed**: {len(processed_students):,}
- **Missing Students**: {len(missing_students):,}

"""

        # Add missing students details if any
        if missing_students:
            report += """
### Missing Students Detail
The following students from legacy receipts were not found in the current database:

| Student ID | Student Name | Receipt # | Amount | Term |
|------------|--------------|-----------|--------|------|
"""
            for student in missing_students[:50]:  # Limit to first 50 for readability
                report += (
                    f"| {student['student_id']} | {student['student_name']} | "
                    f"{student['receipt_number']} | ${student['amount']} | {student['term']} |\n"
                )

            if len(missing_students) > 50:
                report += (
                    f"\n*... and {len(missing_students) - 50} more missing students "
                    f"(see CSV file for complete list)*\n"
                )

        # Add successful reconstructions sample
        if successful_mappings.exists():
            report += """
## Sample Successful Reconstructions

| Receipt # | Student | Legacy Amount | Reconstructed | Variance | Status |
|-----------|---------|---------------|---------------|----------|--------|
"""
            for mapping in successful_mappings[:10]:
                variance = mapping.legacy_amount - mapping.reconstructed_total
                report += (
                    f"| {mapping.legacy_receipt_number} | {mapping.generated_invoice.student} | "
                    f"${mapping.legacy_amount:.2f} | ${mapping.reconstructed_total:.2f} | "
                    f"${variance:.2f} | {mapping.validation_status} |\n"
                )

        # Add processing parameters
        report += f"""
## Processing Configuration

```json
{self.batch.processing_parameters}
```

## System Information
- **Database**: PostgreSQL
- **Processing Time**: {(self.batch.completed_at - self.batch.started_at).total_seconds():.1f} seconds
- **Records per Second**: {
            self.batch.processed_receipts
            / max((self.batch.completed_at - self.batch.started_at).total_seconds(), 1):.1f
}

## Recommendations

"""

        # Add recommendations based on results
        recommendations = []

        if len(missing_students) > 0:
            recommendations.append(
                f"🔍 **Student Data**: {len(missing_students)} students need to be added to the "
                f"database before reprocessing"
            )

        if self.batch.success_rate < 80:
            recommendations.append(
                "⚠️ **Low Success Rate**: Review failed reconstructions and consider data quality improvements"
            )

        if abs(total_variance) > total_legacy_amount * Decimal("0.05"):
            recommendations.append("💰 **High Financial Variance**: Review pricing logic and discount calculations")

        if self.batch.pending_review_count > 0:
            recommendations.append(
                f"👀 **Manual Review**: {self.batch.pending_review_count} records require manual validation"
            )

        for i, rec in enumerate(recommendations, 1):
            report += f"{i}. {rec}\n"

        if not recommendations:
            report += "✅ **All Good**: No major issues detected in this reconstruction batch.\n"

        report += """
## Next Steps

1. **Review Missing Students**: Import missing student records or exclude from processing
2. **Validate Successful Reconstructions**: Spot-check invoices and payments in Django admin
3. **Process Next Batch**: Continue with next term or expand processing scope
4. **Archive Legacy Data**: Ensure legacy receipt data is properly archived

---
*Report generated by A/R Reconstruction System v1.0*
"""

        return report

    def _generate_csv_summary(self, csv_path):
        """Generate CSV summary for easy analysis in Excel/Google Sheets."""
        import csv

        from apps.finance.models import LegacyReceiptMapping

        successful_mappings = LegacyReceiptMapping.objects.filter(reconstruction_batch=self.batch)

        with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)

            # Header
            writer.writerow(
                [
                    "Receipt_Number",
                    "Student_ID",
                    "Student_Name",
                    "Term_ID",
                    "Legacy_Amount",
                    "Legacy_Net_Amount",
                    "Legacy_Discount",
                    "Reconstructed_Total",
                    "Variance_Amount",
                    "Variance_Percent",
                    "Validation_Status",
                    "Invoice_Number",
                    "Payment_Reference",
                    "Processing_Status",
                    "Notes",
                ]
            )

            # Data rows
            for mapping in successful_mappings:
                variance_percent = (abs(mapping.variance_amount) / max(mapping.legacy_amount, 1)) * 100

                writer.writerow(
                    [
                        mapping.legacy_receipt_number,
                        mapping.legacy_student_id,
                        mapping.generated_invoice.student.person.full_name,
                        mapping.legacy_term_id,
                        float(mapping.legacy_amount),
                        float(mapping.legacy_net_amount),
                        float(mapping.legacy_discount),
                        float(mapping.reconstructed_total),
                        float(mapping.variance_amount),
                        f"{variance_percent:.2f}%",
                        mapping.validation_status,
                        mapping.generated_invoice.invoice_number,
                        mapping.generated_payment.payment_reference,
                        "SUCCESS",
                        mapping.validation_notes,
                    ]
                )

        # Also create a separate CSV for missing students
        missing_csv_path = csv_path.parent / f"missing-students-{self.batch.batch_id}.csv"

        receipt_data = self._load_receipt_data("data/legacy/all_receipt_headers_250723.csv")
        if hasattr(self, "batch") and self.batch.term_id:
            receipt_data = [r for r in receipt_data if r["TermID"] == self.batch.term_id]

        missing_students = []
        for receipt in receipt_data[: self.batch.total_receipts]:
            student_id = receipt["ID"].strip().zfill(5)
            try:
                StudentProfile.objects.get(student_id=int(student_id))
            except (ValueError, StudentProfile.DoesNotExist):
                missing_students.append(receipt)

        if missing_students:
            with open(missing_csv_path, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)

                # Header
                writer.writerow(
                    [
                        "Student_ID",
                        "Student_Name",
                        "Receipt_Number",
                        "Term_ID",
                        "Amount",
                        "Net_Amount",
                        "Discount",
                        "Payment_Date",
                        "Program",
                        "Gender",
                        "Current_Level",
                        "Notes",
                    ]
                )

                # Missing student data
                for receipt in missing_students:
                    writer.writerow(
                        [
                            receipt.get("ID", ""),
                            receipt.get("name", ""),
                            receipt.get("ReceiptNo", ""),
                            receipt.get("TermID", ""),
                            receipt.get("Amount", ""),
                            receipt.get("NetAmount", ""),
                            receipt.get("NetDiscount", ""),
                            receipt.get("PmtDate", ""),
                            receipt.get("Program", ""),
                            receipt.get("Gender", ""),
                            receipt.get("CurLevel", ""),
                            receipt.get("Notes", ""),
                        ]
                    )

            self.stdout.write(f"📋 Missing students CSV: {missing_csv_path}")
