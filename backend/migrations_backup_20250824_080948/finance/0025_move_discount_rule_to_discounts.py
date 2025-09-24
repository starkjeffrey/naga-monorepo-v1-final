# Migration to move DiscountRule from ar_reconstruction to discounts module

from django.db import migrations


class Migration(migrations.Migration):
    """
    This migration moves the DiscountRule model from ar_reconstruction.py to discounts.py.

    Since the model is just being moved between files in the same app, and the
    db_table remains 'finance_discount_rule', no database changes are needed.

    The DiscountRule model should NOT be defined in ar_reconstruction.py because:
    1. The AR reconstruction system should only FOLLOW rules, not define them
    2. We want to test the real discount system logic, not bypass it
    3. Discount rules are a core finance concept, not specific to AR reconstruction
    """

    dependencies = [
        ("finance", "0024_update_discount_rule_json_fields"),
    ]

    operations = [
        # No database operations needed - this is just a code reorganization
        # The model has been moved from:
        #   apps/finance/models/ar_reconstruction.py
        # To:
        #   apps/finance/models/discounts.py
        #
        # All imports have been updated to reflect the new location.
    ]
