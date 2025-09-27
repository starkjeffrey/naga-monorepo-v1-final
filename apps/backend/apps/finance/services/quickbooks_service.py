"""QuickBooks report service for generating QuickBooks-friendly reports.

Designed for small schools where the accountant manually enters
summarized data into QuickBooks rather than using automated integration.
"""

import json
from datetime import date, timedelta
from decimal import Decimal

from django.utils import timezone

from apps.finance.models import FinancialTransaction

# Constants
DECEMBER = 12


class QuickBooksReportService:
    """Service for generating QuickBooks-friendly reports for manual entry.

    Designed for small schools where the accountant manually enters
    summarized data into QuickBooks rather than using automated integration.
    """

    def generate_monthly_cash_receipts_summary(self, year: int, month: int, format: str = "readable") -> str:
        """Generate a monthly cash receipts summary suitable for QuickBooks entry.

        Args:
            year: Year for the report
            month: Month for the report (1-12)
            format: Output format - "readable" or "json"

        Returns:
            Formatted report string
        """
        # Get transactions for the month
        start_date = date(year, month, 1)
        if month == DECEMBER:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)

        transactions = FinancialTransaction.objects.filter(
            transaction_date__gte=start_date,
            transaction_date__lte=end_date,
        )

        # Summarize by fee type
        receipts = {}
        refunds = {}

        for trans in transactions:
            # Get fee type from reference data or default
            fee_type = trans.reference_data.get("fee_type", "TUITION")
            category = self._get_quickbooks_account_name(fee_type)

            if trans.transaction_type == FinancialTransaction.TransactionType.PAYMENT_RECEIVED:
                if category not in receipts:
                    receipts[category] = Decimal("0.00")
                receipts[category] += trans.amount
            elif trans.transaction_type == FinancialTransaction.TransactionType.PAYMENT_REFUNDED:
                if category not in refunds:
                    refunds[category] = Decimal("0.00")
                refunds[category] += trans.amount  # Already negative

        if format == "json":
            return json.dumps(
                {
                    "period": f"{date(year, month, 1).strftime('%B %Y')}",
                    "receipts": {k: float(v) for k, v in receipts.items()},
                    "refunds": {k: float(v) for k, v in refunds.items()},
                    "net_total": float(sum(receipts.values()) + sum(refunds.values())),
                },
                indent=2,
            )

        # Generate readable report
        month_name = date(year, month, 1).strftime("%B %Y")
        report = [
            "=" * 60,
            f"MONTHLY CASH RECEIPTS SUMMARY - {month_name}",
            "=" * 60,
            "",
        ]

        if not receipts and not refunds:
            report.append("No transactions found for this period.")
            report.append("")
            report.append(f"{'TOTAL RECEIPTS:':.<40} $0.00")
        else:
            # Cash receipts section
            if receipts:
                report.append("CASH RECEIPTS:")
                report.append("-" * 60)
                total_receipts = Decimal("0.00")
                for category, amount in sorted(receipts.items()):
                    report.append(f"{category:.<40} ${amount:,.2f}")
                    total_receipts += amount
                report.append(f"{'TOTAL RECEIPTS:':.<40} ${total_receipts:,.2f}")
                report.append("")

            # Refunds section
            if refunds:
                report.append("REFUNDS ISSUED:")
                report.append("-" * 60)
                total_refunds = Decimal("0.00")
                for category, amount in sorted(refunds.items()):
                    report.append(f"{category:.<40} $({abs(amount):,.2f})")
                    total_refunds += amount
                report.append(f"{'TOTAL REFUNDS:':.<40} $({abs(total_refunds):,.2f})")
                report.append("")

            # Net total
            net_total = sum(receipts.values()) + sum(refunds.values())
            report.append("=" * 60)
            report.append(f"{'NET CASH RECEIPTS:':.<40} ${net_total:,.2f}")

        report.extend(
            [
                "",
                "-" * 60,
                f"Generated on: {timezone.now().strftime('%b %d, %Y at %I:%M %p')}",
                "For QuickBooks Entry: Debit Cash, Credit Income Accounts",
            ],
        )

        return "\n".join(report)

    def generate_quickbooks_journal_entry(self, year: int, month: int) -> str:
        """Generate a journal entry format that's easy to copy into QuickBooks.

        Args:
            year: Year for the entry
            month: Month for the entry (1-12)

        Returns:
            Formatted journal entry
        """
        # Get transactions for the month
        start_date = date(year, month, 1)
        if month == DECEMBER:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)

        transactions = FinancialTransaction.objects.filter(
            transaction_date__gte=start_date,
            transaction_date__lte=end_date,
        )

        # Summarize by fee type
        account_totals = {}

        for trans in transactions:
            fee_type = trans.reference_data.get("fee_type", "TUITION")
            account_name = self._get_quickbooks_account_name(fee_type)

            if account_name not in account_totals:
                account_totals[account_name] = Decimal("0.00")

            if trans.transaction_type == FinancialTransaction.TransactionType.PAYMENT_RECEIVED:
                account_totals[account_name] += trans.amount
            elif trans.transaction_type == FinancialTransaction.TransactionType.PAYMENT_REFUNDED:
                account_totals[account_name] += trans.amount  # Already negative

        # Calculate net cash amount
        net_cash = sum(account_totals.values())

        # Format journal entry
        month_name = date(year, month, 1).strftime("%B %Y")
        entry = [
            "=" * 60,
            f"QUICKBOOKS JOURNAL ENTRY - {month_name}",
            "=" * 60,
            "",
            f"Date: {date(year, month + 1 if month < DECEMBER else 1, 1) - timedelta(days=1)}",
            f"Memo: Cash receipts for {month_name}",
            "",
            "Account                                  Debit        Credit",
            "-" * 60,
        ]

        # Debit to Cash
        if net_cash > 0:
            entry.append(f"{'Dr  Cash - Bank Account':<40} ${net_cash:>10,.2f}")

        # Credits to income accounts
        for account_name, amount in sorted(account_totals.items()):
            if amount > 0:
                entry.append(f"{'Cr  ' + account_name:<40}              ${amount:>10,.2f}")
            elif amount < 0:
                # For negative amounts (refunds), debit the income account
                entry.append(f"{'Dr  ' + account_name:<40} ${abs(amount):>10,.2f}")

        # Credit to Cash for refunds
        if net_cash < 0:
            entry.append(f"{'Cr  Cash - Bank Account':<40}              ${abs(net_cash):>10,.2f}")

        entry.extend(
            [
                "-" * 60,
                f"{'TOTALS':<40} ${abs(net_cash):>10,.2f}  ${abs(net_cash):>10,.2f}",
                "",
                "=" * 60,
            ],
        )

        return "\n".join(entry)

    def generate_bank_deposit_report(self, year: int, month: int) -> str:
        """Generate a bank deposit report showing daily deposits.

        Args:
            year: Year for the report
            month: Month for the report (1-12)

        Returns:
            Formatted deposit report
        """
        # Get transactions for the month
        start_date = date(year, month, 1)
        if month == DECEMBER:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)

        transactions = (
            FinancialTransaction.objects.filter(
                transaction_date__gte=start_date,
                transaction_date__lte=end_date,
            )
            .select_related("student__person")
            .order_by("transaction_date", "created_at")
        )

        # Group by date
        daily_deposits: dict[date, list] = {}
        for trans in transactions:
            date_key = trans.transaction_date
            if date_key not in daily_deposits:
                daily_deposits[date_key] = []
            daily_deposits[date_key].append(trans)

        # Format report
        month_name = date(year, month, 1).strftime("%B %Y")
        report = [
            "=" * 80,
            f"BANK DEPOSIT REPORT - {month_name}",
            "=" * 80,
            "",
        ]

        total_deposits = Decimal("0.00")

        for deposit_date in sorted(daily_deposits.keys()):
            transactions_on_date = daily_deposits[deposit_date]

            report.append(f"Deposit Date: {deposit_date.strftime('%m/%d/%Y')}")
            report.append("-" * 80)
            report.append("Student ID   Name                          Type         Receipt#      Amount")
            report.append("-" * 80)

            daily_total = Decimal("0.00")

            for trans in transactions_on_date:
                if trans.student:
                    student_name = f"{trans.student.person.personal_name} {trans.student.person.family_name}"[:28]
                    student_id = trans.student.student_id
                else:
                    student_name = "N/A"
                    student_id = "N/A"

                trans_type = (
                    "Payment"
                    if trans.transaction_type == FinancialTransaction.TransactionType.PAYMENT_RECEIVED
                    else "Refund"
                )
                amount_str = f"${trans.amount:,.2f}" if trans.amount > 0 else f"(${abs(trans.amount):,.2f})"
                receipt_number = trans.reference_data.get("payment_reference", "N/A")

                report.append(
                    f"{student_id:<12} {student_name:<30} {trans_type:<12} {receipt_number:<13} {amount_str:>10}",
                )
                daily_total += trans.amount

            report.append("-" * 80)
            report.append(f"{'Daily Total:':<67} ${daily_total:>10,.2f}")
            report.append("")

            total_deposits += daily_total

        report.extend(
            [
                "=" * 80,
                f"{'TOTAL DEPOSITS FOR THE MONTH:':<67} ${total_deposits:>10,.2f}",
                "",
                "-" * 80,
                f"Generated on: {timezone.now().strftime('%b %d, %Y at %I:%M %p')}",
            ],
        )

        return "\n".join(report)

    def generate_monthly_transaction_details(self, year: int, month: int) -> str:
        """Generate detailed transaction report for reconciliation.

        Args:
            year: Year for the report
            month: Month for the report (1-12)

        Returns:
            Formatted detailed report
        """
        # Get transactions for the month
        start_date = date(year, month, 1)
        if month == DECEMBER:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)

        transactions = (
            FinancialTransaction.objects.filter(
                transaction_date__gte=start_date,
                transaction_date__lte=end_date,
            )
            .select_related("student__person")
            .order_by("transaction_date", "created_at")
        )

        # Separate payments and refunds
        payments = [
            t for t in transactions if t.transaction_type == FinancialTransaction.TransactionType.PAYMENT_RECEIVED
        ]
        refunds = [
            t for t in transactions if t.transaction_type == FinancialTransaction.TransactionType.PAYMENT_REFUNDED
        ]

        # Format report
        month_name = date(year, month, 1).strftime("%B %Y")
        report = [
            "=" * 100,
            f"DETAILED TRANSACTION REPORT - {month_name}",
            "=" * 100,
            "",
        ]

        # Payments section
        if payments:
            report.append("PAYMENTS RECEIVED:")
            report.append("-" * 100)
            report.append(
                "Date       Student ID   Name                    Fee Type      Method       Receipt#      Amount",
            )
            report.append("-" * 100)

            total_payments = Decimal("0.00")
            for trans in payments:
                if trans.student:
                    student_name = f"{trans.student.person.personal_name} {trans.student.person.family_name}"[:22]
                    student_id = trans.student.student_id
                else:
                    student_name = "N/A"
                    student_id = "N/A"

                fee_type = trans.reference_data.get("fee_type", "TUITION")[:12]
                payment_method = trans.reference_data.get("payment_method", "CASH")[:11]
                receipt_number = trans.reference_data.get("payment_reference", "N/A")[:12]

                report.append(
                    f"{trans.transaction_date.strftime('%m/%d/%Y')} "
                    f"{student_id:<12} "
                    f"{student_name:<23} "
                    f"{fee_type:<13} "
                    f"{payment_method:<12} "
                    f"{receipt_number:<13} "
                    f"${trans.amount:>10,.2f}",
                )
                total_payments += trans.amount

            report.append("-" * 100)
            report.append(f"{'TOTAL PAYMENTS:':<85} ${total_payments:>10,.2f}")
            report.append("")

        # Refunds section
        if refunds:
            report.append("REFUNDS ISSUED:")
            report.append("-" * 100)
            report.append(
                "Date       Student ID   Name                    Fee Type      Reason                      Amount",
            )
            report.append("-" * 100)

            total_refunds = Decimal("0.00")
            for trans in refunds:
                if trans.student:
                    student_name = f"{trans.student.person.personal_name} {trans.student.person.family_name}"[:22]
                    student_id = trans.student.student_id
                else:
                    student_name = "N/A"
                    student_id = "N/A"

                fee_type = trans.reference_data.get("fee_type", "TUITION")[:12]
                reason = trans.reference_data.get("refund_reason", "Not specified")[:25]

                report.append(
                    f"{trans.transaction_date.strftime('%m/%d/%Y')} "
                    f"{student_id:<12} "
                    f"{student_name:<23} "
                    f"{fee_type:<13} "
                    f"{reason:<27} "
                    f"(${abs(trans.amount):>9,.2f})",
                )
                total_refunds += trans.amount

            report.append("-" * 100)
            report.append(f"{'TOTAL REFUNDS:':<85} (${abs(total_refunds):>9,.2f})")
            report.append("")

        # Summary
        net_total = sum(t.amount for t in transactions)
        report.extend(
            [
                "=" * 100,
                f"{'NET RECEIPTS:':<85} ${net_total:>10,.2f}",
                "",
                "-" * 100,
                f"Generated on: {timezone.now().strftime('%b %d, %Y at %I:%M %p')}",
            ],
        )

        return "\n".join(report)

    def _get_quickbooks_account_name(self, fee_type: str) -> str:
        """Map fee types to QuickBooks income account names."""
        mapping = {
            "TUITION": "Tuition Income",
            "APPLICATION": "Application Fee Income",
            "PLACEMENT_TEST": "Test Fee Income",
            "REGISTRATION": "Registration Fee Income",
            "TECHNOLOGY": "Technology Fee Income",
            "MATERIALS": "Materials Fee Income",
            "LATE": "Late Fee Income",
            "OTHER": "Other Income",
        }

        return mapping.get(fee_type, "Other Income")
