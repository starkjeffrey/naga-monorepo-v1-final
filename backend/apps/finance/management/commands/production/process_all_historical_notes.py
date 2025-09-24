#!/usr/bin/env python
"""
Process ALL legacy receipt notes from the beginning of time.

This command processes every legacy receipt note to extract:
- Discount patterns and percentages
- Authorities and approval chains
- Payment methods and deadlines
- Scholarship information
- Business rules and special cases

Does NOT require full A/R reconstruction - focuses purely on notes analysis.
"""

import os
from datetime import datetime
from decimal import Decimal
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.finance.management.commands.process_receipt_notes import NotesProcessor
from apps.finance.models.ar_reconstruction import (
    ARReconstructionBatch,
)


class HistoricalNotesRecord:
    """Container for historical notes analysis results."""

    def __init__(self, ipk: int, receipt_data: dict[str, Any], notes_result):
        self.ipk = ipk
        self.receipt_number = receipt_data.get("ReceiptNo", "")
        self.receipt_id = receipt_data.get("ReceiptID", "")
        self.student_id = receipt_data.get("ID", "")
        self.term_id = receipt_data.get("TermID", "")
        self.amount = Decimal(str(receipt_data.get("Amount", 0) or 0)) / 100
        self.notes = receipt_data.get("Notes", "")

        # Parsed results
        self.note_type = notes_result.note_type.value if notes_result else "unknown"
        self.percentage_adjustment = notes_result.percentage_adjustment if notes_result else None
        self.amount_adjustment = notes_result.amount_adjustment if notes_result else None
        self.authority = notes_result.authority if notes_result else ""
        self.reason = notes_result.reason if notes_result else ""
        self.confidence = notes_result.confidence if notes_result else 0.0


