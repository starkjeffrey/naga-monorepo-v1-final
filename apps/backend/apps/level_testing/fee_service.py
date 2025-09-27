"""Level Testing Fee Service - Flexible fee management with finance integration.

This service implements the user requirements for:
- Configurable price list with internal codes, human names, and prices
- Local/foreign rate differentiation
- G/L account mapping for financial reporting
- Integration with existing finance app fee structure

Per user requirements: "All fees should be in a configurable price list with
internal codes, human names, and prices. Support local/foreign rate
differentiation and G/L account mapping."
"""

import logging
from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from apps.finance.models import FeeGLMapping, FeePricing, FeeType, GLAccount
from apps.level_testing.constants import (
    DEFAULT_TEST_FEE_AMOUNT,
    TEST_FEE_CURRENCY,
    TEST_FEE_NAMES,
    GLAccountCode,
    TestFeeCode,
)

logger = logging.getLogger(__name__)


class LevelTestingFeeService:
    """Service for managing level testing fees with configurable pricing.

    Integrates with finance app's FeePricing system to provide flexible
    fee management with local/foreign rates and G/L account mapping.
    """

    def __init__(self):
        """Initialize the fee service."""
        self.gl_account_cache = {}

    def calculate_test_fee(
        self,
        fee_code: str = TestFeeCode.PLACEMENT_TEST,
        is_foreign: bool = False,
        currency: str = TEST_FEE_CURRENCY,
    ) -> dict[str, Any]:
        """Calculate test fee amount based on fee code and student type.

        Per user requirements: Supports local/foreign rate differentiation
        with configurable pricing.

        Args:
            fee_code: Internal fee code (e.g., TestFeeCode.PLACEMENT_TEST)
            is_foreign: Whether the student is international/foreign
            currency: Currency code for the fee

        Returns:
            Dictionary with fee calculation details
        """
        try:
            # Get fee pricing from finance app
            fee_pricing = self._get_fee_pricing(fee_code, currency)

            if not fee_pricing:
                # Fallback to default pricing if no specific pricing found
                fee_pricing = self._create_default_fee_pricing(fee_code, currency)

            # Get G/L account mapping
            gl_mapping = self._get_gl_mapping(fee_code)

            # Get amount based on student type
            amount = fee_pricing.get_amount_for_student(is_foreign)

            result = {
                "fee_code": fee_code,
                "fee_name": TEST_FEE_NAMES.get(fee_code, fee_code),
                "amount": amount,
                "currency": fee_pricing.currency,
                "student_type": "foreign" if is_foreign else "local",
                "is_foreign": is_foreign,
                "gl_revenue_account": (gl_mapping.revenue_account.account_code if gl_mapping else None),  # type: ignore[attr-defined]
                "gl_receivable_account": (
                    gl_mapping.receivable_account.account_code
                    if gl_mapping and gl_mapping.receivable_account
                    else None
                ),
                "effective_date": fee_pricing.effective_date,
                "is_active": fee_pricing.is_active,
            }

            logger.info(
                "Calculated fee: %s = %s %s for %s student",
                fee_code,
                amount,
                fee_pricing.currency,
                "foreign" if is_foreign else "local",
            )

            return result

        except Exception as e:
            logger.exception("Error calculating test fee for %s: %s", fee_code, e)
            # Return fallback pricing
            return self._get_fallback_fee_calculation(fee_code, currency, is_foreign)

    def get_all_available_fees(self, is_foreign: bool = False) -> list[dict[str, Any]]:
        """Get all available level testing fees for a student type.

        Args:
            is_foreign: Whether the student is international/foreign

        Returns:
            List of available fees with pricing information
        """
        available_fees = []

        for fee_code in [
            TestFeeCode.PLACEMENT_TEST,
            TestFeeCode.RETEST_FEE,
            TestFeeCode.LATE_REGISTRATION,
            TestFeeCode.RUSH_PROCESSING,
            TestFeeCode.APPLICATION_PROCESSING,
            TestFeeCode.MAKEUP_TEST,
            TestFeeCode.REMOTE_TEST,
            TestFeeCode.SPECIAL_ACCOMMODATION,
        ]:
            try:
                fee_info = self.calculate_test_fee(fee_code, is_foreign)
                available_fees.append(fee_info)
            except Exception as e:
                logger.warning("Could not get pricing for %s: %s", fee_code, e)

        return available_fees

    def create_fee_pricing(
        self,
        fee_code: str,
        fee_name: str,
        local_amount: Decimal,
        foreign_amount: Decimal | None = None,
        currency: str = TEST_FEE_CURRENCY,
        effective_date=None,
    ) -> FeePricing:
        """Create new fee pricing configuration.

        Args:
            fee_code: Internal fee code
            fee_name: Human-readable fee name
            local_amount: Fee amount for local students
            foreign_amount: Fee amount for foreign students (defaults to local_amount)
            currency: Currency code
            effective_date: When pricing becomes effective

        Returns:
            Created FeePricing instance
        """
        try:
            with transaction.atomic():
                # Create fee pricing with separate local/foreign amounts
                fee_pricing = FeePricing.objects.create(
                    name=fee_name,
                    fee_type=FeeType.APPLICATION,
                    local_amount=local_amount,
                    foreign_amount=foreign_amount or local_amount,
                    currency=currency,
                    effective_date=effective_date or timezone.now().date(),
                    description=f"Level testing fee: {fee_name}",
                )

                logger.info(
                    "Created fee pricing: %s = local:%s, foreign:%s %s",
                    fee_code,
                    local_amount,
                    foreign_amount or local_amount,
                    currency,
                )

                return fee_pricing

        except Exception as e:
            logger.exception("Error creating fee pricing for %s: %s", fee_code, e)
            msg = f"Could not create fee pricing: {e}"
            raise ValidationError(msg) from e

    def setup_gl_mapping(
        self,
        fee_code: str,
        revenue_account_code: str,
        receivable_account_code: str | None = None,
    ) -> FeeGLMapping:
        """Set up G/L account mapping for a fee code.

        Args:
            fee_code: Internal fee code
            revenue_account_code: G/L account code for revenue
            receivable_account_code: G/L account code for receivables (optional)

        Returns:
            Created FeeGLMapping instance
        """
        try:
            with transaction.atomic():
                # Get G/L accounts
                revenue_account = GLAccount.objects.get(account_code=revenue_account_code)
                receivable_account = None
                if receivable_account_code:
                    receivable_account = GLAccount.objects.get(account_code=receivable_account_code)

                # Create mapping
                mapping = FeeGLMapping.objects.create(
                    fee_type=FeeType.APPLICATION,
                    fee_code=fee_code,
                    revenue_account=revenue_account,
                    receivable_account=receivable_account,
                    effective_date=timezone.now().date(),
                )

                logger.info(
                    "Created G/L mapping: %s → %s",
                    fee_code,
                    revenue_account_code,
                )

                return mapping

        except GLAccount.DoesNotExist as e:
            msg = f"G/L account not found: {revenue_account_code}"
            raise ValidationError(msg) from e
        except Exception as e:
            logger.exception("Error creating G/L mapping for %s: %s", fee_code, e)
            msg = f"Could not create G/L mapping: {e}"
            raise ValidationError(msg) from e

    def initialize_default_fee_structure(self) -> None:
        """Initialize default fee structure for level testing.

        Creates default G/L accounts and fee configurations
        based on constants defined in the level testing app.
        """
        try:
            with transaction.atomic():
                logger.info("Initializing default level testing fee structure...")

                # Create G/L accounts
                self._create_default_gl_accounts()

                # Create default fee pricing
                self._create_default_fee_pricing_configs()

                # Create G/L mappings
                self._create_default_gl_mappings()

                logger.info("Default fee structure initialized successfully")

        except Exception as e:
            logger.exception("Error initializing default fee structure: %s", e)
            raise

    def _get_fee_pricing(self, fee_code: str, currency: str) -> FeePricing | None:
        """Get active fee pricing for fee code."""
        try:
            fee_name = TEST_FEE_NAMES.get(fee_code, fee_code)

            return (
                FeePricing.objects.filter(
                    name=fee_name,
                    currency=currency,
                    effective_date__lte=timezone.now().date(),
                )
                .filter(models.Q(end_date__isnull=True) | models.Q(end_date__gt=timezone.now().date()))
                .order_by("-effective_date")
                .first()
            )

        except Exception as e:
            logger.warning("Error getting fee pricing for %s: %s", fee_code, e)
            return None

    def _get_gl_mapping(self, fee_code: str) -> FeeGLMapping | None:
        """Get active G/L mapping for fee code."""
        try:
            return (
                FeeGLMapping.objects.filter(
                    fee_code=fee_code,
                    effective_date__lte=timezone.now().date(),
                )
                .filter(models.Q(end_date__isnull=True) | models.Q(end_date__gt=timezone.now().date()))
                .order_by("-effective_date")
                .first()
            )

        except Exception as e:
            logger.warning("Error getting G/L mapping for %s: %s", fee_code, e)
            return None

    def _create_default_fee_pricing(self, fee_code: str, currency: str) -> FeePricing:
        """Create default fee pricing as fallback."""
        try:
            # Use default amount for both local and foreign students
            base_amount = DEFAULT_TEST_FEE_AMOUNT

            return FeePricing.objects.create(
                name=TEST_FEE_NAMES.get(fee_code, fee_code),
                fee_type=FeeType.APPLICATION,
                local_amount=base_amount,
                foreign_amount=base_amount,  # Same amount for both by default
                currency=currency,
                effective_date=timezone.now().date(),
                description=f"Default pricing for {fee_code}",
            )

        except Exception as e:
            logger.exception("Error creating default fee pricing: %s", e)
            raise

    def _get_fallback_fee_calculation(self, fee_code: str, currency: str, is_foreign: bool = False) -> dict[str, Any]:
        """Get fallback fee calculation when normal calculation fails."""
        return {
            "fee_code": fee_code,
            "fee_name": TEST_FEE_NAMES.get(fee_code, fee_code),
            "amount": DEFAULT_TEST_FEE_AMOUNT,
            "currency": currency,
            "student_type": "foreign" if is_foreign else "local",
            "is_foreign": is_foreign,
            "gl_revenue_account": None,
            "gl_receivable_account": None,
            "effective_date": timezone.now().date(),
            "is_active": True,
            "is_fallback": True,
        }

    def _create_default_gl_accounts(self) -> None:
        """Create default G/L accounts for level testing."""
        accounts = [
            (
                GLAccountCode.TEST_FEE_REVENUE,
                "Level Testing Fee Revenue",
                GLAccount.AccountType.REVENUE,
                GLAccount.AccountCategory.OPERATING_REVENUE,
            ),
            (
                GLAccountCode.LATE_FEE_REVENUE,
                "Late Registration Fee Revenue",
                GLAccount.AccountType.REVENUE,
                GLAccount.AccountCategory.OPERATING_REVENUE,
            ),
            (
                GLAccountCode.ADMIN_FEE_REVENUE,
                "Administrative Fee Revenue",
                GLAccount.AccountType.REVENUE,
                GLAccount.AccountCategory.OPERATING_REVENUE,
            ),
            (
                GLAccountCode.TEST_ADMINISTRATION_EXPENSE,
                "Test Administration Expense",
                GLAccount.AccountType.EXPENSE,
                GLAccount.AccountCategory.OPERATING_EXPENSE,
            ),
            (
                GLAccountCode.PREPAID_TEST_FEES,
                "Prepaid Test Fees",
                GLAccount.AccountType.ASSET,
                GLAccount.AccountCategory.CURRENT_ASSET,
            ),
        ]

        for code, name, account_type, category in accounts:
            GLAccount.objects.get_or_create(
                account_code=code,
                defaults={
                    "account_name": name,
                    "account_type": account_type,
                    "account_category": category,
                    "is_active": True,
                    "description": f"Default account for level testing: {name}",
                },
            )

    def _create_default_fee_pricing_configs(self) -> None:
        """Create default fee pricing configurations."""
        default_fees = [
            (TestFeeCode.PLACEMENT_TEST, "Placement Test", DEFAULT_TEST_FEE_AMOUNT),
            (TestFeeCode.RETEST_FEE, "Retest Fee", DEFAULT_TEST_FEE_AMOUNT),
            (
                TestFeeCode.LATE_REGISTRATION,
                "Late Registration Fee",
                DEFAULT_TEST_FEE_AMOUNT * Decimal("2"),
            ),
            (
                TestFeeCode.RUSH_PROCESSING,
                "Rush Processing Fee",
                DEFAULT_TEST_FEE_AMOUNT * Decimal("1.5"),
            ),
        ]

        for _fee_code, fee_name, local_amount in default_fees:
            # Foreign students pay 50% more by default
            foreign_amount = local_amount * Decimal("1.5")

            FeePricing.objects.get_or_create(
                name=fee_name,
                fee_type=FeeType.APPLICATION,
                effective_date=timezone.now().date(),
                defaults={
                    "local_amount": local_amount,
                    "foreign_amount": foreign_amount,
                    "currency": TEST_FEE_CURRENCY,
                    "description": f"Default {fee_name.lower()}",
                },
            )

    def _create_default_gl_mappings(self) -> None:
        """Create default G/L mappings for level testing fees."""
        mappings = [
            (TestFeeCode.PLACEMENT_TEST, GLAccountCode.TEST_FEE_REVENUE),
            (TestFeeCode.RETEST_FEE, GLAccountCode.TEST_FEE_REVENUE),
            (TestFeeCode.LATE_REGISTRATION, GLAccountCode.LATE_FEE_REVENUE),
            (TestFeeCode.RUSH_PROCESSING, GLAccountCode.ADMIN_FEE_REVENUE),
            (TestFeeCode.APPLICATION_PROCESSING, GLAccountCode.ADMIN_FEE_REVENUE),
            (TestFeeCode.MAKEUP_TEST, GLAccountCode.TEST_FEE_REVENUE),
            (TestFeeCode.REMOTE_TEST, GLAccountCode.TEST_FEE_REVENUE),
            (TestFeeCode.SPECIAL_ACCOMMODATION, GLAccountCode.ADMIN_FEE_REVENUE),
        ]

        for fee_code, revenue_account_code in mappings:
            try:
                revenue_account = GLAccount.objects.get(account_code=revenue_account_code)

                FeeGLMapping.objects.get_or_create(
                    fee_code=fee_code,
                    effective_date=timezone.now().date(),
                    defaults={
                        "fee_type": FeeType.APPLICATION,
                        "revenue_account": revenue_account,
                        "receivable_account": None,
                    },
                )
            except GLAccount.DoesNotExist:
                logger.warning("G/L account not found for mapping: %s", revenue_account_code)


# Note: PricingTier model has been deprecated in favor of FeePricing's direct local/foreign amounts
