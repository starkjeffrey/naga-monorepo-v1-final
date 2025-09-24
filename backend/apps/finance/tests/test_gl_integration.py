"""Tests for G/L integration functionality.

Since the existing FinancialTransaction model is designed for audit trails
rather than payment tracking, these tests focus on the G/L models and
demonstrate how the integration would work with proper payment data.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.finance.models import (
    FeeGLMapping,
    FeeType,
    GLAccount,
    GLBatch,
    JournalEntry,
    JournalEntryLine,
)

User = get_user_model()


class GLModelIntegrationTest(TestCase):
    """Test G/L models working together for integration scenarios."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="accountant@test.com",
            password="testpass123",
        )

        # Create chart of accounts
        self.cash_account = GLAccount.objects.create(
            account_code="1010",
            account_name="Cash on Hand",
            account_type=GLAccount.AccountType.ASSET,
            account_category=GLAccount.AccountCategory.CURRENT_ASSET,
        )

        self.tuition_revenue = GLAccount.objects.create(
            account_code="4100",
            account_name="Tuition Revenue",
            account_type=GLAccount.AccountType.REVENUE,
            account_category=GLAccount.AccountCategory.OPERATING_REVENUE,
        )

        self.application_revenue = GLAccount.objects.create(
            account_code="4200",
            account_name="Application Fee Revenue",
            account_type=GLAccount.AccountType.REVENUE,
            account_category=GLAccount.AccountCategory.OPERATING_REVENUE,
        )

        # Create fee mappings
        FeeGLMapping.objects.create(
            fee_type=FeeType.OTHER,  # Using OTHER for tuition since TUITION doesn't exist
            fee_code="TUITION",
            revenue_account=self.tuition_revenue,
            effective_date=date(2025, 1, 1),
        )

        FeeGLMapping.objects.create(
            fee_type=FeeType.APPLICATION,
            fee_code="APPLICATION",
            revenue_account=self.application_revenue,
            effective_date=date(2025, 1, 1),
        )

    def test_create_revenue_journal_entry(self):
        """Test creating a journal entry for revenue recognition."""
        # Create journal entry for daily cash receipts
        entry = JournalEntry.objects.create(
            entry_number="JE-2025-01-001",
            entry_date=date(2025, 1, 15),
            accounting_period="2025-01",
            entry_type=JournalEntry.EntryType.REVENUE,
            description="Daily cash receipts - tuition and fees",
            prepared_by=self.user,
        )

        # Create debit to cash
        JournalEntryLine.objects.create(
            journal_entry=entry,
            line_number=1,
            gl_account=self.cash_account,
            debit_amount=Decimal("1050.00"),
            credit_amount=Decimal("0.00"),
            description="Cash received",
        )

        # Create credit to tuition revenue
        JournalEntryLine.objects.create(
            journal_entry=entry,
            line_number=2,
            gl_account=self.tuition_revenue,
            debit_amount=Decimal("0.00"),
            credit_amount=Decimal("1000.00"),
            description="Tuition revenue",
        )

        # Create credit to application revenue
        JournalEntryLine.objects.create(
            journal_entry=entry,
            line_number=3,
            gl_account=self.application_revenue,
            debit_amount=Decimal("0.00"),
            credit_amount=Decimal("50.00"),
            description="Application fee revenue",
        )

        # Calculate totals
        entry.calculate_totals()
        entry.refresh_from_db()

        assert entry.is_balanced
        assert entry.total_debits == Decimal("1050.00")
        assert entry.total_credits == Decimal("1050.00")

    def test_create_refund_journal_entry(self):
        """Test creating a journal entry for refunds."""
        entry = JournalEntry.objects.create(
            entry_number="JE-2025-01-002",
            entry_date=date(2025, 1, 20),
            accounting_period="2025-01",
            entry_type=JournalEntry.EntryType.REFUND,
            description="Tuition refund - course withdrawal",
            prepared_by=self.user,
        )

        # Debit tuition revenue (reduce revenue)
        JournalEntryLine.objects.create(
            journal_entry=entry,
            line_number=1,
            gl_account=self.tuition_revenue,
            debit_amount=Decimal("500.00"),
            credit_amount=Decimal("0.00"),
            description="Tuition refund",
        )

        # Credit cash (reduce cash)
        JournalEntryLine.objects.create(
            journal_entry=entry,
            line_number=2,
            gl_account=self.cash_account,
            debit_amount=Decimal("0.00"),
            credit_amount=Decimal("500.00"),
            description="Cash refunded",
        )

        entry.calculate_totals()
        entry.refresh_from_db()

        assert entry.is_balanced
        assert entry.total_debits == Decimal("500.00")
        assert entry.total_credits == Decimal("500.00")

    def test_batch_processing(self):
        """Test batch processing of journal entries."""
        batch = GLBatch.objects.create(
            batch_number="GL-2025-01-MONTH",
            accounting_period="2025-01",
            status=GLBatch.BatchStatus.PENDING,
        )

        # Create multiple entries for the batch
        entries = []
        for i in range(3):
            entry = JournalEntry.objects.create(
                entry_number=f"JE-2025-01-{i + 1:03d}",
                entry_date=date(2025, 1, i + 1),
                accounting_period="2025-01",
                entry_type=JournalEntry.EntryType.REVENUE,
                description=f"Daily receipts day {i + 1}",
                prepared_by=self.user,
                total_debits=Decimal("1000.00"),
                total_credits=Decimal("1000.00"),
            )
            batch.add_journal_entry(entry)
            entries.append(entry)

        batch.refresh_from_db()

        assert batch.total_entries == 3
        assert batch.total_amount == Decimal("3000.00")

        # Verify all entries have batch ID
        for entry in entries:
            entry.refresh_from_db()
            assert entry.batch_id == batch.batch_number

    def test_journal_entry_workflow(self):
        """Test the complete journal entry workflow."""
        # Create entry
        entry = JournalEntry.objects.create(
            entry_number="JE-2025-01-100",
            entry_date=date(2025, 1, 31),
            accounting_period="2025-01",
            entry_type=JournalEntry.EntryType.REVENUE,
            description="Month-end revenue entry",
            prepared_by=self.user,
        )

        # Add balanced lines
        JournalEntryLine.objects.create(
            journal_entry=entry,
            line_number=1,
            gl_account=self.cash_account,
            debit_amount=Decimal("5000.00"),
            credit_amount=Decimal("0.00"),
            description="Total cash received",
        )

        JournalEntryLine.objects.create(
            journal_entry=entry,
            line_number=2,
            gl_account=self.tuition_revenue,
            debit_amount=Decimal("0.00"),
            credit_amount=Decimal("5000.00"),
            description="Total tuition revenue",
        )

        entry.calculate_totals()

        # Initial status
        assert entry.status == JournalEntry.EntryStatus.DRAFT

        # Approve
        entry.approve(self.user)
        entry.refresh_from_db()
        assert entry.status == JournalEntry.EntryStatus.APPROVED
        assert entry.approved_by == self.user
        assert entry.approved_date is not None

        # Post to G/L
        entry.post_to_gl()
        entry.refresh_from_db()
        assert entry.status == JournalEntry.EntryStatus.POSTED
        assert entry.posted_date is not None

    def test_fee_gl_mapping_effectiveness(self):
        """Test that fee mappings work correctly with date ranges."""
        # Current mapping
        current_mapping = FeeGLMapping.objects.get(
            fee_type=FeeType.OTHER,  # Using OTHER for tuition
            effective_date=date(2025, 1, 1),
        )

        # Create new revenue account for future
        new_tuition_revenue = GLAccount.objects.create(
            account_code="4101",
            account_name="Tuition Revenue - New Structure",
            account_type=GLAccount.AccountType.REVENUE,
            account_category=GLAccount.AccountCategory.OPERATING_REVENUE,
        )

        # End current mapping
        current_mapping.end_date = date(2025, 3, 31)
        current_mapping.save()

        # Create new mapping starting April
        new_mapping = FeeGLMapping.objects.create(
            fee_type=FeeType.OTHER,  # Using OTHER for tuition
            fee_code="TUITION",
            revenue_account=new_tuition_revenue,
            effective_date=date(2025, 4, 1),
        )

        # Test that correct mapping is active for different dates
        jan_mapping = (
            FeeGLMapping.objects.filter(
                fee_type=FeeType.OTHER,  # Using OTHER for tuition
                effective_date__lte=date(2025, 1, 15),
            )
            .exclude(end_date__lt=date(2025, 1, 15))
            .first()
        )

        assert jan_mapping == current_mapping
        assert jan_mapping.revenue_account == self.tuition_revenue

        apr_mapping = (
            FeeGLMapping.objects.filter(
                fee_type=FeeType.OTHER,  # Using OTHER for tuition
                effective_date__lte=date(2025, 4, 15),
            )
            .exclude(end_date__lt=date(2025, 4, 15))
            .first()
        )

        assert apr_mapping == new_mapping
        assert apr_mapping.revenue_account == new_tuition_revenue


