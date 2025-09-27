"""
Multi-tier semantic processing system for receipt notes in Django.
Processes legacy receipt notes to extract discount, penalty, and scholarship information.
"""

import csv
import re
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any

from apps.common.management.base_migration import BaseMigrationCommand


class ProcessingTier(Enum):
    RULE_BASED = "rule_based"
    NLP = "nlp"
    LLM = "llm"


class NoteType(Enum):
    DISCOUNT_PERCENTAGE = "discount_percentage"
    DISCOUNT_AMOUNT = "discount_amount"
    DISCOUNT_MONK = "discount_monk"
    DISCOUNT_STAFF = "discount_staff"
    DISCOUNT_SIBLING = "discount_sibling"
    DISCOUNT_EARLY_BIRD = "discount_early_bird"
    SCHOLARSHIP = "scholarship"
    SCHOLARSHIP_NEEDS_CREATION = "scholarship_needs_creation"
    PENALTY = "penalty"
    LATE_PAYMENT = "late_payment"
    LATE_FEE = "late_fee"
    EXTRA_COURSE = "extra_course"
    ADMIN_FEE = "admin_fee"
    INSTALLMENT = "installment"
    PAYMENT_METHOD = "payment_method"
    ID_ISSUES = "id_issues"
    REPEAT_CLASS = "repeat_class"
    OTHER = "other"


@dataclass
class ProcessedNote:
    """Represents a processed note with extracted semantic information"""

    original_note: str
    note_type: NoteType
    processing_tier: ProcessingTier
    amount_adjustment: Decimal | None = None
    percentage_adjustment: float | None = None
    authority: str | None = None
    reason: str | None = None
    confidence: float = 1.0
    raw_extracts: dict[Any, Any] | None = None
    ar_transaction_mapping: str | None = None  # Where this gets recorded in A/R


