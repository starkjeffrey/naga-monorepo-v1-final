#!/usr/bin/env python
"""
Incremental CSV loader for legacy receipt data.

This script can load new CSV data into Django models while:
1. Finding the last used IPK in the system
2. Only processing new records (IPK > last processed)
3. Maintaining IPK uniqueness constraints
"""

import csv
import os
import sys
from pathlib import Path
from typing import Any

import django

# Add the backend directory to Python path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from django.db import models, transaction

from apps.finance.models import Invoice, Payment
from apps.finance.models.ar_reconstruction import LegacyReceiptMapping


class IncrementalCSVLoader:
    """Loads CSV data incrementally based on IPK tracking."""

    def __init__(self):
        self.last_processed_ipk = self.get_last_processed_ipk()
        self.new_records_count = 0
        self.skipped_records_count = 0
        self.error_records_count = 0

    def get_last_processed_ipk(self) -> int:
        """Get the highest IPK currently in the system."""
        max_ipks = []

        # Check LegacyReceiptMapping
        mapping_max = LegacyReceiptMapping.objects.aggregate(max_ipk=models.Max("legacy_ipk"))["max_ipk"]
        if mapping_max:
            max_ipks.append(mapping_max)

        # Check Invoices
        invoice_max = Invoice.objects.filter(legacy_ipk__isnull=False).aggregate(max_ipk=models.Max("legacy_ipk"))[
            "max_ipk"
        ]
        if invoice_max:
            max_ipks.append(invoice_max)

        # Check Payments
        payment_max = Payment.objects.filter(legacy_ipk__isnull=False).aggregate(max_ipk=models.Max("legacy_ipk"))[
            "max_ipk"
        ]
        if payment_max:
            max_ipks.append(payment_max)

        return max(max_ipks) if max_ipks else 0

    def should_process_record(self, record: dict[str, Any]) -> bool:
        """Determine if a record should be processed based on IPK."""
        try:
            ipk = int(record.get("IPK", 0))
            return ipk > self.last_processed_ipk
        except (ValueError, TypeError):
            return False

    def load_csv_file(self, csv_path: str) -> None:
        """Load CSV file and process only new records."""
        print(f"🔄 Loading CSV: {csv_path}")
        print(f"📊 Last processed IPK: {self.last_processed_ipk}")

        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        with open(csv_path, encoding="utf-8") as file:
            # Detect CSV format
            sample = file.read(1024)
            file.seek(0)

            # Try different delimiters
            sniffer = csv.Sniffer()
            delimiter = sniffer.sniff(sample).delimiter

            reader = csv.DictReader(file, delimiter=delimiter)

            # Validate required columns
            required_columns = ["IPK", "ReceiptNo", "ReceiptID"]
            missing_columns = [col for col in required_columns if col not in reader.fieldnames]
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")

            print(f"📋 Available columns: {reader.fieldnames}")

            # Process records
            for row_num, record in enumerate(reader, start=2):  # Start at 2 for header
                try:
                    if self.should_process_record(record):
                        self.process_record(record)
                        self.new_records_count += 1
                    else:
                        self.skipped_records_count += 1

                    # Progress reporting
                    if (self.new_records_count + self.skipped_records_count) % 1000 == 0:
                        print(f"📈 Processed {self.new_records_count + self.skipped_records_count:,} records...")

                except Exception as e:
                    print(f"❌ Error processing row {row_num}: {e}")
                    print(f"   Record: {record}")
                    self.error_records_count += 1

    def process_record(self, record: dict[str, Any]) -> None:
        """Process a single CSV record using the smart batch processor logic."""
        # Import here to avoid circular imports
        from apps.finance.management.commands.smart_batch_processor import (
            Command as BatchProcessor,
        )

        # Create a temporary batch processor instance
        processor = BatchProcessor()

        # Initialize processor with minimal setup
        processor.batch_id = f"incremental_{record.get('IPK')}"
        processor.notes_processor = processor._get_notes_processor()

        # Create or get batch record for tracking
        from apps.finance.models.ar_reconstruction import ARReconstructionBatch

        batch_record, _created = ARReconstructionBatch.objects.get_or_create(
            batch_id=processor.batch_id,
            defaults={
                "term_id": record.get("TermID", "INCREMENTAL"),
                "processing_mode": ARReconstructionBatch.ProcessingMode.AUTOMATED,
                "status": ARReconstructionBatch.BatchStatus.PROCESSING,
                "total_receipts": 1,
            },
        )
        processor.batch_record = batch_record

        # Process the individual record
        try:
            with transaction.atomic():
                processor.process_individual_receipt(record)
                batch_record.status = ARReconstructionBatch.BatchStatus.COMPLETED
                batch_record.save()
        except Exception as e:
            batch_record.status = ARReconstructionBatch.BatchStatus.FAILED
            batch_record.save()
            raise e

    def print_summary(self) -> None:
        """Print processing summary."""
        print("\n" + "=" * 60)
        print("📊 INCREMENTAL CSV LOAD SUMMARY")
        print("=" * 60)
        print(f"📈 Last processed IPK: {self.last_processed_ipk:,}")
        print(f"✅ New records processed: {self.new_records_count:,}")
        print(f"⏭️  Records skipped (already processed): {self.skipped_records_count:,}")
        print(f"❌ Records with errors: {self.error_records_count:,}")

        if self.new_records_count > 0:
            new_max_ipk = self.get_last_processed_ipk()
            print(f"📊 New maximum IPK: {new_max_ipk:,}")
            print(f"📈 IPK range processed: {self.last_processed_ipk + 1:,} to {new_max_ipk:,}")


def main():
    """Main execution function."""
    import argparse

    parser = argparse.ArgumentParser(description="Incremental CSV loader for legacy data")
    parser.add_argument("csv_file", help="Path to CSV file to load")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without making changes",
    )

    args = parser.parse_args()

    print("🚀 Starting incremental CSV load...")

    loader = IncrementalCSVLoader()

    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
        # Add dry run logic here
    else:
        loader.load_csv_file(args.csv_file)

    loader.print_summary()
    print("✅ Incremental CSV load completed!")


if __name__ == "__main__":
    main()