class GLAccountHierarchyTest(TestCase):
    """Test G/L account hierarchy functionality."""

    def test_create_account_hierarchy(self):
        """Test creating a hierarchical chart of accounts."""
        # Create parent accounts
        assets = GLAccount.objects.create(
            account_code="1000",
            account_name="Assets",
            account_type=GLAccount.AccountType.ASSET,
            account_category=GLAccount.AccountCategory.CURRENT_ASSET,
        )

        current_assets = GLAccount.objects.create(
            account_code="1100",
            account_name="Current Assets",
            account_type=GLAccount.AccountType.ASSET,
            account_category=GLAccount.AccountCategory.CURRENT_ASSET,
            parent_account=assets,
        )

        cash = GLAccount.objects.create(
            account_code="1110",
            account_name="Cash and Cash Equivalents",
            account_type=GLAccount.AccountType.ASSET,
            account_category=GLAccount.AccountCategory.CURRENT_ASSET,
            parent_account=current_assets,
        )

        petty_cash = GLAccount.objects.create(
            account_code="1111",
            account_name="Petty Cash",
            account_type=GLAccount.AccountType.ASSET,
            account_category=GLAccount.AccountCategory.CURRENT_ASSET,
            parent_account=cash,
        )

        # Test hierarchy
        assert petty_cash.full_account_path == "Assets > Current Assets > Cash and Cash Equivalents > Petty Cash"
        assert cash.parent_account == current_assets
        assert current_assets.parent_account == assets
        assert assets.parent_account is None

    def test_account_type_categories(self):
        """Test that account types and categories work correctly."""
        # Create accounts of different types
        asset = GLAccount.objects.create(
            account_code="1000",
            account_name="Assets",
            account_type=GLAccount.AccountType.ASSET,
            account_category=GLAccount.AccountCategory.CURRENT_ASSET,
        )

        liability = GLAccount.objects.create(
            account_code="2000",
            account_name="Liabilities",
            account_type=GLAccount.AccountType.LIABILITY,
            account_category=GLAccount.AccountCategory.CURRENT_LIABILITY,
        )

        equity = GLAccount.objects.create(
            account_code="3000",
            account_name="Equity",
            account_type=GLAccount.AccountType.EQUITY,
            account_category=GLAccount.AccountCategory.CURRENT_LIABILITY,  # No equity category, using liability
        )

        revenue = GLAccount.objects.create(
            account_code="4000",
            account_name="Revenue",
            account_type=GLAccount.AccountType.REVENUE,
            account_category=GLAccount.AccountCategory.OPERATING_REVENUE,
        )

        expense = GLAccount.objects.create(
            account_code="5000",
            account_name="Expenses",
            account_type=GLAccount.AccountType.EXPENSE,
            account_category=GLAccount.AccountCategory.OPERATING_EXPENSE,
        )

        # Verify account types
        assert asset.account_type == GLAccount.AccountType.ASSET
        assert liability.account_type == GLAccount.AccountType.LIABILITY
        assert equity.account_type == GLAccount.AccountType.EQUITY
        assert revenue.account_type == GLAccount.AccountType.REVENUE
        assert expense.account_type == GLAccount.AccountType.EXPENSE
