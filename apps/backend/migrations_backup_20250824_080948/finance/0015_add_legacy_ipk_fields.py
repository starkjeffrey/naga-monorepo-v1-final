# Generated migration for adding legacy IPK fields

from django.db import migrations, models


def extract_ipk_from_number(number_string):
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


def backfill_legacy_ipk_data(apps, schema_editor):
    """Backfill IPK fields from existing invoice/payment numbers."""
    Invoice = apps.get_model("finance", "Invoice")
    Payment = apps.get_model("finance", "Payment")
    LegacyReceiptMapping = apps.get_model("finance", "LegacyReceiptMapping")

    print("🔄 Backfilling legacy IPK data...")

    # Backfill LegacyReceiptMapping
    updated_mappings = 0
    try:
        for mapping in LegacyReceiptMapping.objects.select_related("generated_invoice").all():
            if mapping.generated_invoice and hasattr(mapping.generated_invoice, "invoice_number"):
                ipk = extract_ipk_from_number(mapping.generated_invoice.invoice_number)
                if ipk:
                    mapping.legacy_ipk = ipk
                    mapping.save(update_fields=["legacy_ipk"])
                    updated_mappings += 1
    except Exception as e:
        print(f"⚠️ Error processing LegacyReceiptMapping: {e}")
        updated_mappings = 0

    print(f"✅ Updated {updated_mappings} LegacyReceiptMapping records")

    # Backfill Invoices
    updated_invoices = 0
    # Check if Invoice model has is_historical field before filtering
    try:
        invoice_queryset = Invoice.objects.all()
        # Try to access is_historical field
        if hasattr(Invoice, "_meta") and any(f.name == "is_historical" for f in Invoice._meta.get_fields()):
            invoice_queryset = invoice_queryset.filter(is_historical=True)

        for invoice in invoice_queryset:
            ipk = extract_ipk_from_number(invoice.invoice_number)
            if ipk:
                invoice.legacy_ipk = ipk
                invoice.save(update_fields=["legacy_ipk"])
                updated_invoices += 1
    except Exception as e:
        print(f"⚠️ Error processing invoices: {e}")
        updated_invoices = 0

    print(f"✅ Updated {updated_invoices} Invoice records")

    # Backfill Payments
    updated_payments = 0
    try:
        payment_queryset = Payment.objects.all()
        # Try to access is_historical_payment field
        if hasattr(Payment, "_meta") and any(f.name == "is_historical_payment" for f in Payment._meta.get_fields()):
            payment_queryset = payment_queryset.filter(is_historical_payment=True)

        for payment in payment_queryset:
            ipk = extract_ipk_from_number(payment.payment_reference)
            if ipk:
                payment.legacy_ipk = ipk
                payment.save(update_fields=["legacy_ipk"])
                updated_payments += 1
    except Exception as e:
        print(f"⚠️ Error processing payments: {e}")
        updated_payments = 0

    print(f"✅ Updated {updated_payments} Payment records")


def reverse_backfill_legacy_ipk_data(apps, schema_editor):
    """Reverse migration - clear IPK fields."""
    Invoice = apps.get_model("finance", "Invoice")
    Payment = apps.get_model("finance", "Payment")
    LegacyReceiptMapping = apps.get_model("finance", "LegacyReceiptMapping")

    # Clear IPK fields
    Invoice.objects.filter(legacy_ipk__isnull=False).update(legacy_ipk=None)
    Payment.objects.filter(legacy_ipk__isnull=False).update(legacy_ipk=None)
    LegacyReceiptMapping.objects.filter(legacy_ipk__isnull=False).update(legacy_ipk=None)


class Migration(migrations.Migration):
    dependencies = [
        ("finance", "0014_add_ar_reconstruction_system"),
    ]

    operations = [
        # Add legacy_ipk field to LegacyReceiptMapping
        migrations.AddField(
            model_name="legacyreceiptmapping",
            name="legacy_ipk",
            field=models.IntegerField(
                help_text="Original IPK primary key from receipt_headers - TRUE unique identifier",
                null=True,  # Allow null initially for backfill
                verbose_name="Legacy IPK",
            ),
        ),
        # Add legacy_ipk field to Invoice
        migrations.AddField(
            model_name="invoice",
            name="legacy_ipk",
            field=models.IntegerField(
                blank=True,
                help_text="Original IPK primary key - TRUE unique identifier",
                null=True,
                verbose_name="Legacy IPK",
            ),
        ),
        # Add legacy_ipk field to Payment
        migrations.AddField(
            model_name="payment",
            name="legacy_ipk",
            field=models.IntegerField(
                blank=True,
                help_text="Original IPK primary key - TRUE unique identifier",
                null=True,
                verbose_name="Legacy IPK",
            ),
        ),
        # Backfill existing data
        migrations.RunPython(backfill_legacy_ipk_data, reverse_backfill_legacy_ipk_data),
        # Make legacy_ipk non-null for LegacyReceiptMapping (after backfill)
        migrations.AlterField(
            model_name="legacyreceiptmapping",
            name="legacy_ipk",
            field=models.IntegerField(
                help_text="Original IPK primary key from receipt_headers - TRUE unique identifier",
                verbose_name="Legacy IPK",
            ),
        ),
        # Remove old unique constraint
        migrations.AlterUniqueTogether(
            name="legacyreceiptmapping",
            unique_together=set(),
        ),
        # Add new unique constraint on IPK
        migrations.AlterUniqueTogether(
            name="legacyreceiptmapping",
            unique_together={("legacy_ipk",)},
        ),
        # Update help text for legacy_receipt_number to clarify it's display only
        migrations.AlterField(
            model_name="legacyreceiptmapping",
            name="legacy_receipt_number",
            field=models.CharField(
                help_text="Original ReceiptNo from receipt_headers (display only)",
                max_length=20,
                verbose_name="Legacy Receipt Number",
            ),
        ),
        migrations.AlterField(
            model_name="invoice",
            name="legacy_receipt_number",
            field=models.CharField(
                blank=True,
                help_text="Original receipt number from legacy system (display only)",
                max_length=50,
                verbose_name="Legacy Receipt Number",
            ),
        ),
        migrations.AlterField(
            model_name="payment",
            name="legacy_receipt_reference",
            field=models.CharField(
                blank=True,
                help_text="Original receipt reference from legacy system (display only)",
                max_length=50,
                verbose_name="Legacy Receipt Reference",
            ),
        ),
    ]
