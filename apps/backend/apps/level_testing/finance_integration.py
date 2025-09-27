"""Finance integration for level testing test fees.

This module provides integration with the finance app for handling test fee
payments as external transactions. Follows clean architecture principles by
avoiding direct model imports from the finance app.

Key features:
- External fee transaction creation
- G/L account mapping for test fees
- Payment method handling
- Accounting report integration
- Clean dependency management
"""

import logging
from decimal import Decimal
from typing import Any

from django.utils import timezone

logger = logging.getLogger(__name__)


class TestFeeFinanceIntegrator:
    """Integrates test fee payments with the finance app.

    Handles creation of external transactions and proper G/L account mapping
    for test fees. Designed to work with the existing finance app structure
    without creating circular dependencies.
    """

    # G/L Account codes for test fees (these should match finance app configuration)
    GL_ACCOUNTS = {
        "TEST_FEE_REVENUE": "4100-01",  # Revenue account for test fees
        "CASH_ACCOUNT": "1100-01",  # Cash/bank account
        "ACCOUNTS_RECEIVABLE": "1200-01",  # A/R for unpaid fees
    }

    def __init__(self):
        """Initialize the finance integrator."""
        self.transaction_service = None
        self._initialize_services()

    def _initialize_services(self) -> None:
        """Initialize finance service references."""
        try:
            from apps.finance import services as _fin_services

            # Use Any to avoid strict attribute checks in core typecheck
            self.transaction_service = getattr(_fin_services, "ExternalTransactionService", None)
        except ImportError as e:
            logger.warning("Finance services not available: %s", e)
            # Continue without finance integration for development

    def create_test_fee_transaction(self, test_payment) -> dict[str, Any]:
        """Create a finance transaction for a test fee payment.

        Args:
            test_payment: TestPayment instance

        Returns:
            Dictionary with transaction details and success status
        """
        if not self.transaction_service:
            logger.warning("Finance service not available, creating mock transaction")
            return self._create_mock_transaction(test_payment)

        try:
            transaction_data = self._prepare_transaction_data(test_payment)

            # Create the transaction through finance service
            result = self.transaction_service.create_external_transaction(
                transaction_type="TEST_FEE",
                source_app="level_testing",
                source_id=test_payment.id,
                transaction_data=transaction_data,
            )

            if result.get("success"):
                # Update test payment with transaction reference
                test_payment.finance_transaction_id = result["transaction_id"]
                test_payment.save(update_fields=["finance_transaction_id"])

                logger.info(
                    "Created finance transaction %s for test payment %s",
                    result["transaction_id"],
                    test_payment.id,
                )

            return result

        except Exception as e:
            logger.exception("Failed to create test fee transaction: %s", e)
            return {"success": False, "error": str(e), "transaction_id": None}

    def _prepare_transaction_data(self, test_payment) -> dict[str, Any]:
        """Prepare transaction data for finance app.

        Args:
            test_payment: TestPayment instance

        Returns:
            Dictionary with structured transaction data
        """
        potential_student = test_payment.potential_student

        # Determine accounts based on payment status
        if test_payment.is_paid:
            debit_account = self.GL_ACCOUNTS["CASH_ACCOUNT"]
            credit_account = self.GL_ACCOUNTS["TEST_FEE_REVENUE"]
            transaction_date = test_payment.paid_at or timezone.now()
        else:
            debit_account = self.GL_ACCOUNTS["ACCOUNTS_RECEIVABLE"]
            credit_account = self.GL_ACCOUNTS["TEST_FEE_REVENUE"]
            transaction_date = timezone.now()

        return {
            "transaction_date": transaction_date,
            "description": f"Level Test Fee - {potential_student.full_name_eng}",
            "reference_number": potential_student.test_number,
            "amount": test_payment.amount,
            "currency": "USD",
            "payment_method": test_payment.payment_method,
            "customer_info": {
                "name": potential_student.full_name_eng,
                "phone": potential_student.phone_number,
                "email": potential_student.personal_email,
                "test_number": potential_student.test_number,
            },
            "journal_entries": [
                {
                    "account_code": debit_account,
                    "debit_amount": test_payment.amount,
                    "credit_amount": Decimal("0.00"),
                    "description": f"Test fee payment - {potential_student.test_number}",
                },
                {
                    "account_code": credit_account,
                    "debit_amount": Decimal("0.00"),
                    "credit_amount": test_payment.amount,
                    "description": f"Test fee revenue - {potential_student.test_number}",
                },
            ],
            "metadata": {
                "source_app": "level_testing",
                "source_model": "TestPayment",
                "source_id": test_payment.id,
                "potential_student_id": potential_student.id,
                "test_date": test_payment.created_at.date(),
            },
        }

    def _create_mock_transaction(self, test_payment) -> dict[str, Any]:
        """Create a mock transaction for development/testing.

        Args:
            test_payment: TestPayment instance

        Returns:
            Mock transaction result
        """
        mock_transaction_id = 90000 + test_payment.id  # Ensure unique ID

        logger.info(
            "Created mock finance transaction %s for test payment %s ($%s - %s)",
            mock_transaction_id,
            test_payment.id,
            test_payment.amount,
            test_payment.potential_student.full_name_eng,
        )

        return {
            "success": True,
            "transaction_id": mock_transaction_id,
            "message": "Mock transaction created for development",
            "gl_entries": [
                f"DR {self.GL_ACCOUNTS['CASH_ACCOUNT']} ${test_payment.amount}",
                f"CR {self.GL_ACCOUNTS['TEST_FEE_REVENUE']} ${test_payment.amount}",
            ],
        }

    def update_payment_transaction(
        self,
        test_payment,
        payment_received: bool = True,
    ) -> dict[str, Any]:
        """Update an existing transaction when payment status changes.

        Args:
            test_payment: TestPayment instance
            payment_received: Whether payment has been received

        Returns:
            Update result dictionary
        """
        if not test_payment.finance_transaction_id:
            logger.warning(
                "No finance transaction found for test payment %s",
                test_payment.id,
            )
            return {"success": False, "error": "No transaction to update"}

        if not self.transaction_service:
            logger.info(
                "Mock: Updated payment status for transaction %s",
                test_payment.finance_transaction_id,
            )
            return {"success": True, "message": "Mock update completed"}

        try:
            # Update the transaction through finance service
            return self.transaction_service.update_payment_status(
                transaction_id=test_payment.finance_transaction_id,
                payment_received=payment_received,
                payment_date=test_payment.paid_at,
                payment_method=test_payment.payment_method,
                received_by=test_payment.received_by,
            )

        except Exception as e:
            logger.exception("Failed to update payment transaction: %s", e)
            return {"success": False, "error": str(e)}

    def generate_test_fee_report(self, start_date, end_date) -> dict[str, Any]:
        """Generate a test fee report for accounting purposes.

        Args:
            start_date: Report start date
            end_date: Report end date

        Returns:
            Report data dictionary
        """
        from apps.level_testing.models import TestPayment

        # Get test payments in date range
        payments = TestPayment.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
        ).select_related("potential_student")

        report_data: dict[str, Any] = {
            "period": {
                "start_date": start_date,
                "end_date": end_date,
            },
            "summary": {
                "total_fees_charged": Decimal("0.00"),
                "total_fees_collected": Decimal("0.00"),
                "total_outstanding": Decimal("0.00"),
                "total_transactions": 0,
                "paid_transactions": 0,
                "unpaid_transactions": 0,
            },
            "payment_methods": {},
            "daily_breakdown": {},
            "gl_summary": {
                "revenue_account": self.GL_ACCOUNTS["TEST_FEE_REVENUE"],
                "cash_account": self.GL_ACCOUNTS["CASH_ACCOUNT"],
                "ar_account": self.GL_ACCOUNTS["ACCOUNTS_RECEIVABLE"],
            },
            "transactions": [],
        }

        # Process each payment
        for payment in payments:
            # Update summary totals
            report_data["summary"]["total_fees_charged"] += payment.amount
            report_data["summary"]["total_transactions"] += 1

            if payment.is_paid:
                report_data["summary"]["total_fees_collected"] += payment.amount
                report_data["summary"]["paid_transactions"] += 1
            else:
                report_data["summary"]["total_outstanding"] += payment.amount
                report_data["summary"]["unpaid_transactions"] += 1

            # Track payment methods
            method = payment.payment_method
            if method not in report_data["payment_methods"]:
                report_data["payment_methods"][method] = {
                    "count": 0,
                    "total_amount": Decimal("0.00"),
                }
            report_data["payment_methods"][method]["count"] += 1
            if payment.is_paid:
                report_data["payment_methods"][method]["total_amount"] += payment.amount

            # Daily breakdown
            date_key = payment.created_at.date().isoformat()
            if date_key not in report_data["daily_breakdown"]:
                report_data["daily_breakdown"][date_key] = {
                    "fees_charged": Decimal("0.00"),
                    "fees_collected": Decimal("0.00"),
                    "transaction_count": 0,
                }

            daily = report_data["daily_breakdown"][date_key]
            daily["fees_charged"] += payment.amount
            daily["transaction_count"] += 1
            if payment.is_paid:
                daily["fees_collected"] += payment.amount

            # Individual transaction details
            report_data["transactions"].append(
                {
                    "test_number": payment.potential_student.test_number,
                    "student_name": payment.potential_student.full_name_eng,
                    "amount": payment.amount,
                    "payment_method": payment.payment_method,
                    "is_paid": payment.is_paid,
                    "paid_date": payment.paid_at,
                    "finance_transaction_id": payment.finance_transaction_id,
                    "created_date": payment.created_at,
                },
            )

        logger.info(
            "Generated test fee report for %s to %s: %s transactions, $%s collected",
            start_date,
            end_date,
            report_data["summary"]["total_transactions"],
            report_data["summary"]["total_fees_collected"],
        )

        return report_data

    def export_gl_entries(self, start_date, end_date) -> list[dict[str, Any]]:
        """Export G/L entries for test fees in a format suitable for accounting software.

        Args:
            start_date: Export start date
            end_date: Export end date

        Returns:
            List of G/L entry dictionaries
        """
        report = self.generate_test_fee_report(start_date, end_date)
        gl_entries = []

        # Summary entries for the period
        if report["summary"]["total_fees_collected"] > 0:
            gl_entries.append(
                {
                    "date": end_date,
                    "account_code": self.GL_ACCOUNTS["CASH_ACCOUNT"],
                    "account_name": "Cash - Test Fees",
                    "debit_amount": report["summary"]["total_fees_collected"],
                    "credit_amount": Decimal("0.00"),
                    "description": f"Test fees collected {start_date} to {end_date}",
                    "reference": f"TEST-FEES-{start_date}-{end_date}",
                },
            )

            gl_entries.append(
                {
                    "date": end_date,
                    "account_code": self.GL_ACCOUNTS["TEST_FEE_REVENUE"],
                    "account_name": "Test Fee Revenue",
                    "debit_amount": Decimal("0.00"),
                    "credit_amount": report["summary"]["total_fees_collected"],
                    "description": f"Test fee revenue {start_date} to {end_date}",
                    "reference": f"TEST-FEES-{start_date}-{end_date}",
                },
            )

        if report["summary"]["total_outstanding"] > 0:
            gl_entries.append(
                {
                    "date": end_date,
                    "account_code": self.GL_ACCOUNTS["ACCOUNTS_RECEIVABLE"],
                    "account_name": "Accounts Receivable - Test Fees",
                    "debit_amount": report["summary"]["total_outstanding"],
                    "credit_amount": Decimal("0.00"),
                    "description": f"Outstanding test fees {start_date} to {end_date}",
                    "reference": f"TEST-AR-{start_date}-{end_date}",
                },
            )

        logger.info("Exported %s G/L entries for test fees", len(gl_entries))
        return gl_entries


# Convenience function for easy integration
def create_test_fee_transaction(test_payment):
    """Convenience function to create a test fee transaction.

    Args:
        test_payment: TestPayment instance

    Returns:
        Transaction result dictionary
    """
    integrator = TestFeeFinanceIntegrator()
    return integrator.create_test_fee_transaction(test_payment)


def update_test_payment_status(test_payment, payment_received: bool = True):
    """Convenience function to update test payment transaction status.

    Args:
        test_payment: TestPayment instance
        payment_received: Whether payment has been received

    Returns:
        Update result dictionary
    """
    integrator = TestFeeFinanceIntegrator()
    return integrator.update_payment_transaction(test_payment, payment_received)