class NotesProcessor:
    """
    Multi-tier semantic processing system for receipt notes
    Processes notes to extract discount, penalty, and scholarship information
    """

    def __init__(self):
        self.tier1_patterns = self._compile_rule_patterns()
        self.processed_count = 0
        self.tier_stats = dict.fromkeys(ProcessingTier, 0)

    def _compile_rule_patterns(self) -> dict[NoteType, list[re.Pattern]]:
        """Compile regex patterns for rule-based processing"""
        return {
            NoteType.DISCOUNT_MONK: [
                re.compile(r"dis[ct]?\.?\s*(\d+).*monk", re.IGNORECASE),
                re.compile(r"monk.*dis[ct]?\.?\s*(\d+)", re.IGNORECASE),
                re.compile(r"(\d+)\s*\$?\s*dis[ct]?\.?.*monk", re.IGNORECASE),
            ],
            NoteType.DISCOUNT_STAFF: [
                re.compile(r"dis[ct]?\.?\s*(\d+)%.*phann", re.IGNORECASE),
                re.compile(r"phann.*dis[ct]?\.?\s*(\d+)%", re.IGNORECASE),
                re.compile(r"staff.*dis[ct]?\.?\s*(\d+)", re.IGNORECASE),
            ],
            NoteType.DISCOUNT_SIBLING: [
                re.compile(r"dis[ct]?\.?\s*(\d+).*sibling", re.IGNORECASE),
                re.compile(r"sibling.*dis[ct]?\.?\s*(\d+)", re.IGNORECASE),
            ],
            NoteType.DISCOUNT_EARLY_BIRD: [
                re.compile(r"early.?bird.*dis[ct]?\.?\s*(\d+)", re.IGNORECASE),
                re.compile(r"dis[ct]?\.?\s*(\d+).*early.?bird", re.IGNORECASE),
                re.compile(r"early.*registration.*dis[ct]?\.?\s*(\d+)", re.IGNORECASE),
                re.compile(r"early.*payment.*dis[ct]?\.?\s*(\d+)", re.IGNORECASE),
            ],
            NoteType.DISCOUNT_PERCENTAGE: [
                re.compile(r"dis[ct]?\.?\s*(\d+)%", re.IGNORECASE),
                re.compile(r"(\d+)%\s*dis[ct]?\.?", re.IGNORECASE),
            ],
            NoteType.DISCOUNT_AMOUNT: [
                re.compile(r"dis[ct]?\.?\s*\$?(\d+)\$?", re.IGNORECASE),
                re.compile(r"\$?(\d+)\$?\s*dis[ct]?\.?", re.IGNORECASE),
            ],
            NoteType.SCHOLARSHIP: [
                re.compile(r"scholar", re.IGNORECASE),  # Must contain "scholar" fragment
                re.compile(r"\bsch\b", re.IGNORECASE),  # Also "sch" as scholarship abbreviation
            ],
            NoteType.SCHOLARSHIP_NEEDS_CREATION: [
                re.compile(r"need.*scholarship|create.*scholarship", re.IGNORECASE),
                re.compile(r"scholarship.*need|scholarship.*create", re.IGNORECASE),
                re.compile(r"new.*scholarship|setup.*scholarship", re.IGNORECASE),
            ],
            NoteType.ADMIN_FEE: [
                re.compile(r"admin\s*=\s*(\d+)", re.IGNORECASE),
                re.compile(r"admin.*fee\s*(\d+)", re.IGNORECASE),
                re.compile(r"administration.*fee\s*(\d+)", re.IGNORECASE),
            ],
            NoteType.PENALTY: [
                re.compile(r"penalty|fine", re.IGNORECASE),
                re.compile(r"charge.*extra|extra.*charge", re.IGNORECASE),
            ],
            NoteType.LATE_PAYMENT: [
                re.compile(r"late|pay\s+late", re.IGNORECASE),
                re.compile(r"overdue|past\s+due", re.IGNORECASE),
            ],
            NoteType.LATE_FEE: [
                re.compile(r"late.*fee\s*(\d+)", re.IGNORECASE),
                re.compile(r"overdue.*fee\s*(\d+)", re.IGNORECASE),
                re.compile(r"(\d+).*late.*fee", re.IGNORECASE),
                re.compile(r"late.*charge\s*(\d+)", re.IGNORECASE),
            ],
            NoteType.EXTRA_COURSE: [
                re.compile(r"added.*course|extra.*course|more.*course", re.IGNORECASE),
                re.compile(r"additional.*class|extra.*class", re.IGNORECASE),
            ],
            NoteType.INSTALLMENT: [
                re.compile(r"installment|payment.*times", re.IGNORECASE),
                re.compile(r"split.*payment|partial.*payment", re.IGNORECASE),
                re.compile(r"paid.*next\s+on|pay.*next\s+on", re.IGNORECASE),
                re.compile(r"paid.*for.*installment|inst\.\s*\d+", re.IGNORECASE),
            ],
            NoteType.PAYMENT_METHOD: [
                # Bank transfers
                re.compile(r"paid?\s+by\s+(ABA|ACLEDA|AC)\s*(bank|check)?", re.IGNORECASE),
                re.compile(r"pay\s+by\s+(bank|transfer|ABA|ACLEDA|AC)", re.IGNORECASE),
                re.compile(r"(ABA|ACLEDA|AC)\s+(bank|transfer|payment)", re.IGNORECASE),
                # Cash payments
                re.compile(r"paid?\s+by\s+cash", re.IGNORECASE),
                re.compile(r"cash\s+payment", re.IGNORECASE),
                # Check payments
                re.compile(r"paid?\s+by\s+check", re.IGNORECASE),
                re.compile(r"pay\s+by\s+check", re.IGNORECASE),
            ],
            NoteType.ID_ISSUES: [
                re.compile(r"4get\s+id|forget\s+id|no\s+id", re.IGNORECASE),
                re.compile(r"lost\s+id|missing\s+id", re.IGNORECASE),
            ],
            NoteType.REPEAT_CLASS: [
                re.compile(r"repeat|retake", re.IGNORECASE),
                re.compile(r"again|second\s+time", re.IGNORECASE),
            ],
        }

    def process_note(self, note: str) -> ProcessedNote:
        """Process a single note through the multi-tier system"""
        if not note or note.strip().lower() in ["null", "none", ""]:
            return ProcessedNote(
                original_note="",
                note_type=NoteType.OTHER,
                processing_tier=ProcessingTier.RULE_BASED,
                confidence=1.0,
            )

        note = str(note).strip()

        # Tier 1: Rule-based processing
        result = self._process_tier1_rules(note)
        if result.note_type != NoteType.OTHER:
            self.tier_stats[ProcessingTier.RULE_BASED] += 1
            return result

        # Tier 2: NLP processing
        result = self._process_tier2_nlp(note)
        if result.note_type != NoteType.OTHER:
            self.tier_stats[ProcessingTier.NLP] += 1
            return result

        # Tier 3: LLM processing (placeholder - would require external API)
        result = self._process_tier3_llm(note)
        self.tier_stats[ProcessingTier.LLM] += 1
        return result

    def _process_tier1_rules(self, note: str) -> ProcessedNote:
        """Rule-based pattern matching (Tier 1)"""

        # Extract potential authority
        authority = self._extract_authority(note)

        # Test each pattern category
        for note_type, patterns in self.tier1_patterns.items():
            for pattern in patterns:
                match = pattern.search(note)
                if match:
                    # Extract numeric values
                    amount_adjustment = None
                    percentage_adjustment = None

                    if match.groups():
                        value = match.group(1)
                        try:
                            numeric_value = float(value)
                            if "%" in match.group(0) or note_type == NoteType.DISCOUNT_PERCENTAGE:
                                percentage_adjustment = numeric_value
                            else:
                                amount_adjustment = Decimal(str(numeric_value))
                        except (ValueError, TypeError):
                            pass

                    return ProcessedNote(
                        original_note=note,
                        note_type=note_type,
                        processing_tier=ProcessingTier.RULE_BASED,
                        amount_adjustment=amount_adjustment,
                        percentage_adjustment=percentage_adjustment,
                        authority=authority,
                        reason=self._extract_reason(note, note_type),
                        confidence=0.95,
                        raw_extracts={"match": match.group(0)},
                        ar_transaction_mapping=self._get_ar_transaction_mapping(note_type),
                    )

        return ProcessedNote(
            original_note=note,
            note_type=NoteType.OTHER,
            processing_tier=ProcessingTier.RULE_BASED,
            confidence=0.0,
        )

    def _process_tier2_nlp(self, note: str) -> ProcessedNote:
        """NLP-based semantic processing (Tier 2)"""
        note_lower = note.lower()

        # Advanced semantic patterns
        semantic_indicators = {
            "discount": ["reduce", "lower", "less", "decrease", "cut", "minus"],
            "penalty": ["add", "extra", "additional", "plus", "increase", "more"],
            # Remove overly broad scholarship matching - let Tier 1 handle it with "scholar" fragment
            "family": ["family", "brother", "sister", "sibling", "parent", "child"],
            "staff": ["employee", "worker", "staff", "faculty", "teacher"],
            "timing": ["late", "early", "on time", "deadline", "due"],
        }

        # Look for semantic clusters
        for category, indicators in semantic_indicators.items():
            if any(indicator in note_lower for indicator in indicators):
                # Extract numbers from context
                numbers = re.findall(r"\b(\d+(?:\.\d+)?)\b", note)
                percentages = re.findall(r"\b(\d+(?:\.\d+)?)%", note)

                amount_adjustment = None
                percentage_adjustment = None

                if percentages:
                    percentage_adjustment = float(percentages[0])
                elif numbers:
                    amount_adjustment = Decimal(numbers[0])

                # Map semantic category to note type
                note_type_mapping = {
                    "discount": NoteType.DISCOUNT_AMOUNT,
                    "penalty": NoteType.PENALTY,
                    "scholarship": NoteType.SCHOLARSHIP,
                    "family": NoteType.DISCOUNT_SIBLING,
                    "staff": NoteType.DISCOUNT_STAFF,
                    "timing": NoteType.LATE_PAYMENT,
                }

                mapped_note_type = note_type_mapping.get(category, NoteType.OTHER)
                return ProcessedNote(
                    original_note=note,
                    note_type=mapped_note_type,
                    processing_tier=ProcessingTier.NLP,
                    amount_adjustment=amount_adjustment,
                    percentage_adjustment=percentage_adjustment,
                    authority=self._extract_authority(note),
                    reason=f"Semantic: {category}",
                    confidence=0.75,
                    raw_extracts={"semantic_category": category, "numbers": numbers},
                    ar_transaction_mapping=self._get_ar_transaction_mapping(mapped_note_type),
                )

        return ProcessedNote(
            original_note=note,
            note_type=NoteType.OTHER,
            processing_tier=ProcessingTier.NLP,
            confidence=0.0,
        )

    def _process_tier3_llm(self, note: str) -> ProcessedNote:
        """LLM-based processing (Tier 3) - Placeholder implementation"""
        # This would integrate with an LLM API for complex semantic understanding
        # For now, we'll use heuristic fallback

        # If contains numbers, likely financial adjustment
        if re.search(r"\d+", note):
            numbers = re.findall(r"\b(\d+(?:\.\d+)?)\b", note)
            if numbers:
                amount_adjustment = Decimal(numbers[0])
                return ProcessedNote(
                    original_note=note,
                    note_type=NoteType.OTHER,
                    processing_tier=ProcessingTier.LLM,
                    amount_adjustment=amount_adjustment,
                    reason="LLM: Numeric pattern detected",
                    confidence=0.5,
                    raw_extracts={"numbers": numbers},
                    ar_transaction_mapping=self._get_ar_transaction_mapping(NoteType.OTHER),
                )

        return ProcessedNote(
            original_note=note,
            note_type=NoteType.OTHER,
            processing_tier=ProcessingTier.LLM,
            confidence=0.3,
        )

    def _extract_authority(self, note: str) -> str | None:
        """Extract authority/approver from note"""
        # Simple approach: look for "by " followed by name patterns
        patterns = [
            # Pattern 1: "by Mr. Name Name" or "by Dr. Name Name" (space after period, multiple names)
            r"by\s+((?:Mr|Ms|Mrs|Dr)\.?\s+[A-Za-z]+(?:\s+[A-Za-z]+)*)",
            # Pattern 2: "by Mr.Name" or "by Dr.Name" (no space after period)
            r"by\s+((?:Mr|Ms|Mrs|Dr)\.?[A-Za-z]+)",
            # Pattern 3: "by FirstName LastName" (no title)
            r"by\s+([A-Za-z]+\s+[A-Za-z]+)",
            # Pattern 4: "by Name" (single name)
            r"by\s+([A-Za-z]+)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, note, re.IGNORECASE)
            if matches:
                # Take the last match (in case there are multiple "by" clauses)
                authority = matches[-1].strip()

                # Clean up trailing punctuation
                authority = re.sub(r"\s*[.,;:]+$", "", authority)

                # Only return if we have meaningful content
                if authority and len(authority) > 1:
                    return authority

        return None

    def _extract_reason(self, note: str, note_type: NoteType) -> str | None:
        """Extract reason/explanation from note"""
        # Simple reason extraction based on note type
        reason_mapping = {
            NoteType.DISCOUNT_MONK: "Monastic discount",
            NoteType.DISCOUNT_STAFF: "Staff/employee discount",
            NoteType.DISCOUNT_SIBLING: "Sibling discount",
            NoteType.DISCOUNT_EARLY_BIRD: "Early registration discount",
            NoteType.SCHOLARSHIP: "Scholarship/grant",
            NoteType.SCHOLARSHIP_NEEDS_CREATION: "Scholarship requires setup",
            NoteType.PENALTY: "Penalty/fine",
            NoteType.LATE_PAYMENT: "Late payment",
            NoteType.LATE_FEE: "Late payment fee",
            NoteType.ADMIN_FEE: "Administrative fee",
            NoteType.EXTRA_COURSE: "Extra course fee",
            NoteType.INSTALLMENT: "Installment payment",
            NoteType.PAYMENT_METHOD: "Payment method/source",
            NoteType.ID_ISSUES: "ID card issues",
            NoteType.REPEAT_CLASS: "Repeat class fee",
        }

        return reason_mapping.get(note_type)

    def _get_ar_transaction_mapping(self, note_type: NoteType) -> str:
        """Determine where this note type gets recorded in the A/R transaction"""
        mapping = {
            # Discounts - recorded as invoice line items with negative amounts or reduced base amounts
            NoteType.DISCOUNT_MONK: "invoice_line_item_discount",
            NoteType.DISCOUNT_STAFF: "invoice_line_item_discount",
            NoteType.DISCOUNT_SIBLING: "invoice_line_item_discount",
            NoteType.DISCOUNT_EARLY_BIRD: "invoice_line_item_discount",
            NoteType.DISCOUNT_PERCENTAGE: "invoice_line_item_discount",
            NoteType.DISCOUNT_AMOUNT: "invoice_line_item_discount",
            # Scholarships - recorded in scholarship tracking system + invoice adjustments
            NoteType.SCHOLARSHIP: "scholarship_entry",
            NoteType.SCHOLARSHIP_NEEDS_CREATION: "scholarship_creation_required",
            # Additional charges - recorded as separate invoice line items
            NoteType.PENALTY: "invoice_line_item_charge",
            NoteType.LATE_FEE: "invoice_line_item_charge",
            NoteType.ADMIN_FEE: "invoice_line_item_charge",
            NoteType.EXTRA_COURSE: "invoice_line_item_charge",
            # Payment processing notes - recorded in payment metadata
            NoteType.LATE_PAYMENT: "payment_metadata",
            NoteType.INSTALLMENT: "payment_metadata",
            NoteType.PAYMENT_METHOD: "payment_metadata",
            NoteType.ID_ISSUES: "payment_metadata",
            NoteType.REPEAT_CLASS: "payment_metadata",
            # Unknown/other - recorded in invoice notes field
            NoteType.OTHER: "invoice_notes",
        }

        return mapping.get(note_type, "invoice_notes")

    def create_normalized_note(self, processed: ProcessedNote) -> str:
        """Create normalized note string for database storage"""
        parts = []

        # Add type
        parts.append(f"TYPE:{processed.note_type.value}")

        # Add adjustment
        if processed.amount_adjustment:
            parts.append(f"AMOUNT:{processed.amount_adjustment}")
        elif processed.percentage_adjustment:
            parts.append(f"PERCENT:{processed.percentage_adjustment}")

        # Add authority
        if processed.authority:
            parts.append(f"AUTH:{processed.authority}")

        # Add reason
        if processed.reason:
            parts.append(f"REASON:{processed.reason}")

        # Add confidence
        parts.append(f"CONF:{processed.confidence:.2f}")

        # Add tier
        parts.append(f"TIER:{processed.processing_tier.value}")

        # Add A/R transaction mapping
        if processed.ar_transaction_mapping:
            parts.append(f"AR_MAPPING:{processed.ar_transaction_mapping}")

        return "|".join(parts)

    def get_processing_stats(self) -> dict:
        """Get processing statistics"""
        total = sum(self.tier_stats.values())
        return {
            "total_processed": total,
            "tier_breakdown": {
                tier.value: {
                    "count": count,
                    "percentage": (count / total * 100) if total > 0 else 0,
                }
                for tier, count in self.tier_stats.items()
            },
        }


class Command(BaseMigrationCommand):
    """Django management command for processing receipt notes."""

    help = "Process receipt notes using multi-tier semantic analysis"

    def add_arguments(self, parser):
        super().add_arguments(parser)

        parser.add_argument(
            "--receipt-file",
            type=str,
            default="data/legacy/all_receipt_headers_250728.csv",
            help="Path to receipt_headers CSV file",
        )

        parser.add_argument("--sample-size", type=int, help="Process only first N records (for testing)")

        parser.add_argument(
            "--output-processed",
            type=str,
            default="project-docs/notes-processing/processed_notes.csv",
            help="Output file for processed notes",
        )

        parser.add_argument(
            "--output-stats",
            type=str,
            default="project-docs/notes-processing/processing_stats.txt",
            help="Output file for processing statistics",
        )

    def execute_migration(self, *args, **options):
        """Execute the notes processing migration."""
        return self.handle(*args, **options)

    def get_rejection_categories(self):
        """Return rejection categories for failed processing."""
        return {
            "INVALID_NOTE": "Note content is invalid or unprocessable",
            "PROCESSING_ERROR": "Error occurred during note processing",
            "LOW_CONFIDENCE": "Processing confidence below threshold",
        }

    def handle(self, *args, **options):
        """Main command handler."""
        self.stdout.write("🔍 Starting multi-tier notes processing...")

        # Load receipt data
        receipts = self._load_receipt_data(options["receipt_file"], options.get("sample_size"))

        # Initialize processor
        processor = NotesProcessor()

        # Process all notes
        self.stdout.write(f"📝 Processing {len(receipts):,} receipt notes...")
        results = []

        for i, receipt in enumerate(receipts):
            note = receipt.get("Notes", "")
            processed = processor.process_note(note)

            # Create result record
            result = {
                "receipt_id": receipt.get("ReceiptID", ""),
                "receipt_no": receipt.get("ReceiptNo", ""),
                "student_id": receipt.get("ID", ""),
                "term_id": receipt.get("TermID", ""),
                "original_note": processed.original_note,
                "note_type": processed.note_type.value,
                "processing_tier": processed.processing_tier.value,
                "amount_adjustment": (str(processed.amount_adjustment) if processed.amount_adjustment else None),
                "percentage_adjustment": processed.percentage_adjustment,
                "authority": processed.authority,
                "reason": processed.reason,
                "confidence": processed.confidence,
                "ar_transaction_mapping": processed.ar_transaction_mapping,
                "normalized_note": processor.create_normalized_note(processed),
            }

            results.append(result)

            # Progress reporting
            if (i + 1) % 1000 == 0:
                self.stdout.write(f"   Processed {i + 1:,} notes...")

        # Generate reports
        self._generate_processed_notes_report(results, options["output_processed"])
        self._generate_statistics_report(processor, options["output_stats"])

        # Show summary statistics
        stats = processor.get_processing_stats()
        self.stdout.write("\n📊 PROCESSING COMPLETE")
        self.stdout.write(f"   Total processed: {stats['total_processed']:,}")

        for tier, data in stats["tier_breakdown"].items():
            self.stdout.write(f"   {tier}: {data['count']:,} ({data['percentage']:.1f}%)")

        # Show interesting results
        self._show_sample_results(results)

        self.stdout.write("\n✅ Reports saved:")
        self.stdout.write(f"   Processed notes: {options['output_processed']}")
        self.stdout.write(f"   Statistics: {options['output_stats']}")

    def _load_receipt_data(self, file_path: str, sample_size: int | None = None) -> list[dict]:
        """Load receipt data, excluding deleted records."""
        receipts = []
        deleted_count = 0
        csv_path = Path(file_path)

        if not csv_path.exists():
            raise FileNotFoundError(f"Receipt file not found: {file_path}")

        self.stdout.write(f"📥 Loading data from {file_path}...")

        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                # Skip deleted records (Deleted=1)
                if row.get("Deleted", "0").strip() == "1":
                    deleted_count += 1
                    continue

                receipts.append(row)

                if sample_size and len(receipts) >= sample_size:
                    break

                # Progress indicator for large datasets
                if i > 0 and i % 10000 == 0:
                    self.stdout.write(
                        f"   Loaded {len(receipts):,} valid records, skipped {deleted_count:,} deleted..."
                    )

        self.stdout.write(f"✅ Loaded {len(receipts):,} valid receipt records")
        self.stdout.write(f"🗑️  Excluded {deleted_count:,} deleted records")
        return receipts

    def _generate_processed_notes_report(self, results: list[dict], output_file: str):
        """Generate CSV report of processed notes."""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if not results:
            return

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            fieldnames = results[0].keys()
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)

    def _generate_statistics_report(self, processor: NotesProcessor, output_file: str):
        """Generate statistics report."""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        stats = processor.get_processing_stats()

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("Receipt Notes Processing Statistics\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Total processed: {stats['total_processed']:,}\n\n")

            f.write("Processing Tier Breakdown:\n")
            for tier, data in stats["tier_breakdown"].items():
                f.write(f"  {tier}: {data['count']:,} ({data['percentage']:.1f}%)\n")

            f.write("\nTier Descriptions:\n")
            f.write("  rule_based: Pattern matching with regex rules\n")
            f.write("  nlp: Semantic analysis with contextual indicators\n")
            f.write("  llm: Fallback processing for complex cases\n")

    def _show_sample_results(self, results: list[dict]):
        """Show sample interesting results."""
        self.stdout.write("\n🔍 SAMPLE RESULTS")

        # Show examples of each note type found
        note_types_seen = set()
        sample_count = 0

        for result in results:
            note_type = result["note_type"]
            if note_type != "other" and note_type not in note_types_seen and sample_count < 10:
                note_types_seen.add(note_type)
                sample_count += 1

                self.stdout.write(f"   {note_type.upper()}:")
                ellipsis = "..." if len(result["original_note"]) > 60 else ""
                self.stdout.write(f'     Original: "{result["original_note"][:60]}{ellipsis}"')

                if result["amount_adjustment"]:
                    self.stdout.write(f"     Amount: ${result['amount_adjustment']}")
                elif result["percentage_adjustment"]:
                    self.stdout.write(f"     Percentage: {result['percentage_adjustment']}%")

                if result["authority"]:
                    self.stdout.write(f"     Authority: {result['authority']}")

                self.stdout.write(f"     Confidence: {result['confidence']:.2f}")
                self.stdout.write("")
