"""Add performance indexes for invoice admin handling 90,000+ records."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("finance", "0021_add_scholarship_reconciliation_support"),
    ]

    operations = [
        # Add composite index for common query patterns
        migrations.AddIndex(
            model_name="invoice",
            index=models.Index(
                fields=["status", "issue_date", "-id"],
                name="finance_inv_status_issue_idx",
            ),
        ),
        # Add index for student lookups (very common in admin)
        migrations.AddIndex(
            model_name="invoice",
            index=models.Index(
                fields=["student", "term", "-issue_date"],
                name="finance_inv_student_term_idx",
            ),
        ),
        # Add index for overdue invoice queries
        migrations.AddIndex(
            model_name="invoice",
            index=models.Index(
                fields=["status", "due_date"],
                name="finance_inv_overdue_idx",
                condition=models.Q(status="OVERDUE") | models.Q(status="SENT"),
            ),
        ),
        # Add index for amount due calculations
        migrations.AddIndex(
            model_name="invoice",
            index=models.Index(
                fields=["total_amount", "paid_amount"],
                name="finance_inv_amounts_idx",
            ),
        ),
        # Add index for invoice number lookups (should already be unique)
        # Commenting out as invoice_number should have unique constraint
        # migrations.AddIndex(
        #     model_name='invoice',
        #     index=models.Index(
        #         fields=['invoice_number'],
        #         name='finance_inv_number_idx',
        #     ),
        # ),
        # Add indexes for line items if not already present
        migrations.AddIndex(
            model_name="invoicelineitem",
            index=models.Index(
                fields=["invoice", "line_item_type"],
                name="finance_line_inv_type_idx",
            ),
        ),
        # Add index for enrollment lookups on line items
        migrations.AddIndex(
            model_name="invoicelineitem",
            index=models.Index(
                fields=["enrollment"],
                name="finance_line_enrollment_idx",
                condition=models.Q(enrollment__isnull=False),
            ),
        ),
    ]