class Command(BaseCommand):
    """Process all historical notes without full reconstruction."""

    help = "Process ALL legacy receipt notes to extract discount patterns and business rules"

    def __init__(self):
        super().__init__()
        self.notes_processor = None
        self.batch_record = None
        self.processed_count = 0
        self.discount_count = 0
        self.scholarship_count = 0
        self.error_count = 0

        # Analysis collections
        self.discount_patterns = []
        self.scholarship_patterns = []
        self.authority_patterns = []
        self.deadline_patterns = []
        self.error_patterns = []

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--source",
            choices=["csv", "django"],
            default="django",
            help="Data source: csv file or django legacy tables",
        )
        parser.add_argument("--csv-file", type=str, help="Path to CSV file (required if source=csv)")
        parser.add_argument("--max-records", type=int, help="Maximum records to process (for testing)")
        parser.add_argument(
            "--report-dir",
            type=str,
            default="project-docs/notes-analysis-reports",
            help="Directory for analysis reports",
        )
        parser.add_argument("--batch-size", type=int, default=1000, help="Processing batch size")

    def handle(self, *args, **options):
        """Main command execution."""
        try:
            self.setup_processing(options)

            if options["source"] == "csv":
                if not options["csv_file"]:
                    raise CommandError("--csv-file required when source=csv")
                self.process_csv_source(options["csv_file"], options)
            else:
                self.process_django_source(options)

            self.generate_comprehensive_report(options["report_dir"])
            self.print_final_summary()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Historical notes processing failed: {e}"))
            raise

    def setup_processing(self, options):
        """Initialize processing components."""
        self.stdout.write("🔧 Setting up historical notes processor...")

        # Initialize notes processor
        self.notes_processor = NotesProcessor()

        # Create batch tracking record
        batch_id = f"historical_notes_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.batch_record = ARReconstructionBatch.objects.create(
            batch_id=batch_id,
            term_id="ALL_HISTORICAL",
            processing_mode=ARReconstructionBatch.ProcessingMode.AUTOMATED,
            status=ARReconstructionBatch.BatchStatus.PROCESSING,
            total_receipts=0,  # Will update as we discover total
            processing_parameters={
                "source": options["source"],
                "max_records": options.get("max_records"),
                "purpose": "historical_notes_analysis",
            },
            started_at=timezone.now(),
        )

        self.stdout.write(f"✅ Created batch: {batch_id}")

    def process_django_source(self, options):
        """Process notes from Django legacy tables."""
        self.stdout.write("📊 Processing notes from Django legacy tables...")

        try:
            # Import here to avoid circular imports during Django setup
            from django.db import connection

            # Query all receipt headers with notes
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT ipk, receiptno, receiptid, id, termid, amount, notes
                    FROM legacy_receipt_headers
                    WHERE deleted != 1
                    AND notes IS NOT NULL
                    AND TRIM(notes) != ''
                    ORDER BY ipk
                """
                )

                receipts = []
                for row in cursor.fetchall():
                    receipts.append(
                        {
                            "IPK": row[0],
                            "ReceiptNo": row[1],
                            "ReceiptID": row[2],
                            "ID": row[3],
                            "TermID": row[4],
                            "Amount": row[5],
                            "Notes": row[6],
                        }
                    )

                self.stdout.write(f"📋 Found {len(receipts):,} receipts with notes")
                self.process_receipt_batch(receipts, options)

        except Exception as e:
            if 'relation "legacy_receipt_headers" does not exist' in str(e):
                self.stdout.write(self.style.WARNING("⚠️ No legacy_receipt_headers table found in current database"))
                self.stdout.write("💡 Suggestion: Use --source=csv with receipt data file")
            raise

    def process_csv_source(self, csv_file_path: str, options):
        """Process notes from CSV file."""
        import csv

        self.stdout.write(f"📂 Processing notes from CSV: {csv_file_path}")

        if not os.path.exists(csv_file_path):
            raise CommandError(f"CSV file not found: {csv_file_path}")

        receipts = []
        with open(csv_file_path, encoding="utf-8") as file:
            # Auto-detect CSV format
            sample = file.read(1024)
            file.seek(0)
            sniffer = csv.Sniffer()
            delimiter = sniffer.sniff(sample).delimiter

            reader = csv.DictReader(file, delimiter=delimiter)

            for row in reader:
                # Only process if notes exist
                notes = row.get("Notes", "").strip()
                if notes and notes.lower() not in ["null", "none", ""]:
                    receipts.append(row)

        self.stdout.write(f"📋 Found {len(receipts):,} receipts with notes")
        self.process_receipt_batch(receipts, options)

    def process_receipt_batch(self, receipts: list[dict[str, Any]], options):
        """Process a batch of receipts."""
        max_records = options.get("max_records")
        batch_size = options["batch_size"]

        if max_records:
            receipts = receipts[:max_records]
            self.stdout.write(f"🎯 Limiting to {max_records:,} records for testing")

        # Update batch total
        self.batch_record.total_receipts = len(receipts)
        self.batch_record.save()

        # Process in batches
        for i in range(0, len(receipts), batch_size):
            batch_end = min(i + batch_size, len(receipts))
            batch_receipts = receipts[i:batch_end]

            self.stdout.write(f"🔄 Processing batch {i // batch_size + 1}: records {i + 1:,} to {batch_end:,}")

            with transaction.atomic():
                for receipt_data in batch_receipts:
                    try:
                        self.process_individual_notes(receipt_data)
                    except Exception as e:
                        self.error_count += 1
                        self.error_patterns.append(
                            {
                                "ipk": receipt_data.get("IPK"),
                                "receipt_number": receipt_data.get("ReceiptNo"),
                                "notes": receipt_data.get("Notes", ""),
                                "error": str(e),
                            }
                        )

            # Progress report
            if (i + batch_size) % 5000 == 0:
                self.print_progress_summary()

    def process_individual_notes(self, receipt_data: dict[str, Any]):
        """Process notes for a single receipt."""
        notes = receipt_data.get("Notes", "").strip()
        if not notes or notes.lower() in ["null", "none", ""]:
            return

        try:
            # Process notes using the existing notes processor
            notes_result = self.notes_processor.process_note(notes)

            # Create historical record
            record = HistoricalNotesRecord(
                ipk=int(receipt_data.get("IPK", 0)),
                receipt_data=receipt_data,
                notes_result=notes_result,
            )

            # Categorize and collect patterns
            self.categorize_and_collect(record)

            self.processed_count += 1

        except Exception as e:
            self.error_count += 1
            raise e

    def categorize_and_collect(self, record: HistoricalNotesRecord):
        """Categorize notes and collect patterns."""

        # Discount patterns
        if record.note_type in [
            "discount_percentage",
            "discount_amount",
            "discount_monk",
        ]:
            self.discount_count += 1
            self.discount_patterns.append(
                {
                    "ipk": record.ipk,
                    "receipt_number": record.receipt_number,
                    "term": record.term_id,
                    "student_id": record.student_id,
                    "type": record.note_type,
                    "percentage": (float(record.percentage_adjustment) if record.percentage_adjustment else None),
                    "amount": (float(record.amount_adjustment) if record.amount_adjustment else None),
                    "authority": record.authority,
                    "notes": record.notes,
                    "confidence": record.confidence,
                }
            )

        # Scholarship patterns
        if record.note_type == "scholarship" or "scholarship" in record.notes.lower():
            self.scholarship_count += 1
            self.scholarship_patterns.append(
                {
                    "ipk": record.ipk,
                    "receipt_number": record.receipt_number,
                    "term": record.term_id,
                    "student_id": record.student_id,
                    "notes": record.notes,
                    "authority": record.authority,
                    "confidence": record.confidence,
                }
            )

        # Authority patterns (anyone with authority info)
        if record.authority:
            self.authority_patterns.append(
                {
                    "ipk": record.ipk,
                    "receipt_number": record.receipt_number,
                    "term": record.term_id,
                    "authority": record.authority,
                    "type": record.note_type,
                    "notes": record.notes,
                }
            )

        # Deadline patterns (notes with date info)
        if any(keyword in record.notes.lower() for keyword in ["pay by", "before", "until", "deadline"]):
            self.deadline_patterns.append(
                {
                    "ipk": record.ipk,
                    "receipt_number": record.receipt_number,
                    "term": record.term_id,
                    "notes": record.notes,
                    "authority": record.authority,
                }
            )

    def generate_comprehensive_report(self, report_dir: str):
        """Generate comprehensive analysis report."""
        os.makedirs(report_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Discount patterns report
        discount_file = os.path.join(report_dir, f"discount_patterns_{timestamp}.csv")
        self.write_csv_report(
            discount_file,
            self.discount_patterns,
            [
                "ipk",
                "receipt_number",
                "term",
                "student_id",
                "type",
                "percentage",
                "amount",
                "authority",
                "notes",
                "confidence",
            ],
        )

        # Scholarship patterns report
        scholarship_file = os.path.join(report_dir, f"scholarship_patterns_{timestamp}.csv")
        self.write_csv_report(
            scholarship_file,
            self.scholarship_patterns,
            [
                "ipk",
                "receipt_number",
                "term",
                "student_id",
                "notes",
                "authority",
                "confidence",
            ],
        )

        # Authority patterns report
        authority_file = os.path.join(report_dir, f"authority_patterns_{timestamp}.csv")
        self.write_csv_report(
            authority_file,
            self.authority_patterns,
            ["ipk", "receipt_number", "term", "authority", "type", "notes"],
        )

        # Deadline patterns report
        deadline_file = os.path.join(report_dir, f"deadline_patterns_{timestamp}.csv")
        self.write_csv_report(
            deadline_file,
            self.deadline_patterns,
            ["ipk", "receipt_number", "term", "notes", "authority"],
        )

        # Error patterns report
        if self.error_patterns:
            error_file = os.path.join(report_dir, f"error_patterns_{timestamp}.csv")
            self.write_csv_report(
                error_file,
                self.error_patterns,
                ["ipk", "receipt_number", "notes", "error"],
            )

        # Summary statistics report
        self.generate_summary_report(report_dir, timestamp)

        self.stdout.write(f"📋 Reports generated in: {report_dir}")

    def write_csv_report(self, filename: str, data: list[dict], fieldnames: list[str]):
        """Write data to CSV report."""
        import csv

        with open(filename, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)

        self.stdout.write(f"  📄 {os.path.basename(filename)}: {len(data):,} records")

    def generate_summary_report(self, report_dir: str, timestamp: str):
        """Generate summary statistics report."""
        summary_file = os.path.join(report_dir, f"historical_notes_summary_{timestamp}.txt")

        with open(summary_file, "w", encoding="utf-8") as file:
            file.write("HISTORICAL NOTES ANALYSIS SUMMARY\n")
            file.write("=" * 50 + "\n\n")
            file.write(f"Processing Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            file.write(f"Batch ID: {self.batch_record.batch_id}\n\n")

            file.write("PROCESSING STATISTICS\n")
            file.write("-" * 30 + "\n")
            file.write(f"Total Processed: {self.processed_count:,}\n")
            discount_pct = (self.discount_count / self.processed_count * 100) if self.processed_count > 0 else 0
            scholarship_pct = (self.scholarship_count / self.processed_count * 100) if self.processed_count > 0 else 0
            file.write(f"Discount Patterns: {self.discount_count:,} ({discount_pct:.1f}%)\n")
            file.write(f"Scholarship Patterns: {self.scholarship_count:,} ({scholarship_pct:.1f}%)\n")
            file.write(f"Authority Patterns: {len(self.authority_patterns):,}\n")
            file.write(f"Deadline Patterns: {len(self.deadline_patterns):,}\n")
            file.write(f"Processing Errors: {self.error_count:,}\n\n")

            # Discount type breakdown
            if self.discount_patterns:
                file.write("DISCOUNT TYPE BREAKDOWN\n")
                file.write("-" * 30 + "\n")
                discount_types: dict[str, int] = {}
                for pattern in self.discount_patterns:
                    dtype = pattern["type"]
                    discount_types[dtype] = discount_types.get(dtype, 0) + 1

                for dtype, count in sorted(discount_types.items(), key=lambda x: x[1], reverse=True):
                    file.write(f"{dtype}: {count:,}\n")
                file.write("\n")

            # Authority breakdown
            if self.authority_patterns:
                file.write("TOP AUTHORITIES\n")
                file.write("-" * 30 + "\n")
                authorities: dict[str, int] = {}
                for pattern in self.authority_patterns:
                    auth = pattern["authority"]
                    authorities[auth] = authorities.get(auth, 0) + 1

                for auth, count in sorted(authorities.items(), key=lambda x: x[1], reverse=True)[:20]:
                    file.write(f"{auth}: {count:,}\n")

        self.stdout.write(f"  📊 Summary: {os.path.basename(summary_file)}")

    def print_progress_summary(self):
        """Print progress summary."""
        self.stdout.write(
            f"📊 Progress: {self.processed_count:,} processed | "
            f"{self.discount_count:,} discounts | {self.scholarship_count:,} scholarships | "
            f"{self.error_count:,} errors"
        )

    def print_final_summary(self):
        """Print final processing summary."""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("🎉 HISTORICAL NOTES PROCESSING COMPLETE")
        self.stdout.write("=" * 60)
        self.stdout.write(f"📊 Total Processed: {self.processed_count:,}")
        discount_pct = (self.discount_count / self.processed_count * 100) if self.processed_count > 0 else 0
        scholarship_pct = (self.scholarship_count / self.processed_count * 100) if self.processed_count > 0 else 0
        self.stdout.write(f"💰 Discount Patterns: {self.discount_count:,} ({discount_pct:.1f}%)")
        self.stdout.write(f"🎓 Scholarship Patterns: {self.scholarship_count:,} ({scholarship_pct:.1f}%)")
        self.stdout.write(f"👤 Authority Patterns: {len(self.authority_patterns):,}")
        self.stdout.write(f"📅 Deadline Patterns: {len(self.deadline_patterns):,}")
        self.stdout.write(f"❌ Processing Errors: {self.error_count:,}")

        # Update batch status
        self.batch_record.status = ARReconstructionBatch.BatchStatus.COMPLETED
        self.batch_record.processed_receipts = self.processed_count
        self.batch_record.successful_reconstructions = self.processed_count - self.error_count
        self.batch_record.completed_at = timezone.now()
        self.batch_record.save()

        self.stdout.write(f"✅ Batch {self.batch_record.batch_id} completed successfully")
