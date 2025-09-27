#!/usr/bin/env python
"""
Backfill legacy IPK fields from existing invoice/payment numbers.

This script extracts IPK values from AR-/PAY- numbers and populates
the new legacy_ipk fields in all relevant models.
"""

import os
import sys
from pathlib import Path

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


def extract_ipk_from_number(number_string: str) -> int | None:
    """Extract IPK from AR-12345 or PAY-12345 format."""
    if not number_string:
        return None

    try:
        # Handle AR-12345 or PAY-12345 format
        if number_string.startswith(("AR-", "PAY-")):
            return int(number_string.split("-", 1)[1])
        # Handle pure number format
        return int(number_string)
    except (ValueError, IndexError):
        return None


def backfill_legacy_receipt_mapping():
    """Backfill IPK in LegacyReceiptMapping from invoice numbers."""
    print("🔄 Backfilling LegacyReceiptMapping.legacy_ipk...")

    updated_count = 0
    failed_count = 0

    # Process all mappings that don't have IPK set
    mappings = LegacyReceiptMapping.objects.select_related("generated_invoice").all()

    for mapping in mappings:
        try:
            # Extract IPK from invoice number
            ipk = extract_ipk_from_number(mapping.generated_invoice.invoice_number)
            if ipk:
                mapping.legacy_ipk = ipk
                mapping.save(update_fields=["legacy_ipk"])
                updated_count += 1
            else:
                print(f"❌ Failed to extract IPK from: {mapping.generated_invoice.invoice_number}")
                failed_count += 1

        except Exception as e:
            print(f"❌ Error processing mapping {mapping.id}: {e}")
            failed_count += 1

    print(f"✅ Updated {updated_count} LegacyReceiptMapping records")
    print(f"❌ Failed {failed_count} records")


def backfill_invoices():
    """Backfill IPK in Invoice model from invoice numbers."""
    print("🔄 Backfilling Invoice.legacy_ipk...")

    updated_count = 0
    failed_count = 0

    # Process historical invoices that don't have IPK set
    invoices = Invoice.objects.filter(is_historical=True, legacy_ipk__isnull=True)

    for invoice in invoices:
        try:
            # Extract IPK from invoice number
            ipk = extract_ipk_from_number(invoice.invoice_number)
            if ipk:
                invoice.legacy_ipk = ipk
                invoice.save(update_fields=["legacy_ipk"])
                updated_count += 1
            else:
                print(f"❌ Failed to extract IPK from: {invoice.invoice_number}")
                failed_count += 1

        except Exception as e:
            print(f"❌ Error processing invoice {invoice.id}: {e}")
            failed_count += 1

    print(f"✅ Updated {updated_count} Invoice records")
    print(f"❌ Failed {failed_count} records")


def backfill_payments():
    """Backfill IPK in Payment model from payment references."""
    print("🔄 Backfilling Payment.legacy_ipk...")

    updated_count = 0
    failed_count = 0

    # Process historical payments that don't have IPK set
    payments = Payment.objects.filter(is_historical_payment=True, legacy_ipk__isnull=True)

    for payment in payments:
        try:
            # Extract IPK from payment reference
            ipk = extract_ipk_from_number(payment.payment_reference)
            if ipk:
                payment.legacy_ipk = ipk
                payment.save(update_fields=["legacy_ipk"])
                updated_count += 1
            else:
                print(f"❌ Failed to extract IPK from: {payment.payment_reference}")
                failed_count += 1

        except Exception as e:
            print(f"❌ Error processing payment {payment.id}: {e}")
            failed_count += 1

    print(f"✅ Updated {updated_count} Payment records")
    print(f"❌ Failed {failed_count} records")


def get_max_ipk():
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


def main():
    """Main execution function."""
    print("🚀 Starting legacy IPK backfill process...")

    with transaction.atomic():
        # Backfill existing data
        backfill_legacy_receipt_mapping()
        backfill_invoices()
        backfill_payments()

        # Report current max IPK
        max_ipk = get_max_ipk()
        print(f"📊 Maximum IPK in system: {max_ipk}")
        print(f"📈 Next IPK for new records: {max_ipk + 1}")

    print("✅ Legacy IPK backfill completed successfully!")


if __name__ == "__main__":
    main()
