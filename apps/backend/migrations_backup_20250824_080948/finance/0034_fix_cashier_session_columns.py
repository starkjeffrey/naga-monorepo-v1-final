# Generated manually to fix CashierSession column mismatches

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("finance", "0033_manual_fix_cashier_session"),
    ]

    operations = [
        # First, backup any existing data from old columns before dropping them
        migrations.RunSQL(
            sql="""
            -- Create backup table for old cashier session data
            CREATE TABLE IF NOT EXISTS finance_cashier_session_backup AS
            SELECT id, date, opening_time, closing_time, status,
                   opening_cash, closing_cash, expected_cash, variance
            FROM finance_cashier_session
            WHERE date IS NOT NULL OR opening_time IS NOT NULL OR status IS NOT NULL;
            """,
            reverse_sql="DROP TABLE IF EXISTS finance_cashier_session_backup;",
        ),
        # Drop the old columns that don't match the model
        migrations.RunSQL(
            sql=[
                "ALTER TABLE finance_cashier_session DROP COLUMN IF EXISTS date;",
                "ALTER TABLE finance_cashier_session DROP COLUMN IF EXISTS opening_time;",
                "ALTER TABLE finance_cashier_session DROP COLUMN IF EXISTS closing_time;",
                "ALTER TABLE finance_cashier_session DROP COLUMN IF EXISTS status;",
                "ALTER TABLE finance_cashier_session DROP COLUMN IF EXISTS opening_cash;",
                "ALTER TABLE finance_cashier_session DROP COLUMN IF EXISTS closing_cash;",
                "ALTER TABLE finance_cashier_session DROP COLUMN IF EXISTS expected_cash;",
                "ALTER TABLE finance_cashier_session DROP COLUMN IF EXISTS variance;",
            ],
            reverse_sql=[
                "ALTER TABLE finance_cashier_session ADD COLUMN date DATE;",
                "ALTER TABLE finance_cashier_session ADD COLUMN opening_time TIMESTAMPTZ;",
                "ALTER TABLE finance_cashier_session ADD COLUMN closing_time TIMESTAMPTZ;",
                "ALTER TABLE finance_cashier_session ADD COLUMN status VARCHAR(20);",
                "ALTER TABLE finance_cashier_session ADD COLUMN opening_cash DECIMAL(10, 2);",
                "ALTER TABLE finance_cashier_session ADD COLUMN closing_cash DECIMAL(10, 2);",
                "ALTER TABLE finance_cashier_session ADD COLUMN expected_cash DECIMAL(10, 2);",
                "ALTER TABLE finance_cashier_session ADD COLUMN variance DECIMAL(10, 2);",
            ],
        ),
        # Ensure the correct columns exist with proper types
        # Note: These should already exist from initial migration, but adding them
        # here ensures they match the model exactly
        migrations.RunSQL(
            sql=[
                """
                DO $$
                BEGIN
                    -- Check if is_active column exists, if not add it
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'finance_cashier_session'
                        AND column_name = 'is_active'
                    ) THEN
                        ALTER TABLE finance_cashier_session
                        ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE;
                    END IF;
                END $$;
                """
            ],
            reverse_sql="ALTER TABLE finance_cashier_session DROP COLUMN IF EXISTS is_active;",
        ),
    ]
