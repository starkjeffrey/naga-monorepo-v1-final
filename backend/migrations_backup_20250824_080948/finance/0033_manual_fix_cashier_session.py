"""
Manual migration to record the fixes applied to CashierSession.
This migration is a record of manual database changes already applied.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    """Record manual fixes to CashierSession model."""

    dependencies = [
        ("finance", "0032_remove_feepricing_finance_fee_is_mand_a2cb82_idx_and_more"),
    ]

    operations = [
        # This migration records manual changes already applied to the database
        # The following SQL was executed directly:
        #
        # ALTER TABLE finance_cashier_session
        # ADD COLUMN session_number VARCHAR(50),
        # ADD COLUMN opened_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        # ADD COLUMN closed_at TIMESTAMP WITH TIME ZONE,
        # ADD COLUMN opening_balance NUMERIC(10,2) DEFAULT 0,
        # ADD COLUMN closing_balance NUMERIC(10,2),
        # ADD COLUMN expected_balance NUMERIC(10,2),
        # ADD COLUMN is_active BOOLEAN DEFAULT FALSE;
        #
        # UPDATE finance_cashier_session SET session_number = 'CS-' || LPAD(id::text, 6, '0');
        # ALTER TABLE finance_cashier_session ADD CONSTRAINT finance_cashier_session_session_number_unique UNIQUE (session_number);
        migrations.RunSQL(
            sql=[
                # This is a no-op since changes were already applied manually
                "SELECT 1;",
            ],
            reverse_sql=[
                # Reverse operation if needed
                "SELECT 1;",
            ],
            state_operations=[
                # Tell Django about the state changes
                migrations.AddField(
                    model_name="cashiersession",
                    name="session_number",
                    field=models.CharField(
                        max_length=50,
                        unique=True,
                        verbose_name="Session Number",
                    ),
                ),
                migrations.AddField(
                    model_name="cashiersession",
                    name="opened_at",
                    field=models.DateTimeField(
                        verbose_name="Opened At",
                    ),
                ),
                migrations.AddField(
                    model_name="cashiersession",
                    name="closed_at",
                    field=models.DateTimeField(
                        blank=True,
                        null=True,
                        verbose_name="Closed At",
                    ),
                ),
                migrations.AddField(
                    model_name="cashiersession",
                    name="opening_balance",
                    field=models.DecimalField(
                        decimal_places=2,
                        max_digits=10,
                        verbose_name="Opening Balance",
                    ),
                ),
                migrations.AddField(
                    model_name="cashiersession",
                    name="closing_balance",
                    field=models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=10,
                        null=True,
                        verbose_name="Closing Balance",
                    ),
                ),
                migrations.AddField(
                    model_name="cashiersession",
                    name="expected_balance",
                    field=models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=10,
                        null=True,
                        verbose_name="Expected Balance",
                    ),
                ),
                migrations.AddField(
                    model_name="cashiersession",
                    name="is_active",
                    field=models.BooleanField(
                        default=False,
                        verbose_name="Is Active",
                    ),
                ),
            ],
        ),
    ]
